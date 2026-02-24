"""
Lock Manager - High-level Distributed Lock Management

This module provides a high-level interface for managing distributed locks
with cache stampede protection and stale data fallback mechanisms.
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any, Callable, Union
from contextlib import asynccontextmanager
from functools import wraps

from .redlock import RedLock, DistributedLock, LockInfo
from .exceptions import (
    LockError,
    LockAcquisitionError,
    LockTimeoutError,
    LockExpiredError
)


class LockManager:
    """
    High-level lock manager with cache stampede protection.
    
    This class provides a comprehensive locking system that prevents cache stampede
    by allowing only one process to refresh data while others wait or receive stale data.
    """
    
    def __init__(
        self,
        redis_nodes: list = None,
        default_ttl: int = 30000,  # 30 seconds
        default_timeout: float = 5.0,  # 5 seconds
        retry_delay: float = 0.1,
        max_retries: int = 3,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize lock manager.
        
        Args:
            redis_nodes: List of Redis connection strings
            default_ttl: Default TTL for locks in milliseconds
            default_timeout: Default timeout for lock acquisition
            retry_delay: Delay between retries
            max_retries: Maximum retry attempts
            logger: Logger instance
        """
        self.default_ttl = default_ttl
        self.default_timeout = default_timeout
        self.logger = logger or logging.getLogger("LockManager")
        
        # Initialize Redlock
        redis_nodes = redis_nodes or ["redis://localhost:6379"]
        self.redlock = RedLock(
            redis_nodes=redis_nodes,
            ttl=default_ttl,
            retry_delay=retry_delay,
            max_retries=max_retries,
            logger=self.logger
        )
        
        # Cache for stale data
        self._stale_data_cache: Dict[str, Any] = {}
        
        self.logger.info("LockManager initialized")
    
    @asynccontextmanager
    async def get_lock(
        self,
        lock_name: str,
        timeout: Optional[float] = None,
        ttl: Optional[int] = None,
        return_stale: bool = True,
        stale_ttl: int = 60  # 1 minute
    ):
        """
        Get a distributed lock with cache stampede protection.
        
        Args:
            lock_name: Name of the lock
            timeout: Maximum time to wait for lock acquisition
            ttl: Lock TTL in milliseconds
            return_stale: Whether to return stale data if lock can't be acquired
            stale_ttl: TTL for stale data in seconds
            
        Yields:
            LockWrapper with lock information and stale data access
        """
        timeout = timeout or self.default_ttl / 1000.0
        ttl = ttl or self.default_ttl
        
        lock_info = None
        start_time = time.time()
        
        try:
            # Try to acquire the lock
            lock_info = await self.redlock.acquire(lock_name, timeout)
            
            if lock_info:
                # Lock acquired successfully
                self.logger.debug(f"Lock '{lock_name}' acquired")
                yield LockWrapper(lock_info, None, self)
            else:
                # Lock not acquired, check if we should return stale data
                if return_stale:
                    stale_data = self._get_stale_data(lock_name, stale_ttl)
                    if stale_data is not None:
                        self.logger.debug(f"Returning stale data for '{lock_name}'")
                        yield LockWrapper(None, stale_data, self)
                        return
                
                # No stale data or not allowed to return it
                raise LockTimeoutError(lock_name, timeout)
                
        except Exception as e:
            self.logger.error(f"Error in get_lock for '{lock_name}': {e}")
            raise
        finally:
            if lock_info:
                try:
                    await self.redlock.release(lock_info)
                    self.logger.debug(f"Lock '{lock_name}' released")
                except Exception as e:
                    self.logger.error(f"Error releasing lock '{lock_name}': {e}")
    
    async def execute_with_lock(
        self,
        lock_name: str,
        func: Callable,
        *args,
        timeout: Optional[float] = None,
        ttl: Optional[int] = None,
        return_stale: bool = True,
        stale_ttl: int = 60,
        cache_stale_result: bool = True,
        **kwargs
    ) -> Any:
        """
        Execute a function with distributed lock protection.
        
        Args:
            lock_name: Name of the lock
            func: Function to execute
            *args: Function arguments
            timeout: Lock acquisition timeout
            ttl: Lock TTL
            return_stale: Whether to return stale data on lock failure
            stale_ttl: TTL for stale data
            cache_stale_result: Whether to cache the result as stale data
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or stale data
        """
        async with self.get_lock(
            lock_name, timeout, ttl, return_stale, stale_ttl
        ) as lock_wrapper:
            if lock_wrapper.has_lock():
                # We have the lock, execute the function
                self.logger.debug(f"Executing function with lock '{lock_name}'")
                
                try:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)
                    
                    # Cache the result as stale data for future use
                    if cache_stale_result:
                        self._set_stale_data(lock_name, result)
                    
                    return result
                    
                except Exception as e:
                    self.logger.error(f"Error executing function with lock '{lock_name}': {e}")
                    raise
            else:
                # No lock, return stale data
                self.logger.debug(f"Returning stale data for '{lock_name}'")
                return lock_wrapper.get_stale_data()
    
    def _get_stale_data(self, lock_name: str, max_age: int) -> Any:
        """
        Get stale data if available and not too old.
        
        Args:
            lock_name: Lock name
            max_age: Maximum age in seconds
            
        Returns:
            Stale data or None
        """
        if lock_name in self._stale_data_cache:
            data, timestamp = self._stale_data_cache[lock_name]
            if time.time() - timestamp < max_age:
                return data
            else:
                # Remove expired stale data
                del self._stale_data_cache[lock_name]
        
        return None
    
    def _set_stale_data(self, lock_name: str, data: Any):
        """
        Set stale data for future use.
        
        Args:
            lock_name: Lock name
            data: Data to cache
        """
        self._stale_data_cache[lock_name] = (data, time.time())
        
        # Limit cache size
        if len(self._stale_data_cache) > 1000:
            # Remove oldest entry
            oldest_key = min(
                self._stale_data_cache.keys(),
                key=lambda k: self._stale_data_cache[k][1]
            )
            del self._stale_data_cache[oldest_key]
    
    async def protect_cache_stampede(
        self,
        cache_key: str,
        data_fetcher: Callable,
        *args,
        timeout: Optional[float] = None,
        ttl: Optional[int] = None,
        return_stale: bool = True,
        **kwargs
    ) -> Any:
        """
        Protect against cache stampede for data fetching.
        
        Args:
            cache_key: Cache key to protect
            data_fetcher: Function to fetch fresh data
            *args: Function arguments
            timeout: Lock timeout
            ttl: Lock TTL
            return_stale: Whether to return stale data
            **kwargs: Function keyword arguments
            
        Returns:
            Fresh data or stale data
        """
        lock_name = f"cache_stampede:{cache_key}"
        
        return await self.execute_with_lock(
            lock_name=lock_name,
            func=data_fetcher,
            *args,
            timeout=timeout,
            ttl=ttl,
            return_stale=return_stale,
            cache_stale_result=True,
            **kwargs
        )
    
    async def refresh_with_lock(
        self,
        key: str,
        refresh_func: Callable,
        *args,
        timeout: Optional[float] = None,
        ttl: Optional[int] = None,
        **kwargs
    ) -> Any:
        """
        Refresh data with lock protection (for SWR integration).
        
        Args:
            key: Data key to refresh
            refresh_func: Function to refresh data
            *args: Function arguments
            timeout: Lock timeout
            ttl: Lock TTL
            **kwargs: Function keyword arguments
            
        Returns:
            Refreshed data
        """
        lock_name = f"refresh:{key}"
        
        async with self.get_lock(lock_name, timeout, ttl, return_stale=False) as lock_wrapper:
            if lock_wrapper.has_lock():
                self.logger.debug(f"Refreshing data for key '{key}'")
                
                if asyncio.iscoroutinefunction(refresh_func):
                    result = await refresh_func(*args, **kwargs)
                else:
                    result = refresh_func(*args, **kwargs)
                
                # Update stale data cache
                self._set_stale_data(key, result)
                
                return result
            else:
                raise LockAcquisitionError(lock_name, "Failed to acquire refresh lock")
    
    def create_lock(self, lock_name: str, **kwargs) -> DistributedLock:
        """
        Create a distributed lock instance.
        
        Args:
            lock_name: Name of the lock
            **kwargs: Additional lock options
            
        Returns:
            DistributedLock instance
        """
        return DistributedLock(self.redlock, lock_name, **kwargs)
    
    async def is_locked(self, lock_name: str) -> bool:
        """
        Check if a lock is currently held.
        
        Args:
            lock_name: Name of the lock
            
        Returns:
            True if locked, False otherwise
        """
        owner = await self.redlock.is_locked(lock_name)
        return owner is not None
    
    async def get_lock_info(self, lock_name: str) -> Optional[str]:
        """
        Get information about a lock.
        
        Args:
            lock_name: Name of the lock
            
        Returns:
            Lock owner or None if not locked
        """
        return await self.redlock.is_locked(lock_name)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get lock manager statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            'stale_data_cache_size': len(self._stale_data_cache),
            'default_ttl': self.default_ttl,
            'default_timeout': self.default_timeout,
            'redis_nodes': len(self.redlock.redis_clients),
            'quorum': self.redlock.quorum
        }
    
    async def clear_stale_cache(self):
        """Clear the stale data cache."""
        self._stale_data_cache.clear()
        self.logger.info("Stale data cache cleared")
    
    async def close(self):
        """Close the lock manager and Redis connections."""
        await self.redlock.close()
        self.logger.info("LockManager closed")


