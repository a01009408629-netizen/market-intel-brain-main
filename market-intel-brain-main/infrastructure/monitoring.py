"""
Enterprise Monitoring & Observability System
Prometheus metrics, Grafana dashboards, structured logging, and alerting
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from functools import wraps
import psutil
import os
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from fastapi.routing import APIRoute
import aiofiles
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MetricConfig:
    """Configuration for metrics collection."""
    name: str
    description: str
    labels: List[str] = None
    metric_type: str = "counter"  # counter, histogram, gauge


@dataclass
class AlertConfig:
    """Configuration for alerts."""
    name: str
    condition: str
    threshold: float
    severity: str = "warning"  # info, warning, critical
    message: str = ""
    enabled: bool = True


class EnterpriseMetrics:
    """Enterprise metrics collection with Prometheus integration."""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        self.metrics = {}
        self._setup_default_metrics()
    
    def _setup_default_metrics(self):
        """Setup default enterprise metrics."""
        # HTTP metrics
        self.metrics["http_requests_total"] = Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status_code"],
            registry=self.registry
        )
        
        self.metrics["http_request_duration_seconds"] = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"],
            registry=self.registry
        )
        
        # Application metrics
        self.metrics["active_users_total"] = Gauge(
            "active_users_total",
            "Number of active users",
            registry=self.registry
        )
        
        self.metrics["data_points_processed_total"] = Counter(
            "data_points_processed_total",
            "Total data points processed",
            ["source", "type"],
            registry=self.registry
        )
        
        # System metrics
        self.metrics["system_cpu_usage_percent"] = Gauge(
            "system_cpu_usage_percent",
            "System CPU usage percentage",
            registry=self.registry
        )
        
        self.metrics["system_memory_usage_percent"] = Gauge(
            "system_memory_usage_percent",
            "System memory usage percentage",
            registry=self.registry
        )
        
        self.metrics["system_disk_usage_percent"] = Gauge(
            "system_disk_usage_percent",
            "System disk usage percentage",
            ["mount_point"],
            registry=self.registry
        )
        
        # Database metrics
        self.metrics["database_connections_active"] = Gauge(
            "database_connections_active",
            "Active database connections",
            ["database"],
            registry=self.registry
        )
        
        self.metrics["database_query_duration_seconds"] = Histogram(
            "database_query_duration_seconds",
            "Database query duration in seconds",
            ["database", "operation"],
            registry=self.registry
        )
        
        # Cache metrics
        self.metrics["cache_hits_total"] = Counter(
            "cache_hits_total",
            "Total cache hits",
            ["cache_type"],
            registry=self.registry
        )
        
        self.metrics["cache_misses_total"] = Counter(
            "cache_misses_total",
            "Total cache misses",
            ["cache_type"],
            registry=self.registry
        )
        
        # Security metrics
        self.metrics["authentication_attempts_total"] = Counter(
            "authentication_attempts_total",
            "Total authentication attempts",
            ["method", "result"],
            registry=self.registry
        )
        
        self.metrics["authorization_failures_total"] = Counter(
            "authorization_failures_total",
            "Total authorization failures",
            ["permission"],
            registry=self.registry
        )
    
    def increment_counter(self, metric_name: str, labels: Dict[str, str] = None, value: int = 1):
        """Increment counter metric."""
        if metric_name in self.metrics:
            if labels:
                self.metrics[metric_name].labels(**labels).inc(value)
            else:
                self.metrics[metric_name].inc(value)
    
    def observe_histogram(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Observe histogram metric."""
        if metric_name in self.metrics:
            if labels:
                self.metrics[metric_name].labels(**labels).observe(value)
            else:
                self.metrics[metric_name].observe(value)
    
    def set_gauge(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Set gauge metric."""
        if metric_name in self.metrics:
            if labels:
                self.metrics[metric_name].labels(**labels).set(value)
            else:
                self.metrics[metric_name].set(value)
    
    def get_metrics(self) -> str:
        """Get Prometheus metrics."""
        return generate_latest(self.registry)


class EnterpriseLogger:
    """Enterprise structured logging with correlation IDs."""
    
    def __init__(self, name: str = "market_intel_brain"):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup structured logger."""
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler for structured logs
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(log_dir / "application.log")
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        self.logger.setLevel(logging.INFO)
    
    def log_structured(self, level: str, message: str, **kwargs):
        """Log structured message with additional context."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "message": message,
            **kwargs
        }
        
        log_message = json.dumps(log_data)
        
        if level.lower() == "debug":
            self.logger.debug(log_message)
        elif level.lower() == "info":
            self.logger.info(log_message)
        elif level.lower() == "warning":
            self.logger.warning(log_message)
        elif level.lower() == "error":
            self.logger.error(log_message)
        elif level.lower() == "critical":
            self.logger.critical(log_message)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.log_structured("info", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.log_structured("warning", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.log_structured("error", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.log_structured("critical", message, **kwargs)


class EnterpriseAlerting:
    """Enterprise alerting system with configurable rules."""
    
    def __init__(self):
        self.alerts = []
        self.alert_history = []
        self.logger = EnterpriseLogger("alerting")
    
    def add_alert(self, alert_config: AlertConfig):
        """Add alert configuration."""
        self.alerts.append(alert_config)
        self.logger.info(f"Added alert: {alert_config.name}")
    
    def check_alerts(self, metrics_data: Dict[str, Any]):
        """Check all alert conditions."""
        for alert in self.alerts:
            if not alert.enabled:
                continue
            
            try:
                if self._evaluate_condition(alert.condition, metrics_data, alert.threshold):
                    self._trigger_alert(alert, metrics_data)
            except Exception as e:
                self.logger.error(f"Alert check failed for {alert.name}: {e}")
    
    def _evaluate_condition(self, condition: str, data: Dict[str, Any], threshold: float) -> bool:
        """Evaluate alert condition."""
        # Simple evaluation - in production, use a proper expression evaluator
        if ">" in condition:
            metric_name = condition.split(">")[0].strip()
            current_value = data.get(metric_name, 0)
            return current_value > threshold
        elif "<" in condition:
            metric_name = condition.split("<")[0].strip()
            current_value = data.get(metric_name, 0)
            return current_value < threshold
        
        return False
    
    def _trigger_alert(self, alert: AlertConfig, data: Dict[str, Any]):
        """Trigger alert."""
        alert_data = {
            "alert_name": alert.name,
            "severity": alert.severity,
            "message": alert.message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        
        self.alert_history.append(alert_data)
        
        # Log alert
        self.logger.warning(
            f"ALERT: {alert.name}",
            severity=alert.severity,
            message=alert.message,
            data=data
        )
        
        # In production, send to alerting system (PagerDuty, Slack, etc.)
        # await self._send_notification(alert_data)


class SystemMonitor:
    """System resource monitoring."""
    
    def __init__(self, metrics: EnterpriseMetrics):
        self.metrics = metrics
        self.monitoring = False
        self._monitor_task = None
    
    async def start_monitoring(self, interval: int = 30):
        """Start system monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info("System monitoring started")
    
    async def stop_monitoring(self):
        """Stop system monitoring."""
        self.monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
        logger.info("System monitoring stopped")
    
    async def _monitor_loop(self, interval: int):
        """Monitoring loop."""
        while self.monitoring:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"System monitoring error: {e}")
                await asyncio.sleep(interval)
    
    async def _collect_system_metrics(self):
        """Collect system metrics."""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        self.metrics.set_gauge("system_cpu_usage_percent", cpu_percent)
        
        # Memory usage
        memory = psutil.virtual_memory()
        self.metrics.set_gauge("system_memory_usage_percent", memory.percent)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        self.metrics.set_gauge("system_disk_usage_percent", disk.percent, labels={"mount_point": "/"})
        
        # Network I/O
        network = psutil.net_io_counters()
        if network:
            self.metrics.increment_counter("network_bytes_sent_total", value=network.bytes_sent)
            self.metrics.increment_counter("network_bytes_received_total", value=network.bytes_recv)


