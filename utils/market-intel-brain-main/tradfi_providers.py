"""
TradFi & Macro Economics Providers
Async Polling Architecture with Circuit Breaker & Adaptive Jitter
"""

import asyncio
import random
import time
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yfinance as yf
from fredapi import Fred
from fake_useragent import UserAgent
import aiohttp
import ssl
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup

from infrastructure.data_normalization import BaseProvider, UnifiedInternalSchema, DataType, SourceType


class CircuitBreaker:
    """Circuit breaker pattern for API resilience."""
    
    def __init__(self, failure_threshold: int = 5, timeout_minutes: int = 10):
        self.failure_threshold = failure_threshold
        self.timeout_minutes = timeout_minutes
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout_minutes * 60:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            
            raise e


class AsyncJitter:
    """Adaptive jitter for rate limiting protection."""
    
    @staticmethod
    def get_jitter(base_delay: float, min_jitter: float = 3.0, max_jitter: float = 7.0) -> float:
        """Get adaptive jitter between 3-7 seconds."""
        jitter = random.uniform(min_jitter, max_jitter)
        return base_delay + jitter


class TradFiBaseProvider(BaseProvider):
    """Enhanced BaseProvider for TradFi with async polling."""
    
    def __init__(self, name: str, source_type: SourceType = SourceType.REST):
        super().__init__(name, source_type)
        self.circuit_breaker = CircuitBreaker()
        self.session = None
        self.user_agent = UserAgent().random
        
    async def connect(self) -> bool:
        """Create HTTP session with proper headers."""
        try:
            self.session = aiohttp.ClientSession(
                headers={'User-Agent': self.user_agent},
                timeout=aiohttp.ClientTimeout(total=30),
                connector=aiohttp.TCPConnector(ssl=ssl.create_default_context())
            )
            return True
        except Exception as e:
            print(f"Connection failed for {self.source_name}: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _make_request(self, url: str, method: str = "GET", **kwargs) -> Optional[Dict]:
        """Make HTTP request with circuit breaker and jitter."""
        if not self.session:
            raise Exception("Not connected")
        
        async def _request():
            await asyncio.sleep(AsyncJitter.get_jitter(0))  # Adaptive jitter
            
            async with self.session.request(method, url, **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"HTTP {response.status}: {url}")
        
        return await self.circuit_breaker.call(_request)


class YahooFinanceProvider(TradFiBaseProvider):
    """Yahoo Finance provider using yfinance with async wrapper."""
    
    def __init__(self):
        super().__init__("yahoo_finance", SourceType.REST)
        self.cache = {}
        self.cache_duration = timedelta(minutes=60)  # 1 hour cache
    
    async def get_data(self, symbol: str, **kwargs) -> List[UnifiedInternalSchema]:
        """Get stock data from Yahoo Finance."""
        try:
            # Check cache
            cache_key = f"{symbol}_stock"
            now = datetime.now(timezone.utc)
            
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if now - cached_time < self.cache_duration:
                    return [cached_data]
            
            # Fetch data using yfinance
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info or 'regularMarketPrice' not in info:
                return []
            
            # Normalize data
            normalized_data = self.normalize_data({
                'symbol': symbol,
                'price': info.get('regularMarketPrice', 0),
                'volume': info.get('regularMarketVolume', 0),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'dividend_yield': info.get('dividendYield', 0),
                '52_week_high': info.get('fiftyTwoWeekHigh', 0),
                '52_week_low': info.get('fiftyTwoWeekLow', 0)
            })
            
            # Update cache
            self.cache[cache_key] = (normalized_data, now)
            
            return [normalized_data]
            
        except Exception as e:
            print(f"Yahoo Finance error for {symbol}: {e}")
            return []
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize Yahoo Finance data."""
        return UnifiedInternalSchema(
            data_type=DataType.EQUITY,
            source=self.source_name,
            source_type=self.source_type,
            symbol=raw_data.get('symbol', ''),
            timestamp=datetime.now(timezone.utc),
            price=Decimal(str(raw_data.get('price', '0'))),
            volume=Decimal(str(raw_data.get('volume', '0'))),
            market_cap=Decimal(str(raw_data.get('market_cap', '0'))),
            pe_ratio=Decimal(str(raw_data.get('pe_ratio', '0'))),
            dividend_yield=Decimal(str(raw_data.get('dividend_yield', '0'))),
            week_52_high=Decimal(str(raw_data.get('52_week_high', '0'))),
            week_52_low=Decimal(str(raw_data.get('52_week_low', '0'))),
            raw_data=raw_data,
            processing_latency_ms=2.5
        )


class GoogleNewsScraper(TradFiBaseProvider):
    """Google News scraper with fake user agent."""
    
    def __init__(self):
        super().__init__("google_news", SourceType.WEBSCRAPER)
        self.base_url = "https://news.google.com"
        self.cache = {}
        self.cache_duration = timedelta(hours=6)  # 6 hour cache
    
    async def get_data(self, symbol: str, **kwargs) -> List[UnifiedInternalSchema]:
        """Scrape news for symbol from Google News."""
        try:
            # Check cache
            cache_key = f"{symbol}_news"
            now = datetime.now(timezone.utc)
            
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if now - cached_time < self.cache_duration:
                    return cached_data
            
            # Search for news
            search_url = f"{self.base_url}/search?q={quote(symbol)}%20stock&hl=en-US&gl=US&ceid=US:en"
            
            async def _scrape():
                await asyncio.sleep(AsyncJitter.get_jitter(0))
                
                async with self.session.get(search_url) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._parse_news_html(html, symbol)
                    else:
                        raise Exception(f"HTTP {response.status}")
            
            news_items = await self.circuit_breaker.call(_scrape)
            
            # Update cache
            self.cache[cache_key] = (news_items, now)
            
            return news_items
            
        except Exception as e:
            print(f"Google News scraper error for {symbol}: {e}")
            return []
    
    def _parse_news_html(self, html: str, symbol: str) -> List[UnifiedInternalSchema]:
        """Parse Google News HTML."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            news_items = []
            
            # Find news articles (simplified parsing)
            articles = soup.find_all('article')[:10]  # Limit to 10 articles
            
            for article in articles:
                try:
                    title_elem = article.find('h3') or article.find('h4')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    link_elem = article.find('a')
                    url = link_elem.get('href') if link_elem else ''
                    
                    # Try to find time
                    time_elem = article.find('time')
                    timestamp_str = time_elem.get('datetime') if time_elem else ''
                    
                    if timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
                    else:
                        timestamp = datetime.now(timezone.utc)
                    
                    news_item = UnifiedInternalSchema(
                        data_type=DataType.NEWS,
                        source=self.source_name,
                        source_type=self.source_type,
                        symbol=symbol,
                        timestamp=timestamp,
                        title=title,
                        url=url,
                        content='',  # Google News doesn't provide full content
                        relevance_score=0.8,
                        tags=["news", "finance"],
                        raw_data={"title": title, "url": url},
                        processing_latency_ms=3.0
                    )
                    
                    news_items.append(news_item)
                    
                except Exception as e:
                    print(f"Error parsing article: {e}")
                    continue
            
            return news_items
            
        except Exception as e:
            print(f"Error parsing HTML: {e}")
            return []


class FREDProvider(TradFiBaseProvider):
    """Federal Reserve Economic Data provider."""
    
    def __init__(self):
        super().__init__("fred", SourceType.REST)
        self.fred = None
        self.cache = {}
        self.cache_duration = timedelta(hours=24)  # 24 hour cache
    
    async def connect(self) -> bool:
        """Initialize FRED API."""
        try:
            # FRED API key from environment
            import os
            api_key = os.getenv('FRED_API_KEY')
            
            if api_key:
                self.fred = Fred(api_key=api_key)
            else:
                # Use without API key (limited)
                self.fred = Fred()
            
            return True
        except Exception as e:
            print(f"FRED connection failed: {e}")
            return False
    
    async def get_data(self, series_id: str, **kwargs) -> List[UnifiedInternalSchema]:
        """Get economic data from FRED."""
        try:
            # Check cache
            cache_key = f"fred_{series_id}"
            now = datetime.now(timezone.utc)
            
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if now - cached_time < self.cache_duration:
                    return [cached_data]
            
            # Fetch data
            def _fetch_data():
                data = self.fred.get_series(series_id)
                if not data.empty:
                    latest_value = data.iloc[-1]
                    return {
                        'series_id': series_id,
                        'value': latest_value,
                        'date': data.index[-1]
                    }
                return None
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _fetch_data)
            
            if not result:
                return []
            
            # Normalize data
            normalized_data = self.normalize_data(result)
            
            # Update cache
            self.cache[cache_key] = (normalized_data, now)
            
            return [normalized_data]
            
        except Exception as e:
            print(f"FRED error for {series_id}: {e}")
            return []
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize FRED data."""
        return UnifiedInternalSchema(
            data_type=DataType.MACRO,
            source=self.source_name,
            source_type=self.source_type,
            symbol=raw_data.get('series_id', ''),
            timestamp=raw_data.get('date', datetime.now(timezone.utc)),
            value=Decimal(str(raw_data.get('value', '0'))),
            raw_data=raw_data,
            processing_latency_ms=1.5
        )


class EconDBProvider(TradFiBaseProvider):
    """Economic Database provider (open data)."""
    
    def __init__(self):
        super().__init__("econdb", SourceType.REST)
        self.base_url = "https://api.econdb.com"
        self.cache = {}
        self.cache_duration = timedelta(hours=24)
    
    async def get_data(self, indicator: str, country: str = "US", **kwargs) -> List[UnifiedInternalSchema]:
        """Get economic indicators from EconDB."""
        try:
            cache_key = f"econdb_{country}_{indicator}"
            now = datetime.now(timezone.utc)
            
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if now - cached_time < self.cache_duration:
                    return [cached_data]
            
            url = f"{self.base_url}/api/v1/series/{country}.{indicator}"
            
            data = await self._make_request(url)
            if not data or 'data' not in data:
                return []
            
            latest_data = data['data'][-1] if data['data'] else {}
            
            normalized_data = self.normalize_data({
                'indicator': indicator,
                'country': country,
                'value': latest_data.get('value', 0),
                'date': latest_data.get('date', datetime.now(timezone.utc))
            })
            
            self.cache[cache_key] = (normalized_data, now)
            return [normalized_data]
            
        except Exception as e:
            print(f"EconDB error for {indicator}: {e}")
            return []
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize EconDB data."""
        return UnifiedInternalSchema(
            data_type=DataType.MACRO,
            source=self.source_name,
            source_type=self.source_type,
            symbol=f"{raw_data.get('country', '')}.{raw_data.get('indicator', '')}",
            timestamp=raw_data.get('date', datetime.now(timezone.utc)),
            value=Decimal(str(raw_data.get('value', '0'))),
            raw_data=raw_data,
            processing_latency_ms=2.0
        )


