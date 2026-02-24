"""
MAIFA v3 News Catcher API Fetcher
Fetches raw news data from News Catcher API
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
import logging

from ...interfaces import DataFetcher
from ...errors import FetchError

class NewsCatcherAPIFetcher(DataFetcher):
    """News Catcher API data fetcher"""
    
    def __init__(self):
        self.logger = logging.getLogger("NewsCatcherAPIFetcher")
        self.base_url = "https://api.newscatcherapi.com/v2/latest_headlines"
        self.timeout = 30.0
        self.api_key = None  # Placeholder for API key
        
    async def fetch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch news data from News Catcher API"""
        try:
            query_params = {
                "apikey": self.api_key or "YOUR_NEWSCATCHER_API_KEY",
                "lang": params.get("lang", "en"),
                "countries": params.get("countries", "US"),
                "topic": params.get("topic", "business"),
                "sources": params.get("sources", ""),
                "search_phrase": params.get("search_phrase", ""),
                "not_sources": params.get("not_sources", ""),
                "not_languages": params.get("not_languages", ""),
                "sort_by": params.get("sort_by", "relevancy"),
                "page": params.get("page", 1),
                "page_size": params.get("page_size", 100)
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
                        if raw_data.get("status") == "error":
                            return {
                                "status": "error",
                                "error": raw_data.get("message", "Unknown API error"),
                                "source": "NewsCatcherAPI"
                            }
                        
                        return {
                            "status": "success",
                            "data": raw_data,
                            "source": "NewsCatcherAPI",
                            "query_params": query_params,
                            "timestamp": params.get("timestamp")
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"HTTP {response.status}",
                            "source": "NewsCatcherAPI"
                        }
                        
        except asyncio.TimeoutError:
            raise FetchError(
                source="NewsCatcherAPI",
                stage="fetch",
                error_type="TimeoutError",
                message="Request timed out",
                retryable=True
            )
        except Exception as e:
            raise FetchError(
                source="NewsCatcherAPI",
                stage="fetch",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=True
            )
    
    async def health_check(self) -> bool:
        """Check News Catcher API health"""
        try:
            test_params = {
                "topic": "business",
                "page_size": 1
            }
            result = await self.fetch(test_params)
            return result.get("status") == "success"
        except Exception as e:
            self.logger.error(f"News Catcher API health check failed: {e}")
            return False
