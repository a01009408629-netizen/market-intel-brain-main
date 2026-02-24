"""
MAIFA v3 Rate Limiter Utility - Advanced rate limiting algorithms
Implements multiple rate limiting strategies for system protection
"""

import asyncio
import time
import threading
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque
import hashlib
import json

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    max_requests: int
    window_seconds: int
    burst_size: int = 0
    penalty_seconds: int = 0
    cleanup_interval: int = 300  # 5 minutes

class TokenBucket:
    """Token bucket rate limiter implementation"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """Consume tokens if available"""
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def get_available_tokens(self) -> int:
        """Get current available tokens"""
        with self._lock:
            self._refill()
            return int(self.tokens)
    
    def get_time_until_available(self, tokens: int = 1) -> float:
        """Get time until specified tokens are available"""
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                return 0.0
            
            needed = tokens - self.tokens
            return needed / self.refill_rate

class SlidingWindowCounter:
    """Sliding window rate limiter implementation"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        self._lock = threading.Lock()
    
    def is_allowed(self) -> bool:
        """Check if request is allowed"""
        with self._lock:
            now = time.time()
            
            # Remove old requests outside the window
            while self.requests and self.requests[0] <= now - self.window_seconds:
                self.requests.popleft()
            
            # Check if under limit
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            
            return False
    
    def get_current_count(self) -> int:
        """Get current request count in window"""
        with self._lock:
            now = time.time()
            
            # Remove old requests
            while self.requests and self.requests[0] <= now - self.window_seconds:
                self.requests.popleft()
            
            return len(self.requests)
    
    def get_time_until_reset(self) -> float:
        """Get time until window resets"""
        with self._lock:
            if not self.requests:
                return 0.0
            
            oldest_request = self.requests[0]
            reset_time = oldest_request + self.window_seconds
            return max(0.0, reset_time - time.time())

