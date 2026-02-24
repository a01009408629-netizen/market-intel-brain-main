"""
Metrics Collector - Performance Monitoring

Enterprise-grade metrics collection with performance monitoring,
system metrics, and OpenTelemetry integration.
"""

import asyncio
import logging
import psutil
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union
from enum import Enum

try:
    from opentelemetry import metrics
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    OPENTELEMETRY_METRICS_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_METRICS_AVAILABLE = False


class MetricType(Enum):
    """Metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    UPDOWN_COUNTER = "updown_counter"


@dataclass
class MetricPoint:
    """Single metric data point."""
    name: str
    value: Union[int, float]
    metric_type: MetricType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""
    description: str = ""


@dataclass
class SystemMetrics:
    """System performance metrics."""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PerformanceMetrics:
    """Application performance metrics."""
    request_count: int
    error_count: int
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    throughput_rps: float
    error_rate: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MetricsCollector:
    """
    Enterprise-grade metrics collector with OpenTelemetry integration.
    
    Features:
    - System metrics collection
    - Application performance metrics
    - Custom metrics registration
    - Real-time monitoring
    - OpenTelemetry integration
    """
    
    def __init__(
        self,
        service_name: str = "market-intel-brain",
        collection_interval_seconds: int = 10,
        retention_minutes: int = 60,
        logger: Optional[logging.Logger] = None
    ):
        self.service_name = service_name
        self.collection_interval_seconds = collection_interval_seconds
        self.retention_minutes = retention_minutes
        self.logger = logger or logging.getLogger("MetricsCollector")
        
        # Metrics storage
        self._metric_points: deque = deque(maxlen=retention_minutes * 60 // collection_interval_seconds)
        self._custom_metrics: Dict[str, List[MetricPoint]] = {}
        
        # System metrics
        self._system_metrics: deque = deque(maxlen=retention_minutes * 60 // collection_interval_seconds)
        self._performance_metrics: deque = deque(maxlen=retention_minutes * 60 // collection_interval_seconds)
        
        # OpenTelemetry metrics
        self.meter_provider: Optional[MeterProvider] = None
        self.meter: Optional[Any] = None
        self._otel_metrics: Dict[str, Any] = {}
        
        # Collection task
        self.collection_task: Optional[asyncio.Task] = None
        self.is_collecting = False
        
        # Performance tracking
        self._response_times: deque = deque(maxlen=1000)
        self._request_timestamps: deque = deque(maxlen=1000)
        
        # Initialize metrics
        self._initialize_metrics()
        
        self.logger.info(f"MetricsCollector initialized: {service_name}")
    
    def _initialize_metrics(self):
        """Initialize metrics collection."""
        try:
            # Initialize OpenTelemetry metrics if available
            if OPENTELEMETRY_METRICS_AVAILABLE:
                self._initialize_opentelemetry_metrics()
            
            # Start collection task
            self._start_collection()
            
            self.logger.info("Metrics collection initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize metrics: {e}")
    
    def _initialize_opentelemetry_metrics(self):
        """Initialize OpenTelemetry metrics."""
        try:
            # Create meter provider
            self.meter_provider = MeterProvider()
            
            # Configure exporter (if endpoint is available)
            otlp_endpoint = os.getenv("OTEL_ENDPOINT")
            if otlp_endpoint:
                exporter = OTLPMetricExporter(endpoint=otlp_endpoint)
                reader = PeriodicExportingMetricReader(
                    exporter,
                    export_interval_millis=60000  # 1 minute
                )
                self.meter_provider.register_metric_reader(reader)
            
            # Set global meter provider
            metrics.set_meter_provider(self.meter_provider)
            
            # Get meter
            self.meter = self.meter_provider.get_meter(self.service_name)
            
            # Create instruments
            self._otel_metrics = {
                "requests_total": self.meter.create_counter(
                    "requests_total",
                    description="Total number of requests"
                ),
                "errors_total": self.meter.create_counter(
                    "errors_total",
                    description="Total number of errors"
                ),
                "response_time": self.meter.create_histogram(
                    "response_time_ms",
                    description="Response time in milliseconds"
                ),
                "cpu_usage": self.meter.create_gauge(
                    "cpu_usage_percent",
                    description="CPU usage percentage"
                ),
                "memory_usage": self.meter.create_gauge(
                    "memory_usage_percent",
                    description="Memory usage percentage"
                )
            }
            
            self.logger.info("OpenTelemetry metrics initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenTelemetry metrics: {e}")
    
    def _start_collection(self):
        """Start metrics collection task."""
        if not self.is_collecting:
            self.is_collecting = True
            self.collection_task = asyncio.create_task(self._collection_loop())
            self.logger.info("Metrics collection started")
    
    async def _collection_loop(self):
        """Background metrics collection loop."""
        while self.is_collecting:
            try:
                # Collect system metrics
                system_metrics = self._collect_system_metrics()
                self._system_metrics.append(system_metrics)
                
                # Update OpenTelemetry gauges
                if self.meter:
                    self._otel_metrics.get("cpu_usage").set(system_metrics.cpu_percent)
                    self._otel_metrics.get("memory_usage").set(system_metrics.memory_percent)
                
                # Calculate performance metrics
                performance_metrics = self._calculate_performance_metrics()
                if performance_metrics:
                    self._performance_metrics.append(performance_metrics)
                
                await asyncio.sleep(self.collection_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(self.collection_interval_seconds)
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect system performance metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_usage_percent = disk.percent
            disk_free_gb = disk.free / (1024 * 1024 * 1024)
            
            # Network metrics
            network = psutil.net_io_counters()
            network_bytes_sent = network.bytes_sent
            network_bytes_recv = network.bytes_recv
            
            # Process count
            process_count = len(psutil.pids())
            
            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=disk_free_gb,
                network_bytes_sent=network_bytes_sent,
                network_bytes_recv=network_bytes_recv,
                process_count=process_count
            )
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
            return SystemMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0,
                network_bytes_sent=0,
                network_bytes_recv=0,
                process_count=0
            )
    
    def _calculate_performance_metrics(self) -> Optional[PerformanceMetrics]:
        """Calculate application performance metrics."""
        try:
            if not self._response_times:
                return None
            
            now = datetime.now(timezone.utc)
            
            # Calculate request count in last minute
            recent_requests = [
                ts for ts in self._request_timestamps
                if now - ts < timedelta(minutes=1)
            ]
            request_count = len(recent_requests)
            
            # Calculate error count (simplified - would track actual errors)
            error_count = 0  # This would be tracked from actual error events
            
            # Calculate response time metrics
            response_times = list(self._response_times)
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                sorted_times = sorted(response_times)
                p95_index = int(len(sorted_times) * 0.95)
                p99_index = int(len(sorted_times) * 0.99)
                p95_response_time = sorted_times[min(p95_index, len(sorted_times) - 1)]
                p99_response_time = sorted_times[min(p99_index, len(sorted_times) - 1)]
            else:
                avg_response_time = 0.0
                p95_response_time = 0.0
                p99_response_time = 0.0
            
            # Calculate throughput and error rate
            throughput_rps = request_count / 60.0  # requests per second
            error_rate = error_count / max(request_count, 1)
            
            return PerformanceMetrics(
                request_count=request_count,
                error_count=error_count,
                avg_response_time_ms=avg_response_time,
                p95_response_time_ms=p95_response_time,
                p99_response_time_ms=p99_response_time,
                throughput_rps=throughput_rps,
                error_rate=error_rate
            )
            
        except Exception as e:
            self.logger.error(f"Failed to calculate performance metrics: {e}")
            return None
    
    def record_request(self, response_time_ms: float, success: bool = True):
        """Record a request for performance metrics."""
        try:
            # Record response time
            self._response_times.append(response_time_ms)
            self._request_timestamps.append(datetime.now(timezone.utc))
            
            # Update OpenTelemetry metrics
            if self.meter:
                self._otel_metrics.get("requests_total").add(1)
                self._otel_metrics.get("response_time").record(response_time_ms)
                
                if not success:
                    self._otel_metrics.get("errors_total").add(1)
            
        except Exception as e:
            self.logger.error(f"Failed to record request: {e}")
    
    def record_custom_metric(
        self,
        name: str,
        value: Union[int, float],
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None,
        unit: str = "",
        description: str = ""
    ):
        """Record custom metric."""
        try:
            metric_point = MetricPoint(
                name=name,
                value=value,
                metric_type=metric_type,
                labels=labels or {},
                unit=unit,
                description=description
            )
            
            # Store in custom metrics
            if name not in self._custom_metrics:
                self._custom_metrics[name] = deque(maxlen=1000)
            
            self._custom_metrics[name].append(metric_point)
            
            # Update OpenTelemetry if available
            if self.meter and name in self._otel_metrics:
                instrument = self._otel_metrics[name]
                if metric_type == MetricType.COUNTER:
                    instrument.add(value)
                elif metric_type == MetricType.GAUGE:
                    instrument.set(value)
                elif metric_type == MetricType.HISTOGRAM:
                    instrument.record(value)
            
        except Exception as e:
            self.logger.error(f"Failed to record custom metric {name}: {e}")
    
    def get_system_metrics(self, limit: int = 100) -> List[SystemMetrics]:
        """Get recent system metrics."""
        return list(self._system_metrics)[-limit:]
    
    def get_performance_metrics(self, limit: int = 100) -> List[PerformanceMetrics]:
        """Get recent performance metrics."""
        return list(self._performance_metrics)[-limit:]
    
    def get_custom_metrics(self, name: str, limit: int = 100) -> List[MetricPoint]:
        """Get recent custom metrics."""
        if name in self._custom_metrics:
            return list(self._custom_metrics[name])[-limit:]
        return []
    
    def get_all_custom_metrics(self) -> Dict[str, List[MetricPoint]]:
        """Get all custom metrics."""
        return {
            name: list(metrics)[-100:]  # Last 100 points
            for name, metrics in self._custom_metrics.items()
        }
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        try:
            # Get latest system metrics
            latest_system = self._system_metrics[-1] if self._system_metrics else None
            latest_performance = self._performance_metrics[-1] if self._performance_metrics else None
            
            # Calculate aggregates
            system_summary = {}
            if latest_system:
                system_summary = {
                    "cpu_percent": latest_system.cpu_percent,
                    "memory_percent": latest_system.memory_percent,
                    "memory_used_mb": latest_system.memory_used_mb,
                    "disk_usage_percent": latest_system.disk_usage_percent,
                    "process_count": latest_system.process_count
                }
            
            performance_summary = {}
            if latest_performance:
                performance_summary = {
                    "request_count": latest_performance.request_count,
                    "avg_response_time_ms": latest_performance.avg_response_time_ms,
                    "p95_response_time_ms": latest_performance.p95_response_time_ms,
                    "p99_response_time_ms": latest_performance.p99_response_time_ms,
                    "throughput_rps": latest_performance.throughput_rps,
                    "error_rate": latest_performance.error_rate
                }
            
            # Custom metrics summary
            custom_summary = {}
            for name, metrics in self._custom_metrics.items():
                if metrics:
                    latest = metrics[-1]
                    custom_summary[name] = {
                        "latest_value": latest.value,
                        "metric_type": latest.metric_type.value,
                        "unit": latest.unit,
                        "description": latest.description
                    }
            
            return {
                "service_name": self.service_name,
                "collection_interval_seconds": self.collection_interval_seconds,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "system_metrics": system_summary,
                "performance_metrics": performance_summary,
                "custom_metrics": custom_summary,
                "opentelemetry_enabled": OPENTELEMETRY_METRICS_AVAILABLE and self.meter is not None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate metrics summary: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def stop(self):
        """Stop metrics collection."""
        if self.is_collecting:
            self.is_collecting = False
            
            if self.collection_task:
                self.collection_task.cancel()
                try:
                    await self.collection_task
                except asyncio.CancelledError:
                    pass
            
            # Shutdown OpenTelemetry meter provider
            if self.meter_provider:
                try:
                    await self.meter_provider.shutdown()
                except:
                    pass
            
            self.logger.info("Metrics collection stopped")
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            if hasattr(self, 'collection_task') and self.collection_task:
                self.collection_task.cancel()
        except:
            pass


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector(
    service_name: str = "market-intel-brain",
    collection_interval_seconds: int = 10
) -> MetricsCollector:
    """Get or create global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(
            service_name=service_name,
            collection_interval_seconds=collection_interval_seconds
        )
    return _metrics_collector


async def initialize_metrics(
    service_name: str = "market-intel-brain",
    collection_interval_seconds: int = 10
) -> MetricsCollector:
    """Initialize and return global metrics collector."""
    collector = get_metrics_collector(service_name, collection_interval_seconds)
    return collector
