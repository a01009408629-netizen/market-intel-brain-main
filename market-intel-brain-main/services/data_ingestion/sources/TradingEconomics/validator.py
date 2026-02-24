"""
MAIFA v3 Trading Economics Validator
Validates parsed Trading Economics data
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataValidator
from ...errors import ValidationError

class TradingEconomicsValidator(DataValidator):
    """Trading Economics data validator"""
    
    def __init__(self):
        self.logger = logging.getLogger("TradingEconomicsValidator")
        
    async def validate(self, parsed_data: Dict[str, Any]) -> bool:
        """Validate parsed Trading Economics data"""
        try:
            # Check status
            if parsed_data.get("status") != "success":
                self.logger.warning(f"Validation failed: status is {parsed_data.get('status')}")
                return False
            
            # Check required fields
            required_fields = ["endpoint", "country", "data_points", "source"]
            for field in required_fields:
                if field not in parsed_data:
                    self.logger.warning(f"Validation failed: missing field {field}")
                    return False
            
            # Check data points
            data_points = parsed_data.get("data_points", [])
            if not data_points:
                self.logger.warning("Validation failed: no data points")
                return False
            
            # Validate each data point
            for i, point in enumerate(data_points):
                if not isinstance(point, dict):
                    self.logger.warning(f"Validation failed: data point {i} is not a dict")
                    return False
                
                # Check for common structures
                if "date" in point and "value" in point:
                    # Date-value structure
                    date_val = point["date"]
                    value = point["value"]
                    
                    if not isinstance(date_val, str):
                        self.logger.warning(f"Validation failed: data point {i} date not string")
                        return False
                    
                    if not isinstance(value, (int, float)):
                        self.logger.warning(f"Validation failed: data point {i} value not numeric")
                        return False
                
                elif "indicator" in point and "value" in point:
                    # Indicator-value structure
                    indicator = point["indicator"]
                    value = point["value"]
                    
                    if not isinstance(indicator, str):
                        self.logger.warning(f"Validation failed: data point {i} indicator not string")
                        return False
                    
                    if not isinstance(value, (int, float)):
                        self.logger.warning(f"Validation failed: data point {i} value not numeric")
                        return False
                
                else:
                    self.logger.warning(f"Validation failed: data point {i} missing required structure")
                    return False
            
            self.logger.debug("Trading Economics data validation passed")
            return True
            
        except Exception as e:
            raise ValidationError(
                source="TradingEconomics",
                stage="validate",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )
