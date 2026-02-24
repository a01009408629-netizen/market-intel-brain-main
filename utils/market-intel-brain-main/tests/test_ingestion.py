"""
Unit Tests for Ingestion Engine

Comprehensive test suite for high-frequency data ingestion
with mocking of Binance API and performance validation.
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any

# Import ingestion components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from ingestion.engine import IngestionEngine, get_ingestion_engine
from ingestion.config import IngestionConfig, SourceConfig, SourceType
from ingestion.workers import BinanceWorker, WorkerPool, CircuitBreaker, RetryHandler


class TestIngestionConfig:
    """Test configuration for ingestion engine."""
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return IngestionConfig(
            max_workers=10,
            queue_size=1000,
            batch_size=50,
            flush_interval=0.1,
            p95_latency_target_ms=100.0,
            throughput_target=100,
            enable_metrics=True,
            metrics_interval=1.0
        )
    
    @pytest.fixture
    def binance_config(self):
        """Create Binance configuration for testing."""
        return SourceConfig(
            name="binance_test",
            source_type=SourceType.CRYPTO,
            base_url="https://api.binance.com",
            api_key="test_key",
            api_secret="test_secret",
            requests_per_second=10,
            requests_per_minute=100,
            connect_timeout=5.0,
            read_timeout=10.0,
            symbols=["BTCUSDT", "ETHUSDT"],
            data_types=["ticker", "depth"]
        )


class TestCircuitBreaker:
    """Test circuit breaker pattern implementation."""
    
    @pytest.fixture
    def circuit_breaker_config(self):
        """Create circuit breaker configuration."""
        from ingestion.workers import CircuitBreakerConfig
        return CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0,
            expected_exception=Exception,
            half_open_max_calls=2
        )
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_success(self, circuit_breaker_config):
        """Test circuit breaker with successful calls."""
        circuit_breaker = CircuitBreaker(circuit_breaker_config)
        
        # Mock successful function
        async def success_func():
            return {"status": "success"}
        
        # Multiple successful calls
        for _ in range(5):
            result = await circuit_breaker.call(success_func)
            assert result["status"] == "success"
        
        # Circuit should remain healthy
        assert circuit_breaker.get_status().value == "healthy"
        
        # Check metrics
        metrics = circuit_breaker.get_metrics()
        assert metrics["total_calls"] == 5
        assert metrics["successful_calls"] == 5
        assert metrics["failure_count"] == 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_failure(self, circuit_breaker_config):
        """Test circuit breaker with failed calls."""
        circuit_breaker = CircuitBreaker(circuit_breaker_config)
        
        # Mock failing function
        async def fail_func():
            raise Exception("Test failure")
        
        # Trigger failures to open circuit
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(fail_func)
        
        # Circuit should be open
        assert circuit_breaker.get_status().value == "circuit_open"
        
        # Subsequent calls should fail immediately
        with pytest.raises(Exception, match="Circuit breaker is open"):
            await circuit_breaker.call(success_func)
        
        # Check metrics
        metrics = circuit_breaker.get_metrics()
        assert metrics["failure_count"] == 3
        assert metrics["successful_calls"] == 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self, circuit_breaker_config):
        """Test circuit breaker recovery after timeout."""
        circuit_breaker = CircuitBreaker(circuit_breaker_config)
        
        async def fail_func():
            raise Exception("Test failure")
        
        async def success_func():
            return {"status": "success"}
        
        # Trigger circuit to open
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(fail_func)
        
        assert circuit_breaker.get_status().value == "circuit_open"
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Next call should succeed (half-open state)
        result = await circuit_breaker.call(success_func)
        assert result["status"] == "success"


class TestRetryHandler:
    """Test retry handler with exponential backoff."""
    
    @pytest.fixture
    def retry_config(self):
        """Create retry configuration."""
        from ingestion.workers import RetryConfig
        return RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            max_delay=1.0,
            exponential_base=2.0,
            jitter=True
        )
    
    @pytest.mark.asyncio
    async def test_retry_success(self, retry_config):
        """Test retry handler with eventual success."""
        retry_handler = RetryHandler(retry_config)
        
        call_count = 0
        
        async def sometimes_fail():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return {"status": "success"}
        
        result = await retry_handler.execute_with_retry(sometimes_fail)
        assert result["status"] == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_max_attempts(self, retry_config):
        """Test retry handler with max attempts reached."""
        retry_handler = RetryHandler(retry_config)
        
        async def always_fail():
            raise Exception("Persistent failure")
        
        with pytest.raises(Exception, match="Persistent failure"):
            await retry_handler.execute_with_retry(always_fail)
    
    @pytest.mark.asyncio
    async def test_retry_no_retry_on_auth_error(self, retry_config):
        """Test that auth errors are not retried."""
        retry_handler = RetryHandler(retry_config)
        
        async def auth_error():
            raise Exception("401 Unauthorized")
        
        with pytest.raises(Exception, match="401 Unauthorized"):
            await retry_handler.execute_with_retry(auth_error)


class TestBinanceWorker:
    """Test Binance worker implementation."""
    
    @pytest.fixture
    def mock_binance_worker(self, binance_config):
        """Create Binance worker with mocked HTTP client."""
        worker = BinanceWorker(binance_config, "test_worker")
        
        # Mock the connection pool
        worker.connection_pool = AsyncMock()
        worker.connection_pool.request = AsyncMock()
        
        return worker
    
    @pytest.mark.asyncio
    async def test_binance_worker_success(self, mock_binance_worker):
        """Test successful Binance API call."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"symbol": "BTCUSDT", "price": "50000.00"})
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        
        mock_binance_worker.connection_pool.request.return_value = mock_context_manager
        
        await mock_binance_worker.initialize()
        
        result = await mock_binance_worker.fetch_data(symbol="BTCUSDT")
        
        assert result is not None
        assert result["symbol"] == "BTCUSDT"
        assert result["price"] == "50000.00"
        
        # Verify metrics
        metrics = mock_binance_worker.get_metrics()
        assert metrics.requests_completed == 1
        assert metrics.requests_failed == 0
        assert metrics.success_rate == 1.0
    
    @pytest.mark.asyncio
    async def test_binance_worker_failure(self, mock_binance_worker):
        """Test Binance API call failure."""
        # Mock failed response
        mock_binance_worker.connection_pool.request.side_effect = Exception("Network error")
        
        await mock_binance_worker.initialize()
        
        result = await mock_binance_worker.fetch_data(symbol="BTCUSDT")
        
        assert result is None
        
        # Verify metrics
        metrics = mock_binance_worker.get_metrics()
        assert metrics.requests_completed == 0
        assert metrics.requests_failed == 1
        assert metrics.success_rate == 0.0


