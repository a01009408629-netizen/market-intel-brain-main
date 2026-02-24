"""
MAIFA v3 Financial Modeling Prep Fetcher
Fetches raw financial data from Financial Modeling Prep API
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
import logging

from ...interfaces import DataFetcher
from ...errors import FetchError

class FinancialModelingPrepFetcher(DataFetcher):
    """Financial Modeling Prep API data fetcher"""
    
    def __init__(self):
        self.logger = logging.getLogger("FinancialModelingPrepFetcher")
        self.base_url = "https://financialmodelingprep.com/api/v3"
        self.timeout = 30.0
        self.api_key = None  # Placeholder for API key
        
    async def fetch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch financial data from Financial Modeling Prep"""
        try:
            endpoint = params.get("endpoint", "historical-price-full")
            symbol = params.get("symbol", "AAPL")
            start_date = params.get("start_date", "2020-01-01")
            end_date = params.get("end_date", "2024-01-01")
            
            url = f"{self.base_url}/{endpoint}"
            query_params = {
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
                "apikey": self.api_key or "YOUR_FINANCIAL_MODELING_PREP_API_KEY"
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
                                "source": "FinancialModelingPrep"
                            }
                        
                        return {
                            "status": "success",
                            "data": raw_data,
                            "source": "FinancialModelingPrep",
                            "endpoint": endpoint,
                            "symbol": symbol,
                            "timestamp": params.get("timestamp")
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"HTTP {response.status}",
                            "source": "FinancialModelingPrep"
                        }
                        
        except asyncio.TimeoutError:
            raise FetchError(
                source="FinancialModelingPrep",
                stage="fetch",
                error_type="TimeoutError",
                message="Request timed out",
                retryable=True
            )
        except Exception as e:
            raise FetchError(
                source="FinancialModelingPrep",
                stage="fetch",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=True
            )
    
    async def health_check(self) -> bool:
        """Check Financial Modeling Prep API health"""
        try:
            test_params = {
                "endpoint": "company-profile",
                "symbol": "AAPL"
            }
            result = await self.fetch(test_params)
            return result.get("status") == "success"
        except Exception as e:
            self.logger.error(f"Financial Modeling Prep health check failed: {e}")
            return False
