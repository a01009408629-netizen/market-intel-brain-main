"""
Data Source Workers - High-Concurrency Processing

Enterprise-grade worker pool with circuit breaker pattern,
exponential backoff, and aggressive connection pooling.
"""

import asyncio
import aiohttp
import time
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import random
from collections import deque

from .config import SourceConfig, SourceStatus, CircuitBreakerConfig, RetryConfig, ConnectionPoolConfig


class WorkerStatus(Enum):
    """Worker status enumeration."""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    CIRCUIT_OPEN = "circuit_open"


@dataclass
class WorkerMetrics:
    """Worker performance metrics."""
    worker_id: str
    source_name: str
    status: WorkerStatus
    requests_completed: int = 0
    requests_failed: int = 0
    total_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    last_error: Optional[str] = None
    circuit_breaker_trips: int = 0
    average_response_time: float = 0.0
    success_rate: float = 0.0


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance.
    """
    
    def __init__(self, config: CircuitBreakerConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(f"CircuitBreaker")
        
        # State management
        self.failure_count = 0
        self.last_failure_time = None
        self.state = SourceStatus.HEALTHY
        self.half_open_calls = 0
        
        # Metrics
        self.total_calls = 0
        self.successful_calls = 0
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == SourceStatus.CIRCUIT_OPEN:
            if self._should_attempt_reset():
                self.state = SourceStatus.DEGRADED
                self.half_open_calls = 0
                self.logger.info("Circuit breaker transitioning to half-open")
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            self.total_calls += 1
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        if self.last_failure_time is None:
            return False
        
        time_since_failure = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
        return time_since_failure >= self.config.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        self.successful_calls += 1
        self.failure_count = 0
        
        if self.state == SourceStatus.DEGRADED:
            self.half_open_calls += 1
            if self.half_open_calls >= self.config.half_open_max_calls:
                self.state = SourceStatus.HEALTHY
                self.logger.info("Circuit breaker reset to healthy")
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = SourceStatus.CIRCUIT_OPEN
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_status(self) -> SourceStatus:
        """Get current circuit breaker status."""
        return self.state
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "success_rate": self.successful_calls / self.total_calls if self.total_calls > 0 else 0,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None
        }


class RetryHandler:
    """
    Exponential backoff retry handler with jitter.
    """
    
    def __init__(self, config: RetryConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger("RetryHandler")
    
    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with exponential backoff retry."""
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                return await func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                # Don't retry on certain errors
                if self._should_not_retry(e):
                    raise e
                
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {str(e)}"
                    )
                    await asyncio.sleep(delay)
        
        self.logger.error(f"All {self.config.max_attempts} attempts failed")
        raise last_exception
    
    def _should_not_retry(self, exception: Exception) -> bool:
        """Check if exception should not be retried."""
        # Don't retry on authentication errors
        if "401" in str(exception) or "403" in str(exception):
            return True
        
        # Don't retry on not found errors
        if "404" in str(exception):
            return True
        
        return False
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            # Add jitter to prevent thundering herd
            jitter = delay * 0.1 * random.random()
            delay += jitter
        
        return delay


