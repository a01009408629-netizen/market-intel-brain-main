"""
MAIFA v3 Market Stack Parser
Parses raw Market Stack data into structured format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataParser

class MarketStackParser(DataParser):
    """Market Stack data parser"""
    
    def __init__(self):
        self.logger = logging.getLogger("MarketStackParser")
        
    async def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw Market Stack data"""
        try:
            if raw_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": raw_data.get("error", "Unknown error"),
                    "source": "MarketStack"
                }
            
            data = raw_data.get("data", {})
            
            # Market Stack typically returns different data structures
            if isinstance(data, list):
                return self._parse_list_data(data, raw_data)
            elif isinstance(data, dict):
                return self._parse_dict_data(data, raw_data)
            else:
                return {
                    "status": "no_data",
                    "message": "Unexpected data format",
                    "source": "MarketStack"
                }
                
        except Exception as e:
            self.logger.error(f"Market Stack parse error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "source": "MarketStack"
            }
    
    def _parse_list_data(self, data: List[Dict[str, Any]], raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse list format data"""
        if not data:
            return {
                "status": "no_data",
                "message": "No market data available",
                "source": "MarketStack"
            }
        
        parsed_data = {
            "status": "success",
            "endpoint": raw_data.get("endpoint"),
            "symbols": raw_data.get("symbols"),
            "data_points": data,
            "source": "MarketStack",
            "parsed_at": datetime.now().isoformat()
        }
        
        self.logger.info(f"Parsed {len(data)} market data points")
        return parsed_data
    
    def _parse_dict_data(self, data: Dict[str, Any], raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse dictionary format data"""
        if not data:
            return {
                "status": "no_data",
                "message": "No market data available",
                "source": "MarketStack"
            }
        
        # Convert dict to list format
        data_points = []
        
        # Handle different Market Stack response formats
        if "eod" in data:
            # End of day data format
            eod_data = data["eod"]
            for symbol, symbol_data in eod_data.items():
                if isinstance(symbol_data, list):
                    for item in symbol_data:
                        data_point = {
                            "symbol": symbol,
                            "date": item.get("date"),
                            "open": item.get("open"),
                            "high": item.get("high"),
                            "low": item.get("low"),
                            "close": item.get("close"),
                            "volume": item.get("volume"),
                            "adj_close": item.get("adj_close")
                        }
                        data_points.append(data_point)
        
        elif "intraday" in data:
            # Intraday data format
            intraday_data = data["intraday"]
            for symbol, symbol_data in intraday_data.items():
                if isinstance(symbol_data, list):
                    for item in symbol_data:
                        data_point = {
                            "symbol": symbol,
                            "date": item.get("date"),
                            "time": item.get("time"),
                            "open": item.get("open"),
                            "high": item.get("high"),
                            "low": item.get("low"),
                            "close": item.get("close"),
                            "volume": item.get("volume")
                        }
                        data_points.append(data_point)
        
        else:
            # Direct key-value format
            for key, value in data.items():
                if key != "request":  # Skip request metadata
                    data_point = {
                        "symbol": key,
                        "data": value
                    }
                    data_points.append(data_point)
        
        parsed_data = {
            "status": "success",
            "endpoint": raw_data.get("endpoint"),
            "symbols": raw_data.get("symbols"),
            "data_points": data_points,
            "source": "MarketStack",
            "parsed_at": datetime.now().isoformat()
        }
        
        self.logger.info(f"Parsed {len(data_points)} market data points")
        return parsed_data
