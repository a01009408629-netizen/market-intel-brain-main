"""
Telemetry Data Collector

This module provides a centralized collector for gathering and processing
telemetry data from various sources before exporting to monitoring systems.
"""

import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from threading import Lock
import json

from .tracer import OpenTelemetryTracer, get_tracer
from .metrics import PrometheusMetrics, get_metrics


@dataclass
class TelemetryEvent:
    """Telemetry event data structure."""
    timestamp: float
    event_type: str
    source: str
    provider: Optional[str]
    operation: Optional[str]
    data: Dict[str, Any]
    trace_id: Optional[str] = None
    span_id: Optional[str] = None


@dataclass
class CollectorConfig:
    """Configuration for telemetry collector."""
    max_events: int = 10000
    batch_size: int = 100
    flush_interval: float = 5.0  # seconds
    enable_persistence: bool = False
    persistence_file: Optional[str] = None
    aggregation_window: float = 60.0  # seconds
    enable_compression: bool = False


class TelemetryCollector:
    """
    Centralized telemetry data collector.
    
    This class collects, processes, and aggregates telemetry data
    from various sources before exporting to monitoring systems.
    """
    
    def __init__(
        self,
        config: Optional[CollectorConfig] = None,
        tracer: Optional[OpenTelemetryTracer] = None,
        metrics: Optional[PrometheusMetrics] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize telemetry collector.
        
        Args:
            config: Collector configuration
            tracer: OpenTelemetry tracer instance
            metrics: Prometheus metrics instance
            logger: Logger instance
        """
        self.config = config or CollectorConfig()
        self.tracer = tracer or get_tracer()
        self.metrics = metrics or get_metrics()
        self.logger = logger or logging.getLogger("TelemetryCollector")
        
        # Event storage
        self._events = deque(maxlen=self.config.max_events)
        self._events_lock = Lock()
        
        # Aggregated data
        self._aggregated_data = defaultdict(lambda: defaultdict(float))
        self._aggregation_lock = Lock()
        
        # Background processing
        self._processing_task = None
        self._running = False
        
        # Event processors
        self._event_processors = []
        
        # Statistics
        self._stats = {
            'events_collected': 0,
            'events_processed': 0,
            'events_dropped': 0,
            'last_flush': None,
            'start_time': time.time()
        }
        
        self.logger.info(f"TelemetryCollector initialized (max_events={self.config.max_events})")
    
    def start(self):
        """Start the collector background processing."""
        if self._running:
            return
        
        self._running = True
        self._processing_task = asyncio.create_task(self._processing_loop())
        
        self.logger.info("TelemetryCollector started")
    
    async def stop(self):
        """Stop the collector and flush remaining events."""
        if not self._running:
            return
        
        self._running = False
        
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        # Flush remaining events
        await self._flush_events()
        
        self.logger.info("TelemetryCollector stopped")
    
    def add_event(self, event: TelemetryEvent):
        """
        Add a telemetry event to the collector.
        
        Args:
            event: Telemetry event to add
        """
        with self._events_lock:
            if len(self._events) >= self.config.max_events:
                # Drop oldest event
                self._events.popleft()
                self._stats['events_dropped'] += 1
            
            self._events.append(event)
            self._stats['events_collected'] += 1
        
        self.logger.debug(f"Added event: {event.event_type} from {event.source}")
    
    def add_event_data(
        self,
        event_type: str,
        source: str,
        data: Dict[str, Any],
        provider: Optional[str] = None,
        operation: Optional[str] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None
    ):
        """
        Add event data as a TelemetryEvent.
        
        Args:
            event_type: Type of event
            source: Source of the event
            data: Event data
            provider: Provider name
            operation: Operation name
            trace_id: Trace ID
            span_id: Span ID
        """
        event = TelemetryEvent(
            timestamp=time.time(),
            event_type=event_type,
            source=source,
            provider=provider,
            operation=operation,
            data=data,
            trace_id=trace_id,
            span_id=span_id
        )
        
        self.add_event(event)
    
    def add_span_event(
        self,
        trace_id: str,
        span_id: str,
        event_type: str,
        data: Dict[str, Any]
    ):
        """
        Add a span-related event.
        
        Args:
            trace_id: Trace ID
            span_id: Span ID
            event_type: Event type
            data: Event data
        """
        self.add_event_data(
            event_type=event_type,
            source="span",
            data=data,
            trace_id=trace_id,
            span_id=span_id
        )
    
    def add_metric_event(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        provider: Optional[str] = None
    ):
        """
        Add a metric event.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            labels: Additional labels
            provider: Provider name
        """
        data = {
            "metric_name": metric_name,
            "value": value,
            "labels": labels or {}
        }
        
        self.add_event_data(
            event_type="metric",
            source="metrics",
            data=data,
            provider=provider
        )
    
    def add_error_event(
        self,
        error: Exception,
        provider: Optional[str] = None,
        operation: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Add an error event.
        
        Args:
            error: Exception object
            provider: Provider name
            operation: Operation where error occurred
            context: Additional context
        """
        data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }
        
        self.add_event_data(
            event_type="error",
            source="exception",
            data=data,
            provider=provider,
            operation=operation
        )
    
    def add_performance_event(
        self,
        operation: str,
        duration: float,
        provider: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add a performance event.
        
        Args:
            operation: Operation name
            duration: Duration in seconds
            provider: Provider name
            metadata: Additional metadata
        """
        data = {
            "duration": duration,
            "metadata": metadata or {}
        }
        
        self.add_event_data(
            event_type="performance",
            source="timing",
            data=data,
            provider=provider,
            operation=operation
        )
    
    def register_event_processor(self, processor: Callable[[TelemetryEvent], None]):
        """
        Register a custom event processor.
        
        Args:
            processor: Function to process events
        """
        self._event_processors.append(processor)
        self.logger.info(f"Registered event processor: {processor.__name__}")
    
    async def _processing_loop(self):
        """Background processing loop for events."""
        while self._running:
            try:
                # Process events in batches
                await self._process_events()
                
                # Update aggregations
                await self._update_aggregations()
                
                # Flush aggregated data
                await self._flush_aggregated_data()
                
                # Wait for next iteration
                await asyncio.sleep(self.config.flush_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in processing loop: {e}")
                await asyncio.sleep(1.0)
    
    async def _process_events(self):
        """Process collected events."""
        if not self._events:
            return
        
        # Get batch of events
        events_batch = []
        
        with self._events_lock:
            batch_size = min(self.config.batch_size, len(self._events))
            for _ in range(batch_size):
                events_batch.append(self._events.popleft())
        
        if not events_batch:
            return
        
        # Process events
        for event in events_batch:
            try:
                # Run custom processors
                for processor in self._event_processors:
                    try:
                        if asyncio.iscoroutinefunction(processor):
                            await processor(event)
                        else:
                            processor(event)
                    except Exception as e:
                        self.logger.error(f"Event processor error: {e}")
                
                # Update aggregated data
                self._update_event_aggregation(event)
                
                self._stats['events_processed'] += 1
                
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")
        
        self.logger.debug(f"Processed {len(events_batch)} events")
    
    def _update_event_aggregation(self, event: TelemetryEvent):
        """
        Update aggregated data for an event.
        
        Args:
            event: Event to aggregate
        """
        with self._aggregation_lock:
            # Aggregate by event type and provider
            key = f"{event.event_type}.{event.provider or 'unknown'}"
            
            # Count events
            self._aggregated_data[key]['count'] += 1
            
            # Aggregate numeric values
            for data_key, data_value in event.data.items():
                if isinstance(data_value, (int, float)):
                    self._aggregated_data[key][f"{data_key}_sum"] += data_value
                    self._aggregated_data[key][f"{data_key}_avg"] = (
                        self._aggregated_data[key][f"{data_key}_sum"] / 
                        self._aggregated_data[key]['count']
                    )
                    self._aggregated_data[key][f"{data_key}_min"] = min(
                        self._aggregated_data[key][f"{data_key}_min"],
                        data_value
                    )
                    self._aggregated_data[key][f"{data_key}_max"] = max(
                        self._aggregated_data[key][f"{data_key}_max"],
                        data_value
                    )
    
    async def _update_aggregations(self):
        """Update time-based aggregations."""
        current_time = time.time()
        
        with self._aggregation_lock:
            # This would implement sliding window aggregations
            # For now, we'll keep it simple
            pass
    
    async def _flush_events(self):
        """Flush events to external systems."""
        if not self._events:
            return
        
        # Get events to flush
        events_to_flush = []
        
        with self._events_lock:
            events_to_flush = list(self._events)
            self._events.clear()
        
        if not events_to_flush:
            return
        
        try:
            # Send to external systems
            await self._send_events_to_external(events_to_flush)
            
            # Persist if enabled
            if self.config.enable_persistence and self.config.persistence_file:
                await self._persist_events(events_to_flush)
            
            self._stats['last_flush'] = current_time = time.time()
            self.logger.info(f"Flushed {len(events_to_flush)} events")
            
        except Exception as e:
            self.logger.error(f"Error flushing events: {e}")
    
    async def _flush_aggregated_data(self):
        """Flush aggregated data to external systems."""
        with self._aggregation_lock:
            if not self._aggregated_data:
                return
            
            try:
                # Send aggregated data to Prometheus
                for key, data in self._aggregated_data.items():
                    parts = key.split('.')
                    event_type = parts[0]
                    provider = parts[1]
                    
                    # Update Prometheus metrics
                    if event_type == "request":
                        self.metrics.request_total.labels(
                            provider=provider,
                            operation=data.get('operation', 'unknown'),
                            status=data.get('status', 'unknown')
                        ).inc(data.get('count', 0))
                    
                    elif event_type == "performance":
                        if 'duration' in data:
                            self.metrics.request_duration.labels(
                                provider=provider,
                                operation=data.get('operation', 'unknown')
                            ).observe(data['duration'])
                
                # Clear aggregated data
                self._aggregated_data.clear()
                
            except Exception as e:
                self.logger.error(f"Error flushing aggregated data: {e}")
    
    async def _send_events_to_external(self, events: List[TelemetryEvent]):
        """Send events to external monitoring systems."""
        # This would integrate with external systems like Grafana, ELK, etc.
        # For now, we'll just log them
        for event in events:
            self.logger.debug(f"External event: {event.event_type} from {event.source}")
    
    async def _persist_events(self, events: List[TelemetryEvent]):
        """Persist events to file."""
        if not self.config.persistence_file:
            return
        
        try:
            events_data = [event.__dict__ for event in events]
            
            # Write to file (append mode)
            with open(self.config.persistence_file, 'a') as f:
                for event_data in events_data:
                    f.write(json.dumps(event_data) + '\n')
            
            self.logger.debug(f"Persisted {len(events)} events to {self.config.persistence_file}")
            
        except Exception as e:
            self.logger.error(f"Error persisting events: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get collector statistics.
        
        Returns:
            Statistics dictionary
        """
        with self._events_lock:
            current_events_count = len(self._events)
        
        with self._aggregation_lock:
            aggregation_count = len(self._aggregated_data)
        
        uptime = time.time() - self._stats['start_time']
        
        return {
            'uptime': uptime,
            'events_collected': self._stats['events_collected'],
            'events_processed': self._stats['events_processed'],
            'events_dropped': self._stats['events_dropped'],
            'current_events': current_events_count,
            'aggregation_keys': aggregation_count,
            'last_flush': self._stats['last_flush'],
            'config': {
                'max_events': self.config.max_events,
                'batch_size': self.config.batch_size,
                'flush_interval': self.config.flush_interval,
                'enable_persistence': self.config.enable_persistence
            }
        }
    
    def get_recent_events(
        self,
        event_type: Optional[str] = None,
        provider: Optional[str] = None,
        limit: int = 100
    ) -> List[TelemetryEvent]:
        """
        Get recent events with optional filtering.
        
        Args:
            event_type: Filter by event type
            provider: Filter by provider
            limit: Maximum number of events to return
            
        Returns:
            List of recent events
        """
        with self._events_lock:
            events = list(self._events)
        
        # Apply filters
        filtered_events = []
        for event in events:
            if event_type and event.event_type != event_type:
                continue
            if provider and event.provider != provider:
                continue
            filtered_events.append(event)
        
        return filtered_events[-limit:]
    
    def get_aggregated_data(self) -> Dict[str, Any]:
        """
        Get current aggregated data.
        
        Returns:
            Aggregated data dictionary
        """
        with self._aggregation_lock:
            return dict(self._aggregated_data)
    
    def clear_events(self):
        """Clear all collected events."""
        with self._events_lock:
            self._events.clear()
        
        with self._aggregation_lock:
            self._aggregated_data.clear()
        
        self.logger.info("Cleared all events and aggregated data")


# Global collector instance
_global_collector: Optional[TelemetryCollector] = None


def get_collector(**kwargs) -> TelemetryCollector:
    """
    Get or create the global collector instance.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global TelemetryCollector instance
    """
    global _global_collector
    if _global_collector is None:
        _global_collector = TelemetryCollector(**kwargs)
    return _global_collector


# Global convenience functions
def add_telemetry_event(event_type: str, source: str, **kwargs):
    """Add telemetry event using global collector."""
    collector = get_collector()
    collector.add_event_data(event_type, source, **kwargs)


def add_telemetry_error(error: Exception, **kwargs):
    """Add error event using global collector."""
    collector = get_collector()
    collector.add_error_event(error, **kwargs)


def add_telemetry_performance(operation: str, duration: float, **kwargs):
    """Add performance event using global collector."""
    collector = get_collector()
    collector.add_performance_event(operation, duration, **kwargs)
