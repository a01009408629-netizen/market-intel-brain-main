"""
MAIFA v3 EuroStat Feeds Fetcher
Fetches raw economic data from EuroStat API
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
import logging

from ...interfaces import DataFetcher
from ...errors import FetchError

class EuroStatFeedsFetcher(DataFetcher):
    """EuroStat Feeds API data fetcher"""
    
    def __init__(self):
        self.logger = logging.getLogger("EuroStatFeedsFetcher")
        self.base_url = "https://ec.europa.eu/eurostat/api/dissemination"
        self.timeout = 30.0
        
    async def fetch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch economic data from EuroStat"""
        try:
            dataset = params.get("dataset", "namq_10_gdp")
            indicator = params.get("indicator", "GDP")
            country = params.get("country", "DE")
            time_period = params.get("time_period", "2023")
            
            url = f"{self.base_url}/statistical/json"
            query_params = {
                "dataset": dataset,
                "indicator": indicator,
                "geo": country,
                "time": time_period,
                "lang": "en"
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
                                "source": "EuroStatFeeds"
                            }
                        
                        return {
                            "status": "success",
                            "data": raw_data,
                            "source": "EuroStatFeeds",
                            "dataset": dataset,
                            "indicator": indicator,
                            "country": country,
                            "time_period": time_period,
                            "timestamp": params.get("timestamp")
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"HTTP {response.status}",
                            "source": "EuroStatFeeds"
                        }
                        
        except asyncio.TimeoutError:
            raise FetchError(
                source="EuroStatFeeds",
                stage="fetch",
                error_type="TimeoutError",
                message="Request timed out",
                retryable=True
            )
        except Exception as e:
            raise FetchError(
                source="EuroStatFeeds",
                stage="fetch",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=True
            )
    
    async def health_check(self) -> bool:
        """Check EuroStat API health"""
        try:
            test_params = {
                "dataset": "namq_10_gdp",
                "indicator": "GDP",
                "country": "DE",
                "time_period": "2023"
            }
            result = await self.fetch(test_params)
            return result.get("status") == "success"
        except Exception as e:
            self.logger.error(f"EuroStat Feeds health check failed: {e}")
            return False
