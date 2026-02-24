import asyncio
import time
import logging
from enum import Enum
from typing import Optional, Dict, Any, Set
from dataclasses import dataclass
import redis.asyncio as redis


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_time_sec: int = 60
    success_threshold: int = 3  # Successes needed to close circuit in HALF_OPEN
    timeout_sec: Optional[float] = None


class DistributedCircuitBreaker:
    """
    Redis-based distributed circuit breaker for multi-node environments.
    Thread-safe and async-safe implementation.
    """
    
    def __init__(
        self,
        provider_name: str,
        redis_client: redis.Redis,
        config: Optional[CircuitBreakerConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.provider_name = provider_name
        self.redis = redis_client
        self.config = config or CircuitBreakerConfig()
        self.logger = logger or logging.getLogger(f"CircuitBreaker.{provider_name}")
        
        # Redis keys
        self.state_key = f"circuit_breaker:{provider_name}:state"
        self.failure_count_key = f"circuit_breaker:{provider_name}:failures"
        self.success_count_key = f"circuit_breaker:{provider_name}:successes"
        self.last_failure_key = f"circuit_breaker:{provider_name}:last_failure"
        self.lock_key = f"circuit_breaker:{provider_name}:lock"
    
    async def get_state(self) -> CircuitState:
        """Get current circuit state from Redis"""
        state_str = await self.redis.get(self.state_key)
        return CircuitState(state_str) if state_str else CircuitState.CLOSED
    
    async def set_state(self, state: CircuitState) -> None:
        """Set circuit state in Redis"""
        await self.redis.set(self.state_key, state.value)
        self.logger.info(f"Circuit breaker for {self.provider_name} changed to {state.value}")
    
    async def get_failure_count(self) -> int:
        """Get current failure count"""
        count = await self.redis.get(self.failure_count_key)
        return int(count) if count else 0
    
    async def increment_failure_count(self) -> int:
        """Increment failure count and return new count"""
        new_count = await self.redis.incr(self.failure_count_key)
        await self.redis.set(self.last_failure_key, time.time())
        return new_count
    
    async def reset_failure_count(self) -> None:
        """Reset failure count"""
        await self.redis.delete(self.failure_count_key)
    
    async def get_success_count(self) -> int:
        """Get current success count in HALF_OPEN state"""
        count = await self.redis.get(self.success_count_key)
        return int(count) if count else 0
    
    async def increment_success_count(self) -> int:
        """Increment success count and return new count"""
        return await self.redis.incr(self.success_count_key)
    
    async def reset_success_count(self) -> None:
        """Reset success count"""
        await self.redis.delete(self.success_count_key)
    
    async def acquire_lock(self, timeout: float = 5.0) -> bool:
        """Acquire distributed lock for atomic operations"""
        return await self.redis.set(self.lock_key, "1", nx=True, ex=timeout)
    
    async def release_lock(self) -> None:
        """Release distributed lock"""
        await self.redis.delete(self.lock_key)
    
    async def can_execute(self) -> bool:
        """Check if execution is allowed based on circuit state"""
        state = await self.get_state()
        
        if state == CircuitState.CLOSED:
            return True
        
        if state == CircuitState.OPEN:
            # Check if recovery time has passed
            last_failure = await self.redis.get(self.last_failure_key)
            if last_failure and (time.time() - float(last_failure)) > self.config.recovery_time_sec:
                await self.set_state(CircuitState.HALF_OPEN)
                await self.reset_success_count()
                return True
            return False
        
        if state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    async def record_success(self) -> None:
        """Record successful execution"""
        acquired = await self.acquire_lock()
        if not acquired:
            return  # Skip if another instance is handling state changes
        
        try:
            state = await self.get_state()
            
            if state == CircuitState.CLOSED:
                # Reset failure count on success
                await self.reset_failure_count()
            
            elif state == CircuitState.HALF_OPEN:
                # Increment success count
                success_count = await self.increment_success_count()
                
                # Close circuit if enough successes
                if success_count >= self.config.success_threshold:
                    await self.set_state(CircuitState.CLOSED)
                    await self.reset_failure_count()
                    await self.reset_success_count()
                    self.logger.info(f"Circuit breaker for {self.provider_name} closed after {success_count} successes")
        
        finally:
            await self.release_lock()
    
    async def record_failure(self, error: Exception) -> None:
        """Record failed execution"""
        acquired = await self.acquire_lock()
        if not acquired:
            return  # Skip if another instance is handling state changes
        
        try:
            state = await self.get_state()
            
            if state == CircuitState.CLOSED:
                # Increment failure count
                failure_count = await self.increment_failure_count()
                
                # Open circuit if threshold reached
                if failure_count >= self.config.failure_threshold:
                    await self.set_state(CircuitState.OPEN)
                    self.logger.error(f"Circuit breaker for {self.provider_name} opened after {failure_count} failures")
            
            elif state == CircuitState.HALF_OPEN:
                # Open circuit immediately on failure in HALF_OPEN
                await self.set_state(CircuitState.OPEN)
                await self.reset_success_count()
                self.logger.error(f"Circuit breaker for {self.provider_name} re-opened due to failure in HALF_OPEN state")
        
        finally:
            await self.release_lock()
    
    async def execute(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if not await self.can_execute():
            raise Exception(f"Circuit breaker is OPEN for provider {self.provider_name}")
        
        try:
            if self.config.timeout_sec:
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.config.timeout_sec)
            else:
                result = await func(*args, **kwargs)
            
            await self.record_success()
            return result
        
        except Exception as e:
            await self.record_failure(e)
            raise
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        return {
            "provider_name": self.provider_name,
            "state": (await self.get_state()).value,
            "failure_count": await self.get_failure_count(),
            "success_count": await self.get_success_count(),
            "last_failure": await self.redis.get(self.last_failure_key),
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_time_sec": self.config.recovery_time_sec,
                "success_threshold": self.config.success_threshold,
                "timeout_sec": self.config.timeout_sec
            }
        }


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self._breakers: Dict[str, DistributedCircuitBreaker] = {}
    
    def get_breaker(
        self,
        provider_name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> DistributedCircuitBreaker:
        """Get or create circuit breaker for provider"""
        if provider_name not in self._breakers:
            self._breakers[provider_name] = DistributedCircuitBreaker(
                provider_name=provider_name,
                redis_client=self.redis,
                config=config
            )
        return self._breakers[provider_name]
    
    async def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers"""
        metrics = {}
        for provider_name, breaker in self._breakers.items():
            metrics[provider_name] = await breaker.get_metrics()
        return metrics
