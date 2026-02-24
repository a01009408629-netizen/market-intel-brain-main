"""
Hybrid Cache Manager - High-Efficiency / Low-Resource Mode

Refactored TieredCacheManager with graceful Redis fallback for constrained hardware.
Implements resilient caching that works flawlessly on 8GB RAM + HDD systems.

Features:
- Graceful Redis fallback to InMemoryCache
- Silent fallback without exceptions to upper layers
- Deterministic behavior for consistent performance
- Minimal resource footprint
- Async-first design with non-blocking operations
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
    L2_FALLBACK = "l2_fallback"  # In-memory fallback when Redis unavailable


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
    """Configuration for hybrid cache optimized for low-resource systems"""
    l1_max_size: int = 500          # Reduced for 8GB RAM
    l1_ttl: int = 60               # 1 minute for L1 (faster eviction)
    l2_ttl: int = 300              # 5 minutes for L2 (reduced from 1 hour)
    stale_while_revalidate_window: int = 30  # 30 seconds stale window
    enable_swr: bool = True
    background_refresh: bool = True
    redis_url: str = "redis://localhost:6379"
    redis_connection_timeout: float = 2.0  # Fast timeout for constrained hardware
    enable_redis_fallback: bool = True
    fallback_cache_size: int = 2000  # Larger fallback cache for reliability


class HybridCacheManager:
    """
    High-Efficiency Hybrid Cache Manager.
    
    Features:
    - Graceful Redis fallback to InMemoryCache
    - Silent fallback without exceptions
    - Optimized for 8GB RAM + HDD systems
    - Non-blocking async operations
    - Minimal resource footprint
    """
    
    def __init__(self, config: Optional[CacheConfig] = None, logger: Optional[logging.Logger] = None):
        self.config = config or CacheConfig()
        self.logger = logger or logging.getLogger("HybridCacheManager")
        
        # Initialize L1 cache with reduced size for low-resource systems
        self.l1_cache = cachetools.TTLCache(
            maxsize=self.config.l1_max_size,
            ttl=self.config.l1_ttl
        )
        
        # Redis client and fallback state
        self._redis_client: Optional[redis.Redis] = None
        self._redis_available: bool = False
        self._redis_checked: bool = False
        self._fallback_cache: Optional[cachetools.TTLCache] = None
        
        # Background refresh management
        self._refresh_tasks: Dict[str, asyncio.Task] = {}
        self._refresh_locks: Dict[str, asyncio.Lock] = {}
        
        # Statistics tracking
        self._stats = {
            'l1_hits': 0,
            'l2_hits': 0,
            'l2_fallback_hits': 0,
            'l1_misses': 0,
            'l2_misses': 0,
            'stale_hits': 0,
            'background_refreshes': 0,
            'total_requests': 0,
            'redis_fallback_count': 0,
            'redis_connection_errors': 0
        }
        
        self.logger.info(
            f"HybridCacheManager initialized (Low-Resource Mode): "
            f"L1(max_size={self.config.l1_max_size}, ttl={self.config.l1_ttl}s), "
            f"L2(ttl={self.config.l2_ttl}s), "
            f"SWR={'enabled' if self.config.enable_swr else 'disabled'}, "
            f"Fallback={'enabled' if self.config.enable_redis_fallback else 'disabled'}"
        )
    
    async def _check_redis_availability(self) -> bool:
        """
        Check Redis availability with graceful fallback.
        Returns True if Redis is available, False otherwise.
        """
        if self._redis_checked:
            return self._redis_available
        
        try:
            # Attempt Redis connection with short timeout
            self._redis_client = redis.from_url(
                self.config.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=self.config.redis_connection_timeout,
                socket_timeout=self.config.redis_connection_timeout
            )
            
            # Test connection with timeout
            await asyncio.wait_for(self._redis_client.ping(), timeout=self.config.redis_connection_timeout)
            
            self._redis_available = True
            self._redis_checked = True
            self.logger.info("✅ Redis connection established successfully")
            return True
            
        except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
            self._redis_available = False
            self._redis_checked = True
            self._stats['redis_connection_errors'] += 1
            
            # Initialize fallback cache if enabled
            if self.config.enable_redis_fallback and self._fallback_cache is None:
                self._fallback_cache = cachetools.TTLCache(
                    maxsize=self.config.fallback_cache_size,
                    ttl=self.config.l2_ttl
                )
                self.logger.info("[REDIS_FALLBACK] Redis unavailable - initialized InMemoryCache fallback")
            
            # Log fallback event to stdout only (no HDD I/O for warnings)
            print(f"[HybridCacheManager] Redis unavailable - using InMemoryCache fallback: {type(e).__name__}")
            return False
            
        except Exception as e:
            self._redis_available = False
            self._redis_checked = True
            self._stats['redis_connection_errors'] += 1
            
            if self.config.enable_redis_fallback and self._fallback_cache is None:
                self._fallback_cache = cachetools.TTLCache(
                    maxsize=self.config.fallback_cache_size,
                    ttl=self.config.l2_ttl
                )
                self.logger.info("[REDIS_FALLBACK] Redis error - initialized InMemoryCache fallback")
            
            print(f"[HybridCacheManager] Redis error - using InMemoryCache fallback: {type(e).__name__}")
            return False
    
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
        Get value from cache with graceful fallback and SWR logic.
        
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
            
            # Try L2 cache (Redis or fallback)
            l2_entry = await self._get_from_l2(cache_key, current_time)
            if l2_entry:
                if self._redis_available:
                    self._stats['l2_hits'] += 1
                    self.logger.debug(f"L2 Redis hit: {cache_key}")
                else:
                    self._stats['l2_fallback_hits'] += 1
                    self.logger.debug(f"L2 Fallback hit: {cache_key}")
                
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
        """Get entry from L1 cache"""
        try:
            entry = self.l1_cache.get(cache_key)
            if entry:
                entry.last_accessed = current_time
                entry.hit_count += 1
                return entry
        except Exception as e:
            self.logger.debug(f"L1 cache error for {cache_key}: {e}")
        return None
    
    async def _get_from_l2(self, cache_key: str, current_time: float) -> Optional[CacheEntry]:
        """Get entry from L2 cache (Redis or fallback)"""
        # Check Redis availability
        redis_available = await self._check_redis_availability()
        
        if redis_available and self._redis_client:
            try:
                # Try Redis
                data = await self._redis_client.get(cache_key)
                if data:
                    entry_data = json.loads(data)
                    entry = CacheEntry(**entry_data)
                    entry.last_accessed = current_time
                    entry.hit_count += 1
                    return entry
            except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
                # Redis failed during operation, fallback to InMemoryCache
                self._redis_available = False
                self._stats['redis_fallback_count'] += 1
                print(f"[HybridCacheManager] Redis operation failed - switching to fallback: {type(e).__name__}")
                
                # Initialize fallback if not already done
                if self._fallback_cache is None:
                    self._fallback_cache = cachetools.TTLCache(
                        maxsize=self.config.fallback_cache_size,
                        ttl=self.config.l2_ttl
                    )
            except Exception as e:
                self.logger.debug(f"Redis error for {cache_key}: {e}")
        
        # Use fallback cache
        if self._fallback_cache is not None:
            try:
                entry = self._fallback_cache.get(cache_key)
                if entry:
                    entry.last_accessed = current_time
                    entry.hit_count += 1
                    return entry
            except Exception as e:
                self.logger.debug(f"Fallback cache error for {cache_key}: {e}")
        
        return None
    
    def _set_to_l1(self, cache_key: str, entry: CacheEntry):
        """Set entry to L1 cache"""
        try:
            self.l1_cache[cache_key] = entry
        except Exception as e:
            self.logger.debug(f"Failed to set L1 cache entry {cache_key}: {e}")
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        namespace: str = "default"
    ) -> bool:
        """
        Set value in cache with graceful fallback.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live (uses config default if None)
            namespace: Cache namespace
            
        Returns:
            True if successful, False otherwise
        """
        cache_key = self._generate_cache_key(key, namespace)
        effective_ttl = ttl or self.config.l2_ttl
        current_time = time.time()
        
        try:
            # Create cache entry
            entry = CacheEntry(
                value=value,
                timestamp=current_time,
                ttl=effective_ttl,
                stale_at=current_time + self.config.stale_while_revalidate_window,
                key=cache_key,
                last_accessed=current_time
            )
            
            # Set in L1 cache
            self._set_to_l1(cache_key, entry)
            
            # Set in L2 cache (Redis or fallback)
            await self._set_to_l2(cache_key, entry)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting cache entry {cache_key}: {e}")
            return False
    
    async def _set_to_l2(self, cache_key: str, entry: CacheEntry):
        """Set entry to L2 cache (Redis or fallback)"""
        redis_available = await self._check_redis_availability()
        
        if redis_available and self._redis_client:
            try:
                # Try Redis
                entry_data = json.dumps(asdict(entry))
                await self._redis_client.setex(
                    cache_key, 
                    entry.ttl, 
                    entry_data
                )
                return
            except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
                # Redis failed during operation
                self._redis_available = False
                self._stats['redis_fallback_count'] += 1
                print(f"[HybridCacheManager] Redis write failed - using fallback: {type(e).__name__}")
                
                # Initialize fallback if not already done
                if self._fallback_cache is None:
                    self._fallback_cache = cachetools.TTLCache(
                        maxsize=self.config.fallback_cache_size,
                        ttl=self.config.l2_ttl
                    )
            except Exception as e:
                self.logger.debug(f"Redis write error for {cache_key}: {e}")
        
        # Use fallback cache
        if self._fallback_cache is not None:
            try:
                self._fallback_cache[cache_key] = entry
            except Exception as e:
                self.logger.debug(f"Fallback cache write error for {cache_key}: {e}")
    
    async def _trigger_background_refresh(
        self, 
        key: str, 
        namespace: str, 
        entry: CacheEntry, 
        refresh_func: Callable
    ):
        """Trigger background refresh with non-blocking operation"""
        cache_key = self._generate_cache_key(key, namespace)
        
        # Prevent multiple refreshes for same key
        if cache_key in self._refresh_tasks:
            return
        
        # Create lock for this key if not exists
        if cache_key not in self._refresh_locks:
            self._refresh_locks[cache_key] = asyncio.Lock()
        
        # Create background refresh task
        task = asyncio.create_task(
            self._background_refresh(key, namespace, entry, refresh_func)
        )
        self._refresh_tasks[cache_key] = task
        
        # Clean up task when done
        task.add_done_callback(lambda t: self._refresh_tasks.pop(cache_key, None))
    
    async def _background_refresh(
        self, 
        key: str, 
        namespace: str, 
        entry: CacheEntry, 
        refresh_func: Callable
    ):
        """Background refresh with non-blocking execution"""
        cache_key = self._generate_cache_key(key, namespace)
        
        async with self._refresh_locks[cache_key]:
            try:
                # Execute refresh function
                new_value = await refresh_func() if asyncio.iscoroutinefunction(refresh_func) else refresh_func()
                
                if new_value is not None:
                    # Update cache with new value
                    await self.set(key, new_value, namespace=namespace)
                    self._stats['background_refreshes'] += 1
                    self.logger.debug(f"Background refresh completed: {cache_key}")
                
            except Exception as e:
                self.logger.debug(f"Background refresh failed for {cache_key}: {e}")
    
    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete entry from cache"""
        cache_key = self._generate_cache_key(key, namespace)
        
        try:
            # Delete from L1
            self.l1_cache.pop(cache_key, None)
            
            # Delete from L2
            redis_available = await self._check_redis_availability()
            if redis_available and self._redis_client:
                try:
                    await self._redis_client.delete(cache_key)
                except Exception as e:
                    self.logger.debug(f"Redis delete error for {cache_key}: {e}")
            
            # Delete from fallback
            if self._fallback_cache is not None:
                self._fallback_cache.pop(cache_key, None)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting cache entry {cache_key}: {e}")
            return False
    
    async def clear(self, namespace: str = "default") -> bool:
        """Clear all entries in namespace"""
        try:
            # Clear L1 cache (simple approach - recreate)
            self.l1_cache.clear()
            
            # Clear L2 cache
            redis_available = await self._check_redis_availability()
            if redis_available and self._redis_client:
                try:
                    pattern = f"{namespace}:*"
                    keys = await self._redis_client.keys(pattern)
                    if keys:
                        await self._redis_client.delete(*keys)
                except Exception as e:
                    self.logger.debug(f"Redis clear error for namespace {namespace}: {e}")
            
            # Clear fallback cache
            if self._fallback_cache is not None:
                self._fallback_cache.clear()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error clearing namespace {namespace}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_hits = self._stats['l1_hits'] + self._stats['l2_hits'] + self._stats['l2_fallback_hits']
        hit_rate = total_hits / self._stats['total_requests'] if self._stats['total_requests'] > 0 else 0
        
        return {
            'total_requests': self._stats['total_requests'],
            'l1_hits': self._stats['l1_hits'],
            'l2_hits': self._stats['l2_hits'],
            'l2_fallback_hits': self._stats['l2_fallback_hits'],
            'l1_misses': self._stats['l1_misses'],
            'l2_misses': self._stats['l2_misses'],
            'stale_hits': self._stats['stale_hits'],
            'background_refreshes': self._stats['background_refreshes'],
            'overall_hit_rate': hit_rate,
            'redis_available': self._redis_available,
            'redis_fallback_count': self._stats['redis_fallback_count'],
            'redis_connection_errors': self._stats['redis_connection_errors'],
            'l1_cache_size': len(self.l1_cache),
            'l2_fallback_size': len(self._fallback_cache) if self._fallback_cache else 0
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        redis_available = await self._check_redis_availability()
        
        return {
            'healthy': True,
            'redis_available': redis_available,
            'fallback_active': not redis_available and self._fallback_cache is not None,
            'l1_cache_size': len(self.l1_cache),
            'l2_fallback_size': len(self._fallback_cache) if self._fallback_cache else 0,
            'stats': self.get_stats()
        }
    
    async def close(self):
        """Close cache manager and cleanup resources"""
        try:
            # Cancel background tasks
            for task in self._refresh_tasks.values():
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self._refresh_tasks:
                await asyncio.gather(*self._refresh_tasks.values(), return_exceptions=True)
            
            # Close Redis connection if available
            if self._redis_client:
                await self._redis_client.close()
            
            # Clear caches
            self.l1_cache.clear()
            if self._fallback_cache:
                self._fallback_cache.clear()
            
            self.logger.info("HybridCacheManager closed successfully")
            
        except Exception as e:
            self.logger.error(f"Error closing HybridCacheManager: {e}")


# Factory function for easy instantiation
def get_hybrid_cache_manager(config: Optional[CacheConfig] = None) -> HybridCacheManager:
    """Get hybrid cache manager instance"""
    return HybridCacheManager(config)
