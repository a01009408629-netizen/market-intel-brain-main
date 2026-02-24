"""
AI-Ready Endpoints - Enterprise-Grade REST/GraphQL API

Strictly optimized endpoints that consume UnifiedDataNormalizer output
and deliver token-efficient payloads for AI consumption.
"""

import asyncio
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

from fastapi import APIRouter, HTTPException, Query, Path, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator, ConfigDict
try:
    from fastapi.middleware.base import BaseHTTPMiddleware
except ImportError:
    # Fallback for older FastAPI versions
    from starlette.middleware.base import BaseHTTPMiddleware

from ..unified_data_normalizer import (
    get_unified_normalizer,
    UnifiedData,
    UnifiedMarketPrice,
    UnifiedNewsArticle,
    UnifiedSentimentData,
    DataType,
    DataSource
)
from ..ai_data_pipeline import (
    get_ai_data_pipeline,
    AIReadyData,
    AIMarketPrice,
    AINewsArticle,
    AISentimentData,
    DataCompressionLevel,
    TokenBudget
)
from .data_quality_gateway import get_data_quality_gateway, ValidationResult, QualityLevel


class ResponseFormat(str, Enum):
    """Response format options."""
    JSON = "json"
    MINIMAL = "minimal"
    COMPRESSED = "compressed"


@dataclass
class EndpointMetrics:
    """Endpoint performance metrics."""
    endpoint: str
    method: str
    execution_time_ms: float
    status_code: int
    token_count: int
    timestamp: datetime
    warning_threshold_exceeded: bool = False


# Pydantic Models for AI-Ready Responses (Zero Token Waste)
class AIMarketPriceResponse(BaseModel):
    """Ultra-optimized market price response for AI consumption."""
    model_config = ConfigDict(strict=True, validate_assignment=True)
    
    # Essential fields only - zero waste
    s: str = Field(..., description="Symbol")  # Shortened field name
    p: float = Field(..., description="Price")  # Shortened field name
    c: Optional[float] = Field(None, description="Change")  # Shortened field name
    cp: Optional[float] = Field(None, description="Change percent")  # Shortened field name
    v: Optional[float] = Field(None, description="Volume")  # Shortened field name
    ms: str = Field(..., description="Market status")  # Shortened field name
    cur: str = Field(..., description="Currency")  # Shortened field name
    conf: float = Field(..., ge=0, le=1, description="Confidence")  # Shortened field name
    ts: str = Field(..., description="Timestamp")  # Shortened field name
    
    @validator('conf')
    @classmethod
    def validate_confidence_range(cls, v):
        """Validate confidence is in valid range."""
        if not 0 <= v <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        return v


class AINewsArticleResponse(BaseModel):
    """Ultra-optimized news article response for AI consumption."""
    model_config = ConfigDict(strict=True, validate_assignment=True)
    
    # Essential fields only - zero waste
    t: str = Field(..., description="Title")  # Shortened field name
    s: Optional[str] = Field(None, description="Summary")  # Shortened field name
    ss: float = Field(..., ge=-1, le=1, description="Sentiment score")  # Shortened field name
    sl: str = Field(..., description="Sentiment label")  # Shortened field name
    rs: float = Field(..., ge=0, le=1, description="Relevance score")  # Shortened field name
    cat: str = Field(..., description="Category")  # Shortened field name
    conf: float = Field(..., ge=0, le=1, description="Confidence")  # Shortened field name
    ts: str = Field(..., description="Timestamp")  # Shortened field name
    
    @validator('ss')
    @classmethod
    def validate_sentiment_score(cls, v):
        """Validate sentiment score range."""
        if not -1 <= v <= 1:
            raise ValueError("Sentiment score must be between -1 and 1")
        return v
    
    @validator('rs')
    @classmethod
    def validate_relevance_score(cls, v):
        """Validate relevance score range."""
        if not 0 <= v <= 1:
            raise ValueError("Relevance score must be between 0 and 1")
        return v


class AISentimentDataResponse(BaseModel):
    """Ultra-optimized sentiment data response for AI consumption."""
    model_config = ConfigDict(strict=True, validate_assignment=True)
    
    # Essential fields only - zero waste
    plat: str = Field(..., description="Platform")  # Shortened field name
    top: str = Field(..., description="Topic")  # Shortened field name
    os: float = Field(..., ge=-1, le=1, description="Overall sentiment")  # Shortened field name
    sl: str = Field(..., description="Sentiment label")  # Shortened field name
    conf: float = Field(..., ge=0, le=1, description="Confidence")  # Shortened field name
    es: Optional[float] = Field(None, description="Engagement score")  # Shortened field name
    pc: Optional[int] = Field(None, description="Post count")  # Shortened field name
    ts: str = Field(..., description="Timestamp")  # Shortened field name
    
    @validator('os')
    @classmethod
    def validate_overall_sentiment(cls, v):
        """Validate overall sentiment range."""
        if not -1 <= v <= 1:
            raise ValueError("Overall sentiment must be between -1 and 1")
        return v


