"""
MAIFA v3 IMF Json Feeds Parser
Parses raw IMF data into structured format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataParser

class IMFJsonFeedsParser(DataParser):
    """IMF Json Feeds data parser"""
    
    def __init__(self):
        self.logger = logging.getLogger("IMFJsonFeedsParser")
        
    async def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw IMF data"""
        try:
            if raw_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": raw_data.get("error", "Unknown error"),
                    "source": "IMFJsonFeeds"
                }
            
            data = raw_data.get("data", {})
            
            # IMF typically returns different data structures
            if isinstance(data, list):
                return self._parse_list_data(data, raw_data)
            elif isinstance(data, dict):
                return self._parse_dict_data(data, raw_data)
            else:
                return {
                    "status": "no_data",
                    "message": "Unexpected data format",
                    "source": "IMFJsonFeeds"
                }
                
        except Exception as e:
            self.logger.error(f"IMF Json Feeds parse error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "source": "IMFJsonFeeds"
            }
    
    def _parse_list_data(self, data: List[Dict[str, Any]], raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse list format data"""
        if not data:
            return {
                "status": "no_data",
                "message": "No monetary data available",
                "source": "IMFJsonFeeds"
            }
        
        parsed_data = {
            "status": "success",
            "endpoint": raw_data.get("endpoint"),
            "series_code": raw_data.get("series_code"),
            "country": raw_data.get("country"),
            "data_points": data,
            "source": "IMFJsonFeeds",
            "parsed_at": datetime.now().isoformat()
        }
        
        self.logger.info(f"Parsed {len(data)} monetary data points")
        return parsed_data
    
    def _parse_dict_data(self, data: Dict[str, Any], raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse dictionary format data"""
        if not data:
            return {
                "status": "no_data",
                "message": "No monetary data available",
                "source": "IMFJsonFeeds"
            }
        
        # Convert dict to list format
        data_points = []
        
        # Handle different IMF response formats
        if "series" in data:
            # Time series data format
            series = data["series"]
            for item in series:
                data_point = {
                    "year": item.get("year"),
                    "value": item.get("value"),
                    "series_code": raw_data.get("series_code"),
                    "country": raw_data.get("country")
                }
                data_points.append(data_point)
        
        elif "value" in data:
            # Simple value format
            value = data["value"]
            data_point = {
                "value": value,
                "series_code": raw_data.get("series_code"),
                "country": raw_data.get("country")
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
            "series_code": raw_data.get("series_code"),
            "country": raw_data.get("country"),
            "data_points": data_points,
            "source": "IMFJsonFeeds",
            "parsed_at": datetime.now().isoformat()
        }
        
        self.logger.info(f"Parsed {len(data_points)} monetary data points")
        return parsed_data
