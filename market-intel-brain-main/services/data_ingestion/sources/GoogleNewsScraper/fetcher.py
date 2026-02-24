"""
MAIFA v3 Google News Scraper Fetcher
Fetches raw news data from Google News
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
import logging
from bs4 import BeautifulSoup
import re

from ...interfaces import DataFetcher
from ...errors import FetchError

class GoogleNewsScraperFetcher(DataFetcher):
    """Google News scraper fetcher"""
    
    def __init__(self):
        self.logger = logging.getLogger("GoogleNewsScraperFetcher")
        self.base_url = "https://news.google.com/rss/search"
        self.timeout = 30.0
        
    async def fetch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch news data from Google News"""
        try:
            query = params.get("query", "business")
            language = params.get("language", "en")
            country = params.get("country", "US")
            
            query_params = {
                "q": query,
                "hl": language,
                "gl": country,
                "ceid": country + ":" + language
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params=query_params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        raw_html = await response.text()
                        
                        # Parse RSS feed
                        soup = BeautifulSoup(raw_html, 'xml')
                        
                        return {
                            "status": "success",
                            "data": {
                                "xml_content": raw_html,
                                "soup": str(soup),
                                "query_params": query_params
                            },
                            "source": "GoogleNewsScraper",
                            "query": query,
                            "timestamp": params.get("timestamp")
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"HTTP {response.status}",
                            "source": "GoogleNewsScraper"
                        }
                        
        except asyncio.TimeoutError:
            raise FetchError(
                source="GoogleNewsScraper",
                stage="fetch",
                error_type="TimeoutError",
                message="Request timed out",
                retryable=True
            )
        except Exception as e:
            raise FetchError(
                source="GoogleNewsScraper",
                stage="fetch",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=True
            )
    
    async def health_check(self) -> bool:
        """Check Google News accessibility"""
        try:
            test_params = {
                "query": "business",
                "language": "en",
                "country": "US"
            }
            result = await self.fetch(test_params)
            return result.get("status") == "success"
        except Exception as e:
            self.logger.error(f"Google News health check failed: {e}")
            return False