class EuroStatProvider(TradFiBaseProvider):
    """EuroStat provider for European economic data."""
    
    def __init__(self):
        super().__init__("eurostat", SourceType.REST)
        self.base_url = "https://ec.europa.eu/eurostat/api"
        self.cache = {}
        self.cache_duration = timedelta(hours=24)
    
    async def get_data(self, dataset: str, **kwargs) -> List[UnifiedInternalSchema]:
        """Get data from EuroStat."""
        try:
            cache_key = f"eurostat_{dataset}"
            now = datetime.now(timezone.utc)
            
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if now - cached_time < self.cache_duration:
                    return [cached_data]
            
            url = f"{self.base_url}/dissemination/statistics/1.0/data/{dataset}"
            
            async def _fetch():
                await asyncio.sleep(AsyncJitter.get_jitter(0))
                
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_eurostat_data(data, dataset)
                    else:
                        raise Exception(f"HTTP {response.status}")
            
            result = await self.circuit_breaker.call(_fetch)
            
            if result:
                self.cache[cache_key] = (result[0], now)
                return result
            
            return []
            
        except Exception as e:
            print(f"EuroStat error for {dataset}: {e}")
            return []
    
    def _parse_eurostat_data(self, data: Dict, dataset: str) -> List[UnifiedInternalSchema]:
        """Parse EuroStat JSON data."""
        try:
            if 'value' not in data:
                return []
            
            # Get latest value (simplified)
            values = data['value']
            if not values:
                return []
            
            latest_value = list(values.values())[-1] if values else 0
            
            normalized_data = UnifiedInternalSchema(
                data_type=DataType.MACRO,
                source=self.source_name,
                source_type=self.source_type,
                symbol=dataset,
                timestamp=datetime.now(timezone.utc),
                value=Decimal(str(latest_value)),
                raw_data=data,
                processing_latency_ms=2.5
            )
            
            return [normalized_data]
            
        except Exception as e:
            print(f"Error parsing EuroStat data: {e}")
            return []


