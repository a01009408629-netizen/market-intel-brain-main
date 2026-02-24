"""
MAIFA v3 IMF Json Feeds Validator
Validates parsed IMF data
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataValidator
from ...errors import ValidationError

class IMFJsonFeedsValidator(DataValidator):
    """IMF Json Feeds data validator"""
    
    def __init__(self):
        self.logger = logging.getLogger("IMFJsonFeedsValidator")
        
    async def validate(self, parsed_data: Dict[str, Any]) -> bool:
        """Validate parsed IMF data"""
        try:
            # Check status
            if parsed_data.get("status") != "success":
                self.logger.warning(f"Validation failed: status is {parsed_data.get('status')}")
                return False
            
            # Check required fields
            required_fields = ["endpoint", "series_code", "country", "data_points", "source"]
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
                
                # Check for year-value structure
                if "year" in point and "value" in point:
                    year = point["year"]
                    value = point["value"]
                    
                    if not isinstance(year, (int, float)):
                        self.logger.warning(f"Validation failed: data point {i} year not numeric")
                        return False
                    
                    if not isinstance(value, (int, float)):
                        self.logger.warning(f"Validation failed: data point {i} value not numeric")
                        return False
                    
                    # Validate year range
                    if isinstance(year, int) and (year < 1900 or year > 2100):
                        self.logger.warning(f"Validation failed: data point {i} year out of range")
                        return False
                
                # Check for simple value structure
                elif "value" in point:
                    value = point["value"]
                    if not isinstance(value, (int, float)):
                        self.logger.warning(f"Validation failed: data point {i} value not numeric")
                        return False
                
                # Check for field-value structure
                elif "field" in point and "value" in point:
                    field = point["field"]
                    value = point["value"]
                    
                    if not isinstance(field, str):
                        self.logger.warning(f"Validation failed: data point {i} field not string")
                        return False
                    
                    # Value validation depends on field type
                    if field in ["value"] and not isinstance(value, (int, float)):
                        self.logger.warning(f"Validation failed: data point {i} value not numeric")
                        return False
            
            self.logger.debug("IMF Json Feeds data validation passed")
            return True
            
        except Exception as e:
            raise ValidationError(
                source="IMFJsonFeeds",
                stage="validate",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )
