import asyncio
import logging
from typing import Any, Dict, Optional
from decimal import Decimal
from datetime import datetime
import httpx
import os
import re

from ..base_adapter_v2 import BaseSourceAdapter
from ..validators.base_schema import StockDataRequest
from ..normalization.unified_schema import UnifiedMarketData
from ..error_contract import (
    MaifaIngestionError, ProviderTimeoutError, ProviderRateLimitError,
    ProviderNetworkError, ProviderNotFoundError, ProviderValidationError
)


class YahooFinanceAdapter(BaseSourceAdapter):
    """Yahoo Finance API adapter"""
    
    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
    
    def __init__(self, redis_client, **kwargs):
        super().__init__(
            provider_name="YahooFinance",
            base_url=self.BASE_URL,
            **kwargs
        )
        self.redis_client = redis_client
    
    async def fetch(self, params: StockDataRequest) -> Dict[str, Any]:
        """Fetch stock data from Yahoo Finance"""
        if not await self.validate_params(params):
            raise ProviderValidationError(
                provider_name="YahooFinance",
                validation_errors={"params": "Invalid parameters"}
            )
        
        raw_data = await self._fetch_internal(params)
        normalized_data = await self.normalize_response(raw_data)
        return normalized_data.dict()
    
    async def validate_params(self, params: StockDataRequest) -> bool:
        """Validate request parameters"""
        if not params.symbol:
            return False
        
        # Yahoo Finance symbol validation
        symbol = params.symbol.strip().upper()
        
        # Basic symbol format validation
        if len(symbol) < 1 or len(symbol) > 10:
            return False
        
        # Check for invalid characters
        if not re.match(r'^[A-Z\.\-^]+$', symbol):
            return False
        
        return True
    
    async def normalize_response(self, raw_data: Any) -> UnifiedMarketData:
        """Normalize Yahoo Finance response to unified format"""
        try:
            if isinstance(raw_data, dict) and 'chart' in raw_data:
                chart_data = raw_data['chart']
                
                if not chart_data.get('result') or len(chart_data['result']) == 0:
                    raise ProviderNotFoundError(
                        provider_name="YahooFinance",
                        resource="Stock data"
                    )
                
                result = chart_data['result'][0]
                
                if not result.get('meta'):
                    raise MaifaIngestionError(
                        message="Missing meta data in Yahoo Finance response",
                        provider_name="YahooFinance",
                        is_transient=False
                    )
                
                meta = result['meta']
                current_price = Decimal(str(meta.get('regularMarketPrice', 0)))
                
                # Get timestamp
                timestamp = datetime.fromtimestamp(meta.get('regularMarketTime', 0))
                
                return UnifiedMarketData(
                    symbol=meta.get('symbol', ''),
                    price=current_price,
                    change=Decimal(str(meta.get('regularMarketPrice', 0))) - Decimal(str(meta.get('previousClose', 0))),
                    change_percent=Decimal(str(meta.get('regularMarketChangePercent', 0))),
                    volume=meta.get('regularMarketVolume'),
                    high=Decimal(str(meta.get('regularMarketDayHigh', 0))) if meta.get('regularMarketDayHigh') else None,
                    low=Decimal(str(meta.get('regularMarketDayLow', 0))) if meta.get('regularMarketDayLow') else None,
                    open=Decimal(str(meta.get('regularMarketOpen', 0))) if meta.get('regularMarketOpen') else None,
                    close=current_price,
                    timestamp=timestamp,
                    source_metadata={
                        "provider": "YahooFinance",
                        "currency": meta.get('currency'),
                        "market_state": meta.get('marketState'),
                        "raw_response": raw_data
                    }
                )
            
            raise MaifaIngestionError(
                message="Unexpected response format from Yahoo Finance",
                provider_name="YahooFinance",
                is_transient=False,
                context={"raw_data": raw_data}
            )
        
        except (ValueError, TypeError, KeyError) as e:
            raise MaifaIngestionError(
                message=f"Failed to normalize Yahoo Finance response: {str(e)}",
                provider_name="YahooFinance",
                is_transient=False,
                context={"raw_data": raw_data}
            )
    
    async def _fetch_internal(self, params: StockDataRequest) -> Any:
        """Internal fetch method for Yahoo Finance API"""
        try:
            # Yahoo Finance uses different endpoint format
            url = f"{self.base_url}/{params.symbol}"
            
            # Prepare headers to mimic browser
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0"
            }
            
            response = await self.client.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if data is valid
                if 'chart' in data and data['chart']['result']:
                    return data
                else:
                    raise ProviderNotFoundError(
                        provider_name="YahooFinance",
                        resource=f"Symbol {params.symbol}"
                    )
            
            elif response.status_code == 404:
                raise ProviderNotFoundError(
                    provider_name="YahooFinance",
                    resource=f"Symbol {params.symbol}"
                )
            
            elif response.status_code == 429:
                raise ProviderRateLimitError(
                    provider_name="YahooFinance",
                    retry_after=60  # Default 1 minute
                )
            
            elif response.status_code >= 500:
                raise MaifaIngestionError(
                    message=f"Yahoo Finance server error: HTTP {response.status_code}",
                    provider_name="YahooFinance",
                    is_transient=True,
                    context={"status_code": response.status_code}
                )
            
            else:
                raise MaifaIngestionError(
                    message=f"Yahoo Finance API error: HTTP {response.status_code}",
                    provider_name="YahooFinance",
                    is_transient=False,
                    context={"status_code": response.status_code, "response": response.text}
                )
        
        except httpx.TimeoutException:
            raise ProviderTimeoutError(
                provider_name="YahooFinance",
                timeout_seconds=self.timeout
            )
        
        except httpx.NetworkError as e:
            raise ProviderNetworkError(
                provider_name="YahooFinance",
                network_error=str(e)
            )
        
        except MaifaIngestionError:
            raise
        
        except Exception as e:
            raise MaifaIngestionError(
                message=f"Unexpected error fetching from Yahoo Finance: {str(e)}",
                provider_name="YahooFinance",
                is_transient=True,
                context={"original_error": str(e)}
            )
