"""
AI Data Pipeline - Optimized for LLM Token Efficiency

Enterprise-grade data pipeline that transforms unified data into AI-optimized
formats with minimal token consumption and maximum information density.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, Union, Literal
from dataclasses import dataclass, field
from enum import Enum
import uuid
from pydantic import BaseModel, Field, validator, ConfigDict

from .unified_data_normalizer import (
    UnifiedData, UnifiedMarketPrice, UnifiedNewsArticle, UnifiedSentimentData,
    get_unified_normalizer, DataType
)
from services.schemas.market_data import DataSource


class AIModelType(Enum):
    """Supported AI model types with different token limits."""
    GPT_4 = "gpt-4"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    CLAUDE = "claude"
    GEMINI = "gemini"
    LOCAL_LLAMA = "local-llama"


class DataCompressionLevel(Enum):
    """Data compression levels for token optimization."""
    MINIMAL = "minimal"      # Essential fields only
    STANDARD = "standard"    # Balanced information
    COMPREHENSIVE = "comprehensive"  # Full details


class TokenBudget(Enum):
    """Token budget configurations."""
    CONSERVATIVE = 1000    # For cost-sensitive operations
    STANDARD = 4000        # Standard operations
    EXTENSIVE = 8000       # For comprehensive analysis


@dataclass
class TokenUsageMetrics:
    """Token usage metrics for cost tracking."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    model_type: AIModelType = AIModelType.GPT_3_5_TURBO
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def add_tokens(self, input_tokens: int, output_tokens: int = 0):
        """Add tokens to metrics."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens += input_tokens + output_tokens
        self.estimated_cost_usd = self._calculate_cost()
    
    def _calculate_cost(self) -> float:
        """Calculate estimated cost based on model pricing."""
        # Pricing per 1K tokens (approximate)
        pricing = {
            AIModelType.GPT_4: {"input": 0.03, "output": 0.06},
            AIModelType.GPT_3_5_TURBO: {"input": 0.0015, "output": 0.002},
            AIModelType.CLAUDE: {"input": 0.008, "output": 0.024},
            AIModelType.GEMINI: {"input": 0.0005, "output": 0.0015},
            AIModelType.LOCAL_LLAMA: {"input": 0.0, "output": 0.0}  # Free for local
        }
        
        model_pricing = pricing.get(self.model_type, pricing[AIModelType.GPT_3_5_TURBO])
        
        input_cost = (self.input_tokens / 1000) * model_pricing["input"]
        output_cost = (self.output_tokens / 1000) * model_pricing["output"]
        
        return input_cost + output_cost


# Pydantic Models for AI-Ready Data
class AIMarketPrice(BaseModel):
    """AI-optimized market price data with minimal token usage."""
    model_config = ConfigDict(strict=True, validate_assignment=True)
    
    # Essential fields only
    symbol: str = Field(..., description="Trading symbol")
    price: float = Field(..., description="Current price")
    change: Optional[float] = Field(None, description="Price change")
    change_percent: Optional[float] = Field(None, description="Percentage change")
    volume: Optional[float] = Field(None, description="Trading volume")
    market_status: str = Field(..., description="Market status")
    currency: str = Field(..., description="Currency")
    
    # Quality indicators
    confidence: float = Field(..., ge=0, le=1, description="Data confidence")
    source: str = Field(..., description="Data source")
    timestamp: str = Field(..., description="ISO timestamp")
    
    @validator('price', 'change', 'change_percent', 'volume')
    @classmethod
    def convert_decimal_to_float(cls, v):
        """Convert Decimal to float for JSON serialization."""
        if isinstance(v, Decimal):
            return float(v)
        return v


class AINewsArticle(BaseModel):
    """AI-optimized news article data with minimal token usage."""
    model_config = ConfigDict(strict=True, validate_assignment=True)
    
    # Essential fields only
    title: str = Field(..., description="Article title")
    summary: Optional[str] = Field(None, description="Article summary")
    sentiment_score: float = Field(..., ge=-1, le=1, description="Sentiment score")
    sentiment_label: str = Field(..., description="Sentiment label")
    relevance_score: float = Field(..., ge=0, le=1, description="Relevance score")
    category: str = Field(..., description="News category")
    
    # Quality indicators
    confidence: float = Field(..., ge=0, le=1, description="Data confidence")
    source: str = Field(..., description="Data source")
    timestamp: str = Field(..., description="ISO timestamp")
    
    @validator('sentiment_score', 'relevance_score', 'confidence')
    @classmethod
    def convert_decimal_to_float(cls, v):
        """Convert Decimal to float for JSON serialization."""
        if isinstance(v, Decimal):
            return float(v)
        return v


class AISentimentData(BaseModel):
    """AI-optimized sentiment data with minimal token usage."""
    model_config = ConfigDict(strict=True, validate_assignment=True)
    
    # Essential fields only
    platform: str = Field(..., description="Social media platform")
    topic: str = Field(..., description="Topic or keyword")
    overall_sentiment: float = Field(..., ge=-1, le=1, description="Overall sentiment")
    sentiment_label: str = Field(..., description="Sentiment label")
    confidence: float = Field(..., ge=0, le=1, description="Confidence level")
    
    # Engagement metrics (compressed)
    engagement_score: Optional[float] = Field(None, description="Overall engagement score")
    post_count: Optional[int] = Field(None, description="Number of posts analyzed")
    
    # Quality indicators
    source: str = Field(..., description="Data source")
    timestamp: str = Field(..., description="ISO timestamp")
    
    @validator('overall_sentiment', 'confidence', 'engagement_score')
    @classmethod
    def convert_decimal_to_float(cls, v):
        """Convert Decimal to float for JSON serialization."""
        if isinstance(v, Decimal):
            return float(v)
        return v


# Type alias for AI-ready data types
AIReadyData = Union[
    AIMarketPrice,
    AINewsArticle,
    AISentimentData
]


class TokenUsageTracker:
    """
    Enterprise-grade token usage tracker for cost monitoring and optimization.
    
    Tracks token consumption across all AI operations and provides cost estimates.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("TokenUsageTracker")
        self._usage_history: List[TokenUsageMetrics] = []
        self._current_session_metrics = TokenUsageMetrics()
        self._daily_budget_limit = 100.0  # Default daily budget in USD
        self._alert_thresholds = {
            "daily_spend": 50.0,
            "hourly_spend": 10.0,
            "token_burst": 5000
        }
        
        # Model pricing per 1K tokens (USD)
        self._model_pricing = {
            AIModelType.GPT_4: {"input": 0.03, "output": 0.06},
            AIModelType.GPT_3_5_TURBO: {"input": 0.0015, "output": 0.002},
            AIModelType.CLAUDE: {"input": 0.008, "output": 0.024},
            AIModelType.GEMINI: {"input": 0.0005, "output": 0.0015},
            AIModelType.LOCAL_LLAMA: {"input": 0.0, "output": 0.0}
        }
    
    def track_token_usage(
        self,
        input_tokens: int,
        output_tokens: int = 0,
        model_type: AIModelType = AIModelType.GPT_3_5_TURBO,
        operation_id: Optional[str] = None
    ) -> TokenUsageMetrics:
        """
        Track token usage for an operation.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model_type: AI model type
            operation_id: Optional operation identifier
            
        Returns:
            Token usage metrics
        """
        metrics = TokenUsageMetrics(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_type=model_type
        )
        
        # Add tokens and calculate cost
        metrics.add_tokens(input_tokens, output_tokens)
        
        # Add to history
        self._usage_history.append(metrics)
        self._current_session_metrics.add_tokens(input_tokens, output_tokens)
        
        # Check alerts
        self._check_alerts(metrics)
        
        # Log usage
        self.logger.info(
            f"Token usage tracked: {input_tokens} input, {output_tokens} output, "
            f"${metrics.estimated_cost_usd:.4f} cost ({model_type.value})"
        )
        
        return metrics
    
    def estimate_tokens_from_text(self, text: str) -> int:
        """
        Estimate token count from text.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Rough estimation: 1 token ≈ 4 characters for English text
        # Add 10% buffer for safety
        return max(1, int(len(text) / 4 * 1.1))
    
    def estimate_tokens_from_data(self, data: Union[Dict[str, Any], List[Any]]) -> int:
        """
        Estimate token count from structured data.
        
        Args:
            data: Data to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Convert to JSON string and estimate
        json_str = json.dumps(data, default=str, separators=(',', ':'))
        return self.estimate_tokens_from_text(json_str)
    
    def get_current_session_metrics(self) -> TokenUsageMetrics:
        """Get current session token usage metrics."""
        return self._current_session_metrics
    
    def get_daily_usage(self) -> Dict[str, Any]:
        """Get daily token usage summary."""
        today = datetime.now(timezone.utc).date()
        daily_usage = [
            metrics for metrics in self._usage_history
            if metrics.timestamp.date() == today
        ]
        
        if not daily_usage:
            return {
                "date": today.isoformat(),
                "total_tokens": 0,
                "total_cost": 0.0,
                "operations": 0
            }
        
        total_tokens = sum(m.total_tokens for m in daily_usage)
        total_cost = sum(m.estimated_cost_usd for m in daily_usage)
        
        return {
            "date": today.isoformat(),
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "operations": len(daily_usage),
            "budget_remaining": max(0, self._daily_budget_limit - total_cost),
            "budget_utilization": (total_cost / self._daily_budget_limit) * 100
        }
    
    def get_usage_by_model(self) -> Dict[str, Any]:
        """Get token usage breakdown by model type."""
        model_usage = {}
        
        for metrics in self._usage_history:
            model = metrics.model_type.value
            if model not in model_usage:
                model_usage[model] = {
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "operations": 0
                }
            
            model_usage[model]["total_tokens"] += metrics.total_tokens
            model_usage[model]["total_cost"] += metrics.estimated_cost_usd
            model_usage[model]["operations"] += 1
        
        return model_usage
    
    def set_daily_budget_limit(self, limit_usd: float):
        """Set daily budget limit in USD."""
        self._daily_budget_limit = limit_usd
        self.logger.info(f"Daily budget limit set to ${limit_usd:.2f}")
    
    def set_alert_thresholds(self, **thresholds):
        """Set alert thresholds for cost monitoring."""
        self._alert_thresholds.update(thresholds)
        self.logger.info(f"Alert thresholds updated: {thresholds}")
    
    def _check_alerts(self, metrics: TokenUsageMetrics):
        """Check if any alert thresholds are exceeded."""
        daily_usage = self.get_daily_usage()
        
        # Check daily spend threshold
        if daily_usage["total_cost"] > self._alert_thresholds["daily_spend"]:
            self.logger.warning(
                f"🚨 Daily spend alert: ${daily_usage['total_cost']:.2f} "
                f"(threshold: ${self._alert_thresholds['daily_spend']:.2f})"
            )
        
        # Check token burst threshold
        if metrics.total_tokens > self._alert_thresholds["token_burst"]:
            self.logger.warning(
                f"🚨 Token burst alert: {metrics.total_tokens} tokens "
                f"(threshold: {self._alert_thresholds['token_burst']})"
            )
        
        # Check budget utilization
        if daily_usage["budget_utilization"] > 80:
            self.logger.warning(
                f"🚨 Budget utilization alert: {daily_usage['budget_utilization']:.1f}% "
                f"of daily budget used"
            )


