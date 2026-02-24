from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class UnifiedMarketData(BaseModel):
    """Unified schema for normalized market data"""
    
    symbol: str = Field(..., description="Trading symbol or ticker")
    price: Optional[Decimal] = Field(None, description="Current price")
    change: Optional[Decimal] = Field(None, description="Price change")
    change_percent: Optional[Decimal] = Field(None, description="Percentage change")
    volume: Optional[int] = Field(None, description="Trading volume")
    high: Optional[Decimal] = Field(None, description="High price")
    low: Optional[Decimal] = Field(None, description="Low price")
    open: Optional[Decimal] = Field(None, description="Open price")
    close: Optional[Decimal] = Field(None, description="Close price")
    bid: Optional[Decimal] = Field(None, description="Bid price")
    ask: Optional[Decimal] = Field(None, description="Ask price")
    timestamp: datetime = Field(..., description="Data timestamp in UTC")
    source_metadata: Dict[str, Any] = Field(default_factory=dict, description="Source-specific metadata")
    
    @validator('symbol')
    def normalize_symbol(cls, v):
        return v.upper().strip()
    
    @validator('timestamp')
    def ensure_utc(cls, v):
        if v.tzinfo is None:
            # Assume UTC if no timezone info
            return v.replace(tzinfo=datetime.timezone.utc)
        return v.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat() + 'Z'
        }


class UnifiedForexData(BaseModel):
    """Unified schema for forex data"""
    
    from_symbol: str = Field(..., description="Base currency symbol")
    to_symbol: str = Field(..., description="Quote currency symbol")
    pair: str = Field(..., description="Currency pair")
    exchange_rate: Decimal = Field(..., description="Exchange rate")
    change: Optional[Decimal] = Field(None, description="Rate change")
    change_percent: Optional[Decimal] = Field(None, description="Percentage change")
    timestamp: datetime = Field(..., description="Data timestamp in UTC")
    source_metadata: Dict[str, Any] = Field(default_factory=dict, description="Source-specific metadata")
    
    @validator('from_symbol', 'to_symbol')
    def normalize_currency_symbols(cls, v):
        return v.upper().strip()
    
    @validator('pair')
    def normalize_pair(cls, v):
        return v.upper().strip()
    
    @validator('timestamp')
    def ensure_utc(cls, v):
        if v.tzinfo is None:
            return v.replace(tzinfo=datetime.timezone.utc)
        return v.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat() + 'Z'
        }


class UnifiedCryptoData(BaseModel):
    """Unified schema for cryptocurrency data"""
    
    symbol: str = Field(..., description="Cryptocurrency symbol")
    price: Decimal = Field(..., description="Current price")
    market_cap: Optional[Decimal] = Field(None, description="Market capitalization")
    volume_24h: Optional[Decimal] = Field(None, description="24-hour trading volume")
    change_24h: Optional[Decimal] = Field(None, description="24-hour price change")
    change_percent_24h: Optional[Decimal] = Field(None, description="24-hour percentage change")
    high_24h: Optional[Decimal] = Field(None, description="24-hour high price")
    low_24h: Optional[Decimal] = Field(None, description="24-hour low price")
    circulating_supply: Optional[Decimal] = Field(None, description="Circulating supply")
    timestamp: datetime = Field(..., description="Data timestamp in UTC")
    exchange: Optional[str] = Field(None, description="Exchange name")
    source_metadata: Dict[str, Any] = Field(default_factory=dict, description="Source-specific metadata")
    
    @validator('symbol')
    def normalize_symbol(cls, v):
        return v.upper().strip()
    
    @validator('timestamp')
    def ensure_utc(cls, v):
        if v.tzinfo is None:
            return v.replace(tzinfo=datetime.timezone.utc)
        return v.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat() + 'Z'
        }


class UnifiedNewsData(BaseModel):
    """Unified schema for news data"""
    
    title: str = Field(..., description="News article title")
    content: Optional[str] = Field(None, description="News article content or summary")
    url: str = Field(..., description="Article URL")
    source: str = Field(..., description="News source name")
    author: Optional[str] = Field(None, description="Article author")
    published_at: datetime = Field(..., description="Publication timestamp in UTC")
    categories: Optional[List[str]] = Field(None, description="News categories")
    tags: Optional[List[str]] = Field(None, description="News tags")
    sentiment: Optional[str] = Field(None, description="Sentiment analysis result")
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Relevance score")
    language: Optional[str] = Field(None, description="Article language code")
    symbols_mentioned: Optional[List[str]] = Field(None, description="Stock symbols mentioned")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp in UTC")
    source_metadata: Dict[str, Any] = Field(default_factory=dict, description="Source-specific metadata")
    
    @validator('source')
    def normalize_source(cls, v):
        return v.strip().title()
    
    @validator('published_at', 'timestamp')
    def ensure_utc(cls, v):
        if v.tzinfo is None:
            return v.replace(tzinfo=datetime.timezone.utc)
        return v.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    
    @validator('symbols_mentioned')
    def normalize_symbols(cls, v):
        if v:
            return [symbol.upper().strip() for symbol in v if symbol.strip()]
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z'
        }


