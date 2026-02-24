"""
MAIFA v3 Yahoo Finance Validator
Validates parsed Yahoo Finance data
"""

from typing import Dict, Any
import logging
from datetime import datetime

from ...interfaces import DataValidator
from ...errors import ValidationError

class YahooFinanceValidator(DataValidator):
    """Yahoo Finance data validator"""
    
    def __init__(self):
        self.logger = logging.getLogger("YahooFinanceValidator")
        
    async def validate(self, parsed_data: Dict[str, Any]) -> bool:
        """Validate parsed Yahoo Finance data"""
        try:
            # Check status
            if parsed_data.get("status") != "success":
                self.logger.warning(f"Validation failed: status is {parsed_data.get('status')}")
                return False
            
            # Check required fields
            required_fields = ["symbol", "data_points", "source"]
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
                
                required_point_fields = ["timestamp", "close", "volume"]
                for field in required_point_fields:
                    if field not in point:
                        self.logger.warning(f"Validation failed: data point {i} missing {field}")
                        return False
                
                # Check data types
                if not isinstance(point["timestamp"], (int, float)):
                    self.logger.warning(f"Validation failed: data point {i} timestamp not numeric")
                    return False
                
                if not isinstance(point["close"], (int, float)):
                    self.logger.warning(f"Validation failed: data point {i} close not numeric")
                    return False
                
                if not isinstance(point["volume"], (int, float)):
                    self.logger.warning(f"Validation failed: data point {i} volume not numeric")
                    return False
                
                # Check for valid values
                if point["close"] <= 0:
                    self.logger.warning(f"Validation failed: data point {i} close price <= 0")
                    return False
                
                if point["volume"] < 0:
                    self.logger.warning(f"Validation failed: data point {i} volume < 0")
                    return False
            
            self.logger.debug("Yahoo Finance data validation passed")
            return True
            
        except Exception as e:
            raise ValidationError(
                source="YahooFinance",
                stage="validate",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )
