import asyncio
import logging
from typing import Any, Dict, Optional
from decimal import Decimal
from datetime import datetime
import httpx

from ..base_adapter_v2 import BaseSourceAdapter
from ..validators.base_schema import StockDataRequest, ForexDataRequest, CryptoDataRequest, NewsDataRequest
from ..normalization.unified_schema import (
    UnifiedMarketData, UnifiedForexData, UnifiedCryptoData, UnifiedNewsData
)
from ..error_contract import (
    MaifaIngestionError, ProviderTimeoutError, ProviderRateLimitError,
    ProviderNetworkError, ProviderNotFoundError, ProviderValidationError
)


class FinnhubAdapter(BaseSourceAdapter):
    """Canonical implementation of Base Adapter for Finnhub API"""
    
    def __init__(self, redis_client, api_key: Optional[str] = None, **kwargs):
        super().__init__(
            provider_name="Finnhub",
            base_url="https://finnhub.io/api/v1",
            **kwargs
        )
        self.redis_client = redis_client
        self.api_key = api_key
        
        if not self.api_key:
            raise MaifaIngestionError(
                message="API key is required for Finnhub",
                provider_name="Finnhub",
                suggested_action="Provide API key in configuration",
                is_transient=False
            )
    
    async def fetch(self, params: StockDataRequest) -> Dict[str, Any]:
        """Main fetch method for stock data"""
        # Validate parameters
        if not await self.validate_params(params):
            raise ProviderValidationError(
                provider_name="Finnhub",
                validation_errors={"params": "Invalid parameters"}
            )
        
        # Fetch raw data
        raw_data = await self._fetch_internal(params)
        
        # Normalize response
        normalized_data = await self.normalize_response(raw_data)
        
        return normalized_data.dict()
    
    async def validate_params(self, params: StockDataRequest) -> bool:
        """Validate request parameters"""
        try:
            # Basic validation handled by Pydantic
            if not params.symbol:
                return False
            
            # Additional Finnhub-specific validation
            if len(params.symbol) > 10:
                return False
            
            return True
        except Exception:
            return False
    
    async def normalize_response(self, raw_data: Any) -> UnifiedMarketData:
        """Normalize Finnhub response to unified format"""
        try:
            if isinstance(raw_data, dict) and 'c' in raw_data:
                # Quote response
                current_price = Decimal(str(raw_data['c']))
                change = Decimal(str(raw_data['d'])) if raw_data.get('d') is not None else None
                change_percent = Decimal(str(raw_data['dp'])) if raw_data.get('dp') is not None else None
                
                return UnifiedMarketData(
                    symbol=raw_data.get('symbol', ''),
                    price=current_price,
                    change=change,
                    change_percent=change_percent,
                    high=Decimal(str(raw_data['h'])) if raw_data.get('h') else None,
                    low=Decimal(str(raw_data['l'])) if raw_data.get('l') else None,
                    open=Decimal(str(raw_data['o'])) if raw_data.get('o') else None,
                    timestamp=datetime.utcnow(),
                    source_metadata={
                        "provider": "Finnhub",
                        "raw_response": raw_data,
                        "data_type": "quote"
                    }
                )
            
            elif isinstance(raw_data, list) and raw_data:
                # Time series data - use latest
                latest = raw_data[-1]
                current_price = Decimal(str(latest[5]))  # Close price
                
                return UnifiedMarketData(
                    symbol=latest[0] if len(latest) > 0 else '',
                    price=current_price,
                    high=Decimal(str(latest[2])) if len(latest) > 2 else None,
                    low=Decimal(str(latest[3])) if len(latest) > 3 else None,
                    open=Decimal(str(latest[1])) if len(latest) > 1 else None,
                    timestamp=datetime.fromtimestamp(latest[0] / 1000),
                    source_metadata={
                        "provider": "Finnhub",
                        "raw_response": raw_data,
                        "data_type": "timeseries"
                    }
                )
            
            else:
                raise MaifaIngestionError(
                    message="Unexpected response format from Finnhub",
                    provider_name="Finnhub",
                    is_transient=False,
                    context={"raw_data": raw_data}
                )
        
        except (ValueError, TypeError) as e:
            raise MaifaIngestionError(
                message=f"Failed to normalize Finnhub response: {str(e)}",
                provider_name="Finnhub",
                is_transient=False,
                context={"raw_data": raw_data}
            )
    
    async def _fetch_internal(self, params: StockDataRequest) -> Any:
        """Internal fetch method for Finnhub API"""
        try:
            # Fetch quote data
            quote_response = await self.get(
                "quote",
                params={
                    "symbol": params.symbol,
                    "token": self.api_key
                }
            )
            
            if quote_response.status_code == 200:
                quote_data = quote_response.json()
                
                # If no data available, try company profile
                if quote_data.get('c') == 0:
                    profile_response = await self.get(
                        "stock/profile2",
                        params={
                            "symbol": params.symbol,
                            "token": self.api_key
                        }
                    )
                    
                    if profile_response.status_code == 200:
                        profile_data = profile_response.json()
                        if profile_data:
                            # Create mock quote from profile data
                            return {
                                "symbol": params.symbol,
                                "c": 0,  # Current price not available
                                "d": 0,  # Change
                                "dp": 0,  # Change percent
                                "h": 0,  # High
                                "l": 0,  # Low
                                "o": 0,  # Open
                                "profile": profile_data
                            }
                
                return quote_data
            
            elif quote_response.status_code == 401:
                raise MaifaIngestionError(
                    message="Invalid API key for Finnhub",
                    provider_name="Finnhub",
                    suggested_action="Check API key configuration",
                    is_transient=False
                )
            
            elif quote_response.status_code == 404:
                raise ProviderNotFoundError(
                    provider_name="Finnhub",
                    resource=f"Symbol {params.symbol}"
                )
            
            elif quote_response.status_code == 429:
                retry_after = quote_response.headers.get("Retry-After")
                raise ProviderRateLimitError(
                    provider_name="Finnhub",
                    retry_after=int(retry_after) if retry_after else None
                )
            
            else:
                raise MaifaIngestionError(
                    message=f"Finnhub API error: HTTP {quote_response.status_code}",
                    provider_name="Finnhub",
                    is_transient=quote_response.status_code >= 500,
                    context={"status_code": quote_response.status_code, "response": quote_response.text}
                )
        
        except httpx.TimeoutException:
            raise ProviderTimeoutError(
                provider_name="Finnhub",
                timeout_seconds=self.timeout
            )
        
        except httpx.NetworkError as e:
            raise ProviderNetworkError(
                provider_name="Finnhub",
                network_error=str(e)
            )
        
        except MaifaIngestionError:
            raise
        
        except Exception as e:
            raise MaifaIngestionError(
                message=f"Unexpected error fetching from Finnhub: {str(e)}",
                provider_name="Finnhub",
                is_transient=True,
                context={"original_error": str(e)}
            )
    
    async def fetch_company_profile(self, symbol: str) -> Dict[str, Any]:
        """Fetch company profile data"""
        try:
            response = await self.get(
                "stock/profile2",
                params={
                    "symbol": symbol,
                    "token": self.api_key
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise MaifaIngestionError(
                    message=f"Failed to fetch company profile: HTTP {response.status_code}",
                    provider_name="Finnhub",
                    is_transient=response.status_code >= 500
                )
        
        except Exception as e:
            raise MaifaIngestionError(
                message=f"Error fetching company profile: {str(e)}",
                provider_name="Finnhub",
                is_transient=True
            )
    
    async def fetch_news(self, category: str = "general", min_id: int = 0) -> Dict[str, Any]:
        """Fetch market news"""
        try:
            response = await self.get(
                "news",
                params={
                    "category": category,
                    "minId": min_id,
                    "token": self.api_key
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise MaifaIngestionError(
                    message=f"Failed to fetch news: HTTP {response.status_code}",
                    provider_name="Finnhub",
                    is_transient=response.status_code >= 500
                )
        
        except Exception as e:
            raise MaifaIngestionError(
                message=f"Error fetching news: {str(e)}",
                provider_name="Finnhub",
                is_transient=True
            )
    
    async def get_adapter_health(self) -> Dict[str, Any]:
        """Get adapter health status"""
        try:
            # Test API connectivity
            response = await self.get(
                "stock/profile2",
                params={"symbol": "AAPL", "token": self.api_key}
            )
            
            is_healthy = response.status_code == 200
            
            return {
                "provider": "Finnhub",
                "healthy": is_healthy,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds() if hasattr(response, 'elapsed') else None,
                "metrics": self.get_metrics()
            }
        
        except Exception as e:
            return {
                "provider": "Finnhub",
                "healthy": False,
                "error": str(e),
                "metrics": self.get_metrics()
            }
