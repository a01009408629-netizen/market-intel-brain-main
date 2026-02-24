from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
import re


class ValidationContractError(Exception):
    """Custom validation error for provider parameters"""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.field:
            return f"Validation error in field '{self.field}': {self.message}"
        return f"Validation error: {self.message}"


class TimeFrame(str, Enum):
    """Standard time frames for market data"""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"


class BaseProviderParams(BaseModel):
    """Base parameters for all providers"""
    
    class Config:
        extra = 'forbid'
        str_strip_whitespace = True
        validate_assignment = True


class FinnhubParams(BaseProviderParams):
    """Finnhub API parameters"""
    
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v):
        if not v or not v.strip():
            raise ValueError("Symbol cannot be empty")
        
        symbol = v.strip().upper()
        
        # Basic symbol validation
        if not re.match(r'^[A-Z\.\-^]+$', symbol):
            raise ValueError("Symbol contains invalid characters")
        
        return symbol


class YahooFinanceParams(BaseProviderParams):
    """Yahoo Finance API parameters"""
    
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    interval: Optional[str] = Field("1m", description="Time interval")
    range: Optional[str] = Field("1d", description="Date range")
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v):
        if not v or not v.strip():
            raise ValueError("Symbol cannot be empty")
        
        symbol = v.strip().upper()
        
        # Yahoo Finance symbol validation
        if len(symbol) < 1 or len(symbol) > 10:
            raise ValueError("Symbol must be 1-10 characters")
        
        if not re.match(r'^[A-Z\.\-^]+$', symbol):
            raise ValueError("Symbol contains invalid characters")
        
        return symbol
    
    @field_validator('interval')
    @classmethod
    def validate_interval(cls, v):
        if v is None:
            return v
        
        valid_intervals = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]
        if v not in valid_intervals:
            raise ValueError(f"Interval must be one of: {', '.join(valid_intervals)}")
        
        return v
    
    @field_validator('range')
    @classmethod
    def validate_range(cls, v):
        if v is None:
            return v
        
        valid_ranges = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
        if v not in valid_ranges:
            raise ValueError(f"Range must be one of: {', '.join(valid_ranges)}")
        
        return v


class MarketStackParams(BaseProviderParams):
    """MarketStack API parameters"""
    
    symbols: str = Field(..., min_length=1, description="Comma-separated stock symbols")
    interval: Optional[str] = Field("1min", description="Time interval")
    
    @field_validator('symbols')
    @classmethod
    def validate_symbols(cls, v):
        if not v or not v.strip():
            raise ValueError("Symbols cannot be empty")
        
        symbols = [s.strip().upper() for s in v.split(',') if s.strip()]
        
        if len(symbols) == 0:
            raise ValueError("At least one symbol is required")
        
        if len(symbols) > 100:  # MarketStack limit
            raise ValueError("Maximum 100 symbols allowed per request")
        
        # Validate each symbol
        for symbol in symbols:
            if not re.match(r'^[A-Z\.\-]+$', symbol):
                raise ValueError(f"Invalid symbol format: {symbol}")
        
        return ','.join(symbols)
    
    @field_validator('interval')
    @classmethod
    def validate_interval(cls, v):
        if v is None:
            return v
        
        valid_intervals = ["1min", "5min", "15min", "30min", "1hour", "1day"]
        if v not in valid_intervals:
            raise ValueError(f"Interval must be one of: {', '.join(valid_intervals)}")
        
        return v


class FinancialModelingPrepParams(BaseProviderParams):
    """Financial Modeling Prep API parameters"""
    
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v):
        if not v or not v.strip():
            raise ValueError("Symbol cannot be empty")
        
        symbol = v.strip().upper()
        
        if len(symbol) < 1 or len(symbol) > 10:
            raise ValueError("Symbol must be 1-10 characters")
        
        if not re.match(r'^[A-Z\.\-^]+$', symbol):
            raise ValueError("Symbol contains invalid characters")
        
        return symbol


