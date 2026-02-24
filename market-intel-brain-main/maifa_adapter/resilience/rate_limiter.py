"""
Distributed Rate Limiter Implementation

This module provides a distributed rate limiter using Redis Lua scripts
to guarantee atomicity and prevent request limit violations.
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
import redis.asyncio as redis

from ..core.exceptions import TransientAdapterError


class RateLimitExceededError(TransientAdapterError):
    """Raised when rate limit is exceeded"""
    
    def __init__(
        self,
        adapter_name: str,
        limit: int,
        window: int,
        retry_after: int,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        if message is None:
            message = f"Rate limit exceeded for adapter {adapter_name}: {limit} requests per {window}s"
        
        super().__init__(
            message=message,
            adapter_name=adapter_name,
            retry_after=retry_after,
            context={
                "limit": limit,
                "window": window,
                "retry_after": retry_after,
                **(context or {})
            }
        )


@dataclass
class RateLimitConfig:
    """Configuration for rate limiter"""
    limit: int                    # Maximum requests allowed
    window: int                   # Time window in seconds
    burst_limit: Optional[int] = None  # Burst limit for token bucket
    refill_rate: Optional[float] = None  # Refill rate for token bucket


class DistributedRateLimiter:
    """
    Redis-backed distributed rate limiter using Lua scripts.
    
    Guarantees atomicity across multiple service instances and prevents
    request limit violations with sliding window or token bucket algorithms.
    """
    
    def __init__(
        self,
        adapter_name: str,
        redis_client: redis.Redis,
        config: RateLimitConfig,
        logger: Optional[logging.Logger] = None
    ):
        self.adapter_name = adapter_name
        self.redis = redis_client
        self.config = config
        self.logger = logger or logging.getLogger(f"RateLimiter.{adapter_name}")
        
        # Redis keys for distributed rate limiting
        self.requests_key = f"rate_limit:{adapter_name}:requests"
        self.window_start_key = f"rate_limit:{adapter_name}:window_start"
        self.tokens_key = f"rate_limit:{adapter_name}:tokens"
        self.last_refill_key = f"rate_limit:{adapter_name}:last_refill"
        
        # Initialize Lua scripts
        self._init_lua_scripts()
    
    def _init_lua_scripts(self):
        """Initialize Redis Lua scripts for atomic rate limiting"""
        
        # Sliding window rate limiting script
        self.sliding_window_script = """
        local requests_key = KEYS[1]
        local window_start_key = KEYS[2]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local current_time = tonumber(ARGV[3])
        
        -- Get window start time
        local window_start = tonumber(redis.call('GET', window_start_key))
        if not window_start then
            window_start = current_time - window
            redis.call('SET', window_start_key, window_start, 'EX', window * 2)
        end
        
        -- Check if we need to slide the window
        if current_time - window_start >= window then
            window_start = current_time - window
            redis.call('SET', window_start_key, window_start, 'EX', window * 2)
            redis.call('DEL', requests_key)
        end
        
        -- Increment request count
        local request_count = tonumber(redis.call('INCR', requests_key))
        redis.call('EXPIRE', requests_key, window)
        
        -- Check if limit exceeded
        if request_count > limit then
            local ttl = redis.call('TTL', requests_key)
            return {false, request_count, ttl}
        else
            return {true, request_count, -1}
        end
        """
        
        # Token bucket rate limiting script
        self.token_bucket_script = """
        local tokens_key = KEYS[1]
        local last_refill_key = KEYS[2]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local current_time = tonumber(ARGV[3])
        local tokens_requested = tonumber(ARGV[4])
        
        -- Get current tokens and last refill time
        local tokens = tonumber(redis.call('GET', tokens_key)) or capacity
        local last_refill = tonumber(redis.call('GET', last_refill_key)) or current_time
        
        -- Calculate tokens to add
        local time_passed = current_time - last_refill
        local tokens_to_add = time_passed * refill_rate
        tokens = math.min(capacity, tokens + tokens_to_add)
        
        -- Check if enough tokens available
        if tokens >= tokens_requested then
            tokens = tokens - tokens_requested
            
            -- Update Redis
            redis.call('SET', tokens_key, tokens, 'EX', 3600)
            redis.call('SET', last_refill_key, current_time, 'EX', 3600)
            
            return {true, tokens, -1}
        else
            -- Update Redis with current token count
            redis.call('SET', tokens_key, tokens, 'EX', 3600)
            redis.call('SET', last_refill_key, current_time, 'EX', 3600)
            
            -- Calculate retry time
            local retry_time = (tokens_requested - tokens) / refill_rate
            return {false, tokens, retry_time}
        end
        """
    
    async def check_sliding_window(self) -> Dict[str, Any]:
        """Check rate limit using sliding window algorithm"""
        try:
            result = await self.redis.eval(
                self.sliding_window_script,
                2,  # Number of keys
                self.requests_key,
                self.window_start_key,
                self.config.limit,
                self.config.window,
                time.time()
            )
            
            allowed, count, retry_after = result
            
            return {
                "allowed": bool(allowed),
                "count": count,
                "retry_after": retry_after,
                "algorithm": "sliding_window"
            }
            
        except Exception as e:
            self.logger.error(f"Error checking sliding window: {e}")
            return {"allowed": True, "error": str(e)}
    
    async def check_token_bucket(self, tokens_requested: int = 1) -> Dict[str, Any]:
        """Check rate limit using token bucket algorithm"""
        try:
            if not self.config.burst_limit:
                self.config.burst_limit = self.config.limit
            if not self.config.refill_rate:
                self.config.refill_rate = self.config.limit / self.config.window
            
            result = await self.redis.eval(
                self.token_bucket_script,
                2,  # Number of keys
                self.tokens_key,
                self.last_refill_key,
                self.config.burst_limit,
                self.config.refill_rate,
                time.time(),
                tokens_requested
            )
            
            allowed, tokens_remaining, retry_after = result
            
            return {
                "allowed": bool(allowed),
                "tokens_remaining": tokens_remaining,
                "retry_after": retry_after,
                "algorithm": "token_bucket"
            }
            
        except Exception as e:
            self.logger.error(f"Error checking token bucket: {e}")
            return {"allowed": True, "error": str(e)}
    
    async def acquire(self, tokens_requested: int = 1) -> bool:
        """
        Acquire permission to make a request.
        
        Args:
            tokens_requested: Number of tokens to acquire (default: 1)
            
        Returns:
            True if request is allowed, False otherwise
            
        Raises:
            RateLimitExceededError: If rate limit is exceeded
        """
        # Choose algorithm based on configuration
        if self.config.refill_rate:
            # Token bucket algorithm
            result = await self.check_token_bucket(tokens_requested)
        else:
            # Sliding window algorithm
            result = await self.check_sliding_window()
        
        if not result["allowed"]:
            retry_after = int(result.get("retry_after", self.config.window))
            
            self.logger.warning(
                f"Rate limit exceeded for {self.adapter_name}: "
                f"count={result.get('count', 0)}, retry_after={retry_after}s"
            )
            
            raise RateLimitExceededError(
                adapter_name=self.adapter_name,
                limit=self.config.limit,
                window=self.config.window,
                retry_after=retry_after,
                context=result
            )
        
        self.logger.debug(
            f"Rate limit check passed for {self.adapter_name}: "
            f"remaining={result.get('tokens_remaining', 'N/A')}"
        )
        
        return True
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get rate limiter metrics"""
        try:
            # Get current state from Redis
            if self.config.refill_rate:
                # Token bucket metrics
                tokens = await self.redis.get(self.tokens_key)
                last_refill = await self.redis.get(self.last_refill_key)
                
                return {
                    "adapter_name": self.adapter_name,
                    "algorithm": "token_bucket",
                    "tokens_remaining": float(tokens) if tokens else self.config.burst_limit,
                    "burst_limit": self.config.burst_limit,
                    "refill_rate": self.config.refill_rate,
                    "last_refill_time": float(last_refill) if last_refill else None,
                    "config": {
                        "limit": self.config.limit,
                        "window": self.config.window
                    }
                }
            else:
                # Sliding window metrics
                count = await self.redis.get(self.requests_key)
                window_start = await self.redis.get(self.window_start_key)
                
                return {
                    "adapter_name": self.adapter_name,
                    "algorithm": "sliding_window",
                    "current_count": int(count) if count else 0,
                    "limit": self.config.limit,
                    "window": self.config.window,
                    "window_start_time": float(window_start) if window_start else None,
                    "config": {
                        "limit": self.config.limit,
                        "window": self.config.window
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error getting metrics: {e}")
            return {"error": str(e)}
    
    async def reset(self):
        """Reset rate limiter state"""
        try:
            # Delete all rate limiter keys
            keys = [
                self.requests_key,
                self.window_start_key,
                self.tokens_key,
                self.last_refill_key
            ]
            
            await self.redis.delete(*keys)
            
            self.logger.info(f"Rate limiter reset for {self.adapter_name}")
            
        except Exception as e:
            self.logger.error(f"Error resetting rate limiter: {e}")


# Rate limiter registry for managing multiple instances
class RateLimiterRegistry:
    """Registry for managing multiple rate limiters"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self._limiters: Dict[str, DistributedRateLimiter] = {}
        self.logger = logging.getLogger("RateLimiterRegistry")
    
    def get_limiter(
        self,
        adapter_name: str,
        config: RateLimitConfig
    ) -> DistributedRateLimiter:
        """Get or create rate limiter for adapter"""
        if adapter_name not in self._limiters:
            self._limiters[adapter_name] = DistributedRateLimiter(
                adapter_name=adapter_name,
                redis_client=self.redis_client,
                config=config
            )
        
        return self._limiters[adapter_name]
    
    async def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all rate limiters"""
        metrics = {}
        for adapter_name, limiter in self._limiters.items():
            try:
                metrics[adapter_name] = await limiter.get_metrics()
            except Exception as e:
                self.logger.error(f"Error getting metrics for {adapter_name}: {e}")
                metrics[adapter_name] = {"error": str(e)}
        
        return metrics
    
    async def reset_all(self):
        """Reset all rate limiters"""
        reset_tasks = []
        for limiter in self._limiters.values():
            reset_tasks.append(limiter.reset())
        
        if reset_tasks:
            await asyncio.gather(*reset_tasks, return_exceptions=True)


# Decorator for rate limiting
def rate_limited(
    adapter_name: str,
    redis_client: redis.Redis,
    config: RateLimitConfig
):
    """
    Decorator for adding rate limiting to functions.
    
    Args:
        adapter_name: Name of the adapter
        redis_client: Redis client for distributed state
        config: Rate limit configuration
        
    Returns:
        Decorated function with rate limiting
    """
    def decorator(func: Callable):
        # Create rate limiter instance
        limiter = DistributedRateLimiter(
            adapter_name=adapter_name,
            redis_client=redis_client,
            config=config
        )
        
        async def async_wrapper(*args, **kwargs):
            await limiter.acquire()
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, func, *args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            # For sync functions, run in executor
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                limiter.acquire()
            ) and loop.run_in_executor(None, func, *args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
