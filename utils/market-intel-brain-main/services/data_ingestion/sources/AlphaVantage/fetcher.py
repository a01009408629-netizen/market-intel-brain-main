"""
MAIFA v3 Alpha Vantage Fetcher
Fetches raw data from Alpha Vantage API
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
import logging

from ...interfaces import DataFetcher
from ...errors import FetchError

class AlphaVantageFetcher(DataFetcher):
    """Alpha Vantage API data fetcher"""
    
    def __init__(self):
        self.logger = logging.getLogger("AlphaVantageFetcher")
        self.base_url = "https://www.alphavantage.co/query"
        self.timeout = 30.0
        self.api_key = None  # Placeholder for API key
        
    async def fetch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch financial data from Alpha Vantage"""
        try:
            function = params.get("function", "TIME_SERIES_DAILY")
            symbol = params.get("symbol", "AAPL")
            interval = params.get("interval", "daily")
            outputsize = params.get("outputsize", "compact")
            
            query_params = {
                "function": function,
                "symbol": symbol,
                "interval": interval,
                "outputsize": outputsize,
                "apikey": self.api_key or "YOUR_ALPHA_VANTAGE_API_KEY"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params=query_params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        raw_data = await response.json()
                        
                        # Check for API errors
                        if "Error Message" in raw_data:
                            return {
                                "status": "error",
                                "error": raw_data["Error Message"],
                                "source": "AlphaVantage"
                            }
                        
                        return {
                            "status": "success",
                            "data": raw_data,
                            "source": "AlphaVantage",
                            "symbol": symbol,
                            "function": function,
                            "timestamp": params.get("timestamp")
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"HTTP {response.status}",
                            "source": "AlphaVantage"
                        }
                        
        except asyncio.TimeoutError:
            raise FetchError(
                source="AlphaVantage",
                stage="fetch",
                error_type="TimeoutError",
                message="Request timed out",
                retryable=True
            )
        except Exception as e:
            raise FetchError(
                source="AlphaVantage",
                stage="fetch",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=True
            )
    
    async def health_check(self) -> bool:
        """Check Alpha Vantage API health"""
        try:
            test_params = {
                "function": "GLOBAL_QUOTE",
                "symbol": "AAPL"
            }
            result = await self.fetch(test_params)
            return result.get("status") == "success"
        except Exception as e:
            self.logger.error(f"Alpha Vantage health check failed: {e}")
            return False
