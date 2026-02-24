"""
Mock Data Providers

This module provides mock data providers for testing and development
with realistic data generation and configurable behavior.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import uuid

from .randomness import get_deterministic_random
from .exceptions import ProviderError, DataGenerationError


@dataclass
class MockDataConfig:
    """Configuration for mock data generation."""
    data_type: str = "financial"  # "financial", "market", "social", "iot"
    update_frequency: float = 1.0  # Updates per second
    data_quality: str = "high"  # "high", "medium", "low"
    error_rate: float = 0.01  # Default error rate
    latency_range: tuple = (0.1, 2.0)  # Min/max latency in seconds
    data_volume_range: tuple = (100, 1000)  # Min/max data size
    enable_real_time: bool = True
    enable_historical_data: bool = True


@dataclass
class MockResponse:
    """Mock response data structure."""
    request_id: str
    provider_name: str
    endpoint: str
    timestamp: datetime
    data: Any
    metadata: Dict[str, Any]
    processing_time: float
    success: bool
    error: Optional[str] = None


class BaseMockProvider(ABC):
    """Abstract base class for mock data providers."""
    
    def __init__(
        self,
        name: str,
        config: Optional[MockDataConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.name = name
        self.config = config or MockDataConfig()
        self.logger = logger or logging.getLogger(f"MockProvider_{name}")
        
        self._random = get_deterministic_random()
        self._historical_data = []
        self._state = {}
        
        self.logger.info(f"MockProvider {name} initialized")
    
    @abstractmethod
    async def fetch_data(self, request_id: str, endpoint: str, params: Dict[str, Any]) -> MockResponse:
        """Fetch data from mock provider."""
        pass
    
    @abstractmethod
    async def get_historical_data(self, symbol: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get historical data for a symbol."""
        pass
    
    def _generate_latency(self) -> float:
        """Generate realistic latency."""
        min_latency, max_latency = self.config.latency_range
        return self._random.next_float(min_latency, max_latency)
    
    def _generate_error(self) -> Optional[str]:
        """Generate error based on error rate."""
        if self._random.next_float() < self.config.error_rate:
            errors = [
                "Rate limit exceeded",
                "Invalid API key",
                "Service temporarily unavailable",
                "Internal server error",
                "Data not found",
                "Invalid request format"
            ]
            return self._random.next_choice(errors)
        return None
    
    def _generate_data_volume(self) -> int:
        """Generate realistic data volume."""
        min_volume, max_volume = self.config.data_volume_range
        return self._random.next_int(min_volume, max_volume)