class TestWorkerPool:
    """Test worker pool functionality."""
    
    @pytest.fixture
    def mock_configs(self):
        """Create mock source configurations."""
        configs = []
        
        # Binance config
        binance_config = SourceConfig(
            name="binance",
            source_type=SourceType.CRYPTO,
            base_url="https://api.binance.com",
            api_key="test_key",
            requests_per_second=10,
            symbols=["BTCUSDT"]
        )
        configs.append(binance_config)
        
        # Yahoo Finance config
        yahoo_config = SourceConfig(
            name="yahoo_finance",
            source_type=SourceType.STOCK,
            base_url="https://query1.finance.yahoo.com",
            requests_per_second=5,
            symbols=["AAPL"]
        )
        configs.append(yahoo_config)
        
        return configs
    
    @pytest.mark.asyncio
    async def test_worker_pool_initialization(self, mock_configs):
        """Test worker pool initialization."""
        worker_pool = WorkerPool(max_workers=5)
        
        await worker_pool.initialize(mock_configs)
        
        metrics = worker_pool.get_pool_metrics()
        assert metrics["pool_metrics"]["total_workers"] == 2
        assert metrics["pool_metrics"]["available_workers"] == 2
    
    @pytest.mark.asyncio
    async def test_worker_pool_data_fetch(self, mock_configs):
        """Test data fetching through worker pool."""
        worker_pool = WorkerPool(max_workers=5)
        
        # Mock workers
        with patch.object(worker_pool, '_create_worker') as mock_create:
            mock_worker = AsyncMock()
            mock_worker.fetch_data = AsyncMock(return_value={"data": "test"})
            mock_worker.config.name = "binance"
            mock_create.return_value = mock_worker
            
            await worker_pool.initialize(mock_configs)
            
            result = await worker_pool.fetch_data("binance", symbol="BTCUSDT")
            
            assert result is not None
            assert result["data"] == "test"
            mock_worker.fetch_data.assert_called_once_with(symbol="BTCUSDT")
    
    @pytest.mark.asyncio
    async def test_worker_pool_concurrent_requests(self, mock_configs):
        """Test concurrent request handling."""
        worker_pool = WorkerPool(max_workers=5)
        
        # Mock workers with delay
        with patch.object(worker_pool, '_create_worker') as mock_create:
            mock_worker = AsyncMock()
            
            async def delayed_fetch(**kwargs):
                await asyncio.sleep(0.1)
                return {"source": kwargs.get("source_name"), "data": "test"}
            
            mock_worker.fetch_data = delayed_fetch
            mock_worker.config.name = "binance"
            mock_create.return_value = mock_worker
            
            await worker_pool.initialize(mock_configs)
            
            # Make concurrent requests
            start_time = time.time()
            tasks = [
                worker_pool.fetch_data("binance", symbol=f"SYMBOL_{i}")
                for i in range(3)
            ]
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            # All requests should complete
            assert len(results) == 3
            assert all(result is not None for result in results)
            
            # Should complete concurrently (not sequentially)
            total_time = end_time - start_time
            assert total_time < 0.3  # Should be much less than 0.3s if concurrent


