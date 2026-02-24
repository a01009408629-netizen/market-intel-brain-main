"""
MAIFA v3 EuroStat Feeds Validator
Validates parsed EuroStat data
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataValidator
from ...errors import ValidationError

class EuroStatFeedsValidator(DataValidator):
    """EuroStat Feeds data validator"""
    
    def __init__(self):
        self.logger = logging.getLogger("EuroStatFeedsValidator")
        
    async def validate(self, parsed_data: Dict[str, Any]) -> bool:
        """Validate parsed EuroStat data"""
        try:
            # Check status
            if parsed_data.get("status") != "success":
                self.logger.warning(f"Validation failed: status is {parsed_data.get('status')}")
                return False
            
            # Check required fields
            required_fields = ["dataset", "indicator", "country", "data_points", "source"]
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
                
                # Check for period-value structure
                if "period" in point and "value" in point:
                    period = point["period"]
                    value = point["value"]
                    
                    if not isinstance(period, str):
                        self.logger.warning(f"Validation failed: data point {i} period not string")
                        return False
                    
                    if not isinstance(value, (int, float)):
                        self.logger.warning(f"Validation failed: data point {i} value not numeric")
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
            
            self.logger.debug("EuroStat Feeds data validation passed")
            return True
            
        except Exception as e:
            raise ValidationError(
                source="EuroStatFeeds",
                stage="validate",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )
