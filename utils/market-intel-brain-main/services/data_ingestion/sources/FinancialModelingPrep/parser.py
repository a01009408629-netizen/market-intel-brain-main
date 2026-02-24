"""
MAIFA v3 Financial Modeling Prep Parser
Parses raw Financial Modeling Prep data into structured format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataParser

class FinancialModelingPrepParser(DataParser):
    """Financial Modeling Prep data parser"""
    
    def __init__(self):
        self.logger = logging.getLogger("FinancialModelingPrepParser")
        
    async def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw Financial Modeling Prep data"""
        try:
            if raw_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": raw_data.get("error", "Unknown error"),
                    "source": "FinancialModelingPrep"
                }
            
            data = raw_data.get("data", {})
            
            # Financial Modeling Prep typically returns different data structures
            if isinstance(data, list):
                return self._parse_list_data(data, raw_data)
            elif isinstance(data, dict):
                return self._parse_dict_data(data, raw_data)
            else:
                return {
                    "status": "no_data",
                    "message": "Unexpected data format",
                    "source": "FinancialModelingPrep"
                }
                
        except Exception as e:
            self.logger.error(f"Financial Modeling Prep parse error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "source": "FinancialModelingPrep"
            }
    
    def _parse_list_data(self, data: List[Dict[str, Any]], raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse list format data"""
        if not data:
            return {
                "status": "no_data",
                "message": "No financial data available",
                "source": "FinancialModelingPrep"
            }
        
        parsed_data = {
            "status": "success",
            "endpoint": raw_data.get("endpoint"),
            "symbol": raw_data.get("symbol"),
            "data_points": data,
            "source": "FinancialModelingPrep",
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
                "source": "FinancialModelingPrep"
            }
        
        # Convert dict to list format
        data_points = []
        
        # Handle different Financial Modeling Prep response formats
        if "historical" in data:
            # Historical data format
            historical_data = data["historical"]
            for item in historical_data:
                data_point = {
                    "date": item.get("date"),
                    "open": item.get("open"),
                    "high": item.get("high"),
                    "low": item.get("low"),
                    "close": item.get("close"),
                    "adj_close": item.get("adj_close"),
                    "volume": item.get("volume"),
                    "unadjusted_volume": item.get("unadjusted_volume"),
                    "change": item.get("change"),
                    "change_percent": item.get("change_percent"),
                    "vwap": item.get("vwap"),
                    "label": item.get("label")
                }
                data_points.append(data_point)
        
        elif "profile" in data:
            # Profile data format
            profile = data["profile"]
            data_point = {
                "profile": profile,
                "symbol": raw_data.get("symbol")
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
            "source": "FinancialModelingPrep",
            "parsed_at": datetime.now().isoformat()
        }
        
        self.logger.info(f"Parsed {len(data_points)} financial data points")
        return parsed_data
