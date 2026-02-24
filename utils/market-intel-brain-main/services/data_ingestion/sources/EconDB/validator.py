"""
MAIFA v3 EconDB Validator
Validates parsed EconDB data
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataValidator
from ...errors import ValidationError

class EconDBValidator(DataValidator):
    """EconDB data validator"""
    
    def __init__(self):
        self.logger = logging.getLogger("EconDBValidator")
        
    async def validate(self, parsed_data: Dict[str, Any]) -> bool:
        """Validate parsed EconDB data"""
        try:
            # Check status
            if parsed_data.get("status") != "success":
                self.logger.warning(f"Validation failed: status is {parsed_data.get('status')}")
                return False
            
            # Check required fields
            required_fields = ["indicator", "country", "data_points", "source"]
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
                
                # Check for period/value structure
                if "period" in point and "value" in point:
                    # Validate period
                    period = point["period"]
                    if not isinstance(period, str):
                        self.logger.warning(f"Validation failed: data point {i} period not string")
                        return False
                    
                    # Validate value
                    value = point["value"]
                    if not isinstance(value, (int, float)):
                        self.logger.warning(f"Validation failed: data point {i} value not numeric")
                        return False
                
                # Check for other possible structures
                elif "date" in point and "value" in point:
                    # Date-value structure
                    date_val = point["date"]
                    value = point["value"]
                    
                    if not isinstance(date_val, str):
                        self.logger.warning(f"Validation failed: data point {i} date not string")
                        return False
                    
                    if not isinstance(value, (int, float)):
                        self.logger.warning(f"Validation failed: data point {i} value not numeric")
                        return False
                
                else:
                    self.logger.warning(f"Validation failed: data point {i} missing required structure")
                    return False
            
            self.logger.debug("EconDB data validation passed")
            return True
            
        except Exception as e:
            raise ValidationError(
                source="EconDB",
                stage="validate",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )
