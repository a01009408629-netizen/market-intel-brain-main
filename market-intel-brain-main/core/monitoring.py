"""
MAIFA v3 Monitoring & Alerts
Comprehensive monitoring with JSON logging, metrics collection, and alerting
"""

import asyncio
import time
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import statistics
import aiohttp

from core.distributed_state import distributed_state_manager
from utils.logger import get_logger

logger = get_logger("monitoring")

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class Alert:
    level: AlertLevel
    service: str
    message: str
    timestamp: float
    metadata: Dict[str, Any]
    resolved: bool = False

@dataclass
class MetricThreshold:
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    operator: str = "gt"  # greater than

class MonitoringSystem:
    def __init__(self):
        self.logger = get_logger("MonitoringSystem")
        self.metrics: Dict[str, List[float]] = {}
        self.alerts: List[Alert] = []
        self.thresholds: List[MetricThreshold] = []
        self.alert_handlers: List[Callable] = []
        self.metrics_window = 300  # 5 minutes
        self.collection_interval = 10
        self.is_running = False
        
        # Default thresholds
        self._setup_default_thresholds()
        
        # Alert handlers
        self._setup_alert_handlers()
    
    def _setup_default_thresholds(self):
        self.thresholds.extend([
            MetricThreshold("response_time", 2.0, 5.0),
            MetricThreshold("error_rate", 0.05, 0.15),
            MetricThreshold("memory_usage", 0.8, 0.95),
            MetricThreshold("cpu_usage", 0.7, 0.9),
            MetricThreshold("queue_size", 1000, 5000),
            MetricThreshold("circuit_breaker_open", 1, 3)
        ])
    
    def _setup_alert_handlers(self):
        self.alert_handlers = [
            self._log_alert,
            self._store_alert,
            self._telegram_alert
        ]
    
    async def start(self):
        self.is_running = True
        asyncio.create_task(self._metrics_collection_loop())
        asyncio.create_task(self._alert_processing_loop())
        self.logger.info("🚀 Monitoring system started")
    
    async def record_metric(self, service: str, metric_name: str, value: float, metadata: Dict[str, Any] = None):
        key = f"{service}:{metric_name}"
        if key not in self.metrics:
            self.metrics[key] = []
        
        # Add timestamp and metadata
        metric_entry = {
            "value": value,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        
        self.metrics[key].append(metric_entry)
        
        # Maintain window size
        cutoff_time = time.time() - self.metrics_window
        self.metrics[key] = [
            entry for entry in self.metrics[key] 
            if entry["timestamp"] > cutoff_time
        ]
        
        # Check thresholds
        await self._check_thresholds(service, metric_name, value)
        
        # Store in distributed state
        await distributed_state_manager.set_state(
            f"metrics:{key}",
            metric_entry,
            ttl=self.metrics_window
        )
    
    async def _check_thresholds(self, service: str, metric_name: str, value: float):
        for threshold in self.thresholds:
            if threshold.metric_name == metric_name:
                triggered = False
                
                if threshold.operator == "gt":
                    triggered = value > threshold.warning_threshold
                elif threshold.operator == "lt":
                    triggered = value < threshold.warning_threshold
                
                if triggered:
                    level = AlertLevel.WARNING if value < threshold.critical_threshold else AlertLevel.CRITICAL
                    
                    alert = Alert(
                        level=level,
                        service=service,
                        message=f"Metric {metric_name} threshold exceeded: {value}",
                        timestamp=time.time(),
                        metadata={
                            "metric_name": metric_name,
                            "value": value,
                            "threshold": threshold.critical_threshold if level == AlertLevel.CRITICAL else threshold.warning_threshold
                        }
                    )
                    
                    await self._create_alert(alert)
    
    async def _create_alert(self, alert: Alert):
        self.alerts.append(alert)
        
        # Process alert through handlers
        for handler in self.alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                self.logger.error(f"Alert handler failed: {e}")
    
    async def _log_alert(self, alert: Alert):
        log_level = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL
        }.get(alert.level, logging.INFO)
        
        self.logger.log(log_level, f"🚨 ALERT [{alert.level.value.upper()}] {alert.service}: {alert.message}")
    
    async def _store_alert(self, alert: Alert):
        await distributed_state_manager.set_state(
            f"alerts:{alert.service}:{int(alert.timestamp)}",
            asdict(alert),
            ttl=86400  # 24 hours
        )
    
    async def _telegram_alert(self, alert: Alert):
        # Telegram integration (placeholder)
        if alert.level in [AlertLevel.ERROR, AlertLevel.CRITICAL]:
            self.logger.critical(f"🚨 CRITICAL ALERT: {alert.service} - {alert.message}")
            # In production, send to Telegram webhook
    
    async def get_service_metrics(self, service: str) -> Dict[str, Any]:
        service_metrics = {}
        
        for key, entries in self.metrics.items():
            if key.startswith(f"{service}:"):
                metric_name = key.split(":", 1)[1]
                
                if entries:
                    values = [entry["value"] for entry in entries]
                    service_metrics[metric_name] = {
                        "current": values[-1],
                        "avg": statistics.mean(values),
                        "min": min(values),
                        "max": max(values),
                        "count": len(values),
                        "trend": "increasing" if len(values) > 1 and values[-1] > values[-2] else "decreasing"
                    }
        
        return service_metrics
    
    async def get_system_status(self) -> Dict[str, Any]:
        total_metrics = sum(len(entries) for entries in self.metrics.values())
        active_alerts = len([a for a in self.alerts if not a.resolved])
        
        return {
            "is_running": self.is_running,
            "total_metrics": total_metrics,
            "active_alerts": active_alerts,
            "services": list(set(key.split(":")[0] for key in self.metrics.keys())),
            "timestamp": datetime.now().isoformat()
        }
    
    async def _metrics_collection_loop(self):
        while self.is_running:
            try:
                await asyncio.sleep(self.collection_interval)
                # Metrics are collected by individual services
            except Exception as e:
                self.logger.error(f"Metrics collection error: {e}")
    
    async def _alert_processing_loop(self):
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Process alerts every minute
                
                # Clean up old alerts
                cutoff_time = time.time() - 86400  # 24 hours
                self.alerts = [a for a in self.alerts if a.timestamp > cutoff_time]
                
            except Exception as e:
                self.logger.error(f"Alert processing error: {e}")
    
    async def shutdown(self):
        self.is_running = False
        self.logger.info("🛑 Monitoring system shutdown")

# Global monitoring system
monitoring_system = MonitoringSystem()

# Decorator for automatic metric collection
def monitor_metric(service: str, metric_name: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                response_time = time.time() - start_time
                await monitoring_system.record_metric(service, f"{metric_name}_response_time", response_time)
                await monitoring_system.record_metric(service, f"{metric_name}_success", 1)
                return result
            except Exception as e:
                response_time = time.time() - start_time
                await monitoring_system.record_metric(service, f"{metric_name}_response_time", response_time)
                await monitoring_system.record_metric(service, f"{metric_name}_error", 1)
                raise
        return wrapper
    return decorator
