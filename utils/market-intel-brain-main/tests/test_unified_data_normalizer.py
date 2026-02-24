"""
Unit Tests for Unified Data Normalizer

Comprehensive test suite to guarantee no data loss or corruption
during the transformation process.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any

from ai_integration.unified_data_normalizer import (
    UnifiedDataNormalizer,
    UnifiedMarketPrice,
    UnifiedNewsArticle,
    UnifiedSentimentData,
    DataType,
    DataQuality,
    ConfidenceLevel,
    DataSource
)


class TestUnifiedDataNormalizer:
    """Test suite for UnifiedDataNormalizer."""
    
    @pytest.fixture
    def normalizer(self):
        """Create normalizer instance for testing."""
        return UnifiedDataNormalizer()
    
    @pytest.fixture
    def sample_market_price_data(self):
        """Sample market price raw data."""
        return {
            "price": 150.25,
            "volume": 1000000,
            "bid": 150.20,
            "ask": 150.30,
            "change": 2.50,
            "change_percent": 1.69,
            "market_status": "open",
            "currency": "USD",
            "timestamp": datetime.now(timezone.utc)
        }
    
    @pytest.fixture
    def sample_news_article_data(self):
        """Sample news article raw data."""
        return {
            "title": "Stock Market Reaches New Heights",
            "content": "The stock market reached new heights today with major gains across all sectors.",
            "summary": "Markets surge to record levels",
            "author": "John Doe",
            "url": "https://example.com/news/123",
            "sentiment_score": 0.75,
            "relevance_score": 0.85,
            "category": "Markets",
            "tags": ["stocks", "finance", "trading"],
            "language": "en",
            "timestamp": datetime.now(timezone.utc)
        }
    
    @pytest.fixture
    def sample_sentiment_data(self):
        """Sample sentiment analysis raw data."""
        return {
            "overall_sentiment": 0.65,
            "confidence": 0.80,
            "emotions": {
                "joy": 0.3,
                "trust": 0.4,
                "fear": 0.2,
                "surprise": 0.1
            },
            "engagement": {
                "likes": 500,
                "shares": 200,
                "comments": 50
            },
            "platform": "twitter",
            "topic": "AAPL",
            "language": "en",
            "timestamp": datetime.now(timezone.utc)
        }
    
    @pytest.mark.asyncio
    async def test_normalize_market_price_success(self, normalizer, sample_market_price_data):
        """Test successful market price normalization."""
        result = await normalizer.normalize_market_price(
            sample_market_price_data,
            DataSource.BINANCE,
            "BTCUSDT"
        )
        
        # Verify type and structure
        assert isinstance(result, UnifiedMarketPrice)
        assert result.data_type == DataType.MARKET_PRICE
        assert result.source == DataSource.BINANCE
        assert result.symbol == "BTCUSDT"
        
        # Verify data integrity
        assert float(result.price) == 150.25
        assert float(result.volume) == 1000000
        assert float(result.bid) == 150.20
        assert float(result.ask) == 150.30
        assert float(result.change) == 2.50
        assert float(result.change_percent) == 1.69
        assert result.market_status == "open"
        assert result.currency == "USD"
        
        # Verify metadata
        assert result.processing_metadata.source_system == "BINANCE"
        assert result.processing_metadata.data_quality in DataQuality
        assert result.processing_metadata.confidence_level in ConfidenceLevel
        assert result.processing_metadata.token_estimate > 0
        
        # Verify raw data preservation
        assert result.raw_data == sample_market_price_data
        
        # Verify statistics update
        stats = normalizer.get_normalization_stats()
        assert stats["total_processed"] == 1
        assert stats["successful_normalizations"] == 1
        assert stats["failed_normalizations"] == 0
    
    @pytest.mark.asyncio
    async def test_normalize_news_article_success(self, normalizer, sample_news_article_data):
        """Test successful news article normalization."""
        result = await normalizer.normalize_news_article(
            sample_news_article_data,
            DataSource.YAHOO_FINANCE,
            "AAPL"
        )
        
        # Verify type and structure
        assert isinstance(result, UnifiedNewsArticle)
        assert result.data_type == DataType.NEWS_ARTICLE
        assert result.source == DataSource.YAHOO_FINANCE
        assert result.symbol == "AAPL"
        
        # Verify data integrity
        assert result.title == "Stock Market Reaches New Heights"
        assert result.content == "The stock market reached new heights today with major gains across all sectors."
        assert result.summary == "Markets surge to record levels"
        assert result.author == "John Doe"
        assert result.url == "https://example.com/news/123"
        assert float(result.sentiment_score) == 0.75
        assert result.sentiment_label == "positive"
        assert float(result.relevance_score) == 0.85
        assert result.category == "Markets"
        assert result.tags == ["stocks", "finance", "trading"]
        assert result.language == "en"
        
        # Verify metadata
        assert result.processing_metadata.source_system == "YAHOO_FINANCE"
        assert result.processing_metadata.data_quality in DataQuality
        assert result.processing_metadata.confidence_level in ConfidenceLevel
        assert result.processing_metadata.token_estimate > 0
        
        # Verify raw data preservation
        assert result.raw_data == sample_news_article_data
    
    @pytest.mark.asyncio
    async def test_normalize_sentiment_data_success(self, normalizer, sample_sentiment_data):
        """Test successful sentiment data normalization."""
        result = await normalizer.normalize_sentiment_data(
            sample_sentiment_data,
            DataSource.FINNHUB,
            "AAPL"
        )
        
        # Verify type and structure
        assert isinstance(result, UnifiedSentimentData)
        assert result.data_type == DataType.SENTIMENT_DATA
        assert result.source == DataSource.FINNHUB
        assert result.symbol == "AAPL"
        
        # Verify data integrity
        assert float(result.overall_sentiment) == 0.65
        assert result.sentiment_label == "positive"
        assert float(result.confidence) == 0.80
        assert len(result.emotions) == 4
        assert float(result.emotions["joy"]) == 0.3
        assert float(result.emotions["trust"]) == 0.4
        assert float(result.emotions["fear"]) == 0.2
        assert float(result.emotions["surprise"]) == 0.1
        assert len(result.engagement_metrics) == 3
        assert result.engagement_metrics["likes"] == 500
        assert result.engagement_metrics["shares"] == 200
        assert result.engagement_metrics["comments"] == 50
        assert result.platform == "twitter"
        assert result.topic == "AAPL"
        assert result.language == "en"
        
        # Verify metadata
        assert result.processing_metadata.source_system == "FINNHUB"
        assert result.processing_metadata.data_quality in DataQuality
        assert result.processing_metadata.confidence_level in ConfidenceLevel
        assert result.processing_metadata.token_estimate > 0
        
        # Verify raw data preservation
        assert result.raw_data == sample_sentiment_data
    
    @pytest.mark.asyncio
    async def test_normalize_market_price_missing_required_field(self, normalizer):
        """Test normalization failure with missing required field."""
        incomplete_data = {
            "volume": 1000000,
            "currency": "USD"
            # Missing price field
        }
        
        with pytest.raises(ValueError, match="No price field found"):
            await normalizer.normalize_market_price(
                incomplete_data,
                DataSource.BINANCE,
                "BTCUSDT"
            )
        
        # Verify statistics update
        stats = normalizer.get_normalization_stats()
        assert stats["total_processed"] == 1
        assert stats["successful_normalizations"] == 0
        assert stats["failed_normalizations"] == 1
    
    @pytest.mark.asyncio
    async def test_normalize_news_article_missing_required_field(self, normalizer):
        """Test normalization failure with missing required field."""
        incomplete_data = {
            "content": "Some content",
            "sentiment_score": 0.5
            # Missing title field
        }
        
        with pytest.raises(ValueError, match="No title field found"):
            await normalizer.normalize_news_article(
                incomplete_data,
                DataSource.YAHOO_FINANCE,
                "AAPL"
            )
        
        # Verify statistics update
        stats = normalizer.get_normalization_stats()
        assert stats["total_processed"] == 1
        assert stats["successful_normalizations"] == 0
        assert stats["failed_normalizations"] == 1
    
    @pytest.mark.asyncio
    async def test_normalize_sentiment_data_missing_required_field(self, normalizer):
        """Test normalization failure with missing required field."""
        incomplete_data = {
            "platform": "twitter",
            "language": "en"
            # Missing overall_sentiment field
        }
        
        # This should not raise an error as overall_sentiment has a default
        result = await normalizer.normalize_sentiment_data(
            incomplete_data,
            DataSource.FINNHUB,
            "AAPL"
        )
        
        # Verify default value is used
        assert float(result.overall_sentiment) == 0.0
        assert result.sentiment_label == "neutral"
    
    @pytest.mark.asyncio
    async def test_price_validation_bid_ask_relationship(self, normalizer):
        """Test bid-ask relationship validation."""
        invalid_data = {
            "price": 150.25,
            "bid": 150.30,  # Bid higher than price - should fail
            "ask": 150.20,  # Ask lower than price - should fail
            "currency": "USD"
        }
        
        with pytest.raises(ValueError, match="Bid price cannot be higher than market price"):
            await normalizer.normalize_market_price(
                invalid_data,
                DataSource.BINANCE,
                "BTCUSDT"
            )
    
    @pytest.mark.asyncio
    async def test_sentiment_score_validation(self, normalizer):
        """Test sentiment score validation."""
        invalid_data = {
            "title": "Test Article",
            "content": "Test content",
            "sentiment_score": 1.5,  # Invalid: > 1.0
            "category": "Test"
        }
        
        with pytest.raises(ValueError, match="sentiment_score"):
            await normalizer.normalize_news_article(
                invalid_data,
                DataSource.YAHOO_FINANCE,
                "AAPL"
            )
    
    @pytest.mark.asyncio
    async def test_emotions_sum_validation(self, normalizer):
        """Test emotion scores sum validation."""
        invalid_data = {
            "overall_sentiment": 0.5,
            "emotions": {
                "joy": 0.6,
                "trust": 0.6  # Sum > 1.0 - should fail
            },
            "platform": "twitter",
            "topic": "test"
        }
        
        with pytest.raises(ValueError, match="Emotion scores should sum to approximately 1.0"):
            await normalizer.normalize_sentiment_data(
                invalid_data,
                DataSource.FINNHUB,
                "AAPL"
            )
    
    @pytest.mark.asyncio
    async def test_timestamp_future_validation(self, normalizer):
        """Test timestamp validation prevents future dates."""
        future_timestamp = datetime.now(timezone.utc).replace(year=2100)
        invalid_data = {
            "price": 150.25,
            "currency": "USD",
            "timestamp": future_timestamp
        }
        
        with pytest.raises(ValueError, match="Timestamp cannot be in the future"):
            await normalizer.normalize_market_price(
                invalid_data,
                DataSource.BINANCE,
                "BTCUSDT",
                timestamp=future_timestamp
            )
    
    @pytest.mark.asyncio
    async def test_symbol_format_validation(self, normalizer):
        """Test symbol format validation."""
        invalid_data = {
            "price": 150.25,
            "currency": "USD"
        }
        
        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            await normalizer.normalize_market_price(
                invalid_data,
                DataSource.BINANCE,
                ""  # Empty symbol
            )
    
    @pytest.mark.asyncio
    async def test_data_quality_assessment(self, normalizer):
        """Test data quality assessment."""
        # High quality data
        high_quality_data = {
            "price": 150.25,
            "volume": 1000000,
            "bid": 150.20,
            "ask": 150.30,
            "change": 2.50,
            "change_percent": 1.69,
            "market_status": "open",
            "currency": "USD",
            "timestamp": datetime.now(timezone.utc),
            "additional_field": "extra_data"
        }
        
        result = await normalizer.normalize_market_price(
            high_quality_data,
            DataSource.BINANCE,
            "BTCUSDT"
        )
        
        assert result.processing_metadata.data_quality == DataQuality.HIGH
        
        # Low quality data
        low_quality_data = {
            "price": 150.25
            # Minimal data
        }
        
        result = await normalizer.normalize_market_price(
            low_quality_data,
            DataSource.BINANCE,
            "BTCUSDT"
        )
        
        assert result.processing_metadata.data_quality == DataQuality.LOW
    
    @pytest.mark.asyncio
    async def test_confidence_assessment_by_source(self, normalizer):
        """Test confidence assessment based on data source."""
        data = {
            "price": 150.25,
            "currency": "USD"
        }
        
        # High confidence source
        result_binance = await normalizer.normalize_market_price(
            data,
            DataSource.BINANCE,
            "BTCUSDT"
        )
        
        # Medium confidence source
        result_alpha = await normalizer.normalize_market_price(
            data,
            DataSource.ALPHA_VANTAGE,
            "AAPL"
        )
        
        assert result_binance.processing_metadata.confidence_level.value >= result_alpha.processing_metadata.confidence_level.value
    
    @pytest.mark.asyncio
    async def test_token_estimation(self, normalizer):
        """Test token estimation accuracy."""
        data = {
            "price": 150.25,
            "volume": 1000000,
            "currency": "USD",
            "additional_field": "Some additional text content for token estimation"
        }
        
        result = await normalizer.normalize_market_price(
            data,
            DataSource.BINANCE,
            "BTCUSDT"
        )
        
        # Token estimate should be reasonable
        assert result.processing_metadata.token_estimate > 0
        assert result.processing_metadata.token_estimate < 1000  # Should not be excessive
    
    @pytest.mark.asyncio
    async def test_processing_latency_tracking(self, normalizer):
        """Test processing latency tracking."""
        data = {
            "price": 150.25,
            "currency": "USD"
        }
        
        result = await normalizer.normalize_market_price(
            data,
            DataSource.BINANCE,
            "BTCUSDT"
        )
        
        # Processing latency should be reasonable
        assert result.processing_metadata.processing_latency_ms >= 0
        assert result.processing_metadata.processing_latency_ms < 1000  # Should complete within 1 second
    
    @pytest.mark.asyncio
    async def test_multiple_normalizations_statistics(self, normalizer):
        """Test statistics tracking across multiple normalizations."""
        data = {
            "price": 150.25,
            "currency": "USD"
        }
        
        # Perform multiple normalizations
        for i in range(5):
            await normalizer.normalize_market_price(
                data,
                DataSource.BINANCE,
                f"SYMBOL{i}"
            )
        
        stats = normalizer.get_normalization_stats()
        
        assert stats["total_processed"] == 5
        assert stats["successful_normalizations"] == 5
        assert stats["failed_normalizations"] == 0
        assert stats["average_processing_time_ms"] > 0
        assert "market_price" in stats["by_data_type"]
        assert "BINANCE" in stats["by_source"]
    
    @pytest.mark.asyncio
    async def test_data_type_specific_statistics(self, normalizer):
        """Test statistics tracking by data type."""
        market_data = {"price": 150.25, "currency": "USD"}
        news_data = {
            "title": "Test News",
            "content": "Test content",
            "sentiment_score": 0.5,
            "category": "Test"
        }
        
        # Normalize different data types
        await normalizer.normalize_market_price(market_data, DataSource.BINANCE, "BTCUSDT")
        await normalizer.normalize_news_article(news_data, DataSource.YAHOO_FINANCE, "AAPL")
        
        stats = normalizer.get_normalization_stats()
        
        assert stats["by_data_type"]["market_price"]["processed"] == 1
        assert stats["by_data_type"]["news_article"]["processed"] == 1
        assert stats["by_source"]["BINANCE"]["processed"] == 1
        assert stats["by_source"]["YAHOO_FINANCE"]["processed"] == 1
    
    def test_global_normalizer_singleton(self):
        """Test global normalizer singleton pattern."""
        from ai_integration.unified_data_normalizer import get_unified_normalizer
        
        # Get normalizer twice - should return same instance
        normalizer1 = get_unified_normalizer()
        normalizer2 = get_unified_normalizer()
        
        assert normalizer1 is normalizer2
        assert isinstance(normalizer1, UnifiedDataNormalizer)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
