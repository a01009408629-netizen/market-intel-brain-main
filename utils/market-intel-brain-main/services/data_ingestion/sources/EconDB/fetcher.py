"""
MAIFA v3 EconDB Fetcher
Fetches raw economic data from EconDB API
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
import logging

from ...interfaces import DataFetcher
from ...errors import FetchError

class EconDBFetcher(DataFetcher):
    """EconDB API data fetcher"""
    
    def __init__(self):
        self.logger = logging.getLogger("EconDBFetcher")
        self.base_url = "https://api.econdb.com/v4"
        self.timeout = 30.0
        self.api_key = None  # Placeholder for API key
        
    async def fetch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch economic data from EconDB"""
        try:
            indicator = params.get("indicator", "GDP")
            country = params.get("country", "US")
            format_type = params.get("format", "json")
            
            url = f"{self.base_url}/{indicator}"
            query_params = {
                "country": country,
                "format": format_type,
                "apikey": self.api_key or "YOUR_ECONDB_API_KEY"
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
                                "source": "EconDB"
                            }
                        
                        return {
                            "status": "success",
                            "data": raw_data,
                            "source": "EconDB",
                            "indicator": indicator,
                            "country": country,
                            "timestamp": params.get("timestamp")
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"HTTP {response.status}",
                            "source": "EconDB"
                        }
                        
        except asyncio.TimeoutError:
            raise FetchError(
                source="EconDB",
                stage="fetch",
                error_type="TimeoutError",
                message="Request timed out",
                retryable=True
            )
        except Exception as e:
            raise FetchError(
                source="EconDB",
                stage="fetch",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=True
            )
    
    async def health_check(self) -> bool:
        """Check EconDB API health"""
        try:
            test_params = {
                "indicator": "GDP",
                "country": "US"
            }
            result = await self.fetch(test_params)
            return result.get("status") == "success"
        except Exception as e:
            self.logger.error(f"EconDB health check failed: {e}")
            return False
