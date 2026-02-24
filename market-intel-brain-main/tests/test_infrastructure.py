"""
Enterprise Testing Framework
Comprehensive unit tests, integration tests, and end-to-end tests for Market Intel Brain
"""

import pytest
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
import aiohttp
import aiofiles
from pathlib import Path
import tempfile
import os

# Import infrastructure components
from infrastructure import (
    EnterpriseDatabaseManager, EnterpriseAuthManager, EnterpriseMetrics,
    EnterpriseCache, EnterpriseLoadBalancer, EnterpriseDataPipeline,
    DatabaseConfig, CacheConfig, LoadBalancerConfig,
    PipelineMessage, MessageType, UserRole, Permission
)


class TestDatabaseManager:
    """Test suite for Enterprise Database Manager."""
    
    @pytest.fixture
    async def db_config(self):
        """Test database configuration."""
        return DatabaseConfig(
            postgres_host="localhost",
            postgres_port=5432,
            postgres_db="test_market_intel",
            postgres_user="test_user",
            postgres_password="test_password",
            redis_host="localhost",
            redis_port=6379,
            redis_password="",
            redis_db=1
        )
    
    @pytest.fixture
    async def db_manager(self, db_config):
        """Test database manager instance."""
        manager = EnterpriseDatabaseManager(db_config)
        yield manager
        await manager.close()
    
    @pytest.mark.asyncio
    async def test_database_initialization(self, db_manager):
        """Test database initialization."""
        with patch('asyncpg.connect') as mock_connect, \
             patch('aioredis.from_url') as mock_redis:
            
            mock_connect.return_value = AsyncMock()
            mock_redis.return_value = AsyncMock()
            
            await db_manager.initialize()
            
            assert db_manager._initialized is True
            mock_connect.assert_called()
            mock_redis.assert_called()
    
    @pytest.mark.asyncio
    async def test_health_check(self, db_manager):
        """Test database health check."""
        db_manager._initialized = True
        db_manager.postgres_engine = AsyncMock()
        db_manager.redis_pool = AsyncMock()
        
        with patch.object(db_manager.postgres_engine, 'begin') as mock_pg, \
             patch('aioredis.Redis') as mock_redis:
            
            mock_pg.return_value.__aenter__.return_value.execute = AsyncMock()
            mock_redis.return_value.ping = AsyncMock()
            
            health = await db_manager.health_check()
            
            assert health["overall"] == "healthy"
            assert health["postgres"]["status"] == "healthy"
            assert health["redis"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_audit_logging(self, db_manager):
        """Test audit logging functionality."""
        db_manager._initialized = True
        
        with patch.object(db_manager, 'get_postgres_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.add = Mock()
            mock_session.return_value.__aenter__.return_value.commit = AsyncMock()
            
            await db_manager.log_audit_event(
                user_id="test_user",
                action="login",
                resource="auth",
                details={"ip": "127.0.0.1"}
            )
            
            mock_session.assert_called_once()


class TestAuthenticationManager:
    """Test suite for Enterprise Authentication Manager."""
    
    @pytest.fixture
    async def auth_manager(self):
        """Test authentication manager instance."""
        manager = EnterpriseAuthManager()
        with patch.object(manager, 'initialize'):
            await manager.initialize()
        yield manager
    
    def test_password_hashing(self, auth_manager):
        """Test password hashing and verification."""
        password = "test_password_123"
        hashed = auth_manager._get_password_hash(password)
        
        assert hashed != password
        assert auth_manager._verify_password(password, hashed) is True
        assert auth_manager._verify_password("wrong_password", hashed) is False
    
    def test_api_key_generation(self, auth_manager):
        """Test API key generation and hashing."""
        api_key = auth_manager._generate_api_key()
        key_hash = auth_manager._hash_api_key(api_key)
        
        assert api_key.startswith("mib_")
        assert len(api_key) > 30
        assert key_hash != api_key
        assert auth_manager._hash_api_key(api_key) == key_hash  # Consistent hashing
    
    @pytest.mark.asyncio
    async def test_jwt_token_creation_and_verification(self, auth_manager):
        """Test JWT token creation and verification."""
        from infrastructure.auth import User
        
        user = User(
            id="test_user_001",
            email="test@example.com",
            username="testuser",
            role=UserRole.ANALYST,
            created_at=datetime.now(timezone.utc)
        )
        
        # Create token
        token = await auth_manager.create_access_token(user)
        assert isinstance(token, str)
        assert len(token) > 50
        
        # Verify token
        token_data = await auth_manager.verify_token(token)
        assert token_data.user_id == user.id
        assert token_data.username == user.username
        assert token_data.role == user.role
        assert Permission.READ_DATA in token_data.permissions
    
    @pytest.mark.asyncio
    async def test_user_authentication(self, auth_manager):
        """Test user authentication."""
        # Valid credentials
        user = await auth_manager.authenticate_user("admin", "admin123")
        assert user is not None
        assert user.username == "admin"
        assert user.role == UserRole.ADMIN
        
        # Invalid credentials
        user = await auth_manager.authenticate_user("admin", "wrong_password")
        assert user is None


class TestMonitoringSystem:
    """Test suite for Enterprise Monitoring System."""
    
    @pytest.fixture
    def metrics(self):
        """Test metrics instance."""
        return EnterpriseMetrics()
    
    def test_counter_metrics(self, metrics):
        """Test counter metrics."""
        metrics.increment_counter("test_counter", {"label1": "value1"})
        metrics.increment_counter("test_counter", {"label1": "value1"}, 5)
        
        # Check that metric exists and has correct values
        assert "test_counter" in metrics.metrics
        
        # Get metrics output
        output = metrics.get_metrics()
        assert "test_counter" in output
        assert "test_counter_total" in output
    
    def test_histogram_metrics(self, metrics):
        """Test histogram metrics."""
        metrics.observe_histogram("test_histogram", 0.5, {"label1": "value1"})
        metrics.observe_histogram("test_histogram", 1.5, {"label1": "value1"})
        
        output = metrics.get_metrics()
        assert "test_histogram" in output
    
    def test_gauge_metrics(self, metrics):
        """Test gauge metrics."""
        metrics.set_gauge("test_gauge", 42.0)
        metrics.set_gauge("test_gauge", 84.0, {"label1": "value1"})
        
        output = metrics.get_metrics()
        assert "test_gauge" in output
    
    def test_structured_logging(self):
        """Test structured logging."""
        from infrastructure.monitoring import EnterpriseLogger
        
        logger = EnterpriseLogger("test_logger")
        
        with patch.object(logger.logger, 'info') as mock_info:
            logger.info("Test message", user_id="test_user", action="test")
            
            mock_info.assert_called_once()
            call_args = mock_info.call_args[0][0]
            
            # Verify JSON structure
            log_data = json.loads(call_args)
            assert log_data["message"] == "Test message"
            assert log_data["user_id"] == "test_user"
            assert log_data["action"] == "test"
            assert "timestamp" in log_data
            assert log_data["level"] == "INFO"


class TestPerformanceSystem:
    """Test suite for Enterprise Performance System."""
    
    @pytest.fixture
    async def cache(self):
        """Test cache instance."""
        mock_pool = AsyncMock()
        cache = EnterpriseCache(mock_pool)
        cache.redis_client = AsyncMock()
        await cache.initialize()
        return cache
    
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache):
        """Test cache set and get operations."""
        key = "test_key"
        value = {"data": "test_value", "timestamp": time.time()}
        
        # Mock Redis operations
        cache.redis_client.get.return_value = None
        cache.redis_client.setex = AsyncMock()
        
        # Set value
        await cache.set(key, value)
        
        # Get value (should be from local cache)
        result = await cache.get(key)
        assert result == value
        
        # Verify Redis was called for set operation
        cache.redis_client.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_redis_fallback(self, cache):
        """Test cache Redis fallback when local cache misses."""
        key = "test_key"
        value = {"data": "test_value"}
        
        # Clear local cache
        cache.local_cache.clear()
        
        # Mock Redis return
        serialized_data = cache._serialize_value(value)
        cache.redis_client.get.return_value = serialized_data
        
        # Get value
        result = await cache.get(key)
        assert result == value
        
        # Verify value is now in local cache
        cache_key = cache._generate_cache_key(key)
        assert cache_key in cache.local_cache
    
    @pytest.mark.asyncio
    async def test_load_balancer_round_robin(self):
        """Test load balancer round robin strategy."""
        from infrastructure.performance import BackendServer, EnterpriseLoadBalancer
        
        config = LoadBalancerConfig(strategy="round_robin")
        lb = EnterpriseLoadBalancer(config)
        
        # Add backends
        backend1 = BackendServer("server1", "localhost", 8001)
        backend2 = BackendServer("server2", "localhost", 8002)
        backend3 = BackendServer("server3", "localhost", 8003)
        
        lb.add_backend(backend1)
        lb.add_backend(backend2)
        lb.add_backend(backend3)
        
        # Test round robin selection
        selected = [lb.select_backend() for _ in range(6)]
        selected_ids = [b.id for b in selected]
        
        assert selected_ids == ["server1", "server2", "server3", "server1", "server2", "server3"]
    
    @pytest.mark.asyncio
    async def test_load_balancer_least_connections(self):
        """Test load balancer least connections strategy."""
        from infrastructure.performance import BackendServer, EnterpriseLoadBalancer
        
        config = LoadBalancerConfig(strategy="least_connections")
        lb = EnterpriseLoadBalancer(config)
        
        # Add backends
        backend1 = BackendServer("server1", "localhost", 8001)
        backend2 = BackendServer("server2", "localhost", 8002)
        
        lb.add_backend(backend1)
        lb.add_backend(backend2)
        
        # Simulate connections
        backend1.active_connections = 5
        backend2.active_connections = 2
        
        # Test least connections selection
        selected = lb.select_backend()
        assert selected.id == "server2"  # Should select server with fewer connections


class TestDataPipeline:
    """Test suite for Enterprise Data Pipeline."""
    
    @pytest.fixture
    async def pipeline(self):
        """Test data pipeline instance."""
        from infrastructure.data_pipeline import EnterpriseDataPipeline
        
        pipeline = EnterpriseDataPipeline()
        yield pipeline
        await pipeline.close()
    
    @pytest.mark.asyncio
    async def test_market_data_processor(self):
        """Test market data processor."""
        from infrastructure.data_pipeline import MarketDataProcessor, PipelineMessage, MessageType
        
        processor = MarketDataProcessor()
        
        # Create test message
        message = PipelineMessage(
            id="test_msg_001",
            type=MessageType.MARKET_DATA,
            data={
                "symbol": "AAPL",
                "price": 150.25,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "volume": 1000000
            },
            timestamp=datetime.now(timezone.utc),
            source="test_source"
        )
        
        # Process message
        result = await processor.process(message)
        
        assert result.status.value == "completed"
        assert result.result is not None
        assert "processed_at" in result.result
        assert result.result["symbol"] == "AAPL"
        assert result.result["processed_by"] == "market_data_processor"
    
    @pytest.mark.asyncio
    async def test_news_data_processor(self):
        """Test news data processor."""
        from infrastructure.data_pipeline import NewsDataProcessor, PipelineMessage, MessageType
        
        processor = NewsDataProcessor()
        
        # Create test message
        message = PipelineMessage(
            id="test_msg_002",
            type=MessageType.NEWS_DATA,
            data={
                "title": "Test News Article",
                "content": "This is a test news article content.",
                "source": "test_news",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            timestamp=datetime.now(timezone.utc),
            source="test_source"
        )
        
        # Process message
        result = await processor.process(message)
        
        assert result.status.value == "completed"
        assert result.result is not None
        assert "processed_at" in result.result
        assert result.result["title"] == "Test News Article"
        assert result.result["processed_by"] == "news_data_processor"
    
    @pytest.mark.asyncio
    async def test_message_queue_operations(self):
        """Test message queue send and receive operations."""
        from infrastructure.data_pipeline import EnterpriseMessageQueue, PipelineMessage, MessageType
        
        # Create test queue
        queue = EnterpriseMessageQueue("redis", redis_url="redis://localhost:6379/2")
        
        with patch('aioredis.from_url') as mock_redis:
            mock_redis.return_value = AsyncMock()
            mock_redis.return_value.ping = AsyncMock()
            mock_redis.return_value.lpush = AsyncMock()
            mock_redis.return_value.brpop = AsyncMock(return_value=None)  # No messages
            
            await queue.initialize()
            
            # Create test message
            message = PipelineMessage(
                id="test_msg_003",
                type=MessageType.SYSTEM_EVENT,
                data={"event": "test"},
                timestamp=datetime.now(timezone.utc),
                source="test"
            )
            
            # Send message
            await queue.send_message("test_queue", message)
            
            # Verify send was called
            mock_redis.return_value.lpush.assert_called_once()
            
            # Receive message (returns None when no messages)
            result = await queue.receive_message("test_queue")
            assert result is None
            
            await queue.close()


class TestIntegration:
    """Integration tests for the entire infrastructure."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_integration(self):
        """Test full pipeline integration."""
        from infrastructure.data_pipeline import (
            EnterpriseDataPipeline, MarketDataProcessor, NewsDataProcessor,
            EnterpriseMessageQueue, PipelineMessage, MessageType
        )
        
        # Create pipeline
        pipeline = EnterpriseDataPipeline()
        
        # Add processors
        pipeline.add_processor(MarketDataProcessor())
        pipeline.add_processor(NewsDataProcessor())
        
        # Mock queue
        mock_queue = AsyncMock()
        mock_queue.receive_message = AsyncMock(return_value=None)  # No messages
        
        pipeline.add_queue("test_queue", mock_queue)
        
        # Initialize
        with patch.object(mock_queue, 'initialize'):
            await pipeline.initialize()
        
        # Start processing (will stop immediately due to no messages)
        await pipeline.start_processing()
        await asyncio.sleep(0.1)  # Brief processing time
        await pipeline.stop_processing()
        
        # Verify stats
        stats = pipeline.get_stats()
        assert "total_processed" in stats
        assert "total_failed" in stats
        assert "processor_stats" in stats
    
    @pytest.mark.asyncio
    async def test_database_auth_integration(self):
        """Test database and authentication integration."""
        from infrastructure.auth import EnterpriseAuthManager
        from infrastructure.database import EnterpriseDatabaseManager, DatabaseConfig
        
        # Create instances
        db_config = DatabaseConfig()
        db_manager = EnterpriseDatabaseManager(db_config)
        auth_manager = EnterpriseAuthManager()
        
        # Mock database operations
        with patch.object(db_manager, 'initialize'), \
             patch.object(auth_manager, 'initialize'), \
             patch.object(db_manager, 'get_postgres_session') as mock_session:
            
            await db_manager.initialize()
            await auth_manager.initialize()
            auth_manager.db_manager = db_manager
            
            # Test API key creation
            from infrastructure.auth import APIKeyCreate
            api_key_data = APIKeyCreate(
                name="Test API Key",
                permissions=["read_data"],
                rate_limit=1000
            )
            
            mock_session.return_value.__aenter__.return_value.add = Mock()
            mock_session.return_value.__aenter__.return_value.commit = AsyncMock()
            
            result = await auth_manager.create_api_key("test_user", api_key_data)
            
            assert result.name == "Test API Key"
            assert result.permissions == ["read_data"]
            assert result.api_key.startswith("mib_")


# Test configuration
pytest_plugins = []

# Test markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.e2e = pytest.mark.e2e

# Test configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")


# Test fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
async def mock_redis():
    """Mock Redis client."""
    mock = AsyncMock()
    mock.ping = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.keys = AsyncMock(return_value=[])
    return mock


@pytest.fixture
async def mock_postgres():
    """Mock PostgreSQL connection."""
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=AsyncMock())
    mock.fetch = AsyncMock(return_value=[])
    mock.fetchrow = AsyncMock(return_value=None)
    return mock


# Performance testing utilities
class PerformanceTester:
    """Utility class for performance testing."""
    
    @staticmethod
    async def measure_async_time(func, *args, **kwargs):
        """Measure execution time of async function."""
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        return result, end_time - start_time
    
    @staticmethod
    def benchmark_function(func, iterations=1000):
        """Benchmark function performance."""
        times = []
        for _ in range(iterations):
            start_time = time.time()
            func()
            end_time = time.time()
            times.append(end_time - start_time)
        
        return {
            "avg_time": sum(times) / len(times),
            "min_time": min(times),
            "max_time": max(times),
            "total_time": sum(times),
            "iterations": iterations
        }


# Test data generators
class TestDataGenerator:
    """Generate test data for various components."""
    
    @staticmethod
    def generate_market_data(symbol: str = "AAPL") -> Dict[str, Any]:
        """Generate market data test sample."""
        import random
        return {
            "symbol": symbol,
            "price": round(random.uniform(100, 200), 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "volume": random.randint(100000, 1000000),
            "bid": round(random.uniform(99, 199), 2),
            "ask": round(random.uniform(101, 201), 2)
        }
    
    @staticmethod
    def generate_news_data() -> Dict[str, Any]:
        """Generate news data test sample."""
        return {
            "title": "Test Market News Article",
            "content": "This is a test news article about market movements and financial data.",
            "source": "test_news_agency",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "author": "Test Reporter",
            "category": "finance"
        }
    
    @staticmethod
    def generate_user_data() -> Dict[str, Any]:
        """Generate user data test sample."""
        return {
            "id": f"user_{int(time.time())}",
            "username": f"testuser_{int(time.time())}",
            "email": f"test_{int(time.time())}@example.com",
            "role": UserRole.ANALYST,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
