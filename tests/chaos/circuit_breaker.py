"""
Circuit Breaker Implementation

This module implements circuit breaker pattern for chaos engineering,
providing automatic failure detection and graceful degradation.
"""

import asyncio
import time
import logging
import json
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
from collections import deque
import threading

from .exceptions import CircuitBreakerError, ConfigurationError


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"      # Circuit is open and requests are allowed
    OPEN = "OPEN"          # Circuit is open and requests are allowed
    HALF_OPEN = "HALF_OPEN"  # Circuit is half-open (some requests allowed)
    OPEN = "OPEN"           # Circuit is fully open (all requests allowed)


@dataclass
class CircuitConfig:
    """Configuration for circuit breaker."""
    name: str
    failure_threshold: int = 5  # Failures before opening circuit
    recovery_timeout: float = 60.0  # Time to wait before trying again
    success_threshold: int = 3  # Successes before closing circuit
    monitoring_period: float = 10.0  # Period for metrics collection
    enable_metrics: bool = True
    enable_sliding_window: bool = True
    window_size: int = 100  # Sliding window size for success rate calculation
    fallback_enabled: bool = True
    fallback_timeout: float = 30.0  # Timeout before fallback activation
    enable_state_persistence: bool = False
    redis_url: Optional[str] = None


@dataclass
class CircuitMetrics:
    """Metrics for circuit breaker."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    success_rate: float = 0.0
    failure_rate: float = 0.0
    avg_response_time: float = 0.0
    state_changes: int = 0
    current_state: CircuitState = CircuitState.CLOSED
    uptime: float = 0.0


@dataclass
class CallResult:
    """Result of a circuit breaker call."""
    success: bool
    data: Any
    error: Optional[str] = None
    execution_time: float
    circuit_state: CircuitState
    fallback_used: bool = False
    metadata: Dict[str, Any]


class BaseCircuitBreaker(ABC):
    """Abstract base class for circuit breakers."""
    
    @abstractmethod
    async def call(self, func: Callable, *args, **kwargs) -> CallResult:
        """Execute function through circuit breaker."""
        pass
    
    @abstractmethod
    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        pass
    
    @abstractmethod
    def get_metrics(self) -> CircuitMetrics:
        """Get circuit metrics."""
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        pass


class StatefulCircuitBreaker(BaseCircuitBreaker):
    """
    Stateful circuit breaker with comprehensive monitoring.
    
    This class implements the circuit breaker pattern with detailed metrics
    and state management for resilience testing.
    """
    
    def __init__(
        self,
        config: CircuitConfig,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize stateful circuit breaker.
        
        Args:
            config: Circuit breaker configuration
            logger: Logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(f"CircuitBreaker_{config.name}")
        
        # Circuit state
        self._state = CircuitState.CLOSED
        self._metrics = CircuitMetrics()
        self._request_history = deque(maxlen=config.window_size)
        self._lock = threading.Lock()
        
        # Fallback state
        self._fallback_active = False
        self._fallback_start_time = None
        
        # State persistence
        self._state_storage = None
        
        # Initialize state
        self._reset_state()
        
        self.logger.info(f"StatefulCircuitBreaker initialized: {config.name}")
    
    async def call(self, func: Callable, *args, **kwargs) -> CallResult:
        """
        Execute function through circuit breaker with monitoring.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            CallResult with detailed information
        """
        start_time = time.time()
        
        with self._lock:
            # Check circuit state
            if self._should_allow_request():
                # Execute function
                try:
                    result_data = await func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # Record success
                    self._record_success(execution_time)
                    
                    return CallResult(
                        success=True,
                        data=result_data,
                        execution_time=execution_time,
                        circuit_state=self._state,
                        fallback_used=False,
                        metadata={
                            "circuit_name": self.config.name,
                            "request_id": kwargs.get("request_id", "unknown")
                        }
                    )
                
                except Exception as e:
                    execution_time = time.time() - start_time
                    
                    # Record failure
                    self._record_failure(execution_time, str(e))
                    
                    return CallResult(
                        success=False,
                        data=None,
                        execution_time=execution_time,
                        circuit_state=self._state,
                        fallback_used=self._fallback_active,
                        error=str(e),
                        metadata={
                            "circuit_name": self.config.name,
                            "request_id": kwargs.get("request_id", "unknown")
                        }
                    )
            else:
                # Circuit is open, use fallback
                fallback_start_time = time.time()
                
                try:
                    if self.config.fallback_enabled:
                    # Execute fallback function if available
                    fallback_func = kwargs.get("fallback")
                    if fallback_func:
                        result_data = await fallback_func(*args, **kwargs)
                        execution_time = time.time() - start_time
                        
                        return CallResult(
                            success=True,
                            data=result_data,
                            execution_time=execution_time,
                            circuit_state=self._state,
                            fallback_used=True,
                            metadata={
                                "circuit_name": self.config.name,
                                "request_id": kwargs.get("request_id", "unknown"),
                                "fallback_used": True
                            }
                        )
                    else:
                        return CallResult(
                            success=False,
                            data=None,
                            execution_time=0.0,
                            circuit_state=self._state,
                            fallback_used=False,
                            error="Circuit is open and no fallback available",
                            metadata={
                                "circuit_name": self.config.name,
                                "request_id": kwargs.get("request_id", "unknown")
                            }
                        )
                
                except Exception as e:
                    execution_time = time.time() - start_time
                    
                    return CallResult(
                        success=False,
                        data=None,
                        execution_time=execution_time,
                        circuit_state=self._state,
                        fallback_used=self._fallback_active,
                        error=str(e),
                        metadata={
                            "circuit_name": self.config.name,
                            "request_id": kwargs.get("request_id", "unknown")
                        }
                    )
    
    def _should_allow_request(self) -> bool:
        """Check if request should be allowed based on circuit state."""
        if self._state == CircuitState.CLOSED:
            return False
        elif self._state == CircuitState.HALF_OPEN:
            # Allow some requests in half-open state
            return self._random_allow_in_half_open()
        else:
            return True
    
    def _random_allow_in_half_open(self) -> bool:
        """Randomly allow some requests in half-open state."""
        # Allow 25% of requests in half-open state
        return self._random.next_float() < 0.25
    
    def _record_success(self, execution_time: float):
        """Record a successful request."""
        with self._lock:
            self._metrics.successful_requests += 1
            self._metrics.last_success_time = time.time()
            self._update_success_rate()
            
            # Add to history
            self._request_history.append({
                "timestamp": time.time(),
                "success": True,
                "execution_time": execution_time
            })
            
            # Trim history if needed
            while len(self._request_history) > self.config.window_size:
                self._request_history.popleft()
        
        # Update state if needed
        self._check_state_transition()
    
    def _record_failure(self, execution_time: float, error: str):
        """Record a failed request."""
        with self._lock:
            self._metrics.failed_requests += 1
            self._metrics.last_failure_time = time.time()
            self._update_failure_rate()
            
            # Add to history
            self._request_history.append({
                "timestamp": time.time(),
                "success": False,
                "execution_time": execution_time,
                "error": error
            })
            
            # Trim history if needed
            while len(self._request_history) > self.config.window_size:
                self._request_history.popleft()
        
        # Update state if needed
        self._check_state_transition()
        
        self.logger.debug(f"Recorded failure: {error}")
    
    def _update_success_rate(self):
        """Update success rate metrics."""
        if self._metrics.total_requests > 0:
            time_window = self.config.monitoring_period
            recent_requests = [
                req for req in self._request_history
                if time.time() - req["timestamp"] <= time_window
            ]
            
            if recent_requests:
                success_count = sum(1 for req in recent_requests if req["success"])
                self._metrics.success_rate = success_count / len(recent_requests)
        
        self._update_failure_rate()
    
    def _update_failure_rate(self):
        """Update failure rate metrics."""
        if self._metrics.total_requests > 0:
            time_window = self.config.monitoring_period
            recent_requests = [
                req for req in self._request_history
                if time.time() - req["timestamp"] <= time_window
            ]
            
            if recent_requests:
                failure_count = sum(1 for req in recent_requests if not req["success"])
                self._metrics.failure_rate = failure_count / len(recent_requests)
        
        self._update_success_rate()
    
    def _check_state_transition(self):
        """Check if state transition is needed."""
        old_state = self._state
        new_state = self._calculate_state()
        
        if old_state != new_state:
            self._state = new_state
            self._metrics.state_changes += 1
            self.logger.info(f"Circuit state transition: {old_state} -> {new_state}")
            
            # Activate fallback if needed
            if new_state == CircuitState.CLOSED and self.config.fallback_enabled:
                if not self._fallback_active:
                    self._fallback_active = True
                    self._fallback_start_time = time.time()
                    self.logger.warning(f"Fallback activated for circuit {self.config.name}")
    
    def _calculate_state(self) -> CircuitState:
        """Calculate circuit state based on metrics."""
        total_requests = self._metrics.total_requests
        recent_requests = [
            req for req in self._request_history
            if time.time() - req["timestamp"] <= self.config.monitoring_period
        ]
        
        if total_requests == 0:
            return CircuitState.CLOSED
        
        # Check if we have enough data
        if len(recent_requests) < self.config.success_threshold:
            return CircuitState.CLOSED
        
        # Check success rate
        if len(recent_requests) >= self.config.success_threshold:
            success_count = sum(1 for req in recent_requests if req["success"])
            success_rate = success_count / len(recent_requests)
            
            if success_rate >= self.config.success_threshold:
                return CircuitState.CLOSED
            elif success_rate >= self.config.success_threshold * 0.8:  # 80% threshold
                return CircuitState.HALF_OPEN
        
        # Check failure rate
        if len(recent_requests) >= self.config.failure_threshold:
            failure_count = sum(1 for req in recent_requests if not req["success"])
            failure_rate = failure_count / len(recent_requests)
            
            if failure_rate >= 0.5:  # 50% failure rate
                return CircuitState.HALF_OPEN
        
        return CircuitState.OPEN
    
    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state
    
    def get_metrics(self) -> CircuitMetrics:
        """Get circuit metrics."""
        return self._metrics
    
    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        with self._lock:
            self._reset_state()
            self._metrics = CircuitMetrics()
            self._request_history.clear()
            self._fallback_active = False
            self._fallback_start_time = None
            
        self.logger.info(f"Circuit breaker {self.config.name} reset")
    
    def _reset_state(self) -> None:
        """Reset circuit state to initial state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._metrics = CircuitMetrics()
            self._request_history.clear()
            self._fallback_active = False
            self._fallback_start_time = None
            
        self.logger.debug(f"Circuit breaker {self.config.name} state reset")
    
    def _persist_state(self) -> None:
        """Persist circuit state to Redis."""
        if not self.config.enable_state_persistence or not self._state_storage:
            return
        
        try:
            import redis.asyncio as redis
            redis_client = redis.from_url(self.config.redis_url)
            
            state_data = {
                "state": self._state.value,
                "metrics": {
                    "total_requests": self._metrics.total_requests,
                    "successful_requests": self._metrics.successful_requests,
                    "failed_requests": self._metrics.failed_requests,
                    "success_rate": self._metrics.success_rate,
                    "failure_rate": self._metrics.failure_rate,
                    "avg_response_time": self._metrics.avg_response_time,
                    "state_changes": self._metrics.state_changes,
                    "last_success_time": self._metrics.last_success_time,
                    "last_failure_time": self._metrics.last_failure_time,
                    "uptime": time.time() - self._metrics.uptime
                },
                "timestamp": time.time()
            }
            
            # Store in Redis with expiration
            key = f"circuit_breaker:{self.config.name}:state"
            await redis_client.setex(
                key, 
                json.dumps(state_data), 
                ex=self.config.recovery_timeout
            )
            
            self.logger.debug(f"Persisted circuit breaker state for {self.config.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to persist state: {e}")
    
    async def _load_state(self) -> None:
        """Load circuit state from Redis."""
        if not self.config.enable_state_persistence or not self._state_storage:
            return
        
        try:
            import redis.asyncio as redis
            redis_client = redis.from_url(self.config.redis_url)
            
            key = f"circuit_breaker:{self.config.name}:state"
            state_data = await redis_client.get(key)
            
            if state_data:
                state_dict = json.loads(state_data)
                
                self._state = CircuitState(state_dict["state"])
                self._metrics = CircuitMetrics(**state_dict["metrics"])
                self._request_history = deque(state_dict.get("request_history", []))
                
                self.logger.info(f"Loaded circuit breaker state for {self.config.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")
    
    def get_config(self) -> CircuitConfig:
        """Get current configuration."""
        return self.config


