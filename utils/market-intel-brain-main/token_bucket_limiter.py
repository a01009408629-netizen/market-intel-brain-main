"""
Token Bucket Rate Limiter for API Free Tier Management
Strict quota management for each specific service
"""

import time
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class APIProvider(Enum):
    """API providers with free tier limits."""
    ALPHA_VANTAGE = "alpha_vantage"
    FINNHUB = "finnhub"
    TWELVE_DATA = "twelve_data"
    MARKET_STACK = "market_stack"
    FMP = "fmp"
    FINMIND = "finmind"
    FRED_AUTH = "fred_auth"


@dataclass
class TokenBucketConfig:
    """Token bucket configuration for each API."""
    max_tokens: int  # Maximum tokens (quota)
    refill_rate: float  # Tokens per second
    window_seconds: int  # Time window for quota reset
    daily_limit: int  # Daily limit (for APIs with daily quotas)


class TokenBucket:
    """Token bucket implementation for rate limiting."""
    
    def __init__(self, config: TokenBucketConfig):
        self.config = config
        self.tokens = config.max_tokens
        self.last_refill = time.time()
        self.daily_tokens = config.daily_limit
        self.daily_reset = self._get_next_daily_reset()
    
    def _get_next_daily_reset(self) -> float:
        """Get next daily reset timestamp (midnight UTC)."""
        import datetime
        now = datetime.datetime.utcnow()
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        return tomorrow.timestamp()
    
    def _refill_tokens(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Refill based on rate
        tokens_to_add = elapsed * self.config.refill_rate
        self.tokens = min(self.config.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now
        
        # Check daily reset
        if now >= self.daily_reset:
            self.daily_tokens = self.config.daily_limit
            self.daily_reset = self._get_next_daily_reset()
    
    async def consume(self, tokens: int = 1) -> bool:
        """Consume tokens if available."""
        self._refill_tokens()
        
        # Check both bucket and daily limits
        if self.tokens >= tokens and self.daily_tokens >= tokens:
            self.tokens -= tokens
            self.daily_tokens -= tokens
            return True
        
        return False
    
    def get_status(self) -> Dict[str, float]:
        """Get current bucket status."""
        self._refill_tokens()
        return {
            "tokens": self.tokens,
            "max_tokens": self.config.max_tokens,
            "daily_tokens": self.daily_tokens,
            "daily_limit": self.config.daily_limit,
            "utilization": 1 - (self.tokens / self.config.max_tokens),
            "daily_utilization": 1 - (self.daily_tokens / self.config.daily_limit),
            "time_to_reset": self.daily_reset - time.time()
        }


class TokenBucketRateLimiter:
    """Centralized rate limiter for all API providers."""
    
    def __init__(self):
        # Free tier configurations (strict limits)
        self.configs = {
            APIProvider.ALPHA_VANTAGE: TokenBucketConfig(
                max_tokens=5,  # Conservative burst
                refill_rate=5/86400,  # 25 requests per day
                window_seconds=86400,
                daily_limit=25
            ),
            APIProvider.FINNHUB: TokenBucketConfig(
                max_tokens=60,  # 1 minute burst
                refill_rate=1.0,  # 1 request per second
                window_seconds=60,
                daily_limit=60000  # 60k per month, ~2k per day
            ),
            APIProvider.TWELVE_DATA: TokenBucketConfig(
                max_tokens=8,  # 8 requests per minute
                refill_rate=8/60,  # 8 requests per minute
                window_seconds=60,
                daily_limit=800  # 8 requests/minute * 100 minutes
            ),
            APIProvider.MARKET_STACK: TokenBucketConfig(
                max_tokens=1000,  # 1000 requests per month
                refill_rate=1000/2592000,  # ~0.0004 per second
                window_seconds=2592000,  # 30 days
                daily_limit=33  # ~1000/30
            ),
            APIProvider.FMP: TokenBucketConfig(
                max_tokens=250,  # 250 requests per day
                refill_rate=250/86400,  # 250 requests per day
                window_seconds=86400,
                daily_limit=250
            ),
            APIProvider.FINMIND: TokenBucketConfig(
                max_tokens=3000,  # 3000 requests per day
                refill_rate=3000/86400,  # 3000 requests per day
                window_seconds=86400,
                daily_limit=3000
            ),
            APIProvider.FRED_AUTH: TokenBucketConfig(
                max_tokens=120,  # 120 requests per minute
                refill_rate=2.0,  # 2 requests per second
                window_seconds=60,
                daily_limit=172800  # 120/min * 24h
            )
        }
        
        # Create token buckets
        self.buckets = {
            provider: TokenBucket(config) 
            for provider, config in self.configs.items()
        }
    
    async def can_consume(self, provider: APIProvider, tokens: int = 1) -> bool:
        """Check if tokens can be consumed."""
        if provider not in self.buckets:
            return False
        
        return await self.buckets[provider].consume(tokens)
    
    def get_status(self, provider: APIProvider) -> Optional[Dict[str, float]]:
        """Get status for specific provider."""
        if provider not in self.buckets:
            return None
        
        return self.buckets[provider].get_status()
    
    def get_all_status(self) -> Dict[str, Dict[str, float]]:
        """Get status for all providers."""
        return {
            provider.value: status 
            for provider, bucket in self.buckets.items()
            for status in [bucket.get_status()]
        }
    
    def get_wait_time(self, provider: APIProvider, tokens: int = 1) -> float:
        """Get estimated wait time for tokens."""
        if provider not in self.buckets:
            return float('inf')
        
        bucket = self.buckets[provider]
        status = bucket.get_status()
        
        if status["tokens"] >= tokens:
            return 0.0
        
        # Calculate time to refill needed tokens
        needed_tokens = tokens - status["tokens"]
        wait_time = needed_tokens / bucket.config.refill_rate
        
        return wait_time
    
    async def wait_for_tokens(self, provider: APIProvider, tokens: int = 1) -> bool:
        """Wait until tokens are available."""
        wait_time = self.get_wait_time(provider, tokens)
        
        if wait_time > 0:
            # Cap wait time to reasonable limit (1 hour)
            wait_time = min(wait_time, 3600)
            await asyncio.sleep(wait_time)
        
        return await self.can_consume(provider, tokens)


# Global rate limiter instance
_token_bucket_limiter: Optional[TokenBucketRateLimiter] = None


def get_token_bucket_limiter() -> TokenBucketRateLimiter:
    """Get global token bucket rate limiter."""
    global _token_bucket_limiter
    if _token_bucket_limiter is None:
        _token_bucket_limiter = TokenBucketRateLimiter()
    return _token_bucket_limiter


async def main():
    """Test token bucket rate limiter."""
    limiter = get_token_bucket_limiter()
    
    print("Testing Token Bucket Rate Limiter")
    print("=" * 50)
    
    # Test Alpha Vantage (very strict limits)
    print("\n1. Testing Alpha Vantage (25/day limit):")
    provider = APIProvider.ALPHA_VANTAGE
    
    for i in range(5):
        can_consume = await limiter.can_consume(provider)
        status = limiter.get_status(provider)
        print(f"  Request {i+1}: {'ALLOWED' if can_consume else 'DENIED'} | Tokens: {status['tokens']:.1f}/{status['max_tokens']} | Daily: {status['daily_tokens']}/{status['daily_limit']}")
    
    # Test Finnhub (more generous)
    print("\n2. Testing Finnhub (1/sec limit):")
    provider = APIProvider.FINNHUB
    
    for i in range(5):
        can_consume = await limiter.can_consume(provider)
        status = limiter.get_status(provider)
        print(f"  Request {i+1}: {'ALLOWED' if can_consume else 'DENIED'} | Tokens: {status['tokens']:.1f}/{status['max_tokens']}")
        
        if can_consume:
            await asyncio.sleep(0.5)  # Wait 0.5 seconds
    
    # Test wait time calculation
    print("\n3. Testing wait time calculation:")
    provider = APIProvider.ALPHA_VANTAGE
    wait_time = limiter.get_wait_time(provider, 10)
    print(f"  Wait time for 10 tokens: {wait_time:.1f} seconds")
    
    # Show all status
    print("\n4. All provider status:")
    all_status = limiter.get_all_status()
    for provider_name, status in all_status.items():
        print(f"  {provider_name:15} | {status['tokens']:6.1f}/{status['max_tokens']:6.1f} | {status['daily_tokens']:4}/{status['daily_limit']:4} | {status['utilization']:.1%}")


if __name__ == "__main__":
    asyncio.run(main())
