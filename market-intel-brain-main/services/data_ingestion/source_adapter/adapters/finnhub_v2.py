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


class FinnhubAdapter(BaseSourceAdapter):
    """Finnhub API adapter"""
    
    BASE_URL = "https://finnhub.io/api/v1"
    
    def __init__(self, redis_client, api_key: Optional[str] = None, **kwargs):
        super().__init__(
            provider_name="Finnhub",
            base_url=self.BASE_URL,
            **kwargs
        )
        self.redis_client = redis_client
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY")
        
        if not self.api_key:
            raise MaifaIngestionError(
                message="API key is required for Finnhub",
                provider_name="Finnhub",
                suggested_action="Set FINNHUB_API_KEY environment variable",
                is_transient=False
            )
    
    async def fetch(self, params: StockDataRequest) -> Dict[str, Any]:
        """Fetch stock data from Finnhub"""
        if not await self.validate_params(params):
            raise ProviderValidationError(
                provider_name="Finnhub",
                validation_errors={"params": "Invalid parameters"}
            )
        
        raw_data = await self._fetch_internal(params)
        normalized_data = await self.normalize_response(raw_data)
        return normalized_data.dict()
    
    async def validate_params(self, params: StockDataRequest) -> bool:
        """Validate request parameters"""
        return bool(params.symbol and len(params.symbol.strip()) > 0)
    
    async def normalize_response(self, raw_data: Any) -> UnifiedMarketData:
        """Normalize Finnhub response to unified format"""
        try:
            if isinstance(raw_data, dict) and 'c' in raw_data:
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
                        "raw_response": raw_data
                    }
                )
            
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
            response = await self.get(
                "quote",
                params={
                    "symbol": params.symbol,
                    "token": self.api_key
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                data['symbol'] = params.symbol  # Add symbol to response
                return data
            
            elif response.status_code == 401:
                raise MaifaIngestionError(
                    message="Invalid API key for Finnhub",
                    provider_name="Finnhub",
                    suggested_action="Check API key configuration",
                    is_transient=False
                )
            
            elif response.status_code == 404:
                raise ProviderNotFoundError(
                    provider_name="Finnhub",
                    resource=f"Symbol {params.symbol}"
                )
            
            elif response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise ProviderRateLimitError(
                    provider_name="Finnhub",
                    retry_after=int(retry_after) if retry_after else None
                )
            
            else:
                raise MaifaIngestionError(
                    message=f"Finnhub API error: HTTP {response.status_code}",
                    provider_name="Finnhub",
                    is_transient=response.status_code >= 500,
                    context={"status_code": response.status_code, "response": response.text}
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