class MetricsMiddleware:
    """FastAPI middleware for metrics collection."""
    
    def __init__(self, app, metrics: EnterpriseMetrics):
        self.app = app
        self.metrics = metrics
        self.logger = EnterpriseLogger("middleware")
    
    async def __call__(self, scope, receive, send):
        """Middleware call."""
        if scope["type"] == "http":
            start_time = time.time()
            
            # Process request
            request = Request(scope, receive)
            
            try:
                # Call next middleware/app
                await self.app(scope, receive, send)
                
                # Record metrics
                process_time = time.time() - start_time
                self.metrics.observe_histogram(
                    "http_request_duration_seconds",
                    process_time,
                    labels={"method": request.method, "endpoint": request.url.path}
                )
                
                self.metrics.increment_counter(
                    "http_requests_total",
                    labels={"method": request.method, "endpoint": request.url.path, "status_code": "200"}
                )
                
            except Exception as e:
                # Record error metrics
                process_time = time.time() - start_time
                self.metrics.observe_histogram(
                    "http_request_duration_seconds",
                    process_time,
                    labels={"method": request.method, "endpoint": request.url.path}
                )
                
                self.metrics.increment_counter(
                    "http_requests_total",
                    labels={"method": request.method, "endpoint": request.url.path, "status_code": "500"}
                )
                
                self.logger.error(f"Request failed: {e}", path=request.url.path, method=request.method)
                raise
        else:
            await self.app(scope, receive, send)


def track_performance(metric_name: str = None, labels: Dict[str, str] = None):
    """Decorator to track function performance."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if metric_name and hasattr(wrapper, '_metrics'):
                    wrapper._metrics.observe_histogram(metric_name, duration, labels)
        return wrapper
    return decorator


# Global instances
enterprise_metrics = EnterpriseMetrics()
enterprise_logger = EnterpriseLogger()
enterprise_alerting = EnterpriseAlerting()
system_monitor = SystemMonitor(enterprise_metrics)


async def get_metrics() -> str:
    """Get Prometheus metrics endpoint."""
    return enterprise_metrics.get_metrics()


async def initialize_monitoring():
    """Initialize monitoring system."""
    try:
        # Setup default alerts
        enterprise_alerting.add_alert(AlertConfig(
            name="high_cpu_usage",
            condition="system_cpu_usage_percent",
            threshold=80.0,
            severity="warning",
            message="CPU usage is above 80%"
        ))
        
        enterprise_alerting.add_alert(AlertConfig(
            name="high_memory_usage",
            condition="system_memory_usage_percent",
            threshold=85.0,
            severity="critical",
            message="Memory usage is above 85%"
        ))
        
        enterprise_alerting.add_alert(AlertConfig(
            name="high_disk_usage",
            condition="system_disk_usage_percent",
            threshold=90.0,
            severity="critical",
            message="Disk usage is above 90%"
        ))
        
        # Start system monitoring
        await system_monitor.start_monitoring()
        
        enterprise_logger.info("Enterprise monitoring initialized")
        
    except Exception as e:
        enterprise_logger.error(f"Failed to initialize monitoring: {e}")
        raise


async def cleanup_monitoring():
    """Cleanup monitoring resources."""
    await system_monitor.stop_monitoring()
    enterprise_logger.info("Enterprise monitoring cleaned up")
