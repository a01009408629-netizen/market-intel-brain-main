"""
OpenTelemetry Tracer - Distributed Tracing Integration

Enterprise-grade distributed tracing with span tracking,
performance monitoring, and trace context propagation.
"""

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Union, Callable
import json

try:
    from opentelemetry import trace, baggage, context
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.semantic_conventions.trace import SpanKind
    from opentelemetry.propagate import inject, extract
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    
    # Fallback classes
    class SpanKind:
        SERVER = "server"
        CLIENT = "client"
        PRODUCER = "producer"
        CONSUMER = "consumer"
        INTERNAL = "internal"
    
    class trace:
        class Span:
            def __init__(self, name):
                self.name = name
                self.start_time = time.time()
                self.end_time = None
                self.attributes = {}
                self.events = []
                self.status = None
            
            def set_attribute(self, key, value):
                self.attributes[key] = value
            
            def add_event(self, name, attributes=None):
                self.events.append({
                    "name": name,
                    "timestamp": time.time(),
                    "attributes": attributes or {}
                })
            
            def set_status(self, status):
                self.status = status
            
            def end(self):
                self.end_time = time.time()
    
    class TracerProvider:
        def __init__(self):
            pass
        
        def get_tracer(self, name, version=None):
            return MockTracer()
    
    class MockTracer:
        def start_span(self, name, kind=None):
            return trace.Span(name)
        
        def start_as_current_span(self, name, kind=None):
            return self._span_context_manager(name, kind)
        
        def _span_context_manager(self, name, kind):
            return MockSpanContextManager(trace.Span(name))
    
    class MockSpanContextManager:
        def __init__(self, span):
            self.span = span
        
        async def __aenter__(self):
            return self.span
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self.span.end()
    
    class baggage:
        @staticmethod
        def set_baggage(key, value):
            return {}
    
    class context:
        @staticmethod
        def attach(context):
            return context
        
        @staticmethod
        def detach(token):
            pass
    
    def inject(headers):
        headers["traceparent"] = f"00-{uuid.uuid4().hex}-{uuid.uuid4().hex[:16]}-01"
    
    def extract(headers):
        return {}


from .config import TelemetryConfig


class SpanStatus(Enum):
    """Span status enumeration."""
    OK = "ok"
    ERROR = "error"
    UNSET = "unset"