class FinancialMockProvider(BaseMockProvider):
    """Mock financial data provider."""
    
    def __init__(self, config: Optional[MockDataConfig] = None):
        super().__init__("financial", config)
        self._stock_data = self._initialize_stock_data()
    
    async def fetch_data(self, request_id: str, endpoint: str, params: Dict[str, Any]) -> MockResponse:
        """Fetch financial data."""
        start_time = time.time()
        
        try:
            # Simulate processing time
            processing_time = self._generate_latency()
            await asyncio.sleep(processing_time)
            
            # Generate response based on endpoint
            if endpoint == "/quote":
                data = self._generate_quote_data(params.get("symbol", "AAPL"))
            elif endpoint == "/market_data":
                data = self._generate_market_data(params.get("symbol", "AAPL"))
            elif endpoint == "/time_series":
                data = self._generate_time_series_data(params.get("symbol", "AAPL"))
            else:
                data = {"error": f"Unknown endpoint: {endpoint}"}
            
            # Check for errors
            error = self._generate_error()
            success = error is None
            
            # Create response
            response = MockResponse(
                request_id=request_id,
                provider_name=self.name,
                endpoint=endpoint,
                timestamp=datetime.now(),
                data=data,
                metadata={
                    "processing_time": processing_time,
                    "data_quality": self.config.data_quality,
                    "data_volume": len(str(data))
                },
                processing_time=time.time() - start_time,
                success=success,
                error=error
            )
            
            self.logger.debug(f"Generated financial data for {endpoint}: {success}")
            return response
            
        except Exception as e:
            self.logger.error(f"Financial provider error: {e}")
            raise ProviderError(f"Failed to generate financial data: {e}")
    
    async def get_historical_data(self, symbol: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get historical financial data."""
        if not self.config.enable_historical_data:
            return []
        
        # Generate historical data
        data_points = []
        current_date = start_date
        base_price = self._random.next_float(50.0, 200.0)
        
        while current_date <= end_date:
            # Generate daily price with some volatility
            price_change = self._random.next_float(-5.0, 5.0)
            base_price = max(1.0, base_price + price_change)
            
            # Generate volume
            volume = self._random.next_int(100000, 10000000)
            
            data_points.append({
                "date": current_date.isoformat(),
                "symbol": symbol,
                "open": base_price,
                "high": base_price * (1 + abs(price_change) * 0.01),
                "low": base_price * (1 - abs(price_change) * 0.01),
                "close": base_price,
                "volume": volume,
                "adjusted_close": base_price
            })
            
            current_date += timedelta(days=1)
        
        self.logger.info(f"Generated {len(data_points)} historical data points for {symbol}")
        return data_points
    
    def _generate_quote_data(self, symbol: str) -> Dict[str, Any]:
        """Generate quote data for a symbol."""
        if symbol not in self._stock_data:
            # Initialize new stock
            self._stock_data[symbol] = {
                "price": self._random.next_float(50.0, 500.0),
                "change": self._random.next_float(-10.0, 10.0),
                "change_percent": self._random.next_float(-5.0, 5.0),
                "volume": self._random.next_int(1000000, 50000000),
                "market_cap": self._random.next_int(1000000000, 50000000000),
                "last_updated": datetime.now().isoformat()
            }
        
        stock_info = self._stock_data[symbol]
        
        return {
            "symbol": symbol,
            "price": stock_info["price"],
            "change": stock_info["change"],
            "change_percent": stock_info["change_percent"],
            "volume": stock_info["volume"],
            "market_cap": stock_info["market_cap"],
            "day_high": stock_info["price"] * 1.02,
            "day_low": stock_info["price"] * 0.98,
            "year_high": stock_info["price"] * 1.5,
            "year_low": stock_info["price"] * 0.7,
            "last_updated": stock_info["last_updated"],
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_market_data(self, symbol: str) -> Dict[str, Any]:
        """Generate market data for a symbol."""
        quote_data = self._generate_quote_data(symbol)
        
        return {
            "symbol": symbol,
            "quote": quote_data,
            "market_status": "open",
            "bid": quote_data["price"] * 0.999,
            "ask": quote_data["price"] * 1.001,
            "bid_size": self._random.next_int(100, 10000),
            "ask_size": self._random.next_int(100, 10000),
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_time_series_data(self, symbol: str) -> Dict[str, Any]:
        """Generate time series data for a symbol."""
        # Generate recent time series data
        time_series = []
        current_price = self._stock_data.get(symbol, {}).get("price", 100.0)
        
        for i in range(30):  # 30 days of data
            price_change = self._random.next_float(-2.0, 2.0)
            current_price = max(1.0, current_price + price_change)
            
            time_series.append({
                "date": (datetime.now() - timedelta(days=i)).isoformat(),
                "symbol": symbol,
                "open": current_price,
                "high": current_price * (1 + abs(price_change) * 0.01),
                "low": current_price * (1 - abs(price_change) * 0.01),
                "close": current_price,
                "volume": self._random.next_int(100000, 1000000)
            })
        
        return {
            "symbol": symbol,
            "time_series": time_series,
            "metadata": {
                "period": "30d",
                "data_points": len(time_series),
                "generated_at": datetime.now().isoformat()
            }
        }
    
    def _initialize_stock_data(self) -> Dict[str, Dict[str, Any]]:
        """Initialize stock data for common symbols."""
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "META", "NVDA"]
        stock_data = {}
        
        for symbol in symbols:
            stock_data[symbol] = {
                "price": self._random.next_float(50.0, 500.0),
                "change": self._random.next_float(-10.0, 10.0),
                "change_percent": self._random.next_float(-5.0, 5.0),
                "volume": self._random.next_int(1000000, 50000000),
                "market_cap": self._random.next_int(1000000000, 50000000000),
                "last_updated": datetime.now().isoformat()
            }
        
        self.logger.info(f"Initialized stock data for {len(symbols)} symbols")
        return stock_data


class MarketMockProvider(BaseMockProvider):
    """Mock market data provider."""
    
    def __init__(self, config: Optional[MockDataConfig] = None):
        super().__init__("market", config)
        self._market_data = self._initialize_market_data()
    
    async def fetch_data(self, request_id: str, endpoint: str, params: Dict[str, Any]) -> MockResponse:
        """Fetch market data."""
        start_time = time.time()
        
        try:
            # Simulate processing time
            processing_time = self._generate_latency()
            await asyncio.sleep(processing_time)
            
            # Generate response based on endpoint
            if endpoint == "/search":
                data = self._generate_search_results(params.get("query", ""))
            elif endpoint == "/trending":
                data = self._generate_trending_stocks()
            elif endpoint == "/sectors":
                data = self._generate_sector_data()
            else:
                data = {"error": f"Unknown endpoint: {endpoint}"}
            
            # Check for errors
            error = self._generate_error()
            success = error is None
            
            # Create response
            response = MockResponse(
                request_id=request_id,
                provider_name=self.name,
                endpoint=endpoint,
                timestamp=datetime.now(),
                data=data,
                metadata={
                    "processing_time": processing_time,
                    "data_quality": self.config.data_quality,
                    "data_volume": len(str(data))
                },
                processing_time=time.time() - start_time,
                success=success,
                error=error
            )
            
            self.logger.debug(f"Generated market data for {endpoint}: {success}")
            return response
            
        except Exception as e:
            self.logger.error(f"Market provider error: {e}")
            raise ProviderError(f"Failed to generate market data: {e}")
    
    async def get_historical_data(self, symbol: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get historical market data."""
        if not self.config.enable_historical_data:
            return []
        
        # Generate historical market data
        data_points = []
        current_date = start_date
        base_index = self._random.next_int(1000, 5000)
        
        while current_date <= end_date:
            # Generate market index with some volatility
            index_change = self._random.next_int(-50, 50)
            base_index = max(1000, base_index + index_change)
            
            data_points.append({
                "date": current_date.isoformat(),
                "symbol": symbol,
                "market_index": base_index,
                "volume": self._random.next_int(1000000000, 5000000000),
                "volatility": self._random.next_float(0.1, 0.5)
            })
            
            current_date += timedelta(days=1)
        
        self.logger.info(f"Generated {len(data_points)} historical market data points for {symbol}")
        return data_points
    
    def _generate_search_results(self, query: str) -> Dict[str, Any]:
        """Generate search results."""
        results = []
        
        # Generate mock search results
        for i in range(self._random.next_int(5, 20)):
            results.append({
                "id": f"result_{i}",
                "title": f"Search result {i} for {query}",
                "description": f"Mock description for search result {i}",
                "url": f"https://example.com/result/{i}",
                "relevance": self._random.next_float(0.5, 1.0),
                "timestamp": datetime.now().isoformat()
            })
        
        return {
            "query": query,
            "results": results,
            "total": len(results),
            "metadata": {
                "search_time": 0.1,
                "generated_at": datetime.now().isoformat()
            }
        }
    
    def _generate_trending_stocks(self) -> Dict[str, Any]:
        """Generate trending stocks data."""
        trending_stocks = [
            "AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"
        ]
        
        trending_data = []
        for i, stock in enumerate(trending_stocks):
            trending_data.append({
                "rank": i + 1,
                "symbol": stock,
                "price": self._random.next_float(100.0, 1000.0),
                "change": self._random.next_float(-5.0, 5.0),
                "volume": self._random.next_int(1000000, 50000000),
                "trending_score": self._random.next_float(0.7, 1.0)
            })
        
        return {
            "trending_stocks": trending_data,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "update_frequency": "real-time"
            }
        }
    
    def _generate_sector_data(self) -> Dict[str, Any]:
        """Generate sector data."""
        sectors = [
            {"name": "Technology", "symbol": "XLK"},
            {"name": "Healthcare", "symbol": "XLV"},
            {"name": "Finance", "symbol": "XLF"},
            {"name": "Energy", "symbol": "XLE"}
        ]
        
        sector_performance = []
        for sector in sectors:
            sector_performance.append({
                "sector": sector["name"],
                "symbol": sector["symbol"],
                "performance": self._random.next_float(-2.0, 2.0),
                "change": self._random.next_float(-1.0, 1.0)
            })
        
        return {
            "sectors": sector_performance,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "market_status": "active"
            }
        }
    
    def _initialize_market_data(self) -> Dict[str, Any]:
        """Initialize market data."""
        return {
            "market_status": "open",
            "volatility_index": self._random.next_float(10.0, 30.0),
            "trending_sectors": ["Technology", "Healthcare"],
            "market_sentiment": "bullish",
            "last_updated": datetime.now().isoformat()
        }