class UnifiedEconomicData(BaseModel):
    """Unified schema for economic data"""
    
    indicator: str = Field(..., description="Economic indicator name")
    country: str = Field(..., description="Country code")
    value: Decimal = Field(..., description="Indicator value")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    frequency: Optional[str] = Field(None, description="Data frequency")
    period: datetime = Field(..., description="Data period timestamp in UTC")
    change: Optional[Decimal] = Field(None, description="Change from previous period")
    change_percent: Optional[Decimal] = Field(None, description="Percentage change from previous period")
    previous_value: Optional[Decimal] = Field(None, description="Previous period value")
    next_release: Optional[datetime] = Field(None, description="Next release date in UTC")
    source_metadata: Dict[str, Any] = Field(default_factory=dict, description="Source-specific metadata")
    
    @validator('indicator')
    def normalize_indicator(cls, v):
        return v.strip().title()
    
    @validator('country')
    def normalize_country(cls, v):
        return v.upper().strip()
    
    @validator('period', 'next_release')
    def ensure_utc(cls, v):
        if v is None:
            return v
        if v.tzinfo is None:
            return v.replace(tzinfo=datetime.timezone.utc)
        return v.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat() + 'Z'
        }


class UnifiedCompanyProfile(BaseModel):
    """Unified schema for company profile data"""
    
    symbol: str = Field(..., description="Company ticker symbol")
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
    phone: Optional[str] = Field(None, description="Company phone number")
    address: Optional[str] = Field(None, description="Company headquarters address")
    ipo_date: Optional[datetime] = Field(None, description="IPO date in UTC")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Data timestamp in UTC")
    source_metadata: Dict[str, Any] = Field(default_factory=dict, description="Source-specific metadata")
    
    @validator('symbol')
    def normalize_symbol(cls, v):
        return v.upper().strip()
    
    @validator('country', 'currency')
    def normalize_country_currency(cls, v):
        return v.upper().strip() if v else v
    
    @validator('ipo_date', 'timestamp')
    def ensure_utc(cls, v):
        if v is None:
            return v
        if v.tzinfo is None:
            return v.replace(tzinfo=datetime.timezone.utc)
        return v.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat() + 'Z'
        }


class UnifiedFinancialStatement(BaseModel):
    """Unified schema for financial statements"""
    
    symbol: str = Field(..., description="Company ticker symbol")
    statement_type: str = Field(..., description="Type of financial statement")
    period: str = Field(..., description="Period type (annual, quarterly)")
    fiscal_year: int = Field(..., description="Fiscal year")
    fiscal_quarter: Optional[int] = Field(None, ge=1, le=4, description="Fiscal quarter")
    currency: str = Field(..., description="Reporting currency")
    data: Dict[str, Decimal] = Field(..., description="Financial data items")
    filing_date: Optional[datetime] = Field(None, description="Filing date in UTC")
    period_end_date: datetime = Field(..., description="Period end date in UTC")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Data timestamp in UTC")
    source_metadata: Dict[str, Any] = Field(default_factory=dict, description="Source-specific metadata")
    
    @validator('symbol')
    def normalize_symbol(cls, v):
        return v.upper().strip()
    
    @validator('currency')
    def normalize_currency(cls, v):
        return v.upper().strip()
    
    @validator('filing_date', 'period_end_date', 'timestamp')
    def ensure_utc(cls, v):
        if v is None:
            return v
        if v.tzinfo is None:
            return v.replace(tzinfo=datetime.timezone.utc)
        return v.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat() + 'Z'
        }


class UnifiedTechnicalIndicator(BaseModel):
    """Unified schema for technical indicators"""
    
    symbol: str = Field(..., description="Trading symbol")
    indicator: str = Field(..., description="Technical indicator name")
    values: List[Dict[str, Any]] = Field(..., description="Indicator values with timestamps")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Indicator parameters")
    interval: Optional[str] = Field(None, description="Time interval")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Data timestamp in UTC")
    source_metadata: Dict[str, Any] = Field(default_factory=dict, description="Source-specific metadata")
    
    @validator('symbol')
    def normalize_symbol(cls, v):
        return v.upper().strip()
    
    @validator('timestamp')
    def ensure_utc(cls, v):
        if v.tzinfo is None:
            return v.replace(tzinfo=datetime.timezone.utc)
        return v.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z'
        }