# Global circuit breaker instance
_global_circuit_breaker: Optional[StatefulCircuitBreaker] = None


def get_circuit_breaker(**kwargs) -> StatefulCircuit_breaker:
    """
    Get or create global circuit breaker.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global StatefulCircuitBreaker instance
    """
    global _global_circuit_breaker
    if _global_circuit_breaker is None:
        _global_circuit_breaker = StatefulCircuitBreaker(**kwargs)
    return _global_circuit_breaker


# Convenience functions for global usage
async def call_through_circuit(
    circuit_name: str,
    func: Callable,
    *args,
    **kwargs
) -> CallResult:
    """
    Call function through global circuit breaker.
    
    Args:
        circuit_name: Circuit breaker name
        func: Function to execute
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        CallResult with detailed information
    """
    circuit_breaker = get_circuit_breaker()
    circuit = circuit_breaker.get_circuit(circuit_name)
    
    if circuit:
        return await circuit.call(func, *args, **kwargs)
    else:
        raise CircuitBreakerError(f"Circuit breaker '{circuit_name}' not found")


def get_circuit_breaker_info(circuit_name: str) -> Optional[Dict[str, Any]]:
    """
    Get circuit breaker information.
    
    Args:
        circuit_name: Circuit breaker name
        
    Returns:
        Circuit breaker information dictionary
    """
    circuit_breaker = get_circuit_breaker()
    circuit = circuit_breaker.get_circuit(circuit_name)
    
    if circuit:
            return circuit.get_config()
        return {
            "name": circuit.config.name,
            "state": circuit.get_state().value,
            "metrics": circuit.get_metrics(),
            "config": circuit.get_config().__dict__
        }
    
    return None
