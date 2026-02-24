"""
Unified Data Normalizer - AI Integration Layer

Enterprise-grade data normalization layer that transforms heterogeneous data sources
into unified, AI-ready formats with strict typing and validation.

This layer sits ON TOP of existing data fetching logic without modifying it.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, Union, Literal, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
import uuid
from pydantic import BaseModel, Field, validator, ConfigDict

# Import existing schemas
from services.schemas.market_data import UnifiedMarketData, DataSource, MarketDataSymbol


class DataType(Enum):
    """Standardized data types for AI consumption."""
    MARKET_PRICE = "market_price"
    MARKET_OHLCV = "market_ohlcv"
    NEWS_ARTICLE = "news_article"
    SENTIMENT_DATA = "sentiment_data"
    ECONOMIC_INDICATOR = "economic_indicator"
    SOCIAL_MEDIA_POST = "social_media_post"
    GEOPOLITICAL_EVENT = "geopolitical_event"


class DataQuality(Enum):
    """Data quality levels."""
    HIGH = "high"      # Complete, validated, fresh data
    MEDIUM = "medium"  # Partial data, some validation
    LOW = "low"        # Incomplete, stale, or unvalidated data


class ConfidenceLevel(Enum):
    """Confidence levels for data accuracy."""
    VERY_HIGH = 0.95
    HIGH = 0.85
    MEDIUM = 0.70
    LOW = 0.50
    VERY_LOW = 0.30


@dataclass
class ProcessingMetadata:
    """Metadata for data processing pipeline."""
    processing_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_system: str = ""
    original_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    normalized_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processing_latency_ms: float = 0.0
    data_quality: DataQuality = DataQuality.MEDIUM
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    transformations_applied: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    token_estimate: int = 0


# Pydantic Models for Strict Validation
class BaseUnifiedData(BaseModel):
    """Base model for all unified data with strict validation."""
    model_config = ConfigDict(strict=True, validate_assignment=True)
    
    # Core identifiers
    data_id: str = Field(..., description="Unique data identifier")
    data_type: DataType = Field(..., description="Type of data")
    source: DataSource = Field(..., description="Data source")
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol or identifier")
    
    # Timestamps
    timestamp: datetime = Field(..., description="Data timestamp")
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Metadata
    processing_metadata: ProcessingMetadata = Field(..., description="Processing metadata")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Original raw data")
    
    @validator('timestamp')
    @classmethod
    def validate_timestamp_not_future(cls, v: datetime) -> datetime:
        """Validate timestamp is not in the future."""
        if v > datetime.now(timezone.utc):
            raise ValueError("Timestamp cannot be in the future")
        return v
    
    @validator('symbol')
    @classmethod
    def validate_symbol_format(cls, v: str) -> str:
        """Validate symbol format."""
        if not v or not v.strip():
            raise ValueError("Symbol cannot be empty")
        return v.upper().strip()


class UnifiedMarketPrice(BaseUnifiedData):
    """Unified market price data with strict validation."""
    model_config = ConfigDict(strict=True, validate_assignment=True)
    
    # Price data
    price: Decimal = Field(..., gt=0, description="Current price")
    volume: Optional[Decimal] = Field(None, ge=0, description="Trading volume")
    bid: Optional[Decimal] = Field(None, gt=0, description="Bid price")
    ask: Optional[Decimal] = Field(None, gt=0, description="Ask price")
    change: Optional[Decimal] = Field(None, description="Price change")
    change_percent: Optional[Decimal] = Field(None, description="Percentage change")
    
    # Market context
    market_status: Literal["open", "closed", "pre_market", "after_hours"] = "open"
    currency: str = Field(..., min_length=3, max_length=3, description="Currency code")
    
    @validator('ask', 'bid')
    @classmethod
    def validate_bid_ask_relationship(cls, v: Optional[Decimal], values: Dict[str, Any]) -> Optional[Decimal]:
        """Validate bid-ask relationship."""
        if v is not None and 'price' in values:
            price = values['price']
            if 'bid' in values and values['bid'] is not None:
                if values['bid'] > price:
                    raise ValueError("Bid price cannot be higher than market price")
            if 'ask' in values and values['ask'] is not None:
                if values['ask'] < price:
                    raise ValueError("Ask price cannot be lower than market price")
        return v


class UnifiedOHLCV(BaseUnifiedData):
    """Unified OHLCV data with strict validation."""
    model_config = ConfigDict(strict=True, validate_assignment=True)
    
    # OHLCV data
    open: Decimal = Field(..., gt=0, description="Opening price")
    high: Decimal = Field(..., gt=0, description="Highest price")
    low: Decimal = Field(..., gt=0, description="Lowest price")
    close: Decimal = Field(..., gt=0, description="Closing price")
    volume: Decimal = Field(..., ge=0, description="Trading volume")
    
    # Additional fields
    adj_close: Optional[Decimal] = Field(None, gt=0, description="Adjusted closing price")
    timeframe: str = Field(..., description="Timeframe (1m, 5m, 1h, 1d, etc.)")
    currency: str = Field(..., min_length=3, max_length=3, description="Currency code")
    
    @validator('high')
    @classmethod
    def validate_high_relationship(cls, v: Decimal, values: Dict[str, Any]) -> Decimal:
        """Validate high price relationship."""
        if 'low' in values and values['low'] is not None:
            if v < values['low']:
                raise ValueError("High price cannot be lower than low price")
        if 'open' in values and values['open'] is not None:
            if v < values['open']:
                raise ValueError("High price cannot be lower than open price")
        if 'close' in values and values['close'] is not None:
            if v < values['close']:
                raise ValueError("High price cannot be lower than close price")
        return v
    
    @validator('low')
    @classmethod
    def validate_low_relationship(cls, v: Decimal, values: Dict[str, Any]) -> Decimal:
        """Validate low price relationship."""
        if 'high' in values and values['high'] is not None:
            if v > values['high']:
                raise ValueError("Low price cannot be higher than high price")
        if 'open' in values and values['open'] is not None:
            if v > values['open']:
                raise ValueError("Low price cannot be higher than open price")
        if 'close' in values and values['close'] is not None:
            if v > values['close']:
                raise ValueError("Low price cannot be higher than close price")
        return v


class UnifiedNewsArticle(BaseUnifiedData):
    """Unified news article data with strict validation."""
    model_config = ConfigDict(strict=True, validate_assignment=True)
    
    # Article content
    title: str = Field(..., min_length=5, max_length=500, description="Article title")
    content: str = Field(..., min_length=10, max_length=10000, description="Article content")
    summary: Optional[str] = Field(None, max_length=1000, description="Article summary")
    author: Optional[str] = Field(None, max_length=100, description="Article author")
    url: Optional[str] = Field(None, description="Article URL")
    
    # Sentiment and relevance
    sentiment_score: Decimal = Field(..., ge=-1, le=1, description="Sentiment score (-1 to 1)")
    sentiment_label: Literal["positive", "negative", "neutral", "mixed"] = "neutral"
    relevance_score: Decimal = Field(..., ge=0, le=1, description="Relevance score (0 to 1)")
    
    # Categorization
    category: str = Field(..., max_length=50, description="News category")
    tags: List[str] = Field(default_factory=list, description="Article tags")
    language: str = Field(default="en", max_length=5, description="Language code")
    
    @validator('sentiment_label')
    @classmethod
    def validate_sentiment_consistency(cls, v: str, values: Dict[str, Any]) -> str:
        """Validate sentiment label consistency with score."""
        if 'sentiment_score' in values:
            score = float(values['sentiment_score'])
            if score > 0.3 and v != "positive":
                raise ValueError("Sentiment label must be 'positive' for scores > 0.3")
            elif score < -0.3 and v != "negative":
                raise ValueError("Sentiment label must be 'negative' for scores < -0.3")
            elif -0.3 <= score <= 0.3 and v not in ["neutral", "mixed"]:
                raise ValueError("Sentiment label must be 'neutral' or 'mixed' for scores between -0.3 and 0.3")
        return v


class UnifiedSentimentData(BaseUnifiedData):
    """Unified sentiment analysis data with strict validation."""
    model_config = ConfigDict(strict=True, validate_assignment=True)
    
    # Sentiment metrics
    overall_sentiment: Decimal = Field(..., ge=-1, le=1, description="Overall sentiment score")
    sentiment_label: Literal["positive", "negative", "neutral", "mixed"] = "neutral"
    confidence: Decimal = Field(..., ge=0, le=1, description="Confidence in sentiment analysis")
    
    # Detailed emotions
    emotions: Dict[str, Decimal] = Field(default_factory=dict, description="Emotion scores")
    engagement_metrics: Dict[str, int] = Field(default_factory=dict, description="Engagement metrics")
    
    # Source information
    platform: str = Field(..., max_length=50, description="Social media platform")
    topic: str = Field(..., max_length=100, description="Topic or keyword")
    language: str = Field(default="en", max_length=5, description="Language code")
    
    @validator('emotions')
    @classmethod
    def validate_emotions_sum(cls, v: Dict[str, Decimal]) -> Dict[str, Decimal]:
        """Validate emotion scores sum to 1.0."""
        if v:
            total = sum(float(score) for score in v.values())
            if abs(total - 1.0) > 0.1:  # Allow 10% tolerance
                raise ValueError(f"Emotion scores should sum to approximately 1.0, got {total}")
        return v
    
    @validator('sentiment_label')
    @classmethod
    def validate_sentiment_consistency(cls, v: str, values: Dict[str, Any]) -> str:
        """Validate sentiment label consistency with score."""
        if 'overall_sentiment' in values:
            score = float(values['overall_sentiment'])
            if score > 0.3 and v != "positive":
                raise ValueError("Sentiment label must be 'positive' for scores > 0.3")
            elif score < -0.3 and v != "negative":
                raise ValueError("Sentiment label must be 'negative' for scores < -0.3")
            elif -0.3 <= score <= 0.3 and v not in ["neutral", "mixed"]:
                raise ValueError("Sentiment label must be 'neutral' or 'mixed' for scores between -0.3 and 0.3")
        return v


# Type alias for unified data types
UnifiedData = Union[
    UnifiedMarketPrice,
    UnifiedOHLCV,
    UnifiedNewsArticle,
    UnifiedSentimentData
]


class UnifiedDataNormalizer:
    """
    Enterprise-grade data normalizer that transforms heterogeneous data sources
    into unified, AI-ready formats with strict validation and typing.
    
    This layer sits ON TOP of existing data fetching logic without modifying it.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("UnifiedDataNormalizer")
        self._normalization_stats = {
            "total_processed": 0,
            "successful_normalizations": 0,
            "failed_normalizations": 0,
            "by_data_type": {},
            "by_source": {},
            "average_processing_time_ms": 0.0
        }
    
    async def normalize_market_price(
        self,
        raw_data: Dict[str, Any],
        source: DataSource,
        symbol: str,
        timestamp: Optional[datetime] = None
    ) -> UnifiedMarketPrice:
        """
        Normalize market price data from any source.
        
        Args:
            raw_data: Raw market price data
            source: Data source identifier
            symbol: Trading symbol
            timestamp: Data timestamp (uses current if None)
            
        Returns:
            Normalized market price data
        """
        start_time = datetime.now()
        
        try:
            # Extract price information with fallbacks
            price = self._extract_price(raw_data)
            volume = self._extract_volume(raw_data)
            bid = self._extract_bid(raw_data)
            ask = self._extract_ask(raw_data)
            change = self._extract_change(raw_data)
            change_percent = self._extract_change_percent(raw_data)
            
            # Determine market status
            market_status = self._determine_market_status(raw_data)
            
            # Extract currency
            currency = self._extract_currency(raw_data, source)
            
            # Create processing metadata
            processing_metadata = ProcessingMetadata(
                source_system=source.value,
                original_timestamp=timestamp or datetime.now(timezone.utc),
                processing_latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
                data_quality=self._assess_data_quality(raw_data),
                confidence_level=self._assess_confidence(raw_data, source),
                transformations_applied=["price_normalization", "currency_standardization"],
                token_estimate=self._estimate_token_count(raw_data)
            )
            
            # Create unified data
            unified_data = UnifiedMarketPrice(
                data_id=str(uuid.uuid4()),
                data_type=DataType.MARKET_PRICE,
                source=source,
                symbol=symbol,
                timestamp=timestamp or datetime.now(timezone.utc),
                price=price,
                volume=volume,
                bid=bid,
                ask=ask,
                change=change,
                change_percent=change_percent,
                market_status=market_status,
                currency=currency,
                processing_metadata=processing_metadata,
                raw_data=raw_data
            )
            
            # Update statistics
            self._update_stats("market_price", source, True, processing_metadata.processing_latency_ms)
            
            self.logger.debug(f"✅ Normalized market price: {symbol} from {source.value}")
            return unified_data
            
        except Exception as e:
            self._update_stats("market_price", source, False, (datetime.now() - start_time).total_seconds() * 1000)
            self.logger.error(f"❌ Failed to normalize market price: {e}")
            raise
    
    async def normalize_news_article(
        self,
        raw_data: Dict[str, Any],
        source: DataSource,
        symbol: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> UnifiedNewsArticle:
        """
        Normalize news article data from any source.
        
        Args:
            raw_data: Raw news article data
            source: Data source identifier
            symbol: Related symbol (optional)
            timestamp: Article timestamp (uses current if None)
            
        Returns:
            Normalized news article data
        """
        start_time = datetime.now()
        
        try:
            # Extract article content
            title = self._extract_title(raw_data)
            content = self._extract_content(raw_data)
            summary = self._extract_summary(raw_data)
            author = self._extract_author(raw_data)
            url = self._extract_url(raw_data)
            
            # Extract sentiment
            sentiment_score = self._extract_sentiment_score(raw_data)
            sentiment_label = self._determine_sentiment_label(sentiment_score)
            relevance_score = self._extract_relevance_score(raw_data)
            
            # Extract categorization
            category = self._extract_category(raw_data)
            tags = self._extract_tags(raw_data)
            language = self._extract_language(raw_data)
            
            # Create processing metadata
            processing_metadata = ProcessingMetadata(
                source_system=source.value,
                original_timestamp=timestamp or datetime.now(timezone.utc),
                processing_latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
                data_quality=self._assess_data_quality(raw_data),
                confidence_level=self._assess_confidence(raw_data, source),
                transformations_applied=["content_normalization", "sentiment_analysis"],
                token_estimate=self._estimate_token_count(raw_data)
            )
            
            # Create unified data
            unified_data = UnifiedNewsArticle(
                data_id=str(uuid.uuid4()),
                data_type=DataType.NEWS_ARTICLE,
                source=source,
                symbol=symbol or "GENERAL",
                timestamp=timestamp or datetime.now(timezone.utc),
                title=title,
                content=content,
                summary=summary,
                author=author,
                url=url,
                sentiment_score=sentiment_score,
                sentiment_label=sentiment_label,
                relevance_score=relevance_score,
                category=category,
                tags=tags,
                language=language,
                processing_metadata=processing_metadata,
                raw_data=raw_data
            )
            
            # Update statistics
            self._update_stats("news_article", source, True, processing_metadata.processing_latency_ms)
            
            self.logger.debug(f"✅ Normalized news article: {title[:50]}... from {source.value}")
            return unified_data
            
        except Exception as e:
            self._update_stats("news_article", source, False, (datetime.now() - start_time).total_seconds() * 1000)
            self.logger.error(f"❌ Failed to normalize news article: {e}")
            raise
    
    async def normalize_sentiment_data(
        self,
        raw_data: Dict[str, Any],
        source: DataSource,
        symbol: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> UnifiedSentimentData:
        """
        Normalize sentiment analysis data from any source.
        
        Args:
            raw_data: Raw sentiment data
            source: Data source identifier
            symbol: Related symbol (optional)
            timestamp: Data timestamp (uses current if None)
            
        Returns:
            Normalized sentiment data
        """
        start_time = datetime.now()
        
        try:
            # Extract sentiment metrics
            overall_sentiment = self._extract_overall_sentiment(raw_data)
            sentiment_label = self._determine_sentiment_label(overall_sentiment)
            confidence = self._extract_confidence(raw_data)
            
            # Extract emotions
            emotions = self._extract_emotions(raw_data)
            
            # Extract engagement metrics
            engagement_metrics = self._extract_engagement_metrics(raw_data)
            
            # Extract source information
            platform = self._extract_platform(raw_data)
            topic = self._extract_topic(raw_data)
            language = self._extract_language(raw_data)
            
            # Create processing metadata
            processing_metadata = ProcessingMetadata(
                source_system=source.value,
                original_timestamp=timestamp or datetime.now(timezone.utc),
                processing_latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
                data_quality=self._assess_data_quality(raw_data),
                confidence_level=self._assess_confidence(raw_data, source),
                transformations_applied=["sentiment_normalization", "emotion_analysis"],
                token_estimate=self._estimate_token_count(raw_data)
            )
            
            # Create unified data
            unified_data = UnifiedSentimentData(
                data_id=str(uuid.uuid4()),
                data_type=DataType.SENTIMENT_DATA,
                source=source,
                symbol=symbol or "GENERAL",
                timestamp=timestamp or datetime.now(timezone.utc),
                overall_sentiment=overall_sentiment,
                sentiment_label=sentiment_label,
                confidence=confidence,
                emotions=emotions,
                engagement_metrics=engagement_metrics,
                platform=platform,
                topic=topic,
                language=language,
                processing_metadata=processing_metadata,
                raw_data=raw_data
            )
            
            # Update statistics
            self._update_stats("sentiment_data", source, True, processing_metadata.processing_latency_ms)
            
            self.logger.debug(f"✅ Normalized sentiment data: {topic} from {source.value}")
            return unified_data
            
        except Exception as e:
            self._update_stats("sentiment_data", source, False, (datetime.now() - start_time).total_seconds() * 1000)
            self.logger.error(f"❌ Failed to normalize sentiment data: {e}")
            raise
    
    # Helper methods for data extraction
    def _extract_price(self, raw_data: Dict[str, Any]) -> Decimal:
        """Extract price from raw data with multiple fallbacks."""
        price_fields = ['price', 'current_price', 'last_price', 'close', 'value']
        for field in price_fields:
            if field in raw_data and raw_data[field] is not None:
                return Decimal(str(raw_data[field]))
        raise ValueError("No price field found in raw data")
    
    def _extract_volume(self, raw_data: Dict[str, Any]) -> Optional[Decimal]:
        """Extract volume from raw data."""
        volume_fields = ['volume', 'trade_volume', 'vol']
        for field in volume_fields:
            if field in raw_data and raw_data[field] is not None:
                return Decimal(str(raw_data[field]))
        return None
    
    def _extract_bid(self, raw_data: Dict[str, Any]) -> Optional[Decimal]:
        """Extract bid price from raw data."""
        bid_fields = ['bid', 'bid_price', 'buy_price']
        for field in bid_fields:
            if field in raw_data and raw_data[field] is not None:
                return Decimal(str(raw_data[field]))
        return None
    
    def _extract_ask(self, raw_data: Dict[str, Any]) -> Optional[Decimal]:
        """Extract ask price from raw data."""
        ask_fields = ['ask', 'ask_price', 'sell_price', 'offer']
        for field in ask_fields:
            if field in raw_data and raw_data[field] is not None:
                return Decimal(str(raw_data[field]))
        return None
    
    def _extract_change(self, raw_data: Dict[str, Any]) -> Optional[Decimal]:
        """Extract price change from raw data."""
        change_fields = ['change', 'price_change', 'net_change']
        for field in change_fields:
            if field in raw_data and raw_data[field] is not None:
                return Decimal(str(raw_data[field]))
        return None
    
    def _extract_change_percent(self, raw_data: Dict[str, Any]) -> Optional[Decimal]:
        """Extract percentage change from raw data."""
        change_percent_fields = ['change_percent', 'percent_change', 'pct_change']
        for field in change_percent_fields:
            if field in raw_data and raw_data[field] is not None:
                return Decimal(str(raw_data[field]))
        return None
    
    def _determine_market_status(self, raw_data: Dict[str, Any]) -> str:
        """Determine market status from raw data."""
        if 'market_status' in raw_data:
            return raw_data['market_status']
        elif 'is_market_open' in raw_data:
            return 'open' if raw_data['is_market_open'] else 'closed'
        else:
            return 'open'  # Default assumption
    
    def _extract_currency(self, raw_data: Dict[str, Any], source: DataSource) -> str:
        """Extract currency from raw data."""
        currency_fields = ['currency', 'quote_currency', 'base_currency']
        for field in currency_fields:
            if field in raw_data and raw_data[field] is not None:
                return str(raw_data[field]).upper()
        
        # Default based on source
        source_currencies = {
            DataSource.BINANCE: "USDT",
            DataSource.YAHOO_FINANCE: "USD",
            DataSource.FINNHUB: "USD",
            DataSource.ALPHA_VANTAGE: "USD"
        }
        return source_currencies.get(source, "USD")
    
    def _extract_title(self, raw_data: Dict[str, Any]) -> str:
        """Extract title from raw data."""
        title_fields = ['title', 'headline', 'subject']
        for field in title_fields:
            if field in raw_data and raw_data[field] is not None:
                return str(raw_data[field])
        raise ValueError("No title field found in raw data")
    
    def _extract_content(self, raw_data: Dict[str, Any]) -> str:
        """Extract content from raw data."""
        content_fields = ['content', 'body', 'text', 'description', 'summary']
        for field in content_fields:
            if field in raw_data and raw_data[field] is not None:
                return str(raw_data[field])
        raise ValueError("No content field found in raw data")
    
    def _extract_summary(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Extract summary from raw data."""
        summary_fields = ['summary', 'excerpt', 'snippet']
        for field in summary_fields:
            if field in raw_data and raw_data[field] is not None:
                return str(raw_data[field])
        return None
    
    def _extract_author(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Extract author from raw data."""
        author_fields = ['author', 'byline', 'creator']
        for field in author_fields:
            if field in raw_data and raw_data[field] is not None:
                return str(raw_data[field])
        return None
    
    def _extract_url(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Extract URL from raw data."""
        url_fields = ['url', 'link', 'permalink', 'web_url']
        for field in url_fields:
            if field in raw_data and raw_data[field] is not None:
                return str(raw_data[field])
        return None
    
    def _extract_sentiment_score(self, raw_data: Dict[str, Any]) -> Decimal:
        """Extract sentiment score from raw data."""
        sentiment_fields = ['sentiment_score', 'sentiment', 'score', 'polarity']
        for field in sentiment_fields:
            if field in raw_data and raw_data[field] is not None:
                return Decimal(str(raw_data[field]))
        return Decimal("0.0")  # Default neutral
    
    def _extract_relevance_score(self, raw_data: Dict[str, Any]) -> Decimal:
        """Extract relevance score from raw data."""
        relevance_fields = ['relevance_score', 'relevance', 'importance', 'weight']
        for field in relevance_fields:
            if field in raw_data and raw_data[field] is not None:
                return Decimal(str(raw_data[field]))
        return Decimal("0.5")  # Default medium relevance
    
    def _extract_category(self, raw_data: Dict[str, Any]) -> str:
        """Extract category from raw data."""
        category_fields = ['category', 'section', 'type']
        for field in category_fields:
            if field in raw_data and raw_data[field] is not None:
                return str(raw_data[field])
        return "general"  # Default category
    
    def _extract_tags(self, raw_data: Dict[str, Any]) -> List[str]:
        """Extract tags from raw data."""
        tags_fields = ['tags', 'keywords', 'labels']
        for field in tags_fields:
            if field in raw_data and raw_data[field] is not None:
                tags = raw_data[field]
                if isinstance(tags, list):
                    return [str(tag) for tag in tags]
                elif isinstance(tags, str):
                    return [tag.strip() for tag in tags.split(',')]
        return []
    
    def _extract_language(self, raw_data: Dict[str, Any]) -> str:
        """Extract language from raw data."""
        language_fields = ['language', 'lang', 'locale']
        for field in language_fields:
            if field in raw_data and raw_data[field] is not None:
                return str(raw_data[field]).lower()
        return "en"  # Default English
    
    def _extract_overall_sentiment(self, raw_data: Dict[str, Any]) -> Decimal:
        """Extract overall sentiment from raw data."""
        sentiment_fields = ['overall_sentiment', 'sentiment', 'average_sentiment']
        for field in sentiment_fields:
            if field in raw_data and raw_data[field] is not None:
                return Decimal(str(raw_data[field]))
        return Decimal("0.0")  # Default neutral
    
    def _extract_confidence(self, raw_data: Dict[str, Any]) -> Decimal:
        """Extract confidence from raw data."""
        confidence_fields = ['confidence', 'confidence_score', 'certainty']
        for field in confidence_fields:
            if field in raw_data and raw_data[field] is not None:
                return Decimal(str(raw_data[field]))
        return Decimal("0.5")  # Default medium confidence
    
    def _extract_emotions(self, raw_data: Dict[str, Any]) -> Dict[str, Decimal]:
        """Extract emotions from raw data."""
        emotions_fields = ['emotions', 'emotion_scores', 'feelings']
        for field in emotions_fields:
            if field in raw_data and raw_data[field] is not None:
                emotions = raw_data[field]
                if isinstance(emotions, dict):
                    return {k: Decimal(str(v)) for k, v in emotions.items()}
        return {}
    
    def _extract_engagement_metrics(self, raw_data: Dict[str, Any]) -> Dict[str, int]:
        """Extract engagement metrics from raw data."""
        engagement_fields = ['engagement', 'metrics', 'stats']
        for field in engagement_fields:
            if field in raw_data and raw_data[field] is not None:
                engagement = raw_data[field]
                if isinstance(engagement, dict):
                    return {k: int(v) if isinstance(v, (int, float, str)) and str(v).isdigit() else 0 
                           for k, v in engagement.items()}
        return {}
    
    def _extract_platform(self, raw_data: Dict[str, Any]) -> str:
        """Extract platform from raw data."""
        platform_fields = ['platform', 'source', 'network']
        for field in platform_fields:
            if field in raw_data and raw_data[field] is not None:
                return str(raw_data[field])
        return "unknown"  # Default unknown platform
    
    def _extract_topic(self, raw_data: Dict[str, Any]) -> str:
        """Extract topic from raw data."""
        topic_fields = ['topic', 'subject', 'keyword', 'query']
        for field in topic_fields:
            if field in raw_data and raw_data[field] is not None:
                return str(raw_data[field])
        return "general"  # Default general topic
    
    def _determine_sentiment_label(self, sentiment_score: Decimal) -> str:
        """Determine sentiment label from score."""
        score = float(sentiment_score)
        if score > 0.3:
            return "positive"
        elif score < -0.3:
            return "negative"
        elif -0.3 <= score <= 0.3:
            return "neutral"
        else:
            return "mixed"
    
    def _assess_data_quality(self, raw_data: Dict[str, Any]) -> DataQuality:
        """Assess data quality based on completeness and freshness."""
        required_fields = ['timestamp']
        missing_required = sum(1 for field in required_fields if field not in raw_data)
        
        if missing_required == 0 and len(raw_data) > 5:
            return DataQuality.HIGH
        elif missing_required <= 1 and len(raw_data) > 3:
            return DataQuality.MEDIUM
        else:
            return DataQuality.LOW
    
    def _assess_confidence(self, raw_data: Dict[str, Any], source: DataSource) -> ConfidenceLevel:
        """Assess confidence level based on source and data completeness."""
        source_confidence = {
            DataSource.BINANCE: ConfidenceLevel.VERY_HIGH,
            DataSource.YAHOO_FINANCE: ConfidenceLevel.HIGH,
            DataSource.FINNHUB: ConfidenceLevel.HIGH,
            DataSource.ALPHA_VANTAGE: ConfidenceLevel.MEDIUM
        }
        
        base_confidence = source_confidence.get(source, ConfidenceLevel.MEDIUM)
        
        # Adjust based on data completeness
        if len(raw_data) > 10:
            return base_confidence
        elif len(raw_data) > 5:
            return ConfidenceLevel(max(0.5, float(base_confidence.value) - 0.15))
        else:
            return ConfidenceLevel(max(0.3, float(base_confidence.value) - 0.35))
    
    def _estimate_token_count(self, raw_data: Dict[str, Any]) -> int:
        """Estimate token count for LLM processing."""
        # Rough estimation: 1 token ≈ 4 characters
        text_content = json.dumps(raw_data, default=str)
        return max(1, len(text_content) // 4)
    
    def _update_stats(self, data_type: str, source: DataSource, success: bool, processing_time_ms: float):
        """Update normalization statistics."""
        self._normalization_stats["total_processed"] += 1
        
        if success:
            self._normalization_stats["successful_normalizations"] += 1
        else:
            self._normalization_stats["failed_normalizations"] += 1
        
        # Update by data type
        if data_type not in self._normalization_stats["by_data_type"]:
            self._normalization_stats["by_data_type"][data_type] = {
                "processed": 0, "successful": 0, "failed": 0
            }
        
        self._normalization_stats["by_data_type"][data_type]["processed"] += 1
        if success:
            self._normalization_stats["by_data_type"][data_type]["successful"] += 1
        else:
            self._normalization_stats["by_data_type"][data_type]["failed"] += 1
        
        # Update by source
        source_key = source.value
        if source_key not in self._normalization_stats["by_source"]:
            self._normalization_stats["by_source"][source_key] = {
                "processed": 0, "successful": 0, "failed": 0
            }
        
        self._normalization_stats["by_source"][source_key]["processed"] += 1
        if success:
            self._normalization_stats["by_source"][source_key]["successful"] += 1
        else:
            self._normalization_stats["by_source"][source_key]["failed"] += 1
        
        # Update average processing time
        total_processed = self._normalization_stats["total_processed"]
        current_avg = self._normalization_stats["average_processing_time_ms"]
        self._normalization_stats["average_processing_time_ms"] = (
            (current_avg * (total_processed - 1) + processing_time_ms) / total_processed
        )
    
    def get_normalization_stats(self) -> Dict[str, Any]:
        """Get normalization statistics."""
        return self._normalization_stats.copy()


# Global normalizer instance
_unified_normalizer: Optional[UnifiedDataNormalizer] = None


def get_unified_normalizer() -> UnifiedDataNormalizer:
    """Get or create the global unified normalizer instance."""
    global _unified_normalizer
    if _unified_normalizer is None:
        _unified_normalizer = UnifiedDataNormalizer()
    return _unified_normalizer
