"""
MAIFA Source Adapter - Unified Schemas

This module contains Pydantic V2 models for unified data representation
across all adapters. All financial data uses Decimal for precision.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


class MarketDataSymbol(str, Enum):
    """Standardized market data symbols."""
    STOCK = "stock"
    FOREX = "forex"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    BOND = "bond"
    INDEX = "index"


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


class BaseMarketData(BaseModel):
    """Base model for all market data."""
    
    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
        "frozen": True  # Immutable once validated
    }
    
    symbol: str = Field(..., description="Trading symbol")
    source: DataSource = Field(..., description="Data source")
    timestamp: datetime = Field(..., description="Data timestamp in UTC")
    provider_metadata: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific metadata")
    
    @field_validator('timestamp')
    @classmethod
    def ensure_utc(cls, v):
        """Ensure timestamp is in UTC."""
        if v.tzinfo is None:
            return v.replace(tzinfo=datetime.timezone.utc)
        return v.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    
    @field_validator('symbol')
    @classmethod
    def normalize_symbol(cls, v):
        """Normalize symbol format."""
        return v.upper().strip()


class PriceData(BaseMarketData):
    """Model for price data."""
    
    price: Decimal = Field(..., description="Current price")
    open: Optional[Decimal] = Field(None, description="Opening price")
    high: Optional[Decimal] = Field(None, description="High price")
    low: Optional[Decimal] = Field(None, description="Low price")
    close: Optional[Decimal] = Field(None, description="Closing price")
    volume: Optional[int] = Field(None, description="Trading volume")
    change: Optional[Decimal] = Field(None, description="Price change")
    change_percent: Optional[Decimal] = Field(None, description="Percentage change")
    
    @field_validator('price', 'open', 'high', 'low', 'close', 'change', 'change_percent')
    @classmethod
    def validate_decimals(cls, v):
        """Ensure financial precision."""
        if v is not None:
            return v.quantize(Decimal('0.01'))
        return v


class ForexData(BaseMarketData):
    """Model for forex data."""
    
    from_symbol: str = Field(..., description="Base currency")
    to_symbol: str = Field(..., description="Quote currency")
    exchange_rate: Decimal = Field(..., description="Exchange rate")
    bid: Optional[Decimal] = Field(None, description="Bid price")
    ask: Optional[Decimal] = Field(None, description="Ask price")
    change: Optional[Decimal] = Field(None, description="Rate change")
    change_percent: Optional[Decimal] = Field(None, description="Percentage change")
    
    @field_validator('exchange_rate', 'bid', 'ask', 'change', 'change_percent')
    @classmethod
    def validate_decimals(cls, v):
        """Ensure financial precision."""
        if v is not None:
            return v.quantize(Decimal('0.0001'))  # Forex precision
        return v
    
    @field_validator('from_symbol', 'to_symbol')
    @classmethod
    def normalize_currency(cls, v):
        """Normalize currency codes."""
        return v.upper().strip()
    
    @model_validator(mode='after')
    def create_pair(self):
        """Create currency pair."""
        if hasattr(self, 'from_symbol') and hasattr(self, 'to_symbol'):
            self.symbol = f"{self.from_symbol}{self.to_symbol}"
        return self


class CryptoData(PriceData):
    """Model for cryptocurrency data."""
    
    market_cap: Optional[Decimal] = Field(None, description="Market capitalization")
    volume_24h: Optional[Decimal] = Field(None, description="24-hour trading volume")
    circulating_supply: Optional[Decimal] = Field(None, description="Circulating supply")
    exchange: Optional[str] = Field(None, description="Exchange name")
    
    @field_validator('market_cap', 'volume_24h', 'circulating_supply')
    @classmethod
    def validate_decimals(cls, v):
        """Ensure financial precision."""
        if v is not None:
            return v.quantize(Decimal('0.01'))
        return v


class NewsArticle(BaseModel):
    """Model for news articles."""
    
    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
        "frozen": True
    }
    
    title: str = Field(..., description="Article title")
    content: Optional[str] = Field(None, description="Article content")
    url: str = Field(..., description="Article URL")
    source: str = Field(..., description="News source")
    author: Optional[str] = Field(None, description="Article author")
    published_at: datetime = Field(..., description="Publication timestamp in UTC")
    categories: Optional[List[str]] = Field(None, description="News categories")
    tags: Optional[List[str]] = Field(None, description="News tags")
    sentiment: Optional[str] = Field(None, description="Sentiment analysis")
    language: str = Field("en", description="Article language")
    symbols_mentioned: Optional[List[str]] = Field(None, description="Stock symbols mentioned")
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Relevance score")
    
    @field_validator('published_at')
    @classmethod
    def ensure_utc(cls, v):
        """Ensure timestamp is in UTC."""
        if v.tzinfo is None:
            return v.replace(tzinfo=datetime.timezone.utc)
        return v.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    
    @field_validator('language')
    @classmethod
    def validate_language(cls, v):
        """Validate language code."""
        if len(v) != 2:
            raise ValueError("Language must be a 2-letter ISO code")
        return v.lower()
    
    @field_validator('symbols_mentioned')
    @classmethod
    def normalize_symbols(cls, v):
        """Normalize symbols."""
        if v:
            return [s.upper().strip() for s in v if s.strip()]
        return v


class EconomicIndicator(BaseModel):
    """Model for economic indicators."""
    
    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
        "frozen": True
    }
    
    indicator: str = Field(..., description="Indicator name")
    country: str = Field(..., description="Country code")
    value: Decimal = Field(..., description="Indicator value")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    frequency: Optional[str] = Field(None, description="Data frequency")
    period: date = Field(..., description="Data period")
    change: Optional[Decimal] = Field(None, description="Change from previous period")
    change_percent: Optional[Decimal] = Field(None, description="Percentage change")
    previous_value: Optional[Decimal] = Field(None, description="Previous period value")
    
    @field_validator('value', 'change', 'change_percent', 'previous_value')
    @classmethod
    def validate_decimals(cls, v):
        """Ensure financial precision."""
        if v is not None:
            return v.quantize(Decimal('0.01'))
        return v
    
    @field_validator('country')
    @classmethod
    def validate_country(cls, v):
        """Validate country code."""
        if len(v) not in [2, 3]:
            raise ValueError("Country must be a 2 or 3 letter code")
        return v.upper().strip()


class CompanyProfile(BaseModel):
    """Model for company profiles."""
    
    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
        "frozen": True
    }
    
    symbol: str = Field(..., description="Company ticker")
    name: str = Field(..., description="Company name")
    description: Optional[str] = Field(None, description="Company description")
    sector: Optional[str] = Field(None, description="Industry sector")
    industry: Optional[str] = Field(None, description="Industry classification")
    market_cap: Optional[Decimal] = Field(None, description="Market capitalization")
    employees: Optional[int] = Field(None, description="Number of employees")
    country: Optional[str] = Field(None, description="Country of incorporation")
    currency: Optional[str] = Field(None, description="Reporting currency")
    exchange: Optional[str] = Field(None, description="Primary exchange")
    website: Optional[str] = Field(None, description="Company website")
    phone: Optional[str] = Field(None, description="Company phone")
    address: Optional[str] = Field(None, description="Company address")
    ipo_date: Optional[date] = Field(None, description="IPO date")
    
    @field_validator('market_cap')
    @classmethod
    def validate_decimals(cls, v):
        """Ensure financial precision."""
        if v is not None:
            return v.quantize(Decimal('0.01'))
        return v
    
    @field_validator('symbol', 'country', 'currency')
    @classmethod
    def normalize_codes(cls, v):
        """Normalize codes."""
        return v.upper().strip() if v else v


class FinancialStatement(BaseModel):
    """Model for financial statements."""
    
    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
        "frozen": True
    }
    
    symbol: str = Field(..., description="Company ticker")
    statement_type: str = Field(..., description="Statement type")
    period: str = Field(..., description="Period type (annual, quarterly)")
    fiscal_year: int = Field(..., description="Fiscal year")
    fiscal_quarter: Optional[int] = Field(None, ge=1, le=4, description="Fiscal quarter")
    currency: str = Field(..., description="Reporting currency")
    data: Dict[str, Decimal] = Field(..., description="Financial data items")
    filing_date: Optional[date] = Field(None, description="Filing date")
    period_end_date: date = Field(..., description="Period end date")
    
    @field_validator('data')
    @classmethod
    def validate_financial_data(cls, v):
        """Ensure all financial values are Decimals."""
        validated_data = {}
        for key, value in v.items():
            if isinstance(value, Decimal):
                validated_data[key] = value.quantize(Decimal('0.01'))
            else:
                validated_data[key] = Decimal(str(value)).quantize(Decimal('0.01'))
        return validated_data
    
    @field_validator('symbol', 'currency')
    @classmethod
    def normalize_codes(cls, v):
        """Normalize codes."""
        return v.upper().strip()


class TechnicalIndicator(BaseModel):
    """Model for technical indicators."""
    
    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
        "frozen": True
    }
    
    symbol: str = Field(..., description="Trading symbol")
    indicator: str = Field(..., description="Technical indicator name")
    values: List[Dict[str, Any]] = Field(..., description="Indicator values with timestamps")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Indicator parameters")
    interval: Optional[TimeFrame] = Field(None, description="Time interval")
    
    @field_validator('symbol')
    @classmethod
    def normalize_symbol(cls, v):
        """Normalize symbol."""
        return v.upper().strip()


# Response wrapper models
class MarketDataResponse(BaseModel):
    """Wrapper for market data responses."""
    
    model_config = {
        "extra": "forbid",
        "validate_assignment": True
    }
    
    data: Union[PriceData, ForexData, CryptoData] = Field(..., description="Market data")
    request_id: Optional[str] = Field(None, description="Request identifier")
    cached: bool = Field(False, description="Whether data was retrieved from cache")
    cache_ttl: Optional[int] = Field(None, description="Cache TTL in seconds")


class NewsResponse(BaseModel):
    """Wrapper for news responses."""
    
    model_config = {
        "extra": "forbid",
        "validate_assignment": True
    }
    
    articles: List[NewsArticle] = Field(..., description="News articles")
    total_count: int = Field(..., description="Total number of articles")
    request_id: Optional[str] = Field(None, description="Request identifier")
    cached: bool = Field(False, description="Whether data was retrieved from cache")


class EconomicDataResponse(BaseModel):
    """Wrapper for economic data responses."""
    
    model_config = {
        "extra": "forbid",
        "validate_assignment": True
    }
    
    data: List[EconomicIndicator] = Field(..., description="Economic indicators")
    request_id: Optional[str] = Field(None, description="Request identifier")
    cached: bool = Field(False, description="Whether data was retrieved from cache")


class ErrorResponse(BaseModel):
    """Wrapper for error responses."""
    
    model_config = {
        "extra": "forbid",
        "validate_assignment": True
    }
    
    error: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Error type")
    adapter_name: str = Field(..., description="Adapter name")
    is_transient: bool = Field(..., description="Whether error is transient")
    retry_after: Optional[int] = Field(None, description="Retry delay in seconds")
    suggested_action: Optional[str] = Field(None, description="Suggested action")
    context: Dict[str, Any] = Field(default_factory=dict, description="Error context")
    request_id: Optional[str] = Field(None, description="Request identifier")


# Export all models
__all__ = [
    "MarketDataSymbol",
    "TimeFrame", 
    "DataSource",
    "BaseMarketData",
    "PriceData",
    "ForexData",
    "CryptoData",
    "NewsArticle",
    "EconomicIndicator",
    "CompanyProfile",
    "FinancialStatement",
    "TechnicalIndicator",
    "MarketDataResponse",
    "NewsResponse",
    "EconomicDataResponse",
    "ErrorResponse"
]
