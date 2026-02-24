"""
MAIFA v3 Twelve Data Fetcher
Fetches raw financial data from Twelve Data API
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
import logging

from ...interfaces import DataFetcher
from ...errors import FetchError

class TwelveDataFetcher(DataFetcher):
    """Twelve Data API data fetcher"""
    
    def __init__(self):
        self.logger = logging.getLogger("TwelveDataFetcher")
        self.base_url = "https://api.twelvedata.com/v12"
        self.timeout = 30.0
        self.api_key = None  # Placeholder for API key
        
    async def fetch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch financial data from Twelve Data"""
        try:
            endpoint = params.get("endpoint", "time_series")
            symbol = params.get("symbol", "AAPL")
            interval = params.get("interval", "1day")
            outputsize = params.get("outputsize", "500")
            
            url = f"{self.base_url}/{endpoint}"
            query_params = {
                "symbol": symbol,
                "interval": interval,
                "outputsize": outputsize,
                "apikey": self.api_key or "YOUR_TWELVE_DATA_API_KEY"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=query_params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        raw_data = await response.json()
                        
                        # Check for API errors
                        if "code" in raw_data and raw_data.get("code") != 200:
                            return {
                                "status": "error",
                                "error": raw_data.get("message", "Unknown API error"),
                                "source": "TwelveData"
                            }
                        
                        return {
                            "status": "success",
                            "data": raw_data,
                            "source": "TwelveData",
                            "endpoint": endpoint,
                            "symbol": symbol,
                            "timestamp": params.get("timestamp")
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"HTTP {response.status}",
                            "source": "TwelveData"
                        }
                        
        except asyncio.TimeoutError:
            raise FetchError(
                source="TwelveData",
                stage="fetch",
                error_type="TimeoutError",
                message="Request timed out",
                retryable=True
            )
        except Exception as e:
            raise FetchError(
                source="TwelveData",
                stage="fetch",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=True
            )
    
    async def health_check(self) -> bool:
        """Check Twelve Data API health"""
        try:
            test_params = {
                "endpoint": "time_series",
                "symbol": "AAPL",
                "outputsize": "1"
            }
            result = await self.fetch(test_params)
            return result.get("status") == "success"
        except Exception as e:
            self.logger.error(f"Twelve Data health check failed: {e}")
            return False
