"""
MAIFA v3 Finnhub Parser
Parses raw Finnhub data into structured format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataParser

class FinnhubParser(DataParser):
    """Finnhub data parser"""
    
    def __init__(self):
        self.logger = logging.getLogger("FinnhubParser")
        
    async def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw Finnhub data"""
        try:
            if raw_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": raw_data.get("error", "Unknown error"),
                    "source": "Finnhub"
                }
            
            data = raw_data.get("data", {})
            
            # Finnhub typically returns different data structures
            if isinstance(data, list):
                return self._parse_list_data(data, raw_data)
            elif isinstance(data, dict):
                return self._parse_dict_data(data, raw_data)
            else:
                return {
                    "status": "no_data",
                    "message": "Unexpected data format",
                    "source": "Finnhub"
                }
                
        except Exception as e:
            self.logger.error(f"Finnhub parse error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "source": "Finnhub"
            }
    
    def _parse_list_data(self, data: List[Dict[str, Any]], raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse list format data"""
        if not data:
            return {
                "status": "no_data",
                "message": "No financial data available",
                "source": "Finnhub"
            }
        
        parsed_data = {
            "status": "success",
            "endpoint": raw_data.get("endpoint"),
            "symbol": raw_data.get("symbol"),
            "data_points": data,
            "source": "Finnhub",
            "parsed_at": datetime.now().isoformat()
        }
        
        self.logger.info(f"Parsed {len(data)} financial data points")
        return parsed_data
    
    def _parse_dict_data(self, data: Dict[str, Any], raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse dictionary format data"""
        if not data:
            return {
                "status": "no_data",
                "message": "No financial data available",
                "source": "Finnhub"
            }
        
        # Convert dict to list format
        data_points = []
        
        # Handle different Finnhub response formats
        if "quote" in data:
            # Quote data format
            quote = data["quote"]
            data_point = {
                "symbol": raw_data.get("symbol"),
                "current": quote.get("current"),
                "high": quote.get("high"),
                "low": quote.get("low"),
                "open": quote.get("open"),
                "previous_close": quote.get("previous_close"),
                "change": quote.get("change"),
                "change_percent": quote.get("percent_change"),
                "timestamp": quote.get("timestamp"),
                "timezone": quote.get("timezone")
            }
            data_points.append(data_point)
        
        elif "candles" in data:
            # Candlestick data format
            candles = data["candles"]
            for candle in candles:
                data_point = {
                    "symbol": raw_data.get("symbol"),
                    "datetime": candle.get("datetime"),
                    "open": candle.get("open"),
                    "high": candle.get("high"),
                    "low": candle.get("low"),
                    "close": candle.get("close"),
                    "volume": candle.get("volume")
                }
                data_points.append(data_point)
        
        else:
            # Direct key-value format
            for key, value in data.items():
                if key != "request":  # Skip request metadata
                    data_point = {
                        "field": key,
                        "value": value
                    }
                    data_points.append(data_point)
        
        parsed_data = {
            "status": "success",
            "endpoint": raw_data.get("endpoint"),
            "symbol": raw_data.get("symbol"),
            "data_points": data_points,
            "source": "Finnhub",
            "parsed_at": datetime.now().isoformat()
        }
        
        self.logger.info(f"Parsed {len(data_points)} financial data points")
        return parsed_data