class LockWrapper:
    """
    Wrapper for lock operations with stale data access.
    """
    
    def __init__(self, lock_info: Optional[LockInfo], stale_data: Any, manager: LockManager):
        self.lock_info = lock_info
        self.stale_data = stale_data
        self.manager = manager
    
    def has_lock(self) -> bool:
        """Check if this wrapper has an active lock."""
        return self.lock_info is not None
    
    def is_stale(self) -> bool:
        """Check if this wrapper contains stale data."""
        return self.stale_data is not None
    
    def get_stale_data(self) -> Any:
        """Get the stale data."""
        return self.stale_data
    
    def get_lock_info(self) -> Optional[LockInfo]:
        """Get the lock information."""
        return self.lock_info
    
    async def extend_lock(self, additional_ttl: int) -> Optional[LockInfo]:
        """
        Extend the lock TTL.
        
        Args:
            additional_ttl: Additional TTL in milliseconds
            
        Returns:
            Updated lock info or None if no lock
        """
        if self.lock_info:
            self.lock_info = await self.manager.redlock.extend(self.lock_info, additional_ttl)
            return self.lock_info
        return None


# Global lock manager instance
_global_manager: Optional[LockManager] = None


def get_global_manager(**kwargs) -> LockManager:
    """Get or create the global lock manager."""
    global _global_manager
    if _global_manager is None:
        _global_manager = LockManager(**kwargs)
    return _global_manager


