"""
U.S. Stock News and Detailed Data Providers
Real-time news and company-specific data for American stocks
"""

import asyncio
import aiohttp
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional

from tradfi_providers import TradFiBaseProvider, AsyncJitter
from infrastructure.data_normalization import UnifiedInternalSchema, DataType, SourceType


class SEC filingsProvider(TradFiBaseProvider):
    """SEC EDGAR filings - Official company disclosures."""
    
    def __init__(self):
        super().__init__("sec_filings", SourceType.REST)
        self.base_url = "https://www.sec.gov/Archives/edgar/data/"
        
    async def connect(self) -> bool:
        """Test SEC connection."""
        try:
            await super().connect()
            
            # Test SEC API
            test_url = "https://data.sec.gov/submissions/CIK0000320193.json"  # Apple CIK
            async with self.session.get(test_url) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"SEC connection error: {e}")
            return False
    
    async def get_data(self, symbol: str = "", **kwargs) -> List[UnifiedInternalSchema]:
        """Get SEC filings for company."""
        try:
            # Convert symbol to CIK (simplified mapping)
            cik_mapping = {
                "AAPL": "0000320193",
                "MSFT": "0000789019", 
                "GOOGL": "0001652044",
                "AMZN": "0001018724",
                "TSLA": "0001318605",
                "NVDA": "0001045810",
                "META": "0001326801",
                "BRK-B": "0001067983",
                "JPM": "0000019617"
            }
            
            cik = cik_mapping.get(symbol.upper(), "")
            if not cik:
                return []
            
            # Get company info
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                filings = []
                if 'filings' in data and 'recent' in data['filings']:
                    recent_filings = data['filings']['recent'][:5]  # Last 5 filings
                    
                    for filing in recent_filings:
                        filing_data = self.normalize_data({
                            'symbol': symbol,
                            'filing_type': filing.get('form', ''),
                            'filing_date': filing.get('filingDate', ''),
                            'company_name': data.get('name', ''),
                            'cik': cik,
                            'accession_number': filing.get('accessionNumber', ''),
                            'document_url': f"https://www.sec.gov/Archives/edgar/data/{cik}/{filing.get('accessionNumber', '')}"
                        })
                        filings.append(filing_data)
                
                return filings
                
        except Exception as e:
            print(f"SEC filings error: {e}")
            return []
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize SEC filing data."""
        date_str = raw_data.get('filing_date', '')
        if date_str:
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except:
                dt = datetime.now(timezone.utc)
        else:
            dt = datetime.now(timezone.utc)
        
        return UnifiedInternalSchema(
            data_type=DataType.NEWS,
            source=self.source_name,
            source_type=self.source_type,
            symbol=raw_data.get('symbol', ''),
            timestamp=dt,
            title=f"{raw_data.get('company_name', '')} - {raw_data.get('filing_type', '')}",
            content=f"SEC Filing: {raw_data.get('filing_type', '')} filed on {raw_data.get('filing_date', '')}",
            url=raw_data.get('document_url', ''),
            relevance_score=0.95,
            tags=["sec", "filing", "regulatory", raw_data.get('symbol', '').lower()],
            raw_data=raw_data,
            processing_latency_ms=3.0
        )


class YahooFinanceNewsProvider(TradFiBaseProvider):
    """Yahoo Finance news for specific stocks."""
    
    def __init__(self):
        super().__init__("yahoo_finance_news", SourceType.WEBSCRAPER)
        self.base_url = "https://finance.yahoo.com"
        
    async def connect(self) -> bool:
        """Test Yahoo Finance news connection."""
        try:
            await super().connect()
            
            # Test Yahoo Finance news
            test_url = "https://finance.yahoo.com/quote/AAPL/news"
            async with self.session.get(test_url) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"Yahoo Finance news connection error: {e}")
            return False
    
    async def get_data(self, symbol: str = "", **kwargs) -> List[UnifiedInternalSchema]:
        """Get Yahoo Finance news for specific stock."""
        try:
            if not symbol:
                return []
            
            url = f"https://finance.yahoo.com/quote/{symbol}/news"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    return []
                
                html_content = await response.text()
                
                # Parse Yahoo Finance news (simplified)
                news_items = []
                
                # Look for news items in HTML
                import re
                
                # Find news headlines (simplified regex approach)
                headline_pattern = r'"title":"([^"]+)"[^}]*"publisher":"([^"]+)"[^}]*"link":"([^"]+)"'
                matches = re.findall(headline_pattern, html_content)
                
                for i, (title, publisher, link) in enumerate(matches[:10]):  # Limit to 10 items
                    try:
                        news_item = UnifiedInternalSchema(
                            data_type=DataType.NEWS,
                            source=self.source_name,
                            source_type=self.source_type,
                            symbol=symbol,
                            timestamp=datetime.now(timezone.utc),
                            title=title,
                            content=f"Source: {publisher}",
                            url=link,
                            relevance_score=0.8,
                            tags=["yahoo", "finance", symbol.lower()],
                            raw_data={"title": title, "publisher": publisher, "link": link},
                            processing_latency_ms=2.5
                        )
                        news_items.append(news_item)
                        
                    except Exception as e:
                        print(f"Error parsing Yahoo news item: {e}")
                        continue
                
                return news_items
                
        except Exception as e:
            print(f"Yahoo Finance news error: {e}")
            return []


class SeekingAlphaProvider(TradFiBaseProvider):
    """Seeking Alpha - Premium financial news and analysis."""
    
    def __init__(self):
        super().__init__("seeking_alpha", SourceType.RSS)
        self.rss_feeds = {
            "general": "https://seekingalpha.com/market_currents.xml",
            "earnings": "https://seekingalpha.com/earnings.xml",
            "analysis": "https://seekingalpha.com/market_analysis.xml"
        }
        
    async def connect(self) -> bool:
        """Test Seeking Alpha connection."""
        try:
            await super().connect()
            
            # Test Seeking Alpha RSS
            test_url = self.rss_feeds["general"]
            async with self.session.get(test_url) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"Seeking Alpha connection error: {e}")
            return False
    
    async def get_data(self, symbol: str = "", **kwargs) -> List[UnifiedInternalSchema]:
        """Get Seeking Alpha news."""
        try:
            all_news = []
            
            for feed_name, feed_url in self.rss_feeds.items():
                try:
                    async with self.session.get(feed_url) as response:
                        if response.status != 200:
                            continue
                        
                        xml_content = await response.text()
                        
                        # Parse RSS XML
                        root = ET.fromstring(xml_content)
                        
                        # Find all items
                        items = root.findall('.//item')
                        
                        for item in items[:15]:  # Limit to 15 items per feed
                            try:
                                title_elem = item.find('title')
                                title = title_elem.text if title_elem is not None else ''
                                
                                desc_elem = item.find('description')
                                description = desc_elem.text if desc_elem is not None else ''
                                
                                link_elem = item.find('link')
                                url = link_elem.text if link_elem is not None else ''
                                
                                # Parse date
                                date_elem = item.find('pubDate')
                                if date_elem is not None:
                                    date_str = date_elem.text
                                    try:
                                        dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z').replace(tzinfo=timezone.utc)
                                    except:
                                        dt = datetime.now(timezone.utc)
                                else:
                                    dt = datetime.now(timezone.utc)
                                
                                # Filter by symbol if provided
                                if symbol and symbol.upper() not in title.upper():
                                    continue
                                
                                news_item = UnifiedInternalSchema(
                                    data_type=DataType.NEWS,
                                    source=self.source_name,
                                    source_type=self.source_type,
                                    symbol=symbol,
                                    timestamp=dt,
                                    title=title,
                                    content=description,
                                    url=url,
                                    relevance_score=0.85,
                                    tags=["seeking_alpha", feed_name, symbol.lower()],
                                    raw_data={"title": title, "description": description, "url": url},
                                    processing_latency_ms=2.8
                                )
                                
                                all_news.append(news_item)
                                
                            except Exception as e:
                                print(f"Error parsing Seeking Alpha item: {e}")
                                continue
                    
                    await asyncio.sleep(0.5)  # Small delay between feeds
                    
                except Exception as e:
                    print(f"Error fetching {feed_name}: {e}")
                    continue
            
            # Sort by timestamp and limit
            all_news.sort(key=lambda x: x.timestamp, reverse=True)
            return all_news[:50]  # Return latest 50 items
            
        except Exception as e:
            print(f"Seeking Alpha error: {e}")
            return []


class BenzingaProvider(TradFiBaseProvider):
    """Benzinga - Fast-breaking financial news."""
    
    def __init__(self):
        super().__init__("benzinga", SourceType.REST)
        self.base_url = "https://www.benzinga.com/api/v1"
        
    async def connect(self) -> bool:
        """Test Benzinga connection."""
        try:
            await super().connect()
            
            # Test Benzinga API (free tier)
            test_url = f"{self.base_url}/news"
            async with self.session.get(test_url) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"Benzinga connection error: {e}")
            return False
    
    async def get_data(self, symbol: str = "", **kwargs) -> List[UnifiedInternalSchema]:
        """Get Benzinga news."""
        try:
            url = f"{self.base_url}/news"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                news_items = []
                if 'news' in data and isinstance(data['news'], list):
                    for article in data['news'][:25]:  # Limit to 25 items
                        try:
                            title = article.get('title', '')
                            description = article.get('body', article.get('teaser', ''))
                            url = article.get('links', {}).get('permalink', '')
                            
                            # Parse date
                            created_at = article.get('createdAt', '')
                            if created_at:
                                try:
                                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
                                except:
                                    dt = datetime.now(timezone.utc)
                            else:
                                dt = datetime.now(timezone.utc)
                            
                            # Filter by symbol if provided
                            if symbol and symbol.upper() not in title.upper():
                                continue
                            
                            # Get related symbols
                            symbols = article.get('symbols', [])
                            if isinstance(symbols, list):
                                symbols_str = ','.join(symbols[:5])  # Limit to 5 symbols
                            else:
                                symbols_str = symbol
                            
                            news_item = UnifiedInternalSchema(
                                data_type=DataType.NEWS,
                                source=self.source_name,
                                source_type=self.source_type,
                                symbol=symbols_str,
                                timestamp=dt,
                                title=title,
                                content=description,
                                url=url,
                                relevance_score=0.9,
                                tags=["benzinga", "breaking-news", symbol.lower()],
                                raw_data={"title": title, "description": description, "url": url},
                                processing_latency_ms=2.2
                            )
                            
                            news_items.append(news_item)
                            
                        except Exception as e:
                            print(f"Error parsing Benzinga article: {e}")
                            continue
                
                return news_items
                
        except Exception as e:
            print(f"Benzinga error: {e}")
            return []


class MarketWatchProvider(TradFiBaseProvider):
    """MarketWatch - Financial news and market data."""
    
    def __init__(self):
        super().__init__("marketwatch", SourceType.RSS)
        self.rss_feeds = {
            "top_news": "https://www.marketwatch.com/rss/topstories",
            "market_news": "https://www.marketwatch.com/rss/marketpulse",
            "stock_news": "https://www.marketwatch.com/rss/stockmarketnews"
        }
        
    async def connect(self) -> bool:
        """Test MarketWatch connection."""
        try:
            await super().connect()
            
            # Test MarketWatch RSS
            test_url = self.rss_feeds["top_news"]
            async with self.session.get(test_url) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"MarketWatch connection error: {e}")
            return False
    
    async def get_data(self, symbol: str = "", **kwargs) -> List[UnifiedInternalSchema]:
        """Get MarketWatch news."""
        try:
            all_news = []
            
            for feed_name, feed_url in self.rss_feeds.items():
                try:
                    async with self.session.get(feed_url) as response:
                        if response.status != 200:
                            continue
                        
                        xml_content = await response.text()
                        
                        # Parse RSS XML
                        root = ET.fromstring(xml_content)
                        
                        # Find all items
                        items = root.findall('.//item')
                        
                        for item in items[:15]:  # Limit to 15 items per feed
                            try:
                                title_elem = item.find('title')
                                title = title_elem.text if title_elem is not None else ''
                                
                                desc_elem = item.find('description')
                                description = desc_elem.text if desc_elem is not None else ''
                                
                                link_elem = item.find('link')
                                url = link_elem.text if link_elem is not None else ''
                                
                                # Parse date
                                date_elem = item.find('pubDate')
                                if date_elem is not None:
                                    date_str = date_elem.text
                                    try:
                                        dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z').replace(tzinfo=timezone.utc)
                                    except:
                                        dt = datetime.now(timezone.utc)
                                else:
                                    dt = datetime.now(timezone.utc)
                                
                                # Filter by symbol if provided
                                if symbol and symbol.upper() not in title.upper():
                                    continue
                                
                                news_item = UnifiedInternalSchema(
                                    data_type=DataType.NEWS,
                                    source=self.source_name,
                                    source_type=self.source_type,
                                    symbol=symbol,
                                    timestamp=dt,
                                    title=title,
                                    content=description,
                                    url=url,
                                    relevance_score=0.8,
                                    tags=["marketwatch", feed_name, symbol.lower()],
                                    raw_data={"title": title, "description": description, "url": url},
                                    processing_latency_ms=2.6
                                )
                                
                                all_news.append(news_item)
                                
                            except Exception as e:
                                print(f"Error parsing MarketWatch item: {e}")
                                continue
                    
                    await asyncio.sleep(0.5)  # Small delay between feeds
                    
                except Exception as e:
                    print(f"Error fetching {feed_name}: {e}")
                    continue
            
            # Sort by timestamp and limit
            all_news.sort(key=lambda x: x.timestamp, reverse=True)
            return all_news[:40]  # Return latest 40 items
            
        except Exception as e:
            print(f"MarketWatch error: {e}")
            return []


# Factory for U.S. stock news providers
class USStockNewsFactory:
    """Factory for U.S. stock news and data providers."""
    
    def __init__(self):
        self._providers = {
            "sec_filings": SEC filingsProvider,
            "yahoo_finance_news": YahooFinanceNewsProvider,
            "seeking_alpha": SeekingAlphaProvider,
            "benzinga": BenzingaProvider,
            "marketwatch": MarketWatchProvider,
        }
    
    def create_provider(self, name: str) -> TradFiBaseProvider:
        """Create a provider instance."""
        if name not in self._providers:
            raise ValueError(f"Unknown provider: {name}")
        
        return self._providers[name]()
    
    def list_providers(self) -> List[str]:
        """List available providers."""
        return list(self._providers.keys())


# Global factory instance
_us_stock_news_factory: Optional[USStockNewsFactory] = None


def get_us_stock_news_factory() -> USStockNewsFactory:
    """Get global factory instance."""
    global _us_stock_news_factory
    if _us_stock_news_factory is None:
        _us_stock_news_factory = USStockNewsFactory()
    return _us_stock_news_factory


async def main():
    """Test U.S. stock news providers."""
    factory = get_us_stock_news_factory()
    
    print("Testing U.S. Stock News and Data Providers")
    print("=" * 60)
    
    # Test SEC Filings
    print("\n1. Testing SEC Filings (AAPL):")
    try:
        provider = factory.create_provider("sec_filings")
        connected = await provider.connect()
        if connected:
            data = await provider.get_data("AAPL")
            print(f"   Connected: {connected}, Filings: {len(data)}")
            for filing in data[:2]:
                print(f"   {filing.title[:50]}...")
        await provider.disconnect()
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test Seeking Alpha
    print("\n2. Testing Seeking Alpha:")
    try:
        provider = factory.create_provider("seeking_alpha")
        connected = await provider.connect()
        if connected:
            data = await provider.get_data("AAPL")
            print(f"   Connected: {connected}, News: {len(data)}")
            for news in data[:2]:
                print(f"   {news.title[:50]}...")
        await provider.disconnect()
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test Benzinga
    print("\n3. Testing Benzinga:")
    try:
        provider = factory.create_provider("benzinga")
        connected = await provider.connect()
        if connected:
            data = await provider.get_data("TSLA")
            print(f"   Connected: {connected}, News: {len(data)}")
            for news in data[:2]:
                print(f"   {news.title[:50]}...")
        await provider.disconnect()
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test MarketWatch
    print("\n4. Testing MarketWatch:")
    try:
        provider = factory.create_provider("marketwatch")
        connected = await provider.connect()
        if connected:
            data = await provider.get_data("MSFT")
            print(f"   Connected: {connected}, News: {len(data)}")
            for news in data[:2]:
                print(f"   {news.title[:50]}...")
        await provider.disconnect()
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\nU.S. Stock News providers test completed!")


if __name__ == "__main__":
    asyncio.run(main())
