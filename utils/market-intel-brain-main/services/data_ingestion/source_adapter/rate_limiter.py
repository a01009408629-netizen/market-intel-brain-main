import asyncio
import time
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import redis.asyncio as redis

from .error_contract_v2 import ProviderRateLimitError


class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms"""
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting per provider"""
    requests_per_period: int
    period_seconds: int
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET
    bucket_size: Optional[int] = None  # For token bucket algorithm
    leak_rate: Optional[float] = None  # For leaky bucket algorithm
    
    def __post_init__(self):
        # Set default bucket size for token bucket
        if self.algorithm == RateLimitAlgorithm.TOKEN_BUCKET and self.bucket_size is None:
            self.bucket_size = self.requests_per_period
        
        # Set default leak rate for leaky bucket
        if self.algorithm == RateLimitAlgorithm.LEAKY_BUCKET and self.leak_rate is None:
            self.leak_rate = self.requests_per_period / self.period_seconds


class TokenBucketState:
    """Token bucket algorithm state"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens = config.bucket_size
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def _refill(self):
        """Refill tokens based on elapsed time"""
        current_time = time.time()
        elapsed = current_time - self.last_refill
        
        if elapsed > 0:
            # Calculate tokens to add
            tokens_to_add = (elapsed / self.config.period_seconds) * self.config.requests_per_period
            self.tokens = min(self.config.bucket_size, self.tokens + tokens_to_add)
            self.last_refill = current_time
    
    async def consume_token(self) -> bool:
        """Consume one token if available"""
        async with self._lock:
            await self._refill()
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False
    
    def get_wait_time(self) -> float:
        """Calculate time until next token is available"""
        if self.tokens >= 1:
            return 0.0
        
        # Time needed for one token
        time_per_token = self.config.period_seconds / self.config.requests_per_period
        return time_per_token


class LeakyBucketState:
    """Leaky bucket algorithm state"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.volume = 0.0
        self.last_leak = time.time()
        self._lock = asyncio.Lock()
    
    async def _leak(self):
        """Leak volume based on elapsed time"""
        current_time = time.time()
        elapsed = current_time - self.last_leak
        
        if elapsed > 0:
            # Calculate volume to leak
            volume_to_leak = elapsed * self.config.leak_rate
            self.volume = max(0, self.volume - volume_to_leak)
            self.last_leak = current_time
    
    async def add_request(self) -> bool:
        """Add request to bucket if not overflowing"""
        async with self._lock:
            await self._leak()
            
            if self.volume < 1.0:
                self.volume += 1.0
                return True
            return False
    
    def get_wait_time(self) -> float:
        """Calculate time until bucket can accept new request"""
        if self.volume < 1.0:
            return 0.0
        
        # Time needed to leak enough volume
        excess_volume = self.volume - 1.0
        return excess_volume / self.config.leak_rate


