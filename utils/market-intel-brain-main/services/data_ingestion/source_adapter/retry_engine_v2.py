import asyncio
import random
import time
import logging
import functools
from typing import Callable, Type, Optional, List, Union, Any
from inspect import iscoroutinefunction

from .error_contract_v2 import (
    ProviderBaseError, ProviderTimeoutError, ProviderRateLimitError,
    ProviderDownError, ProviderAuthError, ProviderNotFoundError,
    ProviderValidationError, ProviderBadResponseError
)


class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        jitter_factor: float = 0.1,
        retryable_exceptions: Optional[List[Type[Exception]]] = None
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.jitter_factor = jitter_factor
        self.retryable_exceptions = retryable_exceptions or []
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter"""
        # Exponential backoff: delay = base_delay * (exponential_base ^ attempt)
        delay = self.base_delay * (self.exponential_base ** attempt)
        
        # Cap at max_delay
        delay = min(delay, self.max_delay)
        
        # Add jitter if enabled
        if self.jitter:
            # Full jitter: random between 0 and delay * jitter_factor
            jitter_range = delay * self.jitter_factor
            jitter = random.uniform(-jitter_range, jitter_range)
            delay = delay + jitter
            delay = max(0, delay)  # Ensure non-negative
        
        return delay


class RetryEngine:
    """Advanced retry engine with exponential backoff and jitter"""
    
    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.config = config or RetryConfig()
        self.logger = logger or logging.getLogger("RetryEngine")
        
        # Default transient exceptions
        self.default_transient_exceptions = [
            ProviderTimeoutError,
            ProviderRateLimitError,
            ProviderDownError,
            # Network-related errors
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError
        ]
        
        # Default fatal exceptions (do not retry)
        self.default_fatal_exceptions = [
            ProviderAuthError,
            ProviderNotFoundError,
            ProviderValidationError,
            ProviderBadResponseError
        ]
    
    def is_transient_error(self, exception: Exception) -> bool:
        """Check if an exception is transient (retryable)"""
        # Check custom retryable exceptions first
        for exc_type in self.config.retryable_exceptions:
            if isinstance(exception, exc_type):
                return True
        
        # Check default transient exceptions
        for exc_type in self.default_transient_exceptions:
            if isinstance(exception, exc_type):
                return True
        
        # Check HTTP status codes for transient errors
        if hasattr(exception, 'status_code'):
            status_code = exception.status_code
            if status_code in [502, 503, 504]:  # Server errors
                return True
            if status_code == 429:  # Rate limit
                return True
        
        return False
    
    def is_fatal_error(self, exception: Exception) -> bool:
        """Check if an exception is fatal (non-retryable)"""
        # Check default fatal exceptions
        for exc_type in self.default_fatal_exceptions:
            if isinstance(exception, exc_type):
                return True
        
        # Check HTTP status codes for fatal errors
        if hasattr(exception, 'status_code'):
            status_code = exception.status_code
            if status_code in [400, 401, 403, 404, 422]:  # Client errors
                return True
        
        return False
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if operation should be retried"""
        # Don't retry if max attempts reached
        if attempt >= self.config.max_attempts:
            return False
        
        # Don't retry fatal errors
        if self.is_fatal_error(exception):
            return False
        
        # Retry transient errors
        if self.is_transient_error(exception):
            return True
        
        # Default: don't retry unknown errors
        return False
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                self.logger.debug(
                    f"Executing {func.__name__}, attempt {attempt + 1}/{self.config.max_attempts}"
                )
                
                # Execute function (sync or async)
                if iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    # Run sync function in executor
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, func, *args, **kwargs)
                
                # Log success on retry attempts
                if attempt > 0:
                    self.logger.info(
                        f"Success on attempt {attempt + 1} for {func.__name__}"
                    )
                
                return result
            
            except Exception as e:
                last_exception = e
                
                # Log the error
                self.logger.warning(
                    f"Attempt {attempt + 1} failed for {func.__name__}: "
                    f"{type(e).__name__}: {e}"
                )
                
                # Check if we should retry
                if not self.should_retry(e, attempt):
                    self.logger.error(
                        f"Not retrying {func.__name__}: "
                        f"{'Max attempts reached' if attempt >= self.config.max_attempts - 1 else 'Fatal error'}"
                    )
                    raise
                
                # Calculate delay and wait
                if attempt < self.config.max_attempts - 1:  # Don't sleep after last attempt
                    delay = self.config.calculate_delay(attempt)
                    self.logger.info(
                        f"Retrying {func.__name__} in {delay:.2f}s "
                        f"(attempt {attempt + 2}/{self.config.max_attempts})"
                    )
                    await asyncio.sleep(delay)
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception


