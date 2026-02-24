"""
Custom Validators for Financial Data

This module provides custom validation functions for financial data
with strict business logic enforcement.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Union, List
import re

from pydantic import ValidationError


def validate_price_range(high_price: Decimal, low_price: Decimal) -> None:
    """
    Validate that high price is greater than or equal to low price.
    
    Args:
        high_price: Highest price value
        low_price: Lowest price value
        
    Raises:
        ValueError: If high_price < low_price
    """
    if high_price < low_price:
        raise ValueError(
            f"High price ({high_price}) must be greater than or equal to "
            f"low price ({low_price})"
        )


def validate_volume_positive(volume: Decimal) -> None:
    """
    Validate that volume is positive.
    
    Args:
        volume: Volume value
        
    Raises:
        ValueError: If volume <= 0
    """
    if volume <= 0:
        raise ValueError(f"Volume must be positive, got {volume}")


def validate_timestamp_order(start_time: datetime, end_time: datetime) -> None:
    """
    Validate that start time is before end time.
    
    Args:
        start_time: Start timestamp
        end_time: End timestamp
        
    Raises:
        ValueError: If start_time >= end_time
    """
    if start_time >= end_time:
        raise ValueError(
            f"Start time ({start_time}) must be before end time ({end_time})"
        )


def validate_currency_code(currency: str) -> str:
    """
    Validate ISO 4217 currency code format.
    
    Args:
        currency: Currency code string
        
    Returns:
        Uppercase currency code
        
    Raises:
        ValueError: If currency code is invalid
    """
    if not re.match(r'^[A-Z]{3}$', currency.upper()):
        raise ValueError(
            f"Invalid currency code '{currency}'. Must be 3 uppercase letters (ISO 4217)"
        )
    return currency.upper()


def validate_symbol_format(symbol: str) -> str:
    """
    Validate trading symbol format.
    
    Args:
        symbol: Trading symbol
        
    Returns:
        Normalized symbol
        
    Raises:
        ValueError: If symbol format is invalid
    """
    if not symbol:
        raise ValueError("Symbol cannot be empty")
    
    # Remove whitespace and convert to uppercase
    normalized = symbol.strip().upper()
    
    # Validate allowed characters
    if not re.match(r'^[A-Z0-9.\-]+$', normalized):
        raise ValueError(
            f"Invalid symbol '{symbol}'. Only alphanumeric characters, dots, and hyphens allowed"
        )
    
    if len(normalized) > 20:
        raise ValueError(f"Symbol too long: {len(normalized)} > 20 characters")
    
    return normalized


def validate_percentage_range(value: Union[str, Decimal]) -> Decimal:
    """
    Validate percentage is within valid range [-1, 1].
    
    Args:
        value: Percentage value as string or Decimal
        
    Returns:
        Decimal value
        
    Raises:
        ValueError: If percentage is out of range
    """
    try:
        decimal_value = Decimal(str(value)) if isinstance(value, str) else value
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"Invalid percentage value: {value}") from e
    
    if decimal_value < Decimal('-1') or decimal_value > Decimal('1'):
        raise ValueError(
            f"Percentage {decimal_value} out of range. Must be between -1 and 1"
        )
    
    return decimal_value


def validate_positive_decimal(value: Union[str, Decimal], field_name: str = "value") -> Decimal:
    """
    Validate that decimal value is positive.
    
    Args:
        value: Decimal value as string or Decimal
        field_name: Name of the field for error messages
        
    Returns:
        Decimal value
        
    Raises:
        ValueError: If value is not positive
    """
    try:
        decimal_value = Decimal(str(value)) if isinstance(value, str) else value
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"Invalid {field_name}: {value}") from e
    
    if decimal_value <= 0:
        raise ValueError(f"{field_name.capitalize()} must be positive, got {decimal_value}")
    
    return decimal_value


def validate_non_negative_decimal(value: Union[str, Decimal], field_name: str = "value") -> Decimal:
    """
    Validate that decimal value is non-negative.
    
    Args:
        value: Decimal value as string or Decimal
        field_name: Name of the field for error messages
        
    Returns:
        Decimal value
        
    Raises:
        ValueError: If value is negative
    """
    try:
        decimal_value = Decimal(str(value)) if isinstance(value, str) else value
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"Invalid {field_name}: {value}") from e
    
    if decimal_value < 0:
        raise ValueError(f"{field_name.capitalize()} cannot be negative, got {decimal_value}")
    
    return decimal_value


def validate_price_sequence(prices: List[Decimal]) -> None:
    """
    Validate that price sequence is logical (no negative prices).
    
    Args:
        prices: List of price values
        
    Raises:
        ValueError: If any price is invalid
    """
    for i, price in enumerate(prices):
        if price <= 0:
            raise ValueError(f"Price at index {i} must be positive, got {price}")


def validate_ohlcv_consistency(
    open_price: Decimal,
    high_price: Decimal,
    low_price: Decimal,
    close_price: Decimal
) -> None:
    """
    Validate OHLCV price consistency.
    
    Args:
        open_price: Opening price
        high_price: Highest price
        low_price: Lowest price
        close_price: Closing price
        
    Raises:
        ValueError: If OHLC relationships are invalid
    """
    # High should be >= all other prices
    if high_price < open_price:
        raise ValueError(f"High price ({high_price}) must be >= open price ({open_price})")
    if high_price < low_price:
        raise ValueError(f"High price ({high_price}) must be >= low price ({low_price})")
    if high_price < close_price:
        raise ValueError(f"High price ({high_price}) must be >= close price ({close_price})")
    
    # Low should be <= all other prices
    if low_price > open_price:
        raise ValueError(f"Low price ({low_price}) must be <= open price ({open_price})")
    if low_price > high_price:
        raise ValueError(f"Low price ({low_price}) must be <= high price ({high_price})")
    if low_price > close_price:
        raise ValueError(f"Low price ({low_price}) must be <= close price ({close_price})")


def validate_order_book_spread(best_bid: Decimal, best_ask: Decimal) -> None:
    """
    Validate order book spread is positive.
    
    Args:
        best_bid: Best bid price
        best_ask: Best ask price
        
    Raises:
        ValueError: If spread is negative or zero
    """
    if best_bid >= best_ask:
        spread = best_ask - best_bid
        raise ValueError(
            f"Invalid order book spread: best bid ({best_bid}) >= best ask ({best_ask}). "
            f"Spread: {spread}"
        )


def validate_timestamp_not_future(timestamp: datetime) -> None:
    """
    Validate timestamp is not in the future.
    
    Args:
        timestamp: Timestamp to validate
        
    Raises:
        ValueError: If timestamp is in the future
    """
    if timestamp > datetime.utcnow():
        raise ValueError(f"Timestamp {timestamp} cannot be in the future")


def validate_timestamp_not_too_old(
    timestamp: datetime, 
    max_age_days: int = 30
) -> None:
    """
    Validate timestamp is not too old.
    
    Args:
        timestamp: Timestamp to validate
        max_age_days: Maximum age in days
        
    Raises:
        ValueError: If timestamp is too old
    """
    from datetime import timedelta
    
    min_allowed = datetime.utcnow() - timedelta(days=max_age_days)
    if timestamp < min_allowed:
        raise ValueError(
            f"Timestamp {timestamp} is too old. Maximum age: {max_age_days} days"
        )


def validate_exchange_name(exchange: str) -> str:
    """
    Validate exchange name format.
    
    Args:
        exchange: Exchange name
        
    Returns:
        Normalized exchange name
        
    Raises:
        ValueError: If exchange name is invalid
    """
    if not exchange or not exchange.strip():
        raise ValueError("Exchange name cannot be empty")
    
    normalized = exchange.strip()
    
    if len(normalized) > 50:
        raise ValueError(f"Exchange name too long: {len(normalized)} > 50 characters")
    
    # Allow alphanumeric, spaces, dots, and hyphens
    if not re.match(r'^[A-Za-z0-9\s.\-]+$', normalized):
        raise ValueError(
            f"Invalid exchange name '{exchange}'. Only alphanumeric characters, spaces, dots, and hyphens allowed"
        )
    
    return normalized


def validate_market_cap(market_cap: Union[str, Decimal]) -> Decimal:
    """
    Validate market cap value.
    
    Args:
        market_cap: Market cap as string or Decimal
        
    Returns:
        Decimal value
        
    Raises:
        ValueError: If market cap is invalid
    """
    try:
        decimal_value = Decimal(str(market_cap)) if isinstance(market_cap, str) else market_cap
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"Invalid market cap: {market_cap}") from e
    
    if decimal_value < 0:
        raise ValueError(f"Market cap cannot be negative, got {decimal_value}")
    
    # Market cap should be reasonable (not too small for public companies)
    if decimal_value > 0 and decimal_value < Decimal('1000000'):  # Less than $1M
        # This is just a warning, not an error
        pass
    
    return decimal_value


# Composite validator for complex scenarios
def validate_complete_market_data(data: dict) -> dict:
    """
    Comprehensive validation for complete market data.
    
    Args:
        data: Dictionary containing market data
        
    Returns:
        Validated data dictionary
        
    Raises:
        ValidationError: If any validation fails
    """
    errors = []
    
    try:
        # Validate symbol
        if 'symbol' in data:
            data['symbol'] = validate_symbol_format(data['symbol'])
    except ValueError as e:
        errors.append(str(e))
    
    try:
        # Validate exchange
        if 'exchange' in data:
            data['exchange'] = validate_exchange_name(data['exchange'])
    except ValueError as e:
        errors.append(str(e))
    
    # Validate OHLCV if present
    ohlcv_fields = ['open', 'high', 'low', 'close']
    if all(field in data for field in ohlcv_fields):
        try:
            validate_ohlcv_consistency(
                Decimal(str(data['open'])),
                Decimal(str(data['high'])),
                Decimal(str(data['low'])),
                Decimal(str(data['close']))
            )
        except (ValueError, InvalidOperation) as e:
            errors.append(f"OHLCV validation error: {e}")
    
    # Validate volume if present
    if 'volume' in data:
        try:
            data['volume'] = validate_positive_decimal(data['volume'], 'volume')
        except ValueError as e:
            errors.append(str(e))
    
    # Validate timestamp if present
    if 'timestamp' in data:
        try:
            validate_timestamp_not_future(data['timestamp'])
        except ValueError as e:
            errors.append(str(e))
    
    if errors:
        raise ValidationError(f"Validation failed: {'; '.join(errors)}")
    
    return data


# Utility functions for data cleaning
def clean_numeric_string(value: str) -> str:
    """
    Clean numeric string by removing common formatting issues.
    
    Args:
        value: Input string
        
    Returns:
        Cleaned string suitable for Decimal conversion
    """
    if not isinstance(value, str):
        return str(value)
    
    # Remove common currency symbols and formatting
    cleaned = re.sub(r'[$,€£¥%\s]', '', value.strip())
    
    # Handle European decimal format (comma as decimal separator)
    if ',' in cleaned and '.' not in cleaned:
        cleaned = cleaned.replace(',', '.')
    elif ',' in cleaned and '.' in cleaned:
        # Assume American format: 1,234.56
        cleaned = cleaned.replace(',', '')
    
    return cleaned


def safe_decimal_conversion(value: Any) -> Decimal:
    """
    Safely convert value to Decimal with proper error handling.
    
    Args:
        value: Value to convert
        
    Returns:
        Decimal value
        
    Raises:
        ValueError: If conversion fails
    """
    if isinstance(value, Decimal):
        return value
    
    if isinstance(value, (int, float)):
        raise ValueError(
            f"Direct conversion from {type(value).__name__} not allowed. "
            "Use string input to prevent precision loss."
        )
    
    if isinstance(value, str):
        cleaned = clean_numeric_string(value)
        try:
            return Decimal(cleaned)
        except InvalidOperation as e:
            raise ValueError(f"Cannot convert '{value}' to Decimal: {e}") from e
    
    raise ValueError(f"Unsupported type for Decimal conversion: {type(value)}")
