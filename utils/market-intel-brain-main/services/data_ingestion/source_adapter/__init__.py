# Source Adapter Layer - MAIFA Data Ingestion Microservice

from .error_contract import *
from .circuit_breaker import *
from .retry_engine import *
from .base_adapter_v2 import *
from .validators.base_schema import *
from .normalization.unified_schema import *
from .adapters.finnhub import *
from .orchestrator.adapter_registry import *

__all__ = [
    # Error Contracts
    'MaifaIngestionError',
    'ProviderTimeoutError',
    'ProviderRateLimitError',
    'ProviderAuthenticationError',
    'ProviderNotFoundError',
    'ProviderServerError',
    'ProviderValidationError',
    'ProviderConfigurationError',
    'ProviderNetworkError',
    'ErrorSeverity',
    
    # Circuit Breaker
    'CircuitState',
    'CircuitBreakerConfig',
    'DistributedCircuitBreaker',
    'CircuitBreakerRegistry',
    
    # Retry Engine
    'RetryConfig',
    'RetryEngine',
    'RetryEngineWithMetrics',
    'RetryMetrics',
    'retry',
    'retry_metrics',
    
    # Base Adapter
    'BaseSourceAdapter',
    'RequestMetrics',
    'UserAgentRotator',
    
    # Validators
    'TimeFrame',
    'BaseMarketDataRequest',
    'StockDataRequest',
    'ForexDataRequest',
    'CryptoDataRequest',
    'NewsDataRequest',
    'EconomicDataRequest',
    'CompanyProfileRequest',
    'FinancialsRequest',
    'TechnicalIndicatorsRequest',
    'SearchRequest',
    
    # Normalization
    'UnifiedMarketData',
    'UnifiedForexData',
    'UnifiedCryptoData',
    'UnifiedNewsData',
    'UnifiedEconomicData',
    'UnifiedCompanyProfile',
    'UnifiedFinancialStatement',
    'UnifiedTechnicalIndicator',
    
    # Adapters
    'FinnhubAdapter',
    
    # Orchestrator
    'AdapterRegistry',
    'get_adapter_registry',
    'get_adapter'
]
