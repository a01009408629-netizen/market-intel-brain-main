"""
Production-Ready Rate Limiting & Token Bucket API Gateway
Prevents HTTP 429 with configurable weights per endpoint
"""

import asyncio
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import defaultdict, deque


class RateLimitUnit(Enum):
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_tokens: int
    refill_rate: float
    unit: RateLimitUnit
    weight: int = 1
    
    def __post_init__(self):
        """Convert refill rate based on unit."""
        if self.unit == RateLimitUnit.SECOND:
            self.refill_rate_per_second = self.refill_rate
        elif self.unit == RateLimitUnit.MINUTE:
            self.refill_rate_per_second = self.refill_rate / 60
        elif self.unit == RateLimitUnit.HOUR:
            self.refill_rate_per_second = self.refill_rate / 3600
        else:
            raise ValueError(f"Unsupported unit: {self.unit}")


@dataclass
class TokenBucket:
    """Token bucket implementation for rate limiting."""
    max_tokens: int
    tokens: float
    refill_rate: float
    last_refill: float
    weight: int = 1
    
    def __init__(self, config: RateLimitConfig):
        self.max_tokens = config.max_tokens
        self.tokens = float(config.max_tokens)
        self.refill_rate = config.refill_rate_per_second
        self.last_refill = time.time()
        self.weight = config.weight
        self._lock = threading.RLock()
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        current_time = time.time()
        elapsed = current_time - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        
        with self._lock:
            self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
            self.last_refill = current_time
    
    def consume(self, tokens: int = 1) -> bool:
        """Consume tokens if available."""
        self._refill()
        
        with self._lock:
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def consume_with_weight(self) -> bool:
        """Consume tokens based on weight."""
        return self.consume(self.weight)
    
    def time_until_available(self, tokens: int = 1) -> float:
        """Calculate time until tokens are available."""
        self._refill()
        
        with self._lock:
            if self.tokens >= tokens:
                return 0.0
            
            deficit = tokens - self.tokens
            return deficit / self.refill_rate
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bucket status."""
        self._refill()
        
        with self._lock:
            return {
                "tokens": self.tokens,
                "max_tokens": self.max_tokens,
                "refill_rate": self.refill_rate,
                "weight": self.weight,
                "utilization": (self.max_tokens - self.tokens) / self.max_tokens
            }


class RateLimiter:
    """Multi-endpoint rate limiter with token bucket algorithm."""
    
    def __init__(self):
        self._buckets: Dict[str, TokenBucket] = {}
        self._configs: Dict[str, RateLimitConfig] = {}
        self._global_lock = threading.RLock()
        self._setup_default_configs()
    
    def _setup_default_configs(self):
        """Setup default rate limit configurations."""
        default_configs = {
            # High-frequency trading endpoints
            "binance_ws": RateLimitConfig(
                max_tokens=1000,
                refill_rate=50,
                unit=RateLimitUnit.SECOND,
                weight=1
            ),
            
            # REST API endpoints
            "binance_rest": RateLimitConfig(
                max_tokens=1200,
                refill_rate=20,
                unit=RateLimitUnit.MINUTE,
                weight=1
            ),
            
            # News endpoints (lower limits)
            "bloomberg_rest": RateLimitConfig(
                max_tokens=500,
                refill_rate=50,
                unit=RateLimitUnit.MINUTE,
                weight=2
            ),
            
            # Other REST endpoints
            "okx_rest": RateLimitConfig(
                max_tokens=600,
                refill_rate=10,
                unit=RateLimitUnit.SECOND,
                weight=1
            ),
            
            "coinbase_rest": RateLimitConfig(
                max_tokens=10000,
                refill_rate=100,
                unit=RateLimitUnit.MINUTE,
                weight=1
            ),
            
            # WebSocket endpoints
            "kraken_ws": RateLimitConfig(
                max_tokens=100,
                refill_rate=10,
                unit=RateLimitUnit.SECOND,
                weight=1
            ),
            
            "huobi_ws": RateLimitConfig(
                max_tokens=200,
                refill_rate=20,
                unit=RateLimitUnit.SECOND,
                weight=1
            )
        }
        
        for endpoint, config in default_configs.items():
            self.add_endpoint(endpoint, config)
    
    def add_endpoint(self, endpoint: str, config: RateLimitConfig):
        """Add rate limit configuration for an endpoint."""
        with self._global_lock:
            self._configs[endpoint] = config
            self._buckets[endpoint] = TokenBucket(config)
    
    def remove_endpoint(self, endpoint: str):
        """Remove rate limit configuration for an endpoint."""
        with self._global_lock:
            self._configs.pop(endpoint, None)
            self._buckets.pop(endpoint, None)
    
    def can_consume(self, endpoint: str, tokens: int = 1) -> bool:
        """Check if endpoint can consume tokens."""
        if endpoint not in self._buckets:
            return True  # No rate limiting for unknown endpoints
        
        bucket = self._buckets[endpoint]
        return bucket.consume(tokens)
    
    async def consume_with_backoff(self, endpoint: str, tokens: int = 1, max_wait: float = 60.0) -> bool:
        """Consume tokens with exponential backoff."""
        if endpoint not in self._buckets:
            return True
        
        bucket = self._buckets[endpoint]
        wait_time = 0.1
        max_wait_time = max_wait
        
        while wait_time <= max_wait_time:
            if bucket.consume(tokens):
                return True
            
            # Wait with exponential backoff
            await asyncio.sleep(wait_time)
            wait_time = min(wait_time * 2, max_wait_time)
        
        return False
    
    def get_wait_time(self, endpoint: str, tokens: int = 1) -> float:
        """Get wait time until tokens are available."""
        if endpoint not in self._buckets:
            return 0.0
        
        bucket = self._buckets[endpoint]
        return bucket.time_until_available(tokens)
    
    def get_endpoint_status(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Get status of specific endpoint."""
        if endpoint not in self._buckets:
            return None
        
        bucket = self._buckets[endpoint]
        config = self._configs[endpoint]
        
        return {
            "endpoint": endpoint,
            "config": {
                "max_tokens": config.max_tokens,
                "refill_rate": config.refill_rate,
                "unit": config.unit.value,
                "weight": config.weight
            },
            "status": bucket.get_status()
        }
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all endpoints."""
        status = {}
        for endpoint in self._buckets:
            status[endpoint] = self.get_endpoint_status(endpoint)
        return status
    
    def reset_endpoint(self, endpoint: str):
        """Reset token bucket for endpoint."""
        if endpoint in self._buckets:
            config = self._configs[endpoint]
            self._buckets[endpoint] = TokenBucket(config)
    
    def update_config(self, endpoint: str, config: RateLimitConfig):
        """Update configuration for endpoint."""
        with self._global_lock:
            self._configs[endpoint] = config
            self._buckets[endpoint] = TokenBucket(config)


class APIGateway:
    """API Gateway with integrated rate limiting."""
    
    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        self.rate_limiter = rate_limiter or RateLimiter()
        self._request_stats = defaultdict(lambda: {"total": 0, "blocked": 0, "allowed": 0})
        self._stats_lock = threading.RLock()
    
    async def make_request(self, endpoint: str, request_func, *args, **kwargs) -> Tuple[bool, Any]:
        """Make request with rate limiting."""
        # Update stats
        with self._stats_lock:
            self._request_stats[endpoint]["total"] += 1
        
        # Check rate limit
        if not self.rate_limiter.can_consume(endpoint):
            with self._stats_lock:
                self._request_stats[endpoint]["blocked"] += 1
            
            wait_time = self.rate_limiter.get_wait_time(endpoint)
            raise RateLimitExceeded(f"Rate limit exceeded for {endpoint}. Wait {wait_time:.2f}s")
        
        # Make request
        try:
            result = await request_func(*args, **kwargs)
            
            with self._stats_lock:
                self._request_stats[endpoint]["allowed"] += 1
            
            return True, result
            
        except Exception as e:
            with self._stats_lock:
                self._request_stats[endpoint]["blocked"] += 1
            raise
    
    async def make_request_with_retry(self, endpoint: str, request_func, *args, 
                                   max_retries: int = 3, **kwargs) -> Tuple[bool, Any]:
        """Make request with retry logic."""
        for attempt in range(max_retries + 1):
            try:
                return await self.make_request(endpoint, request_func, *args, **kwargs)
            except RateLimitExceeded as e:
                if attempt == max_retries:
                    raise
                
                # Wait and retry
                wait_time = self.rate_limiter.get_wait_time(endpoint)
                await asyncio.sleep(min(wait_time, 5.0))
    
    def get_request_stats(self, endpoint: str) -> Dict[str, Any]:
        """Get request statistics for endpoint."""
        with self._stats_lock:
            stats = self._request_stats[endpoint].copy()
        
        if stats["total"] > 0:
            stats["block_rate"] = stats["blocked"] / stats["total"]
            stats["allow_rate"] = stats["allowed"] / stats["total"]
        else:
            stats["block_rate"] = 0.0
            stats["allow_rate"] = 0.0
        
        return stats
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all endpoints."""
        all_stats = {}
        for endpoint in self._request_stats:
            all_stats[endpoint] = self.get_request_stats(endpoint)
        return all_stats


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


# Global instances
_rate_limiter: Optional[RateLimiter] = None
_api_gateway: Optional[APIGateway] = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def get_api_gateway() -> APIGateway:
    """Get global API gateway instance."""
    global _api_gateway
    if _api_gateway is None:
        _api_gateway = APIGateway(get_rate_limiter())
    return _api_gateway


async def main():
    """Example usage."""
    gateway = get_api_gateway()
    limiter = get_rate_limiter()
    
    # Mock request function
    async def mock_request(url):
        await asyncio.sleep(0.1)
        return f"Response from {url}"
    
    # Make requests
    endpoint = "binance_rest"
    
    for i in range(5):
        try:
            success, result = await gateway.make_request(endpoint, mock_request, f"https://api.binance.com/test/{i}")
            print(f"Request {i}: Success - {result}")
        except RateLimitExceeded as e:
            print(f"Request {i}: Rate limited - {e}")
    
    # Show stats
    print(f"\nStats for {endpoint}:")
    print(json.dumps(gateway.get_request_stats(endpoint), indent=2))
    
    print(f"\nAll endpoint status:")
    print(json.dumps(limiter.get_all_status(), indent=2))


if __name__ == "__main__":
    import json
    asyncio.run(main())
