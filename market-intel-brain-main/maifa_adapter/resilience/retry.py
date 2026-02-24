"""
Retry Engine Implementation using Tenacity

This module provides retry decorators with exponential backoff and jitter,
specifically designed for transient adapter errors.
"""

import asyncio
import time
import logging
import functools
from typing import Optional, List, Type, Callable, Any, TypeVar
from dataclasses import dataclass

import tenacity
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

from ..core.exceptions import TransientAdapterError

T = TypeVar('T')


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: Optional[List[Type[Exception]] = None


class RetryEngine:
    """
    Advanced retry engine using tenacity with exponential backoff and jitter.
    
    Specifically designed to retry only transient adapter errors while
    avoiding fatal errors that would never succeed with retries.
    """
    
    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.config = config or RetryConfig()
        self.logger = logger or logging.getLogger("RetryEngine")
        
        # Default retryable exceptions
        self.default_retryable_exceptions = [TransientAdapterError]
        
        # Combine with custom exceptions
        all_retryable = self.default_retryable_exceptions.copy()
        if self.config.retryable_exceptions:
            all_retryable.extend(self.config.retryable_exceptions)
        
        # Create tenacity retrying instance
        self.retryer = tenacity.Retrying(
            stop=stop_after_attempt(self.config.max_attempts),
            wait=wait_exponential_jitter(
                base=self.config.base_delay,
                max=self.config.max_delay,
                exp_base=self.config.exponential_base
            ),
            retry=retry_if_exception_type(tuple(all_retryable)),
            before_sleep=before_sleep_log(
                self.logger,
                logging.WARNING,
                "Retrying {value} after {wait:.2f} seconds (attempt {attempt})"
            ),
            after=after_log(
                self.logger,
                logging.INFO,
                "Operation {value} succeeded after {attempt} attempts"
            ),
            reraise=True
        )
    
    async def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries exhausted
        """
        if asyncio.iscoroutinefunction(func):
            # For async functions
            @functools.wraps(func)
            async def async_wrapper():
                return await self.retryer(func, *args, **kwargs)
            
            return await async_wrapper()
        else:
            # For sync functions, run in executor
            @functools.wraps(func)
            def sync_wrapper():
                loop = asyncio.get_event_loop()
                return loop.run_in_executor(None, self.retryer, func, *args, **kwargs)
            
            return await sync_wrapper()
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Make RetryEngine callable as a decorator.
        
        Args:
            func: Function to decorate
            
        Returns:
            Decorated function
        """
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.execute(func, *args, **kwargs)
        
        return wrapper


def retry_transient(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[List[Type[Exception]] = None,
    logger: Optional[logging.Logger] = None
):
    """
    Decorator for retrying functions on transient adapter errors.
    
    Uses tenacity with exponential backoff and jitter to provide
    robust retry logic for distributed systems.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add jitter to delays
        retryable_exceptions: Additional exception types to retry
        logger: Logger instance for logging
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Create retry configuration
        config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter,
            retryable_exceptions=retryable_exceptions
        )
        
        # Create retry engine
        retry_engine = RetryEngine(config, logger)
        
        # Return decorated function
        return retry_engine(func)
    
    return decorator


def retry_with_circuit_breaker(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    circuit_breaker=None
):
    """
    Decorator that combines retry logic with circuit breaker.
    
    This decorator will retry transient errors but will stop retrying
    if the circuit breaker is open.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        circuit_breaker: Circuit breaker instance
        
    Returns:
        Decorated function with retry and circuit breaker logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if circuit_breaker:
                # Check if circuit breaker allows execution
                if not await circuit_breaker.can_execute():
                    from .circuit_breaker import CircuitBreakerOpenError
                    metrics = await circuit_breaker.get_metrics()
                    raise CircuitBreakerOpenError(
                        adapter_name=circuit_breaker.adapter_name,
                        failure_count=metrics.get("failure_count", 0),
                        recovery_time=circuit_breaker.config.recovery_time
                    )
                
                # Execute with circuit breaker protection
                return await circuit_breaker.execute(func, *args, **kwargs)
            else:
                # Just use retry logic
                retry_engine = RetryEngine(RetryConfig(max_attempts=max_attempts))
                return await retry_engine.execute(func, *args, **kwargs)
        
        return wrapper
    
    return decorator


class RetryMetrics:
    """Metrics collection for retry operations"""
    
    def __init__(self):
        self.attempts = {}
        self.successes = {}
        self.failures = {}
        self.retries = {}
        self.total_delay = {}
    
    def record_attempt(self, func_name: str):
        """Record an attempt"""
        if func_name not in self.attempts:
            self.attempts[func_name] = 0
        self.attempts[func_name] += 1
    
    def record_success(self, func_name: str, attempt: int):
        """Record a successful attempt"""
        if func_name not in self.successes:
            self.successes[func_name] = 0
        self.successes[func_name] += 1
        
        # Record retries (attempts beyond first)
        if attempt > 0:
            if func_name not in self.retries:
                self.retries[func_name] = 0
            self.retries[func_name] += attempt
    
    def record_failure(self, func_name: str, attempt: int, exception: Exception):
        """Record a failed attempt"""
        if func_name not in self.failures:
            self.failures[func_name] = 0
        self.failures[func_name] += 1
        
        # Record retries (attempts beyond first)
        if attempt > 0:
            if func_name not in self.retries:
                self.retries[func_name] = 0
            self.retries[func_name] += attempt
    
    def record_delay(self, func_name: str, delay: float):
        """Record delay time"""
        if func_name not in self.total_delay:
            self.total_delay[func_name] = 0.0
        self.total_delay[func_name] += delay
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get retry metrics"""
        metrics = {}
        
        # Get all function names
        all_funcs = set()
        all_funcs.update(self.attempts.keys())
        all_funcs.update(self.successes.keys())
        all_funcs.update(self.failures.keys())
        all_funcs.update(self.retries.keys())
        
        for func_name in all_funcs:
            attempts = self.attempts.get(func_name, 0)
            successes = self.successes.get(func_name, 0)
            failures = self.failures.get(func_name, 0)
            retries = self.retries.get(func_name, 0)
            total_delay = self.total_delay.get(func_name, 0.0)
            
            metrics[func_name] = {
                "total_attempts": attempts,
                "total_successes": successes,
                "total_failures": failures,
                "total_retries": retries,
                "success_rate": successes / attempts if attempts > 0 else 0,
                "failure_rate": failures / attempts if attempts > 0 else 0,
                "retry_rate": retries / attempts if attempts > 0 else 0,
                "total_delay_time": total_delay,
                "average_delay_per_retry": total_delay / retries if retries > 0 else 0
            }
        
        return metrics


# Global metrics instance
retry_metrics = RetryMetrics()


class RetryEngineWithMetrics(RetryEngine):
    """Retry engine with metrics collection"""
    
    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        super().__init__(config, logger)
        self.metrics = retry_metrics
    
    async def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with retry logic and metrics collection"""
        start_time = time.time()
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                # Record attempt
                self.metrics.record_attempt(func.__name__)
                
                self.logger.debug(
                    f"Executing {func.__name__}, attempt {attempt + 1}/{self.config.max_attempts}"
                )
                
                # Execute function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, func, *args, **kwargs)
                
                # Record success
                self.metrics.record_success(func.__name__, attempt)
                
                # Log success on retry attempts
                if attempt > 0:
                    self.logger.info(
                        f"Success on attempt {attempt + 1} for {func.__name__}"
                    )
                
                return result
            
            except Exception as e:
                last_exception = e
                
                # Record failure
                self.metrics.record_failure(func.__name__, attempt, e)
                
                # Check if we should retry
                if attempt >= self.config.max_attempts - 1:
                    self.logger.error(
                        f"Max attempts reached for {func.__name__}: {e}"
                    )
                    raise
                
                # Check if error is retryable
                retryable_exceptions = self.default_retryable_exceptions.copy()
                if self.config.retryable_exceptions:
                    retryable_exceptions.extend(self.config.retryable_exceptions)
                
                if not any(isinstance(e, exc_type) for exc_type in retryable_exceptions):
                    self.logger.error(
                        f"Non-retryable error for {func.__name__}: {e}"
                    )
                    raise
                
                # Calculate delay and wait
                delay = min(
                    self.config.base_delay * (self.config.exponential_base ** attempt),
                    self.config.max_delay
                )
                
                # Add jitter if enabled
                if self.config.jitter:
                    import random
                    jitter = random.uniform(0, delay * 0.1)
                    delay += jitter
                
                # Record delay
                self.metrics.record_delay(func.__name__, delay)
                
                self.logger.warning(
                    f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                    f"Retrying in {delay:.2f}s"
                )
                
                await asyncio.sleep(delay)
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception


def retry_transient_with_metrics(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[List[Type[Exception]]] None,
    logger: Optional[logging.Logger] = None
):
    """
    Decorator for retrying functions with metrics collection.
    
    Same as retry_transient but includes detailed metrics tracking.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter,
            retryable_exceptions=retryable_exceptions
        )
        
        retry_engine = RetryEngineWithMetrics(config, logger)
        return retry_engine(func)
    
    return decorator


# Convenience functions for common retry patterns
def retry_on_network_errors(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0
):
    """Retry decorator specifically for network errors"""
    from ..core.exceptions import AdapterNetworkError, AdapterTimeoutError
    
    network_errors = [AdapterNetworkError, AdapterTimeoutError]
    
    return retry_transient(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        retryable_exceptions=network_errors
    )


def retry_on_rate_limit(
    max_attempts: int = 5,
    base_delay: float = 5.0,
    max_delay: float = 300.0
):
    """Retry decorator specifically for rate limit errors"""
    from ..core.exceptions import RateLimitExceededError
    
    rate_limit_errors = [RateLimitExceededError]
    
    return retry_transient(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        retryable_exceptions=rate_limit_errors
    )
