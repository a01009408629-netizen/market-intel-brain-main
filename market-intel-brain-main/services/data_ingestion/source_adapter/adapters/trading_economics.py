import asyncio
import logging
from typing import Any, Dict, Optional
from decimal import Decimal
from datetime import datetime
import httpx
import os

from ..base_adapter_v2 import BaseSourceAdapter
from ..validators.base_schema import EconomicDataRequest
from ..normalization.unified_schema import UnifiedEconomicData
from ..error_contract import (
    MaifaIngestionError, ProviderTimeoutError, ProviderRateLimitError,
    ProviderNetworkError, ProviderNotFoundError, ProviderValidationError
)


class TradingEconomicsAdapter(BaseSourceAdapter):
    """Trading Economics API adapter"""
    
    BASE_URL = "https://tradingeconomics.com/api"
    
    def __init__(self, redis_client, api_key: Optional[str] = None, **kwargs):
        super().__init__(
            provider_name="TradingEconomics",
            base_url=self.BASE_URL,
            **kwargs
        )
        self.redis_client = redis_client
        self.api_key = api_key or os.getenv("TRADING_ECONOMICS_API_KEY")
        
        if not self.api_key:
            raise MaifaIngestionError(
                message="API key is required for Trading Economics",
                provider_name="TradingEconomics",
                suggested_action="Set TRADING_ECONOMICS_API_KEY environment variable",
                is_transient=False
            )
    
    async def fetch(self, params: EconomicDataRequest) -> Dict[str, Any]:
        """Fetch economic data from Trading Economics"""
        if not await self.validate_params(params):
            raise ProviderValidationError(
                provider_name="TradingEconomics",
                validation_errors={"params": "Invalid parameters"}
            )
        
        raw_data = await self._fetch_internal(params)
        normalized_data = await self.normalize_response(raw_data)
        return normalized_data.dict()
    
    async def validate_params(self, params: EconomicDataRequest) -> bool:
        """Validate request parameters"""
        return bool(
            params.indicator and 
            params.country and 
            len(params.indicator.strip()) > 0 and 
            len(params.country.strip()) > 0
        )
    
    async def normalize_response(self, raw_data: Any) -> UnifiedEconomicData:
        """Normalize Trading Economics response to unified format"""
        try:
            if isinstance(raw_data, list) and len(raw_data) > 0:
                data = raw_data[0]  # Trading Economics returns array with single object
                
                value = Decimal(str(data.get('Value', 0)))
                
                # Parse period date
                period_str = data.get('DateTime', '')
                if period_str:
                    # Trading Economics returns date in format like "2023-12-01T00:00:00"
                    period = datetime.fromisoformat(period_str.replace('Z', '+00:00'))
                else:
                    period = datetime.utcnow()
                
                # Calculate change if previous value available
                change = None
                change_percent = None
                if data.get('PreviousValue'):
                    prev_value = Decimal(str(data['PreviousValue']))
                    change = value - prev_value
                    if prev_value != 0:
                        change_percent = (change / prev_value) * 100
                
                return UnifiedEconomicData(
                    indicator=data.get('Category', ''),
                    country=data.get('Country', ''),
                    value=value,
                    unit=data.get('Unit'),
                    frequency=data.get('Frequency'),
                    period=period,
                    change=change,
                    change_percent=Decimal(str(change_percent)) if change_percent else None,
                    previous_value=Decimal(str(data.get('PreviousValue', 0))) if data.get('PreviousValue') else None,
                    timestamp=datetime.utcnow(),
                    source_metadata={
                        "provider": "TradingEconomics",
                        "source": data.get('Source'),
                        "url": data.get('URL'),
                        "raw_response": raw_data
                    }
                )
            
            raise MaifaIngestionError(
                message="Unexpected response format from Trading Economics",
                provider_name="TradingEconomics",
                is_transient=False,
                context={"raw_data": raw_data}
            )
        
        except (ValueError, TypeError, KeyError) as e:
            raise MaifaIngestionError(
                message=f"Failed to normalize Trading Economics response: {str(e)}",
                provider_name="TradingEconomics",
                is_transient=False,
                context={"raw_data": raw_data}
            )
    
    async def _fetch_internal(self, params: EconomicDataRequest) -> Any:
        """Internal fetch method for Trading Economics API"""
        try:
            # Trading Economics uses different endpoint format
            endpoint = f"historical/country/{params.country}/indicator/{params.indicator}"
            
            request_params = {
                "c": "json",
                "f": "json"
            }
            
            # Add API key
            if self.api_key:
                request_params["apikey"] = self.api_key
            
            # Add optional parameters
            if params.start_date:
                request_params["d1"] = params.start_date.strftime("%Y-%m-%d")
            
            if params.end_date:
                request_params["d2"] = params.end_date.strftime("%Y-%m-%d")
            
            response = await self.get(
                endpoint,
                params=request_params
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for API errors
                if isinstance(data, dict) and 'message' in data:
                    raise MaifaIngestionError(
                        message=f"Trading Economics API error: {data['message']}",
                        provider_name="TradingEconomics",
                        is_transient=False,
                        context={"error": data}
                    )
                
                return data
            
            elif response.status_code == 401:
                raise MaifaIngestionError(
                    message="Invalid API key for Trading Economics",
                    provider_name="TradingEconomics",
                    suggested_action="Check API key configuration",
                    is_transient=False
                )
            
            elif response.status_code == 404:
                raise ProviderNotFoundError(
                    provider_name="TradingEconomics",
                    resource=f"Economic indicator {params.indicator} for {params.country}"
                )
            
            elif response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise ProviderRateLimitError(
                    provider_name="TradingEconomics",
                    retry_after=int(retry_after) if retry_after else 60
                )
            
            else:
                raise MaifaIngestionError(
                    message=f"Trading Economics API error: HTTP {response.status_code}",
                    provider_name="TradingEconomics",
                    is_transient=response.status_code >= 500,
                    context={"status_code": response.status_code, "response": response.text}
                )
        
        except httpx.TimeoutException:
            raise ProviderTimeoutError(
                provider_name="TradingEconomics",
                timeout_seconds=self.timeout
            )
        
        except httpx.NetworkError as e:
            raise ProviderNetworkError(
                provider_name="TradingEconomics",
                network_error=str(e)
            )
        
        except MaifaIngestionError:
            raise
        
        except Exception as e:
            raise MaifaIngestionError(
                message=f"Unexpected error fetching from Trading Economics: {str(e)}",
                provider_name="TradingEconomics",
                is_transient=True,
                context={"original_error": str(e)}
            )