class SocialMockProvider(BaseMockProvider):
    """Mock social data provider."""
    
    def __init__(self, config: Optional[MockDataConfig] = None):
        super().__init__("social", config)
        self._user_data = self._initialize_user_data()
    
    async def fetch_data(self, request_id: str, endpoint: str, params: Dict[str, Any]) -> MockResponse:
        """Fetch social data."""
        start_time = time.time()
        
        try:
            # Simulate processing time
            processing_time = self._generate_latency()
            await asyncio.sleep(processing_time)
            
            # Generate response based on endpoint
            if endpoint == "/user_profile":
                data = self._generate_user_profile(params.get("user_id", "user123"))
            elif endpoint == "/posts":
                data = self._generate_posts(params.get("user_id", "user123"))
            elif endpoint == "/followers":
                data = self._generate_followers(params.get("user_id", "user123"))
            else:
                data = {"error": f"Unknown endpoint: {endpoint}"}
            
            # Check for errors
            error = self._generate_error()
            success = error is None
            
            # Create response
            response = MockResponse(
                request_id=request_id,
                provider_name=self.name,
                endpoint=endpoint,
                timestamp=datetime.now(),
                data=data,
                metadata={
                    "processing_time": processing_time,
                    "data_quality": self.config.data_quality,
                    "data_volume": len(str(data))
                },
                processing_time=time.time() - start_time,
                success=success,
                error=error
            )
            
            self.logger.debug(f"Generated social data for {endpoint}: {success}")
            return response
            
        except Exception as e:
            self.logger.error(f"Social provider error: {e}")
            raise ProviderError(f"Failed to generate social data: {e}")
    
    def _generate_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Generate user profile data."""
        return {
            "user_id": user_id,
            "username": f"user_{user_id}",
            "display_name": f"User {user_id}",
            "email": f"user{user_id}@example.com",
            "avatar": f"https://api.dicebear.com/7.0/avatars/{user_id}",
            "followers_count": self._random.next_int(100, 10000),
            "following_count": self._random.next_int(50, 5000),
            "posts_count": self._random.next_int(10, 1000),
            "created_at": (datetime.now() - timedelta(days=self._random.next_int(30, 365))).isoformat(),
            "last_active": datetime.now().isoformat(),
            "verified": self._random.next_float() > 0.5,
            "profile": {
                "bio": f"Mock bio for user {user_id}",
                "location": f"City {user_id}",
                "website": f"https://user{user_id}.example.com"
            }
        }
    
    def _generate_posts(self, user_id: str) -> Dict[str, Any]:
        """Generate user posts data."""
        posts = []
        
        for i in range(self._random.next_int(5, 20)):
            posts.append({
                "id": f"post_{i}",
                "user_id": user_id,
                "content": f"Mock post content {i} from user {user_id}",
                "likes_count": self._random.next_int(0, 1000),
                "comments_count": self._random.next_int(0, 100),
                "shares_count": self._random.next_int(0, 100),
                "created_at": (datetime.now() - timedelta(days=self._random.next_int(1, 30))).isoformat(),
                "media": self._random.next_float() > 0.3
            })
        
        return {
            "posts": posts,
            "total": len(posts),
            "metadata": {
                "generated_at": datetime.now().isoformat()
            }
        }
    
    def _generate_followers(self, user_id: str) -> Dict[str, Any]:
        """Generate followers data."""
        followers = []
        
        for i in range(self._random.next_int(10, 100)):
            followers.append({
                "id": f"follower_{i}",
                "username": f"follower_{i}_of_{user_id}",
                "display_name": f"Follower {i}",
                "avatar": f"https://api.dicebear.com/7.0/avatars/follower_{i}",
                "following": self._random.next_float() > 0.5,
                "followed_at": (datetime.now() - timedelta(days=self._random.next_int(1, 365))).isoformat()
            })
        
        return {
            "followers": followers,
            "total": len(followers),
            "metadata": {
                "generated_at": datetime.now().isoformat()
            }
        }
    
    def _initialize_user_data(self) -> Dict[str, Any]:
        """Initialize user data."""
        return {
            "total_users": self._random.next_int(1000, 10000),
            "active_users": self._random.next_int(500, 5000),
            "new_users_today": self._random.next_int(10, 100),
            "user_growth_rate": self._random.next_float(0.01, 0.05)
        }


class MockProviderRegistry:
    """Registry for managing mock providers."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("MockProviderRegistry")
        self._providers = {}
        
        # Register default providers
        self._register_default_providers()
        
        self.logger.info("MockProviderRegistry initialized")
    
    def _register_default_providers(self):
        """Register default mock providers."""
        # Register financial providers
        self.register_provider("finnhub", FinancialMockProvider)
        self.register_provider("yahoo_finance", FinancialMockProvider)
        self.register_provider("alpha_vantage", FinancialMockProvider)
        
        # Register market providers
        self.register_provider("market_data", MarketMockProvider)
        
        # Register social providers
        self.register_provider("twitter", SocialMockProvider)
        self.register_provider("facebook", SocialMockProvider)
        
        self.logger.info("Registered default mock providers")
    
    def register_provider(self, name: str, provider_class: type, config: Optional[MockDataConfig] = None):
        """Register a new mock provider."""
        if name in self._providers:
            self.logger.warning(f"Provider {name} already registered")
            return
        
        try:
            provider = provider_class(config)
            self._providers[name] = provider
            self.logger.info(f"Registered mock provider: {name}")
        except Exception as e:
            self.logger.error(f"Failed to register provider {name}: {e}")
            raise ProviderError(f"Failed to register provider {name}: {e}")
    
    def get_provider(self, name: str) -> Optional[BaseMockProvider]:
        """Get a registered mock provider."""
        return self._providers.get(name)
    
    def list_providers(self) -> List[str]:
        """List all registered providers."""
        return list(self._providers.keys())
    
    def get_provider_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a provider."""
        provider = self.get_provider(name)
        if provider:
            return {
                "name": provider.name,
                "config": provider.get_config(),
                "type": provider.__class__.__name__
            }
        return None
    
    def get_all_providers_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all providers."""
        return {
            name: self.get_provider_info(name)
            for name in self.list_providers()
        }