class AIErrorResponse(BaseModel):
    """Standardized error response."""
    model_config = ConfigDict(strict=True, validate_assignment=True)
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Timestamp")


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Lightweight middleware for endpoint performance monitoring."""
    
    def __init__(self, app, warning_threshold_ms: float = 200.0):
        super().__init__(app)
        self.warning_threshold_ms = warning_threshold_ms
        self.logger = logging.getLogger("PerformanceMiddleware")
        self._metrics: List[EndpointMetrics] = []
    
    async def dispatch(self, request, call_next):
        """Monitor endpoint performance."""
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate metrics
        execution_time_ms = (time.time() - start_time) * 1000
        warning_exceeded = execution_time_ms > self.warning_threshold_ms
        
        # Create metrics record
        metrics = EndpointMetrics(
            endpoint=str(request.url.path),
            method=request.method,
            execution_time_ms=execution_time_ms,
            status_code=response.status_code,
            token_count=self._estimate_tokens_from_response(response),
            timestamp=datetime.now(timezone.utc),
            warning_threshold_exceeded=warning_exceeded
        )
        
        self._metrics.append(metrics)
        
        # Log warning if threshold exceeded
        if warning_exceeded:
            self.logger.warning(
                f"⚠️ Performance Warning: {request.method} {request.url.path} "
                f"took {execution_time_ms:.2f}ms (threshold: {self.warning_threshold_ms}ms)"
            )
        
        # Add performance headers
        response.headers["X-Execution-Time"] = f"{execution_time_ms:.2f}"
        response.headers["X-Token-Count"] = str(metrics.token_count)
        
        if warning_exceeded:
            response.headers["X-Performance-Warning"] = "true"
        
        return response
    
    def _estimate_tokens_from_response(self, response) -> int:
        """Estimate token count from response."""
        if hasattr(response, 'body'):
            try:
                import json
                content = response.body.decode()
                data = json.loads(content)
                # Rough estimation: 1 token ≈ 4 characters
                return max(1, len(json.dumps(data)) // 4)
            except:
                pass
        return 1
    
    def get_metrics(self) -> List[EndpointMetrics]:
        """Get collected metrics."""
        return self._metrics.copy()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        if not self._metrics:
            return {"total_requests": 0}
        
        total_requests = len(self._metrics)
        avg_time = sum(m.execution_time_ms for m in self._metrics) / total_requests
        warnings = sum(1 for m in self._metrics if m.warning_threshold_exceeded)
        
        return {
            "total_requests": total_requests,
            "average_execution_time_ms": avg_time,
            "warnings_triggered": warnings,
            "warning_rate": (warnings / total_requests) * 100,
            "total_tokens_processed": sum(m.token_count for m in self._metrics)
        }


class AIEndpointsRouter:
    """
    Enterprise-grade AI endpoints router with strict performance requirements.
    
    All endpoints consume UnifiedDataNormalizer output and deliver
    token-efficient payloads for AI consumption.
    """
    
    def __init__(self):
        self.router = APIRouter(prefix="/api/v2/ai", tags=["AI Integration"])
        self.logger = logging.getLogger("AIEndpointsRouter")
        
        # Initialize dependencies
        self.normalizer = get_unified_normalizer()
        self.pipeline = get_ai_data_pipeline(
            compression_level=DataCompressionLevel.MINIMAL,  # Maximum token efficiency
            token_budget=TokenBudget.CONSERVATIVE
        )
        self.quality_gateway = get_data_quality_gateway()
        
        # Performance tracking
        self.performance_middleware = PerformanceMiddleware(warning_threshold_ms=200.0)
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup all AI endpoints."""
        
        @self.router.get(
            "/normalized/market/{source}/{symbol}",
            response_model=AIMarketPriceResponse,
            summary="Get AI-ready market price data",
            description="Returns ultra-optimized market price data for AI consumption"
        )
        async def get_ai_market_price(
            source: str = Path(..., description="Data source"),
            symbol: str = Path(..., description="Trading symbol"),
            format: ResponseFormat = Query(ResponseFormat.JSON, description="Response format")
        ) -> AIMarketPriceResponse:
            """Get AI-ready market price data."""
            start_time = time.time()
            
            try:
                # Validate source
                try:
                    data_source = DataSource(source.lower())
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid source: {source}. Valid sources: {[s.value for s in DataSource]}"
                    )
                
                # Get raw data (this would come from existing data fetching logic)
                raw_data = await self._fetch_market_price_data(data_source, symbol)
                
                # Normalize to unified format
                unified_data = await self.normalizer.normalize_market_price(
                    raw_data=raw_data,
                    source=data_source,
                    symbol=symbol
                )
                
                # Transform to AI-ready format
                ai_data = await self.pipeline.transform_market_price(
                    unified_data,
                    compression_level=DataCompressionLevel.MINIMAL
                )
                
                # Quality validation
                validation_result = await self.quality_gateway.validate_market_price(ai_data)
                if validation_result.quality_level == QualityLevel.REJECTED:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Data quality validation failed: {validation_result.errors}"
                    )
                
                # Create ultra-optimized response
                response = AIMarketPriceResponse(
                    s=ai_data.symbol,
                    p=ai_data.price,
                    c=ai_data.change,
                    cp=ai_data.change_percent,
                    v=ai_data.volume,
                    ms=ai_data.market_status,
                    cur=ai_data.currency,
                    conf=ai_data.confidence,
                    ts=ai_data.timestamp
                )
                
                # Log performance
                execution_time = (time.time() - start_time) * 1000
                if execution_time > 200:
                    self.logger.warning(
                        f"⚠️ Market price endpoint took {execution_time:.2f}ms for {symbol}"
                    )
                
                return response
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"❌ Market price endpoint failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Internal server error processing market price data"
                )
        
        @self.router.get(
            "/normalized/news/{source}",
            response_model=List[AINewsArticleResponse],
            summary="Get AI-ready news articles",
            description="Returns ultra-optimized news articles for AI consumption"
        )
        async def get_ai_news_articles(
            source: str = Path(..., description="Data source"),
            symbol: Optional[str] = Query(None, description="Filter by symbol"),
            category: Optional[str] = Query(None, description="Filter by category"),
            limit: int = Query(10, ge=1, le=100, description="Maximum number of articles")
        ) -> List[AINewsArticleResponse]:
            """Get AI-ready news articles."""
            start_time = time.time()
            
            try:
                # Validate source
                try:
                    data_source = DataSource(source.lower())
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid source: {source}. Valid sources: {[s.value for s in DataSource]}"
                    )
                
                # Get raw news data
                raw_articles = await self._fetch_news_articles_data(data_source, symbol, category, limit)
                
                # Process each article
                ai_responses = []
                for raw_article in raw_articles:
                    try:
                        # Normalize to unified format
                        unified_data = await self.normalizer.normalize_news_article(
                            raw_data=raw_article,
                            source=data_source,
                            symbol=symbol
                        )
                        
                        # Transform to AI-ready format
                        ai_data = await self.pipeline.transform_news_article(
                            unified_data,
                            compression_level=DataCompressionLevel.MINIMAL
                        )
                        
                        # Quality validation
                        validation_result = await self.quality_gateway.validate_news_article(ai_data)
                        if validation_result.quality_level == QualityLevel.REJECTED:
                            continue  # Skip rejected data
                        
                        # Create ultra-optimized response
                        response = AINewsArticleResponse(
                            t=ai_data.title,
                            s=ai_data.summary,
                            ss=ai_data.sentiment_score,
                            sl=ai_data.sentiment_label,
                            rs=ai_data.relevance_score,
                            cat=ai_data.category,
                            conf=ai_data.confidence,
                            ts=ai_data.timestamp
                        )
                        
                        ai_responses.append(response)
                        
                    except Exception as e:
                        self.logger.warning(f"⚠️ Failed to process article: {e}")
                        continue
                
                # Log performance
                execution_time = (time.time() - start_time) * 1000
                if execution_time > 200:
                    self.logger.warning(
                        f"⚠️ News articles endpoint took {execution_time:.2f}ms"
                    )
                
                return ai_responses
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"❌ News articles endpoint failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Internal server error processing news articles"
                )
        
        @self.router.get(
            "/normalized/sentiment/{source}",
            response_model=List[AISentimentDataResponse],
            summary="Get AI-ready sentiment data",
            description="Returns ultra-optimized sentiment data for AI consumption"
        )
        async def get_ai_sentiment_data(
            source: str = Path(..., description="Data source"),
            platform: Optional[str] = Query(None, description="Filter by platform"),
            topic: Optional[str] = Query(None, description="Filter by topic"),
            limit: int = Query(10, ge=1, le=100, description="Maximum number of data points")
        ) -> List[AISentimentDataResponse]:
            """Get AI-ready sentiment data."""
            start_time = time.time()
            
            try:
                # Validate source
                try:
                    data_source = DataSource(source.lower())
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid source: {source}. Valid sources: {[s.value for s in DataSource]}"
                    )
                
                # Get raw sentiment data
                raw_sentiment_data = await self._fetch_sentiment_data(data_source, platform, topic, limit)
                
                # Process each sentiment data point
                ai_responses = []
                for raw_data in raw_sentiment_data:
                    try:
                        # Normalize to unified format
                        unified_data = await self.normalizer.normalize_sentiment_data(
                            raw_data=raw_data,
                            source=data_source,
                            symbol=topic
                        )
                        
                        # Transform to AI-ready format
                        ai_data = await self.pipeline.transform_sentiment_data(
                            unified_data,
                            compression_level=DataCompressionLevel.MINIMAL
                        )
                        
                        # Quality validation
                        validation_result = await self.quality_gateway.validate_sentiment_data(ai_data)
                        if validation_result.quality_level == QualityLevel.REJECTED:
                            continue  # Skip rejected data
                        
                        # Create ultra-optimized response
                        response = AISentimentDataResponse(
                            plat=ai_data.platform,
                            top=ai_data.topic,
                            os=ai_data.overall_sentiment,
                            sl=ai_data.sentiment_label,
                            conf=ai_data.confidence,
                            es=ai_data.engagement_score,
                            pc=ai_data.post_count,
                            ts=ai_data.timestamp
                        )
                        
                        ai_responses.append(response)
                        
                    except Exception as e:
                        self.logger.warning(f"⚠️ Failed to process sentiment data: {e}")
                        continue
                
                # Log performance
                execution_time = (time.time() - start_time) * 1000
                if execution_time > 200:
                    self.logger.warning(
                        f"⚠️ Sentiment data endpoint took {execution_time:.2f}ms"
                    )
                
                return ai_responses
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"❌ Sentiment data endpoint failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Internal server error processing sentiment data"
                )
        
        @self.router.get(
            "/health",
            summary="AI endpoints health check",
            description="Health check for AI endpoints with performance metrics"
        )
        async def health_check() -> Dict[str, Any]:
            """Health check endpoint."""
            try:
                # Test data flow
                test_data = {"price": 100.0, "currency": "USD"}
                unified_test = await self.normalizer.normalize_market_price(
                    test_data, DataSource.BINANCE, "TEST"
                )
                ai_test = await self.pipeline.transform_market_price(unified_test)
                
                # Get performance metrics
                performance_summary = self.performance_middleware.get_performance_summary()
                
                return {
                    "status": "healthy",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data_flow_test": "passed",
                    "performance": performance_summary,
                    "token_usage": self.pipeline.get_token_usage_stats()
                }
                
            except Exception as e:
                self.logger.error(f"❌ Health check failed: {e}")
                raise HTTPException(
                    status_code=503,
                    detail="Service unavailable"
                )
    
    async def _fetch_market_price_data(self, source: DataSource, symbol: str) -> Dict[str, Any]:
        """Fetch market price data from existing data sources."""
        # This would integrate with existing data fetching logic
        # For now, return mock data for demonstration
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
    
    async def _fetch_news_articles_data(
        self, 
        source: DataSource, 
        symbol: Optional[str], 
        category: Optional[str], 
        limit: int
    ) -> List[Dict[str, Any]]:
        """Fetch news articles data from existing data sources."""
        # This would integrate with existing data fetching logic
        return [
            {
                "title": "Sample News Article",
                "content": "Sample content for testing",
                "summary": "Sample summary",
                "sentiment_score": 0.5,
                "relevance_score": 0.8,
                "category": category or "general",
                "timestamp": datetime.now(timezone.utc)
            }
            for _ in range(min(limit, 5))
        ]
    
    async def _fetch_sentiment_data(
        self, 
        source: DataSource, 
        platform: Optional[str], 
        topic: Optional[str], 
        limit: int
    ) -> List[Dict[str, Any]]:
        """Fetch sentiment data from existing data sources."""
        # This would integrate with existing data fetching logic
        return [
            {
                "overall_sentiment": 0.6,
                "confidence": 0.8,
                "platform": platform or "twitter",
                "topic": topic or "general",
                "engagement": {"likes": 100, "shares": 50, "comments": 10},
                "timestamp": datetime.now(timezone.utc)
            }
            for _ in range(min(limit, 5))
        ]
    
    def get_router(self) -> APIRouter:
        """Get the configured FastAPI router."""
        return self.router
    
    def get_performance_metrics(self) -> List[EndpointMetrics]:
        """Get performance metrics."""
        return self.performance_middleware.get_metrics()


# Global router instance
_ai_endpoints_router: Optional[AIEndpointsRouter] = None


def get_ai_endpoints_router() -> AIEndpointsRouter:
    """Get or create the global AI endpoints router instance."""
    global _ai_endpoints_router
    if _ai_endpoints_router is None:
        _ai_endpoints_router = AIEndpointsRouter()
    return _ai_endpoints_router
