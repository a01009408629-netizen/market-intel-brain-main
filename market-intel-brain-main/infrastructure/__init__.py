"""
Production Infrastructure Package
TradFi & Macro Economics Architecture
Enterprise-Grade Components for Market Intelligence Platform
"""

from .secrets_manager import SecretsManager, get_secrets_manager
from .data_normalization import (
    UnifiedInternalSchema, DataType, SourceType,
    BaseProvider, DataNormalizationFactory, get_data_factory
)
from .rate_limiter import (
    RateLimiter, APIGateway, RateLimitConfig, RateLimitUnit,
    get_rate_limiter, get_api_gateway
)
from .io_optimizer import (
    RingBuffer, AOFWriter, IOOptimizer,
    RingBufferConfig, AOFConfig, get_io_optimizer
)
from .database import (
    DatabaseConfig, EnterpriseDatabaseManager, get_db_manager,
    get_postgres_session, get_redis_client
)
from .auth import (
    EnterpriseAuthManager, get_auth_manager, get_current_user,
    get_current_active_user, require_permission, require_role,
    api_key_auth, UserRole, Permission, APIKeyCreate, APIKeyResponse
)
from .monitoring import (
    EnterpriseMetrics, EnterpriseLogger, EnterpriseAlerting,
    SystemMonitor, MetricsMiddleware, track_performance,
    enterprise_metrics, enterprise_logger, enterprise_alerting,
    initialize_monitoring, cleanup_monitoring
)
from .performance import (
    EnterpriseCache, EnterpriseLoadBalancer, ConnectionPoolManager,
    CacheConfig, LoadBalancerConfig, BackendServer, cached,
    enterprise_cache, enterprise_load_balancer, connection_pool_manager,
    initialize_performance, cleanup_performance
)
from .data_pipeline import (
    EnterpriseDataPipeline, EnterpriseMessageQueue, DataProcessor,
    PipelineMessage, ProcessingResult, MessageType, ProcessingStatus,
    MarketDataProcessor, NewsDataProcessor,
    enterprise_pipeline, initialize_data_pipeline, cleanup_data_pipeline
)

__all__ = [
    # Secrets Manager
    'SecretsManager', 'get_secrets_manager',
    
    # Data Normalization
    'UnifiedInternalSchema', 'DataType', 'SourceType',
    'BaseProvider', 'DataNormalizationFactory', 'get_data_factory',
    
    # Rate Limiting
    'RateLimiter', 'APIGateway', 'RateLimitConfig', 'RateLimitUnit',
    'get_rate_limiter', 'get_api_gateway',
    
    # I/O Optimizer
    'RingBuffer', 'AOFWriter', 'IOOptimizer',
    'RingBufferConfig', 'AOFConfig', 'get_io_optimizer',
    
    # Database
    'DatabaseConfig', 'EnterpriseDatabaseManager', 'get_db_manager',
    'get_postgres_session', 'get_redis_client',
    
    # Authentication & Authorization
    'EnterpriseAuthManager', 'get_auth_manager', 'get_current_user',
    'get_current_active_user', 'require_permission', 'require_role',
    'api_key_auth', 'UserRole', 'Permission', 'APIKeyCreate', 'APIKeyResponse',
    
    # Monitoring & Observability
    'EnterpriseMetrics', 'EnterpriseLogger', 'EnterpriseAlerting',
    'SystemMonitor', 'MetricsMiddleware', 'track_performance',
    'enterprise_metrics', 'enterprise_logger', 'enterprise_alerting',
    'initialize_monitoring', 'cleanup_monitoring',
    
    # Performance & Scalability
    'EnterpriseCache', 'EnterpriseLoadBalancer', 'ConnectionPoolManager',
    'CacheConfig', 'LoadBalancerConfig', 'BackendServer', 'cached',
    'enterprise_cache', 'enterprise_load_balancer', 'connection_pool_manager',
    'initialize_performance', 'cleanup_performance',
    
    # Data Pipeline & Processing
    'EnterpriseDataPipeline', 'EnterpriseMessageQueue', 'DataProcessor',
    'PipelineMessage', 'ProcessingResult', 'MessageType', 'ProcessingStatus',
    'MarketDataProcessor', 'NewsDataProcessor',
    'enterprise_pipeline', 'initialize_data_pipeline', 'cleanup_data_pipeline'
]
