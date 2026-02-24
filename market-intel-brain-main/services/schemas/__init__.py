"""
Strict Validation Layer - Pydantic V2 Schemas

This module provides strict data validation using Pydantic V2 with:
- Strict type validation (strict=True)
- Decimal for all financial fields (prevents float precision loss)
- Comprehensive business logic validation
- Data contracts that reject invalid data
"""

from .market_data import (
    UnifiedMarketData,
    PricePoint,
    OHLCV,
    MarketTicker,
    OrderBook,
    Trade
)
from .financial import (
    MonetaryAmount,
    Price,
    Volume,
    Percentage
)
from .validators import (
    validate_price_range,
    validate_volume_positive,
    validate_timestamp_order
)

__all__ = [
    # Market Data Models
    "UnifiedMarketData",
    "PricePoint", 
    "OHLCV",
    "MarketTicker",
    "OrderBook",
    "Trade",
    
    # Financial Types
    "MonetaryAmount",
    "Price",
    "Volume", 
    "Percentage",
    
    # Validators
    "validate_price_range",
    "validate_volume_positive",
    "validate_timestamp_order"
]
