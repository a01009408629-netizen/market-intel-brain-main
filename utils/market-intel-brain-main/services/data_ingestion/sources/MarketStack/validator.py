"""
MAIFA v3 Market Stack Validator
Validates parsed Market Stack data
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataValidator
from ...errors import ValidationError

class MarketStackValidator(DataValidator):
    """Market Stack data validator"""
    
    def __init__(self):
        self.logger = logging.getLogger("MarketStackValidator")
        
    async def validate(self, parsed_data: Dict[str, Any]) -> bool:
        """Validate parsed Market Stack data"""
        try:
            # Check status
            if parsed_data.get("status") != "success":
                self.logger.warning(f"Validation failed: status is {parsed_data.get('status')}")
                return False
            
            # Check required fields
            required_fields = ["endpoint", "symbols", "data_points", "source"]
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
                
                # Check for symbol
                elif "symbol" in point:
                    symbol = point["symbol"]
                    if not isinstance(symbol, str) or len(symbol.strip()) == 0:
                        self.logger.warning(f"Validation failed: data point {i} symbol invalid")
                        return False
                
                # Check for date
                elif "date" in point:
                    date = point["date"]
                    if not isinstance(date, str):
                        self.logger.warning(f"Validation failed: data point {i} date not string")
                        return False
            
            self.logger.debug("Market Stack data validation passed")
            return True
            
        except Exception as e:
            raise ValidationError(
                source="MarketStack",
                stage="validate",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )
