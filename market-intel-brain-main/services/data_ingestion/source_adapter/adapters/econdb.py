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


class EconDBAdapter(BaseSourceAdapter):
    """EconDB API adapter"""
    
    BASE_URL = "https://www.econdb.com/api"
    
    def __init__(self, redis_client, api_key: Optional[str] = None, **kwargs):
        super().__init__(
            provider_name="EconDB",
            base_url=self.BASE_URL,
            **kwargs
        )
        self.redis_client = redis_client
        self.api_key = api_key or os.getenv("ECONDB_API_KEY")
    
    async def fetch(self, params: EconomicDataRequest) -> Dict[str, Any]:
        """Fetch economic data from EconDB"""
        if not await self.validate_params(params):
            raise ProviderValidationError(
                provider_name="EconDB",
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
        """Normalize EconDB response to unified format"""
        try:
            if isinstance(raw_data, dict) and 'data' in raw_data:
                data_points = raw_data['data']
                
                if not data_points or len(data_points) == 0:
                    raise ProviderNotFoundError(
                        provider_name="EconDB",
                        resource="Economic data"
                    )
                
                # Get the latest data point
                latest_data = data_points[0]
                
                value = Decimal(str(latest_data.get('value', 0)))
                
                # Parse period date
                period_str = latest_data.get('date', '')
                if period_str:
                    # EconDB returns date in format like "2023-12-01"
                    period = datetime.strptime(period_str, "%Y-%m-%d")
                else:
                    period = datetime.utcnow()
                
                # Get unit from metadata
                unit = None
                if 'metadata' in raw_data:
                    unit = raw_data['metadata'].get('units')
                
                return UnifiedEconomicData(
                    indicator=raw_data.get('metadata', {}).get('description', ''),
                    country=latest_data.get('country', ''),
                    value=value,
                    unit=unit,
                    frequency=latest_data.get('frequency'),
                    period=period,
                    change=Decimal(str(latest_data.get('change', 0))) if latest_data.get('change') else None,
                    change_percent=Decimal(str(latest_data.get('change_pct', 0))) if latest_data.get('change_pct') else None,
                    previous_value=Decimal(str(latest_data.get('prev_value', 0))) if latest_data.get('prev_value') else None,
                    timestamp=datetime.utcnow(),
                    source_metadata={
                        "provider": "EconDB",
                        "dataset": raw_data.get('metadata', {}).get('dataset'),
                        "raw_response": raw_data
                    }
                )
            
            raise MaifaIngestionError(
                message="Unexpected response format from EconDB",
                provider_name="EconDB",
                is_transient=False,
                context={"raw_data": raw_data}
            )
        
        except (ValueError, TypeError, KeyError) as e:
            raise MaifaIngestionError(
                message=f"Failed to normalize EconDB response: {str(e)}",
                provider_name="EconDB",
                is_transient=False,
                context={"raw_data": raw_data}
            )
    
    async def _fetch_internal(self, params: EconomicDataRequest) -> Any:
        """Internal fetch method for EconDB API"""
        try:
            request_params = {
                "series_id": f"{params.country}.{params.indicator}",
                "format": "json"
            }
            
            # Add optional parameters
            if params.frequency:
                request_params["frequency"] = params.frequency
            
            if params.start_date:
                request_params["from"] = params.start_date.strftime("%Y-%m-%d")
            
            if params.end_date:
                request_params["to"] = params.end_date.strftime("%Y-%m-%d")
            
            # Add API key if available
            if self.api_key:
                request_params["api_key"] = self.api_key
            
            response = await self.get(
                "series",
                params=request_params
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for API errors
                if isinstance(data, dict) and 'error' in data:
                    raise MaifaIngestionError(
                        message=f"EconDB API error: {data['error']}",
                        provider_name="EconDB",
                        is_transient=False,
                        context={"error": data['error']}
                    )
                
                return data
            
            elif response.status_code == 401:
                raise MaifaIngestionError(
                    message="Invalid API key for EconDB",
                    provider_name="EconDB",
                    suggested_action="Check API key configuration",
                    is_transient=False
                )
            
            elif response.status_code == 404:
                raise ProviderNotFoundError(
                    provider_name="EconDB",
                    resource=f"Economic indicator {params.indicator} for {params.country}"
                )
            
            elif response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise ProviderRateLimitError(
                    provider_name="EconDB",
                    retry_after=int(retry_after) if retry_after else 60
                )
            
            else:
                raise MaifaIngestionError(
                    message=f"EconDB API error: HTTP {response.status_code}",
                    provider_name="EconDB",
                    is_transient=response.status_code >= 500,
                    context={"status_code": response.status_code, "response": response.text}
                )
        
        except httpx.TimeoutException:
            raise ProviderTimeoutError(
                provider_name="EconDB",
                timeout_seconds=self.timeout
            )
        
        except httpx.NetworkError as e:
            raise ProviderNetworkError(
                provider_name="EconDB",
                network_error=str(e)
            )
        
        except MaifaIngestionError:
            raise
        
        except Exception as e:
            raise MaifaIngestionError(
                message=f"Unexpected error fetching from EconDB: {str(e)}",
                provider_name="EconDB",
                is_transient=True,
                context={"original_error": str(e)}
            )
