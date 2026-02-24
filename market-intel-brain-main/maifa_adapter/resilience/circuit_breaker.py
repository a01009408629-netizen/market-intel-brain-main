"""
Distributed Circuit Breaker Implementation

This module provides an async circuit breaker that manages states (Open, Half-Open, Closed)
in Redis for distributed systems with atomic operations.
"""

import asyncio
import time
import logging
from enum import Enum
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
import redis.asyncio as redis

from ..core.exceptions import TransientAdapterError


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


class CircuitBreakerOpenError(TransientAdapterError):
    """Raised when circuit breaker is open"""
    
    def __init__(
        self,
        adapter_name: str,
        failure_count: int,
        recovery_time: float,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        if message is None:
            message = f"Circuit breaker is open for adapter {adapter_name}"
        
        super().__init__(
            message=message,
            adapter_name=adapter_name,
            retry_after=int(recovery_time),
            context={
                "failure_count": failure_count,
                "recovery_time": recovery_time,
                "circuit_state": CircuitState.OPEN.value,
                **(context or {})
            }
        )


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5          # Failures before opening
    recovery_time: float = 60.0         # Seconds to wait before trying again
    success_threshold: int = 3          # Successes needed to close in HALF_OPEN
    timeout: Optional[float] = None       # Request timeout
    monitoring_period: float = 300.0     # Period to consider for failures


class DistributedCircuitBreaker:
    """
    Redis-backed distributed circuit breaker for async operations.
    
    Manages circuit state in Redis for distributed consistency across
    multiple service instances with atomic operations.
    """
    
    def __init__(
        self,
        adapter_name: str,
        redis_client: redis.Redis,
        config: Optional[CircuitBreakerConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.adapter_name = adapter_name
        self.redis = redis_client
        self.config = config or CircuitBreakerConfig()
        self.logger = logger or logging.getLogger(f"CircuitBreaker.{adapter_name}")
        
        # Redis keys for distributed state management
        self.state_key = f"circuit_breaker:{adapter_name}:state"
        self.failure_count_key = f"circuit_breaker:{adapter_name}:failures"
        self.success_count_key = f"circuit_breaker:{adapter_name}:successes"
        self.last_failure_time_key = f"circuit_breaker:{adapter_name}:last_failure"
        self.last_success_time_key = f"circuit_breaker:{adapter_name}:last_success"
        self.lock_key = f"circuit_breaker:{adapter_name}:lock"
        
        # Lua script for atomic state transitions
        self._init_lua_scripts()
    
    def _init_lua_scripts(self):
        """Initialize Redis Lua scripts for atomic operations"""
        
        # Atomic failure recording script
        self.record_failure_script = """
        local state_key = KEYS[1]
        local failure_count_key = KEYS[2]
        local last_failure_key = KEYS[3]
        local failure_threshold = tonumber(ARGV[1])
        local recovery_time = tonumber(ARGV[2])
        local current_time = tonumber(ARGV[3])
        
        local state = redis.call('GET', state_key)
        if not state then
            state = 'closed'
        end
        
        local failure_count = tonumber(redis.call('INCR', failure_count_key)) or 1
        
        -- Set last failure time
        redis.call('SET', last_failure_key, current_time, 'EX', 3600)
        
        -- Check if we should open circuit
        if state == 'closed' and failure_count >= failure_threshold then
            redis.call('SET', state_key, 'open', 'EX', 3600)
            return {state, 'open', failure_count}
        elseif state == 'half_open' then
            redis.call('SET', state_key, 'open', 'EX', 3600)
            return {state, 'open', failure_count}
        else
            return {state, state, failure_count}
        end
        """
        
        # Atomic success recording script
        self.record_success_script = """
        local state_key = KEYS[1]
        local failure_count_key = KEYS[2]
        local success_count_key = KEYS[3]
        local last_success_key = KEYS[4]
        local success_threshold = tonumber(ARGV[1])
        local current_time = tonumber(ARGV[2])
        
        local state = redis.call('GET', state_key)
        if not state then
            state = 'closed'
        end
        
        local success_count = tonumber(redis.call('INCR', success_count_key)) or 1
        
        -- Set last success time
        redis.call('SET', last_success_key, current_time, 'EX', 3600)
        
        -- Check if we should close circuit
        if state == 'half_open' and success_count >= success_threshold then
            redis.call('SET', state_key, 'closed', 'EX', 3600)
            redis.call('DEL', failure_count_key)
            redis.call('DEL', success_count_key)
            return {state, 'closed', success_count}
        elseif state == 'closed' then
            redis.call('DEL', failure_count_key)
            return {state, 'closed', success_count}
        else
            return {state, state, success_count}
        end
        """
        
        # State checking script
        self.check_state_script = """
        local state_key = KEYS[1]
        local last_failure_key = KEYS[2]
        local recovery_time = tonumber(ARGV[1])
        local current_time = tonumber(ARGV[2])
        
        local state = redis.call('GET', state_key)
        if not state then
            return 'closed'
        end
        
        -- Check if we should transition from OPEN to HALF_OPEN
        if state == 'open' then
            local last_failure = tonumber(redis.call('GET', last_failure_key))
            if last_failure and (current_time - last_failure) >= recovery_time then
                redis.call('SET', state_key, 'half_open', 'EX', 3600)
                redis.call('DEL', KEYS[3]) -- Reset success count
                return 'half_open'
            end
        end
        
        return state
        """
    
    async def get_state(self) -> CircuitState:
        """Get current circuit state from Redis"""
        try:
            result = await self.redis.eval(
                self.check_state_script,
                2,  # Number of keys
                self.state_key,
                self.last_failure_time_key,
                self.success_count_key,  # For reset in half_open
                self.config.recovery_time,
                time.time()
            )
            
            return CircuitState(result)
        except Exception as e:
            self.logger.error(f"Error getting circuit state: {e}")
            return CircuitState.CLOSED
    
    async def can_execute(self) -> bool:
        """Check if execution is allowed"""
        state = await self.get_state()
        return state != CircuitState.OPEN
    
    async def record_failure(self) -> Dict[str, Any]:
        """Record a failure using atomic Redis operation"""
        try:
            result = await self.redis.eval(
                self.record_failure_script,
                3,  # Number of keys
                self.state_key,
                self.failure_count_key,
                self.last_failure_time_key,
                self.config.failure_threshold,
                self.config.recovery_time,
                time.time()
            )
            
            old_state, new_state, failure_count = result
            
            self.logger.warning(
                f"Circuit breaker failure: {old_state} -> {new_state}, "
                f"failures: {failure_count}"
            )
            
            return {
                "old_state": old_state,
                "new_state": new_state,
                "failure_count": failure_count
            }
            
        except Exception as e:
            self.logger.error(f"Error recording failure: {e}")
            return {"error": str(e)}
    
    async def record_success(self) -> Dict[str, Any]:
        """Record a success using atomic Redis operation"""
        try:
            result = await self.redis.eval(
                self.record_success_script,
                4,  # Number of keys
                self.state_key,
                self.failure_count_key,
                self.success_count_key,
                self.last_success_time_key,
                self.config.success_threshold,
                time.time()
            )
            
            old_state, new_state, success_count = result
            
            if old_state != new_state:
                self.logger.info(
                    f"Circuit breaker state change: {old_state} -> {new_state}, "
                    f"successes: {success_count}"
                )
            
            return {
                "old_state": old_state,
                "new_state": new_state,
                "success_count": success_count
            }
            
        except Exception as e:
            self.logger.error(f"Error recording success: {e}")
            return {"error": str(e)}
    
    async def execute(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if not await self.can_execute():
            state = await self.get_state()
            metrics = await self.get_metrics()
            
            raise CircuitBreakerOpenError(
                adapter_name=self.adapter_name,
                failure_count=metrics.get("failure_count", 0),
                recovery_time=self.config.recovery_time
            )
        
        try:
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, func, *args, **kwargs)
            
            # Record success
            await self.record_success()
            return result
            
        except Exception as e:
            # Record failure
            await self.record_failure()
            raise
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics from Redis"""
        try:
            state = await self.get_state()
            
            # Get counts from Redis
            failure_count = await self.redis.get(self.failure_count_key)
            success_count = await self.redis.get(self.success_count_key)
            last_failure = await self.redis.get(self.last_failure_time_key)
            last_success = await self.redis.get(self.last_success_time_key)
            
            return {
                "adapter_name": self.adapter_name,
                "state": state.value,
                "failure_count": int(failure_count) if failure_count else 0,
                "success_count": int(success_count) if success_count else 0,
                "last_failure_time": float(last_failure) if last_failure else None,
                "last_success_time": float(last_success) if last_success else None,
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "recovery_time": self.config.recovery_time,
                    "success_threshold": self.config.success_threshold,
                    "timeout": self.config.timeout,
                    "monitoring_period": self.config.monitoring_period
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting metrics: {e}")
            return {"error": str(e)}
    
    async def reset(self):
        """Reset circuit breaker to CLOSED state"""
        try:
            # Delete all circuit breaker keys
            keys = [
                self.state_key,
                self.failure_count_key,
                self.success_count_key,
                self.last_failure_time_key,
                self.last_success_time_key
            ]
            
            await self.redis.delete(*keys)
            
            self.logger.info(f"Circuit breaker reset for {self.adapter_name}")
            
        except Exception as e:
            self.logger.error(f"Error resetting circuit breaker: {e}")


# Circuit breaker registry for managing multiple instances
class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self._breakers: Dict[str, DistributedCircuitBreaker] = {}
        self.logger = logging.getLogger("CircuitBreakerRegistry")
    
    def get_breaker(
        self,
        adapter_name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> DistributedCircuitBreaker:
        """Get or create circuit breaker for adapter"""
        if adapter_name not in self._breakers:
            self._breakers[adapter_name] = DistributedCircuitBreaker(
                adapter_name=adapter_name,
                redis_client=self.redis_client,
                config=config
            )
        
        return self._breakers[adapter_name]
    
    async def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers"""
        metrics = {}
        for adapter_name, breaker in self._breakers.items():
            try:
                metrics[adapter_name] = await breaker.get_metrics()
            except Exception as e:
                self.logger.error(f"Error getting metrics for {adapter_name}: {e}")
                metrics[adapter_name] = {"error": str(e)}
        
        return metrics
    
    async def reset_all(self):
        """Reset all circuit breakers"""
        reset_tasks = []
        for breaker in self._breakers.values():
            reset_tasks.append(breaker.reset())
        
        if reset_tasks:
            await asyncio.gather(*reset_tasks, return_exceptions=True)


# Decorator for circuit breaker protection
def circuit_breaker(
    adapter_name: str,
    redis_client: redis.Redis,
    config: Optional[CircuitBreakerConfig] = None
):
    """
    Decorator for adding circuit breaker protection to functions.
    
    Args:
        adapter_name: Name of the adapter
        redis_client: Redis client for distributed state
        config: Circuit breaker configuration
        
    Returns:
        Decorated function with circuit breaker protection
    """
    def decorator(func: Callable):
        # Create circuit breaker instance
        breaker = DistributedCircuitBreaker(
            adapter_name=adapter_name,
            redis_client=redis_client,
            config=config
        )
        
        async def async_wrapper(*args, **kwargs):
            return await breaker.execute(func, *args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            # For sync functions, run in executor
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(breaker.execute(func, *args, **kwargs))
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