class GeopoliticalNewsProvider:
    """
    Mock provider for geopolitical news analysis.
    
    This provider generates realistic geopolitical news articles
    with sentiment analysis and relevance scoring.
    """
    
    def __init__(self, config: Optional[MockDataConfig] = None):
        """
        Initialize geopolitical news provider.
        
        Args:
            config: Provider configuration
        """
        self.config = config or MockDataConfig()
        self._random = get_deterministic_random()
        
        # Geopolitical news sources
        self.news_sources = [
            "Reuters", "BBC News", "Al Jazeera", "CNN International",
            "Financial Times", "The Economist", "Associated Press",
            "Bloomberg Politics", "Politico", "Foreign Policy"
        ]
        
        # Geopolitical categories
        self.categories = [
            "International Relations", "Trade Policy", "Military Conflicts",
            "Diplomacy", "Sanctions", "Treaties", "Elections",
            "Human Rights", "Climate Policy", "Energy Politics"
        ]
        
        # Countries and regions
        self.countries = [
            "United States", "China", "Russia", "European Union",
            "United Kingdom", "Japan", "India", "Brazil",
            "Saudi Arabia", "Israel", "Iran", "North Korea",
            "Ukraine", "Turkey", "Egypt", "South Africa"
        ]
        
        # Geopolitical keywords
        self.keywords = [
            "diplomatic relations", "trade agreement", "military alliance",
            "economic sanctions", "peace treaty", "summit meeting",
            "foreign policy", "international law", "sovereignty",
            "geopolitical tension", "regional stability", "global governance"
        ]
        
        self.logger = logging.getLogger("GeopoliticalNewsProvider")
        self.logger.info("GeopoliticalNewsProvider initialized")
    
    async def fetch_data(self, request_id: str, endpoint: str, params: Dict[str, Any]) -> MockResponse:
        """
        Fetch geopolitical news articles.
        
        Args:
            request_id: Unique request identifier
            endpoint: API endpoint
            params: Request parameters
            
        Returns:
            Dictionary containing news articles
        """
        start_time = time.time()
        
        try:
            # Simulate processing time
            processing_time = self._generate_latency()
            await asyncio.sleep(processing_time)
            
            # Parse parameters
            limit = params.get("limit", 20)
            category = params.get("category")
            country = params.get("country")
            keywords = params.get("keywords", [])
            
            # Generate news articles
            articles = []
            for i in range(limit):
                article = self._generate_news_article(
                    category=category,
                    country=country,
                    keywords=keywords
                )
                articles.append(article)
            
            # Sort by relevance and publication date
            articles.sort(key=lambda x: (x.relevance_score, x.published_at), reverse=True)
            
            # Check for errors
            error = self._generate_error()
            success = error is None
            
            # Create response
            response = MockResponse(
                request_id=request_id,
                provider_name="geopolitical_news",
                endpoint=endpoint,
                timestamp=datetime.now(),
                data={
                    "articles": articles,
                    "total_count": len(articles),
                    "category": category,
                    "country": country,
                    "keywords": keywords
                },
                metadata={
                    "processing_time": processing_time,
                    "data_quality": self.config.data_quality,
                    "data_volume": len(str(articles))
                },
                processing_time=time.time() - start_time,
                success=success,
                error=error
            )
            
            self.logger.debug(f"Generated geopolitical news: {success}")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to generate geopolitical news: {e}")
            raise ProviderError(f"Failed to generate geopolitical news: {e}")
    
    def _generate_news_article(
        self,
        category: Optional[str] = None,
        country: Optional[str] = None,
        keywords: List[str] = None
    ) -> Dict[str, Any]:
        """Generate a realistic news article."""
        
        # Select random values if not specified
        selected_category = category or self._random.next_choice(self.categories)
        selected_country = country or self._random.next_choice(self.countries)
        selected_source = self._random.next_choice(self.news_sources)
        
        # Generate title based on category and country
        title_templates = {
            "International Relations": [
                f"{selected_country} and {self._random.next_choice(['US', 'China', 'EU'])} Strengthen Diplomatic Ties",
                f"New Trade Agreement Between {selected_country} and Regional Partners",
                f"{selected_country} Hosts International Summit on Global Cooperation"
            ],
            "Trade Policy": [
                f"{selected_country} Announces New Trade Policy Framework",
                f"Tariff Changes Impact {selected_country}'s Export Economy",
                f"{selected_country} Negotiates Trade Deal with {self._random.next_choice(['ASEAN', 'EU', 'Mercosur'])}"
            ],
            "Military Conflicts": [
                f"Tensions Rise in {selected_country} Region Over Border Dispute",
                f"{selected_country} Increases Defense Spending Amid Security Concerns",
                f"International Community Responds to {selected_country}'s Military Actions"
            ]
        }
        
        title_templates_list = title_templates.get(selected_category, [
            f"{selected_country} Makes Major Policy Announcement",
            f"International Community Reacts to {selected_country}'s Recent Decision",
            f"Economic Developments in {selected_country} Region"
        ])
        
        title = self._random.next_choice(title_templates_list)
        
        # Generate content
        content = self._generate_article_content(title, selected_category, selected_country)
        
        # Generate metadata
        article_id = str(uuid.uuid4())
        published_at = datetime.now(timezone.utc) - timedelta(
            hours=self._random.next_int(0, 72),
            minutes=self._random.next_int(0, 60)
        )
        
        # Calculate sentiment based on content
        sentiment_score = self._calculate_sentiment_score(content)
        
        # Calculate relevance based on keywords match
        relevance_score = self._calculate_relevance_score(content, keywords or [])
        
        return {
            "article_id": article_id,
            "title": title,
            "content": content,
            "summary": self._generate_summary(content),
            "source": selected_source,
            "author": f"{self._random.next_choice(['John', 'Sarah', 'Michael', 'Emma'])} {self._random.next_choice(['Smith', 'Johnson', 'Williams', 'Brown'])}",
            "published_at": published_at.isoformat(),
            "category": selected_category,
            "tags": self._generate_tags(selected_category, selected_country),
            "sentiment_score": sentiment_score,
            "relevance_score": relevance_score,
            "url": f"https://example.com/news/{article_id}",
            "image_url": f"https://example.com/images/{article_id}.jpg" if self._random.next_float() > 0.3 else None,
            "language": "en",
            "country": selected_country,
            "keywords": self._extract_keywords(content)
        }
    
    def _generate_article_content(self, title: str, category: str, country: str) -> str:
        """Generate realistic article content."""
        
        content_templates = {
            "International Relations": [
                f"In a significant development in international diplomacy, {country} has taken steps to strengthen its relationship with key global partners. According to officials familiar with the matter, these initiatives aim to enhance cooperation in areas of mutual interest, including trade, security, and cultural exchange. The move comes at a time when global geopolitical dynamics are undergoing substantial changes, with nations seeking to build more resilient international partnerships. Analysts suggest that this diplomatic initiative could have far-reaching implications for regional stability and global governance structures.",
                f"{country}'s foreign ministry announced today a series of diplomatic engagements designed to deepen ties with neighboring countries and major global powers. These engagements include high-level visits, trade negotiations, and security cooperation agreements. Foreign policy experts note that this approach reflects {country}'s commitment to playing a constructive role in international affairs. The initiatives are expected to address pressing global challenges such as climate change, economic development, and regional security."
            ],
            "Trade Policy": [
                f"{country} unveiled a comprehensive trade policy framework today that officials say will boost economic growth and strengthen international trade relationships. The new policy includes measures to reduce trade barriers, promote exports, and attract foreign investment. Trade experts note that these changes could significantly impact global supply chains and trade patterns. The policy announcement comes amid ongoing discussions about international trade reform and the need for more inclusive economic growth.",
                f"The government of {country} announced significant changes to its trade policy, introducing new measures aimed at modernizing its approach to international commerce. These changes include updated tariff structures, streamlined customs procedures, and enhanced trade facilitation measures. Economic analysts suggest that these reforms could improve {country}'s competitiveness in global markets and strengthen its position in international trade negotiations."
            ]
        }
        
        templates = content_templates.get(category, [
            f"{country} has announced new policy initiatives that are expected to have significant impact on both domestic and international affairs. The measures, which were unveiled today by government officials, represent a strategic shift in {country}'s approach to addressing current challenges. Policy experts note that these initiatives could influence regional dynamics and set new precedents for international cooperation."
        ])
        
        return self._random.next_choice(templates)
    
    def _generate_summary(self, content: str) -> str:
        """Generate a summary of the article content."""
        sentences = content.split('.')
        if len(sentences) <= 2:
            return content
        
        # Return first 2-3 sentences as summary
        summary = '.'.join(sentences[:2]) + '.'
        return summary.strip()
    
    def _generate_tags(self, category: str, country: str) -> List[str]:
        """Generate relevant tags for the article."""
        base_tags = [category.lower().replace(" ", "_"), country.lower().replace(" ", "_")]
        
        additional_tags = []
        if "trade" in category.lower():
            additional_tags.extend(["economics", "commerce", "international_trade"])
        elif "military" in category.lower():
            additional_tags.extend(["defense", "security", "conflict"])
        elif "diplomacy" in category.lower():
            additional_tags.extend(["foreign_policy", "international_relations", "negotiation"])
        
        return base_tags + additional_tags[:3]  # Limit total tags
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction based on geopolitical terms
        geopolitical_terms = [
            "diplomacy", "trade", "sanctions", "treaty", "summit", "policy",
            "international", "relations", "cooperation", "agreement", "negotiation",
            "security", "defense", "military", "conflict", "peace", "stability"
        ]
        
        text_lower = text.lower()
        found_keywords = [term for term in geopolitical_terms if term in text_lower]
        
        return found_keywords[:5]  # Return top 5 keywords
    
    def _calculate_sentiment_score(self, content: str) -> float:
        """Calculate sentiment score for content."""
        positive_words = ["cooperation", "agreement", "peace", "success", "growth", "strengthen", "positive"]
        negative_words = ["conflict", "tension", "crisis", "decline", "threat", "concern", "dispute"]
        
        content_lower = content.lower()
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)
        
        total_words = len(content.split())
        if total_words == 0:
            return 0.0
        
        score = (positive_count - negative_count) / max(total_words * 0.1, 1)
        return max(-1.0, min(1.0, score))
    
    def _calculate_relevance_score(self, content: str, keywords: List[str]) -> float:
        """Calculate relevance score based on keyword matches."""
        if not keywords:
            return self._random.next_float(0.5, 0.9)
        
        content_lower = content.lower()
        matches = sum(1 for keyword in keywords if keyword.lower() in content_lower)
        
        relevance = matches / len(keywords)
        return min(1.0, relevance + self._random.next_float(0.1, 0.3))


