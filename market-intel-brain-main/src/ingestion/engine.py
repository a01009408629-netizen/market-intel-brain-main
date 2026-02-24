"""
Ingestion Engine - High-Frequency Data Aggregation

Enterprise-grade ingestion engine with <100ms p95 latency,
concurrent processing from 13+ financial and news sources.
"""

import asyncio
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from collections import deque
import statistics

from .config import IngestionConfig, get_config, SourceType
from .workers import WorkerPool, WorkerMetrics


@dataclass
class IngestionMetrics:
    """Comprehensive ingestion engine metrics."""
    
    # Performance metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    
    # Latency tracking
    response_times: deque = field(default_factory=lambda: deque(maxlen=10000))
    p50_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0
    
    # Throughput metrics
    requests_per_second: float = 0.0
    peak_rps: float = 0.0
    
    # Queue metrics
    queue_size: int = 0
    queue_max_size: int = 0
    queue_processed: int = 0
    
    # Source metrics
    source_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Timestamps
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def update_latency_metrics(self):
        """Update latency percentiles."""
        if not self.response_times:
            return
        
        times = list(self.response_times)
        self.p50_latency = statistics.median(times)
        self.p95_latency = statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times)
        self.p99_latency = statistics.quantiles(times, n=100)[98] if len(times) >= 100 else max(times)
    
    def update_throughput_metrics(self):
        """Update throughput metrics."""
        runtime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        if runtime > 0:
            self.requests_per_second = self.total_requests / runtime
            self.peak_rps = max(self.peak_rps, self.requests_per_second)
    
    def get_success_rate(self) -> float:
        """Calculate success rate."""
        total = self.successful_requests + self.failed_requests
        return self.successful_requests / total if total > 0 else 0.0


