"""
Production Infrastructure Package
TradFi & Macro Economics Architecture
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
    'RingBufferConfig', 'AOFConfig', 'get_io_optimizer'
]
