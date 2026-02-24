"""
MAIFA v3 Finnhub Fetcher
Fetches raw financial data from Finnhub API
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
import logging

from ...interfaces import DataFetcher
from ...errors import FetchError

class FinnhubFetcher(DataFetcher):
    """Finnhub API data fetcher"""
    
    def __init__(self):
        self.logger = logging.getLogger("FinnhubFetcher")
        self.base_url = "https://finnhub.io/api/v1"
        self.timeout = 30.0
        self.api_key = None  # Placeholder for API key
        
    async def fetch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch financial data from Finnhub"""
        try:
            endpoint = params.get("endpoint", "quote")
            symbol = params.get("symbol", "AAPL")
            
            url = f"{self.base_url}/{endpoint}"
            query_params = {
                "symbol": symbol,
                "token": self.api_key or "YOUR_FINNHUB_API_KEY"
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
                                "source": "Finnhub"
                            }
                        
                        return {
                            "status": "success",
                            "data": raw_data,
                            "source": "Finnhub",
                            "endpoint": endpoint,
                            "symbol": symbol,
                            "timestamp": params.get("timestamp")
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"HTTP {response.status}",
                            "source": "Finnhub"
                        }
                        
        except asyncio.TimeoutError:
            raise FetchError(
                source="Finnhub",
                stage="fetch",
                error_type="TimeoutError",
                message="Request timed out",
                retryable=True
            )
        except Exception as e:
            raise FetchError(
                source="Finnhub",
                stage="fetch",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=True
            )
    
    async def health_check(self) -> bool:
        """Check Finnhub API health"""
        try:
            test_params = {
                "endpoint": "quote",
                "symbol": "AAPL"
            }
            result = await self.fetch(test_params)
            return result.get("status") == "success"
        except Exception as e:
            self.logger.error(f"Finnhub health check failed: {e}")
            return False
