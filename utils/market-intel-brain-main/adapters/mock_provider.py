"""
Mock Provider - Integrated Sandbox Logic

Deprecates standalone Sandbox server process and integrates mock functionality
directly into the AdapterRegistry as a MockProvider. Provides dynamic routing
to mock data when external APIs are unavailable or credentials are missing.

Features:
- Dynamic routing from external adapters to mock data
- Deterministic market data generation
- Zero network overhead
- Seamless integration with existing adapter architecture
- Automatic fallback when API keys are missing/invalid
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from services.data_ingestion.source_adapter.base_adapter import BaseSourceAdapter
from services.schemas.market_data import UnifiedMarketData
from services.mock.mock_generator import get_mock_generator, generate_mock_market_data
from orchestrator.registry import register_adapter
from security.settings import get_settings


class MockProvider(BaseSourceAdapter):
    """
    Mock Provider that generates deterministic market data.
    
    This provider serves as a fallback when external APIs are unavailable
    or when API credentials are missing/invalid. It integrates seamlessly
    with the existing adapter architecture.
    """
    
    def __init__(self, redis_client=None, **kwargs):
        """Initialize MockProvider with minimal configuration."""
        # Mock provider doesn't need real Redis client
        self._redis_client = None
        super().__init__(
            provider_name="mock",
            base_url="mock://localhost",  # Mock URL
            redis_client=redis_client,
            **kwargs
        )
        
        self.logger = logging.getLogger("MockProvider")
        self.mock_generator = get_mock_generator()
        
        # Mock provider doesn't need real HTTP client or Redis
        self._http_client = None
        self._redis_client = None
        
        self.logger.info("MockProvider initialized - generating deterministic market data")
    
    async def _fetch_internal(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal fetch method for mock data generation.
        
        Args:
            params: Request parameters (symbol, etc.)
            
        Returns:
            Mock market data as dictionary
        """
        symbol = params.get('symbol', '').upper()
        if not symbol:
            raise ValueError("Symbol parameter is required")
        
        try:
            # Generate mock market data
            market_data = generate_mock_market_data(symbol)
            if market_data is None:
                raise ValueError(f"Failed to generate mock data for {symbol}")
            
            # Convert to dictionary for consistency with other adapters
            return {
                'symbol': market_data.symbol,
                'price': str(market_data.get_price().value),
                'currency': market_data.get_price().currency,
                'exchange': market_data.exchange,
                'source': market_data.source.value,
                'timestamp': market_data.timestamp.isoformat(),
                'volume': getattr(market_data, 'volume', None),
                'asset_type': market_data.asset_type.value,
                'mock': True  # Flag to indicate mock data
            }
            
        except Exception as e:
            self.logger.error(f"Error generating mock data for {symbol}: {e}")
            raise
    
    def normalize_payload(self, raw_data: Dict[str, Any]) -> UnifiedMarketData:
        """
        Normalize mock data to UnifiedMarketData.
        
        Args:
            raw_data: Raw mock data dictionary
            
        Returns:
            UnifiedMarketData instance
        """
        try:
            from services.schemas.market_data import create_market_data, MarketDataSymbol, DataSource
            
            # Parse asset type
            asset_type_map = {
                'crypto': MarketDataSymbol.CRYPTO,
                'stock': MarketDataSymbol.STOCK,
                'forex': MarketDataSymbol.FOREX,
                'commodity': MarketDataSymbol.COMMODITY
            }
            
            # Parse source
            source_map = {
                'mock': DataSource.MOCK,
                'binance': DataSource.BINANCE,
                'nasdaq': DataSource.NASDAQ,
                'forex_com': DataSource.FOREX_COM
            }
            
            asset_type = asset_type_map.get(raw_data.get('asset_type', 'crypto'), MarketDataSymbol.CRYPTO)
            source = source_map.get(raw_data.get('source', 'mock'), DataSource.MOCK)
            
            # Create market data
            market_data = create_market_data(
                symbol=raw_data['symbol'],
                asset_type=asset_type,
                exchange=raw_data['exchange'],
                price_str=raw_data['price'],
                currency=raw_data['currency'],
                source=source,
                timestamp=datetime.fromisoformat(raw_data['timestamp'].replace('Z', '+00:00')),
                volume=raw_data.get('volume')
            )
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error normalizing mock data: {e}")
            raise
    
    async def get_price(self, symbol: str) -> UnifiedMarketData:
        """
        Get price for a symbol using mock data generation.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            UnifiedMarketData with mock data
        """
        try:
            # Generate mock data
            params = {'symbol': symbol}
            raw_data = await self._fetch_internal(params)
            market_data = self.normalize_payload(raw_data)
            
            self.logger.debug(f"Generated mock price for {symbol}: {market_data.get_price().value}")
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error getting mock price for {symbol}: {e}")
            raise
    
    async def get_adapter_health(self) -> Dict[str, Any]:
        """Get mock provider health status."""
        return {
            'healthy': True,
            'provider': 'mock',
            'type': 'deterministic_generator',
            'supported_symbols': self.mock_generator.get_supported_symbols(),
            'seed': self.mock_generator.seed,
            'cache_size': len(self.mock_generator._price_cache),
            'response_time': 0.001,  # Mock response time
            'status': 'operational'
        }
    
    async def close(self):
        """Close mock provider (no cleanup needed)."""
        self.logger.info("MockProvider closed")


