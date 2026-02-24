import asyncio
import json
import logging
import time
import hashlib
import orjson
from typing import Any, Dict, Callable, Optional, Set
import redis.asyncio as redis
from services.data_ingestion.fingerprint import MAIFAFingerprint

logger = logging.getLogger("MAIFA.SWR")

class SWRCounter:
    __slots__ = ("cache_hit", "cache_miss", "stale_served", "refresh_failed")
    
    def __init__(self):
        self.cache_hit = 0
        self.cache_miss = 0
        self.stale_served = 0
        self.refresh_failed = 0
    
    def to_dict(self) -> Dict[str, int]:
        return {
            "cache_hit": self.cache_hit,
            "cache_miss": self.cache_miss,
            "stale_served": self.stale_served,
            "refresh_failed": self.refresh_failed
        }

class EnterpriseSWR:
    __slots__ = ("_redis", "_semaphores", "_inflight_refreshes", "_counters", "_ttl_default")
    
    def __init__(self, redis_url: str = "redis://localhost:6379", ttl_default: int = 300):
        self._redis = None
        self._redis_url = redis_url
        self._ttl_default = ttl_default
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._inflight_refreshes: Set[str] = set()
        self._counters = SWRCounter()
    
    async def _get_redis(self):
        if not self._redis:
            self._redis = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis
    
    def _get_semaphore(self, source: str) -> asyncio.Semaphore:
        if source not in self._semaphores:
            self._semaphores[source] = asyncio.Semaphore(10)  # Limit 10 concurrent per source
        return self._semaphores[source]
    
    def _calculate_checksum(self, data: Any) -> str:
        if isinstance(data, (str, bytes)):
            payload = data
        else:
            payload = orjson.dumps(data, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
    
    async def get_with_swr(
        self,
        source: str,
        params: Dict[str, Any],
        real_fetch: Callable[[], Any],
        ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        ttl = ttl or self._ttl_default
        fp = MAIFAFingerprint.build(source, params)
        redis = await self._get_redis()
        semaphore = self._get_semaphore(source)
        
        try:
            # Step 1: Async Redis GET
            cached_raw = await redis.get(fp)
            
            if cached_raw is not None:
                cached_data = orjson.loads(cached_raw)
                self._counters.cache_hit += 1
                
                # Step 2: IF Fresh -> Return data
                cached_ts = cached_data.get("ts", 0)
                if time.time() - cached_ts < ttl:
                    logger.info(f"CACHE_HIT | FP: {fp} | SOURCE: {source}")
                    return {
                        "fp": fp,
                        "status": "fresh",
                        "data": cached_data["payload"],
                        "ts": cached_ts,
                        "checksum": cached_data.get("checksum")
                    }
                
                # Step 3: IF Stale -> Return stale + fire background refresh
                self._counters.stale_served += 1
                logger.info(f"STALE_SERVED | FP: {fp} | SOURCE: {source}")
                
                if fp not in self._inflight_refreshes:
                    asyncio.create_task(self._refresh_pipeline(fp, source, real_fetch, ttl))
                
                return {
                    "fp": fp,
                    "status": "stale",
                    "data": cached_data["payload"],
                    "ts": cached_ts,
                    "checksum": cached_data.get("checksum")
                }
            
            # Step 4: IF Miss -> Wait for fetch with semaphore
            self._counters.cache_miss += 1
            logger.info(f"CACHE_MISS | FP: {fp} | SOURCE: {source}")
            
            async with semaphore:
                fresh_data = await real_fetch()
                checksum = self._calculate_checksum(fresh_data)
                
                cache_entry = {
                    "payload": fresh_data,
                    "ts": time.time(),
                    "checksum": checksum
                }
                
                await redis.setex(fp, ttl, orjson.dumps(cache_entry, separators=(",", ":")))
                
                return {
                    "fp": fp,
                    "status": "fresh",
                    "data": fresh_data,
                    "ts": time.time(),
                    "checksum": checksum
                }
                
        except Exception as e:
            logger.error(f"SWR_ERROR | FP: {fp} | SOURCE: {source} | ERROR: {str(e)}")
            raise
    
    async def _refresh_pipeline(self, fp: str, source: str, real_fetch: Callable[[], Any], ttl: int):
        if fp in self._inflight_refreshes:
            return
        
        self._inflight_refreshes.add(fp)
        redis = await self._get_redis()
        
        try:
            # Distributed lock to prevent thundering herd
            lock_key = f"lock:{fp}"
            lock_acquired = await redis.set(lock_key, "1", nx=True, ex=30)
            
            if not lock_acquired:
                logger.debug(f"LOCK_FAILED | FP: {fp} | SOURCE: {source}")
                return
            
            try:
                fresh_data = await real_fetch()
                new_checksum = self._calculate_checksum(fresh_data)
                
                # Get current cached data for diffing
                cached_raw = await redis.get(fp)
                if cached_raw:
                    cached_data = orjson.loads(cached_raw)
                    old_checksum = cached_data.get("checksum")
                    
                    if old_checksum == new_checksum:
                        # Hyper-SWR Diffing: checksum unchanged -> extend TTL
                        await redis.expire(fp, ttl)
                        logger.info(f"DIFF_SAME | FP: {fp} | SOURCE: {source} | TTL_EXTENDED")
                    else:
                        # Hyper-SWR Diffing: checksum changed -> update data
                        cache_entry = {
                            "payload": fresh_data,
                            "ts": time.time(),
                            "checksum": new_checksum
                        }
                        await redis.setex(fp, ttl, orjson.dumps(cache_entry, separators=(",", ":")))
                        logger.info(f"DIFF_CHANGED | FP: {fp} | SOURCE: {source} | DATA_UPDATED")
                else:
                    # No existing data, set new
                    cache_entry = {
                        "payload": fresh_data,
                        "ts": time.time(),
                        "checksum": new_checksum
                    }
                    await redis.setex(fp, ttl, orjson.dumps(cache_entry, separators=(",", ":")))
                    logger.info(f"DIFF_NEW | FP: {fp} | SOURCE: {source} | DATA_CREATED")
                    
            except Exception as fetch_error:
                # Stale-If-Error: Extend TTL of existing stale data
                self._counters.refresh_failed += 1
                logger.error(f"REFRESH_FAILED | FP: {fp} | SOURCE: {source} | ERROR: {str(fetch_error)}")
                
                cached_raw = await redis.get(fp)
                if cached_raw:
                    # Extend TTL of existing stale data to prevent cascade failure
                    await redis.expire(fp, ttl * 2)  # Double TTL on failure
                    logger.warning(f"STALE_IF_ERROR | FP: {fp} | SOURCE: {source} | TTL_EXTENDED")
                    
            finally:
                # Release distributed lock
                await redis.delete(lock_key)
                
        finally:
            self._inflight_refreshes.discard(fp)
    
    def get_metrics(self) -> Dict[str, Any]:
        return self._counters.to_dict()

# Global enterprise SWR instance
enterprise_swr = EnterpriseSWR()
