"""
MAIFA v3 Market Stack Fetcher
Fetches raw financial data from Market Stack API
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
import logging

from ...interfaces import DataFetcher
from ...errors import FetchError

class MarketStackFetcher(DataFetcher):
    """Market Stack API data fetcher"""
    
    def __init__(self):
        self.logger = logging.getLogger("MarketStackFetcher")
        self.base_url = "http://api.marketstack.com/v1"
        self.timeout = 30.0
        self.api_key = None  # Placeholder for API key
        
    async def fetch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch financial data from Market Stack"""
        try:
            endpoint = params.get("endpoint", "eod")  # End of day by default
            symbols = params.get("symbols", "AAPL")
            exchange = params.get("exchange", "NASDAQ")
            country = params.get("country", "US")
            
            url = f"{self.base_url}/{endpoint}"
            query_params = {
                "access_key": self.api_key or "YOUR_MARKET_STACK_API_KEY",
                "symbols": symbols,
                "exchange": exchange,
                "country": country
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
                        if "error" in raw_data:
                            return {
                                "status": "error",
                                "error": raw_data["error"],
                                "source": "MarketStack"
                            }
                        
                        return {
                            "status": "success",
                            "data": raw_data,
                            "source": "MarketStack",
                            "endpoint": endpoint,
                            "symbols": symbols,
                            "timestamp": params.get("timestamp")
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"HTTP {response.status}",
                            "source": "MarketStack"
                        }
                        
        except asyncio.TimeoutError:
            raise FetchError(
                source="MarketStack",
                stage="fetch",
                error_type="TimeoutError",
                message="Request timed out",
                retryable=True
            )
        except Exception as e:
            raise FetchError(
                source="MarketStack",
                stage="fetch",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=True
            )
    
    async def health_check(self) -> bool:
        """Check Market Stack API health"""
        try:
            test_params = {
                "endpoint": "eod",
                "symbols": "AAPL"
            }
            result = await self.fetch(test_params)
            return result.get("status") == "success"
        except Exception as e:
            self.logger.error(f"Market Stack health check failed: {e}")
            return False
