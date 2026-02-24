"""
MAIFA v3 Trading Economics Fetcher
Fetches raw economic data from Trading Economics API
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
import logging

from ...interfaces import DataFetcher
from ...errors import FetchError

class TradingEconomicsFetcher(DataFetcher):
    """Trading Economics API data fetcher"""
    
    def __init__(self):
        self.logger = logging.getLogger("TradingEconomicsFetcher")
        self.base_url = "https://tradingeconomics.com/api"
        self.timeout = 30.0
        self.api_key = None  # Placeholder for API key
        
    async def fetch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch economic data from Trading Economics"""
        try:
            endpoint = params.get("endpoint", "historical")
            country = params.get("country", "united states")
            indicator = params.get("indicator", "gdp")
            start_date = params.get("start_date", "2020-01-01")
            end_date = params.get("end_date", "2024-01-01")
            
            url = f"{self.base_url}/{endpoint}"
            query_params = {
                "c": country,
                "g": indicator,
                "d1": start_date,
                "d2": end_date,
                "f": "json",
                "apikey": self.api_key or "YOUR_TRADING_ECONOMICS_API_KEY"
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
                            "source": "TradingEconomics",
                            "endpoint": endpoint,
                            "country": country,
                            "indicator": indicator,
                            "timestamp": params.get("timestamp")
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"HTTP {response.status}",
                            "source": "TradingEconomics"
                        }
                        
        except asyncio.TimeoutError:
            raise FetchError(
                source="TradingEconomics",
                stage="fetch",
                error_type="TimeoutError",
                message="Request timed out",
                retryable=True
            )
        except Exception as e:
            raise FetchError(
                source="TradingEconomics",
                stage="fetch",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=True
            )
    
    async def health_check(self) -> bool:
        """Check Trading Economics API health"""
        try:
            test_params = {
                "endpoint": "country",
                "country": "united states"
            }
            result = await self.fetch(test_params)
            return result.get("status") == "success"
        except Exception as e:
            self.logger.error(f"Trading Economics health check failed: {e}")
            return False
