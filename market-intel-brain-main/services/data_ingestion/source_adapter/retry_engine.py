import asyncio
import random
import time
import logging
from typing import Callable, Any, Optional, Type, Tuple, List
from functools import wraps
from .error_contract import MaifaIngestionError


class RetryConfig:
    """Configuration for retry engine"""
    
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
        self.retryable_exceptions = retryable_exceptions or [
            MaifaIngestionError
        ]


class RetryEngine:
    """Advanced retry engine with exponential backoff and full jitter"""
    
    def __init__(self, config: Optional[RetryConfig] = None, logger: Optional[logging.Logger] = None):
        self.config = config or RetryConfig()
        self.logger = logger or logging.getLogger("RetryEngine")
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter"""
        # Exponential backoff: delay = base_delay * (exponential_base ^ attempt)
        delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        
        # Cap at max_delay
        delay = min(delay, self.config.max_delay)
        
        # Add jitter if enabled
        if self.config.jitter:
            # Full jitter: random between 0 and delay
            jitter_range = delay * self.config.jitter_factor
            delay = delay + random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)  # Ensure non-negative
        
        return delay
    
    def _is_retryable_exception(self, exception: Exception) -> bool:
        """Check if exception is retryable"""
        # Check if exception is in retryable list
        for retryable_type in self.config.retryable_exceptions:
            if isinstance(exception, retryable_type):
                # For MaifaIngestionError, check if it's transient
                if isinstance(exception, MaifaIngestionError):
                    return exception.is_transient
                return True
        
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
                self.logger.debug(f"Executing {func.__name__}, attempt {attempt + 1}/{self.config.max_attempts}")
                
                # Execute the function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Log success on retry attempts
                if attempt > 0:
                    self.logger.info(f"Success on attempt {attempt + 1} for {func.__name__}")
                
                return result
            
            except Exception as e:
                last_exception = e
                
                # Check if exception is retryable
                if not self._is_retryable_exception(e):
                    self.logger.error(f"Non-retryable exception for {func.__name__}: {type(e).__name__}: {e}")
                    raise
                
                # Check if this was the last attempt
                if attempt == self.config.max_attempts - 1:
                    self.logger.error(f"Max attempts ({self.config.max_attempts}) reached for {func.__name__}: {e}")
                    raise
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt)
                self.logger.warning(
                    f"Attempt {attempt + 1} failed for {func.__name__}: {type(e).__name__}: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                
                # Wait before next attempt
                await asyncio.sleep(delay)
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    jitter_factor: float = 0.1,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
    logger: Optional[logging.Logger] = None
):
    """Decorator for adding retry functionality to functions"""
    
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
        
        retry_engine = RetryEngine(config, logger)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await retry_engine.execute_with_retry(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, run in event loop
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(retry_engine.execute_with_retry(func, *args, **kwargs))
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class RetryMetrics:
    """Metrics collection for retry engine"""
    
    def __init__(self):
        self.attempts = {}
        self.successes = {}
        self.failures = {}
    
    def record_attempt(self, func_name: str):
        """Record an attempt"""
        if func_name not in self.attempts:
            self.attempts[func_name] = 0
        self.attempts[func_name] += 1
    
    def record_success(self, func_name: str):
        """Record a success"""
        if func_name not in self.successes:
            self.successes[func_name] = 0
        self.successes[func_name] += 1
    
    def record_failure(self, func_name: str):
        """Record a failure"""
        if func_name not in self.failures:
            self.failures[func_name] = 0
        self.failures[func_name] += 1
    
    def get_metrics(self) -> dict:
        """Get retry metrics"""
        metrics = {}
        for func_name in set(list(self.attempts.keys()) + list(self.successes.keys()) + list(self.failures.keys())):
            attempts = self.attempts.get(func_name, 0)
            successes = self.successes.get(func_name, 0)
            failures = self.failures.get(func_name, 0)
            
            metrics[func_name] = {
                "total_attempts": attempts,
                "total_successes": successes,
                "total_failures": failures,
                "success_rate": successes / attempts if attempts > 0 else 0,
                "failure_rate": failures / attempts if attempts > 0 else 0
            }
        
        return metrics


# Global metrics instance
retry_metrics = RetryMetrics()


class RetryEngineWithMetrics(RetryEngine):
    """Retry engine with metrics collection"""
    
    def __init__(self, config: Optional[RetryConfig] = None, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        self.metrics = retry_metrics
    
    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic and metrics"""
        func_name = func.__name__
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                self.metrics.record_attempt(func_name)
                self.logger.debug(f"Executing {func_name}, attempt {attempt + 1}/{self.config.max_attempts}")
                
                # Execute the function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Record success
                self.metrics.record_success(func_name)
                
                # Log success on retry attempts
                if attempt > 0:
                    self.logger.info(f"Success on attempt {attempt + 1} for {func_name}")
                
                return result
            
            except Exception as e:
                last_exception = e
                self.metrics.record_failure(func_name)
                
                # Check if exception is retryable
                if not self._is_retryable_exception(e):
                    self.logger.error(f"Non-retryable exception for {func_name}: {type(e).__name__}: {e}")
                    raise
                
                # Check if this was the last attempt
                if attempt == self.config.max_attempts - 1:
                    self.logger.error(f"Max attempts ({self.config.max_attempts}) reached for {func_name}: {e}")
                    raise
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt)
                self.logger.warning(
                    f"Attempt {attempt + 1} failed for {func_name}: {type(e).__name__}: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                
                # Wait before next attempt
                await asyncio.sleep(delay)
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
