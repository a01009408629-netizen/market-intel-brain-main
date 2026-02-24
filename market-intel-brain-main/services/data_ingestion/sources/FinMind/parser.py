"""
MAIFA v3 FinMind Parser
Parses raw FinMind data into structured format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataParser

class FinMindParser(DataParser):
    """FinMind data parser"""
    
    def __init__(self):
        self.logger = logging.getLogger("FinMindParser")
        
    async def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw FinMind data"""
        try:
            if raw_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": raw_data.get("error", "Unknown error"),
                    "source": "FinMind"
                }
            
            data = raw_data.get("data", {})
            
            # FinMind typically returns different data structures
            if isinstance(data, list):
                return self._parse_list_data(data, raw_data)
            elif isinstance(data, dict):
                return self._parse_dict_data(data, raw_data)
            else:
                return {
                    "status": "no_data",
                    "message": "Unexpected data format",
                    "source": "FinMind"
                }
                
        except Exception as e:
            self.logger.error(f"FinMind parse error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "source": "FinMind"
            }
    
    def _parse_list_data(self, data: List[Dict[str, Any]], raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse list format data"""
        if not data:
            return {
                "status": "no_data",
                "message": "No financial data available",
                "source": "FinMind"
            }
        
        parsed_data = {
            "status": "success",
            "dataset": raw_data.get("dataset"),
            "data_id": raw_data.get("data_id"),
            "data_points": data,
            "source": "FinMind",
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
                "source": "FinMind"
            }
        
        # Convert dict to list format
        data_points = []
        
        # Handle different FinMind response formats
        if "data" in data:
            # Time series data format
            time_series_data = data["data"]
            for item in time_series_data:
                data_point = {
                    "date": item.get("date"),
                    "open": item.get("open"),
                    "high": item.get("high"),
                    "low": item.get("low"),
                    "close": item.get("close"),
                    "volume": item.get("volume"),
                    "trading_volume": item.get("trading_volume")
                }
                data_points.append(data_point)
        
        elif "info" in data:
            # Info data format
            info = data["info"]
            data_point = {
                "info": info,
                "dataset": raw_data.get("dataset"),
                "data_id": raw_data.get("data_id")
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
            "dataset": raw_data.get("dataset"),
            "data_id": raw_data.get("data_id"),
            "data_points": data_points,
            "source": "FinMind",
            "parsed_at": datetime.now().isoformat()
        }
        
        self.logger.info(f"Parsed {len(data_points)} financial data points")
        return parsed_data
