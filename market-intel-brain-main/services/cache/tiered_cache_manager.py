"""
Advanced Tiered Cache Manager with SWR (Stale-While-Revalidate)

This module provides a sophisticated two-tier caching system with:
- L1 (Local Memory) using cachetools.TTLCache for instant responses
- L2 (Redis) for shared cache across workers/servers
- SWR logic: serve stale data immediately while refreshing in background
- Async-first design with asyncio.create_task for background operations
"""

import asyncio
import json
import logging
import time
from typing import Any, Optional, Dict, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum

import cachetools
import redis.asyncio as redis


class CacheLayer(Enum):
    """Cache layer enumeration"""
    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"


@dataclass
class CacheEntry:
    """Cache entry with metadata for SWR logic"""
    value: Any
    timestamp: float
    ttl: int
    stale_at: float
    key: str
    hit_count: int = 0
    last_accessed: float = 0.0


@dataclass
class CacheConfig:
    """Configuration for tiered cache"""
    l1_max_size: int = 1000
    l1_ttl: int = 300          # 5 minutes for L1
    l2_ttl: int = 3600         # 1 hour for L2
    stale_while_revalidate_window: int = 60  # 1 minute stale window
    enable_swr: bool = True
    background_refresh: bool = True
    redis_url: str = "redis://localhost:6379"


