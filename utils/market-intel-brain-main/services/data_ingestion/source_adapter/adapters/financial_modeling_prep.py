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


class FinancialModelingPrepAdapter(BaseSourceAdapter):
    """Financial Modeling Prep API adapter"""
    
    BASE_URL = "https://financialmodelingprep.com/api/v3"
    
    def __init__(self, redis_client, api_key: Optional[str] = None, **kwargs):
        super().__init__(
            provider_name="FinancialModelingPrep",
            base_url=self.BASE_URL,
            **kwargs
        )
        self.redis_client = redis_client
        self.api_key = api_key or os.getenv("FMP_API_KEY")
        
        if not self.api_key:
            raise MaifaIngestionError(
                message="API key is required for Financial Modeling Prep",
                provider_name="FinancialModelingPrep",
                suggested_action="Set FMP_API_KEY environment variable",
                is_transient=False
            )
    
    async def fetch(self, params: StockDataRequest) -> Dict[str, Any]:
        """Fetch stock data from Financial Modeling Prep"""
        if not await self.validate_params(params):
            raise ProviderValidationError(
                provider_name="FinancialModelingPrep",
                validation_errors={"params": "Invalid parameters"}
            )
        
        raw_data = await self._fetch_internal(params)
        normalized_data = await self.normalize_response(raw_data)
        return normalized_data.dict()
    
    async def validate_params(self, params: StockDataRequest) -> bool:
        """Validate request parameters"""
        return bool(params.symbol and len(params.symbol.strip()) > 0)
    
    async def normalize_response(self, raw_data: Any) -> UnifiedMarketData:
        """Normalize Financial Modeling Prep response to unified format"""
        try:
            if isinstance(raw_data, list) and len(raw_data) > 0:
                data = raw_data[0]  # FMP returns array with single object
                
                current_price = Decimal(str(data.get('price', 0)))
                change = Decimal(str(data.get('change', 0)))
                change_percent = Decimal(str(data.get('changesPercentage', 0)))
                volume = data.get('volume', 0)
                high_price = Decimal(str(data.get('dayHigh', 0))) if data.get('dayHigh') else None
                low_price = Decimal(str(data.get('dayLow', 0))) if data.get('dayLow') else None
                open_price = Decimal(str(data.get('open', 0))) if data.get('open') else None
                
                # Parse timestamp
                timestamp_str = data.get('timestamp')
                if timestamp_str:
                    timestamp = datetime.fromtimestamp(timestamp_str)
                else:
                    timestamp = datetime.utcnow()
                
                return UnifiedMarketData(
                    symbol=data.get('symbol', ''),
                    price=current_price,
                    change=change,
                    change_percent=change_percent,
                    volume=volume,
                    high=high_price,
                    low=low_price,
                    open=open_price,
                    close=current_price,
                    timestamp=timestamp,
                    source_metadata={
                        "provider": "FinancialModelingPrep",
                        "exchange": data.get('exchange'),
                        "market_cap": data.get('marketCap'),
                        "raw_response": raw_data
                    }
                )
            
            raise MaifaIngestionError(
                message="Unexpected response format from Financial Modeling Prep",
                provider_name="FinancialModelingPrep",
                is_transient=False,
                context={"raw_data": raw_data}
            )
        
        except (ValueError, TypeError, KeyError) as e:
            raise MaifaIngestionError(
                message=f"Failed to normalize Financial Modeling Prep response: {str(e)}",
                provider_name="FinancialModelingPrep",
                is_transient=False,
                context={"raw_data": raw_data}
            )
    
    async def _fetch_internal(self, params: StockDataRequest) -> Any:
        """Internal fetch method for Financial Modeling Prep API"""
        try:
            response = await self.get(
                f"quote-short/{params.symbol}",
                params={
                    "apikey": self.api_key
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for API errors
                if isinstance(data, dict) and 'Error Message' in data:
                    raise MaifaIngestionError(
                        message=f"Financial Modeling Prep API error: {data['Error Message']}",
                        provider_name="FinancialModelingPrep",
                        is_transient=False,
                        context={"error": data}
                    )
                
                return data
            
            elif response.status_code == 401:
                raise MaifaIngestionError(
                    message="Invalid API key for Financial Modeling Prep",
                    provider_name="FinancialModelingPrep",
                    suggested_action="Check API key configuration",
                    is_transient=False
                )
            
            elif response.status_code == 404:
                raise ProviderNotFoundError(
                    provider_name="FinancialModelingPrep",
                    resource=f"Symbol {params.symbol}"
                )
            
            elif response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise ProviderRateLimitError(
                    provider_name="FinancialModelingPrep",
                    retry_after=int(retry_after) if retry_after else 60
                )
            
            else:
                raise MaifaIngestionError(
                    message=f"Financial Modeling Prep API error: HTTP {response.status_code}",
                    provider_name="FinancialModelingPrep",
                    is_transient=response.status_code >= 500,
                    context={"status_code": response.status_code, "response": response.text}
                )
        
        except httpx.TimeoutException:
            raise ProviderTimeoutError(
                provider_name="FinancialModelingPrep",
                timeout_seconds=self.timeout
            )
        
        except httpx.NetworkError as e:
            raise ProviderNetworkError(
                provider_name="FinancialModelingPrep",
                network_error=str(e)
            )
        
        except MaifaIngestionError:
            raise
        
        except Exception as e:
            raise MaifaIngestionError(
                message=f"Unexpected error fetching from Financial Modeling Prep: {str(e)}",
                provider_name="FinancialModelingPrep",
                is_transient=True,
                context={"original_error": str(e)}
            )