class TestIngestionEngine:
    """Test ingestion engine functionality."""
    
    @pytest.fixture
    def mock_engine(self, test_config):
        """Create ingestion engine with mocked components."""
        engine = IngestionEngine(test_config)
        
        # Mock worker pool
        engine.worker_pool = AsyncMock()
        engine.worker_pool.fetch_data = AsyncMock(return_value={"test": "data"})
        engine.worker_pool.initialize = AsyncMock()
        engine.worker_pool.get_pool_metrics = AsyncMock(return_value={"pool_metrics": {}})
        
        return engine
    
    @pytest.mark.asyncio
    async def test_engine_start_stop(self, mock_engine):
        """Test engine start and stop."""
        # Test start
        await mock_engine.start()
        assert mock_engine.is_running is True
        assert len(mock_engine.background_tasks) == 3  # queue_processor, metrics_collector, performance_monitor
        
        # Test stop
        await mock_engine.stop()
        assert mock_engine.is_running is False
    
    @pytest.mark.asyncio
    async def test_fetch_data_success(self, mock_engine):
        """Test successful data fetching."""
        await mock_engine.start()
        
        result = await mock_engine.fetch_data(
            source_name="binance",
            symbol="BTCUSDT",
            data_type="ticker"
        )
        
        assert result is not None
        assert result["test"] == "data"
        
        # Check metrics
        metrics = mock_engine.get_metrics()
        assert metrics["engine_metrics"]["total_requests"] == 1
        assert metrics["engine_metrics"]["successful_requests"] == 1
        assert metrics["engine_metrics"]["failed_requests"] == 0
    
    @pytest.mark.asyncio
    async def test_fetch_data_failure(self, mock_engine):
        """Test data fetching failure."""
        # Mock worker pool to return None
        mock_engine.worker_pool.fetch_data = AsyncMock(return_value=None)
        
        await mock_engine.start()
        
        result = await mock_engine.fetch_data(
            source_name="binance",
            symbol="BTCUSDT"
        )
        
        assert result is None
        
        # Check metrics
        metrics = mock_engine.get_metrics()
        assert metrics["engine_metrics"]["total_requests"] == 1
        assert metrics["engine_metrics"]["successful_requests"] == 0
        assert metrics["engine_metrics"]["failed_requests"] == 1
    
    @pytest.mark.asyncio
    async def test_batch_fetch(self, mock_engine):
        """Test batch data fetching."""
        await mock_engine.start()
        
        requests = [
            {"source_name": "binance", "symbol": "BTCUSDT"},
            {"source_name": "yahoo_finance", "symbol": "AAPL"},
            {"source_name": "finnhub", "symbol": "GOOGL"}
        ]
        
        results = await mock_engine.fetch_batch(requests)
        
        assert len(results) == 3
        assert all(result is not None for result in results)
        
        # Check metrics
        metrics = mock_engine.get_metrics()
        assert metrics["engine_metrics"]["total_requests"] == 3
        assert metrics["engine_metrics"]["successful_requests"] == 3
    
    @pytest.mark.asyncio
    async def test_buffer_operations(self, mock_engine):
        """Test normalization buffer operations."""
        await mock_engine.start()
        
        # Add items to buffer
        test_items = [
            {"source": "binance", "data": "test1"},
            {"source": "yahoo", "data": "test2"},
            {"source": "finnhub", "data": "test3"}
        ]
        
        for item in test_items:
            await mock_engine._add_to_buffer(item)
        
        # Get items from buffer
        retrieved_items = await mock_engine.get_buffer_items(max_items=2)
        
        assert len(retrieved_items) == 2
        assert retrieved_items[0]["data"] == "test1"
        assert retrieved_items[1]["data"] == "test2"
        
        # Check queue metrics
        metrics = mock_engine.get_metrics()
        assert metrics["queue_metrics"]["current_size"] == 1  # One item left
        assert metrics["queue_metrics"]["processed"] == 2
    
    def test_latency_calculation(self, test_config):
        """Test latency percentile calculations."""
        engine = IngestionEngine(test_config)
        
        # Add sample response times
        sample_times = [0.05, 0.08, 0.12, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45]
        
        for time_val in sample_times:
            engine.metrics.response_times.append(time_val)
        
        engine.metrics.update_latency_metrics()
        
        # Check calculated percentiles
        assert engine.metrics.p50_latency == 0.225  # Median of sample times
        assert engine.metrics.p95_latency == 0.45   # 95th percentile
        assert engine.metrics.p99_latency == 0.45   # 99th percentile (same as 95th in this sample)
    
    def test_performance_targets(self, test_config):
        """Test performance target validation."""
        engine = IngestionEngine(test_config)
        
        # Test P95 target achievement
        engine.metrics.p95_latency = 0.09  # 90ms
        engine.metrics.requests_per_second = 150.0
        
        metrics = engine.get_metrics()
        targets = metrics["performance_targets"]
        
        assert targets["p95_achieved"] is True  # 90ms < 100ms target
        assert targets["throughput_achieved"] is True  # 150 > 100 target