class RedisRateLimitState:
    """Redis-backed rate limiting state for distributed systems"""
    
    def __init__(
        self,
        provider_name: str,
        redis_client: redis.Redis,
        config: RateLimitConfig,
        logger: Optional[logging.Logger] = None
    ):
        self.provider_name = provider_name
        self.redis = redis_client
        self.config = config
        self.logger = logger or logging.getLogger(f"RateLimiter.{provider_name}")
        
        # Redis keys
        if config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            self.tokens_key = f"rate_limit:{provider_name}:tokens"
            self.last_refill_key = f"rate_limit:{provider_name}:last_refill"
            self.lock_key = f"rate_limit:{provider_name}:lock"
        else:  # LEAKY_BUCKET
            self.volume_key = f"rate_limit:{provider_name}:volume"
            self.last_leak_key = f"rate_limit:{provider_name}:last_leak"
            self.lock_key = f"rate_limit:{provider_name}:lock"
    
    async def _get_redis_value(self, key: str, default: Any = None) -> Any:
        """Get value from Redis with error handling"""
        try:
            value = await self.redis.get(key)
            if value is None:
                return default
            return float(value)
        except Exception as e:
            self.logger.warning(f"Redis get error for key {key}: {e}")
            return default
    
    async def _set_redis_value(self, key: str, value: Any, ex: Optional[int] = None):
        """Set value in Redis with error handling"""
        try:
            await self.redis.set(key, str(value), ex=ex)
        except Exception as e:
            self.logger.warning(f"Redis set error for key {key}: {e}")
    
    async def _acquire_lock(self, timeout: float = 5.0) -> bool:
        """Acquire distributed lock"""
        try:
            return await self.redis.set(self.lock_key, "1", nx=True, ex=timeout)
        except Exception as e:
            self.logger.warning(f"Redis lock error: {e}")
            return False
    
    async def _release_lock(self):
        """Release distributed lock"""
        try:
            await self.redis.delete(self.lock_key)
        except Exception as e:
            self.logger.warning(f"Redis lock release error: {e}")
    
    async def consume_token(self) -> bool:
        """Consume token using Redis (token bucket algorithm)"""
        if not await self._acquire_lock():
            return False
        
        try:
            current_time = time.time()
            
            # Get current state
            tokens = await self._get_redis_value(self.tokens_key, self.config.bucket_size)
            last_refill = await self._get_redis_value(self.last_refill_key, current_time)
            
            # Refill tokens
            elapsed = current_time - last_refill
            if elapsed > 0:
                tokens_to_add = (elapsed / self.config.period_seconds) * self.config.requests_per_period
                tokens = min(self.config.bucket_size, tokens + tokens_to_add)
                last_refill = current_time
            
            # Check if token available
            if tokens >= 1:
                tokens -= 1
                
                # Update Redis
                await self._set_redis_value(self.tokens_key, tokens, ex=3600)
                await self._set_redis_value(self.last_refill_key, last_refill, ex=3600)
                
                return True
            
            return False
        
        finally:
            await self._release_lock()
    
    async def add_request(self) -> bool:
        """Add request using Redis (leaky bucket algorithm)"""
        if not await self._acquire_lock():
            return False
        
        try:
            current_time = time.time()
            
            # Get current state
            volume = await self._get_redis_value(self.volume_key, 0.0)
            last_leak = await self._get_redis_value(self.last_leak_key, current_time)
            
            # Leak volume
            elapsed = current_time - last_leak
            if elapsed > 0:
                volume_to_leak = elapsed * self.config.leak_rate
                volume = max(0, volume - volume_to_leak)
                last_leak = current_time
            
            # Check if can accept request
            if volume < 1.0:
                volume += 1.0
                
                # Update Redis
                await self._set_redis_value(self.volume_key, volume, ex=3600)
                await self._set_redis_value(self.last_leak_key, last_leak, ex=3600)
                
                return True
            
            return False
        
        finally:
            await self._release_lock()