@dataclass
class TraceContext:
    """Trace context information."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)
    sampled: bool = True
    
    def to_headers(self) -> Dict[str, str]:
        """Convert trace context to HTTP headers."""
        headers = {}
        inject(headers)
        return headers
    
    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> "TraceContext":
        """Create trace context from HTTP headers."""
        try:
            ctx = extract(headers)
            return cls(
                trace_id=getattr(ctx, 'trace_id', str(uuid.uuid4())),
                span_id=getattr(ctx, 'span_id', str(uuid.uuid4())[:16]),
                baggage=getattr(ctx, 'baggage', {})
            )
        except:
            return cls(
                trace_id=str(uuid.uuid4()),
                span_id=str(uuid.uuid4())[:16]
            )


@dataclass
class SpanMetrics:
    """Span performance metrics."""
    span_name: str
    span_kind: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    attributes_count: int = 0
    events_count: int = 0
    error: Optional[str] = None


class OpenTelemetryTracer:
    """
    Enterprise-grade OpenTelemetry tracer with distributed tracing.
    
    Features:
    - Distributed trace propagation
    - Span lifecycle management
    - Performance monitoring
    - Automatic instrumentation
    - Context propagation
    """
    
    def __init__(
        self,
        config: Optional[TelemetryConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.config = config or TelemetryConfig()
        self.logger = logger or logging.getLogger("OpenTelemetryTracer")
        
        # Trace context
        self._current_trace_context: ContextVar[Optional[TraceContext]] = ContextVar(
            "current_trace_context", default=None
        )
        
        # Tracer provider
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer: Optional[Any] = None
        
        # Performance metrics
        self.spans_created = 0
        self.spans_completed = 0
        self.total_span_duration_ms = 0.0
        self.error_spans = 0
        self._span_metrics: List[SpanMetrics] = []
        
        # Initialize tracer
        self._initialize_tracer()
        
        self.logger.info(f"OpenTelemetryTracer initialized: {self.config.service_name}")
    
    def _initialize_tracer(self):
        """Initialize OpenTelemetry tracer."""
        try:
            if not OPENTELEMETRY_AVAILABLE:
                self.logger.warning("OpenTelemetry not available, using mock tracer")
                self.tracer_provider = TracerProvider()
                self.tracer = self.tracer_provider.get_tracer(
                    self.config.service_name,
                    self.config.service_version
                )
                return
            
            # Create resource
            resource = Resource.create({
                "service.name": self.config.service_name,
                "service.version": self.config.service_version,
                "service.namespace": self.config.service_namespace,
                "deployment.environment": self.config.environment
            })
            
            # Create tracer provider
            self.tracer_provider = TracerProvider(resource=resource)
            
            # Configure exporter
            if self.config.otlp_endpoint:
                exporter = OTLPSpanExporter(
                    endpoint=self.config.otlp_endpoint,
                    insecure=self.config.otlp_insecure
                )
                span_processor = BatchSpanProcessor(exporter)
                self.tracer_provider.add_span_processor(span_processor)
            
            # Set global tracer provider
            trace.set_tracer_provider(self.tracer_provider)
            
            # Get tracer
            self.tracer = trace.get_tracer(
                self.config.service_name,
                self.config.service_version
            )
            
            self.logger.info("OpenTelemetry tracer initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenTelemetry tracer: {e}")
            # Fallback to mock tracer
            self.tracer_provider = TracerProvider()
            self.tracer = self.tracer_provider.get_tracer(
                self.config.service_name,
                self.config.service_version
            )
    
    def get_current_trace_context(self) -> Optional[TraceContext]:
        """Get current trace context."""
        return self._current_trace_context.get()
    
    def set_trace_context(self, trace_context: TraceContext):
        """Set current trace context."""
        self._current_trace_context.set(trace_context)
    
    @asynccontextmanager
    async def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        links: Optional[List[Any]] = None
    ):
        """Start a new span with context management."""
        span = None
        span_metrics = SpanMetrics(
            span_name=name,
            span_kind=kind,
            start_time=time.time()
        )
        
        try:
            # Start span
            if OPENTELEMETRY_AVAILABLE:
                span = self.tracer.start_span(name, kind=kind, links=links)
            else:
                span = self.tracer.start_span(name, kind=kind)
            
            # Set attributes
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))
                span_metrics.attributes_count = len(attributes)
            
            # Update metrics
            self.spans_created += 1
            
            # Set trace context
            if hasattr(span, 'get_span_context'):
                span_context = span.get_span_context()
                trace_context = TraceContext(
                    trace_id=format(span_context.trace_id, '032x'),
                    span_id=format(span_context.span_id, '016x')
                )
                self.set_trace_context(trace_context)
            
            yield span
            
            # Mark as successful
            span_metrics.status = SpanStatus.OK
            
        except Exception as e:
            # Mark as error
            span_metrics.status = SpanStatus.ERROR
            span_metrics.error = str(e)
            self.error_spans += 1
            
            if span:
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.add_event("exception", {
                    "exception.message": str(e),
                    "exception.stacktrace": str(e.__traceback__)
                })
            
            raise
        
        finally:
            # End span
            if span:
                span.end()
            
            # Update metrics
            span_metrics.end_time = time.time()
            span_metrics.duration_ms = (span_metrics.end_time - span_metrics.start_time) * 1000
            
            self.spans_completed += 1
            self.total_span_duration_ms += span_metrics.duration_ms
            self._span_metrics.append(span_metrics)
            
            # Keep only recent metrics
            if len(self._span_metrics) > 1000:
                self._span_metrics = self._span_metrics[-500:]
    
    @asynccontextmanager
    async def start_as_current_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """Start span as current span."""
        if OPENTELEMETRY_AVAILABLE:
            async with self.tracer.start_as_current_span(name, kind=kind) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))
                yield span
        else:
            async with self.start_span(name, kind, attributes) as span:
                yield span
    
    def inject_headers(self, headers: Dict[str, str]):
        """Inject trace context into HTTP headers."""
        try:
            inject(headers)
        except Exception as e:
            self.logger.error(f"Failed to inject headers: {e}")
    
    def extract_headers(self, headers: Dict[str, str]) -> TraceContext:
        """Extract trace context from HTTP headers."""
        try:
            return TraceContext.from_headers(headers)
        except Exception as e:
            self.logger.error(f"Failed to extract headers: {e}")
            return TraceContext(
                trace_id=str(uuid.uuid4()),
                span_id=str(uuid.uuid4())[:16]
            )
    
    def add_baggage(self, key: str, value: str):
        """Add baggage to current context."""
        try:
            if OPENTELEMETRY_AVAILABLE:
                baggage.set_baggage(key, value)
        except Exception as e:
            self.logger.error(f"Failed to add baggage: {e}")
    
    def create_trace_context(self) -> TraceContext:
        """Create new trace context."""
        return TraceContext(
            trace_id=str(uuid.uuid4()),
            span_id=str(uuid.uuid4())[:16]
        )
    
    def trace_function(self, name: Optional[str] = None, kind: SpanKind = SpanKind.INTERNAL):
        """Decorator for tracing functions."""
        def decorator(func: Callable):
            async def async_wrapper(*args, **kwargs):
                span_name = name or f"{func.__module__}.{func.__name__}"
                
                async with self.start_span(span_name, kind=kind) as span:
                    # Add function attributes
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    span.set_attribute("function.args_count", len(args))
                    span.set_attribute("function.kwargs_count", len(kwargs))
                    
                    try:
                        result = await func(*args, **kwargs)
                        span.set_attribute("function.success", True)
                        return result
                    except Exception as e:
                        span.set_attribute("function.success", False)
                        span.set_attribute("function.error", str(e))
                        raise
            
            def sync_wrapper(*args, **kwargs):
                span_name = name or f"{func.__module__}.{func.__name__}"
                
                # For sync functions, we'll use a simple span
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = (time.time() - start_time) * 1000
                    
                    # Log span completion
                    self.logger.debug(f"Span completed: {span_name} in {duration:.2f}ms")
                    return result
                except Exception as e:
                    duration = (time.time() - start_time) * 1000
                    self.logger.error(f"Span failed: {span_name} in {duration:.2f}ms - {e}")
                    raise
            
            # Return appropriate wrapper based on function type
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    def trace_method(self, name: Optional[str] = None, kind: SpanKind = SpanKind.INTERNAL):
        """Decorator for tracing class methods."""
        def decorator(method: Callable):
            async def async_wrapper(self, *args, **kwargs):
                span_name = name or f"{self.__class__.__name__}.{method.__name__}"
                
                async with self.start_span(span_name, kind=kind) as span:
                    # Add method attributes
                    span.set_attribute("method.name", method.__name__)
                    span.set_attribute("class.name", self.__class__.__name__)
                    span.set_attribute("method.args_count", len(args))
                    span.set_attribute("method.kwargs_count", len(kwargs))
                    
                    try:
                        result = await method(self, *args, **kwargs)
                        span.set_attribute("method.success", True)
                        return result
                    except Exception as e:
                        span.set_attribute("method.success", False)
                        span.set_attribute("method.error", str(e))
                        raise
            
            def sync_wrapper(self, *args, **kwargs):
                span_name = name or f"{self.__class__.__name__}.{method.__name__}"
                
                start_time = time.time()
                try:
                    result = method(self, *args, **kwargs)
                    duration = (time.time() - start_time) * 1000
                    
                    self.logger.debug(f"Method span completed: {span_name} in {duration:.2f}ms")
                    return result
                except Exception as e:
                    duration = (time.time() - start_time) * 1000
                    self.logger.error(f"Method span failed: {span_name} in {duration:.2f}ms - {e}")
                    raise
            
            # Return appropriate wrapper based on function type
            if asyncio.iscoroutinefunction(method):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get tracer metrics."""
        if not self._span_metrics:
            return {
                "tracer_metrics": {
                    "spans_created": self.spans_created,
                    "spans_completed": self.spans_completed,
                    "error_spans": self.error_spans,
                    "avg_span_duration_ms": 0.0,
                    "total_span_duration_ms": self.total_span_duration_ms
                }
            }
        
        # Calculate statistics
        recent_spans = self._span_metrics[-100:]  # Last 100 spans
        avg_duration = sum(s.duration_ms for s in recent_spans if s.duration_ms) / max(len(recent_spans), 1)
        
        # Span kind distribution
        kind_distribution = {}
        for span in recent_spans:
            kind = span.span_kind
            kind_distribution[kind] = kind_distribution.get(kind, 0) + 1
        
        # Error rate
        error_rate = self.error_spans / max(self.spans_completed, 1)
        
        return {
            "tracer_metrics": {
                "spans": {
                    "created": self.spans_created,
                    "completed": self.spans_completed,
                    "errors": self.error_spans,
                    "error_rate": error_rate
                },
                "performance": {
                    "avg_duration_ms": avg_duration,
                    "total_duration_ms": self.total_span_duration_ms,
                    "recent_spans_count": len(recent_spans)
                },
                "distribution": kind_distribution,
                "configuration": {
                    "service_name": self.config.service_name,
                    "service_version": self.config.service_version,
                    "otlp_endpoint": self.config.otlp_endpoint
                }
            }
        }
    
    async def flush(self):
        """Flush pending spans."""
        try:
            if self.tracer_provider and hasattr(self.tracer_provider, 'force_flush'):
                self.tracer_provider.force_flush()
                self.logger.debug("Tracer flushed")
        except Exception as e:
            self.logger.error(f"Failed to flush tracer: {e}")
    
    async def shutdown(self):
        """Shutdown tracer."""
        try:
            if self.tracer_provider and hasattr(self.tracer_provider, 'shutdown'):
                await self.tracer_provider.shutdown()
                self.logger.info("Tracer shutdown completed")
        except Exception as e:
            self.logger.error(f"Failed to shutdown tracer: {e}")


# Global tracer instance
_tracer: Optional[OpenTelemetryTracer] = None


def get_tracer(config: Optional[TelemetryConfig] = None) -> OpenTelemetryTracer:
    """Get or create global tracer."""
    global _tracer
    if _tracer is None:
        _tracer = OpenTelemetryTracer(config)
    return _tracer


async def initialize_tracer(config: Optional[TelemetryConfig] = None) -> OpenTelemetryTracer:
    """Initialize and return global tracer."""
    tracer = get_tracer(config)
    return tracer


# Decorators for easy usage
def trace_span(name: Optional[str] = None, kind: SpanKind = SpanKind.INTERNAL):
    """Decorator for tracing functions."""
    tracer = get_tracer()
    return tracer.trace_function(name, kind)


def trace_method(name: Optional[str] = None, kind: SpanKind = SpanKind.INTERNAL):
    """Decorator for tracing class methods."""
    tracer = get_tracer()
    return tracer.trace_method(name, kind)
