"""
MAIFA v3 FinMind Fetcher
Fetches raw financial data from FinMind API
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
import logging

from ...interfaces import DataFetcher
from ...errors import FetchError

class FinMindFetcher(DataFetcher):
    """FinMind API data fetcher"""
    
    def __init__(self):
        self.logger = logging.getLogger("FinMindFetcher")
        self.base_url = "https://api.finmind.tw/v4"
        self.timeout = 30.0
        self.api_key = None  # Placeholder for API key
        
    async def fetch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch financial data from FinMind"""
        try:
            dataset = params.get("dataset", "TaiwanStockPrice")
            data_id = params.get("data_id", "2330")  # TSMC by default
            start_date = params.get("start_date", "2020-01-01")
            end_date = params.get("end_date", "2024-01-01")
            
            url = f"{self.base_url}/data"
            query_params = {
                "dataset": dataset,
                "data_id": data_id,
                "start_date": start_date,
                "end_date": end_date,
                "token": self.api_key or "YOUR_FINMIND_API_KEY"
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
                        if "msg" in raw_data and raw_data.get("msg") != "OK":
                            return {
                                "status": "error",
                                "error": raw_data.get("msg", "Unknown API error"),
                                "source": "FinMind"
                            }
                        
                        return {
                            "status": "success",
                            "data": raw_data,
                            "source": "FinMind",
                            "dataset": dataset,
                            "data_id": data_id,
                            "timestamp": params.get("timestamp")
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"HTTP {response.status}",
                            "source": "FinMind"
                        }
                        
        except asyncio.TimeoutError:
            raise FetchError(
                source="FinMind",
                stage="fetch",
                error_type="TimeoutError",
                message="Request timed out",
                retryable=True
            )
        except Exception as e:
            raise FetchError(
                source="FinMind",
                stage="fetch",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=True
            )
    
    async def health_check(self) -> bool:
        """Check FinMind API health"""
        try:
            test_params = {
                "dataset": "TaiwanStockPrice",
                "data_id": "2330"
            }
            result = await self.fetch(test_params)
            return result.get("status") == "success"
        except Exception as e:
            self.logger.error(f"FinMind health check failed: {e}")
            return False
