"""
Token Bucket Implementation

This module implements the token bucket algorithm for rate limiting
using Redis for distributed token management.
"""

import time
import math
import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from .exceptions import TokenBucketError, RedisConnectionError


class TokenBucket(ABC):
    """Abstract base class for token bucket implementation."""
    
    @abstractmethod
    async def consume(self, tokens: int) -> bool:
        """Consume tokens from the bucket."""
        pass
    
    @abstractmethod
    async def add_tokens(self, tokens: int):
        """Add tokens to the bucket."""
        pass
    
    @abstractmethod
    async def get_available_tokens(self) -> int:
        """Get the number of available tokens."""
        pass
    
    @abstractmethod
    async def get_bucket_info(self) -> Dict[str, Any]:
        """Get bucket information."""
        pass


class RedisTokenBucket(TokenBucket):
    """
    Redis-based token bucket implementation.
    
    This class implements the token bucket algorithm using Redis
    for distributed rate limiting across multiple processes.
    """
    
    def __init__(
        self,
        redis_client,
        bucket_key: str,
        capacity: int,
        refill_rate: float,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Redis token bucket.
        
        Args:
            redis_client: Redis client instance
            bucket_key: Unique key for the bucket
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
            logger: Logger instance
        """
        self.redis = redis_client
        self.bucket_key = bucket_key
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.logger = logger or logging.getLogger("RedisTokenBucket")
        
        # Lua script for atomic token consumption
        self.consume_script = """
        local bucket_key = KEYS[1]
        local tokens_to_consume = tonumber(ARGV[1])
        local capacity = tonumber(ARGV[2])
        local refill_rate = tonumber(ARGV[3])
        local current_time = tonumber(ARGV[4])
        
        -- Get current bucket state
        local bucket_data = redis.call('HMGET', bucket_key, 'tokens', 'last_refill')
        local current_tokens = tonumber(bucket_data[1]) or 0
        local last_refill = tonumber(bucket_data[2]) or 0
        
        -- Calculate tokens to add based on refill rate
        local time_diff = current_time - last_refill
        local tokens_to_add = math.min(time_diff * refill_rate, capacity - current_tokens)
        local new_tokens = math.min(current_tokens + tokens_to_add, capacity)
        
        -- Check if enough tokens available
        if new_tokens >= tokens_to_consume then
            -- Consume tokens
            local remaining_tokens = new_tokens - tokens_to_consume
            
            -- Update bucket state
            redis.call('HMSET', bucket_key, 'tokens', remaining_tokens, 'last_refill', current_time)
            redis.call('EXPIRE', bucket_key, math.ceil(capacity / refill_rate) + 60)
            
            return {1, remaining_tokens, current_time}
        else
            -- Not enough tokens, update last_refill time
            redis.call('HMSET', bucket_key, 'tokens', new_tokens, 'last_refill', current_time)
            redis.call('EXPIRE', bucket_key, math.ceil(capacity / refill_rate) + 60)
            
            return {0, new_tokens, current_time}
        """
        
        self.logger.info(
            f"RedisTokenBucket initialized: key={bucket_key}, "
            f"capacity={capacity}, refill_rate={refill_rate}/s"
        )
    
    async def consume(self, tokens: int) -> bool:
        """
        Consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False otherwise
        """
        try:
            current_time = time.time()
            
            # Execute Lua script atomically
            result = await self.redis.eval(
                self.consume_script,
                1,
                self.bucket_key,
                tokens,
                self.capacity,
                self.refill_rate,
                current_time
            )
            
            success, remaining_tokens, last_refill = result
            
            if success:
                self.logger.debug(
                    f"Consumed {tokens} tokens from {self.bucket_key}, "
                    f"remaining: {remaining_tokens}"
                )
                return True
            else:
                self.logger.debug(
                    f"Failed to consume {tokens} tokens from {self.bucket_key}, "
                    f"available: {remaining_tokens}"
                )
                return False
                
        except Exception as e:
            self.logger.error(f"Error consuming tokens: {e}")
            raise TokenBucketError(f"Failed to consume tokens: {e}", self.bucket_key)
    
    async def add_tokens(self, tokens: int):
        """
        Add tokens to the bucket.
        
        Args:
            tokens: Number of tokens to add
        """
        try:
            current_time = time.time()
            
            # Get current state
            bucket_data = await self.redis.hmget(self.bucket_key, 'tokens', 'last_refill')
            current_tokens = float(bucket_data[0] or 0)
            
            # Add tokens (respecting capacity)
            new_tokens = min(current_tokens + tokens, self.capacity)
            
            # Update bucket
            await self.redis.hmset(
                self.bucket_key,
                {
                    'tokens': str(new_tokens),
                    'last_refill': str(current_time)
                }
            )
            
            # Set expiration
            await self.redis.expire(
                self.bucket_key,
                math.ceil(self.capacity / self.refill_rate) + 60
            )
            
            self.logger.debug(
                f"Added {tokens} tokens to {self.bucket_key}, "
                f"new total: {new_tokens}"
            )
            
        except Exception as e:
            self.logger.error(f"Error adding tokens: {e}")
            raise TokenBucketError(f"Failed to add tokens: {e}", self.bucket_key)
    
    async def get_available_tokens(self) -> int:
        """
        Get the number of available tokens.
        
        Returns:
            Number of available tokens
        """
        try:
            current_time = time.time()
            
            # Get current state
            bucket_data = await self.redis.hmget(self.bucket_key, 'tokens', 'last_refill')
            current_tokens = float(bucket_data[0] or 0)
            last_refill = float(bucket_data[1] or 0)
            
            # Calculate tokens to add based on refill rate
            time_diff = current_time - last_refill
            tokens_to_add = min(time_diff * self.refill_rate, self.capacity - current_tokens)
            new_tokens = min(current_tokens + tokens_to_add, self.capacity)
            
            return int(new_tokens)
            
        except Exception as e:
            self.logger.error(f"Error getting available tokens: {e}")
            raise TokenBucketError(f"Failed to get available tokens: {e}", self.bucket_key)
    
    async def get_bucket_info(self) -> Dict[str, Any]:
        """
        Get comprehensive bucket information.
        
        Returns:
            Bucket information dictionary
        """
        try:
            current_time = time.time()
            
            # Get current state
            bucket_data = await self.redis.hmget(self.bucket_key, 'tokens', 'last_refill')
            current_tokens = float(bucket_data[0] or 0)
            last_refill = float(bucket_data[1] or 0)
            
            # Calculate tokens to add based on refill rate
            time_diff = current_time - last_refill
            tokens_to_add = min(time_diff * self.refill_rate, self.capacity - current_tokens)
            new_tokens = min(current_tokens + tokens_to_add, self.capacity)
            
            # Get TTL
            ttl = await self.redis.ttl(self.bucket_key)
            
            return {
                'bucket_key': self.bucket_key,
                'capacity': self.capacity,
                'refill_rate': self.refill_rate,
                'current_tokens': new_tokens,
                'last_refill': last_refill,
                'time_since_refill': time_diff,
                'tokens_to_add': tokens_to_add,
                'utilization': (self.capacity - new_tokens) / self.capacity,
                'ttl': ttl,
                'time_to_full': max(0, (self.capacity - new_tokens) / self.refill_rate) if self.refill_rate > 0 else float('inf')
            }
            
        except Exception as e:
            self.logger.error(f"Error getting bucket info: {e}")
            raise TokenBucketError(f"Failed to get bucket info: {e}", self.bucket_key)
    
    async def reset(self):
        """Reset the bucket to full capacity."""
        try:
            current_time = time.time()
            
            await self.redis.hmset(
                self.bucket_key,
                {
                    'tokens': str(self.capacity),
                    'last_refill': str(current_time)
                }
            )
            
            # Set expiration
            await self.redis.expire(
                self.bucket_key,
                math.ceil(self.capacity / self.refill_rate) + 60
            )
            
            self.logger.info(f"Reset bucket {self.bucket_key} to full capacity")
            
        except Exception as e:
            self.logger.error(f"Error resetting bucket: {e}")
            raise TokenBucketError(f"Failed to reset bucket: {e}", self.bucket_key)
    
    async def delete(self):
        """Delete the bucket from Redis."""
        try:
            await self.redis.delete(self.bucket_key)
            self.logger.info(f"Deleted bucket {self.bucket_key}")
        except Exception as e:
            self.logger.error(f"Error deleting bucket: {e}")
            raise TokenBucketError(f"Failed to delete bucket: {e}", self.bucket_key)


class InMemoryTokenBucket(TokenBucket):
    """
    In-memory token bucket implementation for testing and single-process use.
    
    This class implements the token bucket algorithm in memory
    for scenarios where Redis is not available.
    """
    
    def __init__(
        self,
        bucket_key: str,
        capacity: int,
        refill_rate: float,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize in-memory token bucket.
        
        Args:
            bucket_key: Unique key for the bucket
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
            logger: Logger instance
        """
        self.bucket_key = bucket_key
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.logger = logger or logging.getLogger("InMemoryTokenBucket")
        
        self._tokens = capacity
        self._last_refill = time.time()
        
        self.logger.info(
            f"InMemoryTokenBucket initialized: key={bucket_key}, "
            f"capacity={capacity}, refill_rate={refill_rate}/s"
        )
    
    def _refill_if_needed(self):
        """Refill tokens based on elapsed time."""
        current_time = time.time()
        time_diff = current_time - self._last_refill
        
        if time_diff > 0:
            tokens_to_add = min(time_diff * self.refill_rate, self.capacity - self._tokens)
            self._tokens = min(self._tokens + tokens_to_add, self.capacity)
            self._last_refill = current_time
    
    async def consume(self, tokens: int) -> bool:
        """Consume tokens from the bucket."""
        self._refill_if_needed()
        
        if self._tokens >= tokens:
            self._tokens -= tokens
            self.logger.debug(
                f"Consumed {tokens} tokens from {self.bucket_key}, "
                f"remaining: {self._tokens}"
            )
            return True
        else:
            self.logger.debug(
                f"Failed to consume {tokens} tokens from {self.bucket_key}, "
                f"available: {self._tokens}"
            )
            return False
    
    async def add_tokens(self, tokens: int):
        """Add tokens to the bucket."""
        self._refill_if_needed()
        self._tokens = min(self._tokens + tokens, self.capacity)
        self.logger.debug(
            f"Added {tokens} tokens to {self.bucket_key}, "
            f"new total: {self._tokens}"
        )
    
    async def get_available_tokens(self) -> int:
        """Get the number of available tokens."""
        self._refill_if_needed()
        return int(self._tokens)
    
    async def get_bucket_info(self) -> Dict[str, Any]:
        """Get comprehensive bucket information."""
        self._refill_if_needed()
        current_time = time.time()
        
        return {
            'bucket_key': self.bucket_key,
            'capacity': self.capacity,
            'refill_rate': self.refill_rate,
            'current_tokens': self._tokens,
            'last_refill': self._last_refill,
            'time_since_refill': current_time - self._last_refill,
            'utilization': (self.capacity - self._tokens) / self.capacity,
            'time_to_full': max(0, (self.capacity - self._tokens) / self.refill_rate) if self.refill_rate > 0 else float('inf')
        }
    
    async def reset(self):
        """Reset the bucket to full capacity."""
        self._tokens = self.capacity
        self._last_refill = time.time()
        self.logger.info(f"Reset bucket {self.bucket_key} to full capacity")
    
    async def delete(self):
        """Delete the bucket (no-op for in-memory)."""
        self.logger.info(f"Deleted bucket {self.bucket_key} (no-op for in-memory)")


# Utility function to create token buckets
def create_token_bucket(
    redis_client,
    bucket_type: str = "redis",
    bucket_key: str,
    capacity: int,
    refill_rate: float,
    logger: Optional[logging.Logger] = None
) -> TokenBucket:
    """
    Create a token bucket of the specified type.
    
    Args:
        redis_client: Redis client instance
        bucket_type: Type of bucket ("redis" or "memory")
        bucket_key: Unique key for the bucket
        capacity: Maximum number of tokens
        refill_rate: Tokens added per second
        logger: Logger instance
        
    Returns:
        TokenBucket instance
    """
    if bucket_type == "redis":
        return RedisTokenBucket(redis_client, bucket_key, capacity, refill_rate, logger)
    elif bucket_type == "memory":
        return InMemoryTokenBucket(bucket_key, capacity, refill_rate, logger)
    else:
        raise ValueError(f"Unknown bucket type: {bucket_type}")


# Import required modules
import math
