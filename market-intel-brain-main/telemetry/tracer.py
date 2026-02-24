"""
OpenTelemetry Tracer Implementation

This module provides distributed tracing capabilities using OpenTelemetry
to create spans for each adapter operation and fetch operation.
"""

import time
import uuid
import logging
from typing import Optional, Dict, Any, Callable, Union
from functools import wraps
from contextlib import asynccontextmanager

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.trace import SpanKind
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace import Status, StatusCode


class OpenTelemetryTracer:
    """
    OpenTelemetry tracer for distributed tracing.
    
    This class provides comprehensive tracing capabilities for monitoring
    adapter operations, fetch operations, and system performance.
    """
    
    def __init__(
        self,
        service_name: str = "market-intel-brain",
        jaeger_endpoint: Optional[str] = None,
        enable_tracing: bool = True,
        sample_rate: float = 1.0,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize OpenTelemetry tracer.
        
        Args:
            service_name: Name of the service being traced
            jaeger_endpoint: Jaeger collector endpoint
            enable_tracing: Whether to enable tracing
            sample_rate: Sampling rate (0.0 to 1.0)
            logger: Logger instance
        """
        self.service_name = service_name
        self.jaeger_endpoint = jaeger_endpoint
        self.enable_tracing = enable_tracing
        self.sample_rate = sample_rate
        self.logger = logger or logging.getLogger("OpenTelemetryTracer")
        
        self._tracer = None
        self._span_processors = []
        
        if self.enable_tracing:
            self._setup_tracer()
        
        self.logger.info(f"OpenTelemetryTracer initialized (service={service_name})")
    
    def _setup_tracer(self):
        """Set up OpenTelemetry tracer with exporters."""
        try:
            # Create resource
            resource = Resource.create({
                "service.name": self.service_name,
                "service.version": "1.0.0",
                "service.instance.id": str(uuid.uuid4())
            })
            
            # Set up tracer provider
            tracer_provider = TracerProvider(resource=resource)
            
            # Add Jaeger exporter if endpoint provided
            if self.jaeger_endpoint:
                jaeger_exporter = JaegerExporter(
                    agent_host_name=self.jaeger_endpoint.split(':')[0],
                    agent_port=int(self.jaeger_endpoint.split(':')[1]) if ':' in self.jaeger_endpoint else 6831,
                    collector_endpoint=self.jaeger_endpoint
                )
                span_processor = BatchSpanProcessor(jaeger_exporter)
                tracer_provider.add_span_processor(span_processor)
                self._span_processors.append(span_processor)
            
            # Register tracer provider
            trace.set_tracer_provider(tracer_provider)
            
            # Get tracer
            self._tracer = trace.get_tracer(self.service_name)
            
            self.logger.info(f"OpenTelemetry tracer setup complete")
            
        except Exception as e:
            self.logger.error(f"Failed to setup OpenTelemetry tracer: {e}")
            self._tracer = trace.get_tracer(__name__)  # Fallback tracer
    
    def create_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Create a new span.
        
        Args:
            name: Span name
            kind: Span kind
            attributes: Span attributes
            
        Returns:
            OpenTelemetry span
        """
        if not self.enable_tracing or not self._tracer:
            return NoOpSpan()
        
        # Apply sampling
        if not self._should_sample():
            return NoOpSpan()
        
        span = self._tracer.start_span(
            name=name,
            kind=kind,
            attributes=attributes or {}
        )
        
        return span
    
    @asynccontextmanager
    async def trace_async(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Async context manager for tracing.
        
        Args:
            name: Span name
            kind: Span kind
            attributes: Span attributes
            
        Yields:
            Active span
        """
        if not self.enable_tracing or not self._tracer:
            yield NoOpSpan()
            return
        
        if not self._should_sample():
            yield NoOpSpan()
            return
        
        span = self._tracer.start_span(
            name=name,
            kind=kind,
            attributes=attributes or {}
        )
        
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
        finally:
            span.end()
    
    def trace_function(
        self,
        name: Optional[str] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Decorator for tracing function execution.
        
        Args:
            name: Span name (uses function name if None)
            kind: Span kind
            attributes: Span attributes
            
        Returns:
            Decorated function
        """
        def decorator(func: Callable):
            span_name = name or f"{func.__module__}.{func.__name__}"
            
            if asyncio.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    async with self.trace_async(span_name, kind, attributes) as span:
                        # Add function arguments as attributes
                        self._add_function_args_to_span(span, args, kwargs)
                        
                        start_time = time.time()
                        try:
                            result = await func(*args, **kwargs)
                            
                            # Record execution time
                            execution_time = time.time() - start_time
                            span.set_attribute("execution_time", execution_time)
                            
                            return result
                        except Exception as e:
                            span.set_status(Status(StatusCode.ERROR, str(e)))
                            span.record_exception(e)
                            raise
                
                return async_wrapper
            else:
                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    with self.trace_async(span_name, kind, attributes) as span:
                        # Add function arguments as attributes
                        self._add_function_args_to_span(span, args, kwargs)
                        
                        start_time = time.time()
                        try:
                            result = func(*args, **kwargs)
                            
                            # Record execution time
                            execution_time = time.time() - start_time
                            span.set_attribute("execution_time", execution_time)
                            
                            return result
                        except Exception as e:
                            span.set_status(Status(StatusCode.ERROR, str(e)))
                            span.record_exception(e)
                            raise
                
                return sync_wrapper
        
        return decorator
    
    def trace_adapter_operation(
        self,
        adapter_name: str,
        operation: str,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Specialized tracer for adapter operations.
        
        Args:
            adapter_name: Name of the adapter
            operation: Operation being performed
            attributes: Additional attributes
            
        Returns:
            Decorator for adapter functions
        """
        span_attributes = {
            "adapter.name": adapter_name,
            "adapter.operation": operation,
            "component": "adapter",
            **(attributes or {})
        }
        
        return self.trace_function(
            name=f"adapter.{adapter_name}.{operation}",
            kind=SpanKind.CLIENT,
            attributes=span_attributes
        )
    
    def trace_fetch_operation(
        self,
        provider_name: str,
        endpoint: str,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Specialized tracer for fetch operations.
        
        Args:
            provider_name: Name of the data provider
            endpoint: API endpoint or data source
            attributes: Additional attributes
            
        Returns:
            Decorator for fetch functions
        """
        span_attributes = {
            "provider.name": provider_name,
            "fetch.endpoint": endpoint,
            "operation.type": "fetch",
            "component": "fetch",
            **(attributes or {})
        }
        
        return self.trace_function(
            name=f"fetch.{provider_name}.{endpoint}",
            kind=SpanKind.CLIENT,
            attributes=span_attributes
        )
    
    def _add_function_args_to_span(self, span, args, kwargs):
        """Add function arguments to span attributes."""
        try:
            # Add positional arguments (safely)
            for i, arg in enumerate(args[:5]):  # Limit to first 5 args
                if isinstance(arg, (str, int, float, bool)):
                    span.set_attribute(f"arg.{i}", str(arg))
                else:
                    span.set_attribute(f"arg.{i}.type", type(arg).__name__)
            
            # Add keyword arguments (safely)
            for key, value in list(kwargs.items())[:5]:  # Limit to first 5 kwargs
                if isinstance(value, (str, int, float, bool)):
                    span.set_attribute(f"kwarg.{key}", str(value))
                else:
                    span.set_attribute(f"kwarg.{key}.type", type(value).__name__)
                    
        except Exception as e:
            self.logger.debug(f"Failed to add function args to span: {e}")
    
    def _should_sample(self) -> bool:
        """Determine if trace should be sampled."""
        return random.random() < self.sample_rate
    
    def add_span_event(self, span, name: str, attributes: Optional[Dict[str, Any]] = None):
        """
        Add an event to the current span.
        
        Args:
            span: Active span
            name: Event name
            attributes: Event attributes
        """
        if hasattr(span, 'add_event'):
            span.add_event(name, attributes or {})
    
    def set_span_status(self, span, status: StatusCode, description: str = None):
        """
        Set span status.
        
        Args:
            span: Active span
            status: Status code
            description: Status description
        """
        if hasattr(span, 'set_status'):
            span.set_status(Status(status, description))
    
    def inject_context(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Inject tracing context into headers.
        
        Args:
            headers: Existing headers to inject into
            
        Returns:
            Headers with tracing context
        """
        from opentelemetry.propagate import inject
        
        headers = headers or {}
        
        @inject
        def _get_headers(headers_dict):
            return headers_dict
        
        injected_headers = _get_headers(headers)
        return injected_headers
    
    def extract_context(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract tracing context from headers.
        
        Args:
            headers: Headers containing tracing context
            
        Returns:
            Extracted tracing context
        """
        from opentelemetry.propagate import extract
        
        context = extract(headers)
        return context
    
    def get_trace_statistics(self) -> Dict[str, Any]:
        """
        Get tracing statistics.
        
        Returns:
            Tracing statistics dictionary
        """
        return {
            "service_name": self.service_name,
            "jaeger_endpoint": self.jaeger_endpoint,
            "enabled": self.enable_tracing,
            "sample_rate": self.sample_rate,
            "span_processors_count": len(self._span_processors)
        }
    
    def shutdown(self):
        """Shutdown the tracer."""
        if self._span_processors:
            for processor in self._span_processors:
                if hasattr(processor, 'shutdown'):
                    processor.shutdown()
        
        self.logger.info("OpenTelemetry tracer shutdown")


class NoOpSpan:
    """No-operation span for when tracing is disabled."""
    
    def __init__(self):
        pass
    
    def set_attribute(self, key: str, value: Any):
        pass
    
    def set_status(self, status: Status, description: str = None):
        pass
    
    def record_exception(self, exception: Exception):
        pass
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        pass
    
    def end(self):
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


# Global tracer instance
_global_tracer: Optional[OpenTelemetryTracer] = None


def get_tracer(**kwargs) -> OpenTelemetryTracer:
    """
    Get or create the global tracer instance.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global OpenTelemetryTracer instance
    """
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = OpenTelemetryTracer(**kwargs)
    return _global_tracer


def trace_span(
    name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None
):
    """
    Decorator for creating spans.
    
    Args:
        name: Span name
        kind: Span kind
        attributes: Span attributes
        
    Returns:
        Decorator function
    """
    tracer = get_tracer()
    return tracer.trace_function(name, kind, attributes)


# Import required modules
import random
import asyncio
