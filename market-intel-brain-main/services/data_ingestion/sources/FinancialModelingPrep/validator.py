"""
MAIFA v3 Financial Modeling Prep Validator
Validates parsed Financial Modeling Prep data
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataValidator
from ...errors import ValidationError

class FinancialModelingPrepValidator(DataValidator):
    """Financial Modeling Prep data validator"""
    
    def __init__(self):
        self.logger = logging.getLogger("FinancialModelingPrepValidator")
        
    async def validate(self, parsed_data: Dict[str, Any]) -> bool:
        """Validate parsed Financial Modeling Prep data"""
        try:
            # Check status
            if parsed_data.get("status") != "success":
                self.logger.warning(f"Validation failed: status is {parsed_data.get('status')}")
                return False
            
            # Check required fields
            required_fields = ["endpoint", "symbol", "data_points", "source"]
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
                
                # Check for OHLCV structure
                if "open" in point and "high" in point and "low" in point and "close" in point:
                    # Validate OHLCV data
                    ohlcv_fields = ["open", "high", "low", "close", "volume", "adj_close", "change", "change_percent"]
                    for field in ohlcv_fields:
                        if field in point:
                            value = point[field]
                            if not isinstance(value, (int, float)):
                                self.logger.warning(f"Validation failed: data point {i} {field} not numeric")
                                return False
                            
                            if field in ["open", "high", "low", "close", "adj_close"] and value <= 0:
                                self.logger.warning(f"Validation failed: data point {i} {field} <= 0")
                                return False
                            
                            if field in ["volume", "change"] and value < 0:
                                self.logger.warning(f"Validation failed: data point {i} {field} < 0")
                                return False
                    
                    # Validate OHLC relationships
                    open_price = float(point["open"])
                    high_price = float(point["high"])
                    low_price = float(point["low"])
                    close_price = float(point["close"])
                    
                    if not (low_price <= open_price <= high_price and low_price <= close_price <= high_price):
                        self.logger.warning(f"Validation failed: data point {i} OHLC relationship invalid")
                        return False
                
                # Check for profile structure
                elif "profile" in point:
                    profile = point["profile"]
                    if not isinstance(profile, dict):
                        self.logger.warning(f"Validation failed: data point {i} profile not dict")
                        return False
                
                # Check for field-value structure
                elif "field" in point and "value" in point:
                    field = point["field"]
                    value = point["value"]
                    
                    if not isinstance(field, str):
                        self.logger.warning(f"Validation failed: data point {i} field not string")
                        return False
                    
                    # Value validation depends on field type
                    if field in ["open", "high", "low", "close", "volume"]:
                        if not isinstance(value, (int, float)):
                            self.logger.warning(f"Validation failed: data point {i} value not numeric")
                            return False
            
            self.logger.debug("Financial Modeling Prep data validation passed")
            return True
            
        except Exception as e:
            raise ValidationError(
                source="FinancialModelingPrep",
                stage="validate",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )
