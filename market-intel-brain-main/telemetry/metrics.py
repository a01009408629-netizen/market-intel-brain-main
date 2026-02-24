"""
Prometheus Metrics Implementation

This module provides Prometheus metrics collection for monitoring
latency, success/failure rates, and other performance indicators.
"""

import time
import logging
from typing import Optional, Dict, Any, Union
from threading import Lock
from dataclasses import dataclass

try:
    from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
    from prometheus_client import push_to_gateway
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Create dummy classes for when prometheus_client is not available
    class Counter:
        def __init__(self, *args, **kwargs): pass
        def inc(self, amount=1): pass
        def labels(self, **kwargs): return self
    
    class Histogram:
        def __init__(self, *args, **kwargs): pass
        def observe(self, amount): pass
        def labels(self, **kwargs): return self
    
    class Gauge:
        def __init__(self, *args, **kwargs): pass
        def set(self, value): pass
        def labels(self, **kwargs): return self
    
    class CollectorRegistry:
        def __init__(self): pass
        def register(self, collector): pass
    
    def push_to_gateway(*args, **kwargs): pass


@dataclass
class MetricConfig:
    """Configuration for Prometheus metrics."""
    registry: CollectorRegistry = None
    namespace: str = "market_intel_brain"
    subsystem: str = "adapters"
    push_gateway: Optional[str] = None
    push_interval: int = 60  # seconds