class SocialMediaSentimentProvider:
    """
    Mock provider for social media sentiment analysis.
    
    This provider generates realistic social media sentiment data
    from various platforms including Twitter, Facebook, and Instagram.
    """
    
    def __init__(self, config: Optional[MockDataConfig] = None):
        """
        Initialize social media sentiment provider.
        
        Args:
            config: Provider configuration
        """
        self.config = config or MockDataConfig()
        self._random = get_deterministic_random()
        
        # Social media platforms
        self.platforms = ["twitter", "facebook", "instagram", "linkedin", "reddit"]
        
        # Sentiment categories
        self.sentiment_categories = ["positive", "negative", "neutral", "mixed"]
        
        # Emotions
        self.emotions = ["joy", "anger", "fear", "sadness", "surprise", "trust"]
        
        # Topics for social media analysis
        self.topics = [
            "politics", "economy", "technology", "environment", "health",
            "entertainment", "sports", "international", "business", "science"
        ]
        
        self.logger = logging.getLogger("SocialMediaSentimentProvider")
        self.logger.info("SocialMediaSentimentProvider initialized")
    
    async def fetch_data(self, request_id: str, endpoint: str, params: Dict[str, Any]) -> MockResponse:
        """
        Fetch social media sentiment data.
        
        Args:
            request_id: Unique request identifier
            endpoint: API endpoint
            params: Request parameters
            
        Returns:
            Dictionary containing sentiment data
        """
        start_time = time.time()
        
        try:
            # Simulate processing time
            processing_time = self._generate_latency()
            await asyncio.sleep(processing_time)
            
            # Parse parameters
            platform = params.get("platform")
            topic = params.get("topic")
            time_range = params.get("time_range", "24h")
            limit = params.get("limit", 100)
            
            # Generate sentiment data
            sentiment_data = []
            for i in range(limit):
                data_point = self._generate_sentiment_data_point(
                    platform=platform,
                    topic=topic,
                    time_range=time_range
                )
                sentiment_data.append(data_point)
            
            # Calculate aggregate statistics
            aggregate_stats = self._calculate_aggregate_stats(sentiment_data)
            
            # Check for errors
            error = self._generate_error()
            success = error is None
            
            # Create response
            response = MockResponse(
                request_id=request_id,
                provider_name="social_media_sentiment",
                endpoint=endpoint,
                timestamp=datetime.now(),
                data={
                    "sentiment_data": sentiment_data,
                    "aggregate_stats": aggregate_stats,
                    "platform": platform,
                    "topic": topic,
                    "time_range": time_range,
                    "total_posts": len(sentiment_data)
                },
                metadata={
                    "processing_time": processing_time,
                    "data_quality": self.config.data_quality,
                    "data_volume": len(str(sentiment_data))
                },
                processing_time=time.time() - start_time,
                success=success,
                error=error
            )
            
            self.logger.debug(f"Generated social media sentiment: {success}")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to generate social media sentiment: {e}")
            raise ProviderError(f"Failed to generate social media sentiment: {e}")
    
    def _generate_sentiment_data_point(
        self,
        platform: Optional[str] = None,
        topic: Optional[str] = None,
        time_range: str = "24h"
    ) -> Dict[str, Any]:
        """Generate a single sentiment data point."""
        
        selected_platform = platform or self._random.next_choice(self.platforms)
        selected_topic = topic or self._random.next_choice(self.topics)
        
        # Generate sentiment scores
        sentiment_score = self._random.next_float(-1.0, 1.0)
        if sentiment_score > 0.3:
            sentiment = "positive"
        elif sentiment_score < -0.3:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        # Generate emotion scores
        emotions = {}
        for emotion in self.emotions:
            emotions[emotion] = self._random.next_float(0.0, 1.0)
        
        # Normalize emotions
        emotion_total = sum(emotions.values())
        if emotion_total > 0:
            emotions = {k: v / emotion_total for k, v in emotions.items()}
        
        # Generate engagement metrics
        engagement = {
            "likes": self._random.next_int(0, 10000),
            "shares": self._random.next_int(0, 5000),
            "comments": self._random.next_int(0, 2000),
            "views": self._random.next_int(1000, 100000)
        }
        
        # Generate timestamp
        hours_ago = self._random.next_int(0, 24) if time_range == "24h" else self._random.next_int(0, 168)
        timestamp = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
        
        return {
            "post_id": str(uuid.uuid4()),
            "platform": selected_platform,
            "topic": selected_topic,
            "sentiment": sentiment,
            "sentiment_score": sentiment_score,
            "emotions": emotions,
            "engagement": engagement,
            "timestamp": timestamp.isoformat(),
            "author": f"user_{self._random.next_int(1000, 9999)}",
            "content": self._generate_post_content(selected_topic, sentiment),
            "language": "en",
            "location": self._random.next_choice(["US", "UK", "Canada", "Australia", "India"])
        }
    
    def _generate_post_content(self, topic: str, sentiment: str) -> str:
        """Generate realistic social media post content."""
        
        content_templates = {
            "positive": [
                f"Great news about {topic}! Really optimistic about the future. #{topic.replace(' ', '')}",
                f"Amazing developments in {topic} today. This is exactly what we needed! #{topic.replace(' ', '')}",
                f"Feeling hopeful about {topic}. Progress is being made! #{topic.replace(' ', '')} #positive"
            ],
            "negative": [
                f"Concerned about the situation with {topic}. Something needs to change. #{topic.replace(' ', '')}",
                f"Disappointed with the latest {topic} news. This isn't good enough. #{topic.replace(' ', '')}",
                f"Worried about where {topic} is heading. We need better solutions. #{topic.replace(' ', '')} #concern"
            ],
            "neutral": [
                f"Following the latest developments in {topic}. Will be interesting to see what happens next. #{topic.replace(' ', '')}",
                f"Observing the {topic} situation. Time will tell how this plays out. #{topic.replace(' ', '')}",
                f"Monitoring {topic} news. Keeping an eye on developments. #{topic.replace(' ', '')} #analysis"
            ]
        }
        
        templates = content_templates.get(sentiment, content_templates["neutral"])
        return self._random.next_choice(templates)
    
    def _calculate_aggregate_stats(self, sentiment_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate aggregate statistics from sentiment data."""
        
        if not sentiment_data:
            return {}
        
        # Count sentiments
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
        total_sentiment_score = 0
        total_engagement = {"likes": 0, "shares": 0, "comments": 0, "views": 0}
        
        for data_point in sentiment_data:
            sentiment = data_point["sentiment"]
            sentiment_counts[sentiment] += 1
            total_sentiment_score += data_point["sentiment_score"]
            
            for metric in total_engagement:
                total_engagement[metric] += data_point["engagement"][metric]
        
        total_posts = len(sentiment_data)
        
        return {
            "total_posts": total_posts,
            "sentiment_distribution": sentiment_counts,
            "average_sentiment_score": total_sentiment_score / total_posts,
            "total_engagement": total_engagement,
            "sentiment_percentages": {
                k: (v / total_posts) * 100 for k, v in sentiment_counts.items()
            }
        }


# Enhanced MockProviderRegistry with new providers
class MockProviderRegistry:
    """Enhanced registry for all mock providers including news and sentiment."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("MockProviderRegistry")
        self._providers = {}
        
        # Register default providers
        self._register_default_providers()
        
        self.logger.info("MockProviderRegistry initialized")
    
    def _register_default_providers(self):
        """Register default mock providers."""
        # Register financial providers
        self.register_provider("finnhub", FinancialMockProvider)
        self.register_provider("yahoo_finance", FinancialMockProvider)
        self.register_provider("alpha_vantage", FinancialMockProvider)
        
        # Register market providers
        self.register_provider("market_data", MarketMockProvider)
        
        # Register social providers
        self.register_provider("twitter", SocialMockProvider)
        self.register_provider("facebook", SocialMockProvider)
        
        # Register new geopolitical news provider
        self.register_provider("geopolitical_news", GeopoliticalNewsProvider)
        
        # Register new social media sentiment provider
        self.register_provider("social_media_sentiment", SocialMediaSentimentProvider)
        
        self.logger.info("Registered default mock providers")
    
    def register_provider(self, name: str, provider_class: type, config: Optional[MockDataConfig] = None):
        """Register a new mock provider."""
        if name in self._providers:
            self.logger.warning(f"Provider {name} already registered")
            return
        
        try:
            provider = provider_class(config)
            self._providers[name] = provider
            self.logger.info(f"Registered mock provider: {name}")
        except Exception as e:
            self.logger.error(f"Failed to register provider {name}: {e}")
            raise ProviderError(f"Failed to register provider {name}: {e}")
    
    def get_provider(self, name: str) -> Optional[BaseMockProvider]:
        """Get provider by name."""
        return self._providers.get(name)
    
    def list_providers(self) -> List[str]:
        """List all available providers."""
        return list(self._providers.keys())
    
    def get_provider_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a provider."""
        provider = self.get_provider(name)
        if provider:
            return {
                "name": provider.name,
                "config": provider.config.__dict__,
                "type": provider.__class__.__name__
            }
        return None
    
    def get_all_providers_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all providers."""
        return {
            name: self.get_provider_info(name)
            for name in self.list_providers()
        }


# Global provider registry instance
_global_provider_registry: Optional[MockProviderRegistry] = None


def get_provider_registry(**kwargs) -> MockProviderRegistry:
    """
    Get or create global provider registry.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global MockProviderRegistry instance
    """
    global _global_provider_registry
    if _global_provider_registry is None:
        _global_provider_registry = MockProviderRegistry(**kwargs)
    return _global_provider_registry
