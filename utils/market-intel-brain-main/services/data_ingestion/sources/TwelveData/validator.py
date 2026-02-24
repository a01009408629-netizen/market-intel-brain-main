"""
MAIFA v3 Twelve Data Validator
Validates parsed Twelve Data
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataValidator
from ...errors import ValidationError

class TwelveDataValidator(DataValidator):
    """Twelve Data validator"""
    
    def __init__(self):
        self.logger = logging.getLogger("TwelveDataValidator")
        
    async def validate(self, parsed_data: Dict[str, Any]) -> bool:
        """Validate parsed Twelve Data"""
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
                    ohlcv_fields = ["open", "high", "low", "close", "volume"]
                    for field in ohlcv_fields:
                        if field in point:
                            value = point[field]
                            if not isinstance(value, (int, float)):
                                self.logger.warning(f"Validation failed: data point {i} {field} not numeric")
                                return False
                            
                            if field in ["open", "high", "low", "close"] and value <= 0:
                                self.logger.warning(f"Validation failed: data point {i} {field} <= 0")
                                return False
                            
                            if field == "volume" and value < 0:
                                self.logger.warning(f"Validation failed: data point {i} volume < 0")
                                return False
                    
                    # Validate OHLC relationships
                    open_price = float(point["open"])
                    high_price = float(point["high"])
                    low_price = float(point["low"])
                    close_price = float(point["close"])
                    
                    if not (low_price <= open_price <= high_price and low_price <= close_price <= high_price):
                        self.logger.warning(f"Validation failed: data point {i} OHLC relationship invalid")
                        return False
                
                # Check for quote structure
                elif "price" in point:
                    price = point["price"]
                    change = point.get("change")
                    change_percent = point.get("change_percent")
                    
                    if not isinstance(price, (int, float)):
                        self.logger.warning(f"Validation failed: data point {i} price not numeric")
                        return False
                    
                    if change is not None and not isinstance(change, (int, float)):
                        self.logger.warning(f"Validation failed: data point {i} change not numeric")
                        return False
                    
                    if change_percent is not None and not isinstance(change_percent, (int, float)):
                        self.logger.warning(f"Validation failed: data point {i} change_percent not numeric")
                        return False
                
                # Check for datetime
                elif "datetime" in point:
                    datetime_val = point["datetime"]
                    if not isinstance(datetime_val, str):
                        self.logger.warning(f"Validation failed: data point {i} datetime not string")
                        return False
            
            self.logger.debug("Twelve Data validation passed")
            return True
            
        except Exception as e:
            raise ValidationError(
                source="TwelveData",
                stage="validate",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )
