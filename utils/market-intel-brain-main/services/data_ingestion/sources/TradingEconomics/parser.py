"""
MAIFA v3 Trading Economics Parser
Parses raw Trading Economics data into structured format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataParser

class TradingEconomicsParser(DataParser):
    """Trading Economics data parser"""
    
    def __init__(self):
        self.logger = logging.getLogger("TradingEconomicsParser")
        
    async def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw Trading Economics data"""
        try:
            if raw_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": raw_data.get("error", "Unknown error"),
                    "source": "TradingEconomics"
                }
            
            data = raw_data.get("data", {})
            
            # Trading Economics typically returns different data structures
            if isinstance(data, list):
                return self._parse_list_data(data, raw_data)
            elif isinstance(data, dict):
                return self._parse_dict_data(data, raw_data)
            else:
                return {
                    "status": "no_data",
                    "message": "Unexpected data format",
                    "source": "TradingEconomics"
                }
                
        except Exception as e:
            self.logger.error(f"Trading Economics parse error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "source": "TradingEconomics"
            }
    
    def _parse_list_data(self, data: List[Dict[str, Any]], raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse list format data"""
        if not data:
            return {
                "status": "no_data",
                "message": "No economic data available",
                "source": "TradingEconomics"
            }
        
        parsed_data = {
            "status": "success",
            "endpoint": raw_data.get("endpoint"),
            "country": raw_data.get("country"),
            "indicator": raw_data.get("indicator"),
            "data_points": data,
            "source": "TradingEconomics",
            "parsed_at": datetime.now().isoformat()
        }
        
        self.logger.info(f"Parsed {len(data)} economic data points")
        return parsed_data
    
    def _parse_dict_data(self, data: Dict[str, Any], raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse dictionary format data"""
        if not data:
            return {
                "status": "no_data",
                "message": "No economic data available",
                "source": "TradingEconomics"
            }
        
        # Convert dict to list format
        data_points = []
        
        # Handle different Trading Economics response formats
        if "data" in data:
            # Historical data format
            historical_data = data["data"]
            for item in historical_data:
                data_point = {
                    "date": item.get("Date"),
                    "value": item.get("Value"),
                    "symbol": item.get("Symbol"),
                    "frequency": item.get("Frequency")
                }
                data_points.append(data_point)
        
        elif "details" in data:
            # Country/indicator details format
            details = data["details"]
            for key, value in details.items():
                data_point = {
                    "indicator": key,
                    "value": value,
                    "country": raw_data.get("country")
                }
                data_points.append(data_point)
        
        else:
            # Direct key-value format
            for key, value in data.items():
                if key != "request":  # Skip request metadata
                    data_point = {
                        "indicator": key,
                        "value": value,
                        "country": raw_data.get("country")
                    }
                    data_points.append(data_point)
        
        parsed_data = {
            "status": "success",
            "endpoint": raw_data.get("endpoint"),
            "country": raw_data.get("country"),
            "indicator": raw_data.get("indicator"),
            "data_points": data_points,
            "source": "TradingEconomics",
            "parsed_at": datetime.now().isoformat()
        }
        
        self.logger.info(f"Parsed {len(data_points)} economic data points")
        return parsed_data