class AIDataPipeline:
    """
    Enterprise-grade AI data pipeline optimized for LLM token efficiency.
    
    Transforms unified data into AI-ready formats with minimal token consumption
    and maximum information density.
    """
    
    def __init__(
        self,
        compression_level: DataCompressionLevel = DataCompressionLevel.STANDARD,
        token_budget: TokenBudget = TokenBudget.STANDARD,
        model_type: AIModelType = AIModelType.GPT_3_5_TURBO,
        logger: Optional[logging.Logger] = None
    ):
        self.compression_level = compression_level
        self.token_budget = token_budget
        self.model_type = model_type
        self.logger = logger or logging.getLogger("AIDataPipeline")
        
        # Initialize components
        self.normalizer = get_unified_normalizer()
        self.token_tracker = TokenUsageTracker(logger)
        
        # Pipeline statistics
        self._pipeline_stats = {
            "total_processed": 0,
            "successful_transformations": 0,
            "failed_transformations": 0,
            "tokens_saved": 0,
            "compression_ratio": 0.0
        }
        
        self.logger.info(
            f"AIDataPipeline initialized: {compression_level.value} compression, "
            f"{token_budget.value} budget, {model_type.value} model"
        )
    
    async def transform_market_price(
        self,
        unified_data: UnifiedMarketPrice,
        compression_level: Optional[DataCompressionLevel] = None
    ) -> AIMarketPrice:
        """
        Transform unified market price data to AI-optimized format.
        
        Args:
            unified_data: Unified market price data
            compression_level: Override default compression level
            
        Returns:
            AI-optimized market price data
        """
        compression_level = compression_level or self.compression_level
        
        try:
            # Create AI-optimized data based on compression level
            if compression_level == DataCompressionLevel.MINIMAL:
                ai_data = AIMarketPrice(
                    symbol=unified_data.symbol,
                    price=float(unified_data.price),
                    change=float(unified_data.change) if unified_data.change else None,
                    change_percent=float(unified_data.change_percent) if unified_data.change_percent else None,
                    market_status=unified_data.market_status,
                    currency=unified_data.currency,
                    confidence=float(unified_data.processing_metadata.confidence_level.value),
                    source=unified_data.source.value,
                    timestamp=unified_data.timestamp.isoformat()
                )
            elif compression_level == DataCompressionLevel.STANDARD:
                ai_data = AIMarketPrice(
                    symbol=unified_data.symbol,
                    price=float(unified_data.price),
                    change=float(unified_data.change) if unified_data.change else None,
                    change_percent=float(unified_data.change_percent) if unified_data.change_percent else None,
                    volume=float(unified_data.volume) if unified_data.volume else None,
                    market_status=unified_data.market_status,
                    currency=unified_data.currency,
                    confidence=float(unified_data.processing_metadata.confidence_level.value),
                    source=unified_data.source.value,
                    timestamp=unified_data.timestamp.isoformat()
                )
            else:  # COMPREHENSIVE
                ai_data = AIMarketPrice(
                    symbol=unified_data.symbol,
                    price=float(unified_data.price),
                    change=float(unified_data.change) if unified_data.change else None,
                    change_percent=float(unified_data.change_percent) if unified_data.change_percent else None,
                    volume=float(unified_data.volume) if unified_data.volume else None,
                    market_status=unified_data.market_status,
                    currency=unified_data.currency,
                    confidence=float(unified_data.processing_metadata.confidence_level.value),
                    source=unified_data.source.value,
                    timestamp=unified_data.timestamp.isoformat()
                )
            
            # Track token usage
            original_tokens = self.token_tracker.estimate_tokens_from_data(unified_data.dict())
            compressed_tokens = self.token_tracker.estimate_tokens_from_data(ai_data.dict())
            tokens_saved = original_tokens - compressed_tokens
            
            self.token_tracker.track_token_usage(
                input_tokens=compressed_tokens,
                model_type=self.model_type,
                operation_id=f"market_price_{unified_data.symbol}"
            )
            
            # Update statistics
            self._update_pipeline_stats("market_price", True, tokens_saved, original_tokens, compressed_tokens)
            
            self.logger.debug(
                f"✅ Transformed market price: {unified_data.symbol} "
                f"({tokens_saved} tokens saved, {compressed_tokens} tokens used)"
            )
            
            return ai_data
            
        except Exception as e:
            self._update_pipeline_stats("market_price", False, 0, 0, 0)
            self.logger.error(f"❌ Failed to transform market price: {e}")
            raise
    
    async def transform_news_article(
        self,
        unified_data: UnifiedNewsArticle,
        compression_level: Optional[DataCompressionLevel] = None
    ) -> AINewsArticle:
        """
        Transform unified news article data to AI-optimized format.
        
        Args:
            unified_data: Unified news article data
            compression_level: Override default compression level
            
        Returns:
            AI-optimized news article data
        """
        compression_level = compression_level or self.compression_level
        
        try:
            # Create AI-optimized data based on compression level
            if compression_level == DataCompressionLevel.MINIMAL:
                ai_data = AINewsArticle(
                    title=unified_data.title,
                    sentiment_score=float(unified_data.sentiment_score),
                    sentiment_label=unified_data.sentiment_label,
                    relevance_score=float(unified_data.relevance_score),
                    category=unified_data.category,
                    confidence=float(unified_data.processing_metadata.confidence_level.value),
                    source=unified_data.source.value,
                    timestamp=unified_data.timestamp.isoformat()
                )
            elif compression_level == DataCompressionLevel.STANDARD:
                ai_data = AINewsArticle(
                    title=unified_data.title,
                    summary=unified_data.summary,
                    sentiment_score=float(unified_data.sentiment_score),
                    sentiment_label=unified_data.sentiment_label,
                    relevance_score=float(unified_data.relevance_score),
                    category=unified_data.category,
                    confidence=float(unified_data.processing_metadata.confidence_level.value),
                    source=unified_data.source.value,
                    timestamp=unified_data.timestamp.isoformat()
                )
            else:  # COMPREHENSIVE
                ai_data = AINewsArticle(
                    title=unified_data.title,
                    summary=unified_data.summary,
                    sentiment_score=float(unified_data.sentiment_score),
                    sentiment_label=unified_data.sentiment_label,
                    relevance_score=float(unified_data.relevance_score),
                    category=unified_data.category,
                    confidence=float(unified_data.processing_metadata.confidence_level.value),
                    source=unified_data.source.value,
                    timestamp=unified_data.timestamp.isoformat()
                )
            
            # Track token usage
            original_tokens = self.token_tracker.estimate_tokens_from_data(unified_data.dict())
            compressed_tokens = self.token_tracker.estimate_tokens_from_data(ai_data.dict())
            tokens_saved = original_tokens - compressed_tokens
            
            self.token_tracker.track_token_usage(
                input_tokens=compressed_tokens,
                model_type=self.model_type,
                operation_id=f"news_article_{unified_data.data_id[:8]}"
            )
            
            # Update statistics
            self._update_pipeline_stats("news_article", True, tokens_saved, original_tokens, compressed_tokens)
            
            self.logger.debug(
                f"✅ Transformed news article: {unified_data.title[:30]}... "
                f"({tokens_saved} tokens saved, {compressed_tokens} tokens used)"
            )
            
            return ai_data
            
        except Exception as e:
            self._update_pipeline_stats("news_article", False, 0, 0, 0)
            self.logger.error(f"❌ Failed to transform news article: {e}")
            raise
    
    async def transform_sentiment_data(
        self,
        unified_data: UnifiedSentimentData,
        compression_level: Optional[DataCompressionLevel] = None
    ) -> AISentimentData:
        """
        Transform unified sentiment data to AI-optimized format.
        
        Args:
            unified_data: Unified sentiment data
            compression_level: Override default compression level
            
        Returns:
            AI-optimized sentiment data
        """
        compression_level = compression_level or self.compression_level
        
        try:
            # Calculate engagement score from metrics
            engagement_score = None
            post_count = None
            if unified_data.engagement_metrics:
                # Simple engagement score calculation
                total_engagement = sum(unified_data.engagement_metrics.values())
                engagement_score = min(1.0, total_engagement / 1000)  # Normalize to 0-1
                post_count = len(unified_data.engagement_metrics)
            
            # Create AI-optimized data
            ai_data = AISentimentData(
                platform=unified_data.platform,
                topic=unified_data.topic,
                overall_sentiment=float(unified_data.overall_sentiment),
                sentiment_label=unified_data.sentiment_label,
                confidence=float(unified_data.confidence),
                engagement_score=engagement_score,
                post_count=post_count,
                source=unified_data.source.value,
                timestamp=unified_data.timestamp.isoformat()
            )
            
            # Track token usage
            original_tokens = self.token_tracker.estimate_tokens_from_data(unified_data.dict())
            compressed_tokens = self.token_tracker.estimate_tokens_from_data(ai_data.dict())
            tokens_saved = original_tokens - compressed_tokens
            
            self.token_tracker.track_token_usage(
                input_tokens=compressed_tokens,
                model_type=self.model_type,
                operation_id=f"sentiment_data_{unified_data.data_id[:8]}"
            )
            
            # Update statistics
            self._update_pipeline_stats("sentiment_data", True, tokens_saved, original_tokens, compressed_tokens)
            
            self.logger.debug(
                f"✅ Transformed sentiment data: {unified_data.topic} "
                f"({tokens_saved} tokens saved, {compressed_tokens} tokens used)"
            )
            
            return ai_data
            
        except Exception as e:
            self._update_pipeline_stats("sentiment_data", False, 0, 0, 0)
            self.logger.error(f"❌ Failed to transform sentiment data: {e}")
            raise
    
    async def process_raw_to_ai(
        self,
        raw_data: Dict[str, Any],
        data_type: DataType,
        source: DataSource,
        symbol: Optional[str] = None,
        compression_level: Optional[DataCompressionLevel] = None
    ) -> AIReadyData:
        """
        Process raw data directly to AI-ready format (bypassing unified normalization).
        
        Args:
            raw_data: Raw data from source
            data_type: Type of data
            source: Data source
            symbol: Trading symbol (optional)
            compression_level: Compression level override
            
        Returns:
            AI-ready data
        """
        try:
            # First normalize to unified format
            if data_type == DataType.MARKET_PRICE:
                unified_data = await self.normalizer.normalize_market_price(
                    raw_data, source, symbol or "UNKNOWN"
                )
                ai_data = await self.transform_market_price(unified_data, compression_level)
            elif data_type == DataType.NEWS_ARTICLE:
                unified_data = await self.normalizer.normalize_news_article(
                    raw_data, source, symbol
                )
                ai_data = await self.transform_news_article(unified_data, compression_level)
            elif data_type == DataType.SENTIMENT_DATA:
                unified_data = await self.normalizer.normalize_sentiment_data(
                    raw_data, source, symbol
                )
                ai_data = await self.transform_sentiment_data(unified_data, compression_level)
            else:
                raise ValueError(f"Unsupported data type: {data_type}")
            
            return ai_data
            
        except Exception as e:
            self.logger.error(f"❌ Failed to process raw to AI: {e}")
            raise
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline transformation statistics."""
        return self._pipeline_stats.copy()
    
    def get_token_usage_stats(self) -> Dict[str, Any]:
        """Get comprehensive token usage statistics."""
        return {
            "current_session": self.token_tracker.get_current_session_metrics().__dict__,
            "daily_usage": self.token_tracker.get_daily_usage(),
            "usage_by_model": self.token_tracker.get_usage_by_model(),
            "pipeline_compression": {
                "total_tokens_saved": self._pipeline_stats["tokens_saved"],
                "average_compression_ratio": self._pipeline_stats["compression_ratio"]
            }
        }
    
    def _update_pipeline_stats(
        self,
        data_type: str,
        success: bool,
        tokens_saved: int,
        original_tokens: int,
        compressed_tokens: int
    ):
        """Update pipeline transformation statistics."""
        self._pipeline_stats["total_processed"] += 1
        
        if success:
            self._pipeline_stats["successful_transformations"] += 1
            self._pipeline_stats["tokens_saved"] += tokens_saved
        else:
            self._pipeline_stats["failed_transformations"] += 1
        
        # Update compression ratio
        if self._pipeline_stats["successful_transformations"] > 0:
            total_original = sum([
                self.token_tracker.estimate_tokens_from_data({"dummy": "data"}) 
                for _ in range(self._pipeline_stats["successful_transformations"])
            ])
            total_compressed = sum([
                self.token_tracker.estimate_tokens_from_data({"dummy": "data"}) 
                for _ in range(self._pipeline_stats["successful_transformations"])
            ])
            
            if total_original > 0:
                self._pipeline_stats["compression_ratio"] = (
                    (total_original - total_compressed) / total_original
                ) * 100


# Global pipeline instance
_ai_data_pipeline: Optional[AIDataPipeline] = None


def get_ai_data_pipeline(
    compression_level: DataCompressionLevel = DataCompressionLevel.STANDARD,
    token_budget: TokenBudget = TokenBudget.STANDARD,
    model_type: AIModelType = AIModelType.GPT_3_5_TURBO
) -> AIDataPipeline:
    """Get or create the global AI data pipeline instance."""
    global _ai_data_pipeline
    if _ai_data_pipeline is None:
        _ai_data_pipeline = AIDataPipeline(
            compression_level=compression_level,
            token_budget=token_budget,
            model_type=model_type
        )
    return _ai_data_pipeline
