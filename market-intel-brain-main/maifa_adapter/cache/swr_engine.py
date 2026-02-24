"""
SWR (Stale-While-Revalidate) Engine Implementation

This module provides advanced SWR logic with background refresh,
cache invalidation, and intelligent refresh scheduling.
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Optional, Dict, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum

from .tiered_cache import TieredCacheManager, CacheConfig
from ..core.exceptions import TransientAdapterError


class SWRState(Enum):
    """SWR operation states"""
    FRESH = "fresh"           # Data is fresh
    STALE = "stale"           # Data is stale but usable
    REFRESHING = "refreshing"   # Background refresh in progress
    ERROR = "error"           # Error occurred during refresh


@dataclass
class SWREntry:
    """SWR cache entry with refresh state"""
    value: Any
    timestamp: float
    ttl: int
    stale_at: float
    refresh_state: SWRState
    last_refresh_attempt: float
    refresh_error: Optional[str] = None
    refresh_count: int = 0


@dataclass
class SWRConfig:
    """SWR configuration"""
    fresh_ttl: int = 300          # 5 minutes fresh
    stale_ttl: int = 60           # 1 minute stale window
    max_refresh_attempts: int = 3   # Max refresh attempts
    refresh_backoff: float = 5.0   # Backoff between refresh attempts
    enable_background_refresh: bool = True
    refresh_timeout: float = 30.0
    error_retry_delay: float = 60.0  # Delay on refresh errors


class SWREngine:
    """
    Stale-While-Revalidate engine with intelligent cache management.
    
    Provides SWR logic with background refresh, error handling,
    and seamless integration with tiered cache system.
    """
    
    def __init__(
        self,
        cache_manager: TieredCacheManager,
        config: Optional[SWRConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.cache_manager = cache_manager
        self.config = config or SWRConfig()
        self.logger = logger or logging.getLogger("SWREngine")
        
        # SWR state tracking
        self._swr_state: Dict[str, SWREntry] = {}
        self._refresh_locks: Dict[str, asyncio.Lock] = {}
        self._refresh_tasks: Dict[str, asyncio.Task] = {}
        
        # Statistics
        self._stats = {
            'fresh_hits': 0,
            'stale_hits': 0,
            'background_refreshes': 0,
            'refresh_errors': 0,
            'total_requests': 0
        }
        
        self.logger.info(
            f"Initialized SWR engine: fresh_ttl={self.config.fresh_ttl}s, "
            f"stale_ttl={self.config.stale_ttl}s, background_refresh={self.config.enable_background_refresh}"
        )
    
    def _generate_swr_key(self, key: str, namespace: str = "default") -> str:
        """Generate SWR key with namespace"""
        return f"swr:{namespace}:{key}"
    
    async def get(
        self,
        key: str,
        refresh_func: Optional[Callable[[], Awaitable[Any]]] = None,
        namespace: str = "default"
    ) -> Optional[Any]:
        """
        Get value with SWR logic.
        
        Args:
            key: Cache key
            refresh_func: Async function to refresh data
            namespace: Cache namespace
            
        Returns:
            Fresh data, stale data, or None if not found
        """
        swr_key = self._generate_swr_key(key, namespace)
        current_time = time.time()
        
        try:
            self._stats['total_requests'] += 1
            
            # Get from cache manager
            cached_value = await self.cache_manager.get(key, namespace)
            
            if cached_value is None:
                # Cache miss - try to fetch
                if refresh_func:
                    return await self._fetch_and_cache(key, refresh_func, namespace)
                return None
            
            # Get or create SWR entry
            swr_entry = self._get_swr_entry(swr_key, cached_value, current_time)
            
            if swr_entry.refresh_state == SWRState.FRESH:
                self._stats['fresh_hits'] += 1
                self.logger.debug(f"Fresh hit for key: {swr_key}")
                return swr_entry.value
            
            elif swr_entry.refresh_state == SWRState.STALE:
                self._stats['stale_hits'] += 1
                self.logger.debug(f"Stale hit for key: {swr_key}")
                
                # Trigger background refresh
                if (self.config.enable_background_refresh and 
                    refresh_func and 
                    swr_entry.refresh_state != SWRState.REFRESHING):
                    await self._trigger_background_refresh(key, refresh_func, namespace, swr_entry)
                
                return swr_entry.value
            
            elif swr_entry.refresh_state == SWRState.ERROR:
                self.logger.warning(f"Error state for key: {swr_key}, error: {swr_entry.refresh_error}")
                
                # Try to refresh if error state and refresh function available
                if (self.config.enable_background_refresh and 
                    refresh_func and 
                    swr_entry.refresh_state != SWRState.REFRESHING):
                    await self._trigger_background_refresh(key, refresh_func, namespace, swr_entry)
                
                return swr_entry.value if swr_entry.value is not None else None
            
            else:
                # REFRESHING state - return stale data if available
                self.logger.debug(f"Refreshing state for key: {swr_key}")
                return swr_entry.value if swr_entry.value is not None else None
            
        except Exception as e:
            self.logger.error(f"Error getting SWR value: {e}")
            return None
    
    def _get_swr_entry(self, swr_key: str, cached_value: Any, current_time: float) -> SWREntry:
        """Get or create SWR entry from cached value"""
        if swr_key in self._swr_state:
            return self._swr_state[swr_key]
        
        # Create new SWR entry
        ttl = self.config.fresh_ttl + self.config.stale_ttl
        stale_at = current_time + self.config.fresh_ttl
        
        swr_entry = SWREntry(
            value=cached_value,
            timestamp=current_time,
            ttl=ttl,
            stale_at=stale_at,
            refresh_state=SWRState.FRESH,
            last_refresh_attempt=0,
            refresh_count=0
        )
        
        self._swr_state[swr_key] = swr_entry
        return swr_entry
    
    async def _fetch_and_cache(
        self,
        key: str,
        refresh_func: Callable[[], Awaitable[Any]],
        namespace: str
    ) -> Any:
        """Fetch data using refresh function and cache it"""
        try:
            self.logger.debug(f"Fetching fresh data for key: {key}")
            
            # Execute refresh function
            fresh_value = await refresh_func()
            
            # Cache the fresh value
            await self.set(key, fresh_value, namespace)
            
            return fresh_value
            
        except Exception as e:
            self.logger.error(f"Error fetching fresh data: {e}")
            raise TransientAdapterError(
                message=f"SWR refresh failed: {str(e)}",
                adapter_name="SWREngine"
            ) from e
    
    async def set(
        self,
        key: str,
        value: Any,
        namespace: str = "default"
    ) -> bool:
        """
        Set value in cache with SWR state.
        
        Args:
            key: Cache key
            value: Value to cache
            namespace: Cache namespace
            
        Returns:
            True if successful, False otherwise
        """
        try:
            swr_key = self._generate_swr_key(key, namespace)
            current_time = time.time()
            
            # Cache in underlying cache manager
            success = await self.cache_manager.set(
                key=key,
                value=value,
                ttl=self.config.fresh_ttl + self.config.stale_ttl,
                namespace=namespace
            )
            
            if success:
                # Update SWR state
                ttl = self.config.fresh_ttl + self.config.stale_ttl
                stale_at = current_time + self.config.fresh_ttl
                
                swr_entry = SWREntry(
                    value=value,
                    timestamp=current_time,
                    ttl=ttl,
                    stale_at=stale_at,
                    refresh_state=SWRState.FRESH,
                    last_refresh_attempt=0,
                    refresh_count=0
                )
                
                self._swr_state[swr_key] = swr_entry
                self.logger.debug(f"Set SWR entry: {swr_key}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error setting SWR value: {e}")
            return False
    
    async def _trigger_background_refresh(
        self,
        key: str,
        refresh_func: Callable[[], Awaitable[Any]],
        namespace: str,
        current_entry: SWREntry
    ):
        """Trigger background refresh for stale data"""
        swr_key = self._generate_swr_key(key, namespace)
        
        try:
            # Check if refresh already in progress
            if swr_key in self._refresh_tasks:
                task = self._refresh_tasks[swr_key]
                if not task.done():
                    self.logger.debug(f"Background refresh already in progress: {swr_key}")
                    return
            
            # Get or create refresh lock
            if swr_key not in self._refresh_locks:
                self._refresh_locks[swr_key] = asyncio.Lock()
            
            lock = self._refresh_locks[swr_key]
            
            # Check rate limiting
            time_since_last_attempt = current_time - current_entry.last_refresh_attempt
            if time_since_last_attempt < self.config.refresh_backoff:
                self.logger.debug(f"Refresh rate limited for key: {swr_key}")
                return
            
            async with lock:
                # Double-check after acquiring lock
                if (swr_key in self._refresh_tasks and 
                    not self._refresh_tasks[swr_key].done()):
                    return
                
                # Update entry state to REFRESHING
                current_entry.refresh_state = SWRState.REFRESHING
                current_entry.last_refresh_attempt = time.time()
                self._swr_state[swr_key] = current_entry
                
                # Create background refresh task
                task = asyncio.create_task(
                    self._background_refresh(key, refresh_func, namespace, current_entry)
                )
                self._refresh_tasks[swr_key] = task
                
                self.logger.debug(f"Triggered background refresh for: {swr_key}")
                self._stats['background_refreshes'] += 1
                
        except Exception as e:
            self.logger.error(f"Error triggering background refresh: {e}")
    
    async def _background_refresh(
        self,
        key: str,
        refresh_func: Callable[[], Awaitable[Any]],
        namespace: str,
        current_entry: SWREntry
    ):
        """Background refresh task"""
        swr_key = self._generate_swr_key(key, namespace)
        
        try:
            self.logger.debug(f"Starting background refresh for: {swr_key}")
            
            # Execute refresh with timeout
            fresh_value = await asyncio.wait_for(
                refresh_func(),
                timeout=self.config.refresh_timeout
            )
            
            # Update cache and SWR state
            await self.set(key, fresh_value, namespace)
            
            # Update entry state
            updated_entry = self._swr_state[swr_key]
            updated_entry.refresh_state = SWRState.FRESH
            updated_entry.refresh_error = None
            updated_entry.refresh_count += 1
            updated_entry.last_refresh_attempt = time.time()
            
            self.logger.debug(f"Completed background refresh for: {swr_key}")
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Background refresh timeout for: {swr_key}")
            
            # Update entry state to ERROR
            current_entry.refresh_state = SWRState.ERROR
            current_entry.refresh_error = "timeout"
            current_entry.last_refresh_attempt = time.time()
            self._stats['refresh_errors'] += 1
            
        except Exception as e:
            self.logger.error(f"Background refresh error for: {swr_key}: {e}")
            
            # Update entry state to ERROR
            current_entry.refresh_state = SWRState.ERROR
            current_entry.refresh_error = str(e)
            current_entry.last_refresh_attempt = time.time()
            self._stats['refresh_errors'] += 1
        
        finally:
            # Clean up task
            if swr_key in self._refresh_tasks:
                del self._refresh_tasks[swr_key]
    
    async def invalidate(self, key: str, namespace: str = "default"):
        """Invalidate SWR entry"""
        swr_key = self._generate_swr_key(key, namespace)
        
        try:
            # Invalidate from cache manager
            await self.cache_manager.invalidate(key, namespace)
            
            # Remove SWR state
            if swr_key in self._swr_state:
                del self._swr_state[swr_key]
            
            # Cancel background refresh if in progress
            if swr_key in self._refresh_tasks:
                task = self._refresh_tasks[swr_key]
                if not task.done():
                    task.cancel()
                del self._refresh_tasks[swr_key]
            
            self.logger.debug(f"Invalidated SWR entry: {swr_key}")
            
        except Exception as e:
            self.logger.error(f"Error invalidating SWR entry: {e}")
    
    async def clear_namespace(self, namespace: str = "default"):
        """Clear all SWR entries in namespace"""
        try:
            # Clear from cache manager
            await self.cache_manager.clear_namespace(namespace)
            
            # Clear SWR state
            keys_to_remove = [
                key for key in self._swr_state.keys()
                if key.startswith(f"swr:{namespace}:")
            ]
            
            for key in keys_to_remove:
                # Cancel background tasks
                if key in self._refresh_tasks:
                    task = self._refresh_tasks[key]
                    if not task.done():
                        task.cancel()
                    del self._refresh_tasks[key]
                
                del self._swr_state[key]
            
            self.logger.info(f"Cleared SWR namespace: {namespace}")
            
        except Exception as e:
            self.logger.error(f"Error clearing SWR namespace: {e}")
    
    async def clear_all(self):
        """Clear all SWR entries"""
        try:
            # Clear from cache manager
            await self.cache_manager.clear_all()
            
            # Cancel all background tasks
            for task in self._refresh_tasks.values():
                if not task.done():
                    task.cancel()
            
            self._refresh_tasks.clear()
            self._swr_state.clear()
            
            self.logger.info("Cleared all SWR entries")
            
        except Exception as e:
            self.logger.error(f"Error clearing SWR entries: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get SWR engine statistics"""
        total_hits = self._stats['fresh_hits'] + self._stats['stale_hits']
        total_requests = self._stats['total_requests']
        
        active_refresh_tasks = len([
            task for task in self._refresh_tasks.values()
            if not task.done()
        ])
        
        return {
            'swr_stats': {
                'fresh_hits': self._stats['fresh_hits'],
                'stale_hits': self._stats['stale_hits'],
                'background_refreshes': self._stats['background_refreshes'],
                'refresh_errors': self._stats['refresh_errors'],
                'active_refresh_tasks': active_refresh_tasks
            },
            'performance_stats': {
                'total_hits': total_hits,
                'total_requests': total_requests,
                'hit_rate': total_hits / total_requests if total_requests > 0 else 0,
                'fresh_hit_rate': self._stats['fresh_hits'] / total_requests if total_requests > 0 else 0,
                'stale_hit_rate': self._stats['stale_hits'] / total_requests if total_requests > 0 else 0
            },
            'state_stats': {
                'swr_entries': len(self._swr_state),
                'refresh_locks': len(self._refresh_locks),
                'refresh_tasks': len(self._refresh_tasks)
            },
            'config': {
                'fresh_ttl': self.config.fresh_ttl,
                'stale_ttl': self.config.stale_ttl,
                'max_refresh_attempts': self.config.max_refresh_attempts,
                'refresh_backoff': self.config.refresh_backoff,
                'enable_background_refresh': self.config.enable_background_refresh,
                'refresh_timeout': self.config.refresh_timeout,
                'error_retry_delay': self.config.error_retry_delay
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on SWR engine"""
        try:
            # Test SWR functionality
            test_key = "swr_health_check"
            test_value = {"test": True, "timestamp": time.time()}
            
            async def test_refresh():
                await asyncio.sleep(0.1)  # Simulate work
                return {"test": True, "refreshed": True, "timestamp": time.time()}
            
            # Set initial value
            await self.set(test_key, test_value)
            
            # Wait for it to become stale
            await asyncio.sleep(0.1)
            
            # Get stale value and trigger refresh
            retrieved_value = await self.get(test_key, test_refresh)
            
            # Wait for background refresh
            await asyncio.sleep(0.2)
            
            # Check final state
            final_value = await self.get(test_key)
            
            healthy = (
                retrieved_value is not None and
                final_value is not None and
                final_value.get("refreshed", False)
            )
            
            return {
                'healthy': healthy,
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


# Decorator for SWR functionality
def swr_cached(
    swr_engine: SWREngine,
    namespace: str = "default",
    ttl: Optional[int] = None
):
    """
    Decorator for adding SWR caching to functions.
    
    Args:
        swr_engine: SWR engine instance
        namespace: Cache namespace
        ttl: Custom TTL (overrides engine config)
        
    Returns:
        Decorated function with SWR caching
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key = f"{func.__name__}:{hashlib.md5(str(args).encode()).hexdigest()[:8]}"
            
            # Create refresh function
            async def refresh_func():
                return await func(*args, **kwargs)
            
            # Get from SWR engine
            return await swr_engine.get(key, refresh_func, namespace)
        
        return wrapper