def get_lock(lock_name: str, **kwargs):
    """
    Get a distributed lock using the global manager.
    
    Args:
        lock_name: Name of the lock
        **kwargs: Additional lock options
        
    Returns:
        Context manager for the lock
    """
    manager = get_global_manager()
    return manager.get_lock(lock_name, **kwargs)


def distributed_lock(lock_name: str, **kwargs):
    """
    Decorator for distributed lock protection.
    
    Args:
        lock_name: Name of the lock (can use function arguments)
        **kwargs: Additional lock options
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs_inner):
            manager = get_global_manager()
            
            # Format lock name with function arguments if needed
            if '{' in lock_name:
                try:
                    formatted_name = lock_name.format(*args, **kwargs_inner)
                except (KeyError, IndexError):
                    formatted_name = f"{func.__name__}_{hash(str(args) + str(kwargs_inner))}"
            else:
                formatted_name = lock_name
            
            return await manager.execute_with_lock(
                lock_name=formatted_name,
                func=func,
                *args,
                **kwargs_inner,
                **kwargs
            )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs_inner):
            # For synchronous functions, we need to run in async context
            import asyncio
            
            async def async_execute():
                manager = get_global_manager()
                
                # Format lock name with function arguments if needed
                if '{' in lock_name:
                    try:
                        formatted_name = lock_name.format(*args, **kwargs_inner)
                    except (KeyError, IndexError):
                        formatted_name = f"{func.__name__}_{hash(str(args) + str(kwargs_inner))}"
                else:
                    formatted_name = lock_name
                
                return await manager.execute_with_lock(
                    lock_name=formatted_name,
                    func=func,
                    *args,
                    **kwargs_inner,
                    **kwargs
                )
            
            return asyncio.run(async_execute())
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def cache_stampede_protect(cache_key_template: str, **kwargs):
    """
    Decorator for cache stampede protection.
    
    Args:
        cache_key_template: Template for cache key
        **kwargs: Additional lock options
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs_inner):
            manager = get_global_manager()
            
            # Format cache key
            try:
                cache_key = cache_key_template.format(*args, **kwargs_inner)
            except (KeyError, IndexError):
                cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs_inner))}"
            
            return await manager.protect_cache_stampede(
                cache_key=cache_key,
                data_fetcher=func,
                *args,
                **kwargs_inner,
                **kwargs
            )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs_inner):
            import asyncio
            
            async def async_execute():
                manager = get_global_manager()
                
                # Format cache key
                try:
                    cache_key = cache_key_template.format(*args, **kwargs_inner)
                except (KeyError, IndexError):
                    cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs_inner))}"
                
                return await manager.protect_cache_stampede(
                    cache_key=cache_key,
                    data_fetcher=func,
                    *args,
                    **kwargs_inner,
                    **kwargs
                )
            
            return asyncio.run(async_execute())
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