class TieredCacheManager:
    """
    Advanced Tiered Cache Manager with SWR support.
    
    Features:
    - L1 (Memory): cachetools.TTLCache for instant responses
    - L2 (Redis): Shared cache across workers/servers
    - SWR: Serve stale data while refreshing in background
    - Async-first design with proper task management
    - Comprehensive statistics and health monitoring
    """
    
    def __init__(self, config: Optional[CacheConfig] = None, logger: Optional[logging.Logger] = None):
        self.config = config or CacheConfig()
        self.logger = logger or logging.getLogger("TieredCacheManager")
        
        # Initialize L1 cache with TTLCache
        self.l1_cache = cachetools.TTLCache(
            maxsize=self.config.l1_max_size,
            ttl=self.config.l1_ttl
        )
        
        # Redis client (lazy initialization)
        self._redis_client: Optional[redis.Redis] = None
        
        # Background refresh management
        self._refresh_tasks: Dict[str, asyncio.Task] = {}
        self._refresh_locks: Dict[str, asyncio.Lock] = {}
        
        # Statistics tracking
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
            f"TieredCacheManager initialized: "
            f"L1(max_size={self.config.l1_max_size}, ttl={self.config.l1_ttl}s), "
            f"L2(ttl={self.config.l2_ttl}s), "
            f"SWR={'enabled' if self.config.enable_swr else 'disabled'}"
        )
    
    async def _get_redis_client(self) -> redis.Redis:
        """Get or create Redis client with lazy initialization"""
        if self._redis_client is None:
            self._redis_client = redis.from_url(
                self.config.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self._redis_client.ping()
            self.logger.info("Redis client connected successfully")
        return self._redis_client
    
    def _generate_cache_key(self, key: str, namespace: str = "default") -> str:
        """Generate namespaced cache key"""
        return f"{namespace}:{key}"
    
    def _is_stale(self, entry: CacheEntry) -> bool:
        """Check if cache entry is stale"""
        return time.time() >= entry.stale_at
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is completely expired"""
        return time.time() >= (entry.timestamp + entry.ttl)
    
    async def get(
        self, 
        key: str, 
        namespace: str = "default",
        refresh_func: Optional[Callable[[], Any]] = None
    ) -> Optional[Any]:
        """
        Get value from cache with SWR logic.
        
        Args:
            key: Cache key
            namespace: Cache namespace for isolation
            refresh_func: Optional function to refresh stale data
            
        Returns:
            Cached value or None if not found
        """
        cache_key = self._generate_cache_key(key, namespace)
        current_time = time.time()
        
        try:
            self._stats['total_requests'] += 1
            
            # Try L1 cache first (fastest)
            l1_entry = self._get_from_l1(cache_key, current_time)
            if l1_entry:
                self._stats['l1_hits'] += 1
                self.logger.debug(f"L1 hit: {cache_key}")
                
                # SWR logic: if stale, serve immediately and refresh in background
                if (self.config.enable_swr and 
                    self.config.background_refresh and 
                    self._is_stale(l1_entry) and 
                    not self._is_expired(l1_entry) and
                    refresh_func):
                    
                    self._stats['stale_hits'] += 1
                    await self._trigger_background_refresh(
                        key, namespace, l1_entry, refresh_func
                    )
                
                return l1_entry.value
            
            # Try L2 cache (Redis)
            l2_entry = await self._get_from_l2(cache_key, current_time)
            if l2_entry:
                self._stats['l2_hits'] += 1
                self.logger.debug(f"L2 hit: {cache_key}")
                
                # Promote to L1 for faster future access
                self._set_to_l1(cache_key, l2_entry)
                
                # SWR logic for L2
                if (self.config.enable_swr and 
                    self.config.background_refresh and 
                    self._is_stale(l2_entry) and 
                    not self._is_expired(l2_entry) and
                    refresh_func):
                    
                    self._stats['stale_hits'] += 1
                    await self._trigger_background_refresh(
                        key, namespace, l2_entry, refresh_func
                    )
                
                return l2_entry.value
            
            # Cache miss
            self._stats['l1_misses'] += 1
            self._stats['l2_misses'] += 1
            self.logger.debug(f"Cache miss: {cache_key}")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting cache entry {cache_key}: {e}")
            return None
    
    def _get_from_l1(self, cache_key: str, current_time: float) -> Optional[CacheEntry]:
        """Get entry from L1 (memory) cache"""
        try:
            entry = self.l1_cache.get(cache_key)
            if entry is None:
                return None
            
            # Update access statistics
            entry.hit_count += 1
            entry.last_accessed = current_time
            
            return entry
            
        except Exception as e:
            self.logger.error(f"Error reading from L1 cache: {e}")
            return None
    
    async def _get_from_l2(self, cache_key: str, current_time: float) -> Optional[CacheEntry]:
        """Get entry from L2 (Redis) cache"""
        try:
            redis_client = await self._get_redis_client()
            
            # Get cached data from Redis
            cached_data = await redis_client.get(cache_key)
            if cached_data is None:
                return None
            
            # Deserialize cache entry
            entry_data = json.loads(cached_data)
            
            # Reconstruct CacheEntry
            entry = CacheEntry(
                value=entry_data['value'],
                timestamp=entry_data['timestamp'],
                ttl=entry_data['ttl'],
                stale_at=entry_data['stale_at'],
                key=entry_data['key'],
                hit_count=entry_data.get('hit_count', 0) + 1,
                last_accessed=current_time
            )
            
            return entry
            
        except Exception as e:
            self.logger.error(f"Error reading from L2 cache: {e}")
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
            ttl: Time to live (uses default if None)
            namespace: Cache namespace
            
        Returns:
            True if successful, False otherwise
        """
        cache_key = self._generate_cache_key(key, namespace)
        current_time = time.time()
        cache_ttl = ttl or self.config.l2_ttl
        
        try:
            # Create cache entry with SWR metadata
            entry = CacheEntry(
                value=value,
                timestamp=current_time,
                ttl=cache_ttl,
                stale_at=current_time + cache_ttl - self.config.stale_while_revalidate_window,
                key=cache_key,
                hit_count=0,
                last_accessed=current_time
            )
            
            # Set in L1 cache
            self._set_to_l1(cache_key, entry)
            
            # Set in L2 cache (Redis)
            await self._set_to_l2(cache_key, entry)
            
            self.logger.debug(f"Cache set: {cache_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting cache entry {cache_key}: {e}")
            return False
    
    def _set_to_l1(self, cache_key: str, entry: CacheEntry):
        """Set entry in L1 cache"""
        try:
            self.l1_cache[cache_key] = entry
        except Exception as e:
            self.logger.error(f"Error setting L1 cache entry {cache_key}: {e}")
    
    async def _set_to_l2(self, cache_key: str, entry: CacheEntry):
        """Set entry in L2 cache (Redis)"""
        try:
            redis_client = await self._get_redis_client()
            
            # Prepare entry data for serialization
            entry_data = asdict(entry)
            
            # Store in Redis with TTL
            await redis_client.setex(
                cache_key,
                entry.ttl + 60,  # Add buffer time
                json.dumps(entry_data)
            )
            
        except Exception as e:
            self.logger.error(f"Error setting L2 cache entry {cache_key}: {e}")
    
    async def _trigger_background_refresh(
        self,
        key: str,
        namespace: str,
        stale_entry: CacheEntry,
        refresh_func: Callable
    ):
        """Trigger background refresh for stale cache entry using asyncio.create_task"""
        refresh_key = f"{namespace}:{key}"
        
        try:
            # Check if refresh already in progress
            if refresh_key in self._refresh_tasks:
                task = self._refresh_tasks[refresh_key]
                if not task.done():
                    self.logger.debug(f"Background refresh already in progress: {refresh_key}")
                    return
            
            # Get or create refresh lock
            if refresh_key not in self._refresh_locks:
                self._refresh_locks[refresh_key] = asyncio.Lock()
            
            lock = self._refresh_locks[refresh_key]
            
            # Use asyncio.create_task for background refresh
            async def refresh_with_lock():
                async with lock:
                    # Double-check after acquiring lock
                    if refresh_key in self._refresh_tasks:
                        existing_task = self._refresh_tasks[refresh_key]
                        if not existing_task.done():
                            return
                    
                    # Create background task
                    task = asyncio.create_task(
                        self._background_refresh(key, namespace, stale_entry, refresh_func)
                    )
                    self._refresh_tasks[refresh_key] = task
                    
                    self.logger.debug(f"Background refresh triggered: {refresh_key}")
                    self._stats['background_refreshes'] += 1
                    
                    # Wait for completion (but don't block main flow)
                    try:
                        await task
                    except Exception as e:
                        self.logger.error(f"Background refresh error: {e}")
                    finally:
                        # Clean up completed task
                        if refresh_key in self._refresh_tasks:
                            del self._refresh_tasks[refresh_key]
            
            # Start background refresh without awaiting
            asyncio.create_task(refresh_with_lock())
            
        except Exception as e:
            self.logger.error(f"Error triggering background refresh: {e}")
    
    async def _background_refresh(
        self,
        key: str,
        namespace: str,
        stale_entry: CacheEntry,
        refresh_func: Callable
    ):
        """Background refresh task that updates both cache layers"""
        refresh_key = f"{namespace}:{key}"
        
        try:
            self.logger.debug(f"Starting background refresh: {refresh_key}")
            
            # Execute refresh function (could be API call, database query, etc.)
            if asyncio.iscoroutinefunction(refresh_func):
                fresh_value = await refresh_func()
            else:
                fresh_value = refresh_func()
            
            # Update cache entry with fresh data
            current_time = time.time()
            updated_entry = CacheEntry(
                value=fresh_value,
                timestamp=current_time,
                ttl=stale_entry.ttl,
                stale_at=current_time + stale_entry.ttl - self.config.stale_while_revalidate_window,
                key=stale_entry.key,
                hit_count=stale_entry.hit_count,
                last_accessed=current_time
            )
            
            # Update both cache layers
            self._set_to_l1(stale_entry.key, updated_entry)
            await self._set_to_l2(stale_entry.key, updated_entry)
            
            self.logger.debug(f"Background refresh completed: {refresh_key}")
            
        except Exception as e:
            self.logger.error(f"Background refresh failed for {refresh_key}: {e}")
    
    async def invalidate(self, key: str, namespace: str = "default"):
        """Invalidate cache entry from both layers"""
        cache_key = self._generate_cache_key(key, namespace)
        
        try:
            # Remove from L1
            if cache_key in self.l1_cache:
                del self.l1_cache[cache_key]
            
            # Remove from L2
            try:
                redis_client = await self._get_redis_client()
                await redis_client.delete(cache_key)
            except Exception:
                pass  # Redis might be unavailable
            
            # Cancel background refresh if in progress
            refresh_key = f"{namespace}:{key}"
            if refresh_key in self._refresh_tasks:
                task = self._refresh_tasks[refresh_key]
                if not task.done():
                    task.cancel()
                del self._refresh_tasks[refresh_key]
            
            self.logger.debug(f"Cache invalidated: {cache_key}")
            
        except Exception as e:
            self.logger.error(f"Error invalidating cache {cache_key}: {e}")
    
    async def clear_namespace(self, namespace: str = "default"):
        """Clear all entries in a namespace"""
        try:
            # Clear L1 entries
            l1_keys_to_remove = [
                key for key in self.l1_cache.keys() 
                if key.startswith(f"{namespace}:")
            ]
            for key in l1_keys_to_remove:
                del self.l1_cache[key]
            
            # Clear L2 entries
            try:
                redis_client = await self._get_redis_client()
                pattern = f"{namespace}:*"
                keys = await redis_client.keys(pattern)
                if keys:
                    await redis_client.delete(*keys)
            except Exception:
                pass  # Redis might be unavailable
            
            self.logger.info(f"Cache namespace cleared: {namespace}")
            
        except Exception as e:
            self.logger.error(f"Error clearing namespace {namespace}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        total_hits = self._stats['l1_hits'] + self._stats['l2_hits']
        total_requests = self._stats['total_requests']
        
        return {
            'l1_stats': {
                'hits': self._stats['l1_hits'],
                'misses': self._stats['l1_misses'],
                'size': len(self.l1_cache),
                'max_size': self.l1_cache.maxsize,
                'utilization': len(self.l1_cache) / self.l1_cache.maxsize
            },
            'l2_stats': {
                'hits': self._stats['l2_hits'],
                'misses': self._stats['l2_misses']
            },
            'swr_stats': {
                'stale_hits': self._stats['stale_hits'],
                'background_refreshes': self._stats['background_refreshes'],
                'active_refresh_tasks': len([
                    t for t in self._refresh_tasks.values() if not t.done()
                ])
            },
            'overall_stats': {
                'total_hits': total_hits,
                'total_requests': total_requests,
                'hit_rate': total_hits / total_requests if total_requests > 0 else 0
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on cache system"""
        try:
            # Test L1 cache
            test_key = "health_check_test"
            test_value = {"test": True, "timestamp": time.time()}
            
            await self.set(test_key, test_value, ttl=10)
            retrieved = await self.get(test_key)
            l1_healthy = retrieved == test_value
            
            # Test L2 cache
            l2_healthy = False
            try:
                redis_client = await self._get_redis_client()
                await redis_client.ping()
                l2_healthy = True
            except Exception as e:
                self.logger.warning(f"Redis health check failed: {e}")
            
            # Clean up test key
            await self.invalidate(test_key)
            
            return {
                'healthy': l1_healthy and l2_healthy,
                'l1_healthy': l1_healthy,
                'l2_healthy': l2_healthy,
                'timestamp': time.time(),
                'stats': self.get_stats()
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    async def close(self):
        """Clean up resources"""
        try:
            # Cancel all background tasks
            for task in self._refresh_tasks.values():
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self._refresh_tasks:
                await asyncio.gather(
                    *self._refresh_tasks.values(),
                    return_exceptions=True
                )
            
            # Close Redis connection
            if self._redis_client:
                await self._redis_client.close()
            
            self.logger.info("TieredCacheManager closed successfully")
            
        except Exception as e:
            self.logger.error(f"Error closing cache manager: {e}")


# Example usage and factory function
async def create_cache_manager(
    config: Optional[CacheConfig] = None,
    logger: Optional[logging.Logger] = None
) -> TieredCacheManager:
    """Factory function to create and initialize cache manager"""
    manager = TieredCacheManager(config, logger)
    
    # Perform health check
    health = await manager.health_check()
    if not health['healthy']:
        logger.warning(f"Cache manager health check failed: {health}")
    
    return manager


# Decorator for easy cache integration
def cached(
    key_template: str,
    ttl: Optional[int] = None,
    namespace: str = "default",
    cache_manager: Optional[TieredCacheManager] = None
):
    """
    Decorator for caching function results with SWR support.
    
    Args:
        key_template: Template for cache key (can use {arg_name} placeholders)
        ttl: Time to live for cache entry
        namespace: Cache namespace
        cache_manager: Cache manager instance
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Use provided cache manager or create default
            manager = cache_manager or TieredCacheManager()
            
            # Generate cache key
            try:
                cache_key = key_template.format(*args, **kwargs)
            except (KeyError, IndexError):
                # Fallback to function name if template fails
                cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = await manager.get(cache_key, namespace)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            await manager.set(cache_key, result, ttl, namespace)
            return result
        
        return wrapper
    return decorator
