"""
Shadow Engine

This module provides the core shadow testing engine for A/B experiments
with concurrent request execution and comprehensive comparison.
"""

import asyncio
import time
import uuid
import logging
import json
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum

from .comparator import ResponseComparator, get_comparator
from .metrics import ShadowMetrics, get_metrics
from .exceptions import (
    ShadowError,
    AdapterError,
    ConfigurationError,
    RequestTimeoutError
)


class RequestStatus(Enum):
    """Status of a shadow request."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ShadowRequest:
    """A shadow request configuration."""
    request_id: str
    adapter_name: str
    payload: Dict[str, Any]
    timestamp: float
    timeout: float
    status: RequestStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    latency_ms: Optional[float] = None
    metadata: Dict[str, Any]


@dataclass
class ShadowConfig:
    """Configuration for shadow engine."""
    max_concurrent_requests: int = 10
    default_timeout: float = 30.0  # 30 seconds
    enable_comparison: bool = True
    enable_metrics: bool = True
    enable_background_diff: bool = True
    enable_real_time_alerts: bool = True
    diff_storage_backend: str = "memory"  # "memory" or "database"
    database_url: str = "sqlite:///tmp/shadow_metrics.db"
    enable_request_logging: bool = False
    enable_response_logging: bool = False
    dark_launch_detection: bool = True
    similarity_threshold: float = 0.95  # 95% similarity for dark launch detection


class ShadowEngine:
    """
    Core shadow testing engine for A/B experiments.
    
    This class orchestrates concurrent requests to primary and shadow adapters,
    compares responses, and provides comprehensive metrics.
    """
    
    def __init__(
        self,
        config: Optional[ShadowConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize shadow engine.
        
        Args:
            config: Shadow configuration
            logger: Logger instance
        """
        self.config = config or ShadowConfig()
        self.logger = logger or logging.getLogger("ShadowEngine")
        
        # Components
        self.comparator = get_comparator()
        self.metrics = get_metrics()
        
        # Request tracking
        self._active_requests: Dict[str, ShadowRequest] = {}
        self._request_history: List[ShadowRequest] = []
        
        # Statistics
        self._stats = {
            'requests_initiated': 0,
            'requests_completed': 0,
            'requests_failed': 0,
            'requests_timed_out': 0,
            'comparisons_performed': 0,
            'dark_launches_detected': 0,
            'start_time': time.time()
        }
        
        # Background diff task
        self._diff_task = None
        self._diff_running = False
        
        self.logger.info("ShadowEngine initialized")
    
    async def start(self):
        """Start the shadow engine."""
        self._diff_running = True
        self._diff_task = asyncio.create_task(self._background_diff_loop())
        self.logger.info("ShadowEngine started")
    
    async def stop(self):
        """Stop the shadow engine."""
        self._diff_running = False
        
        if self._diff_task:
            self._diff_task.cancel()
            try:
                await self._diff_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("ShadowEngine stopped")
    
    async def fetch_with_shadow(
        self,
        primary_adapter: Callable,
        shadow_adapter: Callable,
        payload: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute fetch on both primary and shadow adapters concurrently.
        
        Args:
            primary_adapter: Primary adapter function
            shadow_adapter: Shadow adapter function
            payload: Request payload
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with both results
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Create shadow requests
            primary_request = ShadowRequest(
                request_id=f"{request_id}_primary",
                adapter_name="primary",
                payload=payload,
                timestamp=start_time,
                timeout=self.config.default_timeout,
                status=RequestStatus.PENDING
            )
            
            shadow_request = ShadowRequest(
                request_id=f"{request_id}_shadow",
                adapter_name="shadow",
                payload=payload,
                timestamp=start_time,
                timeout=self.config.default_timeout,
                status=RequestStatus.PENDING
            )
            
            # Store requests
            self._active_requests[primary_request.request_id] = primary_request
            self._active_requests[shadow_request.request_id] = shadow_request
            
            # Execute requests concurrently
            tasks = []
            
            # Primary request
            tasks.append(self._execute_request(primary_adapter, primary_request))
            
            # Shadow request
            tasks.append(self._execute_request(shadow_adapter, shadow_request))
            
            # Wait for both to complete
            primary_result, shadow_result = await asyncio.gather(*tasks)
            
            # Calculate latencies
            primary_latency = (time.time() - start_time) * 1000
            shadow_latency = (time.time() - start_time) * 1000
            
            primary_request.result = primary_result
            primary_request.latency_ms = primary_latency
            primary_request.status = RequestStatus.COMPLETED
            
            shadow_request.result = shadow_result
            shadow_request.latency_ms = shadow_latency
            shadow_request.status = RequestStatus.COMPLETED
            
            # Store in history
            self._request_history.extend([primary_request, shadow_request])
            
            # Remove from active requests
            del self._active_requests[primary_request.request_id]
            del self._active_requests[shadow_request.request_id]
            
            # Update statistics
            self._stats['requests_completed'] += 2
            self._stats['requests_initiated'] += 2
            
            # Perform comparison if enabled
            comparison_result = None
            if self.config.enable_comparison:
                comparison_result = await self.comparator.compare_responses(
                    primary_result, shadow_result,
                    primary_adapter=primary_adapter.adapter_name,
                    shadow_adapter=shadow_adapter.adapter_name,
                    primary_request_id=primary_request.request_id,
                    shadow_request_id=shadow_request.request_id
                )
                
                # Store comparison metrics
                if self.config.enable_metrics:
                    await self.metrics.collect_comparison_metrics(comparison_result)
            
            # Check for dark launch detection
            if self.config.dark_launch_detection:
                await self._check_dark_launch(primary_result, shadow_result)
            
            return {
                "request_id": request_id,
                "primary_result": primary_result,
                "shadow_result": shadow_result,
                "comparison_result": comparison_result,
                "primary_latency_ms": primary_latency,
                "shadow_latency_ms": shadow_latency,
                "primary_status": primary_request.status,
                "shadow_status": shadow_request.status
            }
            
        except Exception as e:
            self.logger.error(f"Error in fetch_with_shadow: {e}")
            raise ShadowError(f"Failed to fetch with shadow: {e}")
    
    async def _execute_request(self, adapter: Callable, request: ShadowRequest) -> ShadowRequest:
        """Execute a single request."""
        try:
            request.status = RequestStatus.RUNNING
            
            # Execute request
            start_time = time.time()
            
            if asyncio.iscoroutinefunction(adapter):
                result = await adapter(request.payload)
            else:
                result = adapter(request.payload)
            
            end_time = time.time()
            
            # Update request
            request.result = result
            request.latency_ms = (end_time - start_time) * 1000
            request.status = RequestStatus.COMPLETED
            
            if isinstance(result, Exception):
                request.status = RequestStatus.FAILED
                request.error = str(result)
            elif result is None:
                request.status = RequestStatus.FAILED
                request.error = "No result returned"
            
            return request
            
        except asyncio.TimeoutError:
            request.status = RequestStatus.TIMEOUT
            request.error = f"Request timeout after {self.config.default_timeout}s"
            return request
        except Exception as e:
            request.status = RequestStatus.FAILED
            request.error = str(e)
            return request
    
    async def _background_diff_loop(self):
        """Background loop for processing comparisons."""
        while self._diff_running:
            try:
                # Get recent requests that need comparison
                recent_requests = [
                    r for r in self._request_history
                    if r.timestamp > time.time() - self.config.aggregation_window
                ]
                
                # Group by request ID
                request_groups = {}
                for request in recent_requests:
                    base_id = request.request_id.split('_')[0]
                    if base_id not in request_groups:
                        request_groups[base_id] = []
                    request_groups[base_id].append(request)
                
                # Process each group
                for group_id, requests in request_groups.items():
                    if len(requests) == 2:  # Primary and shadow
                        primary_request = next((r for r in requests if r.adapter_type == "primary"), None)
                        shadow_request = next((r for r in requests if r.adapter_type == "shadow"), None)
                        
                        if primary_request and shadow_request:
                            # Perform comparison
                            comparison_result = await self.comparator.compare_responses(
                                primary_request.result, shadow_request.result
                            )
                            
                            # Store comparison metrics
                            if self.config.enable_metrics:
                                await self.metrics.collect_comparison_metrics(comparison_result)
                            
                            # Check for dark launch
                            if self.config.dark_launch_detection:
                                await self._check_dark_launch(
                                    primary_request.result, shadow_request.result
                                )
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                self.logger.error(f"Error in background diff loop: {e}")
                    if self._diff_running:
                        self._diff_running = False
    
    async def _check_dark_launch(self, primary_result: Any, shadow_result: Any):
        """Check for dark launch conditions."""
        try:
            # Check for identical responses with different adapters
            if (
                primary_result == shadow_result and
                primary_request.adapter_name != shadow_request.adapter_name
            ):
                # This could indicate dark launching
                self._stats['dark_launches_detected'] += 1
                
                alert = {
                    "type": "dark_launch_detected",
                    "message": f"Dark launch detected: {primary_request.adapter_name} vs {shadow_request.adapter_name}",
                    "primary_adapter": primary_request.adapter_name,
                    "shadow_adapter": shadow_request.adapter_name,
                    "primary_request_id": primary_request.request_id,
                    "shadow_request_id": shadow_request.request_id,
                    "timestamp": time.time()
                }
                
                # Log alert
                self.logger.critical(f"Dark launch alert: {alert['message']}")
                
                # Add to alert history
                if self.config.enable_real_time_alerts:
                    self.metrics._alert_history.append(alert)
                    self._stats['alerts_triggered'] += 1
                
        except Exception as e:
            self.logger.error(f"Error checking dark launch: {e}")
    
    def get_active_requests(self) -> Dict[str, ShadowRequest]:
        """Get currently active requests."""
        return self._active_requests.copy()
    
    def get_request_history(
        self,
        limit: int = 100,
        adapter_type: Optional[str] = None
    ) -> List[ShadowRequest]:
        """Get request history."""
        history = self._request_history
        
        if adapter_type:
            history = [r for r in history if r.adapter_type == adapter_type]
        else:
            history = history
        
        return history[-limit:] if len(history) > limit else history
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        uptime = time.time() - self._stats['start_time']
        
        return {
            "uptime": uptime,
            "requests_initiated": self._stats['requests_initiated'],
            "requests_completed": self._stats['requests_completed'],
            "requests_failed": self._stats['requests_failed'],
            "requests_timed_out': self._stats['requests_timed_out'],
            "comparisons_performed": self._stats['comparisons_performed'],
            "dark_launches_detected": self._stats['dark_launches_detected'],
            "active_requests": len(self._active_requests),
            "request_history_size": len(self._request_history),
            "config": self.config.__dict__
        }
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return self.metrics.get_statistics()


# Global shadow engine instance
_global_engine: Optional[ShadowEngine] = None


def get_engine(**kwargs) -> ShadowEngine:
    """
    Get or create the global shadow engine.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global ShadowEngine instance
    """
    global _global_engine
    if _global_engine is None:
        _global_engine = ShadowEngine(**kwargs)
    return _global_engine


# Convenience functions for global usage
async def fetch_with_shadow_globally(
    primary_adapter: Callable,
    shadow_adapter: Callable,
    payload: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """Fetch with shadow using global engine."""
    engine = get_engine()
    return await engine.fetch_with_shadow(
        primary_adapter, shadow_adapter, payload, **kwargs
    )


def get_engine_statistics() -> Dict[str, Any]:
    """Get global engine statistics."""
    engine = get_engine()
    return engine.get_statistics()
