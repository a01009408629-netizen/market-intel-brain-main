"""
Shadow Metrics

This module provides metrics collection for shadow testing A/B experiments
with performance tracking and statistical analysis.
"""

import asyncio
import time
import logging
import statistics
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from abc import ABC, abstractmethod

from .exceptions import MetricsError, ConfigurationError


@dataclass
class MetricsConfig:
    """Configuration for shadow metrics collection."""
    enable_performance_metrics: bool = True
    enable_success_rate_tracking: bool = True
    enable_error_tracking: bool = true
    enable_latency_tracking: bool = True
    enable_throughput_tracking: bool = true
    enable_resource_usage: bool = True
    enable_detailed_logging: bool = False
    max_history_size: int = 10000
    aggregation_window: int = 300  # 5 minutes
    enable_real_time_alerts: bool = True
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "error_rate": 0.05,      # 5% error rate
        "latency_p95": 1000.0,    # 1 second P95 latency
        "similarity_threshold": 0.9,  # 90% similarity threshold
        "throughput_drop": 0.2         # 20% throughput drop
    })


@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    request_id: str
    adapter_name: str
    adapter_type: str  # "primary" or "shadow"
    timestamp: float
    latency_ms: float
    status: str  # "success", "error", "timeout"
    response_size: int
    error_message: Optional[str]
    metadata: Dict[str, Any]


@dataclass
class ComparisonMetrics:
    """Metrics for a comparison."""
    comparison_id: str
    primary_request_id: str
    shadow_request_id: str
    primary_adapter: str
    shadow_adapter: str
    timestamp: float
    similarity_score: float
    field_differences_count: int
    content_differences_count: int
    structure_differences_count: int
    performance_differences: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class AggregatedMetrics:
    """Aggregated metrics over a time window."""
    window_start: float
    window_end: float
    total_requests: int
    primary_metrics: Dict[str, Any]
    shadow_metrics: Dict[str, Any]
    comparison_metrics: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    alert_metrics: Dict[str, Any]


class BaseMetricsCollector(ABC):
    """Abstract base class for metrics collectors."""
    
    @abstractmethod
    async def collect_request_metrics(self, metrics: RequestMetrics):
        """Collect metrics for a request."""
        pass
    
    @abstractmethod
    async def collect_comparison_metrics(self, metrics: ComparisonMetrics):
        """Collect metrics for a comparison."""
        pass
    
    @abstractmethod
    async def get_aggregated_metrics(self, window_seconds: int) -> AggregatedMetrics:
        """Get aggregated metrics over a time window."""
        pass


