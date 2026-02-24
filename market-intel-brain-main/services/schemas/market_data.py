"""
Unified Market Data Schema with Strict Validation

This module defines the UnifiedMarketData model with strict Pydantic V2 validation.
All financial fields use Decimal with string input to prevent precision loss.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Annotated, Literal
from enum import Enum

from pydantic import (
    BaseModel, 
    Field, 
    ConfigDict,
    model_validator,
    field_validator
)

from .financial import Price, Volume, Percentage, DecimalString


class MarketDataSymbol(str, Enum):
    """Standardized market data symbols."""
    STOCK = "stock"
    FOREX = "forex"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    BOND = "bond"
    INDEX = "index"
    OPTION = "option"
    FUTURE = "future"


class TimeFrame(str, Enum):
    """Standardized time frames."""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"
    YEAR_1 = "1Y"


class DataSource(str, Enum):
    """Standardized data sources."""
    FINNHUB = "finnhub"
    YAHOO_FINANCE = "yahoo_finance"
    MARKETSTACK = "marketstack"
    FMP = "financial_modeling_prep"
    ALPHA_VANTAGE = "alpha_vantage"
    BINANCE = "binance"
    COINGECKO = "coingecko"
    NEWS_CATCHER = "news_catcher"
    ECONDB = "econdb"
    TRADING_ECONOMICS = "trading_economics"


class PricePoint(BaseModel):
    """Single price point with strict validation."""
    model_config = ConfigDict(strict=True)
    
    price: Price = Field(..., description="Price with currency")
    timestamp: datetime = Field(..., description="Timestamp of price point")
    source: DataSource = Field(..., description="Data source")
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp_not_future(cls, v: datetime) -> datetime:
        """Validate timestamp is not in the future"""
        from datetime import datetime as dt
        if v > dt.utcnow():
            raise ValueError("Timestamp cannot be in the future")
        return v


class OHLCV(BaseModel):
    """OHLCV data with strict Decimal validation."""
    model_config = ConfigDict(strict=True)
    
    open: Price = Field(..., description="Opening price")
    high: Price = Field(..., description="Highest price")
    low: Price = Field(..., description="Lowest price")
    close: Price = Field(..., description="Closing price")
    volume: Volume = Field(..., description="Trading volume")
    timestamp: datetime = Field(..., description="Candlestick timestamp")
    
    @model_validator(mode='after')
    def validate_price_relationships(self) -> 'OHLCV':
        """Validate OHLC price relationships."""
        # All prices should have the same currency
        currencies = {self.open.currency, self.high.currency, self.low.currency, self.close.currency}
        if len(currencies) > 1:
            raise ValueError("All OHLC prices must have the same currency")
        
        # High should be >= all other prices
        if self.high.value < self.open.value:
            raise ValueError("High price must be >= open price")
        if self.high.value < self.low.value:
            raise ValueError("High price must be >= low price")
        if self.high.value < self.close.value:
            raise ValueError("High price must be >= close price")
        
        # Low should be <= all other prices
        if self.low.value > self.open.value:
            raise ValueError("Low price must be <= open price")
        if self.low.value > self.high.value:
            raise ValueError("Low price must be <= high price")
        if self.low.value > self.close.value:
            raise ValueError("Low price must be <= close price")
        
        return self


class MarketTicker(BaseModel):
    """Market ticker information with strict validation."""
    model_config = ConfigDict(strict=True)
    
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol")
    name: str = Field(..., min_length=1, max_length=100, description="Full name")
    asset_type: MarketDataSymbol = Field(..., description="Asset type")
    exchange: str = Field(..., min_length=1, max_length=50, description="Exchange name")
    currency: str = Field(..., pattern=r'^[A-Z]{3}$', description="Currency code")
    current_price: Optional[Price] = Field(None, description="Current price")
    day_change: Optional[Percentage] = Field(None, description="Daily change percentage")
    day_volume: Optional[Volume] = Field(None, description="Daily volume")
    market_cap: Optional[Annotated[Decimal, DecimalString]] = Field(
        None, description="Market cap as string"
    )
    last_updated: datetime = Field(..., description="Last update timestamp")
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol_format(cls, v: str) -> str:
        """Validate symbol format."""
        if not v.isalnum() and '.' not in v and '-' not in v:
            raise ValueError("Symbol must contain only alphanumeric characters, dots, or hyphens")
        return v.upper()


class OrderBookLevel(BaseModel):
    """Single order book level."""
    model_config = ConfigDict(strict=True)
    
    price: Price = Field(..., description="Price level")
    volume: Volume = Field(..., description="Volume at this price")
    orders_count: Optional[int] = Field(None, ge=0, description="Number of orders")


class OrderBook(BaseModel):
    """Order book with strict validation."""
    model_config = ConfigDict(strict=True)
    
    symbol: str = Field(..., min_length=1, description="Trading symbol")
    exchange: str = Field(..., min_length=1, description="Exchange name")
    timestamp: datetime = Field(..., description="Order book timestamp")
    bids: List[OrderBookLevel] = Field(..., min_items=1, description="Bid levels")
    asks: List[OrderBookLevel] = Field(..., min_items=1, description="Ask levels")
    
    @model_validator(mode='after')
    def validate_order_book_structure(self) -> 'OrderBook':
        """Validate order book structure."""
        # Check that best bid is less than best ask
        if not self.bids or not self.asks:
            raise ValueError("Order book must have at least one bid and one ask")
        
        best_bid = max(self.bids, key=lambda x: x.price.value)
        best_ask = min(self.asks, key=lambda x: x.price.value)
        
        if best_bid.price.value >= best_ask.price.value:
            raise ValueError("Best bid must be less than best ask")
        
        # Validate price ordering within each side
        for i in range(len(self.bids) - 1):
            if self.bids[i].price.value < self.bids[i + 1].price.value:
                raise ValueError("Bids must be in descending price order")
        
        for i in range(len(self.asks) - 1):
            if self.asks[i].price.value > self.asks[i + 1].price.value:
                raise ValueError("Asks must be in ascending price order")
        
        return self


class Trade(BaseModel):
    """Trade information with strict validation."""
    model_config = ConfigDict(strict=True)
    
    symbol: str = Field(..., min_length=1, description="Trading symbol")
    exchange: str = Field(..., min_length=1, description="Exchange name")
    timestamp: datetime = Field(..., description="Trade timestamp")
    price: Price = Field(..., description="Trade price")
    volume: Volume = Field(..., description="Trade volume")
    trade_id: Optional[str] = Field(None, description="Unique trade identifier")
    side: Literal['buy', 'sell'] = Field(..., description="Trade side")


class UnifiedMarketData(BaseModel):
    """
    Unified market data model with strict validation.
    This is the main data contract that enforces strict typing and business rules.
    """
    model_config = ConfigDict(strict=True)
    
    # Core identification
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol")
    asset_type: MarketDataSymbol = Field(..., description="Asset type")
    exchange: str = Field(..., min_length=1, max_length=50, description="Exchange name")
    
    # Price data
    price_data: Optional[OHLCV] = Field(None, description="OHLCV price data")
    current_price: Optional[Price] = Field(None, description="Current/latest price")
    
    # Volume and market data
    volume: Optional[Volume] = Field(None, description="Current volume")
    market_cap: Optional[Annotated[Decimal, DecimalString]] = Field(
        None, description="Market cap as string"
    )
    
    # Metadata
    timestamp: datetime = Field(..., description="Data timestamp")
    source: DataSource = Field(..., description="Data source")
    timeframe: Optional[TimeFrame] = Field(None, description="Time frame for OHLCV data")
    
    # Additional data
    additional_data: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional metadata"
    )
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol format."""
        if not v.replace('.', '').replace('-', '').isalnum():
            raise ValueError("Symbol must contain only alphanumeric characters, dots, or hyphens")
        return v.upper()
    
    @model_validator(mode='after')
    def validate_data_consistency(self) -> 'UnifiedMarketData':
        """Validate data consistency across fields."""
        # If OHLCV is provided, ensure currency consistency
        if self.price_data:
            ohlcv_currency = self.price_data.close.currency
            
            if self.current_price and self.current_price.currency != ohlcv_currency:
                raise ValueError("Current price currency must match OHLCV currency")
            
            if self.volume and hasattr(self.volume, 'currency'):  # Some volume types might have currency
                pass  # Volume currency validation if needed
        
        # Validate timeframe consistency with OHLCV
        if self.timeframe and not self.price_data:
            raise ValueError("Timeframe can only be specified with OHLCV data")
        
        if self.price_data and not self.timeframe:
            raise ValueError("OHLCV data requires timeframe specification")
        
        # Validate timestamp is not too old (more than 30 days for real-time data)
        from datetime import datetime as dt, timedelta
        if self.timestamp < dt.utcnow() - timedelta(days=30):
            if self.timeframe in [TimeFrame.MINUTE_1, TimeFrame.MINUTE_5, TimeFrame.MINUTE_15]:
                raise ValueError("Real-time timeframe data cannot be older than 30 days")
        
        return self
    
    def get_price(self) -> Optional[Price]:
        """Get the best available price."""
        if self.current_price:
            return self.current_price
        elif self.price_data:
            return self.price_data.close
        return None
    
    def get_volume(self) -> Optional[Volume]:
        """Get the best available volume."""
        if self.volume:
            return self.volume
        elif self.price_data:
            return self.price_data.volume
        return None
    
    def is_real_time(self) -> bool:
        """Check if data is real-time."""
        from datetime import datetime as dt, timedelta
        return self.timestamp > dt.utcnow() - timedelta(minutes=5)


# Factory functions for easy creation
def create_market_data(
    symbol: str,
    asset_type: MarketDataSymbol,
    exchange: str,
    price_str: str,
    currency: str,
    source: DataSource,
    timestamp: datetime,
    **kwargs
) -> UnifiedMarketData:
    """Factory function to create UnifiedMarketData with string price."""
    price = Price(value=price_str, currency=currency)
    
    return UnifiedMarketData(
        symbol=symbol,
        asset_type=asset_type,
        exchange=exchange,
        current_price=price,
        source=source,
        timestamp=timestamp,
        **kwargs
    )


def create_ohlcv(
    open_str: str,
    high_str: str,
    low_str: str,
    close_str: str,
    volume_str: str,
    currency: str,
    timestamp: datetime,
    **kwargs
) -> OHLCV:
    """Factory function to create OHLCV with string inputs."""
    return OHLCV(
        open=Price(value=open_str, currency=currency),
        high=Price(value=high_str, currency=currency),
        low=Price(value=low_str, currency=currency),
        close=Price(value=close_str, currency=currency),
        volume=Volume(value=volume_str),
        timestamp=timestamp,
        **kwargs
    )
