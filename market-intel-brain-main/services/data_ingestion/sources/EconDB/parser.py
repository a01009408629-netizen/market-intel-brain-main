"""
MAIFA v3 EconDB Parser
Parses raw EconDB data into structured format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataParser

class EconDBParser(DataParser):
    """EconDB data parser"""
    
    def __init__(self):
        self.logger = logging.getLogger("EconDBParser")
        
    async def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw EconDB data"""
        try:
            if raw_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": raw_data.get("error", "Unknown error"),
                    "source": "EconDB"
                }
            
            data = raw_data.get("data", {})
            
            # EconDB typically returns data in different formats
            if isinstance(data, list):
                return self._parse_list_data(data, raw_data)
            elif isinstance(data, dict):
                return self._parse_dict_data(data, raw_data)
            else:
                return {
                    "status": "no_data",
                    "message": "Unexpected data format",
                    "source": "EconDB"
                }
                
        except Exception as e:
            self.logger.error(f"EconDB parse error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "source": "EconDB"
            }
    
    def _parse_list_data(self, data: List[Dict[str, Any]], raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse list format data"""
        if not data:
            return {
                "status": "no_data",
                "message": "No economic data available",
                "source": "EconDB"
            }
        
        parsed_data = {
            "status": "success",
            "indicator": raw_data.get("indicator"),
            "country": raw_data.get("country"),
            "data_points": data,
            "source": "EconDB",
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
                "source": "EconDB"
            }
        
        # Convert dict to list format
        data_points = []
        for key, value in data.items():
            if key != "request":  # Skip request metadata
                data_point = {
                    "period": key,
                    "value": value
                }
                data_points.append(data_point)
        
        parsed_data = {
            "status": "success",
            "indicator": raw_data.get("indicator"),
            "country": raw_data.get("country"),
            "data_points": data_points,
            "source": "EconDB",
            "parsed_at": datetime.now().isoformat()
        }
        
        self.logger.info(f"Parsed {len(data_points)} economic data points")
        return parsed_data
