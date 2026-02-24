"""
MAIFA v3 Twelve Data Parser
Parses raw Twelve Data into structured format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataParser

class TwelveDataParser(DataParser):
    """Twelve Data parser"""
    
    def __init__(self):
        self.logger = logging.getLogger("TwelveDataParser")
        
    async def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw Twelve Data"""
        try:
            if raw_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": raw_data.get("error", "Unknown error"),
                    "source": "TwelveData"
                }
            
            data = raw_data.get("data", {})
            
            # Twelve Data typically returns different data structures
            if isinstance(data, list):
                return self._parse_list_data(data, raw_data)
            elif isinstance(data, dict):
                return self._parse_dict_data(data, raw_data)
            else:
                return {
                    "status": "no_data",
                    "message": "Unexpected data format",
                    "source": "TwelveData"
                }
                
        except Exception as e:
            self.logger.error(f"Twelve Data parse error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "source": "TwelveData"
            }
    
    def _parse_list_data(self, data: List[Dict[str, Any]], raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse list format data"""
        if not data:
            return {
                "status": "no_data",
                "message": "No financial data available",
                "source": "TwelveData"
            }
        
        parsed_data = {
            "status": "success",
            "endpoint": raw_data.get("endpoint"),
            "symbol": raw_data.get("symbol"),
            "data_points": data,
            "source": "TwelveData",
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
                "source": "TwelveData"
            }
        
        # Convert dict to list format
        data_points = []
        
        # Handle different Twelve Data response formats
        if "values" in data:
            # Time series data format
            time_series_data = data["values"]
            for item in time_series_data:
                data_point = {
                    "datetime": item.get("datetime"),
                    "open": item.get("open"),
                    "high": item.get("high"),
                    "low": item.get("low"),
                    "close": item.get("close"),
                    "volume": item.get("volume")
                }
                data_points.append(data_point)
        
        elif "quote" in data:
            # Quote data format
            quote = data["quote"]
            data_point = {
                "symbol": raw_data.get("symbol"),
                "price": quote.get("price"),
                "change": quote.get("change"),
                "change_percent": quote.get("percent_change"),
                "timestamp": quote.get("timestamp")
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
            "source": "TwelveData",
            "parsed_at": datetime.now().isoformat()
        }
        
        self.logger.info(f"Parsed {len(data_points)} financial data points")
        return parsed_data
