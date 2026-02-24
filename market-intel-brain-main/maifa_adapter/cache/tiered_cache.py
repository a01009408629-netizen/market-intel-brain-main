"""
Tiered Cache Manager Implementation

This module provides a two-tier caching system with L1 (memory) and L2 (Redis)
layers, with intelligent cache management and SWR integration.
"""

import asyncio
import json
import logging
import time
import hashlib
from typing import Any, Optional, Dict, Union, Callable
from dataclasses import dataclass
from enum import Enum

import cachetools
import redis.asyncio as redis
import msgpack

from ..core.exceptions import TransientAdapterError


class CacheLayer(Enum):
    """Cache layers"""
    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    value: Any
    timestamp: float
    ttl: int
    layer: CacheLayer
    stale_at: float
    key: str
    hit_count: int = 0
    last_accessed: float = 0


@dataclass
class CacheConfig:
    """Cache configuration"""
    l1_max_size: int = 1000
    l1_ttl: int = 300          # 5 minutes
    l2_ttl: int = 3600         # 1 hour
    stale_ttl: int = 60          # 1 minute stale window
    enable_swr: bool = True
    background_refresh: bool = True
    compression: bool = True
    serialization: str = "msgpack"  # "msgpack" or "json"


class TieredCacheManager:
    """
    Tiered cache manager with L1 (memory) and L2 (Redis) layers.
    
    Provides intelligent caching with SWR logic, automatic background
    refresh, and seamless layer synchronization.
    """
    
    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        config: Optional[CacheConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.redis_client = redis_client
        self.config = config or CacheConfig()
        self.logger = logger or logging.getLogger("TieredCacheManager")
        
        # Initialize L1 cache (memory)
        self.l1_cache = cachetools.TTLCache(
            maxsize=self.config.l1_max_size,
            ttl=self.config.l1_ttl
        )
        
        # Background refresh tasks
        self._refresh_tasks: Dict[str, asyncio.Task] = {}
        self._refresh_locks: Dict[str, asyncio.Lock] = {}
        
        # Statistics
        self._stats = {
            'l1_hits': 0,
            'l2_hits': 0,
            'l1_misses': 0,
            'l2_misses': 0,
            'stale_hits': 0,
            'background_refreshes': 0,
            'total_requests': 0
        }
        
        self.logger.info(
            f"Initialized tiered cache: L1(max_size={self.config.l1_max_size}, ttl={self.config.l1_ttl}s), "
            f"L2(ttl={self.config.l2_ttl}s), SWR={'enabled' if self.config.enable_swr else 'disabled'}"
        )
    
    def _generate_cache_key(self, key: str, namespace: str = "default") -> str:
        """Generate cache key with namespace"""
        return f"{namespace}:{key}"
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            if self.config.serialization == "msgpack":
                return msgpack.packb(value, default=str)
            else:
                return json.dumps(value).encode('utf-8')
        except Exception as e:
            self.logger.error(f"Error serializing value: {e}")
            raise TransientAdapterError(
                message=f"Cache serialization failed: {str(e)}",
                adapter_name="TieredCacheManager"
            ) from e
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        try:
            if self.config.serialization == "msgpack":
                return msgpack.unpackb(data, raw=False)
            else:
                return json.loads(data.decode('utf-8'))
        except Exception as e:
            self.logger.error(f"Error deserializing value: {e}")
            raise TransientAdapterError(
                message=f"Cache deserialization failed: {str(e)}",
                adapter_name="TieredCacheManager"
            ) from e
    
    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """
        Get value from cache with SWR logic.
        
        Args:
            key: Cache key
            namespace: Cache namespace
            
        Returns:
            Cached value or None if not found
        """
        cache_key = self._generate_cache_key(key, namespace)
        current_time = time.time()
        
        try:
            self._stats['total_requests'] += 1
            
            # Try L1 cache first
            l1_entry = self._get_from_l1(cache_key, current_time)
            if l1_entry:
                self._stats['l1_hits'] += 1
                self.logger.debug(f"L1 hit for key: {cache_key}")
                
                # Check if stale and trigger background refresh
                if (self.config.enable_swr and 
                    self.config.background_refresh and 
                    l1_entry.stale_at <= current_time):
                    await self._trigger_background_refresh(key, namespace, l1_entry)
                
                return l1_entry.value
            
            # Try L2 cache
            l2_entry = await self._get_from_l2(cache_key, current_time)
            if l2_entry:
                self._stats['l2_hits'] += 1
                self.logger.debug(f"L2 hit for key: {cache_key}")
                
                # Promote to L1
                await self._set_to_l1(cache_key, l2_entry)
                
                # Check if stale and trigger background refresh
                if (self.config.enable_swr and 
                    self.config.background_refresh and 
                    l2_entry.stale_at <= current_time):
                    await self._trigger_background_refresh(key, namespace, l2_entry)
                
                return l2_entry.value
            
            # Cache miss
            self._stats['l1_misses'] += 1
            self._stats['l2_misses'] += 1
            self.logger.debug(f"Cache miss for key: {cache_key}")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting from cache: {e}")
            return None
    
    def _get_from_l1(self, cache_key: str, current_time: float) -> Optional[CacheEntry]:
        """Get entry from L1 cache"""
        try:
            cached_value = self.l1_cache.get(cache_key)
            if cached_value is None:
                return None
            
            # L1 stores CacheEntry objects directly
            if isinstance(cached_value, CacheEntry):
                entry = cached_value
            else:
                # Backward compatibility
                entry = CacheEntry(
                    value=cached_value,
                    timestamp=current_time - self.config.l1_ttl + 1,  # Force stale check
                    ttl=self.config.l1_ttl,
                    layer=CacheLayer.L1_MEMORY,
                    stale_at=current_time - self.config.stale_ttl - 1,
                    key=cache_key
                )
                self._set_to_l1(cache_key, entry)
            
            # Update access stats
            entry.hit_count += 1
            entry.last_accessed = current_time
            
            return entry
            
        except Exception as e:
            self.logger.error(f"Error getting from L1: {e}")
            return None
    
    async def _get_from_l2(self, cache_key: str, current_time: float) -> Optional[CacheEntry]:
        """Get entry from L2 cache"""
        if not self.redis_client:
            return None
        
        try:
            # Get cached data from Redis
            cached_data = await self.redis_client.get(cache_key)
            if cached_data is None:
                return None
            
            # Deserialize entry
            entry_data = self._deserialize_value(cached_data)
            
            # Create CacheEntry
            entry = CacheEntry(
                value=entry_data['value'],
                timestamp=entry_data['timestamp'],
                ttl=entry_data['ttl'],
                layer=CacheLayer.L2_REDIS,
                stale_at=entry_data['timestamp'] + entry_data['ttl'] - self.config.stale_ttl,
                key=cache_key,
                hit_count=entry_data.get('hit_count', 0) + 1,
                last_accessed=current_time
            )
            
            return entry
            
        except Exception as e:
            self.logger.error(f"Error getting from L2: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: str = "default"
    ) -> bool:
        """
        Set value in both cache layers.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live (None for default)
            namespace: Cache namespace
            
        Returns:
            True if successful, False otherwise
        """
        cache_key = self._generate_cache_key(key, namespace)
        current_time = time.time()
        cache_ttl = ttl or self.config.l2_ttl
        
        try:
            # Create cache entry
            entry = CacheEntry(
                value=value,
                timestamp=current_time,
                ttl=cache_ttl,
                layer=CacheLayer.L1_MEMORY,
                stale_at=current_time + cache_ttl - self.config.stale_ttl,
                key=cache_key,
                hit_count=0,
                last_accessed=current_time
            )
            
            # Set in L1
            await self._set_to_l1(cache_key, entry)
            
            # Set in L2
            if self.redis_client:
                await self._set_to_l2(cache_key, entry)
            
            self.logger.debug(f"Set cache entry: {cache_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting cache: {e}")
            return False
    
    async def _set_to_l1(self, cache_key: str, entry: CacheEntry):
        """Set entry in L1 cache"""
        try:
            self.l1_cache[cache_key] = entry
        except Exception as e:
            self.logger.error(f"Error setting to L1: {e}")
    
    async def _set_to_l2(self, cache_key: str, entry: CacheEntry):
        """Set entry in L2 cache"""
        try:
            # Prepare entry data
            entry_data = {
                'value': entry.value,
                'timestamp': entry.timestamp,
                'ttl': entry.ttl,
                'hit_count': entry.hit_count,
                'layer': entry.layer.value
            }
            
            # Serialize and store in Redis
            serialized_data = self._serialize_value(entry_data)
            await self.redis_client.setex(
                cache_key,
                entry.ttl + 60,  # Add buffer time
                serialized_data
            )
            
        except Exception as e:
            self.logger.error(f"Error setting to L2: {e}")
    
    async def _trigger_background_refresh(
        self,
        key: str,
        namespace: str,
        stale_entry: CacheEntry
    ):
        """Trigger background refresh for stale cache entry"""
        try:
            # Check if refresh already in progress
            refresh_key = f"{namespace}:{key}"
            if refresh_key in self._refresh_tasks:
                task = self._refresh_tasks[refresh_key]
                if not task.done():
                    self.logger.debug(f"Background refresh already in progress: {refresh_key}")
                    return
            
            # Get refresh lock
            if refresh_key not in self._refresh_locks:
                self._refresh_locks[refresh_key] = asyncio.Lock()
            
            lock = self._refresh_locks[refresh_key]
            
            async with lock:
                # Double-check after acquiring lock
                if refresh_key in self._refresh_tasks and not self._refresh_tasks[refresh_key].done():
                    return
                
                # Create background refresh task
                task = asyncio.create_task(
                    self._background_refresh(key, namespace, stale_entry)
                )
                self._refresh_tasks[refresh_key] = task
                
                self.logger.debug(f"Triggered background refresh for: {refresh_key}")
                self._stats['stale_hits'] += 1
                self._stats['background_refreshes'] += 1
                
        except Exception as e:
            self.logger.error(f"Error triggering background refresh: {e}")
    
    async def _background_refresh(
        self,
        key: str,
        namespace: str,
        stale_entry: CacheEntry
    ):
        """Background refresh task"""
        refresh_key = f"{namespace}:{key}"
        
        try:
            self.logger.debug(f"Starting background refresh for: {refresh_key}")
            
            # This would be overridden by the cache user
            # The actual refresh logic should be provided by the user
            # For now, we'll just mark it as refreshed
            
            # Simulate refresh delay
            await asyncio.sleep(0.1)
            
            # Update entry timestamp (simulate fresh data)
            stale_entry.timestamp = time.time()
            stale_entry.stale_at = time.time() + stale_entry.ttl - self.config.stale_ttl
            
            # Update caches
            await self._set_to_l1(stale_entry.key, stale_entry)
            await self._set_to_l2(stale_entry.key, stale_entry)
            
            self.logger.debug(f"Completed background refresh for: {refresh_key}")
            
        except Exception as e:
            self.logger.error(f"Error in background refresh: {e}")
        
        finally:
            # Clean up task
            if refresh_key in self._refresh_tasks:
                del self._refresh_tasks[refresh_key]
    
    async def invalidate(self, key: str, namespace: str = "default"):
        """Invalidate cache entry"""
        cache_key = self._generate_cache_key(key, namespace)
        
        try:
            # Remove from L1
            if cache_key in self.l1_cache:
                del self.l1_cache[cache_key]
            
            # Remove from L2
            if self.redis_client:
                await self.redis_client.delete(cache_key)
            
            # Cancel background refresh if in progress
            refresh_key = f"{namespace}:{key}"
            if refresh_key in self._refresh_tasks:
                task = self._refresh_tasks[refresh_key]
                if not task.done():
                    task.cancel()
                del self._refresh_tasks[refresh_key]
            
            self.logger.debug(f"Invalidated cache entry: {cache_key}")
            
        except Exception as e:
            self.logger.error(f"Error invalidating cache: {e}")
    
    async def clear_namespace(self, namespace: str = "default"):
        """Clear all entries in namespace"""
        try:
            # Clear L1 entries for namespace
            keys_to_remove = []
            for key in self.l1_cache.keys():
                if key.startswith(f"{namespace}:"):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.l1_cache[key]
            
            # Clear L2 entries for namespace
            if self.redis_client:
                pattern = f"{namespace}:*"
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
            
            self.logger.info(f"Cleared cache namespace: {namespace}")
            
        except Exception as e:
            self.logger.error(f"Error clearing namespace: {e}")
    
    async def clear_all(self):
        """Clear all cache entries"""
        try:
            # Clear L1 cache
            self.l1_cache.clear()
            
            # Clear L2 cache
            if self.redis_client:
                await self.redis_client.flushdb()
            
            # Cancel all background tasks
            for task in self._refresh_tasks.values():
                if not task.done():
                    task.cancel()
            self._refresh_tasks.clear()
            
            self.logger.info("Cleared all cache entries")
            
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_hits = self._stats['l1_hits'] + self._stats['l2_hits']
        total_misses = self._stats['l1_misses'] + self._stats['l2_misses']
        total_requests = self._stats['total_requests']
        
        l1_size = len(self.l1_cache)
        l1_max_size = self.l1_cache.maxsize
        
        return {
            'l1_stats': {
                'hits': self._stats['l1_hits'],
                'misses': self._stats['l1_misses'],
                'size': l1_size,
                'max_size': l1_max_size,
                'utilization': l1_size / l1_max_size if l1_max_size > 0 else 0
            },
            'l2_stats': {
                'hits': self._stats['l2_hits'],
                'misses': self._stats['l2_misses']
            },
            'swr_stats': {
                'stale_hits': self._stats['stale_hits'],
                'background_refreshes': self._stats['background_refreshes'],
                'active_refresh_tasks': len([t for t in self._refresh_tasks.values() if not t.done()])
            },
            'overall_stats': {
                'total_hits': total_hits,
                'total_misses': total_misses,
                'total_requests': total_requests,
                'hit_rate': total_hits / total_requests if total_requests > 0 else 0,
                'miss_rate': total_misses / total_requests if total_requests > 0 else 0
            },
            'config': {
                'l1_max_size': self.config.l1_max_size,
                'l1_ttl': self.config.l1_ttl,
                'l2_ttl': self.config.l2_ttl,
                'stale_ttl': self.config.stale_ttl,
                'enable_swr': self.config.enable_swr,
                'background_refresh': self.config.background_refresh,
                'serialization': self.config.serialization,
                'redis_available': self.redis_client is not None
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on cache system"""
        try:
            # Test L1 cache
            test_key = "health_check"
            test_value = {"test": True, "timestamp": time.time()}
            
            await self.set(test_key, test_value, ttl=10)
            retrieved_value = await self.get(test_key)
            
            l1_healthy = retrieved_value is not None
            l2_healthy = True
            
            if self.redis_client:
                # Test Redis connection
                try:
                    await self.redis_client.ping()
                    l2_healthy = True
                except Exception:
                    l2_healthy = False
            
            return {
                'healthy': l1_healthy and l2_healthy,
                'l1_healthy': l1_healthy,
                'l2_healthy': l2_healthy,
                'test_key': test_key,
                'timestamp': time.time(),
                'stats': self.get_stats()
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'timestamp': time.time()
            }
