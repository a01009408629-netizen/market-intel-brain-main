"""
Data Quality Gateway - Enterprise-Grade Validation Layer

Strict schema validation layer that ensures AI engine never receives
null values, broken JSONs, or unstandardized metrics.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union, Literal
from dataclasses import dataclass, field
from enum import Enum
import uuid
from pydantic import BaseModel, Field, validator, ConfigDict

from ..ai_data_pipeline import AIMarketPrice, AINewsArticle, AISentimentData


class QualityLevel(Enum):
    """Data quality levels for AI consumption."""
    HIGH = "high"           # Excellent quality, ready for AI
    MEDIUM = "medium"       # Acceptable quality, minor issues
    LOW = "low"           # Poor quality, use with caution
    REJECTED = "rejected"   # Unusable quality, reject completely


class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Individual validation issue."""
    field: str
    severity: ValidationSeverity
    message: str
    value: Any = None
    expected: Any = None


@dataclass
class ValidationResult:
    """Result of data quality validation."""
    is_valid: bool
    quality_level: QualityLevel
    issues: List[ValidationIssue] = field(default_factory=list)
    processing_time_ms: float = 0.0
    validation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def add_issue(self, field: str, severity: ValidationSeverity, message: str, value: Any = None, expected: Any = None):
        """Add a validation issue."""
        self.issues.append(ValidationIssue(field, severity, message, value, expected))
        
        # Update quality level based on severity
        if severity == ValidationSeverity.CRITICAL:
            self.quality_level = QualityLevel.REJECTED
            self.is_valid = False
        elif severity == ValidationSeverity.ERROR:
            if self.quality_level in [QualityLevel.HIGH, QualityLevel.MEDIUM]:
                self.quality_level = QualityLevel.LOW
                self.is_valid = False
        elif severity == ValidationSeverity.WARNING:
            if self.quality_level == QualityLevel.HIGH:
                self.quality_level = QualityLevel.MEDIUM


class IValidator(ABC):
    """Abstract validator interface."""
    
    @abstractmethod
    async def validate(self, data: Any) -> ValidationResult:
        """Validate data and return result."""
        pass