class ConnectionPoolManager:
    """
    Aggressive connection pooling manager for high-performance I/O.
    """
    
    def __init__(self, config: ConnectionPoolConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger("ConnectionPoolManager")
        
        # Connection pool
        self.connector = None
        self.session = None
        
        # Pool metrics
        self.active_connections = 0
        self.total_connections_created = 0
        self.connection_errors = 0
    
    async def initialize(self):
        """Initialize connection pool."""
        try:
            self.connector = aiohttp.TCPConnector(
                limit=self.config.max_connections,
                limit_per_host=self.config.limit_per_host,
                keepalive_timeout=self.config.keepalive_timeout,
                enable_cleanup_closed=self.config.enable_cleanup_closed,
                use_dns_cache=True,
                ttl_dns_cache=300,
                family=0,  # IPv4 preferred
                ssl=False  # Configure based on needs
            )
            
            timeout = aiohttp.ClientTimeout(
                total=self.config.total_timeout,
                connect=self.config.connect_timeout,
                sock_read=self.config.total_timeout  # Use total_timeout as read timeout
            )
            
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'MarketIntelBrain/1.0',
                    'Accept': 'application/json',
                    'Connection': 'keep-alive'
                }
            )
            
            self.logger.info(f"Connection pool initialized: max={self.config.max_connections}, per_host={self.config.limit_per_host}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    async def close(self):
        """Close connection pool."""
        if self.session:
            await self.session.close()
        if self.connector:
            await self.connector.close()
        self.logger.info("Connection pool closed")
    
    async def request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make HTTP request with connection pooling."""
        if not self.session:
            raise RuntimeError("Connection pool not initialized")
        
        try:
            self.active_connections += 1
            response = await self.session.request(method, url, **kwargs)
            return response
            
        except Exception as e:
            self.connection_errors += 1
            raise e
        finally:
            self.active_connections -= 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get connection pool metrics."""
        return {
            "active_connections": self.active_connections,
            "total_connections_created": self.total_connections_created,
            "connection_errors": self.connection_errors,
            "max_connections": self.config.max_connections,
            "limit_per_host": self.config.limit_per_host,
            "keepalive_timeout": self.config.keepalive_timeout
        }


class DataSourceWorker(ABC):
    """
    Abstract base class for data source workers.
    """
    
    def __init__(
        self,
        config: SourceConfig,
        worker_id: str,
        logger: Optional[logging.Logger] = None
    ):
        self.config = config
        self.worker_id = worker_id
        self.logger = logger or logging.getLogger(f"Worker-{worker_id}")
        
        # Initialize components
        self.connection_pool = ConnectionPoolManager(config.connection_pool, self.logger)
        self.circuit_breaker = CircuitBreaker(config.circuit_breaker, self.logger)
        self.retry_handler = RetryHandler(config.retry_config, self.logger)
        
        # Worker state
        self.status = WorkerStatus.IDLE
        self.metrics = WorkerMetrics(
            worker_id=worker_id,
            source_name=config.name,
            status=WorkerStatus.IDLE
        )
        
        # Rate limiting
        self.request_times = deque(maxlen=config.requests_per_minute)
        self.last_request_time = None
    
    async def initialize(self):
        """Initialize worker components."""
        await self.connection_pool.initialize()
        self.logger.info(f"Worker {self.worker_id} initialized for {self.config.name}")
    
    async def close(self):
        """Close worker components."""
        await self.connection_pool.close()
        self.logger.info(f"Worker {self.worker_id} closed")
    
    async def fetch_data(self, **params) -> Optional[Dict[str, Any]]:
        """Fetch data with all protection mechanisms."""
        start_time = time.time()
        
        try:
            # Check rate limiting
            if not self._can_make_request():
                await asyncio.sleep(self._get_rate_limit_delay())
            
            # Execute with circuit breaker and retry
            result = await self.circuit_breaker.call(
                self.retry_handler.execute_with_retry,
                self._fetch_data_internal,
                **params
            )
            
            # Update metrics
            self._update_metrics(success=True, response_time=time.time() - start_time)
            
            return result
            
        except Exception as e:
            # Update metrics
            self._update_metrics(success=False, response_time=time.time() - start_time, error=str(e))
            
            self.logger.error(f"Worker {self.worker_id} failed to fetch data: {e}")
            return None
    
    @abstractmethod
    async def _fetch_data_internal(self, **params) -> Dict[str, Any]:
        """Internal data fetching method to be implemented by subclasses."""
        pass
    
    def _can_make_request(self) -> bool:
        """Check if request can be made based on rate limiting."""
        now = time.time()
        
        # Clean old request times
        cutoff_time = now - 60  # 1 minute window
        while self.request_times and self.request_times[0] < cutoff_time:
            self.request_times.popleft()
        
        # Check if we can make request
        return len(self.request_times) < self.config.requests_per_minute
    
    def _get_rate_limit_delay(self) -> float:
        """Get delay for rate limiting."""
        if not self.request_times:
            return 0.0
        
        # Calculate delay until next allowed request
        oldest_request = self.request_times[0]
        time_until_available = 60.0 - (time.time() - oldest_request)
        
        return max(0.0, time_until_available)
    
    def _update_metrics(self, success: bool, response_time: float, error: Optional[str] = None):
        """Update worker metrics."""
        self.metrics.requests_completed += 1 if success else 0
        self.metrics.requests_failed += 0 if success else 1
        self.metrics.total_response_time += response_time
        self.metrics.last_request_time = datetime.now(timezone.utc)
        self.metrics.last_error = error
        
        # Update calculated metrics
        total_requests = self.metrics.requests_completed + self.metrics.requests_failed
        self.metrics.success_rate = self.metrics.requests_completed / total_requests if total_requests > 0 else 0
        self.metrics.average_response_time = self.metrics.total_response_time / total_requests if total_requests > 0 else 0
        
        # Update status
        if success:
            self.status = WorkerStatus.IDLE
        else:
            self.status = WorkerStatus.ERROR
        
        # Check circuit breaker status
        if self.circuit_breaker.get_status() == SourceStatus.CIRCUIT_OPEN:
            self.status = WorkerStatus.CIRCUIT_OPEN
            self.metrics.circuit_breaker_trips += 1
    
    def get_metrics(self) -> WorkerMetrics:
        """Get current worker metrics."""
        return self.metrics
    
    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed metrics including all components."""
        return {
            "worker_metrics": self.metrics.__dict__,
            "circuit_breaker": self.circuit_breaker.get_metrics(),
            "connection_pool": self.connection_pool.get_metrics(),
            "rate_limit": {
                "requests_per_minute": len(self.request_times),
                "max_requests_per_minute": self.config.requests_per_minute,
                "can_make_request": self._can_make_request()
            }
        }


class BinanceWorker(DataSourceWorker):
    """Binance API worker implementation."""
    
    async def _fetch_data_internal(self, symbol: str = "BTCUSDT", **params) -> Dict[str, Any]:
        """Fetch data from Binance API."""
        url = f"{self.config.base_url}/api/v3/ticker/price"
        
        params = {
            'symbol': symbol,
            **self.config.custom_params,
            **params
        }
        
        headers = {}
        if self.config.api_key:
            headers['X-MBX-APIKEY'] = self.config.api_key
        
        async with self.connection_pool.request('GET', url, params=params, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=await response.text()
                )


class YahooFinanceWorker(DataSourceWorker):
    """Yahoo Finance API worker implementation."""
    
    async def _fetch_data_internal(self, symbol: str = "AAPL", **params) -> Dict[str, Any]:
        """Fetch data from Yahoo Finance API."""
        url = f"{self.config.base_url}/v7/finance/quote"
        
        params = {
            'symbols': symbol,
            'fields': 'regularMarketPrice,regularMarketChange,regularMarketChangePercent',
            **self.config.custom_params,
            **params
        }
        
        async with self.connection_pool.request('GET', url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('quoteResponse', {}).get('result', [{}])[0]
            else:
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=await response.text()
                )


class WorkerPool:
    """
    High-performance worker pool for concurrent data ingestion.
    """
    
    def __init__(self, max_workers: int = 100, logger: Optional[logging.Logger] = None):
        self.max_workers = max_workers
        self.logger = logger or logging.getLogger("WorkerPool")
        
        # Worker management
        self.workers: Dict[str, DataSourceWorker] = {}
        self.worker_tasks: Dict[str, asyncio.Task] = {}
        self.available_workers = asyncio.Queue()
        
        # Pool metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.start_time = datetime.now(timezone.utc)
    
    async def initialize(self, source_configs: List[SourceConfig]):
        """Initialize worker pool with source configurations."""
        for i, config in enumerate(source_configs):
            if not config.enabled:
                continue
            
            # Create worker based on source type
            worker_id = f"{config.name}_{i}"
            worker = self._create_worker(config, worker_id)
            
            await worker.initialize()
            
            self.workers[worker_id] = worker
            await self.available_workers.put(worker_id)
            
            self.logger.info(f"Initialized worker {worker_id} for source {config.name}")
        
        self.logger.info(f"Worker pool initialized with {len(self.workers)} workers")
    
    def _create_worker(self, config: SourceConfig, worker_id: str) -> DataSourceWorker:
        """Create appropriate worker based on source configuration."""
        if config.name.lower() == 'binance':
            return BinanceWorker(config, worker_id, self.logger)
        elif config.name.lower() == 'yahoo_finance':
            return YahooFinanceWorker(config, worker_id, self.logger)
        else:
            # Default worker for other sources
            class DefaultWorker(DataSourceWorker):
                async def _fetch_data_internal(self, **params) -> Dict[str, Any]:
                    # Default implementation for stubbed sources
                    await asyncio.sleep(0.1)  # Simulate network delay
                    return {
                        "source": self.config.name,
                        "data": "mock_data",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
            
            return DefaultWorker(config, worker_id, self.logger)
    
    async def fetch_data(self, source_name: str, **params) -> Optional[Dict[str, Any]]:
        """Fetch data using available worker."""
        worker_id = await self._get_available_worker(source_name)
        if not worker_id:
            self.logger.warning(f"No available worker for source {source_name}")
            return None
        
        worker = self.workers[worker_id]
        
        try:
            self.total_requests += 1
            result = await worker.fetch_data(**params)
            
            if result:
                self.successful_requests += 1
            else:
                self.failed_requests += 1
            
            return result
            
        finally:
            # Return worker to pool
            await self.available_workers.put(worker_id)
    
    async def _get_available_worker(self, source_name: str) -> Optional[str]:
        """Get available worker for specific source."""
        # Try to find worker for specific source
        for _ in range(len(self.workers)):
            try:
                worker_id = await asyncio.wait_for(
                    self.available_workers.get(),
                    timeout=1.0
                )
                
                worker = self.workers[worker_id]
                if worker.config.name.lower() == source_name.lower():
                    return worker_id
                else:
                    # Return to pool if not matching
                    await self.available_workers.put(worker_id)
                    
            except asyncio.TimeoutError:
                continue
        
        return None
    
    async def close_all(self):
        """Close all workers."""
        for worker in self.workers.values():
            await worker.close()
        
        # Cancel any running tasks
        for task in self.worker_tasks.values():
            task.cancel()
        
        self.logger.info("Worker pool closed")
    
    def get_pool_metrics(self) -> Dict[str, Any]:
        """Get comprehensive pool metrics."""
        runtime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        worker_metrics = {}
        for worker_id, worker in self.workers.items():
            worker_metrics[worker_id] = worker.get_detailed_metrics()
        
        return {
            "pool_metrics": {
                "total_workers": len(self.workers),
                "max_workers": self.max_workers,
                "available_workers": self.available_workers.qsize(),
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "success_rate": self.successful_requests / self.total_requests if self.total_requests > 0 else 0,
                "runtime_seconds": runtime,
                "requests_per_second": self.total_requests / runtime if runtime > 0 else 0
            },
            "worker_metrics": worker_metrics
        }