class TestPerformanceValidation:
    """Performance validation tests."""
    
    @pytest.mark.asyncio
    async def test_p95_latency_target(self, test_config):
        """Validate P95 latency target under load."""
        engine = IngestionEngine(test_config)
        
        # Mock fast responses
        engine.worker_pool.fetch_data = AsyncMock(side_effect=[
            {"data": f"test_{i}"} for i in range(100)
        ])
        
        await engine.start()
        
        # Make 100 requests
        tasks = [
            engine.fetch_data("binance", symbol=f"SYMBOL_{i}")
            for i in range(100)
        ]
        await asyncio.gather(*tasks)
        
        # Wait for metrics to update
        await asyncio.sleep(0.2)
        
        metrics = engine.get_metrics()
        p95_ms = metrics["engine_metrics"]["p95_latency_ms"]
        
        # Should meet P95 target
        assert p95_ms < test_config.p95_latency_target_ms
        
        await engine.stop()
    
    @pytest.mark.asyncio
    async def test_throughput_target(self, test_config):
        """Validate throughput target under load."""
        engine = IngestionEngine(test_config)
        
        # Mock fast responses
        engine.worker_pool.fetch_data = AsyncMock(return_value={"data": "test"})
        
        await engine.start()
        
        start_time = time.time()
        
        # Make requests for 2 seconds
        tasks = []
        for _ in range(200):  # Aim for 100 RPS
            tasks.append(engine.fetch_data("binance", symbol="BTCUSDT"))
        
        # Run for 2 seconds
        await asyncio.wait_for(
            asyncio.gather(*tasks),
            timeout=2.0
        )
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        # Calculate actual RPS
        actual_rps = 200 / actual_duration
        
        # Should meet throughput target
        assert actual_rps >= test_config.throughput_target * 0.8  # Allow 20% variance
        
        await engine.stop()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
