"""
Telemetry Middleware and Decorators

This module provides middleware and decorators for automatic instrumentation
of BaseSourceAdapter classes without modifying business logic.
"""

import time
import functools
import logging
from typing import Optional, Dict, Any, Callable, Union
from functools import wraps

from .tracer import OpenTelemetryTracer, get_tracer
from .metrics import PrometheusMetrics, get_metrics


class TelemetryMiddleware:
    """
    Middleware class for automatic instrumentation.
    
    This class provides middleware functionality that can be applied
    to adapter classes to automatically record telemetry data.
    """
    
    def __init__(
        self,
        tracer: Optional[OpenTelemetryTracer] = None,
        metrics: Optional[PrometheusMetrics] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize telemetry middleware.
        
        Args:
            tracer: OpenTelemetry tracer instance
            metrics: Prometheus metrics instance
            logger: Logger instance
        """
        self.tracer = tracer or get_tracer()
        self.metrics = metrics or get_metrics()
        self.logger = logger or logging.getLogger("TelemetryMiddleware")
        
        self.logger.info("TelemetryMiddleware initialized")
    
    def instrument_class(self, cls: type, class_name: Optional[str] = None):
        """
        Instrument a class with telemetry.
        
        Args:
            cls: Class to instrument
            class_name: Name for tracing (uses class name if None)
            
        Returns:
            Instrumented class
        """
        if class_name is None:
            class_name = f"{cls.__module__}.{cls.__name__}"
        
        # Store original methods
        original_methods = {}
        
        # Find all methods to instrument
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if callable(attr) and not attr_name.startswith('_'):
                original_methods[attr_name] = attr
        
        # Create instrumented methods
        for method_name, original_method in original_methods.items():
            instrumented_method = self._create_instrumented_method(
                original_method,
                class_name,
                method_name
            )
            setattr(cls, method_name, instrumented_method)
        
        # Add telemetry metadata
        cls._telemetry_instrumented = True
        cls._telemetry_original_methods = original_methods
        
        self.logger.info(f"Instrumented class {class_name} with {len(original_methods)} methods")
        
        return cls
    
    def _create_instrumented_method(
        self,
        original_method: Callable,
        class_name: str,
        method_name: str
    ) -> Callable:
        """
        Create an instrumented version of a method.
        
        Args:
            original_method: Original method to instrument
            class_name: Name of the class
            method_name: Name of the method
            
        Returns:
            Instrumented method
        """
        if functools.iscoroutinefunction(original_method):
            return self._create_instrumented_async_method(
                original_method,
                class_name,
                method_name
            )
        else:
            return self._create_instrumented_sync_method(
                original_method,
                class_name,
                method_name
            )
    
    def _create_instrumented_async_method(
        self,
        original_method: Callable,
        class_name: str,
        method_name: str
    ) -> Callable:
        """Create instrumented async method."""
        
        @wraps(original_method)
        async def async_wrapper(*args, **kwargs):
            # Extract provider name from instance or kwargs
            provider_name = self._extract_provider_name(args, kwargs)
            
            # Create span name
            span_name = f"{class_name}.{method_name}"
            
            # Start tracing
            with self.tracer.trace_async(
                name=span_name,
                attributes={
                    "class": class_name,
                    "method": method_name,
                    "provider": provider_name,
                    "component": "adapter"
                }
            ) as span:
                # Record request start
                self.metrics.record_request_start(provider_name, method_name)
                
                start_time = time.time()
                
                try:
                    # Execute original method
                    result = await original_method(*args, **kwargs)
                    
                    # Record success
                    duration = time.time() - start_time
                    self.metrics.record_request_success(
                        provider=provider_name,
                        operation=method_name,
                        duration=duration
                    )
                    
                    # Add result metadata to span
                    if hasattr(result, '__dict__'):
                        if hasattr(result, 'data'):
                            span.set_attribute("result.data_size", len(str(result.data)))
                        if hasattr(result, 'count'):
                            span.set_attribute("result.count", result.count)
                    
                    return result
                    
                except Exception as e:
                    # Record error
                    duration = time.time() - start_time
                    self.metrics.record_request_error(
                        provider=provider_name,
                        operation=method_name,
                        error_type=type(e).__name__,
                        duration=duration
                    )
                    
                    # Add error details to span
                    span.set_status(
                        Status(StatusCode.ERROR, str(e))
                    )
                    span.record_exception(e)
                    
                    raise
                    
                finally:
                    # Record request end
                    self.metrics.record_request_end(provider_name)
        
        return async_wrapper
    
    def _create_instrumented_sync_method(
        self,
        original_method: Callable,
        class_name: str,
        method_name: str
    ) -> Callable:
        """Create instrumented sync method."""
        
        @wraps(original_method)
        def sync_wrapper(*args, **kwargs):
            # Extract provider name
            provider_name = self._extract_provider_name(args, kwargs)
            
            # Create span name
            span_name = f"{class_name}.{method_name}"
            
            # Start tracing
            with self.tracer.trace_async(
                name=span_name,
                attributes={
                    "class": class_name,
                    "method": method_name,
                    "provider": provider_name,
                    "component": "adapter"
                }
            ) as span:
                # Record request start
                self.metrics.record_request_start(provider_name, method_name)
                
                start_time = time.time()
                
                try:
                    # Execute original method
                    result = original_method(*args, **kwargs)
                    
                    # Record success
                    duration = time.time() - start_time
                    self.metrics.record_request_success(
                        provider=provider_name,
                        operation=method_name,
                        duration=duration
                    )
                    
                    # Add result metadata to span
                    if hasattr(result, '__dict__'):
                        if hasattr(result, 'data'):
                            span.set_attribute("result.data_size", len(str(result.data)))
                        if hasattr(result, 'count'):
                            span.set_attribute("result.count", result.count)
                    
                    return result
                    
                except Exception as e:
                    # Record error
                    duration = time.time() - start_time
                    self.metrics.record_request_error(
                        provider=provider_name,
                        operation=method_name,
                        error_type=type(e).__name__,
                        duration=duration
                    )
                    
                    # Add error details to span
                    span.set_status(
                        Status(StatusCode.ERROR, str(e))
                    )
                    span.record_exception(e)
                    
                    raise
                    
                finally:
                    # Record request end
                    self.metrics.record_request_end(provider_name)
        
        return sync_wrapper
    
    def _extract_provider_name(self, args: tuple, kwargs: dict) -> str:
        """
        Extract provider name from arguments.
        
        Args:
            args: Positional arguments
            kwargs: Keyword arguments
            
        Returns:
            Provider name
        """
        # Try to get provider from kwargs
        if 'provider_name' in kwargs:
            return kwargs['provider_name']
        
        # Try to get provider from self argument
        if args and hasattr(args[0], 'provider_name'):
            return args[0].provider_name
        
        # Try to get from class name
        if args and hasattr(args[0], '__class__'):
            class_name = args[0].__class__.__name__
            if 'Adapter' in class_name:
                return class_name.replace('Adapter', '').lower()
        
        # Default fallback
        return 'unknown'
    
    def wrap_instance(self, instance: Any, instance_name: Optional[str] = None):
        """
        Wrap an instance with telemetry instrumentation.
        
        Args:
            instance: Instance to wrap
            instance_name: Name for tracing
            
        Returns:
            Wrapped instance
        """
        if instance_name is None:
            instance_name = f"{instance.__class__.__module__}.{instance.__class__.__name__}"
        
        # Store original instance
        original_instance = instance
        
        # Create wrapper
        class TelemetryWrapper:
            def __init__(self):
                self._wrapped = original_instance
                self._instance_name = instance_name
            
            def __getattr__(self, name):
                attr = getattr(self._wrapped, name)
                
                if callable(attr) and not name.startswith('_'):
                    # Wrap method
                    return self._create_instrumented_method(
                        attr,
                        instance_name,
                        name
                    )
                else:
                    return attr
            
            def __setattr__(self, name, value):
                setattr(self._wrapped, name, value)
            
            def __delattr__(self, name):
                delattr(self._wrapped, name)
            
            def __dir__(self):
                return dir(self._wrapped)
        
        wrapper = TelemetryWrapper()
        wrapper._wrapped = instance
        wrapper._instance_name = instance_name
        
        return wrapper


def telemetry_decorator(
    tracer: Optional[OpenTelemetryTracer] = None,
    metrics: Optional[PrometheusMetrics] = None,
    provider_name: Optional[str] = None
):
    """
    Decorator for automatic telemetry instrumentation.
    
    Args:
        tracer: OpenTelemetry tracer instance
        metrics: Prometheus metrics instance
        provider_name: Provider name for metrics
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        tracer_instance = tracer or get_tracer()
        metrics_instance = metrics or get_metrics()
        
        if functools.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Determine provider name
                current_provider = provider_name or _extract_provider_from_args(args, kwargs)
                
                # Create span name
                span_name = f"{func.__module__}.{func.__name__}"
                
                # Start tracing
                with tracer_instance.trace_async(
                    name=span_name,
                    attributes={
                        "function": func.__name__,
                        "module": func.__module__,
                        "provider": current_provider,
                        "component": "adapter"
                    }
                ) as span:
                    # Record request start
                    metrics_instance.record_request_start(current_provider, func.__name__)
                    
                    start_time = time.time()
                    
                    try:
                        # Execute original function
                        result = await func(*args, **kwargs)
                        
                        # Record success
                        duration = time.time() - start_time
                        metrics_instance.record_request_success(
                            provider=current_provider,
                            operation=func.__name__,
                            duration=duration
                        )
                        
                        # Add result metadata to span
                        if hasattr(result, '__dict__'):
                            if hasattr(result, 'data'):
                                span.set_attribute("result.data_size", len(str(result.data)))
                            if hasattr(result, 'count'):
                                span.set_attribute("result.count", result.count)
                        
                        return result
                        
                    except Exception as e:
                        # Record error
                        duration = time.time() - start_time
                        metrics_instance.record_request_error(
                            provider=current_provider,
                            operation=func.__name__,
                            error_type=type(e).__name__,
                            duration=duration
                        )
                        
                        # Add error details to span
                        span.set_status(
                            Status(StatusCode.ERROR, str(e))
                        )
                        span.record_exception(e)
                        
                        raise
                        
                    finally:
                        # Record request end
                        metrics_instance.record_request_end(current_provider)
            
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Determine provider name
                current_provider = provider_name or _extract_provider_from_args(args, kwargs)
                
                # Create span name
                span_name = f"{func.__module__}.{func.__name__}"
                
                # Start tracing
                with tracer_instance.trace_async(
                    name=span_name,
                    attributes={
                        "function": func.__name__,
                        "module": func.__module__,
                        "provider": current_provider,
                        "component": "adapter"
                    }
                ) as span:
                    # Record request start
                    metrics_instance.record_request_start(current_provider, func.__name__)
                    
                    start_time = time.time()
                    
                    try:
                        # Execute original function
                        result = func(*args, **kwargs)
                        
                        # Record success
                        duration = time.time() - start_time
                        metrics_instance.record_request_success(
                            provider=current_provider,
                            operation=func.__name__,
                            duration=duration
                        )
                        
                        # Add result metadata to span
                        if hasattr(result, '__dict__'):
                            if hasattr(result, 'data'):
                                span.set_attribute("result.data_size", len(str(result.data)))
                            if hasattr(result, 'count'):
                                span.set_attribute("result.count", result.count)
                        
                        return result
                        
                    except Exception as e:
                        # Record error
                        duration = time.time() - start_time
                        metrics_instance.record_request_error(
                            provider=current_provider,
                            operation=func.__name__,
                            error_type=type(e).__name__,
                            duration=duration
                        )
                        
                        # Add error details to span
                        span.set_status(
                            Status(StatusCode.ERROR, str(e))
                        )
                        span.record_exception(e)
                        
                        raise
                        
                    finally:
                        # Record request end
                        metrics_instance.record_request_end(current_provider)
            
            return sync_wrapper
    
    return decorator


def _extract_provider_from_args(args: tuple, kwargs: dict) -> str:
    """Extract provider name from function arguments."""
    # Try to get provider from kwargs
    if 'provider_name' in kwargs:
        return kwargs['provider_name']
    
    # Try to get from self argument
    if args and hasattr(args[0], 'provider_name'):
        return args[0].provider_name
    
    # Try to get from class name
    if args and hasattr(args[0], '__class__'):
        class_name = args[0].__class__.__name__
        if 'Adapter' in class_name:
            return class_name.replace('Adapter', '').lower()
    
    # Default fallback
    return 'unknown'


# Convenience decorator
def instrument_adapter(
    provider_name: Optional[str] = None,
    tracer: Optional[OpenTelemetryTracer] = None,
    metrics: Optional[PrometheusMetrics] = None
):
    """
    Convenience decorator for adapter instrumentation.
    
    Args:
        provider_name: Provider name for metrics
        tracer: OpenTelemetry tracer instance
        metrics: Prometheus metrics instance
        
    Returns:
        Decorator function
    """
    return telemetry_decorator(tracer, metrics, provider_name)


# Import required modules
from opentelemetry.trace.status import Status, StatusCode
