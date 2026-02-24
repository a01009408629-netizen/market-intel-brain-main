"""
MAIFA v3 Alpha Vantage Parser
Parses raw Alpha Vantage data into structured format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataParser

class AlphaVantageParser(DataParser):
    """Alpha Vantage data parser"""
    
    def __init__(self):
        self.logger = logging.getLogger("AlphaVantageParser")
        
    async def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw Alpha Vantage data"""
        try:
            if raw_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": raw_data.get("error", "Unknown error"),
                    "source": "AlphaVantage"
                }
            
            data = raw_data.get("data", {})
            function = raw_data.get("function")
            
            # Parse based on function type
            if function == "TIME_SERIES_DAILY":
                return self._parse_time_series_daily(data)
            elif function == "GLOBAL_QUOTE":
                return self._parse_global_quote(data)
            elif function == "NEWS_SENTIMENT":
                return self._parse_news_sentiment(data)
            else:
                return self._parse_generic(data)
                
        except Exception as e:
            self.logger.error(f"Alpha Vantage parse error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "source": "AlphaVantage"
            }
    
    def _parse_time_series_daily(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse TIME_SERIES_DAILY response"""
        time_series = data.get("Time Series (Daily)", {})
        meta_data = data.get("Meta Data", {})
        
        if not time_series:
            return {
                "status": "no_data",
                "message": "No time series data available",
                "source": "AlphaVantage"
            }
        
        data_points = []
        for date_str, values in time_series.items():
            try:
                data_point = {
                    "date": date_str,
                    "timestamp": datetime.strptime(date_str, "%Y-%m-%d").timestamp(),
                    "open": float(values.get("1. open", 0)),
                    "high": float(values.get("2. high", 0)),
                    "low": float(values.get("3. low", 0)),
                    "close": float(values.get("4. close", 0)),
                    "volume": int(values.get("5. volume", 0))
                }
                data_points.append(data_point)
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Failed to parse data point {date_str}: {e}")
                continue
        
        return {
            "status": "success",
            "function": "TIME_SERIES_DAILY",
            "symbol": meta_data.get("2. Symbol"),
            "last_refreshed": meta_data.get("3. Last Refreshed"),
            "timezone": meta_data.get("5. Time Zone"),
            "data_points": data_points,
            "source": "AlphaVantage",
            "parsed_at": datetime.now().isoformat()
        }
    
    def _parse_global_quote(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse GLOBAL_QUOTE response"""
        quote_data = data.get("Global Quote", {})
        
        if not quote_data:
            return {
                "status": "no_data",
                "message": "No quote data available",
                "source": "AlphaVantage"
            }
        
        return {
            "status": "success",
            "function": "GLOBAL_QUOTE",
            "symbol": quote_data.get("01. symbol"),
            "price": float(quote_data.get("05. price", 0)),
            "change": float(quote_data.get("09. change", 0)),
            "change_percent": quote_data.get("10. change percent", "0%"),
            "timestamp": quote_data.get("07. latest trading day"),
            "data_points": [quote_data],
            "source": "AlphaVantage",
            "parsed_at": datetime.now().isoformat()
        }
    
    def _parse_news_sentiment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse NEWS_SENTIMENT response"""
        feed = data.get("feed", [])
        
        if not feed:
            return {
                "status": "no_data",
                "message": "No news sentiment data available",
                "source": "AlphaVantage"
            }
        
        return {
            "status": "success",
            "function": "NEWS_SENTIMENT",
            "data_points": feed,
            "source": "AlphaVantage",
            "parsed_at": datetime.now().isoformat()
        }
    
    def _parse_generic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse generic response"""
        return {
            "status": "success",
            "data_points": [data],
            "source": "AlphaVantage",
            "parsed_at": datetime.now().isoformat()
        }
