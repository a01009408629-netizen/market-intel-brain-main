"""
Advanced Telemetry System

This module provides comprehensive monitoring and observability using
OpenTelemetry for distributed tracing and Prometheus for metrics collection.
"""

from .tracer import OpenTelemetryTracer, get_tracer, trace_span
from .metrics import PrometheusMetrics, get_metrics
from .middleware import TelemetryMiddleware, telemetry_decorator
from .collector import TelemetryCollector, get_collector
from .exporter import PrometheusExporter, get_exporter

__all__ = [
    # Core components
    'OpenTelemetryTracer',
    'PrometheusMetrics',
    'TelemetryMiddleware',
    'TelemetryCollector',
    'PrometheusExporter',
    
    # Convenience functions
    'get_tracer',
    'trace_span',
    'get_metrics',
    'get_collector',
    'get_exporter',
    'telemetry_decorator'
]

# Global instances
_global_tracer = None
_global_metrics = None
_global_collector = None
_global_exporter = None


def get_global_tracer(**kwargs) -> OpenTelemetryTracer:
    """Get or create the global tracer instance."""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = OpenTelemetryTracer(**kwargs)
    return _global_tracer


def get_global_metrics(**kwargs) -> PrometheusMetrics:
    """Get or create the global metrics instance."""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = PrometheusMetrics(**kwargs)
    return _global_metrics


def get_global_collector(**kwargs) -> TelemetryCollector:
    """Get or create the global collector instance."""
    global _global_collector
    if _global_collector is None:
        _global_collector = TelemetryCollector(**kwargs)
    return _global_collector


def get_global_exporter(**kwargs) -> PrometheusExporter:
    """Get or create the global exporter instance."""
    global _global_exporter
    if _global_exporter is None:
        _global_exporter = PrometheusExporter(**kwargs)
    return _global_exporter