class RateLimiter:
    """
    Rate limiter with Token Bucket and Leaky Bucket algorithms.
    
    Supports both in-memory and Redis-backed distributed rate limiting.
    Prevents hitting provider rate limits by checking locally first.
    """
    
    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        default_config: Optional[Dict[str, RateLimitConfig]] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.redis_client = redis_client
        self.logger = logger or logging.getLogger("RateLimiter")
        
        # Default provider configurations
        self.default_configs = default_config or {
            "finnhub": RateLimitConfig(
                requests_per_period=60,
                period_seconds=60,
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET
            ),
            "yahoo_finance": RateLimitConfig(
                requests_per_period=2000,
                period_seconds=3600,  # 1 hour
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET
            ),
            "marketstack": RateLimitConfig(
                requests_per_period=1000,
                period_seconds=30,  # 30 seconds
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET
            ),
            "financial_modeling_prep": RateLimitConfig(
                requests_per_period=250,
                period_seconds=300,  # 5 minutes
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET
            ),
            "news_catcher": RateLimitConfig(
                requests_per_period=100,
                period_seconds=60,
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET
            ),
            "econdb": RateLimitConfig(
                requests_per_period=300,
                period_seconds=300,  # 5 minutes
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET
            ),
            "trading_economics": RateLimitConfig(
                requests_per_period=200,
                period_seconds=60,
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET
            ),
            "alpha_vantage": RateLimitConfig(
                requests_per_period=5,
                period_seconds=60,  # 1 minute (very strict)
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET
            )
        }
        
        # Rate limiter states per provider
        self._states: Dict[str, Any] = {}
        
        # Initialize states for default configs
        for provider_name, config in self.default_configs.items():
            self._initialize_provider_state(provider_name, config)
        
        self.logger.info(f"Rate limiter initialized with {len(self.default_configs)} provider configs")
    
    def _initialize_provider_state(self, provider_name: str, config: RateLimitConfig):
        """Initialize rate limiting state for a provider"""
        if self.redis_client:
            # Use Redis-backed state for distributed systems
            self._states[provider_name] = RedisRateLimitState(
                provider_name=provider_name,
                redis_client=self.redis_client,
                config=config,
                logger=self.logger
            )
        else:
            # Use in-memory state
            if config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
                self._states[provider_name] = TokenBucketState(config)
            else:  # LEAKY_BUCKET
                self._states[provider_name] = LeakyBucketState(config)
    
    def add_provider_config(self, provider_name: str, config: RateLimitConfig):
        """Add or update rate limit configuration for a provider"""
        provider_name_lower = provider_name.lower()
        self.default_configs[provider_name_lower] = config
        self._initialize_provider_state(provider_name_lower, config)
        self.logger.info(f"Added rate limit config for {provider_name}: {config.requests_per_period}/{config.period_seconds}s")
    
    def get_provider_config(self, provider_name: str) -> Optional[RateLimitConfig]:
        """Get rate limit configuration for a provider"""
        return self.default_configs.get(provider_name.lower())
    
    async def wait_for_token(self, provider_name: str) -> bool:
        """
        Wait for a token/permit for the specified provider.
        
        If rate limit would be exceeded, raises ProviderRateLimitError
        before the network request is made.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            bool: True if token is available
            
        Raises:
            ProviderRateLimitError: If rate limit is exceeded
        """
        provider_name_lower = provider_name.lower()
        
        if provider_name_lower not in self._states:
            # Use default config for unknown providers
            default_config = RateLimitConfig(
                requests_per_period=100,
                period_seconds=60,
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET
            )
            self.add_provider_config(provider_name_lower, default_config)
        
        state = self._states[provider_name_lower]
        config = self.default_configs[provider_name_lower]
        
        # Try to consume token/add request
        if config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            can_proceed = await state.consume_token()
            wait_time = state.get_wait_time()
        else:  # LEAKY_BUCKET
            can_proceed = await state.add_request()
            wait_time = state.get_wait_time()
        
        if can_proceed:
            self.logger.debug(f"Rate limit check passed for {provider_name}")
            return True
        else:
            # Rate limit exceeded - raise error before network call
            retry_after = int(wait_time) if wait_time > 0 else config.period_seconds
            
            self.logger.warning(
                f"Rate limit exceeded for {provider_name}. "
                f"Wait time: {wait_time:.2f}s, Retry after: {retry_after}s"
            )
            
            raise ProviderRateLimitError(
                provider_name=provider_name,
                retry_after=retry_after,
                limit=config.requests_per_period,
                message=f"Rate limit exceeded for {provider_name}. "
                       f"Maximum {config.requests_per_period} requests per {config.period_seconds} seconds. "
                       f"Retry after {retry_after} seconds.",
                context={
                    "algorithm": config.algorithm.value,
                    "wait_time": wait_time,
                    "current_limit": config.requests_per_period,
                    "period_seconds": config.period_seconds
                }
            )
    
    async def get_wait_time(self, provider_name: str) -> float:
        """Get current wait time for a provider"""
        provider_name_lower = provider_name.lower()
        
        if provider_name_lower not in self._states:
            return 0.0
        
        state = self._states[provider_name_lower]
        return state.get_wait_time()
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get rate limiting metrics"""
        metrics = {
            "providers": {},
            "backend": "redis" if self.redis_client else "memory",
            "total_providers": len(self._states)
        }
        
        for provider_name, state in self._states.items():
            try:
                wait_time = await state.get_wait_time()
                config = self.default_configs[provider_name]
                
                metrics["providers"][provider_name] = {
                    "algorithm": config.algorithm.value,
                    "requests_per_period": config.requests_per_period,
                    "period_seconds": config.period_seconds,
                    "current_wait_time": wait_time,
                    "backend": "redis" if self.redis_client else "memory"
                }
            except Exception as e:
                self.logger.error(f"Error getting metrics for {provider_name}: {e}")
                metrics["providers"][provider_name] = {"error": str(e)}
        
        return metrics
    
    def list_providers(self) -> Dict[str, RateLimitConfig]:
        """List all provider configurations"""
        return self.default_configs.copy()


# Global rate limiter instance
_global_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(
    redis_client: Optional[redis.Redis] = None,
    default_config: Optional[Dict[str, RateLimitConfig]] = None
) -> RateLimiter:
    """Get or create the global rate limiter"""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter(redis_client, default_config)
    return _global_rate_limiter


async def wait_for_token(provider_name: str) -> bool:
    """Convenience function to wait for token using global rate limiter"""
    rate_limiter = get_rate_limiter()
    return await rate_limiter.wait_for_token(provider_name)
