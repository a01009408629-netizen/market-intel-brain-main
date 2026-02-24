import asyncio
import logging
from typing import Any, Dict, Optional
from decimal import Decimal
from datetime import datetime
import httpx
import os

from ..base_adapter_v2 import BaseSourceAdapter
from ..validators.base_schema import StockDataRequest
from ..normalization.unified_schema import UnifiedMarketData
from ..error_contract import (
    MaifaIngestionError, ProviderTimeoutError, ProviderRateLimitError,
    ProviderNetworkError, ProviderNotFoundError, ProviderValidationError
)


class MarketStackAdapter(BaseSourceAdapter):
    """MarketStack API adapter"""
    
    BASE_URL = "http://api.marketstack.com/v1"
    
    def __init__(self, redis_client, api_key: Optional[str] = None, **kwargs):
        super().__init__(
            provider_name="MarketStack",
            base_url=self.BASE_URL,
            **kwargs
        )
        self.redis_client = redis_client
        self.api_key = api_key or os.getenv("MARKETSTACK_API_KEY")
        
        if not self.api_key:
            raise MaifaIngestionError(
                message="API key is required for MarketStack",
                provider_name="MarketStack",
                suggested_action="Set MARKETSTACK_API_KEY environment variable",
                is_transient=False
            )
    
    async def fetch(self, params: StockDataRequest) -> Dict[str, Any]:
        """Fetch stock data from MarketStack"""
        if not await self.validate_params(params):
            raise ProviderValidationError(
                provider_name="MarketStack",
                validation_errors={"params": "Invalid parameters"}
            )
        
        raw_data = await self._fetch_internal(params)
        normalized_data = await self.normalize_response(raw_data)
        return normalized_data.dict()
    
    async def validate_params(self, params: StockDataRequest) -> bool:
        """Validate request parameters"""
        return bool(params.symbol and len(params.symbol.strip()) > 0)
    
    async def normalize_response(self, raw_data: Any) -> UnifiedMarketData:
        """Normalize MarketStack response to unified format"""
        try:
            if isinstance(raw_data, dict) and 'data' in raw_data:
                data_list = raw_data['data']
                
                if not data_list or len(data_list) == 0:
                    raise ProviderNotFoundError(
                        provider_name="MarketStack",
                        resource="Stock data"
                    )
                
                # Get the latest data point
                latest_data = data_list[0]
                
                current_price = Decimal(str(latest_data.get('last', 0)))
                open_price = Decimal(str(latest_data.get('open', 0)))
                high_price = Decimal(str(latest_data.get('high', 0)))
                low_price = Decimal(str(latest_data.get('low', 0)))
                volume = latest_data.get('volume', 0)
                
                # Calculate change
                change = current_price - open_price if open_price > 0 else None
                change_percent = (change / open_price * 100) if change and open_price > 0 else None
                
                # Parse timestamp
                timestamp_str = latest_data.get('date', '')
                if timestamp_str:
                    # MarketStack returns date in format like "2023-12-01T15:30:00+0000"
                    timestamp = datetime.fromisoformat(timestamp_str.replace('+0000', '+00:00'))
                else:
                    timestamp = datetime.utcnow()
                
                return UnifiedMarketData(
                    symbol=latest_data.get('symbol', ''),
                    price=current_price,
                    change=change,
                    change_percent=change_percent,
                    volume=volume,
                    high=high_price if high_price > 0 else None,
                    low=low_price if low_price > 0 else None,
                    open=open_price if open_price > 0 else None,
                    close=current_price,
                    timestamp=timestamp,
                    source_metadata={
                        "provider": "MarketStack",
                        "exchange": latest_data.get('exchange'),
                        "raw_response": raw_data
                    }
                )
            
            raise MaifaIngestionError(
                message="Unexpected response format from MarketStack",
                provider_name="MarketStack",
                is_transient=False,
                context={"raw_data": raw_data}
            )
        
        except (ValueError, TypeError, KeyError) as e:
            raise MaifaIngestionError(
                message=f"Failed to normalize MarketStack response: {str(e)}",
                provider_name="MarketStack",
                is_transient=False,
                context={"raw_data": raw_data}
            )
    
    async def _fetch_internal(self, params: StockDataRequest) -> Any:
        """Internal fetch method for MarketStack API"""
        try:
            response = await self.get(
                "intraday",
                params={
                    "access_key": self.api_key,
                    "symbols": params.symbol,
                    "interval": "1min",  # Get latest intraday data
                    "limit": 1  # Only need the latest data point
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for API errors
                if 'error' in data:
                    error_info = data['error']
                    raise MaifaIngestionError(
                        message=f"MarketStack API error: {error_info.get('message', 'Unknown error')}",
                        provider_name="MarketStack",
                        is_transient=False,
                        context={"error": error_info}
                    )
                
                return data
            
            elif response.status_code == 401:
                raise MaifaIngestionError(
                    message="Invalid API key for MarketStack",
                    provider_name="MarketStack",
                    suggested_action="Check API key configuration",
                    is_transient=False
                )
            
            elif response.status_code == 404:
                raise ProviderNotFoundError(
                    provider_name="MarketStack",
                    resource=f"Symbol {params.symbol}"
                )
            
            elif response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise ProviderRateLimitError(
                    provider_name="MarketStack",
                    retry_after=int(retry_after) if retry_after else 60
                )
            
            else:
                raise MaifaIngestionError(
                    message=f"MarketStack API error: HTTP {response.status_code}",
                    provider_name="MarketStack",
                    is_transient=response.status_code >= 500,
                    context={"status_code": response.status_code, "response": response.text}
                )
        
        except httpx.TimeoutException:
            raise ProviderTimeoutError(
                provider_name="MarketStack",
                timeout_seconds=self.timeout
            )
        
        except httpx.NetworkError as e:
            raise ProviderNetworkError(
                provider_name="MarketStack",
                network_error=str(e)
            )
        
        except MaifaIngestionError:
            raise
        
        except Exception as e:
            raise MaifaIngestionError(
                message=f"Unexpected error fetching from MarketStack: {str(e)}",
                provider_name="MarketStack",
                is_transient=True,
                context={"original_error": str(e)}
            )