def async_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    jitter_factor: float = 0.1,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
    logger: Optional[logging.Logger] = None
):
    """
    Decorator for adding retry functionality to async functions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add jitter to delays
        jitter_factor: Factor for jitter calculation (0.0 to 1.0)
        retryable_exceptions: List of exception types to retry
        logger: Logger instance for logging retry attempts
    
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        # Create retry configuration
        config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter,
            jitter_factor=jitter_factor,
            retryable_exceptions=retryable_exceptions
        )
        
        # Create retry engine
        retry_engine = RetryEngine(config, logger)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await retry_engine.execute_with_retry(func, *args, **kwargs)
        
        # Return async wrapper
        return async_wrapper
    
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
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with retry logic and metrics collection"""
        last_exception = None
        start_time = time.time()
        
        for attempt in range(self.config.max_attempts):
            try:
                # Record attempt
                self.metrics.record_attempt(func.__name__)
                
                self.logger.debug(
                    f"Executing {func.__name__}, attempt {attempt + 1}/{self.config.max_attempts}"
                )
                
                # Execute function
                if iscoroutinefunction(func):
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
                
                # Log the error
                self.logger.warning(
                    f"Attempt {attempt + 1} failed for {func.__name__}: "
                    f"{type(e).__name__}: {e}"
                )
                
                # Check if we should retry
                if not self.should_retry(e, attempt):
                    self.logger.error(
                        f"Not retrying {func.__name__}: "
                        f"{'Max attempts reached' if attempt >= self.config.max_attempts - 1 else 'Fatal error'}"
                    )
                    raise
                
                # Calculate delay and wait
                if attempt < self.config.max_attempts - 1:  # Don't sleep after last attempt
                    delay = self.config.calculate_delay(attempt)
                    
                    # Record delay
                    self.metrics.record_delay(func.__name__, delay)
                    
                    self.logger.info(
                        f"Retrying {func.__name__} in {delay:.2f}s "
                        f"(attempt {attempt + 2}/{self.config.max_attempts})"
                    )
                    await asyncio.sleep(delay)
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception


def async_retry_with_metrics(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    jitter_factor: float = 0.1,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
    logger: Optional[logging.Logger] = None
):
    """
    Decorator for adding retry functionality with metrics collection.
    
    Same as async_retry but includes detailed metrics tracking.
    """
    def decorator(func: Callable) -> Callable:
        config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter,
            jitter_factor=jitter_factor,
            retryable_exceptions=retryable_exceptions
        )
        
        retry_engine = RetryEngineWithMetrics(config, logger)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await retry_engine.execute_with_retry(func, *args, **kwargs)
        
        return async_wrapper
    
    return decorator


# Convenience functions for common retry patterns
def retry_on_network_errors(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0
):
    """Retry decorator specifically for network errors"""
    network_errors = [
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
        ProviderTimeoutError,
        ProviderDownError
    ]
    
    return async_retry(
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
    rate_limit_errors = [
        ProviderRateLimitError
    ]
    
    return async_retry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        retryable_exceptions=rate_limit_errors
    )