class PrometheusMetrics:
    """
    Prometheus metrics collector for adapter monitoring.
    
    This class provides comprehensive metrics collection including latency
    histograms, success/failure counters, and performance gauges.
    """
    
    def __init__(
        self,
        config: Optional[MetricConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Prometheus metrics.
        
        Args:
            config: Metrics configuration
            logger: Logger instance
        """
        self.config = config or MetricConfig()
        self.logger = logger or logging.getLogger("PrometheusMetrics")
        self._lock = Lock()
        
        if not PROMETHEUS_AVAILABLE:
            self.logger.warning("prometheus_client not available, using dummy metrics")
            self._setup_dummy_metrics()
        else:
            self._setup_prometheus_metrics()
        
        self.logger.info(f"PrometheusMetrics initialized (namespace={self.config.namespace})")
    
    def _setup_prometheus_metrics(self):
        """Set up Prometheus metrics."""
        self.registry = self.config.registry or CollectorRegistry()
        
        # Request metrics
        self.request_total = Counter(
            'adapter_requests_total',
            'Total number of adapter requests',
            ['provider', 'operation', 'status'],
            registry=self.registry
        )
        
        # Latency metrics
        self.request_duration = Histogram(
            'adapter_request_duration_seconds',
            'Adapter request duration in seconds',
            ['provider', 'operation'],
            registry=self.registry
        )
        
        # Active requests gauge
        self.active_requests = Gauge(
            'adapter_active_requests',
            'Number of active adapter requests',
            ['provider'],
            registry=self.registry
        )
        
        # Error metrics
        self.error_total = Counter(
            'adapter_errors_total',
            'Total number of adapter errors',
            ['provider', 'operation', 'error_type'],
            registry=self.registry
        )
        
        # Success rate metrics
        self.success_rate = Gauge(
            'adapter_success_rate',
            'Adapter success rate (0-1)',
            ['provider'],
            registry=self.registry
        )
        
        # Data volume metrics
        self.data_volume_total = Counter(
            'adapter_data_volume_total',
            'Total data volume processed',
            ['provider', 'data_type'],
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_hits_total = Counter(
            'adapter_cache_hits_total',
            'Total number of cache hits',
            ['provider', 'cache_type'],
            registry=self.registry
        )
        
        self.cache_misses_total = Counter(
            'adapter_cache_misses_total',
            'Total number of cache misses',
            ['provider', 'cache_type'],
            registry=self.registry
        )
        
        # Rate limiting metrics
        self.rate_limited_total = Counter(
            'adapter_rate_limited_total',
            'Total number of rate limit events',
            ['provider'],
            registry=self.registry
        )
        
        # Connection metrics
        self.connection_errors_total = Counter(
            'adapter_connection_errors_total',
            'Total number of connection errors',
            ['provider'],
            registry=self.registry
        )
        
        # Timeout metrics
        self.timeout_total = Counter(
            'adapter_timeouts_total',
            'Total number of timeouts',
            ['provider', 'operation'],
            registry=self.registry
        )
        
        # Custom metrics storage
        self._custom_metrics = {}
    
    def _setup_dummy_metrics(self):
        """Set up dummy metrics when prometheus_client is not available."""
        self.registry = None
        
        # Create dummy metrics
        self.request_total = DummyCounter()
        self.request_duration = DummyHistogram()
        self.active_requests = DummyGauge()
        self.error_total = DummyCounter()
        self.success_rate = DummyGauge()
        self.data_volume_total = DummyCounter()
        self.cache_hits_total = DummyCounter()
        self.cache_misses_total = DummyCounter()
        self.rate_limited_total = DummyCounter()
        self.connection_errors_total = DummyCounter()
        self.timeout_total = DummyCounter()
        self._custom_metrics = {}
    
    def record_request_start(self, provider: str, operation: str):
        """
        Record the start of a request.
        
        Args:
            provider: Provider name
            operation: Operation type
        """
        self.active_requests.labels(provider=provider).inc()
    
    def record_request_success(
        self,
        provider: str,
        operation: str,
        duration: float,
        data_size: Optional[int] = None
    ):
        """
        Record a successful request.
        
        Args:
            provider: Provider name
            operation: Operation type
            duration: Request duration in seconds
            data_size: Size of data returned
        """
        with self._lock:
            # Record request count
            self.request_total.labels(
                provider=provider,
                operation=operation,
                status='success'
            ).inc()
            
            # Record duration
            self.request_duration.labels(provider=provider, operation=operation).observe(duration)
            
            # Record data volume
            if data_size is not None:
                self.data_volume_total.labels(
                    provider=provider,
                    data_type='response'
                ).inc(data_size)
            
            # Update success rate (simplified)
            self._update_success_rate(provider)
    
    def record_request_error(
        self,
        provider: str,
        operation: str,
        error_type: str,
        duration: Optional[float] = None
    ):
        """
        Record a request error.
        
        Args:
            provider: Provider name
            operation: Operation type
            error_type: Type of error
            duration: Request duration in seconds
        """
        with self._lock:
            # Record error count
            self.error_total.labels(
                provider=provider,
                operation=operation,
                error_type=error_type
            ).inc()
            
            # Record as failed request
            self.request_total.labels(
                provider=provider,
                operation=operation,
                status='error'
            ).inc()
            
            # Record duration if provided
            if duration is not None:
                self.request_duration.labels(provider=provider, operation=operation).observe(duration)
            
            # Update success rate
            self._update_success_rate(provider)
    
    def record_request_end(self, provider: str):
        """
        Record the end of a request.
        
        Args:
            provider: Provider name
        """
        self.active_requests.labels(provider=provider).dec()
    
    def record_cache_hit(self, provider: str, cache_type: str = 'default'):
        """
        Record a cache hit.
        
        Args:
            provider: Provider name
            cache_type: Type of cache
        """
        self.cache_hits_total.labels(provider=provider, cache_type=cache_type).inc()
    
    def record_cache_miss(self, provider: str, cache_type: str = 'default'):
        """
        Record a cache miss.
        
        Args:
            provider: Provider name
            cache_type: Type of cache
        """
        self.cache_misses_total.labels(provider=provider, cache_type=cache_type).inc()
    
    def record_rate_limit(self, provider: str):
        """
        Record a rate limit event.
        
        Args:
            provider: Provider name
        """
        self.rate_limited_total.labels(provider=provider).inc()
    
    def record_connection_error(self, provider: str):
        """
        Record a connection error.
        
        Args:
            provider: Provider name
        """
        self.connection_errors_total.labels(provider=provider).inc()
    
    def record_timeout(self, provider: str, operation: str):
        """
        Record a timeout event.
        
        Args:
            provider: Provider name
            operation: Operation type
        """
        self.timeout_total.labels(provider=provider, operation=operation).inc()
    
    def record_data_volume(self, provider: str, data_type: str, volume: int):
        """
        Record data volume.
        
        Args:
            provider: Provider name
            data_type: Type of data
            volume: Volume amount
        """
        self.data_volume_total.labels(provider=provider, data_type=data_type).inc(volume)
    
    def _update_success_rate(self, provider: str):
        """
        Update success rate gauge for a provider.
        
        Args:
            provider: Provider name
        """
        try:
            # Get current counts
            total_requests = (
                self.request_total.labels(provider=provider, operation='*', status='success')._value.get() +
                self.request_total.labels(provider=provider, operation='*', status='error')._value.get()
            )
            
            if total_requests > 0:
                success_count = self.request_total.labels(provider=provider, operation='*', status='success')._value.get()
                success_rate = success_count / total_requests
                self.success_rate.labels(provider=provider).set(success_rate)
        
        except Exception as e:
            self.logger.error(f"Failed to update success rate for {provider}: {e}")
    
    def create_custom_counter(
        self,
        name: str,
        documentation: str,
        labelnames: Optional[list] = None
    ):
        """
        Create a custom counter metric.
        
        Args:
            name: Metric name
            documentation: Metric description
            labelnames: List of label names
            
        Returns:
            Counter metric
        """
        if not PROMETHEUS_AVAILABLE:
            return DummyCounter()
        
        with self._lock:
            if name in self._custom_metrics:
                return self._custom_metrics[name]
            
            counter = Counter(
                name,
                documentation,
                labelnames or [],
                registry=self.registry
            )
            
            self._custom_metrics[name] = counter
            return counter
    
    def create_custom_histogram(
        self,
        name: str,
        documentation: str,
        labelnames: Optional[list] = None,
        buckets: Optional[list] = None
    ):
        """
        Create a custom histogram metric.
        
        Args:
            name: Metric name
            documentation: Metric description
            labelnames: List of label names
            buckets: Histogram buckets
            
        Returns:
            Histogram metric
        """
        if not PROMETHEUS_AVAILABLE:
            return DummyHistogram()
        
        with self._lock:
            if name in self._custom_metrics:
                return self._custom_metrics[name]
            
            histogram = Histogram(
                name,
                documentation,
                labelnames or [],
                buckets=buckets,
                registry=self.registry
            )
            
            self._custom_metrics[name] = histogram
            return histogram
    
    def create_custom_gauge(
        self,
        name: str,
        documentation: str,
        labelnames: Optional[list] = None
    ):
        """
        Create a custom gauge metric.
        
        Args:
            name: Metric name
            documentation: Metric description
            labelnames: List of label names
            
        Returns:
            Gauge metric
        """
        if not PROMETHEUS_AVAILABLE:
            return DummyGauge()
        
        with self._lock:
            if name in self._custom_metrics:
                return self._custom_metrics[name]
            
            gauge = Gauge(
                name,
                documentation,
                labelnames or [],
                registry=self.registry
            )
            
            self._custom_metrics[name] = gauge
            return gauge
    
    def get_metric_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all metrics.
        
        Returns:
            Metrics summary dictionary
        """
        summary = {
            "namespace": self.config.namespace,
            "subsystem": self.config.subsystem,
            "prometheus_available": PROMETHEUS_AVAILABLE,
            "custom_metrics_count": len(self._custom_metrics)
        }
        
        if PROMETHEUS_AVAILABLE:
            # Add registry info
            summary["registry"] = {
                "collectors": list(self.registry._collector_to_names.keys()),
                "names": list(self.registry._names_to_collectors.keys())
            }
        
        return summary
    
    def push_to_gateway(self):
        """Push metrics to Prometheus gateway."""
        if not PROMETHEUS_AVAILABLE or not self.config.push_gateway:
            return
        
        try:
            push_to_gateway(
                self.config.push_gateway,
                job='market_intel_brain_metrics',
                registry=self.registry
            )
            self.logger.info(f"Pushed metrics to gateway: {self.config.push_gateway}")
        except Exception as e:
            self.logger.error(f"Failed to push metrics to gateway: {e}")
    
    def start_push_loop(self):
        """Start background loop for pushing to gateway."""
        if not self.config.push_gateway:
            return
        
        import threading
        import time
        
        def push_loop():
            while True:
                try:
                    self.push_to_gateway()
                    time.sleep(self.config.push_interval)
                except Exception as e:
                    self.logger.error(f"Error in push loop: {e}")
                    time.sleep(self.config.push_interval)
        
        push_thread = threading.Thread(target=push_loop, daemon=True)
        push_thread.start()
        self.logger.info(f"Started push loop (interval: {self.config.push_interval}s)")
    
    def get_metrics_data(self) -> Dict[str, Any]:
        """
        Get current metrics data for debugging.
        
        Returns:
            Current metrics values
        """
        if not PROMETHEUS_AVAILABLE:
            return {"error": "Prometheus not available"}
        
        try:
            # This is a simplified version - in production you'd use the HTTP endpoint
            from prometheus_client import generate_latest
            return generate_latest(self.registry)
        except Exception as e:
            return {"error": f"Failed to generate metrics: {e}"}


# Dummy classes for when prometheus_client is not available
class DummyCounter:
    def __init__(self, *args, **kwargs):
        self._value = 0
        self._labels = {}
    
    def inc(self, amount=1):
        self._value += amount
    
    def labels(self, **kwargs):
        self._labels.update(kwargs)
        return self
    
    @property
    def _value(self):
        return self._value


class DummyHistogram:
    def __init__(self, *args, **kwargs):
        self._observations = []
    
    def observe(self, amount):
        self._observations.append(amount)
    
    def labels(self, **kwargs):
        return self


class DummyGauge:
    def __init__(self, *args, **kwargs):
        self._value = 0
        self._labels = {}
    
    def set(self, value):
        self._value = value
    
    def labels(self, **kwargs):
        self._labels.update(kwargs)
        return self


# Global metrics instance
_global_metrics: Optional[PrometheusMetrics] = None


def get_metrics(**kwargs) -> PrometheusMetrics:
    """
    Get or create the global metrics instance.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global PrometheusMetrics instance
    """
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = PrometheusMetrics(**kwargs)
    return _global_metrics