class MarketPriceValidator(IValidator):
    """Validator for market price data."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("MarketPriceValidator")
    
    async def validate(self, data: AIMarketPrice) -> ValidationResult:
        """Validate market price data."""
        start_time = datetime.now()
        result = ValidationResult(is_valid=True, quality_level=QualityLevel.HIGH)
        
        try:
            # Validate symbol
            if not data.symbol or not data.symbol.strip():
                result.add_issue("symbol", ValidationSeverity.CRITICAL, "Symbol cannot be empty", data.symbol)
            elif len(data.symbol) > 20:
                result.add_issue("symbol", ValidationSeverity.WARNING, "Symbol unusually long", data.symbol, "<=20 chars")
            elif not data.symbol.isalpha():
                result.add_issue("symbol", ValidationSeverity.WARNING, "Symbol contains non-alphabetic characters", data.symbol)
            
            # Validate price
            if data.price is None:
                result.add_issue("price", ValidationSeverity.CRITICAL, "Price cannot be null", data.price)
            elif not isinstance(data.price, (int, float)):
                result.add_issue("price", ValidationSeverity.ERROR, "Price must be numeric", data.price, "numeric")
            elif data.price <= 0:
                result.add_issue("price", ValidationSeverity.ERROR, "Price must be positive", data.price, ">0")
            elif data.price > 1000000:  # $1M+ seems unusual
                result.add_issue("price", ValidationSeverity.WARNING, "Price seems unusually high", data.price)
            
            # Validate change
            if data.change is not None:
                if not isinstance(data.change, (int, float)):
                    result.add_issue("change", ValidationSeverity.ERROR, "Change must be numeric", data.change, "numeric")
                elif abs(data.change) > data.price * 0.5:  # More than 50% change
                    result.add_issue("change", ValidationSeverity.WARNING, "Change seems unusually large", data.change)
            
            # Validate change_percent
            if data.change_percent is not None:
                if not isinstance(data.change_percent, (int, float)):
                    result.add_issue("change_percent", ValidationSeverity.ERROR, "Change percent must be numeric", data.change_percent, "numeric")
                elif abs(data.change_percent) > 50:  # More than 50% change
                    result.add_issue("change_percent", ValidationSeverity.WARNING, "Change percent seems unusually large", data.change_percent)
            
            # Validate volume
            if data.volume is not None:
                if not isinstance(data.volume, (int, float)):
                    result.add_issue("volume", ValidationSeverity.ERROR, "Volume must be numeric", data.volume, "numeric")
                elif data.volume < 0:
                    result.add_issue("volume", ValidationSeverity.ERROR, "Volume cannot be negative", data.volume, ">=0")
            
            # Validate market status
            valid_statuses = ["open", "closed", "pre_market", "after_hours"]
            if data.market_status not in valid_statuses:
                result.add_issue("market_status", ValidationSeverity.ERROR, "Invalid market status", data.market_status, valid_statuses)
            
            # Validate currency
            if not data.currency or len(data.currency) != 3:
                result.add_issue("currency", ValidationSeverity.ERROR, "Currency must be 3-character code", data.currency, "3 chars")
            elif not data.currency.isalpha():
                result.add_issue("currency", ValidationSeverity.ERROR, "Currency must be alphabetic", data.currency)
            
            # Validate confidence
            if data.confidence is None:
                result.add_issue("confidence", ValidationSeverity.ERROR, "Confidence cannot be null", data.confidence)
            elif not isinstance(data.confidence, (int, float)):
                result.add_issue("confidence", ValidationSeverity.ERROR, "Confidence must be numeric", data.confidence, "numeric")
            elif not 0 <= data.confidence <= 1:
                result.add_issue("confidence", ValidationSeverity.ERROR, "Confidence must be between 0 and 1", data.confidence, "0-1")
            
            # Validate timestamp
            try:
                if data.timestamp:
                    timestamp = datetime.fromisoformat(data.timestamp.replace('Z', '+00:00'))
                    if timestamp > datetime.now(timezone.utc):
                        result.add_issue("timestamp", ValidationSeverity.WARNING, "Timestamp is in the future", data.timestamp)
            except (ValueError, AttributeError):
                result.add_issue("timestamp", ValidationSeverity.ERROR, "Invalid timestamp format", data.timestamp, "ISO format")
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            result.add_issue("validation", ValidationSeverity.CRITICAL, f"Validation failed: {str(e)}")
        
        # Calculate processing time
        result.processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return result


class NewsArticleValidator(IValidator):
    """Validator for news article data."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("NewsArticleValidator")
    
    async def validate(self, data: AINewsArticle) -> ValidationResult:
        """Validate news article data."""
        start_time = datetime.now()
        result = ValidationResult(is_valid=True, quality_level=QualityLevel.HIGH)
        
        try:
            # Validate title
            if not data.title or not data.title.strip():
                result.add_issue("title", ValidationSeverity.CRITICAL, "Title cannot be empty", data.title)
            elif len(data.title) < 5:
                result.add_issue("title", ValidationSeverity.ERROR, "Title too short", data.title, ">=5 chars")
            elif len(data.title) > 500:
                result.add_issue("title", ValidationSeverity.WARNING, "Title unusually long", data.title, "<=500 chars")
            
            # Validate summary
            if data.summary is not None:
                if len(data.summary) > 1000:
                    result.add_issue("summary", ValidationSeverity.WARNING, "Summary unusually long", data.summary, "<=1000 chars")
            
            # Validate sentiment score
            if data.sentiment_score is None:
                result.add_issue("sentiment_score", ValidationSeverity.ERROR, "Sentiment score cannot be null", data.sentiment_score)
            elif not isinstance(data.sentiment_score, (int, float)):
                result.add_issue("sentiment_score", ValidationSeverity.ERROR, "Sentiment score must be numeric", data.sentiment_score, "numeric")
            elif not -1 <= data.sentiment_score <= 1:
                result.add_issue("sentiment_score", ValidationSeverity.ERROR, "Sentiment score must be between -1 and 1", data.sentiment_score, "-1 to 1")
            
            # Validate sentiment label
            valid_labels = ["positive", "negative", "neutral", "mixed"]
            if data.sentiment_label not in valid_labels:
                result.add_issue("sentiment_label", ValidationSeverity.ERROR, "Invalid sentiment label", data.sentiment_label, valid_labels)
            
            # Check sentiment consistency
            if data.sentiment_score is not None and data.sentiment_label:
                score = data.sentiment_score
                label = data.sentiment_label
                if score > 0.3 and label != "positive":
                    result.add_issue("sentiment_consistency", ValidationSeverity.WARNING, "Sentiment label inconsistent with score", f"score={score}, label={label}")
                elif score < -0.3 and label != "negative":
                    result.add_issue("sentiment_consistency", ValidationSeverity.WARNING, "Sentiment label inconsistent with score", f"score={score}, label={label}")
            
            # Validate relevance score
            if data.relevance_score is None:
                result.add_issue("relevance_score", ValidationSeverity.ERROR, "Relevance score cannot be null", data.relevance_score)
            elif not isinstance(data.relevance_score, (int, float)):
                result.add_issue("relevance_score", ValidationSeverity.ERROR, "Relevance score must be numeric", data.relevance_score, "numeric")
            elif not 0 <= data.relevance_score <= 1:
                result.add_issue("relevance_score", ValidationSeverity.ERROR, "Relevance score must be between 0 and 1", data.relevance_score, "0-1")
            
            # Validate category
            if not data.category or not data.category.strip():
                result.add_issue("category", ValidationSeverity.ERROR, "Category cannot be empty", data.category)
            elif len(data.category) > 50:
                result.add_issue("category", ValidationSeverity.WARNING, "Category unusually long", data.category, "<=50 chars")
            
            # Validate confidence
            if data.confidence is None:
                result.add_issue("confidence", ValidationSeverity.ERROR, "Confidence cannot be null", data.confidence)
            elif not isinstance(data.confidence, (int, float)):
                result.add_issue("confidence", ValidationSeverity.ERROR, "Confidence must be numeric", data.confidence, "numeric")
            elif not 0 <= data.confidence <= 1:
                result.add_issue("confidence", ValidationSeverity.ERROR, "Confidence must be between 0 and 1", data.confidence, "0-1")
            
            # Validate timestamp
            try:
                if data.timestamp:
                    timestamp = datetime.fromisoformat(data.timestamp.replace('Z', '+00:00'))
                    if timestamp > datetime.now(timezone.utc):
                        result.add_issue("timestamp", ValidationSeverity.WARNING, "Timestamp is in the future", data.timestamp)
            except (ValueError, AttributeError):
                result.add_issue("timestamp", ValidationSeverity.ERROR, "Invalid timestamp format", data.timestamp, "ISO format")
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            result.add_issue("validation", ValidationSeverity.CRITICAL, f"Validation failed: {str(e)}")
        
        # Calculate processing time
        result.processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return result


