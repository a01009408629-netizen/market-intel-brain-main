from pydantic import BaseModel, Field, validator
from typing import Optional, List, Union, Dict, Any
from datetime import datetime
from enum import Enum


class TimeFrame(str, Enum):
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"


class BaseMarketDataRequest(BaseModel):
    """Base model for market data requests"""
    
    symbol: str = Field(..., description="Trading symbol or ticker")
    timeframe: Optional[TimeFrame] = Field(None, description="Time interval for data")
    start_date: Optional[datetime] = Field(None, description="Start date for historical data")
    end_date: Optional[datetime] = Field(None, description="End date for historical data")
    limit: Optional[int] = Field(None, ge=1, le=10000, description="Maximum number of records")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or not v.strip():
            raise ValueError("Symbol cannot be empty")
        return v.upper().strip()
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        if v and 'start_date' in values and values['start_date']:
            if v <= values['start_date']:
                raise ValueError("End date must be after start date")
        return v


class StockDataRequest(BaseMarketDataRequest):
    """Request model for stock market data"""
    
    include_prepost: bool = Field(True, description="Include pre-market and post-market data")
    include_extended: bool = Field(False, description="Include extended hours data")
    
    class Config:
        extra = "forbid"


class ForexDataRequest(BaseMarketDataRequest):
    """Request model for forex data"""
    
    from_symbol: str = Field(..., description="Base currency symbol")
    to_symbol: str = Field(..., description="Quote currency symbol")
    
    @validator('from_symbol', 'to_symbol')
    def validate_currency_symbols(cls, v):
        if not v or not v.strip():
            raise ValueError("Currency symbol cannot be empty")
        return v.upper().strip()
    
    class Config:
        extra = "forbid"


class CryptoDataRequest(BaseMarketDataRequest):
    """Request model for cryptocurrency data"""
    
    exchange: Optional[str] = Field(None, description="Cryptocurrency exchange")
    
    class Config:
        extra = "forbid"


class NewsDataRequest(BaseModel):
    """Request model for news data"""
    
    query: Optional[str] = Field(None, description="Search query for news")
    sources: Optional[List[str]] = Field(None, description="News sources to include")
    categories: Optional[List[str]] = Field(None, description="News categories")
    language: str = Field("en", description="Language code")
    limit: int = Field(50, ge=1, le=1000, description="Number of news articles")
    from_date: Optional[datetime] = Field(None, description="Start date for news")
    to_date: Optional[datetime] = Field(None, description="End date for news")
    
    @validator('language')
    def validate_language(cls, v):
        if len(v) != 2:
            raise ValueError("Language must be a 2-letter ISO code")
        return v.lower()
    
    @validator('to_date')
    def validate_news_date_range(cls, v, values):
        if v and 'from_date' in values and values['from_date']:
            if v <= values['from_date']:
                raise ValueError("End date must be after start date")
        return v
    
    class Config:
        extra = "forbid"


class EconomicDataRequest(BaseModel):
    """Request model for economic data"""
    
    indicator: str = Field(..., description="Economic indicator name")
    country: str = Field(..., description="Country code")
    start_date: Optional[datetime] = Field(None, description="Start date for data")
    end_date: Optional[datetime] = Field(None, description="End date for data")
    frequency: Optional[str] = Field(None, description="Data frequency (daily, monthly, quarterly, yearly)")
    
    @validator('indicator')
    def validate_indicator(cls, v):
        if not v or not v.strip():
            raise ValueError("Indicator cannot be empty")
        return v.strip()
    
    @validator('country')
    def validate_country(cls, v):
        if len(v) != 2 and len(v) != 3:
            raise ValueError("Country must be a 2 or 3 letter code")
        return v.upper()
    
    class Config:
        extra = "forbid"


class CompanyProfileRequest(BaseModel):
    """Request model for company profile data"""
    
    symbol: str = Field(..., description="Company ticker symbol")
    fields: Optional[List[str]] = Field(None, description="Specific fields to retrieve")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or not v.strip():
            raise ValueError("Symbol cannot be empty")
        return v.upper().strip()
    
    class Config:
        extra = "forbid"


class FinancialsRequest(BaseModel):
    """Request model for financial statements"""
    
    symbol: str = Field(..., description="Company ticker symbol")
    statement_type: str = Field(..., description="Type of financial statement (income-statement, balance-sheet, cash-flow)")
    period: str = Field("annual", description="Period type (annual, quarterly)")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or not v.strip():
            raise ValueError("Symbol cannot be empty")
        return v.upper().strip()
    
    @validator('statement_type')
    def validate_statement_type(cls, v):
        valid_types = ["income-statement", "balance-sheet", "cash-flow"]
        if v not in valid_types:
            raise ValueError(f"Statement type must be one of: {valid_types}")
        return v
    
    @validator('period')
    def validate_period(cls, v):
        if v not in ["annual", "quarterly"]:
            raise ValueError("Period must be either 'annual' or 'quarterly'")
        return v
    
    class Config:
        extra = "forbid"


class TechnicalIndicatorsRequest(BaseModel):
    """Request model for technical indicators"""
    
    symbol: str = Field(..., description="Trading symbol")
    indicator: str = Field(..., description="Technical indicator name")
    interval: Optional[TimeFrame] = Field(None, description="Time interval")
    time_period: int = Field(20, ge=1, le=500, description="Number of periods")
    series_type: str = Field("close", description="Price series to use")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or not v.strip():
            raise ValueError("Symbol cannot be empty")
        return v.upper().strip()
    
    @validator('indicator')
    def validate_indicator(cls, v):
        if not v or not v.strip():
            raise ValueError("Indicator cannot be empty")
        return v.strip()
    
    @validator('series_type')
    def validate_series_type(cls, v):
        valid_types = ["open", "high", "low", "close"]
        if v not in valid_types:
            raise ValueError(f"Series type must be one of: {valid_types}")
        return v
    
    class Config:
        extra = "forbid"


class SearchRequest(BaseModel):
    """Request model for symbol search"""
    
    query: str = Field(..., description="Search query")
    exchange: Optional[str] = Field(None, description="Exchange filter")
    security_types: Optional[List[str]] = Field(None, description="Security type filters")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    
    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError("Search query cannot be empty")
        return v.strip()
    
    class Config:
        extra = "forbid"