class MockRouter:
    """
    Dynamic routing system that intercepts external API calls and routes
    to MockProvider when necessary.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("MockRouter")
        self.settings = get_settings()
        self.mock_provider = None
        
    async def _should_use_mock(self, provider: str) -> bool:
        """
        Determine if mock should be used for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            True if mock should be used
        """
        try:
            # Check if API keys are available for the provider
            if provider.lower() == "binance":
                binance_creds = self.settings.get_binance_credentials()
                api_key = binance_creds.get('api_key', '')
                api_secret = binance_creds.get('api_secret', '')
                
                # Use mock if credentials are missing or placeholder values
                if not api_key or not api_secret or \
                   api_key.startswith('your_') or api_secret.startswith('your_'):
                    return True
            
            # Add checks for other providers as needed
            return False
            
        except Exception as e:
            self.logger.debug(f"Error checking mock routing for {provider}: {e}")
            return True  # Default to mock on error
    
    async def route_request(
        self, 
        provider: str, 
        method: str, 
        params: Dict[str, Any],
        original_adapter: Optional[BaseSourceAdapter] = None
    ) -> Any:
        """
        Route request to mock if necessary, otherwise use original adapter.
        
        Args:
            provider: Target provider name
            method: Method name to call
            params: Method parameters
            original_adapter: Original adapter to use if not mocking
            
        Returns:
            Result from mock or original adapter
        """
        # Check if we should use mock
        if await self._should_use_mock(provider):
            if self.mock_provider is None:
                self.mock_provider = MockProvider()
            
            self.logger.info(f"Routing {provider}.{method} to MockProvider")
            
            # Route to mock provider
            if method == 'get_price':
                symbol = params.get('symbol', '')
                return await self.mock_provider.get_price(symbol)
            else:
                # For other methods, try to call dynamically
                if hasattr(self.mock_provider, method):
                    return await getattr(self.mock_provider, method)(**params)
                else:
                    raise AttributeError(f"MockProvider does not support method: {method}")
        
        # Use original adapter
        if original_adapter is None:
            raise ValueError(f"No original adapter available for provider: {provider}")
        
        self.logger.debug(f"Using original adapter for {provider}.{method}")
        
        if hasattr(original_adapter, method):
            return await getattr(original_adapter, method)(**params)
        else:
            raise AttributeError(f"Adapter {provider} does not support method: {method}")


# Global mock router instance
_mock_router: Optional[MockRouter] = None


def get_mock_router() -> MockRouter:
    """Get or create global mock router instance."""
    global _mock_router
    if _mock_router is None:
        _mock_router = MockRouter()
    return _mock_router


# Register MockProvider in the adapter registry
@register_adapter(name="mock")
class RegisteredMockProvider(MockProvider):
    """Registered MockProvider for dynamic discovery."""
    pass


# Enhanced adapter creation function with mock routing
async def create_adapter_with_mock_routing(
    provider: str, 
    redis_client=None,
    **kwargs
) -> BaseSourceAdapter:
    """
    Create adapter with automatic mock routing.
    
    Args:
        provider: Provider name
        redis_client: Redis client (optional)
        **kwargs: Additional adapter parameters
        
    Returns:
        Adapter instance with mock routing capability
    """
    from orchestrator.registry import AdapterRegistry
    
    registry = AdapterRegistry()
    mock_router = get_mock_router()
    
    # Try to create original adapter
    try:
        if registry.is_registered(provider):
            original_adapter = registry.create_instance(provider, redis_client=redis_client, **kwargs)
        else:
            raise ValueError(f"Provider {provider} not registered")
        
        # Create wrapper that routes to mock when necessary
        class MockRoutingAdapter:
            def __init__(self, original_adapter, provider, mock_router):
                self.original_adapter = original_adapter
                self.provider = provider
                self.mock_router = mock_router
                self.logger = logging.getLogger(f"MockRoutingAdapter.{provider}")
            
            async def get_price(self, symbol: str) -> UnifiedMarketData:
                """Route get_price calls with mock fallback."""
                return await self.mock_router.route_request(
                    self.provider, 
                    'get_price', 
                    {'symbol': symbol},
                    self.original_adapter
                )
            
            async def get_adapter_health(self) -> Dict[str, Any]:
                """Get health status."""
                try:
                    return await self.original_adapter.get_adapter_health()
                except:
                    return await self.mock_router.mock_provider.get_adapter_health()
            
            async def close(self):
                """Close adapter."""
                await self.original_adapter.close()
        
        return MockRoutingAdapter(original_adapter, provider, mock_router)
        
    except Exception as e:
        # If original adapter creation fails, use mock
        logging.getLogger("MockRouting").warning(
            f"Failed to create {provider} adapter, using MockProvider: {e}"
        )
        return MockProvider()


# Utility function to check if mock is being used
async def is_using_mock(provider: str) -> bool:
    """
    Check if a provider is currently using mock data.
    
    Args:
        provider: Provider name
        
    Returns:
        True if mock is being used
    """
    mock_router = get_mock_router()
    return await mock_router._should_use_mock(provider)
