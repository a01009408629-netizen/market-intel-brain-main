import asyncio
import logging
import time
from typing import Any, Dict, Optional, Tuple
import orjson
import xxhash
import redis.asyncio as redis

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("HyperSWR")

# Mock External Fetcher
async def real_fetch(source_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    await asyncio.sleep(0.5)  # Simulate network I/O
    return {"source": source_name, "params": params, "timestamp": time.time()}

class MAIFAFingerprint:
    @staticmethod
    def build(source_name: str, params: Dict[str, Any]) -> str:
        serialized = orjson.dumps(params, option=orjson.OPT_SORT_KEYS)
        return f"swr:{source_name}:{xxhash.xxh64(serialized).hexdigest()}"

class SmartTTL:
    _rules = {"user_profile": (60, 300), "market_data": (5, 60)} # (Freshness, Max Stale)

    @classmethod
    def get(cls, source_name: str) -> Tuple[int, int]:
        return cls._rules.get(source_name, (30, 300))

class EnterpriseSWROrchestrator:
    def __init__(self, redis_url: str = "redis://localhost"):
        self.redis = redis.Redis.from_url(redis_url)
        self.semaphores: Dict[str, asyncio.Semaphore] = {}
        self.cb_fails: Dict[str, int] = {}

    def _get_semaphore(self, source_name: str) -> asyncio.Semaphore:
        if source_name not in self.semaphores:
            self.semaphores[source_name] = asyncio.Semaphore(10) # Max 10 concurrent outgoing per source
        return self.semaphores[source_name]

    async def get_with_swr(self, source_name: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        cache_key = MAIFAFingerprint.build(source_name, params)
        fresh_ttl, stale_ttl = SmartTTL.get(source_name)
        
        cached_raw = await self.redis.get(cache_key)
        
        if cached_raw:
            cached_data = orjson.loads(cached_raw)
            current_time = time.time()
            
            if current_time > cached_data["stale_at"]:
                logger.info(f"[CACHE STALE] Triggering bg refresh for {cache_key}")
                asyncio.create_task(
                    self._refresh_pipeline(source_name, params, cache_key, fresh_ttl, stale_ttl, cached_data["hash"])
                )
            else:
                logger.info(f"[CACHE HIT] Fresh data served for {cache_key}")
                
            return cached_data["data"]

        logger.info(f"[CACHE MISS] Blocking wait for {cache_key}")
        return await self._refresh_pipeline(source_name, params, cache_key, fresh_ttl, stale_ttl, None)

    async def _refresh_pipeline(
        self, source_name: str, params: Dict[str, Any], key: str, fresh_ttl: int, stale_ttl: int, old_hash: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        
        lock_key = f"lock:{key}"
        lock_acquired = await self.redis.set(lock_key, "1", nx=True, ex=10)
        
        if not lock_acquired:
            logger.info(f"[LOCK ACQUIRED BY OTHER WORKER] Skipping refresh for {key}")
            return None

        try:
            async with self._get_semaphore(source_name):
                # Circuit Breaker Check
                if self.cb_fails.get(source_name,0) > 5:
                    logger.error(f"[CIRCUIT BREAKER OPEN] Aborting fetch for {source_name}")
                    raise Exception("Circuit Breaker Open")

                new_data = await asyncio.wait_for(real_fetch(source_name, params), timeout=3.0)
                self.cb_fails[source_name] = 0 # Reset CB on success
                
                new_payload_bytes = orjson.dumps(new_data)
                new_hash = xxhash.xxh64(new_payload_bytes).hexdigest()
                
                if new_hash == old_hash:
                    logger.info(f"[HYPER-SWR] No changes. Extending TTL for {key}")
                    await self.redis.expire(key, stale_ttl)
                else:
                    logger.info(f"[HYPER-SWR] Data changed. Updating cache for {key}")
                    payload = {
                        "data": new_data,
                        "hash": new_hash,
                        "stale_at": time.time() + fresh_ttl
                    }
                    await self.redis.set(key, orjson.dumps(payload), ex=stale_ttl)
                    
                return new_data

        except Exception as e:
            self.cb_fails[source_name] = self.cb_fails.get(source_name, 0) + 1
            logger.error(f"[FETCH FAILED] {str(e)}. Stale-If-Error applied for {key}")
            # Stale-If-Error: Extend TTL of existing stale data dynamically to prevent cascade failures
            await self.redis.expire(key, stale_ttl) 
            return None
        finally:
            await self.redis.delete(lock_key)
