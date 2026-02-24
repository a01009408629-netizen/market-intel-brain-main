"""
MAIFA v3 IMF Json Feeds Fetcher
Fetches raw monetary data from IMF JSON Feeds API
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
import logging

from ...interfaces import DataFetcher
from ...errors import FetchError

class IMFJsonFeedsFetcher(DataFetcher):
    """IMF Json Feeds API data fetcher"""
    
    def __init__(self):
        self.logger = logging.getLogger("IMFJsonFeedsFetcher")
        self.base_url = "https://www.imf.org/external/datamapper"
        self.timeout = 30.0
        
    async def fetch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch monetary data from IMF"""
        try:
            endpoint = params.get("endpoint", "api/v1")
            series_code = params.get("series_code", "NGDP_RPCH")
            country = params.get("country", "US")
            start_year = params.get("start_year", "2020")
            end_year = params.get("end_year", "2024")
            
            url = f"{self.base_url}/{endpoint}/series"
            query_params = {
                "series_code": series_code,
                "country": country,
                "start_year": start_year,
                "end_year": end_year
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
                                "source": "IMFJsonFeeds"
                            }
                        
                        return {
                            "status": "success",
                            "data": raw_data,
                            "source": "IMFJsonFeeds",
                            "endpoint": endpoint,
                            "series_code": series_code,
                            "country": country,
                            "timestamp": params.get("timestamp")
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"HTTP {response.status}",
                            "source": "IMFJsonFeeds"
                        }
                        
        except asyncio.TimeoutError:
            raise FetchError(
                source="IMFJsonFeeds",
                stage="fetch",
                error_type="TimeoutError",
                message="Request timed out",
                retryable=True
            )
        except Exception as e:
            raise FetchError(
                source="IMFJsonFeeds",
                stage="fetch",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=True
            )
    
    async def health_check(self) -> bool:
        """Check IMF API health"""
        try:
            test_params = {
                "endpoint": "api/v1",
                "series_code": "NGDP_RPCH",
                "country": "US",
                "start_year": "2023",
                "end_year": "2023"
            }
            result = await self.fetch(test_params)
            return result.get("status") == "success"
        except Exception as e:
            self.logger.error(f"IMF Json Feeds health check failed: {e}")
            return False
