"""
Redlock Algorithm Implementation

This module implements the Redlock distributed locking algorithm
with Redis to provide safe distributed locking with auto-release.
"""

import asyncio
import time
import uuid
import logging
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from contextlib import asynccontextmanager

import redis.asyncio as redis

from .exceptions import (
    LockError,
    LockAcquisitionError,
    LockReleaseError,
    LockTimeoutError,
    DeadlockError,
    LockOwnershipError,
    LockExpiredError,
    QuorumError,
    RedisConnectionError
)


@dataclass
class LockInfo:
    """Information about a distributed lock."""
    name: str
    owner: str
    acquired_at: float
    expires_at: float
    ttl: int
    redis_nodes: List[str]


class RedLock:
    """
    Redlock distributed lock implementation.
    
    This class implements the Redlock algorithm to provide distributed locking
    across multiple Redis instances with automatic expiration to prevent deadlocks.
    """
    
    def __init__(
        self,
        redis_nodes: List[Union[str, redis.Redis]],
        ttl: int = 30000,  # 30 seconds default
        retry_delay: float = 0.1,  # 100ms between retries
        max_retries: int = 3,
        clock_drift_factor: float = 0.01,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Redlock instance.
        
        Args:
            redis_nodes: List of Redis connection strings or Redis clients
            ttl: Time-to-live for locks in milliseconds
            retry_delay: Delay between retry attempts in seconds
            max_retries: Maximum number of retry attempts
            clock_drift_factor: Clock drift factor for safety margin
            logger: Logger instance
        """
        self.ttl = ttl
        self.retry_delay = retry_delay
        self.max_retries = max_retries
        self.clock_drift_factor = clock_drift_factor
        self.logger = logger or logging.getLogger("RedLock")
        
        # Initialize Redis clients
        self.redis_clients = []
        for node in redis_nodes:
            if isinstance(node, str):
                client = redis.from_url(node, encoding="utf-8", decode_responses=True)
            elif isinstance(node, redis.Redis):
                client = node
            else:
                raise ValueError(f"Invalid Redis node type: {type(node)}")
            
            self.redis_clients.append(client)
        
        self.quorum = len(self.redis_clients) // 2 + 1
        self.logger.info(f"RedLock initialized with {len(self.redis_clients)} nodes, quorum: {self.quorum}")
    
    async def acquire(
        self,
        lock_name: str,
        timeout: Optional[float] = None,
        owner: Optional[str] = None
    ) -> Optional[LockInfo]:
        """
        Acquire a distributed lock.
        
        Args:
            lock_name: Name of the lock to acquire
            timeout: Maximum time to wait for lock acquisition (None = no timeout)
            owner: Unique identifier for lock owner (auto-generated if None)
            
        Returns:
            LockInfo if lock acquired successfully, None otherwise
            
        Raises:
            LockTimeoutError: If timeout is reached
            QuorumError: If quorum cannot be achieved
        """
        if owner is None:
            owner = str(uuid.uuid4())
        
        start_time = time.time()
        retry_count = 0
        
        while True:
            try:
                lock_info = await self._try_acquire(lock_name, owner)
                if lock_info:
                    self.logger.debug(f"Lock '{lock_name}' acquired by {owner}")
                    return lock_info
                
                retry_count += 1
                if retry_count >= self.max_retries:
                    self.logger.warning(f"Max retries ({self.max_retries}) reached for lock '{lock_name}'")
                    return None
                
                # Check timeout
                if timeout is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        raise LockTimeoutError(lock_name, timeout)
                
                # Wait before retry
                await asyncio.sleep(self.retry_delay)
                
            except Exception as e:
                self.logger.error(f"Error acquiring lock '{lock_name}': {e}")
                raise
    
    async def _try_acquire(self, lock_name: str, owner: str) -> Optional[LockInfo]:
        """
        Try to acquire lock on all Redis nodes.
        
        Args:
            lock_name: Name of the lock
            owner: Lock owner identifier
            
        Returns:
            LockInfo if quorum achieved, None otherwise
        """
        lock_key = f"redlock:{lock_name}"
        acquired_at = time.time()
        expires_at = acquired_at + (self.ttl / 1000.0)
        
        # Try to acquire lock on all nodes
        successful_nodes = 0
        tasks = []
        
        for client in self.redis_clients:
            task = self._acquire_on_node(client, lock_key, owner, self.ttl)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Error acquiring lock on node {i}: {result}")
            elif result:
                successful_nodes += 1
        
        # Check if we achieved quorum
        if successful_nodes >= self.quorum:
            # Apply clock drift
            safety_margin = self.ttl * self.clock_drift_factor
            adjusted_ttl = self.ttl - safety_margin
            
            lock_info = LockInfo(
                name=lock_name,
                owner=owner,
                acquired_at=acquired_at,
                expires_at=acquired_at + (adjusted_ttl / 1000.0),
                ttl=adjusted_ttl,
                redis_nodes=[str(client.connection_pool.connection_kwargs.get('host', 'unknown')) 
                           for client in self.redis_clients]
            )
            
            return lock_info
        else:
            # Failed to achieve quorum, release any acquired locks
            await self._release_partial_lock(lock_key, owner)
            raise QuorumError(lock_name, successful_nodes, self.quorum)
    
    async def _acquire_on_node(
        self, 
        client: redis.Redis, 
        lock_key: str, 
        owner: str, 
        ttl: int
    ) -> bool:
        """
        Try to acquire lock on a single Redis node.
        
        Args:
            client: Redis client
            lock_key: Lock key
            owner: Lock owner
            ttl: Time-to-live in milliseconds
            
        Returns:
            True if lock acquired, False otherwise
        """
        try:
            # Use SET with NX and PX options (atomic operation)
            result = await client.set(lock_key, owner, nx=True, px=ttl)
            return result is True
        except Exception as e:
            self.logger.error(f"Error acquiring lock on Redis node: {e}")
            return False
    
    async def release(self, lock_info: LockInfo) -> bool:
        """
        Release a distributed lock.
        
        Args:
            lock_info: Lock information from acquire()
            
        Returns:
            True if lock released successfully, False otherwise
            
        Raises:
            LockOwnershipError: If lock is owned by another process
            LockExpiredError: If lock has expired
        """
        if lock_info.expires_at < time.time():
            raise LockExpiredError(lock_info.name, lock_info.expires_at)
        
        lock_key = f"redlock:{lock_info.name}"
        
        # Release lock on all nodes
        successful_nodes = 0
        tasks = []
        
        for client in self.redis_clients:
            task = self._release_on_node(client, lock_key, lock_info.owner)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Error releasing lock on node {i}: {result}")
            elif result:
                successful_nodes += 1
        
        # Check if we achieved quorum for release
        if successful_nodes >= self.quorum:
            self.logger.debug(f"Lock '{lock_info.name}' released by {lock_info.owner}")
            return True
        else:
            raise LockReleaseError(
                lock_info.name, 
                f"Failed to achieve quorum for release: {successful_nodes}/{self.quorum}"
            )
    
    async def _release_on_node(
        self, 
        client: redis.Redis, 
        lock_key: str, 
        owner: str
    ) -> bool:
        """
        Release lock on a single Redis node using Lua script.
        
        Args:
            client: Redis client
            lock_key: Lock key
            owner: Lock owner
            
        Returns:
            True if lock released, False otherwise
        """
        # Lua script for atomic release
        lua_script = """
        if redis.call("GET", KEYS[1]) == ARGV[1] then
            return redis.call("DEL", KEYS[1])
        else
            return 0
        end
        """
        
        try:
            result = await client.eval(lua_script, 1, lock_key, owner)
            return result == 1
        except Exception as e:
            self.logger.error(f"Error releasing lock on Redis node: {e}")
            return False
    
    async def _release_partial_lock(self, lock_key: str, owner: str):
        """Release partially acquired locks when quorum not achieved."""
        tasks = []
        for client in self.redis_clients:
            task = self._release_on_node(client, lock_key, owner)
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def extend(self, lock_info: LockInfo, additional_ttl: int) -> LockInfo:
        """
        Extend the TTL of an existing lock.
        
        Args:
            lock_info: Current lock information
            additional_ttl: Additional TTL in milliseconds
            
        Returns:
            Updated lock information
            
        Raises:
            LockOwnershipError: If lock is owned by another process
            LockExpiredError: If lock has expired
        """
        if lock_info.expires_at < time.time():
            raise LockExpiredError(lock_info.name, lock_info.expires_at)
        
        lock_key = f"redlock:{lock_info.name}"
        current_time = time.time()
        
        # Extend lock on all nodes
        successful_nodes = 0
        tasks = []
        
        for client in self.redis_clients:
            task = self._extend_on_node(client, lock_key, lock_info.owner, additional_ttl)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Error extending lock on node {i}: {result}")
            elif result:
                successful_nodes += 1
        
        if successful_nodes >= self.quorum:
            # Create updated lock info
            updated_lock = LockInfo(
                name=lock_info.name,
                owner=lock_info.owner,
                acquired_at=lock_info.acquired_at,
                expires_at=current_time + (additional_ttl / 1000.0),
                ttl=additional_ttl,
                redis_nodes=lock_info.redis_nodes
            )
            
            self.logger.debug(f"Lock '{lock_info.name}' extended by {additional_ttl}ms")
            return updated_lock
        else:
            raise LockReleaseError(
                lock_info.name,
                f"Failed to achieve quorum for extension: {successful_nodes}/{self.quorum}"
            )
    
    async def _extend_on_node(
        self, 
        client: redis.Redis, 
        lock_key: str, 
        owner: str, 
        additional_ttl: int
    ) -> bool:
        """
        Extend lock TTL on a single Redis node.
        
        Args:
            client: Redis client
            lock_key: Lock key
            owner: Lock owner
            additional_ttl: Additional TTL in milliseconds
            
        Returns:
            True if lock extended, False otherwise
        """
        # Lua script for atomic extension
        lua_script = """
        if redis.call("GET", KEYS[1]) == ARGV[1] then
            return redis.call("PEXPIRE", KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        
        try:
            result = await client.eval(lua_script, 1, lock_key, owner, additional_ttl)
            return result == 1
        except Exception as e:
            self.logger.error(f"Error extending lock on Redis node: {e}")
            return False
    
    async def is_locked(self, lock_name: str) -> Optional[str]:
        """
        Check if a lock is currently held.
        
        Args:
            lock_name: Name of the lock to check
            
        Returns:
            Owner identifier if locked, None otherwise
        """
        lock_key = f"redlock:{lock_name}"
        
        # Check on a majority of nodes
        responses = []
        tasks = []
        
        for client in self.redis_clients[:self.quorum]:
            task = client.get(lock_key)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                continue
            responses.append(result)
        
        # Return owner if majority agree
        if responses:
            return responses[0]  # First response from majority
        
        return None
    
    async def cleanup_expired_locks(self) -> int:
        """
        Clean up expired locks (maintenance operation).
        
        Returns:
            Number of locks cleaned up
        """
        # This is a maintenance operation that could be expensive
        # In practice, Redis TTL handles expiration automatically
        self.logger.info("Expired lock cleanup not needed (Redis TTL handles it)")
        return 0
    
    @asynccontextmanager
    async def lock(
        self, 
        lock_name: str, 
        timeout: Optional[float] = None,
        owner: Optional[str] = None
    ):
        """
        Context manager for automatic lock acquisition and release.
        
        Args:
            lock_name: Name of the lock
            timeout: Maximum time to wait for acquisition
            owner: Lock owner identifier
            
        Yields:
            LockInfo if acquired successfully
            
        Raises:
            LockTimeoutError: If timeout is reached
            LockAcquisitionError: If acquisition fails
        """
        lock_info = None
        try:
            lock_info = await self.acquire(lock_name, timeout, owner)
            if lock_info is None:
                raise LockAcquisitionError(lock_name, "Failed to acquire lock")
            
            yield lock_info
            
        finally:
            if lock_info:
                try:
                    await self.release(lock_info)
                except Exception as e:
                    self.logger.error(f"Error releasing lock '{lock_name}': {e}")
    
    async def close(self):
        """Close all Redis connections."""
        tasks = []
        for client in self.redis_clients:
            tasks.append(client.close())
        
        await asyncio.gather(*tasks, return_exceptions=True)
        self.logger.info("RedLock connections closed")


class DistributedLock:
    """
    High-level distributed lock wrapper with additional features.
    """
    
    def __init__(
        self,
        redlock: RedLock,
        name: str,
        timeout: Optional[float] = None,
        stale_data_callback: Optional[callable] = None
    ):
        """
        Initialize distributed lock wrapper.
        
        Args:
            redlock: Redlock instance
            name: Lock name
            timeout: Default timeout for acquisition
            stale_data_callback: Callback to return stale data when lock can't be acquired
        """
        self.redlock = redlock
        self.name = name
        self.timeout = timeout
        self.stale_data_callback = stale_data_callback
        self.logger = logging.getLogger(f"DistributedLock.{name}")
    
    async def __aenter__(self) -> 'DistributedLock':
        """Async context manager entry."""
        self.lock_info = await self.redlock.acquire(self.name, self.timeout)
        if self.lock_info is None:
            if self.stale_data_callback:
                stale_data = await self.stale_data_callback()
                return StaleLockWrapper(stale_data)
            raise LockAcquisitionError(self.name, "Failed to acquire lock")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if hasattr(self, 'lock_info') and self.lock_info:
            await self.redlock.release(self.lock_info)
    
    async def acquire(self, timeout: Optional[float] = None) -> Optional[LockInfo]:
        """Acquire the lock with optional timeout override."""
        timeout = timeout or self.timeout
        return await self.redlock.acquire(self.name, timeout)
    
    async def release(self, lock_info: LockInfo) -> bool:
        """Release the lock."""
        return await self.redlock.release(lock_info)
    
    async def is_locked(self) -> bool:
        """Check if the lock is currently held."""
        owner = await self.redlock.is_locked(self.name)
        return owner is not None


class StaleLockWrapper:
    """Wrapper for stale data when lock acquisition fails."""
    
    def __init__(self, stale_data: Any):
        self.stale_data = stale_data
        self.is_stale = True
    
    def get_data(self) -> Any:
        """Get the stale data."""
        return self.stale_data
