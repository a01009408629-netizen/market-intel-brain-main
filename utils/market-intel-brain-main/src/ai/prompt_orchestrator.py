"""
Prompt Orchestrator - AI Router & Context Optimizer

Enterprise-grade prompt orchestration with context window optimization,
data summarization, and intelligent routing to LLM inference engines.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

from .normalizer import UnifiedMarketEntity
from .cache import SemanticCache, CacheStrategy
from .security import PromptInjectionDefense


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"


class PromptType(Enum):
    """Prompt type enumeration."""
    MARKET_ANALYSIS = "market_analysis"
    SENTIMENT_SUMMARY = "sentiment_summary"
    PRICE_PREDICTION = "price_prediction"
    RISK_ASSESSMENT = "risk_assessment"
    NEWS_SUMMARY = "news_summary"
    PORTFOLIO_RECOMMENDATION = "portfolio_recommendation"


@dataclass
class ContextWindow:
    """Context window configuration."""
    max_tokens: int
    reserved_tokens: int = 100  # Reserved for system prompts
    available_tokens: int = field(init=False)
    
    def __post_init__(self):
        self.available_tokens = self.max_tokens - self.reserved_tokens
    
    @classmethod
    def for_provider(cls, provider: LLMProvider) -> "ContextWindow":
        """Get context window for specific provider."""
        windows = {
            LLMProvider.OPENAI: cls(max_tokens=4096),
            LLMProvider.ANTHROPIC: cls(max_tokens=100000),
            LLMProvider.AZURE_OPENAI: cls(max_tokens=4096),
            LLMProvider.HUGGINGFACE: cls(max_tokens=4096),
            LLMProvider.LOCAL: cls(max_tokens=2048)
        }
        return windows.get(provider, cls(max_tokens=4096))


@dataclass
class PromptTemplate:
    """Prompt template structure."""
    template_id: str
    name: str
    prompt_type: PromptType
    template: str
    system_prompt: str
    required_context: List[str] = field(default_factory=list)
    optional_context: List[str] = field(default_factory=list)
    max_response_tokens: int = 500
    temperature: float = 0.7
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizedPrompt:
    """Optimized prompt ready for LLM."""
    prompt_id: str
    system_prompt: str
    user_prompt: str
    context_summary: str
    truncated_data: List[Dict[str, Any]]
    token_count: int
    optimization_strategy: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMRequest:
    """LLM request structure."""
    request_id: str
    provider: LLMProvider
    model: str
    prompt: OptimizedPrompt
    temperature: float
    max_tokens: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """LLM response structure."""
    request_id: str
    response_text: str
    token_usage: Dict[str, int]
    response_time_ms: float
    model: str
    provider: LLMProvider
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextOptimizer:
    """
    Context window optimizer with intelligent data summarization.
    
    Features:
    - Token counting and optimization
    - Data prioritization and truncation
    - Intelligent summarization
    - Performance monitoring
    """
    
    def __init__(
        self,
        context_window: ContextWindow,
        logger: Optional[logging.Logger] = None
    ):
        self.context_window = context_window
        self.logger = logger or logging.getLogger("ContextOptimizer")
        
        # Optimization strategies
        self.data_priority_weights = {
            "price_data": 1.0,
            "sentiment_data": 0.8,
            "news_articles": 0.6,
            "metadata": 0.4
        }
        
        # Performance metrics
        self.optimizations_performed = 0
        self.avg_optimization_time_ms = 0.0
        self.total_tokens_saved = 0
        
        self.logger.info(f"ContextOptimizer initialized: {context_window.max_tokens} tokens")
    
    async def optimize_context(
        self,
        entity: UnifiedMarketEntity,
        prompt_template: PromptTemplate,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> OptimizedPrompt:
        """
        Optimize context to fit within token limits.
        
        Args:
            entity: Unified market entity
            prompt_template: Prompt template
            additional_context: Additional context
            
        Returns:
            Optimized prompt
        """
        import time
        start_time = time.time()
        
        try:
            # Extract and prioritize data
            prioritized_data = self._extract_prioritized_data(entity, prompt_template)
            
            # Add additional context
            if additional_context:
                prioritized_data.append(("additional_context", additional_context, 0.5))
            
            # Calculate initial token count
            initial_tokens = self._estimate_tokens(prioritized_data)
            
            # Optimize if needed
            if initial_tokens > self.context_window.available_tokens:
                optimized_data = await self._optimize_data(
                    prioritized_data,
                    self.context_window.available_tokens
                )
            else:
                optimized_data = prioritized_data
            
            # Build optimized prompt
            prompt_id = str(uuid.uuid4())
            optimized_prompt = OptimizedPrompt(
                prompt_id=prompt_id,
                system_prompt=prompt_template.system_prompt,
                user_prompt=self._build_user_prompt(prompt_template, optimized_data),
                context_summary=self._generate_context_summary(optimized_data),
                truncated_data=[item[1] for item in optimized_data],
                token_count=self._estimate_tokens(optimized_data),
                optimization_strategy=self._determine_optimization_strategy(initial_tokens),
                metadata={
                    "initial_tokens": initial_tokens,
                    "final_tokens": self._estimate_tokens(optimized_data),
                    "tokens_saved": initial_tokens - self._estimate_tokens(optimized_data),
                    "data_items_count": len(optimized_data)
                }
            )
            
            # Update metrics
            self.optimizations_performed += 1
            optimization_time = (time.time() - start_time) * 1000
            self.avg_optimization_time_ms = (
                (self.avg_optimization_time_ms * (self.optimizations_performed - 1) + optimization_time) /
                self.optimizations_performed
            )
            
            tokens_saved = initial_tokens - optimized_prompt.token_count
            self.total_tokens_saved += tokens_saved
            
            self.logger.debug(f"Optimized context: {initial_tokens} -> {optimized_prompt.token_count} tokens")
            return optimized_prompt
            
        except Exception as e:
            self.logger.error(f"Context optimization failed: {e}")
            raise
    
    def _extract_prioritized_data(
        self,
        entity: UnifiedMarketEntity,
        prompt_template: PromptTemplate
    ) -> List[Tuple[str, Dict[str, Any], float]]:
        """Extract and prioritize data from entity."""
        prioritized_data = []
        
        # Price data (highest priority)
        if "price_data" in prompt_template.required_context:
            price_data = {
                "symbol": entity.primary_symbol,
                "current_price": entity.price_data.current,
                "change": entity.price_data.change,
                "change_percent": entity.price_data.change_percent,
                "volume": entity.price_data.volume,
                "timestamp": entity.updated_at.isoformat()
            }
            prioritized_data.append(("price_data", price_data, self.data_priority_weights["price_data"]))
        
        # Sentiment data
        if "sentiment_data" in prompt_template.required_context and entity.sentiment_data:
            sentiment_summary = self._summarize_sentiment_data(entity.sentiment_data)
            prioritized_data.append(("sentiment_data", sentiment_summary, self.data_priority_weights["sentiment_data"]))
        
        # News articles
        if "news_articles" in prompt_template.required_context and entity.news_articles:
            news_summary = self._summarize_news_articles(entity.news_articles)
            prioritized_data.append(("news_articles", news_summary, self.data_priority_weights["news_articles"]))
        
        # Market data
        if entity.market_data:
            market_summary = self._summarize_market_data(entity.market_data)
            prioritized_data.append(("market_data", market_summary, self.data_priority_weights["price_data"]))
        
        # Metadata (lowest priority)
        if entity.metadata:
            prioritized_data.append(("metadata", entity.metadata, self.data_priority_weights["metadata"]))
        
        # Sort by priority (descending)
        prioritized_data.sort(key=lambda x: x[2], reverse=True)
        
        return prioritized_data
    
    def _summarize_sentiment_data(self, sentiment_data: List) -> Dict[str, Any]:
        """Summarize sentiment data."""
        if not sentiment_data:
            return {}
        
        # Aggregate sentiment scores
        positive_count = sum(1 for s in sentiment_data if s.sentiment.value == "positive")
        negative_count = sum(1 for s in sentiment_data if s.sentiment.value == "negative")
        neutral_count = sum(1 for s in sentiment_data if s.sentiment.value == "neutral")
        
        avg_score = sum(s.score for s in sentiment_data) / len(sentiment_data)
        avg_confidence = sum(s.confidence for s in sentiment_data) / len(sentiment_data)
        
        return {
            "total_analyses": len(sentiment_data),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "average_score": avg_score,
            "average_confidence": avg_confidence,
            "dominant_sentiment": "positive" if positive_count > negative_count else "negative",
            "latest_analysis": max(sentiment_data, key=lambda s: s.timestamp).timestamp.isoformat()
        }
    
    def _summarize_news_articles(self, news_articles: List) -> Dict[str, Any]:
        """Summarize news articles."""
        if not news_articles:
            return {}
        
        # Get recent articles (last 5)
        recent_articles = sorted(news_articles, key=lambda n: n.published_at or datetime.min, reverse=True)[:5]
        
        # Extract keywords and themes
        all_keywords = []
        for article in recent_articles:
            if hasattr(article, 'keywords'):
                all_keywords.extend(article.keywords)
        
        # Count keyword frequency
        keyword_counts = {}
        for keyword in all_keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        # Get top keywords
        top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "total_articles": len(news_articles),
            "recent_articles_count": len(recent_articles),
            "top_keywords": dict(top_keywords),
            "latest_article": recent_articles[0].title if recent_articles else None,
            "article_sentiments": {
                "positive": sum(1 for a in recent_articles if a.sentiment and a.sentiment.value == "positive"),
                "negative": sum(1 for a in recent_articles if a.sentiment and a.sentiment.value == "negative"),
                "neutral": sum(1 for a in recent_articles if a.sentiment and a.sentiment.value == "neutral")
            }
        }
    
    def _summarize_market_data(self, market_data: List) -> Dict[str, Any]:
        """Summarize market data."""
        if not market_data:
            return {}
        
        # Get latest data points
        latest_data = sorted(market_data, key=lambda m: m.timestamp, reverse=True)[:10]
        
        # Calculate statistics
        prices = [m.price.current for m in latest_data if m.price.current]
        volumes = [m.price.volume for m in latest_data if m.price.volume]
        
        return {
            "data_points": len(latest_data),
            "price_range": {
                "min": min(prices) if prices else None,
                "max": max(prices) if prices else None,
                "avg": sum(prices) / len(prices) if prices else None
            },
            "volume_stats": {
                "total": sum(volumes) if volumes else None,
                "avg": sum(volumes) / len(volumes) if volumes else None
            },
            "sources": list(set(m.source.value for m in latest_data)),
            "latest_timestamp": max(m.timestamp for m in latest_data).isoformat()
        }
    
    def _estimate_tokens(self, data: List[Tuple[str, Dict[str, Any], float]]) -> int:
        """Estimate token count for data."""
        # Rough estimation: 1 token ≈ 4 characters
        total_chars = 0
        
        for data_type, data_dict, _ in data:
            # Convert to JSON and count characters
            json_str = json.dumps(data_dict, separators=(',', ':'))
            total_chars += len(json_str)
        
        # Add overhead for structure
        total_chars += len(data) * 20  # Overhead per item
        
        return total_chars // 4  # Convert to tokens
    
    async def _optimize_data(
        self,
        data: List[Tuple[str, Dict[str, Any], float]],
        max_tokens: int
    ) -> List[Tuple[str, Dict[str, Any], float]]:
        """Optimize data to fit within token limits."""
        optimized_data = []
        current_tokens = 0
        
        for data_type, data_dict, priority in data:
            # Estimate tokens for this item
            item_tokens = self._estimate_tokens([(data_type, data_dict, priority)])
            
            if current_tokens + item_tokens <= max_tokens:
                # Include full item
                optimized_data.append((data_type, data_dict, priority))
                current_tokens += item_tokens
            else:
                # Try to truncate or summarize
                if priority > 0.5:  # High priority items get summarized
                    summarized = await self._summarize_data_item(data_type, data_dict)
                    if summarized:
                        optimized_data.append((data_type, summarized, priority))
                        current_tokens += self._estimate_tokens([(data_type, summarized, priority)])
                # Low priority items are dropped
        
        return optimized_data
    
    async def _summarize_data_item(self, data_type: str, data_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Summarize a single data item."""
        try:
            if data_type == "news_articles":
                # Keep only top 3 articles
                if "recent_articles" in data_dict:
                    data_dict["recent_articles"] = data_dict["recent_articles"][:3]
                return data_dict
            elif data_type == "market_data":
                # Keep only summary stats
                if "data_points" in data_dict:
                    return {
                        "summary": data_dict.get("price_range", {}),
                        "sources": data_dict.get("sources", [])
                    }
            elif data_type == "sentiment_data":
                # Keep only aggregate stats
                return {
                    "dominant_sentiment": data_dict.get("dominant_sentiment"),
                    "average_score": data_dict.get("average_score"),
                    "total_analyses": data_dict.get("total_analyses")
                }
            
            return data_dict
            
        except Exception as e:
            self.logger.error(f"Failed to summarize data item {data_type}: {e}")
            return None
    
    def _build_user_prompt(
        self,
        prompt_template: PromptTemplate,
        optimized_data: List[Tuple[str, Dict[str, Any], float]]
    ) -> str:
        """Build user prompt from template and data."""
        # Format data for prompt
        formatted_data = {}
        for data_type, data_dict, _ in optimized_data:
            formatted_data[data_type] = data_dict
        
        # Replace placeholders in template
        user_prompt = prompt_template.template
        
        for data_type, data_dict in formatted_data.items():
            placeholder = f"{{{data_type}}}"
            if placeholder in user_prompt:
                data_str = json.dumps(data_dict, indent=2, ensure_ascii=False)
                user_prompt = user_prompt.replace(placeholder, data_str)
        
        return user_prompt
    
    def _generate_context_summary(self, optimized_data: List[Tuple[str, Dict[str, Any], float]]) -> str:
        """Generate summary of context provided."""
        data_types = [data_type for data_type, _, _ in optimized_data]
        return f"Context includes: {', '.join(data_types)}"
    
    def _determine_optimization_strategy(self, initial_tokens: int) -> str:
        """Determine optimization strategy used."""
        if initial_tokens <= self.context_window.available_tokens:
            return "no_optimization"
        elif initial_tokens <= self.context_window.available_tokens * 1.5:
            return "truncation"
        elif initial_tokens <= self.context_window.available_tokens * 2.0:
            return "summarization"
        else:
            return "aggressive_summarization"
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get optimizer metrics."""
        return {
            "optimizations_performed": self.optimizations_performed,
            "avg_optimization_time_ms": self.avg_optimization_time_ms,
            "total_tokens_saved": self.total_tokens_saved,
            "context_window": {
                "max_tokens": self.context_window.max_tokens,
                "available_tokens": self.context_window.available_tokens
            },
            "data_priority_weights": self.data_priority_weights
        }


class PromptOrchestrator:
    """
    Enterprise-grade prompt orchestration with AI routing.
    
    Features:
    - Template management
    - Context optimization
    - LLM provider routing
    - Performance monitoring
    - Semantic caching integration
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider = LLMProvider.OPENAI,
        model: str = "gpt-3.5-turbo",
        semantic_cache: Optional[SemanticCache] = None,
        security_defense: Optional[PromptInjectionDefense] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.llm_provider = llm_provider
        self.model = model
        self.semantic_cache = semantic_cache
        self.security_defense = security_defense
        self.logger = logger or logging.getLogger("PromptOrchestrator")
        
        # Initialize components
        self.context_window = ContextWindow.for_provider(llm_provider)
        self.context_optimizer = ContextOptimizer(self.context_window, logger)
        
        # Prompt templates
        self.prompt_templates = self._initialize_prompt_templates()
        
        # Performance metrics
        self.requests_processed = 0
        self.cache_hits = 0
        self.security_blocks = 0
        self.avg_processing_time_ms = 0.0
        
        self.logger.info(f"PromptOrchestrator initialized: {llm_provider.value}/{model}")
    
    def _initialize_prompt_templates(self) -> Dict[PromptType, PromptTemplate]:
        """Initialize prompt templates."""
        return {
            PromptType.MARKET_ANALYSIS: PromptTemplate(
                template_id="market_analysis_v1",
                name="Market Analysis",
                prompt_type=PromptType.MARKET_ANALYSIS,
                template="""Analyze the following market data for {symbol}:

{price_data}

{sentiment_data}

{news_articles}

Provide a comprehensive market analysis including:
1. Current market sentiment
2. Key price movements and trends
3. News impact assessment
4. Short-term outlook
5. Risk factors

Focus on actionable insights and data-driven conclusions.""",
                system_prompt="You are an expert financial analyst providing market intelligence.",
                required_context=["price_data", "sentiment_data", "news_articles"],
                max_response_tokens=800,
                temperature=0.7
            ),
            
            PromptType.SENTIMENT_SUMMARY: PromptTemplate(
                template_id="sentiment_summary_v1",
                name="Sentiment Summary",
                prompt_type=PromptType.SENTIMENT_SUMMARY,
                template="""Summarize the sentiment analysis for {symbol}:

{sentiment_data}

{news_articles}

Provide:
1. Overall sentiment score and trend
2. Key sentiment drivers
3. Sentiment consistency across sources
4. Notable sentiment shifts
5. Confidence assessment

Be concise and focus on the most important sentiment indicators.""",
                system_prompt="You are a sentiment analysis expert specializing in financial markets.",
                required_context=["sentiment_data", "news_articles"],
                max_response_tokens=400,
                temperature=0.6
            ),
            
            PromptType.PRICE_PREDICTION: PromptTemplate(
                template_id="price_prediction_v1",
                name="Price Prediction",
                prompt_type=PromptType.PRICE_PREDICTION,
                template="""Based on the following data for {symbol}, provide a price prediction:

{price_data}

{sentiment_data}

{market_data}

Include:
1. Short-term price target (24-48 hours)
2. Confidence level (0-100%)
3. Key factors influencing the prediction
4. Potential price ranges
5. Risk considerations

Be specific about timeframes and confidence levels.""",
                system_prompt="You are a quantitative analyst specializing in price prediction models.",
                required_context=["price_data", "sentiment_data", "market_data"],
                max_response_tokens=600,
                temperature=0.5
            )
        }
    
    async def process_request(
        self,
        entity: UnifiedMarketEntity,
        prompt_type: PromptType,
        additional_context: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> LLMResponse:
        """
        Process AI request with full orchestration.
        
        Args:
            entity: Unified market entity
            prompt_type: Type of analysis requested
            additional_context: Additional context
            use_cache: Whether to use semantic cache
            
        Returns:
            LLM response
        """
        import time
        start_time = time.time()
        
        try:
            self.requests_processed += 1
            request_id = str(uuid.uuid4())
            
            # Get prompt template
            template = self.prompt_templates.get(prompt_type)
            if not template:
                raise ValueError(f"Unknown prompt type: {prompt_type}")
            
            # Check semantic cache first
            if use_cache and self.semantic_cache:
                cache_key = self._build_cache_key(entity, prompt_type, additional_context)
                cached_response = await self.semantic_cache.get_cached_response(cache_key)
                
                if cached_response:
                    self.cache_hits += 1
                    processing_time = (time.time() - start_time) * 1000
                    
                    return LLMResponse(
                        request_id=request_id,
                        response_text=cached_response,
                        token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                        response_time_ms=processing_time,
                        model=self.model,
                        provider=self.llm_provider,
                        metadata={"cached": True}
                    )
            
            # Security check
            if self.security_defense:
                security_result = await self.security_defense.process_input(
                    json.dumps(entity.to_dict(), default=str),
                    {"prompt_type": prompt_type.value}
                )
                
                if not security_result["success"]:
                    self.security_blocks += 1
                    raise ValueError(f"Security block: {security_result['error']}")
            
            # Optimize context
            optimized_prompt = await self.context_optimizer.optimize_context(
                entity, template, additional_context
            )
            
            # Create LLM request
            llm_request = LLMRequest(
                request_id=request_id,
                provider=self.llm_provider,
                model=self.model,
                prompt=optimized_prompt,
                temperature=template.temperature,
                max_tokens=template.max_response_tokens,
                metadata={
                    "prompt_type": prompt_type.value,
                    "entity_id": entity.entity_id,
                    "symbol": entity.primary_symbol
                }
            )
            
            # Call LLM (simulated - in production would call actual LLM)
            response = await self._call_llm(llm_request)
            
            # Cache response
            if use_cache and self.semantic_cache:
                await self.semantic_cache.cache_response(
                    cache_key, response.response_text, additional_context
                )
            
            # Update metrics
            processing_time = (time.time() - start_time) * 1000
            self.avg_processing_time_ms = (
                (self.avg_processing_time_ms * (self.requests_processed - 1) + processing_time) /
                self.requests_processed
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Request processing failed: {e}")
            raise
    
    async def _call_llm(self, request: LLMRequest) -> LLMResponse:
        """Call LLM API (simulated)."""
        # In production, this would call the actual LLM API
        # For now, we'll simulate a response
        
        await asyncio.sleep(0.1)  # Simulate API latency
        
        mock_response = f"""Analysis for {request.metadata.get('symbol', 'Unknown')}:

Based on the provided market data, sentiment analysis, and news articles, here's my assessment:

1. **Current Market Position**: The asset is showing {request.prompt.context_summary}
2. **Sentiment Analysis**: Market sentiment appears balanced with mixed signals
3. **Key Factors**: Recent news and price movements suggest cautious optimism
4. **Outlook**: Short-term volatility expected with medium-term potential
5. **Risk Level**: Moderate - monitor key support and resistance levels

*This analysis is based on the most recent data available and should be considered in context with broader market conditions.*

Generated at: {datetime.now(timezone.utc).isoformat()}"""
        
        return LLMResponse(
            request_id=request.request_id,
            response_text=mock_response,
            token_usage={
                "prompt_tokens": request.prompt.token_count,
                "completion_tokens": 250,
                "total_tokens": request.prompt.token_count + 250
            },
            response_time_ms=100.0,
            model=request.model,
            provider=request.provider,
            metadata={"cached": False}
        )
    
    def _build_cache_key(
        self,
        entity: UnifiedMarketEntity,
        prompt_type: PromptType,
        additional_context: Optional[Dict[str, Any]]
    ) -> str:
        """Build cache key for request."""
        key_data = {
            "entity_id": entity.entity_id,
            "prompt_type": prompt_type.value,
            "updated_at": entity.updated_at.isoformat(),
            "additional_context": additional_context
        }
        return json.dumps(key_data, sort_keys=True)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get orchestrator metrics."""
        optimizer_metrics = self.context_optimizer.get_metrics()
        
        return {
            "orchestrator_metrics": {
                "requests_processed": self.requests_processed,
                "cache_hits": self.cache_hits,
                "security_blocks": self.security_blocks,
                "cache_hit_rate": self.cache_hits / max(self.requests_processed, 1),
                "avg_processing_time_ms": self.avg_processing_time_ms,
                "llm_provider": self.llm_provider.value,
                "model": self.model
            },
            "optimizer_metrics": optimizer_metrics,
            "available_templates": list(self.prompt_templates.keys())
        }


# Global orchestrator instance
_prompt_orchestrator: Optional[PromptOrchestrator] = None


def get_prompt_orchestrator(
    llm_provider: LLMProvider = LLMProvider.OPENAI,
    model: str = "gpt-3.5-turbo",
    semantic_cache: Optional[SemanticCache] = None,
    security_defense: Optional[PromptInjectionDefense] = None
) -> PromptOrchestrator:
    """Get or create global prompt orchestrator."""
    global _prompt_orchestrator
    if _prompt_orchestrator is None:
        _prompt_orchestrator = PromptOrchestrator(
            llm_provider=llm_provider,
            model=model,
            semantic_cache=semantic_cache,
            security_defense=security_defense
        )
    return _prompt_orchestrator