class IMFProvider(TradFiBaseProvider):
    """International Monetary Fund provider."""
    
    def __init__(self):
        super().__init__("imf", SourceType.REST)
        self.base_url = "https://dataservices.imf.org/REST/SDMX_JSON.svc"
        self.cache = {}
        self.cache_duration = timedelta(hours=24)
    
    async def get_data(self, indicator: str, country: str = "US", **kwargs) -> List[UnifiedInternalSchema]:
        """Get data from IMF."""
        try:
            cache_key = f"imf_{country}_{indicator}"
            now = datetime.now(timezone.utc)
            
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if now - cached_time < self.cache_duration:
                    return [cached_data]
            
            # IMF API endpoint
            url = f"{self.base_url}/CompactData/{indicator}.{country}"
            
            data = await self._make_request(url)
            if not data or 'CompactData' not in data:
                return []
            
            compact_data = data['CompactData']
            if not compact_data or 'DataSet' not in compact_data:
                return []
            
            dataset = compact_data['DataSet']
            if not dataset or 'Series' not in dataset:
                return []
            
            series = dataset['Series']
            if not series:
                return []
            
            # Get latest observation
            observations = series.get('Obs', [])
            if not observations:
                return []
            
            latest_obs = observations[-1]
            
            normalized_data = self.normalize_data({
                'indicator': indicator,
                'country': country,
                'value': latest_obs.get('@OBS_VALUE', 0),
                'date': latest_obs.get('@TIME_PERIOD', datetime.now(timezone.utc))
            })
            
            self.cache[cache_key] = (normalized_data, now)
            return [normalized_data]
            
        except Exception as e:
            print(f"IMF error for {indicator}: {e}")
            return []
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize IMF data."""
        return UnifiedInternalSchema(
            data_type=DataType.MACRO,
            source=self.source_name,
            source_type=self.source_type,
            symbol=f"{raw_data.get('country', '')}.{raw_data.get('indicator', '')}",
            timestamp=raw_data.get('date', datetime.now(timezone.utc)),
            value=Decimal(str(raw_data.get('value', '0'))),
            raw_data=raw_data,
            processing_latency_ms=3.0
        )


class RSSNewsProvider(TradFiBaseProvider):
    """RSS News provider for financial news feeds."""
    
    def __init__(self):
        super().__init__("rss_news", SourceType.RSS)
        self.feeds = [
            "https://feeds.finance.yahoo.com/rss/2.0/headline",
            "https://www.reuters.com/rssFeed/worldNews",
            "https://feeds.bloomberg.com/markets/news.rss"
        ]
        self.cache = {}
        self.cache_duration = timedelta(minutes=30)
    
    async def get_data(self, symbol: str = "", **kwargs) -> List[UnifiedInternalSchema]:
        """Get news from RSS feeds."""
        try:
            cache_key = "rss_news_all"
            now = datetime.now(timezone.utc)
            
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if now - cached_time < self.cache_duration:
                    return cached_data
            
            all_news = []
            
            for feed_url in self.feeds:
                try:
                    async def _fetch_feed():
                        await asyncio.sleep(AsyncJitter.get_jitter(0))
                        
                        async with self.session.get(feed_url) as response:
                            if response.status == 200:
                                xml_content = await response.text()
                                return self._parse_rss_feed(xml_content, feed_url)
                            else:
                                raise Exception(f"HTTP {response.status}")
                    
                    news_items = await self.circuit_breaker.call(_fetch_feed)
                    all_news.extend(news_items)
                    
                except Exception as e:
                    print(f"RSS feed error for {feed_url}: {e}")
                    continue
            
            # Filter by symbol if provided
            if symbol:
                all_news = [item for item in all_news 
                           if symbol.upper() in item.title.upper() 
                           or symbol.upper() in item.content.upper()]
            
            self.cache[cache_key] = (all_news, now)
            return all_news
            
        except Exception as e:
            print(f"RSS News error: {e}")
            return []
    
    def _parse_rss_feed(self, xml_content: str, feed_url: str) -> List[UnifiedInternalSchema]:
        """Parse RSS XML content."""
        try:
            import xml.etree.ElementTree as ET
            
            root = ET.fromstring(xml_content)
            news_items = []
            
            # Find all items
            items = root.findall('.//item')
            
            for item in items[:20]:  # Limit to 20 items per feed
                try:
                    title = item.find('title').text if item.find('title') is not None else ''
                    description = item.find('description').text if item.find('description') is not None else ''
                    link = item.find('link').text if item.find('link') is not None else ''
                    
                    # Parse date
                    date_elem = item.find('pubDate') or item.find('pubdate')
                    if date_elem is not None:
                        date_str = date_elem.text
                        try:
                            timestamp = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z').replace(tzinfo=timezone.utc)
                        except:
                            timestamp = datetime.now(timezone.utc)
                    else:
                        timestamp = datetime.now(timezone.utc)
                    
                    news_item = UnifiedInternalSchema(
                        data_type=DataType.NEWS,
                        source=self.source_name,
                        source_type=self.source_type,
                        symbol="",  # RSS feeds don't have specific symbols
                        timestamp=timestamp,
                        title=title,
                        content=description,
                        url=link,
                        relevance_score=0.7,
                        tags=["rss", "news", "finance"],
                        raw_data={"title": title, "description": description, "link": link},
                        processing_latency_ms=1.5
                    )
                    
                    news_items.append(news_item)
                    
                except Exception as e:
                    print(f"Error parsing RSS item: {e}")
                    continue
            
            return news_items
            
        except Exception as e:
            print(f"Error parsing RSS feed: {e}")
            return []


# Factory for TradFi providers
class TradFiProviderFactory:
    """Factory for creating TradFi providers."""
    
    def __init__(self):
        self._providers = {
            "yahoo_finance": YahooFinanceProvider,
            "google_news": GoogleNewsScraper,
            "fred": FREDProvider,
            "econdb": EconDBProvider,
            "eurostat": EuroStatProvider,
            "imf": IMFProvider,
            "rss_news": RSSNewsProvider,
        }
    
    def create_provider(self, name: str) -> TradFiBaseProvider:
        """Create a TradFi provider instance."""
        if name not in self._providers:
            raise ValueError(f"Unknown TradFi provider: {name}")
        
        return self._providers[name]()
    
    def list_providers(self) -> List[str]:
        """List available TradFi providers."""
        return list(self._providers.keys())


# Global factory instance
_tradfi_provider_factory: Optional[TradFiProviderFactory] = None


def get_tradfi_provider_factory() -> TradFiProviderFactory:
    """Get global TradFi provider factory."""
    global _tradfi_provider_factory
    if _tradfi_provider_factory is None:
        _tradfi_provider_factory = TradFiProviderFactory()
    return _tradfi_provider_factory


async def main():
    """Test TradFi providers."""
    factory = get_tradfi_provider_factory()
    
    print("Testing TradFi Providers...")
    
    # Test Yahoo Finance
    print("\n1. Testing Yahoo Finance...")
    yahoo_provider = factory.create_provider("yahoo_finance")
    await yahoo_provider.connect()
    
    data = await yahoo_provider.get_data("AAPL")
    print(f"   AAPL data: {len(data)} items")
    if data:
        print(f"   Price: {data[0].price}, Volume: {data[0].volume}")
    
    await yahoo_provider.disconnect()
    
    # Test FRED
    print("\n2. Testing FRED...")
    fred_provider = factory.create_provider("fred")
    await fred_provider.connect()
    
    data = await fred_provider.get_data("GDP")
    print(f"   GDP data: {len(data)} items")
    if data:
        print(f"   Latest GDP: {data[0].value}")
    
    await fred_provider.disconnect()
    
    # Test RSS News
    print("\n3. Testing RSS News...")
    rss_provider = factory.create_provider("rss_news")
    await rss_provider.connect()
    
    data = await rss_provider.get_data()
    print(f"   RSS news: {len(data)} items")
    
    await rss_provider.disconnect()
    
    print("\nTradFi providers test completed!")


if __name__ == "__main__":
    asyncio.run(main())
