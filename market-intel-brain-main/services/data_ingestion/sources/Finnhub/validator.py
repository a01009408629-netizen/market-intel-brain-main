"""
MAIFA v3 Finnhub Validator
Validates parsed Finnhub data
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataValidator
from ...errors import ValidationError

class FinnhubValidator(DataValidator):
    """Finnhub data validator"""
    
    def __init__(self):
        self.logger = logging.getLogger("FinnhubValidator")
        
    async def validate(self, parsed_data: Dict[str, Any]) -> bool:
        """Validate parsed Finnhub data"""
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
                
                # Check for quote structure
                if "current" in point and "open" in point and "high" in point and "low" in point:
                    # Validate quote data
                    quote_fields = ["current", "high", "low", "open", "previous_close", "change", "change_percent"]
                    for field in quote_fields:
                        if field in point:
                            value = point[field]
                            if not isinstance(value, (int, float)):
                                self.logger.warning(f"Validation failed: data point {i} {field} not numeric")
                                return False
                            
                            if field in ["current", "high", "low", "open", "previous_close"] and value <= 0:
                                self.logger.warning(f"Validation failed: data point {i} {field} <= 0")
                                return False
                
                # Check for candlestick structure
                elif "open" in point and "high" in point and "low" in point and "close" in point:
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
                
                # Check for datetime
                elif "datetime" in point:
                    datetime_val = point["datetime"]
                    if not isinstance(datetime_val, str):
                        self.logger.warning(f"Validation failed: data point {i} datetime not string")
                        return False
            
            self.logger.debug("Finnhub data validation passed")
            return True
            
        except Exception as e:
            raise ValidationError(
                source="Finnhub",
                stage="validate",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )
