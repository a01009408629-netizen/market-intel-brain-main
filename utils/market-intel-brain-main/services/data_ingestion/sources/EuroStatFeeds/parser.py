"""
MAIFA v3 EuroStat Feeds Parser
Parses raw EuroStat data into structured format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataParser

class EuroStatFeedsParser(DataParser):
    """EuroStat Feeds data parser"""
    
    def __init__(self):
        self.logger = logging.getLogger("EuroStatFeedsParser")
        
    async def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw EuroStat data"""
        try:
            if raw_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": raw_data.get("error", "Unknown error"),
                    "source": "EuroStatFeeds"
                }
            
            data = raw_data.get("data", {})
            
            # EuroStat typically returns different data structures
            if isinstance(data, list):
                return self._parse_list_data(data, raw_data)
            elif isinstance(data, dict):
                return self._parse_dict_data(data, raw_data)
            else:
                return {
                    "status": "no_data",
                    "message": "Unexpected data format",
                    "source": "EuroStatFeeds"
                }
                
        except Exception as e:
            self.logger.error(f"EuroStat Feeds parse error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "source": "EuroStatFeeds"
            }
    
    def _parse_list_data(self, data: List[Dict[str, Any]], raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse list format data"""
        if not data:
            return {
                "status": "no_data",
                "message": "No economic data available",
                "source": "EuroStatFeeds"
            }
        
        parsed_data = {
            "status": "success",
            "dataset": raw_data.get("dataset"),
            "indicator": raw_data.get("indicator"),
            "country": raw_data.get("country"),
            "time_period": raw_data.get("time_period"),
            "data_points": data,
            "source": "EuroStatFeeds",
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
                "source": "EuroStatFeeds"
            }
        
        # Convert dict to list format
        data_points = []
        
        # Handle different EuroStat response formats
        if "value" in data:
            # Simple value format
            value = data["value"]
            data_point = {
                "value": value,
                "dataset": raw_data.get("dataset"),
                "indicator": raw_data.get("indicator"),
                "country": raw_data.get("country"),
                "time_period": raw_data.get("time_period")
            }
            data_points.append(data_point)
        
        elif "series" in data:
            # Time series format
            series = data["series"]
            for item in series:
                data_point = {
                    "period": item.get("period"),
                    "value": item.get("value"),
                    "dataset": raw_data.get("dataset"),
                    "indicator": raw_data.get("indicator"),
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
            "dataset": raw_data.get("dataset"),
            "indicator": raw_data.get("indicator"),
            "country": raw_data.get("country"),
            "time_period": raw_data.get("time_period"),
            "data_points": data_points,
            "source": "EuroStatFeeds",
            "parsed_at": datetime.now().isoformat()
        }
        
        self.logger.info(f"Parsed {len(data_points)} economic data points")
        return parsed_data