class ShadowMetrics(BaseMetricsCollector):
    """
    Shadow testing metrics collector for A/B experiments.
    
    This class collects and analyzes metrics from shadow testing
    to provide insights into performance and reliability.
    """
    
    def __init__(
        self,
        config: Optional[MetricsConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize shadow metrics collector.
        
        Args:
            config: Metrics configuration
            logger: Logger instance
        """
        self.config = config or MetricsConfig()
        self.logger = logger or logging.getLogger("ShadowMetrics")
        
        # Metrics storage
        self._request_metrics: deque(maxlen=self.config.max_history_size)
        self._comparison_metrics: deque(maxlen=self.config.max_history_size)
        self._aggregated_metrics: Dict[str, AggregatedMetrics] = {}
        
        # Statistics
        self._stats = {
            'requests_collected': 0,
            'comparisons_performed': 0,
            'alerts_triggered': 0,
            'start_time': time.time()
        }
        
        # Real-time alerts
        self._alert_history = deque(maxlen=100)
        
        self.logger.info("ShadowMetrics initialized")
    
    async def collect_request_metrics(self, metrics: RequestMetrics):
        """Collect metrics for a single request."""
        try:
            self._request_metrics.append(metrics)
            self._stats['requests_collected'] += 1
            
            # Log detailed metrics if enabled
            if self.config.enable_detailed_logging:
                self.logger.debug(
                    f"Request metrics: {metrics.adapter_name} "
                    f"({metrics.adapter_type}) - "
                    f"latency: {metrics.latency_ms}ms, "
                    f"status: {metrics.status}"
                )
            
            # Check for real-time alerts
            if self.config.enable_real_time_alerts:
                await self._check_real_time_alerts(metrics)
            
        except Exception as e:
            self.logger.error(f"Error collecting request metrics: {e}")
            raise MetricsError(f"Failed to collect metrics: {e}")
    
    async def collect_comparison_metrics(self, metrics: ComparisonMetrics):
        """Collect metrics for a comparison."""
        try:
            self._comparison_metrics.append(metrics)
            self._stats['comparisons_performed'] += 1
            
            # Log detailed metrics if enabled
            if self.config.enable_detailed_logging:
                self.logger.debug(
                    f"Comparison metrics: {metrics.primary_adapter} vs {metrics.shadow_adapter} "
                    f"- similarity: {metrics.similarity_score:.3f}, "
                    f"differences: {metrics.field_differences_count + metrics.content_differences_count}"
                )
            
            # Check for real-time alerts
            if self.config.enable_real_time_alerts:
                await self._check_comparison_alerts(metrics)
            
        except Exception as e:
            self.logger.error(f"Error collecting comparison metrics: {e}")
            raise MetricsError(f"Failed to collect comparison metrics: {e}")
    
    async def get_aggregated_metrics(self, window_seconds: int = 300) -> AggregatedMetrics:
        """
        Get aggregated metrics over a time window.
        
        Args:
            window_seconds: Time window in seconds
            
        Returns:
            AggregatedMetrics with windowed statistics
        """
        try:
            current_time = time.time()
            window_start = current_time - window_seconds
            window_end = current_time
            
            # Filter metrics within window
            recent_requests = [
                m for m in self._request_metrics
                if m.timestamp >= window_start
            ]
            
            recent_comparisons = [
                m for m in self._comparison_metrics
                if m.timestamp >= window_start
            ]
            
            # Aggregate request metrics
            primary_metrics = self._aggregate_request_metrics(
                [m for m in recent_requests if m.adapter_type == "primary"]
            )
            
            shadow_metrics = self._aggregate_request_metrics(
                [m for m in recent_requests if m.adapter_type == "shadow"]
            )
            
            # Aggregate comparison metrics
            comparison_metrics = self._aggregate_comparison_metrics(recent_comparisons)
            
            # Aggregate performance metrics
            performance_metrics = self._aggregate_performance_metrics(
                recent_requests, recent_comparisons
            )
            
            # Create aggregated metrics
            aggregated = AggregatedMetrics(
                window_start=window_start,
                window_end=window_end,
                total_requests=len(recent_requests),
                primary_metrics=primary_metrics,
                shadow_metrics=shadow_metrics,
                comparison_metrics=comparison_metrics,
                performance_metrics=performance_metrics,
                alert_metrics=self._get_alert_metrics()
            )
            
            # Store aggregated metrics
            window_key = f"metrics_{window_seconds}s"
            self._aggregated_metrics[window_key] = aggregated
            
            return aggregated
            
        except Exception as e:
            self.logger.error(f"Error getting aggregated metrics: {e}")
            raise MetricsError(f"Failed to get aggregated metrics: {e}")
    
    def _aggregate_request_metrics(self, metrics: List[RequestMetrics]) -> Dict[str, Any]:
        """Aggregate request metrics."""
        if not metrics:
            return {}
        
        total_requests = len(metrics)
        successful_requests = len([m for m in metrics if m.status == "success"])
        failed_requests = len([m for m in metrics if m.status == "error"])
        
        latencies = [m.latency_ms for m in metrics if m.status == "success"]
        
        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": successful_requests / max(total_requests, 1),
            "error_rate": failed_requests / max(total_requests, 1),
            "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
            "p50_latency_ms": statistics.median(latencies) if latencies else 0,
            "p95_latency_ms": statistics.quantiles(latencies, 0.95)[0] if latencies else 0,
            "p99_latency_ms": statistics.quantiles(latencies, 0.99)[0] if latencies else 0,
            "min_latency_ms": min(latencies) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0
        }
    
    def _aggregate_comparison_metrics(self, metrics: List[ComparisonMetrics]) -> Dict[str, Any]:
        """Aggregate comparison metrics."""
        if not metrics:
            return {}
        
        total_comparisons = len(metrics)
        
        similarity_scores = [m.similarity_score for m in metrics]
        field_diff_counts = [m.field_differences_count for m in metrics]
        content_diff_counts = [m.content_differences_count for m in metrics]
        
        return {
            "total_comparisons": total_comparisons,
            "avg_similarity_score": statistics.mean(similarity_scores) if similarity_scores else 0,
            "min_similarity_score": min(similarity_scores) if similarity_scores else 1.0,
            "max_similarity_score": max(similarity_scores) if similarity_scores else 0.0,
            "avg_field_differences": statistics.mean(field_diff_counts) if field_diff_counts else 0,
            "avg_content_differences": statistics.mean(content_diff_counts) if content_diff_counts else 0,
            "identical_comparisons": len([s for s in similarity_scores if s == 1.0])
        }
    
    def _aggregate_performance_metrics(
        self,
        requests: List[RequestMetrics],
        comparisons: List[ComparisonMetrics] = None
    ) -> Dict[str, Any]:
        """Aggregate performance metrics."""
        
        # Get primary vs shadow performance
        primary_metrics = self._aggregate_request_metrics(
            [m for m in requests if m.adapter_type == "primary"]
        )
        shadow_metrics = self._aggregate_request_metrics(
            [m for m in requests if m.adapter_type == "shadow"]
        )
        
        # Calculate performance differences
        performance_diff = {}
        if comparisons and self.config.enable_performance_metrics:
            shadow_faster = len([
                c for c in comparisons
                if c.performance_differences.get("is_shadow_faster", False)
            ])
            
            performance_diff = {
                "shadow_faster_count": shadow_faster,
                "shadow_faster_rate": shadow_faster / max(len(comparisons), 1),
                "avg_latency_difference_ms": statistics.mean([
                    c.performance_differences.get("latency_difference_ms", 0)
                    for c in comparisons
                ]),
                "max_latency_difference_ms": max([
                    c.performance_differences.get("latency_difference_ms", 0)
                    for c in comparisons
                ]),
                "performance_impact": statistics.mean([
                    c.performance_differences.get("performance_impact", 0)
                    for c in comparisons
                ])
            }
        
        return {
            "primary_metrics": primary_metrics,
            "shadow_metrics": shadow_metrics,
            "performance_differences": performance_diff
        }
    
    def _check_real_time_alerts(self, metrics: RequestMetrics):
        """Check for real-time alert conditions."""
        try:
            alerts = []
            
            # Check for high latency
            if self.config.enable_latency_tracking and metrics.status == "success":
                if metrics.latency_ms > self.config.alert_thresholds.get("latency_p95", 1000.0):
                    alerts.append({
                        "type": "high_latency",
                        "message": f"High latency detected: {metrics.latency_ms}ms",
                        "value": metrics.latency_ms
                    })
            
            # Check for errors
            if self.config.enable_error_tracking and metrics.status == "error":
                alerts.append({
                    "type": "error",
                    "message": f"Error in {metrics.adapter_name}: {metrics.error_message}",
                    "error": metrics.error_message
                })
            
            # Add alerts to history
            for alert in alerts:
                self._alert_history.append(alert)
                self._stats['alerts_triggered'] += 1
                
                # Log alert
                self.logger.warning(f"Real-time alert: {alert['message']}")
            
        except Exception as e:
            self.logger.error(f"Error checking real-time alerts: {e}")
    
    def _check_comparison_alerts(self, metrics: ComparisonMetrics):
        """Check for real-time comparison alerts."""
        try:
            alerts = []
            
            # Check for low similarity
            if metrics.similarity_score < self.config.alert_thresholds.get("similarity_threshold", 0.9):
                alerts.append({
                    "type": "low_similarity",
                    "message": f"Low similarity detected: {metrics.similarity_score:.3f}",
                    "value": metrics.similarity_score
                })
            
            # Check for high number of differences
            total_differences = metrics.field_differences_count + metrics.content_differences_count
            if total_differences > 10:
                alerts.append({
                    "type": "high_differences",
                    "message": f"High number of differences: {total_differences}",
                    "value": total_differences
                })
            
            # Add alerts to history
            for alert in alerts:
                self._alert_history.append(alert)
                self._stats['alerts_triggered'] += 1
                
                # Log alert
                self.logger.warning(f"Comparison alert: {alert['message']}")
            
        except Exception as e:
            self.logger.error(f"Error checking comparison alerts: {e}")
    
    def _get_alert_metrics(self) -> Dict[str, Any]:
        """Get alert metrics."""
        if not self._alert_history:
            return {}
        
        recent_alerts = list(self._alert_history)
        
        return {
            "total_alerts": len(recent_alerts),
            "alert_types": {
                alert_type: len([a for a in recent_alerts if a['type'] == alert_type])
                for alert_type in ["high_latency", "error", "low_similarity", "high_differences"]
            },
            "recent_alerts": recent_alerts[-10:]  # Last 10 alerts
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get collector statistics."""
        uptime = time.time() - self._stats['start_time']
        
        return {
            "uptime": uptime,
            "requests_collected": self._stats['requests_collected'],
            "comparisons_performed": self._stats['comparisons_performed'],
            "alerts_triggered": self._stats['alerts_triggered'],
            "current_request_queue_size": len(self._request_metrics),
            "current_comparison_queue_size": len(self._comparison_metrics),
            "aggregated_windows": len(self._aggregated_metrics),
            "config": self.config.__dict__
        }
    
    def get_recent_metrics(
        self,
        request_count: int = 100,
        comparison_count: int = 50
    ) -> Dict[str, Any]:
        """Get recent metrics."""
        return {
            "recent_requests": list(self._request_metrics)[-request_count:],
            "recent_comparisons": list(self._comparison_metrics)[-comparison_count:],
            "recent_alerts": list(self._alert_history)[-10:]
        }


# Global metrics collector instance
_global_metrics: Optional[ShadowMetrics] = None


def get_metrics(**kwargs) -> ShadowMetrics:
    """
    Get or create the global metrics collector.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global ShadowMetrics instance
    """
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = ShadowMetrics(**kwargs)
    return _global_metrics
