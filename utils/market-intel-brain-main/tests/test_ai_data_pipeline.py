"""
Unit Tests for AI Data Pipeline

Comprehensive test suite for AI data pipeline functionality,
token tracking, and compression optimization.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any

from ai_integration.ai_data_pipeline import (
    AIDataPipeline,
    TokenUsageTracker,
    AIMarketPrice,
    AINewsArticle,
    AISentimentData,
    AIModelType,
    DataCompressionLevel,
    TokenBudget,
    get_ai_data_pipeline
)
from ai_integration.unified_data_normalizer import (
    UnifiedMarketPrice,
    UnifiedNewsArticle,
    UnifiedSentimentData,
    DataSource,
    DataType
)


class TestTokenUsageTracker:
    """Test suite for TokenUsageTracker."""
    
    @pytest.fixture
    def tracker(self):
        """Create token tracker instance for testing."""
        return TokenUsageTracker()
    
    def test_track_token_usage_basic(self, tracker):
        """Test basic token usage tracking."""
        metrics = tracker.track_token_usage(
            input_tokens=100,
            output_tokens=20,
            model_type=AIModelType.GPT_3_5_TURBO
        )
        
        assert metrics.input_tokens == 100
        assert metrics.output_tokens == 20
        assert metrics.total_tokens == 120
        assert metrics.model_type == AIModelType.GPT_3_5_TURBO
        assert metrics.estimated_cost_usd > 0
    
    def test_track_token_usage_different_models(self, tracker):
        """Test token usage tracking with different models."""
        gpt4_metrics = tracker.track_token_usage(
            input_tokens=100,
            model_type=AIModelType.GPT_4
        )
        
        gpt35_metrics = tracker.track_token_usage(
            input_tokens=100,
            model_type=AIModelType.GPT_3_5_TURBO
        )
        
        # GPT-4 should be more expensive
        assert gpt4_metrics.estimated_cost_usd > gpt35_metrics.estimated_cost_usd
    
    def test_estimate_tokens_from_text(self, tracker):
        """Test token estimation from text."""
        text = "This is a sample text for token estimation."
        tokens = tracker.estimate_tokens_from_text(text)
        
        assert tokens > 0
        assert tokens < len(text)  # Tokens should be less than characters
    
    def test_estimate_tokens_from_data(self, tracker):
        """Test token estimation from structured data."""
        data = {
            "price": 150.25,
            "volume": 1000000,
            "symbol": "BTCUSDT"
        }
        
        tokens = tracker.estimate_tokens_from_data(data)
        assert tokens > 0
    
    def test_get_daily_usage_empty(self, tracker):
        """Test daily usage when no usage recorded."""
        daily_usage = tracker.get_daily_usage()
        
        assert daily_usage["total_tokens"] == 0
        assert daily_usage["total_cost"] == 0.0
        assert daily_usage["operations"] == 0
        assert daily_usage["budget_remaining"] > 0
    
    def test_get_daily_usage_with_data(self, tracker):
        """Test daily usage with recorded data."""
        # Add some usage
        tracker.track_token_usage(100, 20, AIModelType.GPT_3_5_TURBO)
        tracker.track_token_usage(200, 30, AIModelType.GPT_3_5_TURBO)
        
        daily_usage = tracker.get_daily_usage()
        
        assert daily_usage["total_tokens"] == 350
        assert daily_usage["total_cost"] > 0
        assert daily_usage["operations"] == 2
    
    def test_get_usage_by_model(self, tracker):
        """Test usage breakdown by model."""
        # Add usage for different models
        tracker.track_token_usage(100, 20, AIModelType.GPT_4)
        tracker.track_token_usage(200, 30, AIModelType.GPT_3_5_TURBO)
        tracker.track_token_usage(150, 25, AIModelType.CLAUDE)
        
        usage_by_model = tracker.get_usage_by_model()
        
        assert "gpt-4" in usage_by_model
        assert "gpt-3.5-turbo" in usage_by_model
        assert "claude" in usage_by_model
        
        assert usage_by_model["gpt-4"]["operations"] == 1
        assert usage_by_model["gpt-3.5-turbo"]["operations"] == 1
        assert usage_by_model["claude"]["operations"] == 1
    
    def test_set_daily_budget_limit(self, tracker):
        """Test setting daily budget limit."""
        tracker.set_daily_budget_limit(50.0)
        
        # Verify the limit is set
        daily_usage = tracker.get_daily_usage()
        assert daily_usage["budget_remaining"] == 50.0
    
    def test_set_alert_thresholds(self, tracker):
        """Test setting alert thresholds."""
        tracker.set_alert_thresholds(daily_spend=25.0, token_burst=1000)
        
        # Verify thresholds are set (access through private attribute for testing)
        assert tracker._alert_thresholds["daily_spend"] == 25.0
        assert tracker._alert_thresholds["token_burst"] == 1000


class TestAIDataPipeline:
    """Test suite for AIDataPipeline."""
    
    @pytest.fixture
    def pipeline(self):
        """Create AI data pipeline instance for testing."""
        return AIDataPipeline(
            compression_level=DataCompressionLevel.STANDARD,
            token_budget=TokenBudget.STANDARD,
            model_type=AIModelType.GPT_3_5_TURBO
        )
    
    @pytest.fixture
    def sample_unified_market_price(self):
        """Sample unified market price data."""
        return UnifiedMarketPrice(
            data_id="test_123",
            data_type=DataType.MARKET_PRICE,
            source=DataSource.BINANCE,
            symbol="BTCUSDT",
            timestamp=datetime.now(timezone.utc),
            price=Decimal("150.25"),
            volume=Decimal("1000000"),
            bid=Decimal("150.20"),
            ask=Decimal("150.30"),
            change=Decimal("2.50"),
            change_percent=Decimal("1.69"),
            market_status="open",
            currency="USD",
            processing_metadata=None,  # Will be set in actual implementation
            raw_data={}
        )
    
    @pytest.fixture
    def sample_unified_news_article(self):
        """Sample unified news article data."""
        return UnifiedNewsArticle(
            data_id="news_123",
            data_type=DataType.NEWS_ARTICLE,
            source=DataSource.YAHOO_FINANCE,
            symbol="AAPL",
            timestamp=datetime.now(timezone.utc),
            title="Stock Market Reaches New Heights",
            content="The stock market reached new heights today with major gains across all sectors.",
            summary="Markets surge to record levels",
            author="John Doe",
            url="https://example.com/news/123",
            sentiment_score=Decimal("0.75"),
            sentiment_label="positive",
            relevance_score=Decimal("0.85"),
            category="Markets",
            tags=["stocks", "finance", "trading"],
            language="en",
            processing_metadata=None,
            raw_data={}
        )
    
    @pytest.fixture
    def sample_unified_sentiment_data(self):
        """Sample unified sentiment data."""
        return UnifiedSentimentData(
            data_id="sentiment_123",
            data_type=DataType.SENTIMENT_DATA,
            source=DataSource.FINNHUB,
            symbol="AAPL",
            timestamp=datetime.now(timezone.utc),
            overall_sentiment=Decimal("0.65"),
            sentiment_label="positive",
            confidence=Decimal("0.80"),
            emotions={
                "joy": Decimal("0.3"),
                "trust": Decimal("0.4"),
                "fear": Decimal("0.2"),
                "surprise": Decimal("0.1")
            },
            engagement_metrics={
                "likes": 500,
                "shares": 200,
                "comments": 50
            },
            platform="twitter",
            topic="AAPL",
            language="en",
            processing_metadata=None,
            raw_data={}
        )
    
    @pytest.mark.asyncio
    async def test_transform_market_price_minimal(self, pipeline, sample_unified_market_price):
        """Test market price transformation with minimal compression."""
        # Set processing metadata for the sample
        from ai_integration.unified_data_normalizer import ProcessingMetadata, DataQuality, ConfidenceLevel
        sample_unified_market_price.processing_metadata = ProcessingMetadata(
            source_system="BINANCE",
            original_timestamp=datetime.now(timezone.utc),
            data_quality=DataQuality.HIGH,
            confidence_level=ConfidenceLevel.VERY_HIGH
        )
        
        result = await pipeline.transform_market_price(
            sample_unified_market_price,
            compression_level=DataCompressionLevel.MINIMAL
        )
        
        # Verify type and structure
        assert isinstance(result, AIMarketPrice)
        assert result.symbol == "BTCUSDT"
        assert result.price == 150.25
        assert result.change == 2.5
        assert result.change_percent == 1.69
        assert result.market_status == "open"
        assert result.currency == "USD"
        
        # Verify compression level (minimal shouldn't include volume)
        assert result.volume is None
        assert result.confidence == 0.95  # VERY_HIGH
        assert result.source == "BINANCE"
    
    @pytest.mark.asyncio
    async def test_transform_market_price_standard(self, pipeline, sample_unified_market_price):
        """Test market price transformation with standard compression."""
        # Set processing metadata for the sample
        from ai_integration.unified_data_normalizer import ProcessingMetadata, DataQuality, ConfidenceLevel
        sample_unified_market_price.processing_metadata = ProcessingMetadata(
            source_system="BINANCE",
            original_timestamp=datetime.now(timezone.utc),
            data_quality=DataQuality.HIGH,
            confidence_level=ConfidenceLevel.VERY_HIGH
        )
        
        result = await pipeline.transform_market_price(
            sample_unified_market_price,
            compression_level=DataCompressionLevel.STANDARD
        )
        
        # Verify standard compression includes volume
        assert result.volume == 1000000.0
        assert result.confidence == 0.95
        assert result.source == "BINANCE"
    
    @pytest.mark.asyncio
    async def test_transform_news_article_minimal(self, pipeline, sample_unified_news_article):
        """Test news article transformation with minimal compression."""
        # Set processing metadata for the sample
        from ai_integration.unified_data_normalizer import ProcessingMetadata, DataQuality, ConfidenceLevel
        sample_unified_news_article.processing_metadata = ProcessingMetadata(
            source_system="YAHOO_FINANCE",
            original_timestamp=datetime.now(timezone.utc),
            data_quality=DataQuality.HIGH,
            confidence_level=ConfidenceLevel.HIGH
        )
        
        result = await pipeline.transform_news_article(
            sample_unified_news_article,
            compression_level=DataCompressionLevel.MINIMAL
        )
        
        # Verify type and structure
        assert isinstance(result, AINewsArticle)
        assert result.title == "Stock Market Reaches New Heights"
        assert result.sentiment_score == 0.75
        assert result.sentiment_label == "positive"
        assert result.relevance_score == 0.85
        assert result.category == "Markets"
        
        # Verify minimal compression (no summary)
        assert result.summary is None
        assert result.confidence == 0.85  # HIGH
        assert result.source == "YAHOO_FINANCE"
    
    @pytest.mark.asyncio
    async def test_transform_news_article_standard(self, pipeline, sample_unified_news_article):
        """Test news article transformation with standard compression."""
        # Set processing metadata for the sample
        from ai_integration.unified_data_normalizer import ProcessingMetadata, DataQuality, ConfidenceLevel
        sample_unified_news_article.processing_metadata = ProcessingMetadata(
            source_system="YAHOO_FINANCE",
            original_timestamp=datetime.now(timezone.utc),
            data_quality=DataQuality.HIGH,
            confidence_level=ConfidenceLevel.HIGH
        )
        
        result = await pipeline.transform_news_article(
            sample_unified_news_article,
            compression_level=DataCompressionLevel.STANDARD
        )
        
        # Verify standard compression includes summary
        assert result.summary == "Markets surge to record levels"
        assert result.confidence == 0.85
        assert result.source == "YAHOO_FINANCE"
    
    @pytest.mark.asyncio
    async def test_transform_sentiment_data(self, pipeline, sample_unified_sentiment_data):
        """Test sentiment data transformation."""
        # Set processing metadata for the sample
        from ai_integration.unified_data_normalizer import ProcessingMetadata, DataQuality, ConfidenceLevel
        sample_unified_sentiment_data.processing_metadata = ProcessingMetadata(
            source_system="FINNHUB",
            original_timestamp=datetime.now(timezone.utc),
            data_quality=DataQuality.MEDIUM,
            confidence_level=ConfidenceLevel.MEDIUM
        )
        
        result = await pipeline.transform_sentiment_data(
            sample_unified_sentiment_data
        )
        
        # Verify type and structure
        assert isinstance(result, AISentimentData)
        assert result.platform == "twitter"
        assert result.topic == "AAPL"
        assert result.overall_sentiment == 0.65
        assert result.sentiment_label == "positive"
        assert result.confidence == 0.80
        
        # Verify engagement score calculation
        assert result.engagement_score is not None
        assert result.post_count == 3  # likes, shares, comments
        assert result.source == "FINNHUB"
    
    @pytest.mark.asyncio
    async def test_process_raw_to_ai_market_price(self, pipeline):
        """Test processing raw data directly to AI format."""
        raw_data = {
            "price": 150.25,
            "volume": 1000000,
            "currency": "USD",
            "market_status": "open"
        }
        
        result = await pipeline.process_raw_to_ai(
            raw_data,
            DataType.MARKET_PRICE,
            DataSource.BINANCE,
            "BTCUSDT"
        )
        
        assert isinstance(result, AIMarketPrice)
        assert result.symbol == "BTCUSDT"
        assert result.price == 150.25
        assert result.source == "BINANCE"
    
    @pytest.mark.asyncio
    async def test_process_raw_to_ai_news_article(self, pipeline):
        """Test processing raw news data directly to AI format."""
        raw_data = {
            "title": "Test News",
            "content": "Test content",
            "sentiment_score": 0.5,
            "category": "Test"
        }
        
        result = await pipeline.process_raw_to_ai(
            raw_data,
            DataType.NEWS_ARTICLE,
            DataSource.YAHOO_FINANCE,
            "AAPL"
        )
        
        assert isinstance(result, AINewsArticle)
        assert result.title == "Test News"
        assert result.source == "YAHOO_FINANCE"
    
    @pytest.mark.asyncio
    async def test_process_raw_to_ai_sentiment_data(self, pipeline):
        """Test processing raw sentiment data directly to AI format."""
        raw_data = {
            "overall_sentiment": 0.5,
            "platform": "twitter",
            "topic": "test"
        }
        
        result = await pipeline.process_raw_to_ai(
            raw_data,
            DataType.SENTIMENT_DATA,
            DataSource.FINNHUB,
            "AAPL"
        )
        
        assert isinstance(result, AISentimentData)
        assert result.platform == "twitter"
        assert result.source == "FINNHUB"
    
    def test_get_pipeline_stats(self, pipeline):
        """Test pipeline statistics retrieval."""
        stats = pipeline.get_pipeline_stats()
        
        assert "total_processed" in stats
        assert "successful_transformations" in stats
        assert "failed_transformations" in stats
        assert "tokens_saved" in stats
        assert "compression_ratio" in stats
    
    def test_get_token_usage_stats(self, pipeline):
        """Test token usage statistics retrieval."""
        stats = pipeline.get_token_usage_stats()
        
        assert "current_session" in stats
        assert "daily_usage" in stats
        assert "usage_by_model" in stats
        assert "pipeline_compression" in stats
    
    @pytest.mark.asyncio
    async def test_token_tracking_integration(self, pipeline, sample_unified_market_price):
        """Test token tracking integration with pipeline."""
        # Set processing metadata for the sample
        from ai_integration.unified_data_normalizer import ProcessingMetadata, DataQuality, ConfidenceLevel
        sample_unified_market_price.processing_metadata = ProcessingMetadata(
            source_system="BINANCE",
            original_timestamp=datetime.now(timezone.utc),
            data_quality=DataQuality.HIGH,
            confidence_level=ConfidenceLevel.VERY_HIGH
        )
        
        # Transform data
        await pipeline.transform_market_price(sample_unified_market_price)
        
        # Check token usage was tracked
        token_stats = pipeline.get_token_usage_stats()
        assert token_stats["current_session"]["total_tokens"] > 0
        assert token_stats["current_session"]["estimated_cost_usd"] > 0
    
    @pytest.mark.asyncio
    async def test_compression_effectiveness(self, pipeline, sample_unified_news_article):
        """Test compression effectiveness."""
        # Set processing metadata for the sample
        from ai_integration.unified_data_normalizer import ProcessingMetadata, DataQuality, ConfidenceLevel
        sample_unified_news_article.processing_metadata = ProcessingMetadata(
            source_system="YAHOO_FINANCE",
            original_timestamp=datetime.now(timezone.utc),
            data_quality=DataQuality.HIGH,
            confidence_level=ConfidenceLevel.HIGH
        )
        
        # Transform with different compression levels
        minimal_result = await pipeline.transform_news_article(
            sample_unified_news_article,
            compression_level=DataCompressionLevel.MINIMAL
        )
        
        standard_result = await pipeline.transform_news_article(
            sample_unified_news_article,
            compression_level=DataCompressionLevel.STANDARD
        )
        
        comprehensive_result = await pipeline.transform_news_article(
            sample_unified_news_article,
            compression_level=DataCompressionLevel.COMPREHENSIVE
        )
        
        # Verify compression levels
        assert minimal_result.summary is None
        assert standard_result.summary is not None
        assert comprehensive_result.summary is not None
        
        # All should have the same core data
        assert minimal_result.title == standard_result.title == comprehensive_result.title
        assert minimal_result.sentiment_score == standard_result.sentiment_score == comprehensive_result.sentiment_score
    
    def test_global_pipeline_singleton(self):
        """Test global pipeline singleton pattern."""
        pipeline1 = get_ai_data_pipeline()
        pipeline2 = get_ai_data_pipeline()
        
        assert pipeline1 is pipeline2
        assert isinstance(pipeline1, AIDataPipeline)
    
    def test_pipeline_initialization_options(self):
        """Test pipeline initialization with different options."""
        conservative_pipeline = AIDataPipeline(
            compression_level=DataCompressionLevel.MINIMAL,
            token_budget=TokenBudget.CONSERVATIVE,
            model_type=AIModelType.GPT_4
        )
        
        assert conservative_pipeline.compression_level == DataCompressionLevel.MINIMAL
        assert conservative_pipeline.token_budget == TokenBudget.CONSERVATIVE
        assert conservative_pipeline.model_type == AIModelType.GPT_4


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