class NewsCatcherParams(BaseProviderParams):
    """NewsCatcher API parameters"""
    
    query: Optional[str] = Field(None, max_length=1000, description="Search query")
    sources: Optional[List[str]] = Field(None, max_items=100, description="News sources")
    categories: Optional[List[str]] = Field(None, description="News categories")
    language: str = Field("en", min_length=2, max_length=2, description="Language code")
    limit: int = Field(50, ge=1, le=1000, description="Number of articles")
    from_date: Optional[datetime] = Field(None, description="Start date")
    to_date: Optional[datetime] = Field(None, description="End date")
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError("Query cannot be empty string")
        return v.strip() if v else v
    
    @field_validator('sources')
    @classmethod
    def validate_sources(cls, v):
        if v is None:
            return v
        
        if len(v) == 0:
            raise ValueError("At least one source must be specified")
        
        if len(v) > 100:
            raise ValueError("Maximum 100 sources allowed")
        
        # Validate source format
        for source in v:
            if not isinstance(source, str) or len(source.strip()) == 0:
                raise ValueError("All sources must be non-empty strings")
        
        return [s.strip() for s in v]
    
    @field_validator('categories')
    @classmethod
    def validate_categories(cls, v):
        if v is None:
            return v
        
        if len(v) == 0:
            raise ValueError("At least one category must be specified")
        
        # Validate category format
        for category in v:
            if not isinstance(category, str) or len(category.strip()) == 0:
                raise ValueError("All categories must be non-empty strings")
        
        return [c.strip() for c in v]
    
    @field_validator('language')
    @classmethod
    def validate_language(cls, v):
        if len(v) != 2:
            raise ValueError("Language must be a 2-letter ISO code")
        
        return v.lower()
    
    @field_validator('from_date', 'to_date')
    @classmethod
    def validate_date_range(cls, v, info):
        if v is None:
            return v
        
        # Ensure datetime is timezone-aware or assume UTC
        if v.tzinfo is None:
            v = v.replace(tzinfo=datetime.timezone.utc)
        
        return v
    
    @model_validator(mode='after')
    @classmethod
    def validate_date_order(cls, values):
        from_date = values.get('from_date')
        to_date = values.get('to_date')
        
        if from_date and to_date and from_date >= to_date:
            raise ValueError("from_date must be before to_date")
        
        return values


class EconDBParams(BaseProviderParams):
    """EconDB API parameters"""
    
    indicator: str = Field(..., min_length=1, description="Economic indicator")
    country: str = Field(..., min_length=2, max_length=3, description="Country code")
    frequency: Optional[str] = Field(None, description="Data frequency")
    start_date: Optional[date] = Field(None, description="Start date")
    end_date: Optional[date] = Field(None, description="End date")
    
    @field_validator('indicator')
    @classmethod
    def validate_indicator(cls, v):
        if not v or not v.strip():
            raise ValueError("Indicator cannot be empty")
        
        indicator = v.strip().title()
        
        # Basic validation for common indicators
        valid_indicators = [
            "GDP", "Inflation Rate", "Unemployment Rate", "Interest Rate",
            "Exchange Rate", "Trade Balance", "Government Debt"
        ]
        
        # Allow custom indicators but validate format
        if not re.match(r'^[A-Za-z\s\-]+$', indicator):
            raise ValueError("Indicator contains invalid characters")
        
        return indicator
    
    @field_validator('country')
    @classmethod
    def validate_country(cls, v):
        if not v or not v.strip():
            raise ValueError("Country cannot be empty")
        
        country = v.strip().upper()
        
        if len(country) not in [2, 3]:
            raise ValueError("Country must be 2 or 3 letter code")
        
        if not re.match(r'^[A-Z]{2,3}$', country):
            raise ValueError("Country must contain only letters")
        
        return country
    
    @field_validator('frequency')
    @classmethod
    def validate_frequency(cls, v):
        if v is None:
            return v
        
        valid_frequencies = ["daily", "weekly", "monthly", "quarterly", "annual"]
        if v.lower() not in valid_frequencies:
            raise ValueError(f"Frequency must be one of: {', '.join(valid_frequencies)}")
        
        return v.lower()
    
    @model_validator(mode='after')
    @classmethod
    def validate_date_range(cls, values):
        start_date = values.get('start_date')
        end_date = values.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise ValueError("start_date must be before end_date")
        
        return values


class TradingEconomicsParams(BaseProviderParams):
    """Trading Economics API parameters"""
    
    indicator: str = Field(..., min_length=1, description="Economic indicator")
    country: str = Field(..., min_length=2, max_length=3, description="Country code")
    start_date: Optional[date] = Field(None, description="Start date")
    end_date: Optional[date] = Field(None, description="End date")
    
    @field_validator('indicator')
    @classmethod
    def validate_indicator(cls, v):
        if not v or not v.strip():
            raise ValueError("Indicator cannot be empty")
        
        indicator = v.strip().title()
        
        if not re.match(r'^[A-Za-z\s\-]+$', indicator):
            raise ValueError("Indicator contains invalid characters")
        
        return indicator
    
    @field_validator('country')
    @classmethod
    def validate_country(cls, v):
        if not v or not v.strip():
            raise ValueError("Country cannot be empty")
        
        country = v.strip().upper()
        
        if len(country) not in [2, 3]:
            raise ValueError("Country must be 2 or 3 letter code")
        
        if not re.match(r'^[A-Z]{2,3}$', country):
            raise ValueError("Country must contain only letters")
        
        return country
    
    @model_validator(mode='after')
    @classmethod
    def validate_date_range(cls, values):
        start_date = values.get('start_date')
        end_date = values.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise ValueError("start_date must be before end_date")
        
        return values