class SentimentDataValidator(IValidator):
    """Validator for sentiment data."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("SentimentDataValidator")
    
    async def validate(self, data: AISentimentData) -> ValidationResult:
        """Validate sentiment data."""
        start_time = datetime.now()
        result = ValidationResult(is_valid=True, quality_level=QualityLevel.HIGH)
        
        try:
            # Validate platform
            if not data.platform or not data.platform.strip():
                result.add_issue("platform", ValidationSeverity.ERROR, "Platform cannot be empty", data.platform)
            elif len(data.platform) > 50:
                result.add_issue("platform", ValidationSeverity.WARNING, "Platform name unusually long", data.platform, "<=50 chars")
            
            # Validate topic
            if not data.topic or not data.topic.strip():
                result.add_issue("topic", ValidationSeverity.ERROR, "Topic cannot be empty", data.topic)
            elif len(data.topic) > 100:
                result.add_issue("topic", ValidationSeverity.WARNING, "Topic unusually long", data.topic, "<=100 chars")
            
            # Validate overall sentiment
            if data.overall_sentiment is None:
                result.add_issue("overall_sentiment", ValidationSeverity.ERROR, "Overall sentiment cannot be null", data.overall_sentiment)
            elif not isinstance(data.overall_sentiment, (int, float)):
                result.add_issue("overall_sentiment", ValidationSeverity.ERROR, "Overall sentiment must be numeric", data.overall_sentiment, "numeric")
            elif not -1 <= data.overall_sentiment <= 1:
                result.add_issue("overall_sentiment", ValidationSeverity.ERROR, "Overall sentiment must be between -1 and 1", data.overall_sentiment, "-1 to 1")
            
            # Validate sentiment label
            valid_labels = ["positive", "negative", "neutral", "mixed"]
            if data.sentiment_label not in valid_labels:
                result.add_issue("sentiment_label", ValidationSeverity.ERROR, "Invalid sentiment label", data.sentiment_label, valid_labels)
            
            # Check sentiment consistency
            if data.overall_sentiment is not None and data.sentiment_label:
                score = data.overall_sentiment
                label = data.sentiment_label
                if score > 0.3 and label != "positive":
                    result.add_issue("sentiment_consistency", ValidationSeverity.WARNING, "Sentiment label inconsistent with score", f"score={score}, label={label}")
                elif score < -0.3 and label != "negative":
                    result.add_issue("sentiment_consistency", ValidationSeverity.WARNING, "Sentiment label inconsistent with score", f"score={score}, label={label}")
            
            # Validate confidence
            if data.confidence is None:
                result.add_issue("confidence", ValidationSeverity.ERROR, "Confidence cannot be null", data.confidence)
            elif not isinstance(data.confidence, (int, float)):
                result.add_issue("confidence", ValidationSeverity.ERROR, "Confidence must be numeric", data.confidence, "numeric")
            elif not 0 <= data.confidence <= 1:
                result.add_issue("confidence", ValidationSeverity.ERROR, "Confidence must be between 0 and 1", data.confidence, "0-1")
            
            # Validate engagement score
            if data.engagement_score is not None:
                if not isinstance(data.engagement_score, (int, float)):
                    result.add_issue("engagement_score", ValidationSeverity.ERROR, "Engagement score must be numeric", data.engagement_score, "numeric")
                elif not 0 <= data.engagement_score <= 1:
                    result.add_issue("engagement_score", ValidationSeverity.WARNING, "Engagement score should be between 0 and 1", data.engagement_score, "0-1")
            
            # Validate post count
            if data.post_count is not None:
                if not isinstance(data.post_count, int):
                    result.add_issue("post_count", ValidationSeverity.ERROR, "Post count must be integer", data.post_count, "integer")
                elif data.post_count < 0:
                    result.add_issue("post_count", ValidationSeverity.ERROR, "Post count cannot be negative", data.post_count, ">=0")
                elif data.post_count > 1000000:  # 1M+ posts seems unusual
                    result.add_issue("post_count", ValidationSeverity.WARNING, "Post count seems unusually high", data.post_count)
            
            # Validate timestamp
            try:
                if data.timestamp:
                    timestamp = datetime.fromisoformat(data.timestamp.replace('Z', '+00:00'))
                    if timestamp > datetime.now(timezone.utc):
                        result.add_issue("timestamp", ValidationSeverity.WARNING, "Timestamp is in the future", data.timestamp)
            except (ValueError, AttributeError):
                result.add_issue("timestamp", ValidationSeverity.ERROR, "Invalid timestamp format", data.timestamp, "ISO format")
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            result.add_issue("validation", ValidationSeverity.CRITICAL, f"Validation failed: {str(e)}")
        
        # Calculate processing time
        result.processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return result


class DataQualityGateway:
    """
    Enterprise-grade data quality gateway that ensures AI engine
    never receives null values, broken JSONs, or unstandardized metrics.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("DataQualityGateway")
        
        # Initialize validators
        self.market_price_validator = MarketPriceValidator(logger)
        self.news_article_validator = NewsArticleValidator(logger)
        self.sentiment_data_validator = SentimentDataValidator(logger)
        
        # Validation statistics
        self._validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "by_quality_level": {
                "high": 0,
                "medium": 0,
                "low": 0,
                "rejected": 0
            },
            "average_validation_time_ms": 0.0
        }
    
    async def validate_market_price(self, data: AIMarketPrice) -> ValidationResult:
        """Validate market price data."""
        try:
            result = await self.market_price_validator.validate(data)
            self._update_validation_stats(result)
            
            if result.quality_level == QualityLevel.REJECTED:
                self.logger.warning(f"❌ Market price validation rejected: {data.symbol}")
            elif result.quality_level == QualityLevel.LOW:
                self.logger.warning(f"⚠️ Market price validation low quality: {data.symbol}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Market price validation failed: {e}")
            error_result = ValidationResult(is_valid=False, quality_level=QualityLevel.REJECTED)
            error_result.add_issue("validation", ValidationSeverity.CRITICAL, f"Validation failed: {str(e)}")
            self._update_validation_stats(error_result)
            return error_result
    
    async def validate_news_article(self, data: AINewsArticle) -> ValidationResult:
        """Validate news article data."""
        try:
            result = await self.news_article_validator.validate(data)
            self._update_validation_stats(result)
            
            if result.quality_level == QualityLevel.REJECTED:
                self.logger.warning(f"❌ News article validation rejected: {data.title[:50]}...")
            elif result.quality_level == QualityLevel.LOW:
                self.logger.warning(f"⚠️ News article validation low quality: {data.title[:50]}...")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ News article validation failed: {e}")
            error_result = ValidationResult(is_valid=False, quality_level=QualityLevel.REJECTED)
            error_result.add_issue("validation", ValidationSeverity.CRITICAL, f"Validation failed: {str(e)}")
            self._update_validation_stats(error_result)
            return error_result
    
    async def validate_sentiment_data(self, data: AISentimentData) -> ValidationResult:
        """Validate sentiment data."""
        try:
            result = await self.sentiment_data_validator.validate(data)
            self._update_validation_stats(result)
            
            if result.quality_level == QualityLevel.REJECTED:
                self.logger.warning(f"❌ Sentiment data validation rejected: {data.topic}")
            elif result.quality_level == QualityLevel.LOW:
                self.logger.warning(f"⚠️ Sentiment data validation low quality: {data.topic}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Sentiment data validation failed: {e}")
            error_result = ValidationResult(is_valid=False, quality_level=QualityLevel.REJECTED)
            error_result.add_issue("validation", ValidationSeverity.CRITICAL, f"Validation failed: {str(e)}")
            self._update_validation_stats(error_result)
            return error_result
    
    async def validate_batch(
        self, 
        data_list: List[Union[AIMarketPrice, AINewsArticle, AISentimentData]]
    ) -> List[ValidationResult]:
        """Validate multiple data items in batch."""
        tasks = []
        
        for data in data_list:
            if isinstance(data, AIMarketPrice):
                tasks.append(self.validate_market_price(data))
            elif isinstance(data, AINewsArticle):
                tasks.append(self.validate_news_article(data))
            elif isinstance(data, AISentimentData):
                tasks.append(self.validate_sentiment_data(data))
            else:
                # Unknown data type
                error_result = ValidationResult(is_valid=False, quality_level=QualityLevel.REJECTED)
                error_result.add_issue("data_type", ValidationSeverity.CRITICAL, "Unknown data type")
                tasks.append(asyncio.create_task(asyncio.sleep(0, result=error_result)))
        
        return await asyncio.gather(*tasks)
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return self._validation_stats.copy()
    
    def reset_stats(self):
        """Reset validation statistics."""
        self._validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "by_quality_level": {
                "high": 0,
                "medium": 0,
                "low": 0,
                "rejected": 0
            },
            "average_validation_time_ms": 0.0
        }
    
    def _update_validation_stats(self, result: ValidationResult):
        """Update validation statistics."""
        self._validation_stats["total_validations"] += 1
        
        if result.is_valid:
            self._validation_stats["successful_validations"] += 1
        else:
            self._validation_stats["failed_validations"] += 1
        
        # Update by quality level
        quality_key = result.quality_level.value
        if quality_key in self._validation_stats["by_quality_level"]:
            self._validation_stats["by_quality_level"][quality_key] += 1
        
        # Update average validation time
        total = self._validation_stats["total_validations"]
        current_avg = self._validation_stats["average_validation_time_ms"]
        self._validation_stats["average_validation_time_ms"] = (
            (current_avg * (total - 1) + result.processing_time_ms) / total
        )


# Global gateway instance
_data_quality_gateway: Optional[DataQualityGateway] = None


def get_data_quality_gateway() -> DataQualityGateway:
    """Get or create the global data quality gateway instance."""
    global _data_quality_gateway
    if _data_quality_gateway is None:
        _data_quality_gateway = DataQualityGateway()
    return _data_quality_gateway