class IngestionEngine:
    """
    High-performance ingestion engine for concurrent data aggregation.
    
    Features:
    - <100ms p95 latency target
    - 13+ concurrent data sources
    - Aggressive connection pooling
    - Circuit breaker pattern
    - Exponential backoff retry
    - Memory-efficient queue processing
    """
    
    def __init__(
        self,
        config: Optional[IngestionConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.config = config or get_config()
        self.logger = logger or logging.getLogger("IngestionEngine")
        
        # Core components
        self.worker_pool = WorkerPool(
            max_workers=self.config.max_workers,
            logger=self.logger
        )
        
        # Normalization buffer (memory-efficient O(1) queue)
        self.normalization_buffer = asyncio.Queue(
            maxsize=self.config.queue_size
        )
        
        # Metrics tracking
        self.metrics = IngestionMetrics()
        
        # Engine state
        self.is_running = False
        self.background_tasks: List[asyncio.Task] = []
        
        # Performance monitoring
        self.latency_history = deque(maxlen=1000)
        self.throughput_samples = deque(maxlen=60)  # 1-minute samples
        
        self.logger.info("Ingestion engine initialized")
    
    async def start(self):
        """Start the ingestion engine."""
        if self.is_running:
            self.logger.warning("Ingestion engine is already running")
            return
        
        try:
            self.is_running = True
            self.metrics.start_time = datetime.now(timezone.utc)
            
            # Initialize worker pool
            enabled_sources = self.config.get_enabled_sources()
            await self.worker_pool.initialize(enabled_sources)
            
            # Start background tasks
            self.background_tasks = [
                asyncio.create_task(self._queue_processor()),
                asyncio.create_task(self._metrics_collector()),
                asyncio.create_task(self._performance_monitor())
            ]
            
            self.logger.info(f"Ingestion engine started with {len(enabled_sources)} sources")
            
        except Exception as e:
            self.is_running = False
            self.logger.error(f"Failed to start ingestion engine: {e}")
            raise
    
    async def stop(self):
        """Stop the ingestion engine gracefully."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Close worker pool
        await self.worker_pool.close_all()
        
        # Process remaining queue items
        await self._process_remaining_queue()
        
        self.logger.info("Ingestion engine stopped")
    
    async def fetch_data(
        self,
        source_name: str,
        symbol: Optional[str] = None,
        data_type: Optional[str] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch data from a specific source with performance tracking.
        
        Args:
            source_name: Name of the data source
            symbol: Trading symbol (optional)
            data_type: Type of data to fetch (optional)
            **kwargs: Additional parameters
            
        Returns:
            Fetched data or None if failed
        """
        if not self.is_running:
            self.logger.warning("Ingestion engine is not running")
            return None
        
        start_time = time.time()
        
        try:
            # Fetch data using worker pool
            result = await self.worker_pool.fetch_data(
                source_name=source_name,
                symbol=symbol,
                data_type=data_type,
                **kwargs
            )
            
            # Track metrics
            response_time = time.time() - start_time
            self._track_request(success=result is not None, response_time=response_time)
            
            # Add to normalization buffer if successful
            if result:
                await self._add_to_buffer({
                    "source": source_name,
                    "symbol": symbol,
                    "data_type": data_type,
                    "data": result,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "response_time": response_time
                })
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            self._track_request(success=False, response_time=response_time)
            
            self.logger.error(f"Failed to fetch data from {source_name}: {e}")
            return None
    
    async def fetch_batch(
        self,
        requests: List[Dict[str, Any]]
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Fetch data from multiple sources concurrently.
        
        Args:
            requests: List of request dictionaries
            
        Returns:
            List of results (None for failed requests)
        """
        if not self.is_running:
            self.logger.warning("Ingestion engine is not running")
            return [None] * len(requests)
        
        # Create concurrent tasks
        tasks = []
        for request in requests:
            task = asyncio.create_task(
                self.fetch_data(**request)
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Batch request {i} failed: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def get_buffer_items(self, max_items: int = 100) -> List[Dict[str, Any]]:
        """
        Get items from the normalization buffer.
        
        Args:
            max_items: Maximum number of items to retrieve
            
        Returns:
            List of data items from buffer
        """
        items = []
        
        for _ in range(max_items):
            try:
                item = await asyncio.wait_for(
                    self.normalization_buffer.get(),
                    timeout=0.1
                )
                items.append(item)
                self.metrics.queue_processed += 1
                
            except asyncio.TimeoutError:
                break
            except asyncio.QueueEmpty:
                break
        
        return items
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive ingestion metrics."""
        # Update calculated metrics
        self.metrics.update_latency_metrics()
        self.metrics.update_throughput_metrics()
        
        # Get worker pool metrics
        pool_metrics = self.worker_pool.get_pool_metrics()
        
        # Combine all metrics
        return {
            "engine_metrics": {
                "is_running": self.is_running,
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "success_rate": self.metrics.get_success_rate(),
                "p50_latency_ms": self.metrics.p50_latency * 1000,
                "p95_latency_ms": self.metrics.p95_latency * 1000,
                "p99_latency_ms": self.metrics.p99_latency * 1000,
                "requests_per_second": self.metrics.requests_per_second,
                "peak_rps": self.metrics.peak_rps,
                "start_time": self.metrics.start_time.isoformat(),
                "last_update": self.metrics.last_update.isoformat()
            },
            "queue_metrics": {
                "current_size": self.normalization_buffer.qsize(),
                "max_size": self.config.queue_size,
                "utilization": self.normalization_buffer.qsize() / self.config.queue_size,
                "processed": self.metrics.queue_processed
            },
            "pool_metrics": pool_metrics,
            "performance_targets": {
                "p95_latency_target_ms": self.config.p95_latency_target_ms,
                "throughput_target": self.config.throughput_target,
                "p95_achieved": self.metrics.p95_latency * 1000 <= self.config.p95_latency_target_ms,
                "throughput_achieved": self.metrics.requests_per_second >= self.config.throughput_target
            }
        }
    
    async def _queue_processor(self):
        """Background task to process normalization buffer."""
        while self.is_running:
            try:
                # Process buffer in batches
                batch_size = min(self.config.batch_size, self.normalization_buffer.qsize())
                if batch_size > 0:
                    batch = await self.get_buffer_items(batch_size)
                    
                    # Here you would integrate with the normalization layer
                    # For now, just log the batch processing
                    self.logger.debug(f"Processed batch of {len(batch)} items")
                
                await asyncio.sleep(self.config.flush_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Queue processor error: {e}")
                await asyncio.sleep(1.0)
    
    async def _metrics_collector(self):
        """Background task to collect and update metrics."""
        while self.is_running:
            try:
                # Update queue metrics
                self.metrics.queue_size = self.normalization_buffer.qsize()
                self.metrics.queue_max_size = max(self.metrics.queue_max_size, self.metrics.queue_size)
                
                # Update source-specific metrics
                pool_metrics = self.worker_pool.get_pool_metrics()
                self.metrics.source_metrics = pool_metrics.get("worker_metrics", {})
                
                self.metrics.last_update = datetime.now(timezone.utc)
                
                await asyncio.sleep(self.config.metrics_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics collector error: {e}")
                await asyncio.sleep(1.0)
    
    async def _performance_monitor(self):
        """Background task to monitor performance targets."""
        while self.is_running:
            try:
                # Check P95 latency target
                p95_ms = self.metrics.p95_latency * 1000
                if p95_ms > self.config.p95_latency_target_ms:
                    self.logger.warning(
                        f"P95 latency target missed: {p95_ms:.2f}ms > {self.config.p95_latency_target_ms}ms"
                    )
                
                # Check throughput target
                if self.metrics.requests_per_second < self.config.throughput_target:
                    self.logger.warning(
                        f"Throughput target missed: {self.metrics.requests_per_second:.2f} < {self.config.throughput_target}"
                    )
                
                # Log performance summary
                if self.metrics.total_requests % 1000 == 0:  # Every 1000 requests
                    self.logger.info(
                        f"Performance Summary - P95: {p95_ms:.2f}ms, "
                        f"RPS: {self.metrics.requests_per_second:.2f}, "
                        f"Success Rate: {self.metrics.get_success_rate():.2%}"
                    )
                
                await asyncio.sleep(60.0)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Performance monitor error: {e}")
                await asyncio.sleep(1.0)
    
    def _track_request(self, success: bool, response_time: float):
        """Track individual request metrics."""
        self.metrics.total_requests += 1
        
        if success:
            self.metrics.successful_requests += 1
        else:
            self.metrics.failed_requests += 1
        
        self.metrics.total_response_time += response_time
        self.metrics.response_times.append(response_time)
        self.latency_history.append(response_time)
        
        # Update average response time
        total_requests = self.metrics.successful_requests + self.metrics.failed_requests
        if total_requests > 0:
            self.metrics.total_response_time = (
                (self.metrics.total_response_time * (total_requests - 1) + response_time) / total_requests
            )
    
    async def _add_to_buffer(self, item: Dict[str, Any]):
        """Add item to normalization buffer."""
        try:
            await self.normalization_buffer.put(item)
        except asyncio.QueueFull:
            self.logger.warning("Normalization buffer is full, dropping item")
    
    async def _process_remaining_queue(self):
        """Process remaining items in queue during shutdown."""
        remaining_items = self.normalization_buffer.qsize()
        if remaining_items > 0:
            self.logger.info(f"Processing {remaining_items} remaining queue items")
            
            items = await self.get_buffer_items(remaining_items)
            self.logger.info(f"Processed {len(items)} remaining items")


# Global engine instance
_ingestion_engine: Optional[IngestionEngine] = None


def get_ingestion_engine(config: Optional[IngestionConfig] = None) -> IngestionEngine:
    """Get or create global ingestion engine instance."""
    global _ingestion_engine
    if _ingestion_engine is None:
        _ingestion_engine = IngestionEngine(config)
    return _ingestion_engine


async def start_ingestion_engine(config: Optional[IngestionConfig] = None) -> IngestionEngine:
    """Start and return ingestion engine."""
    engine = get_ingestion_engine(config)
    await engine.start()
    return engine


async def stop_ingestion_engine():
    """Stop the global ingestion engine."""
    global _ingestion_engine
    if _ingestion_engine:
        await _ingestion_engine.stop()
