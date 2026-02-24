import asyncio
import time
import logging
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass
import json
import redis.asyncio as redis

from .error_contract_v2 import ProviderBaseError


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


class CircuitBreakerOpenError(ProviderBaseError):
    """Raised when circuit breaker is open"""
    
    def __init__(
        self,
        provider_name: str,
        failure_count: int,
        recovery_time: float,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        if message is None:
            message = f"Circuit breaker is open for provider {provider_name}"
        
        super().__init__(
            provider_name=provider_name,
            message=message,
            status_code=503,
            suggested_action="Wait for circuit to recover or check provider status",
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


class CircuitBreakerState:
    """Thread-safe circuit breaker state management"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_success_time: Optional[float] = None
        self._lock = asyncio.Lock()
    
    async def get_state(self) -> CircuitState:
        """Get current circuit state"""
        async with self._lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if (self._state == CircuitState.OPEN and 
                self._last_failure_time and 
                time.time() - self._last_failure_time >= self.config.recovery_time):
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                return CircuitState.HALF_OPEN
            
            return self._state
    
    async def can_execute(self) -> bool:
        """Check if execution is allowed"""
        state = await self.get_state()
        return state != CircuitState.OPEN
    
    async def record_success(self):
        """Record a successful execution"""
        async with self._lock:
            self._last_success_time = time.time()
            
            if self._state == CircuitState.CLOSED:
                # Reset failure count on success in CLOSED state
                self._failure_count = 0
            
            elif self._state == CircuitState.HALF_OPEN:
                # Increment success count in HALF_OPEN state
                self._success_count += 1
                
                # Close circuit if enough successes
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
    
    async def record_failure(self):
        """Record a failed execution"""
        async with self._lock:
            self._last_failure_time = time.time()
            self._failure_count += 1
            
            if self._state == CircuitState.CLOSED:
                # Open circuit if threshold reached
                if self._failure_count >= self.config.failure_threshold:
                    self._state = CircuitState.OPEN
            
            elif self._state == CircuitState.HALF_OPEN:
                # Open circuit immediately on failure in HALF_OPEN
                self._state = CircuitState.OPEN
                self._success_count = 0
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        return {
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time,
            "last_success_time": self._last_success_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_time": self.config.recovery_time,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout,
                "monitoring_period": self.config.monitoring_period
            }
        }


class RedisCircuitBreakerState:
    """Redis-backed circuit breaker state for distributed systems"""
    
    def __init__(
        self,
        provider_name: str,
        redis_client: redis.Redis,
        config: CircuitBreakerConfig,
        logger: Optional[logging.Logger] = None
    ):
        self.provider_name = provider_name
        self.redis = redis_client
        self.config = config
        self.logger = logger or logging.getLogger(f"CircuitBreaker.{provider_name}")
        
        # Redis keys
        self.state_key = f"circuit_breaker:{provider_name}:state"
        self.failure_count_key = f"circuit_breaker:{provider_name}:failures"
        self.success_count_key = f"circuit_breaker:{provider_name}:successes"
        self.last_failure_key = f"circuit_breaker:{provider_name}:last_failure"
        self.last_success_key = f"circuit_breaker:{provider_name}:last_success"
        self.lock_key = f"circuit_breaker:{provider_name}:lock"
    
    async def _get_redis_value(self, key: str, default: Any = None) -> Any:
        """Get value from Redis with error handling"""
        try:
            value = await self.redis.get(key)
            if value is None:
                return default
            
            # Try to parse as JSON first, then as int/float
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                try:
                    return int(value)
                except ValueError:
                    try:
                        return float(value)
                    except ValueError:
                        return value
        except Exception as e:
            self.logger.warning(f"Redis get error for key {key}: {e}")
            return default
    
    async def _set_redis_value(self, key: str, value: Any, ex: Optional[int] = None):
        """Set value in Redis with error handling"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif not isinstance(value, str):
                value = str(value)
            
            await self.redis.set(key, value, ex=ex)
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
    
    async def get_state(self) -> CircuitState:
        """Get current circuit state from Redis"""
        try:
            state_str = await self._get_redis_value(self.state_key)
            state = CircuitState(state_str) if state_str else CircuitState.CLOSED
            
            # Check if we should transition from OPEN to HALF_OPEN
            if (state == CircuitState.OPEN):
                last_failure = await self._get_redis_value(self.last_failure_key)
                if last_failure and time.time() - last_failure >= self.config.recovery_time:
                    await self._set_state(CircuitState.HALF_OPEN)
                    await self._set_redis_value(self.success_count_key, 0)
                    return CircuitState.HALF_OPEN
            
            return state
        
        except Exception as e:
            self.logger.error(f"Error getting circuit state: {e}")
            return CircuitState.CLOSED
    
    async def _set_state(self, state: CircuitState):
        """Set circuit state in Redis"""
        await self._set_redis_value(self.state_key, state.value, ex=3600)  # 1 hour TTL
    
    async def can_execute(self) -> bool:
        """Check if execution is allowed"""
        state = await self.get_state()
        return state != CircuitState.OPEN
    
    async def record_success(self):
        """Record a successful execution"""
        if not await self._acquire_lock():
            return  # Skip if another instance is handling state changes
        
        try:
            current_time = time.time()
            await self._set_redis_value(self.last_success_key, current_time, ex=3600)
            
            state = await self.get_state()
            if state == CircuitState.CLOSED:
                # Reset failure count on success in CLOSED state
                await self.redis.delete(self.failure_count_key)
            
            elif state == CircuitState.HALF_OPEN:
                # Increment success count in HALF_OPEN state
                success_count = await self._get_redis_value(self.success_count_key, 0) + 1
                await self._set_redis_value(self.success_count_key, success_count)
                
                # Close circuit if enough successes
                if success_count >= self.config.success_threshold:
                    await self._set_state(CircuitState.CLOSED)
                    await self.redis.delete(self.failure_count_key)
                    await self.redis.delete(self.success_count_key)
        
        finally:
            await self._release_lock()
    
    async def record_failure(self):
        """Record a failed execution"""
        if not await self._acquire_lock():
            return  # Skip if another instance is handling state changes
        
        try:
            current_time = time.time()
            await self._set_redis_value(self.last_failure_key, current_time, ex=3600)
            
            # Increment failure count
            failure_count = await self._get_redis_value(self.failure_count_key, 0) + 1
            await self._set_redis_value(self.failure_count_key, failure_count, ex=3600)
            
            state = await self.get_state()
            if state == CircuitState.CLOSED:
                # Open circuit if threshold reached
                if failure_count >= self.config.failure_threshold:
                    await self._set_state(CircuitState.OPEN)
            
            elif state == CircuitState.HALF_OPEN:
                # Open circuit immediately on failure in HALF_OPEN
                await self._set_state(CircuitState.OPEN)
                await self.redis.delete(self.success_count_key)
        
        finally:
            await self._release_lock()
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics from Redis"""
        try:
            return {
                "provider_name": self.provider_name,
                "state": (await self.get_state()).value,
                "failure_count": await self._get_redis_value(self.failure_count_key, 0),
                "success_count": await self._get_redis_value(self.success_count_key, 0),
                "last_failure_time": await self._get_redis_value(self.last_failure_key),
                "last_success_time": await self._get_redis_value(self.last_success_key),
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "recovery_time": self.config.recovery_time,
                    "success_threshold": self.config.success_threshold,
                    "timeout": self.config.timeout,
                    "monitoring_period": self.config.monitoring_period
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting circuit metrics: {e}")
            return {"error": str(e)}


class CircuitBreaker:
    """
    Circuit breaker with Redis backend and in-memory fallback.
    
    Provides fault tolerance for external service calls by automatically
    failing fast when a service is experiencing issues.
    """
    
    def __init__(
        self,
        provider_name: str,
        redis_client: Optional[redis.Redis] = None,
        config: Optional[CircuitBreakerConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.provider_name = provider_name
        self.config = config or CircuitBreakerConfig()
        self.logger = logger or logging.getLogger(f"CircuitBreaker.{provider_name}")
        
        # Choose backend based on Redis availability
        if redis_client:
            self._state = RedisCircuitBreakerState(
                provider_name=provider_name,
                redis_client=redis_client,
                config=self.config,
                logger=self.logger
            )
            self._backend = "redis"
        else:
            self._state = CircuitBreakerState(self.config)
            self._backend = "memory"
        
        self.logger.info(f"Circuit breaker initialized for {provider_name} using {self._backend} backend")
    
    async def can_execute(self) -> bool:
        """Check if execution is allowed"""
        return await self._state.can_execute()
    
    async def execute(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if not await self.can_execute():
            metrics = await self.get_metrics()
            raise CircuitBreakerOpenError(
                provider_name=self.provider_name,
                failure_count=metrics.get("failure_count", 0),
                recovery_time=self.config.recovery_time
            )
        
        try:
            # Execute function with timeout if configured
            if self.config.timeout:
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.config.timeout)
            else:
                result = await func(*args, **kwargs)
            
            await self.record_success()
            return result
        
        except Exception as e:
            await self.record_failure()
            raise
    
    async def record_success(self):
        """Record a successful execution"""
        await self._state.record_success()
    
    async def record_failure(self):
        """Record a failed execution"""
        await self._state.record_failure()
    
    async def get_state(self) -> CircuitState:
        """Get current circuit state"""
        return await self._state.get_state()
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        metrics = await self._state.get_metrics()
        metrics["backend"] = self._backend
        return metrics
    
    async def reset(self):
        """Reset circuit breaker to CLOSED state"""
        if hasattr(self._state, '_lock'):
            async with self._state._lock:
                self._state._state = CircuitState.CLOSED
                self._state._failure_count = 0
                self._state._success_count = 0
                self._state._last_failure_time = None
                self._state._last_success_time = None
        elif hasattr(self._state, '_set_state'):
            await self._state._set_state(CircuitState.CLOSED)
            await self._state.redis.delete(self._state.failure_count_key)
            await self._state.redis.delete(self._state.success_count_key)
        
        self.logger.info(f"Circuit breaker reset for {self.provider_name}")


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self._breakers: Dict[str, CircuitBreaker] = {}
        self.logger = logging.getLogger("CircuitBreakerRegistry")
    
    def get_breaker(
        self,
        provider_name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get or create circuit breaker for provider"""
        if provider_name not in self._breakers:
            self._breakers[provider_name] = CircuitBreaker(
                provider_name=provider_name,
                redis_client=self.redis_client,
                config=config
            )
        
        return self._breakers[provider_name]
    
    async def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers"""
        metrics = {}
        for provider_name, breaker in self._breakers.items():
            try:
                metrics[provider_name] = await breaker.get_metrics()
            except Exception as e:
                self.logger.error(f"Error getting metrics for {provider_name}: {e}")
                metrics[provider_name] = {"error": str(e)}
        
        return metrics
    
    async def close_all(self):
        """Close all circuit breakers"""
        for breaker in self._breakers.values():
            await breaker.reset()
