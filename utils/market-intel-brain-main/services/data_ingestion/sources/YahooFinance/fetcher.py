"""
MAIFA v3 Yahoo Finance Fetcher
Fetches raw data from Yahoo Finance API
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
import logging

from ...interfaces import DataFetcher
from ...errors import FetchError

class YahooFinanceFetcher(DataFetcher):
    """Yahoo Finance API data fetcher"""
    
    def __init__(self):
        self.logger = logging.getLogger("YahooFinanceFetcher")
        self.base_url = "https://query1.finance.yahoo.com/v8/finance/chart"
        self.timeout = 30.0
        self.api_key = None  # Yahoo Finance doesn't require API key
        
    async def fetch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch stock data from Yahoo Finance"""
        try:
            symbol = params.get("symbol", "AAPL")
            interval = params.get("interval", "1d")
            range_param = params.get("range", "1mo")
            
            url = f"{self.base_url}/{symbol}"
            query_params = {
                "interval": interval,
                "range": range_param,
                "includePrePost": "true",
                "events": "div%7Csplit"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    params=query_params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        raw_data = await response.json()
                        return {
                            "status": "success",
                            "data": raw_data,
                            "source": "YahooFinance",
                            "symbol": symbol,
                            "timestamp": params.get("timestamp")
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"HTTP {response.status}",
                            "source": "YahooFinance"
                        }
                        
        except asyncio.TimeoutError:
            raise FetchError(
                source="YahooFinance",
                stage="fetch",
                error_type="TimeoutError",
                message="Request timed out",
                retryable=True
            )
        except Exception as e:
            raise FetchError(
                source="YahooFinance",
                stage="fetch",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=True
            )
    
    async def health_check(self) -> bool:
        """Check Yahoo Finance API health"""
        try:
            test_params = {"symbol": "AAPL", "range": "1d"}
            result = await self.fetch(test_params)
            return result.get("status") == "success"
        except Exception as e:
            self.logger.error(f"Yahoo Finance health check failed: {e}")
            return False
