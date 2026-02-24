"""
Binance Adapter - First Concrete Adapter

This adapter demonstrates the integration of all 19 architectural layers:
- Core: BaseSourceAdapter inheritance
- Resilience: Retry decorators and circuit breaker
- Caching: Tiered Cache with SWR
- Validation: Pydantic models for data validation
- Security: Zero-trust principles with SecretStr
- Identity: Session management for request isolation
- Financial Operations: Budget Firewall for cost control
- Registry: Dynamic adapter registration
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional

import httpx
from pydantic import BaseModel, Field

# Import from our 19 architectural layers
from ..services.data_ingestion.source_adapter.base_adapter import BaseSourceAdapter
from ..orchestrator.registry import register_adapter
from ..services.schemas.market_data import (
    UnifiedMarketData, 
    MarketDataSymbol, 
    DataSource, 
    Price,
    create_market_data
)
from ..services.cache.tiered_cache_manager import TieredCacheManager, cached
from ..finops.budget_firewall import get_firewall, BudgetFirewall
from ..security.settings import get_settings
from ..services.data_ingestion.source_adapter.retry_engine import RetryEngineWithMetrics


class BinancePriceRequest(BaseModel):
    """Request model for Binance price fetch."""
    symbol: str = Field(default="BTCUSDT", description="Trading symbol")
    
    class Config:
        extra = "forbid"


@register_adapter(name="binance")
class BinanceAdapter(BaseSourceAdapter):
    """
    Binance API Adapter - Concrete implementation demonstrating full architecture integration.
    
    This adapter showcases:
    - Zero-trust security with encrypted credentials
    - Tiered caching with SWR for performance
    - Budget firewall for cost control
    - Retry mechanisms for resilience
    - Dynamic registration and discovery
    """
    
    def __init__(
        self,
        redis_client,
        provider_name: str = "binance",
        base_url: str = "https://api.binance.com",
        timeout: float = 30.0,
        max_retries: int = 3,
        logger: Optional[logging.Logger] = None
    ):
        super().__init__(
            provider_name=provider_name,
            base_url=base_url,
            redis_client=redis_client,
            timeout=timeout,
            max_retries=max_retries,
            logger=logger or logging.getLogger("BinanceAdapter")
        )
        
        # Load secure settings
        self.settings = get_settings()
        
        # Initialize tiered cache
        self.cache_manager = TieredCacheManager(
            config=self._get_cache_config(),
            logger=self.logger
        )
        
        # Initialize budget firewall
        self.budget_firewall = get_firewall()
        
        # Initialize retry engine with custom config
        self.retry_engine = RetryEngineWithMetrics(
            config=self._get_retry_config(),
            logger=self.logger
        )
        
        self.logger.info("BinanceAdapter initialized with full architecture integration")
    
    def _get_cache_config(self):
        """Get cache configuration."""
        from ..services.cache.tiered_cache_manager import CacheConfig
        return CacheConfig(
            l1_max_size=100,
            l1_ttl=60,  # 1 minute for L1
            l2_ttl=300,  # 5 minutes for L2
            stale_while_revalidate_window=30,  # 30 seconds stale window
            enable_swr=True,
            background_refresh=True,
            redis_url=self.settings.redis_url.get_secret_value()
        )
    
    def _get_retry_config(self):
        """Get retry configuration."""
        from ..services.data_ingestion.source_adapter.retry_engine import RetryConfig
        return RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=True
        )
    
    async def fetch_data(self, params: BinancePriceRequest) -> Dict[str, Any]:
        """
        Fetch BTCUSDT price from Binance API with full layer integration.
        
        This method demonstrates:
        - Budget firewall protection
        - Tiered caching with SWR
        - Retry mechanisms
        - Secure API calls
        """
        # Generate cache key
        cache_key = f"binance_price_{params.symbol}"
        
        # Check cache first with SWR support
        cached_data = await self.cache_manager.get(
            key=cache_key,
            namespace="binance",
            refresh_func=lambda: self._fetch_fresh_data(params)
        )
        
        if cached_data is not None:
            self.logger.debug(f"Cache hit for {params.symbol}")
            return cached_data
        
        # Cache miss - fetch fresh data
        return await self._fetch_fresh_data(params)
    
    async def _fetch_fresh_data(self, params: BinancePriceRequest) -> Dict[str, Any]:
        """
        Fetch fresh data from Binance API with budget and retry protection.
        """
        try:
            # Check budget firewall before making request
            await self.budget_firewall.check_request(
                provider="binance",
                user_id="system",  # Could be extracted from session context
                operation="get_price",
                request_size=len(params.symbol.encode()),
                metadata={"symbol": params.symbol}
            )
            
            # Execute with retry logic
            raw_data = await self.retry_engine.execute_with_retry(
                self._make_binance_request,
                params
            )
            
            # Cache the result
            cache_key = f"binance_price_{params.symbol}"
            await self.cache_manager.set(
                key=cache_key,
                value=raw_data,
                ttl=60,  # 1 minute TTL
                namespace="binance"
            )
            
            return raw_data
            
        except Exception as e:
            self.logger.error(f"Failed to fetch data for {params.symbol}: {e}")
            raise
    
    async def _make_binance_request(self, params: BinancePriceRequest) -> Dict[str, Any]:
        """
        Make actual request to Binance API.
        """
        endpoint = "/api/v3/ticker/price"
        request_params = {"symbol": params.symbol}
        
        # Make HTTP request using base adapter infrastructure
        response = await self.get(endpoint, params=request_params)
        
        if response.status_code != 200:
            raise Exception(f"Binance API error: {response.status_code} - {response.text}")
        
        return response.json()
    
    def normalize_payload(self, raw_data: Dict[str, Any]) -> UnifiedMarketData:
        """
        Convert Binance API response to UnifiedMarketData.
        
        Args:
            raw_data: Raw JSON response from Binance API
            
        Returns:
            UnifiedMarketData with proper validation
        """
        try:
            # Extract data from Binance response
            symbol = raw_data.get("symbol", "BTCUSDT")
            price_str = raw_data.get("price", "0")
            
            # Parse symbol components
            base_symbol = symbol[:symbol.index("USDT")] if "USDT" in symbol else symbol
            quote_currency = "USDT"
            
            # Convert price to Decimal for precision
            price_decimal = Decimal(str(price_str))
            
            # Create UnifiedMarketData using factory function
            market_data = create_market_data(
                symbol=base_symbol,
                asset_type=MarketDataSymbol.CRYPTO,
                exchange="binance",
                price_str=str(price_decimal),
                currency=quote_currency,
                source=DataSource.BINANCE,
                timestamp=datetime.utcnow(),
                additional_data={
                    "raw_symbol": symbol,
                    "provider": "binance",
                    "api_endpoint": "/api/v3/ticker/price"
                }
            )
            
            self.logger.info(f"Normalized Binance data: {symbol} -> {price_decimal}")
            return market_data
            
        except Exception as e:
            self.logger.error(f"Failed to normalize Binance payload: {e}")
            raise ValueError(f"Payload normalization failed: {e}")
    
    async def get_price(self, symbol: str = "BTCUSDT") -> UnifiedMarketData:
        """
        Convenience method to get price for a symbol.
        
        Args:
            symbol: Trading symbol (default: BTCUSDT)
            
        Returns:
            UnifiedMarketData with current price
        """
        request = BinancePriceRequest(symbol=symbol)
        
        # Fetch raw data
        raw_data = await self.fetch_data(request)
        
        # Normalize to unified format
        return self.normalize_payload(raw_data)
    
    async def get_adapter_health(self) -> Dict[str, Any]:
        """Get comprehensive health status of the adapter."""
        try:
            # Test basic connectivity
            test_request = BinancePriceRequest(symbol="BTCUSDT")
            start_time = asyncio.get_event_loop().time()
            
            raw_data = await self.fetch_data(test_request)
            response_time = asyncio.get_event_loop().time() - start_time
            
            # Validate response
            market_data = self.normalize_payload(raw_data)
            
            # Get cache stats
            cache_stats = self.cache_manager.get_stats()
            
            # Get budget status
            budget_status = await self.budget_firewall.get_budget_status(
                provider="binance",
                user_id="system"
            )
            
            return {
                "adapter": "binance",
                "healthy": True,
                "response_time": response_time,
                "last_check": datetime.utcnow().isoformat(),
                "test_symbol": "BTCUSDT",
                "test_price": str(market_data.get_price().value) if market_data.get_price() else None,
                "cache_stats": cache_stats,
                "budget_status": {
                    "remaining_budget": float(budget_status.remaining_budget),
                    "utilization": budget_status.budget_utilization
                },
                "base_metrics": self.get_metrics()
            }
            
        except Exception as e:
            return {
                "adapter": "binance",
                "healthy": False,
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def close(self):
        """Clean up resources."""
        try:
            await super().close()
            await self.cache_manager.close()
            await self.budget_firewall.stop()
            self.logger.info("BinanceAdapter closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing BinanceAdapter: {e}")


# Factory function for easy instantiation
async def create_binance_adapter(redis_client) -> BinanceAdapter:
    """
    Factory function to create and initialize BinanceAdapter.
    
    Args:
        redis_client: Redis client instance
        
    Returns:
        Initialized BinanceAdapter
    """
    adapter = BinanceAdapter(redis_client=redis_client)
    
    # Start budget firewall
    await adapter.budget_firewall.start()
    
    # Perform health check
    health = await adapter.get_adapter_health()
    if not health["healthy"]:
        logging.warning(f"BinanceAdapter health check failed: {health}")
    
    return adapter
