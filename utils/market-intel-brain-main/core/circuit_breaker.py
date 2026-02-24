"""
MAIFA v3 Circuit Breakers & Retry System
Intelligent circuit breaker pattern with exponential backoff and comprehensive logging
"""

import asyncio
import time
import json
import logging
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import random
import math

from core.distributed_state import distributed_state_manager
from utils.logger import get_logger
from utils.helpers import TimeHelper

logger = get_logger("circuit_breaker")

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, blocking calls
    HALF_OPEN = "half_open"  # Testing if service has recovered

class FailureType(Enum):
    TIMEOUT = "timeout"
    EXCEPTION = "exception"
    RATE_LIMIT = "rate_limit"
    NETWORK_ERROR = "network_error"
    SERVICE_UNAVAILABLE = "service_unavailable"

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5           # Failures before opening
    success_threshold: int = 3           # Successes to close circuit
    timeout: float = 60.0               # Seconds to wait before trying again
    recovery_timeout: float = 30.0         # Time in half-open state
    max_retries: int = 3                 # Maximum retry attempts
    base_delay: float = 0.1               # Base delay for exponential backoff
    max_delay: float = 10.0               # Maximum delay
    jitter: bool = True                     # Add randomness to delay
    metrics_window: int = 100              # Size of metrics window

@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_attempts: int = 3
    base_delay: float = 0.1
    max_delay: float = 5.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on: List[Exception] = None