class AlphaVantageParams(BaseProviderParams):
    """Alpha Vantage API parameters"""
    
    function: str = Field(..., description="API function")
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    interval: Optional[str] = Field("1min", description="Time interval")
    outputsize: Optional[str] = Field("compact", description="Output size")
    
    @field_validator('function')
    @classmethod
    def validate_function(cls, v):
        valid_functions = [
            "TIME_SERIES_INTRADAY", "TIME_SERIES_DAILY", "TIME_SERIES_WEEKLY",
            "TIME_SERIES_MONTHLY", "GLOBAL_QUOTE", "SYMBOL_SEARCH"
        ]
        
        if v not in valid_functions:
            raise ValueError(f"Function must be one of: {', '.join(valid_functions)}")
        
        return v
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v):
        if not v or not v.strip():
            raise ValueError("Symbol cannot be empty")
        
        symbol = v.strip().upper()
        
        if len(symbol) < 1 or len(symbol) > 10:
            raise ValueError("Symbol must be 1-10 characters")
        
        if not re.match(r'^[A-Z\.\-]+$', symbol):
            raise ValueError("Symbol contains invalid characters")
        
        return symbol
    
    @field_validator('interval')
    @classmethod
    def validate_interval(cls, v):
        if v is None:
            return v
        
        valid_intervals = ["1min", "5min", "15min", "30min", "60min"]
        if v not in valid_intervals:
            raise ValueError(f"Interval must be one of: {', '.join(valid_intervals)}")
        
        return v
    
    @field_validator('outputsize')
    @classmethod
    def validate_outputsize(cls, v):
        if v is None:
            return v
        
        valid_outputs = ["compact", "full"]
        if v not in valid_outputs:
            raise ValueError(f"Output size must be one of: {', '.join(valid_outputs)}")
        
        return v


# Provider parameter mapping
PROVIDER_PARAMS = {
    "finnhub": FinnhubParams,
    "yahoo_finance": YahooFinanceParams,
    "marketstack": MarketStackParams,
    "financial_modeling_prep": FinancialModelingPrepParams,
    "news_catcher": NewsCatcherParams,
    "econdb": EconDBParams,
    "trading_economics": TradingEconomicsParams,
    "alpha_vantage": AlphaVantageParams
}


def get_provider_params(provider_name: str) -> type[BaseProviderParams]:
    """Get parameter model for a specific provider"""
    provider_name_lower = provider_name.lower()
    
    if provider_name_lower not in PROVIDER_PARAMS:
        raise ValidationContractError(
            f"Unknown provider: {provider_name}",
            field="provider_name",
            value=provider_name
        )
    
    return PROVIDER_PARAMS[provider_name_lower]


def validate_provider_params(provider_name: str, params: Dict[str, Any]) -> BaseModel:
    """
    Validate parameters for a specific provider
    
    Args:
        provider_name: Name of the provider
        params: Dictionary of parameters to validate
        
    Returns:
        Validated Pydantic model
        
    Raises:
        ValidationContractError: If validation fails
    """
    try:
        params_class = get_provider_params(provider_name)
        return params_class(**params)
    except ValueError as e:
        raise ValidationContractError(str(e))
    except Exception as e:
        raise ValidationContractError(f"Validation failed: {str(e)}")


# Utility functions for common transformations
def transform_to_timestamp(value: Union[str, datetime, int]) -> int:
    """Transform various date formats to Unix timestamp"""
    if isinstance(value, int):
        return value
    elif isinstance(value, str):
        try:
            # Try ISO format first
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return int(dt.timestamp())
        except ValueError:
            # Try Unix timestamp string
            return int(value)
    elif isinstance(value, datetime):
        return int(value.timestamp())
    else:
        raise ValueError(f"Cannot transform {type(value)} to timestamp")


def transform_to_iso8601(value: Union[str, datetime, int]) -> str:
    """Transform various date formats to ISO8601 string"""
    if isinstance(value, str):
        # Assume already in ISO format or try to parse
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt.isoformat()
        except ValueError:
            raise ValueError(f"Invalid date string: {value}")
    elif isinstance(value, int):
        dt = datetime.fromtimestamp(value)
        return dt.isoformat()
    elif isinstance(value, datetime):
        return value.isoformat()
    else:
        raise ValueError(f"Cannot transform {type(value)} to ISO8601")


def transform_symbol(symbol: str) -> str:
    """Standardize symbol format"""
    if not symbol:
        raise ValueError("Symbol cannot be empty")
    
    return symbol.strip().upper()


def transform_symbols_list(symbols: Union[str, List[str]]) -> str:
    """Transform symbols list to comma-separated string"""
    if isinstance(symbols, str):
        symbols = [s.strip() for s in symbols.split(',') if s.strip()]
    elif isinstance(symbols, list):
        symbols = [s.strip().upper() for s in symbols if s.strip()]
    else:
        raise ValueError("Symbols must be string or list")
    
    if not symbols:
        raise ValueError("At least one symbol is required")
    
    return ','.join(symbols)