class FixedWindowCounter:
    """Fixed window rate limiter implementation"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.current_count = 0
        self.window_start = time.time()
        self._lock = threading.Lock()
    
    def is_allowed(self) -> bool:
        """Check if request is allowed"""
        with self._lock:
            now = time.time()
            
            # Reset window if expired
            if now - self.window_start >= self.window_seconds:
                self.current_count = 0
                self.window_start = now
            
            # Check if under limit
            if self.current_count < self.max_requests:
                self.current_count += 1
                return True
            
            return False
    
    def get_current_count(self) -> int:
        """Get current request count"""
        with self._lock:
            now = time.time()
            
            # Reset window if expired
            if now - self.window_start >= self.window_seconds:
                self.current_count = 0
                self.window_start = now
            
            return self.current_count
    
    def get_time_until_reset(self) -> float:
        """Get time until window resets"""
        with self._lock:
            now = time.time()
            reset_time = self.window_start + self.window_seconds
            return max(0.0, reset_time - now)

class RateLimiter:
    """
    MAIFA v3 Rate Limiter - Multi-strategy rate limiting
    
    Supports:
    - Token bucket algorithm
    - Sliding window counter
    - Fixed window counter
    - Distributed rate limiting
    - Adaptive rate limiting
    - Penalty system
    """
    
    def __init__(self):
        self._limiters: Dict[str, Any] = {}
        self._configs: Dict[str, RateLimitConfig] = {}
        self._penalties: Dict[str, float] = {}
        self._stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_requests": 0,
            "allowed_requests": 0,
            "blocked_requests": 0,
            "last_request": 0.0
        })
        self._lock = threading.Lock()
        
        # Background cleanup task
        self._cleanup_task = None
        self._running = False
    
    def add_limit(self, 
                   key: str,
                   config: RateLimitConfig,
                   algorithm: str = "token_bucket"):
        """Add rate limit for a key"""
        with self._lock:
            self._configs[key] = config
            
            # Create appropriate limiter
            if algorithm == "token_bucket":
                refill_rate = config.max_requests / config.window_seconds
                self._limiters[key] = TokenBucket(config.max_requests, refill_rate)
            elif algorithm == "sliding_window":
                self._limiters[key] = SlidingWindowCounter(config.max_requests, config.window_seconds)
            elif algorithm == "fixed_window":
                self._limiters[key] = FixedWindowCounter(config.max_requests, config.window_seconds)
            else:
                raise ValueError(f"Unknown algorithm: {algorithm}")
            
            # Initialize stats
            self._stats[key] = {
                "total_requests": 0,
                "allowed_requests": 0,
                "blocked_requests": 0,
                "last_request": 0.0
            }
    
    def is_allowed(self, key: str, tokens: int = 1) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed for key"""
        with self._lock:
            # Check if key exists
            if key not in self._limiters:
                return True, {"reason": "no_limit_set"}
            
            # Check penalty
            if key in self._penalties:
                penalty_until = self._penalties[key]
                if time.time() < penalty_until:
                    return False, {
                        "reason": "penalty_active",
                        "penalty_until": penalty_until
                    }
                else:
                    # Penalty expired
                    del self._penalties[key]
            
            # Check rate limit
            limiter = self._limiters[key]
            config = self._configs[key]
            
            # Update stats
            self._stats[key]["total_requests"] += 1
            self._stats[key]["last_request"] = time.time()
            
            # Check allowance
            if hasattr(limiter, 'consume'):
                # Token bucket
                allowed = limiter.consume(tokens)
                info = {
                    "available_tokens": limiter.get_available_tokens(),
                    "time_until_available": limiter.get_time_until_available(tokens)
                }
            else:
                # Window counters
                allowed = limiter.is_allowed()
                info = {
                    "current_count": limiter.get_current_count(),
                    "time_until_reset": limiter.get_time_until_reset()
                }
            
            # Update stats
            if allowed:
                self._stats[key]["allowed_requests"] += 1
            else:
                self._stats[key]["blocked_requests"] += 1
                
                # Apply penalty if configured
                if config.penalty_seconds > 0:
                    self._penalties[key] = time.time() + config.penalty_seconds
                    info["penalty_applied"] = config.penalty_seconds
            
            info.update({
                "algorithm": type(limiter).__name__,
                "config": {
                    "max_requests": config.max_requests,
                    "window_seconds": config.window_seconds
                }
            })
            
            return allowed, info
    
    def get_status(self, key: str) -> Dict[str, Any]:
        """Get current status for key"""
        with self._lock:
            if key not in self._limiters:
                return {"status": "no_limit"}
            
            limiter = self._limiters[key]
            config = self._configs[key]
            stats = self._stats[key]
            
            # Get limiter-specific info
            if hasattr(limiter, 'get_available_tokens'):
                limiter_info = {
                    "available_tokens": limiter.get_available_tokens(),
                    "time_until_available": limiter.get_time_until_available()
                }
            else:
                limiter_info = {
                    "current_count": limiter.get_current_count(),
                    "time_until_reset": limiter.get_time_until_reset()
                }
            
            # Check penalty
            penalty_info = {}
            if key in self._penalties:
                penalty_until = self._penalties[key]
                if time.time() < penalty_until:
                    penalty_info = {
                        "penalty_active": True,
                        "penalty_until": penalty_until,
                        "penalty_remaining": penalty_until - time.time()
                    }
                else:
                    penalty_info = {"penalty_active": False}
            
            return {
                "status": "active",
                "config": {
                    "max_requests": config.max_requests,
                    "window_seconds": config.window_seconds,
                    "burst_size": config.burst_size,
                    "penalty_seconds": config.penalty_seconds
                },
                "limiter_info": limiter_info,
                "penalty_info": penalty_info,
                "statistics": {
                    "total_requests": stats["total_requests"],
                    "allowed_requests": stats["allowed_requests"],
                    "blocked_requests": stats["blocked_requests"],
                    "allowance_rate": (
                        stats["allowed_requests"] / stats["total_requests"]
                        if stats["total_requests"] > 0 else 0.0
                    ),
                    "last_request": stats["last_request"]
                }
            }
    
    def remove_limit(self, key: str) -> bool:
        """Remove rate limit for key"""
        with self._lock:
            if key in self._limiters:
                del self._limiters[key]
                del self._configs[key]
                if key in self._penalties:
                    del self._penalties[key]
                if key in self._stats:
                    del self._stats[key]
                return True
            return False
    
    def reset_stats(self, key: str = None):
        """Reset statistics for key or all keys"""
        with self._lock:
            if key:
                if key in self._stats:
                    self._stats[key] = {
                        "total_requests": 0,
                        "allowed_requests": 0,
                        "blocked_requests": 0,
                        "last_request": 0.0
                    }
            else:
                for stats_key in self._stats:
                    self._stats[stats_key] = {
                        "total_requests": 0,
                        "allowed_requests": 0,
                        "blocked_requests": 0,
                        "last_request": 0.0
                    }
    
    def apply_penalty(self, key: str, penalty_seconds: int):
        """Apply manual penalty to key"""
        with self._lock:
            self._penalties[key] = time.time() + penalty_seconds
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status for all keys"""
        with self._lock:
            all_status = {}
            for key in self._limiters.keys():
                all_status[key] = self.get_status(key)
            
            return {
                "total_limits": len(self._limiters),
                "active_penalties": len(self._penalties),
                "limits": all_status
            }
    
    def cleanup_expired_data(self):
        """Clean up expired penalties and old data"""
        with self._lock:
            current_time = time.time()
            expired_penalties = [
                key for key, until in self._penalties.items()
                if current_time >= until
            ]
            
            for key in expired_penalties:
                del self._penalties[key]
            
            return len(expired_penalties)
    
    def start_background_cleanup(self, interval: int = 300):
        """Start background cleanup task"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._running = True
            self._cleanup_task = asyncio.create_task(self._background_cleanup(interval))
    
    def stop_background_cleanup(self):
        """Stop background cleanup task"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
    
    async def _background_cleanup(self, interval: int):
        """Background cleanup loop"""
        while self._running:
            try:
                cleaned = self.cleanup_expired_data()
                if cleaned > 0:
                    print(f"Cleaned {cleaned} expired penalties")
                
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Background cleanup error: {e}")
                await asyncio.sleep(interval)


class DistributedRateLimiter:
    """
    Distributed rate limiter using Redis or similar
    Placeholder implementation - would need actual Redis client
    """
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.local_limiter = RateLimiter()
    
    def is_allowed(self, key: str, tokens: int = 1) -> Tuple[bool, Dict[str, Any]]:
        """Check distributed rate limit"""
        if self.redis_client:
            # Implement Redis-based rate limiting
            # This is a placeholder - actual implementation would use Redis operations
            return self._redis_is_allowed(key, tokens)
        else:
            # Fallback to local rate limiting
            return self.local_limiter.is_allowed(key, tokens)
    
    def _redis_is_allowed(self, key: str, tokens: int) -> Tuple[bool, Dict[str, Any]]:
        """Redis-based rate limiting implementation"""
        # Placeholder for Redis implementation
        # Would use Redis INCR, EXPIRE, Lua scripts for atomic operations
        return True, {"reason": "redis_not_configured"}


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts based on system conditions
    """
    
    def __init__(self, base_limiter: RateLimiter):
        self.base_limiter = base_limiter
        self.load_factor = 1.0
        self.error_rate = 0.0
        self.adaptation_threshold = 0.1
    
    def update_system_load(self, load_factor: float):
        """Update system load factor (0.0 to 1.0)"""
        self.load_factor = max(0.0, min(1.0, load_factor))
    
    def update_error_rate(self, error_rate: float):
        """Update error rate (0.0 to 1.0)"""
        self.error_rate = max(0.0, min(1.0, error_rate))
    
    def is_allowed(self, key: str, tokens: int = 1) -> Tuple[bool, Dict[str, Any]]:
        """Check with adaptive limits"""
        # Calculate adjustment factor
        load_adjustment = 1.0 - (self.load_factor * 0.5)  # Reduce by up to 50% under high load
        error_adjustment = 1.0 - (self.error_rate * 0.7)  # Reduce by up to 70% under high error rate
        
        adjustment_factor = min(load_adjustment, error_adjustment)
        
        # Apply adjustment to tokens (make it harder to get tokens)
        adjusted_tokens = max(1, int(tokens / adjustment_factor))
        
        allowed, info = self.base_limiter.is_allowed(key, adjusted_tokens)
        
        # Add adaptation info
        info.update({
            "load_factor": self.load_factor,
            "error_rate": self.error_rate,
            "adjustment_factor": adjustment_factor,
            "adjusted_tokens": adjusted_tokens
        })
        
        return allowed, info


# Global rate limiter instance
rate_limiter = RateLimiter()

# Convenience functions
def add_rate_limit(key: str, max_requests: int, window_seconds: int, **kwargs):
    """Add rate limit with default token bucket algorithm"""
    config = RateLimitConfig(max_requests, window_seconds, **kwargs)
    rate_limiter.add_limit(key, config, "token_bucket")

def check_rate_limit(key: str, tokens: int = 1) -> Tuple[bool, Dict[str, Any]]:
    """Check rate limit for key"""
    return rate_limiter.is_allowed(key, tokens)

def get_rate_limit_status(key: str) -> Dict[str, Any]:
    """Get rate limit status for key"""
    return rate_limiter.get_status(key)