@dataclass
class CircuitMetrics:
    """Circuit breaker performance metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeouts: int = 0
    circuit_opens: int = 0
    circuit_closes: int = 0
    retry_attempts: int = 0
    avg_response_time: float = 0.0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0

class CircuitBreaker:
    """
    Advanced circuit breaker with intelligent retry and comprehensive monitoring
    
    Features:
    - State machine (CLOSED → OPEN → HALF_OPEN → CLOSED)
    - Exponential backoff with jitter
    - Failure type classification
    - Performance metrics tracking
    - Distributed state synchronization
    - Automatic recovery detection
    """
    
    def __init__(self, 
                 name: str,
                 config: CircuitBreakerConfig = None,
                 retry_config: RetryConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.retry_config = retry_config or RetryConfig()
        self.logger = get_logger(f"CircuitBreaker.{name}")
        
        # Circuit state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.last_state_change = time.time()
        
        # Metrics
        self.metrics = CircuitMetrics()
        self.request_history: List[Dict[str, Any]] = []
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def call(self, 
                    func: Callable,
                    *args,
                    timeout: Optional[float] = None,
                    **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args: Function arguments
            timeout: Override timeout
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or raises CircuitBreakerOpenException
        """
        start_time = time.time()
        
        async with self._lock:
            # Check circuit state
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.logger.info(f"🔄 Circuit {self.name} transitioning to HALF_OPEN")
                    await self._log_state_change("OPEN", "HALF_OPEN")
                else:
                    self.metrics.total_requests += 1
                    self.logger.warning(f"⚠️ Circuit {self.name} is OPEN, blocking call")
                    raise CircuitBreakerOpenException(f"Circuit {self.name} is open")
            
            # Execute with retry logic
            return await self._execute_with_retry(func, args, kwargs, timeout, start_time)
    
    async def _execute_with_retry(self, 
                                  func: Callable,
                                  args: tuple,
                                  kwargs: dict,
                                  timeout: Optional[float],
                                  start_time: float) -> Any:
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(self.retry_config.max_attempts):
            try:
                # Execute function
                if timeout:
                    result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                else:
                    result = await func(*args, **kwargs)
                
                # Success - record metrics and update state
                await self._record_success(time.time() - start_time)
                
                return result
                
            except Exception as e:
                last_exception = e
                failure_type = self._classify_failure(e)
                
                # Record failure
                await self._record_failure(failure_type, time.time() - start_time)
                
                # Check if we should retry
                if attempt < self.retry_config.max_attempts - 1:
                    if self._should_retry(e, attempt):
                        delay = self._calculate_retry_delay(attempt)
                        self.logger.warning(f"🔄 Retry {attempt + 1}/{self.retry_config.max_attempts} for {self.name} after {delay:.2f}s: {e}")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        break
                else:
                    self.logger.error(f"❌ All retries failed for {self.name}: {e}")
        
        # All retries failed - check if circuit should open
        await self._check_circuit_state()
        raise last_exception
    
    def _classify_failure(self, exception: Exception) -> FailureType:
        """Classify failure type for better monitoring"""
        if isinstance(exception, asyncio.TimeoutError):
            return FailureType.TIMEOUT
        elif "timeout" in str(exception).lower():
            return FailureType.TIMEOUT
        elif "rate limit" in str(exception).lower():
            return FailureType.RATE_LIMIT
        elif "connection" in str(exception).lower():
            return FailureType.NETWORK_ERROR
        elif "unavailable" in str(exception).lower():
            return FailureType.SERVICE_UNAVAILABLE
        else:
            return FailureType.EXCEPTION
    
    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if exception should be retried"""
        if self.retry_config.retry_on:
            return any(isinstance(exception, exc_type) for exc_type in self.retry_config.retry_on)
        
        # Default retry logic
        non_retryable = [
            "authentication",
            "authorization",
            "forbidden",
            "not found"
        ]
        
        error_msg = str(exception).lower()
        return not any(keyword in error_msg for keyword in non_retryable)
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter"""
        delay = self.retry_config.base_delay * (
            self.retry_config.exponential_base ** attempt
        )
        
        # Apply maximum delay limit
        delay = min(delay, self.retry_config.max_delay)
        
        # Add jitter if enabled
        if self.retry_config.jitter:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    async def _record_success(self, response_time: float):
        """Record successful execution"""
        async with self._lock:
            self.metrics.total_requests += 1
            self.metrics.successful_requests += 1
            self.metrics.last_success_time = time.time()
            
            # Update average response time
            self._update_avg_response_time(response_time)
            
            # Add to history
            self._add_to_history("success", response_time)
            
            # Update circuit state
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    await self._close_circuit()
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success in closed state
                self.failure_count = 0
            
            # Store in distributed state
            await self._persist_metrics()
    
    async def _record_failure(self, failure_type: FailureType, response_time: float):
        """Record failed execution"""
        async with self._lock:
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            self.metrics.last_failure_time = time.time()
            
            # Update failure-specific metrics
            if failure_type == FailureType.TIMEOUT:
                self.metrics.timeouts += 1
            
            # Update average response time
            self._update_avg_response_time(response_time)
            
            # Add to history
            self._add_to_history("failure", response_time, failure_type.value)
            
            # Update circuit state
            if self.state == CircuitState.CLOSED:
                self.failure_count += 1
                if self.failure_count >= self.config.failure_threshold:
                    await self._open_circuit()
            elif self.state == CircuitState.HALF_OPEN:
                await self._open_circuit()
            
            # Store in distributed state
            await self._persist_metrics()
    
    def _update_avg_response_time(self, response_time: float):
        """Update average response time"""
        total = self.metrics.total_requests
        current_avg = self.metrics.avg_response_time
        self.metrics.avg_response_time = (current_avg * (total - 1) + response_time) / total
    
    def _add_to_history(self, 
                         status: str, 
                         response_time: float, 
                         failure_type: str = None):
        """Add request to history with sliding window"""
        self.request_history.append({
            "timestamp": time.time(),
            "status": status,
            "response_time": response_time,
            "failure_type": failure_type
        })
        
        # Maintain window size
        if len(self.request_history) > self.config.metrics_window:
            self.request_history.pop(0)
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset"""
        return time.time() - self.last_failure_time >= self.config.timeout
    
    async def _open_circuit(self):
        """Open circuit to prevent further calls"""
        self.state = CircuitState.OPEN
        self.last_failure_time = time.time()
        self.metrics.circuit_opens += 1
        self.last_state_change = time.time()
        
        self.logger.warning(f"🚨 Circuit {self.name} OPENED after {self.failure_count} failures")
        await self._log_state_change("CLOSED", "OPEN")
        await self._persist_metrics()
    
    async def _close_circuit(self):
        """Close circuit to resume normal operation"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.metrics.circuit_closes += 1
        self.last_state_change = time.time()
        
        self.logger.info(f"✅ Circuit {self.name} CLOSED after {self.success_count} successes")
        await self._log_state_change("OPEN", "CLOSED")
        await self._persist_metrics()
    
    async def _log_state_change(self, from_state: str, to_state: str):
        """Log circuit state change"""
        try:
            log_entry = {
                "circuit_name": self.name,
                "from_state": from_state,
                "to_state": to_state,
                "timestamp": datetime.now().isoformat(),
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "metrics": asdict(self.metrics)
            }
            
            # Store in distributed state
            await distributed_state_manager.set_state(
                f"circuit_breaker:{self.name}:state_change",
                log_entry,
                ttl=86400  # 24 hours
            )
            
            # Log to file
            self.logger.info(f"🔄 Circuit State Change: {self.name} {from_state} → {to_state}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to log state change: {e}")
    
    async def _persist_metrics(self):
        """Persist metrics to distributed state"""
        try:
            await distributed_state_manager.set_state(
                f"circuit_breaker:{self.name}:metrics",
                asdict(self.metrics),
                ttl=3600  # 1 hour
            )
        except Exception as e:
            self.logger.error(f"❌ Failed to persist metrics: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive circuit breaker status"""
        async with self._lock:
            # Calculate recent performance
            recent_requests = [
                req for req in self.request_history
                if time.time() - req["timestamp"] <= 300  # Last 5 minutes
            ]
            
            recent_success_rate = 0.0
            if recent_requests:
                recent_successes = len([req for req in recent_requests if req["status"] == "success"])
                recent_success_rate = recent_successes / len(recent_requests)
            
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "last_failure_time": self.metrics.last_failure_time,
                "last_success_time": self.metrics.last_success_time,
                "last_state_change": self.last_state_change,
                "time_until_retry": max(0, self.config.timeout - (time.time() - self.last_failure_time)),
                "metrics": asdict(self.metrics),
                "recent_performance": {
                    "requests_last_5min": len(recent_requests),
                    "success_rate_last_5min": recent_success_rate,
                    "avg_response_time_last_5min": sum(req["response_time"] for req in recent_requests) / len(recent_requests) if recent_requests else 0.0
                },
                "config": asdict(self.config),
                "timestamp": datetime.now().isoformat()
            }
    
    async def reset(self):
        """Manually reset circuit breaker"""
        async with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.metrics = CircuitMetrics()
            self.request_history.clear()
            
            self.logger.info(f"🔄 Circuit {self.name} manually reset")
            await self._persist_metrics()


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit is open"""
    pass


class CircuitBreakerManager:
    """
    Manager for multiple circuit breakers with centralized monitoring
    """
    
    def __init__(self):
        self.logger = get_logger("CircuitBreakerManager")
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.global_metrics = {
            "total_circuits": 0,
            "open_circuits": 0,
            "closed_circuits": 0,
            "half_open_circuits": 0,
            "total_requests": 0,
            "total_failures": 0
        }
    
    def create_circuit_breaker(self, 
                                 name: str,
                                 config: CircuitBreakerConfig = None,
                                 retry_config: RetryConfig = None) -> CircuitBreaker:
        """Create and register new circuit breaker"""
        circuit_breaker = CircuitBreaker(name, config, retry_config)
        self.circuit_breakers[name] = circuit_breaker
        self.global_metrics["total_circuits"] += 1
        
        self.logger.info(f"🔧 Created circuit breaker: {name}")
        return circuit_breaker
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name"""
        return self.circuit_breakers.get(name)
    
    async def call_with_circuit_breaker(self, 
                                        circuit_name: str,
                                        func: Callable,
                                        *args,
                                        **kwargs) -> Any:
        """Call function with circuit breaker protection"""
        circuit_breaker = self.get_circuit_breaker(circuit_name)
        if not circuit_breaker:
            self.logger.error(f"❌ Circuit breaker not found: {circuit_name}")
            raise ValueError(f"Circuit breaker {circuit_name} not found")
        
        return await circuit_breaker.call(func, *args, **kwargs)
    
    async def get_all_status(self) -> Dict[str, Any]:
        """Get status of all circuit breakers"""
        status = {
            "global_metrics": self.global_metrics.copy(),
            "circuit_breakers": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Update global metrics
        open_count = 0
        closed_count = 0
        half_open_count = 0
        
        for name, circuit in self.circuit_breakers.items():
            circuit_status = await circuit.get_status()
            status["circuit_breakers"][name] = circuit_status
            
            if circuit_status["state"] == "open":
                open_count += 1
            elif circuit_status["state"] == "closed":
                closed_count += 1
            elif circuit_status["state"] == "half_open":
                half_open_count += 1
        
        status["global_metrics"]["open_circuits"] = open_count
        status["global_metrics"]["closed_circuits"] = closed_count
        status["global_metrics"]["half_open_circuits"] = half_open_count
        
        return status
    
    async def reset_all(self):
        """Reset all circuit breakers"""
        for circuit in self.circuit_breakers.values():
            await circuit.reset()
        
        self.logger.info("🔄 All circuit breakers reset")
    
    async def shutdown(self):
        """Shutdown circuit breaker manager"""
        for circuit in self.circuit_breakers.values():
            await circuit._persist_metrics()
        
        self.logger.info("🛑 Circuit breaker manager shutdown")


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()

# Decorator for circuit breaker protection
def circuit_breaker_protected(circuit_name: str, 
                              config: CircuitBreakerConfig = None,
                              retry_config: RetryConfig = None):
    """Decorator for circuit breaker protection"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            circuit = circuit_breaker_manager.get_circuit_breaker(circuit_name)
            if not circuit:
                circuit = circuit_breaker_manager.create_circuit_breaker(
                    circuit_name, config, retry_config
                )
            
            return await circuit.call(func, *args, **kwargs)
        return wrapper
    return decorator
