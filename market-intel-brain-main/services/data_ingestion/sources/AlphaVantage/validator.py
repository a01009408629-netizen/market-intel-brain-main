"""
MAIFA v3 Alpha Vantage Validator
Validates parsed Alpha Vantage data
"""

from typing import List, Dict, Any
import logging
from datetime import datetime

from ...interfaces import DataValidator
from ...errors import ValidationError

class AlphaVantageValidator(DataValidator):
    """Alpha Vantage data validator"""
    
    def __init__(self):
        self.logger = logging.getLogger("AlphaVantageValidator")
        
    async def validate(self, parsed_data: Dict[str, Any]) -> bool:
        """Validate parsed Alpha Vantage data"""
        try:
            # Check status
            if parsed_data.get("status") != "success":
                self.logger.warning(f"Validation failed: status is {parsed_data.get('status')}")
                return False
            
            # Check required fields
            required_fields = ["symbol", "data_points", "source", "function"]
            for field in required_fields:
                if field not in parsed_data:
                    self.logger.warning(f"Validation failed: missing field {field}")
                    return False
            
            # Check data points
            data_points = parsed_data.get("data_points", [])
            if not data_points:
                self.logger.warning("Validation failed: no data points")
                return False
            
            # Validate based on function type
            function = parsed_data.get("function")
            
            if function == "TIME_SERIES_DAILY":
                return self._validate_time_series(data_points)
            elif function == "GLOBAL_QUOTE":
                return self._validate_quote(data_points)
            elif function == "NEWS_SENTIMENT":
                return self._validate_news(data_points)
            else:
                return self._validate_generic(data_points)
                
        except Exception as e:
            raise ValidationError(
                source="AlphaVantage",
                stage="validate",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )
    
    def _validate_time_series(self, data_points: List[Dict[str, Any]]) -> bool:
        """Validate time series data points"""
        for i, point in enumerate(data_points):
            if not isinstance(point, dict):
                self.logger.warning(f"Validation failed: data point {i} is not a dict")
                return False
            
            required_fields = ["date", "open", "high", "low", "close", "volume"]
            for field in required_fields:
                if field not in point:
                    self.logger.warning(f"Validation failed: data point {i} missing {field}")
                    return False
            
            # Validate numeric fields
            numeric_fields = ["open", "high", "low", "close", "volume"]
            for field in numeric_fields:
                try:
                    value = float(point[field])
                    if field != "volume" and value <= 0:
                        self.logger.warning(f"Validation failed: data point {i} {field} <= 0")
                        return False
                    if field == "volume" and value < 0:
                        self.logger.warning(f"Validation failed: data point {i} volume < 0")
                        return False
                except (ValueError, TypeError):
                    self.logger.warning(f"Validation failed: data point {i} {field} not numeric")
                    return False
            
            # Validate OHLC relationships
            open_price = float(point["open"])
            high_price = float(point["high"])
            low_price = float(point["low"])
            close_price = float(point["close"])
            
            if not (low_price <= open_price <= high_price and low_price <= close_price <= high_price):
                self.logger.warning(f"Validation failed: data point {i} OHLC relationship invalid")
                return False
        
        return True
    
    def _validate_quote(self, data_points: List[Dict[str, Any]]) -> bool:
        """Validate quote data points"""
        if len(data_points) != 1:
            self.logger.warning("Validation failed: quote should have exactly one data point")
            return False
        
        point = data_points[0]
        required_fields = ["symbol", "price", "change", "change_percent"]
        for field in required_fields:
            if field not in point:
                self.logger.warning(f"Validation failed: quote missing {field}")
                return False
        
        # Validate numeric fields
        numeric_fields = ["price", "change"]
        for field in numeric_fields:
            try:
                float(point[field])
            except (ValueError, TypeError):
                self.logger.warning(f"Validation failed: quote {field} not numeric")
                return False
        
        return True
    
    def _validate_news(self, data_points: List[Dict[str, Any]]) -> bool:
        """Validate news sentiment data points"""
        for i, point in enumerate(data_points):
            if not isinstance(point, dict):
                self.logger.warning(f"Validation failed: news point {i} is not a dict")
                return False
        
        return True
    
    def _validate_generic(self, data_points: List[Dict[str, Any]]) -> bool:
        """Validate generic data points"""
        for i, point in enumerate(data_points):
            if not isinstance(point, dict):
                self.logger.warning(f"Validation failed: data point {i} is not a dict")
                return False
        
        return True
