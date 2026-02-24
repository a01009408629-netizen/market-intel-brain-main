"""
Authenticated REST API Providers
7 APIs with strict rate limiting and token bucket management
"""

import asyncio
import aiohttp
import ssl
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from decimal import Decimal
import json

from tradfi_providers import TradFiBaseProvider, AsyncJitter
from token_bucket_limiter import get_token_bucket_limiter, APIProvider
from infrastructure.data_normalization import UnifiedInternalSchema, DataType, SourceType
from infrastructure.secrets_manager import get_secrets_manager


class AlphaVantageProvider(TradFiBaseProvider):
    """Alpha Vantage provider with strict 25/day limit."""
    
    def __init__(self):
        super().__init__("alpha_vantage", SourceType.REST)
        self.base_url = "https://www.alphavantage.co/query"
        self.secrets = get_secrets_manager()
        self.api_key = None
        self.rate_limiter = get_token_bucket_limiter()
        
    async def connect(self) -> bool:
        """Connect with API key."""
        try:
            self.api_key = self.secrets.get_secret("ALPHAVANTAGE_API_KEY")
            if not self.api_key:
                print("Alpha Vantage API key not found")
                return False
            
            # Test connection with minimal request
            await super().connect()
            
            # Test API key validity
            test_url = f"{self.base_url}?function=GLOBAL_QUOTE&symbol=IBM&apikey={self.api_key}"
            async with self.session.get(test_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if "Error Message" in data:
                        print(f"Alpha Vantage API error: {data['Error Message']}")
                        return False
                    return True
                else:
                    print(f"Alpha Vantage HTTP error: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"Alpha Vantage connection error: {e}")
            return False
    
    async def get_data(self, symbol: str, **kwargs) -> List[UnifiedInternalSchema]:
        """Get stock quote with rate limiting."""
        try:
            # Check rate limit
            if not await self.rate_limiter.can_consume(APIProvider.ALPHA_VANTAGE):
                wait_time = self.rate_limiter.get_wait_time(APIProvider.ALPHA_VANTAGE)
                print(f"Alpha Vantage rate limited, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                
                if not await self.rate_limiter.can_consume(APIProvider.ALPHA_VANTAGE):
                    return []
            
            # Make request
            url = f"{self.base_url}?function=GLOBAL_QUOTE&symbol={symbol}&apikey={self.api_key}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    print(f"Alpha Vantage HTTP error: {response.status}")
                    return []
                
                data = await response.json()
                
                if "Error Message" in data:
                    print(f"Alpha Vantage API error: {data['Error Message']}")
                    return []
                
                # Parse quote
                quote = data.get("Global Quote", {})
                if not quote:
                    return []
                
                return [self.normalize_data({
                    'symbol': symbol,
                    'price': quote.get('05. price', '0'),
                    'change': quote.get('09. change', '0'),
                    'change_percent': quote.get('10. change percent', '0').replace('%', ''),
                    'volume': quote.get('06. volume', '0'),
                    'open': quote.get('02. open', '0'),
                    'high': quote.get('03. high', '0'),
                    'low': quote.get('04. low', '0'),
                    'previous_close': quote.get('08. previous close', '0')
                })]
                
        except Exception as e:
            print(f"Alpha Vantage data fetch error: {e}")
            return []
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize Alpha Vantage data."""
        return UnifiedInternalSchema(
            data_type=DataType.EQUITY,
            source=self.source_name,
            source_type=self.source_type,
            symbol=raw_data.get('symbol', ''),
            timestamp=datetime.now(timezone.utc),
            price=Decimal(str(raw_data.get('price', '0').replace(',', ''))),
            volume=Decimal(str(raw_data.get('volume', '0').replace(',', ''))),
            open_price=Decimal(str(raw_data.get('open', '0').replace(',', ''))),
            high_price=Decimal(str(raw_data.get('high', '0').replace(',', ''))),
            low_price=Decimal(str(raw_data.get('low', '0').replace(',', ''))),
            change=Decimal(str(raw_data.get('change', '0').replace(',', ''))),
            change_percent=Decimal(str(raw_data.get('change_percent', '0').replace('%', ''))),
            raw_data=raw_data,
            processing_latency_ms=3.0
        )


class FinnhubProvider(TradFiBaseProvider):
    """Finnhub provider with 1/sec rate limit."""
    
    def __init__(self):
        super().__init__("finnhub", SourceType.REST)
        self.base_url = "https://finnhub.io/api/v1"
        self.secrets = get_secrets_manager()
        self.api_key = None
        self.rate_limiter = get_token_bucket_limiter()
        
    async def connect(self) -> bool:
        """Connect with API key."""
        try:
            self.api_key = self.secrets.get_secret("FINNHUB_API_KEY")
            if not self.api_key:
                print("Finnhub API key not found")
                return False
            
            await super().connect()
            
            # Test API key
            test_url = f"{self.base_url}/quote?symbol=AAPL&token={self.api_key}"
            async with self.session.get(test_url) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"Finnhub connection error: {e}")
            return False
    
    async def get_data(self, symbol: str, **kwargs) -> List[UnifiedInternalSchema]:
        """Get quote with rate limiting."""
        try:
            # Check rate limit
            if not await self.rate_limiter.can_consume(APIProvider.FINNHUB):
                wait_time = self.rate_limiter.get_wait_time(APIProvider.FINNHUB)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                
                if not await self.rate_limiter.can_consume(APIProvider.FINNHUB):
                    return []
            
            # Make request
            url = f"{self.base_url}/quote?symbol={symbol}&token={self.api_key}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                if not data or 'c' not in data:
                    return []
                
                return [self.normalize_data({
                    'symbol': symbol,
                    'current_price': data.get('c', 0),
                    'change': data.get('d', 0),
                    'change_percent': data.get('dp', 0),
                    'high': data.get('h', 0),
                    'low': data.get('l', 0),
                    'open': data.get('o', 0),
                    'previous_close': data.get('pc', 0),
                    'timestamp': data.get('t', 0)
                })]
                
        except Exception as e:
            print(f"Finnhub data fetch error: {e}")
            return []
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize Finnhub data."""
        timestamp = raw_data.get('timestamp', 0)
        if timestamp:
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        else:
            dt = datetime.now(timezone.utc)
        
        return UnifiedInternalSchema(
            data_type=DataType.EQUITY,
            source=self.source_name,
            source_type=self.source_type,
            symbol=raw_data.get('symbol', ''),
            timestamp=dt,
            price=Decimal(str(raw_data.get('current_price', 0))),
            change=Decimal(str(raw_data.get('change', 0))),
            change_percent=Decimal(str(raw_data.get('change_percent', 0))),
            high_price=Decimal(str(raw_data.get('high', 0))),
            low_price=Decimal(str(raw_data.get('low', 0))),
            open_price=Decimal(str(raw_data.get('open', 0))),
            raw_data=raw_data,
            processing_latency_ms=2.5
        )


class TwelveDataProvider(TradFiBaseProvider):
    """Twelve Data provider with 8/min rate limit."""
    
    def __init__(self):
        super().__init__("twelve_data", SourceType.REST)
        self.base_url = "https://api.twelvedata.com/v1"
        self.secrets = get_secrets_manager()
        self.api_key = None
        self.rate_limiter = get_token_bucket_limiter()
        
    async def connect(self) -> bool:
        """Connect with API key."""
        try:
            self.api_key = self.secrets.get_secret("TWELVEDATA_API_KEY")
            if not self.api_key:
                print("Twelve Data API key not found")
                return False
            
            await super().connect()
            
            # Test API key
            test_url = f"{self.base_url}/quote?symbol=AAPL&apikey={self.api_key}"
            async with self.session.get(test_url) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"Twelve Data connection error: {e}")
            return False
    
    async def get_data(self, symbol: str, **kwargs) -> List[UnifiedInternalSchema]:
        """Get quote with rate limiting."""
        try:
            # Check rate limit
            if not await self.rate_limiter.can_consume(APIProvider.TWELVE_DATA):
                wait_time = self.rate_limiter.get_wait_time(APIProvider.TWELVE_DATA)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                
                if not await self.rate_limiter.can_consume(APIProvider.TWELVE_DATA):
                    return []
            
            # Make request
            url = f"{self.base_url}/quote?symbol={symbol}&apikey={self.api_key}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                if not data or 'price' not in data:
                    return []
                
                return [self.normalize_data({
                    'symbol': symbol,
                    'price': data.get('price', 0),
                    'change': data.get('change', 0),
                    'change_percent': data.get('percent_change', 0),
                    'high': data.get('fifty_two_week_high', 0),
                    'low': data.get('fifty_two_week_low', 0),
                    'open': data.get('open', 0),
                    'previous_close': data.get('previous_close', 0)
                })]
                
        except Exception as e:
            print(f"Twelve Data data fetch error: {e}")
            return []
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize Twelve Data."""
        return UnifiedInternalSchema(
            data_type=DataType.EQUITY,
            source=self.source_name,
            source_type=self.source_type,
            symbol=raw_data.get('symbol', ''),
            timestamp=datetime.now(timezone.utc),
            price=Decimal(str(raw_data.get('price', 0))),
            change=Decimal(str(raw_data.get('change', 0))),
            change_percent=Decimal(str(raw_data.get('change_percent', 0))),
            high_price=Decimal(str(raw_data.get('high', 0))),
            low_price=Decimal(str(raw_data.get('low', 0))),
            open_price=Decimal(str(raw_data.get('open', 0))),
            raw_data=raw_data,
            processing_latency_ms=2.8
        )


class MarketStackProvider(TradFiBaseProvider):
    """Market Stack provider with 1000/month limit."""
    
    def __init__(self):
        super().__init__("market_stack", SourceType.REST)
        self.base_url = "http://api.marketstack.com/v1"
        self.secrets = get_secrets_manager()
        self.api_key = None
        self.rate_limiter = get_token_bucket_limiter()
        
    async def connect(self) -> bool:
        """Connect with API key."""
        try:
            self.api_key = self.secrets.get_secret("MARKETSTACK_API_KEY")
            if not self.api_key:
                print("Market Stack API key not found")
                return False
            
            await super().connect()
            
            # Test API key
            test_url = f"{self.base_url}/tickers/AAPL/intraday/latest?access_key={self.api_key}"
            async with self.session.get(test_url) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"Market Stack connection error: {e}")
            return False
    
    async def get_data(self, symbol: str, **kwargs) -> List[UnifiedInternalSchema]:
        """Get intraday data with rate limiting."""
        try:
            # Check rate limit (very strict)
            if not await self.rate_limiter.can_consume(APIProvider.MARKET_STACK):
                wait_time = self.rate_limiter.get_wait_time(APIProvider.MARKET_STACK)
                if wait_time > 3600:  # Don't wait more than 1 hour
                    return []
                
                await asyncio.sleep(wait_time)
                
                if not await self.rate_limiter.can_consume(APIProvider.MARKET_STACK):
                    return []
            
            # Make request
            url = f"{self.base_url}/tickers/{symbol}/intraday/latest?access_key={self.api_key}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                if 'data' not in data or not data['data']:
                    return []
                
                latest = data['data'][0]
                
                return [self.normalize_data({
                    'symbol': symbol,
                    'price': latest.get('last', 0),
                    'open': latest.get('open', 0),
                    'high': latest.get('high', 0),
                    'low': latest.get('low', 0),
                    'volume': latest.get('volume', 0),
                    'timestamp': latest.get('date', '')
                })]
                
        except Exception as e:
            print(f"Market Stack data fetch error: {e}")
            return []
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize Market Stack data."""
        timestamp_str = raw_data.get('timestamp', '')
        if timestamp_str:
            try:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
            except:
                dt = datetime.now(timezone.utc)
        else:
            dt = datetime.now(timezone.utc)
        
        return UnifiedInternalSchema(
            data_type=DataType.EQUITY,
            source=self.source_name,
            source_type=self.source_type,
            symbol=raw_data.get('symbol', ''),
            timestamp=dt,
            price=Decimal(str(raw_data.get('price', 0))),
            open_price=Decimal(str(raw_data.get('open', 0))),
            high_price=Decimal(str(raw_data.get('high', 0))),
            low_price=Decimal(str(raw_data.get('low', 0))),
            volume=Decimal(str(raw_data.get('volume', 0))),
            raw_data=raw_data,
            processing_latency_ms=3.5
        )


class FMPProvider(TradFiBaseProvider):
    """Financial Modeling Prep provider with 250/day limit."""
    
    def __init__(self):
        super().__init__("fmp", SourceType.REST)
        self.base_url = "https://financialmodelingprep.com/api/v3"
        self.secrets = get_secrets_manager()
        self.api_key = None
        self.rate_limiter = get_token_bucket_limiter()
        
    async def connect(self) -> bool:
        """Connect with API key."""
        try:
            self.api_key = self.secrets.get_secret("FMP_API_KEY")
            if not self.api_key:
                print("FMP API key not found")
                return False
            
            await super().connect()
            
            # Test API key
            test_url = f"{self.base_url}/quote-short/AAPL?apikey={self.api_key}"
            async with self.session.get(test_url) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"FMP connection error: {e}")
            return False
    
    async def get_data(self, symbol: str, **kwargs) -> List[UnifiedInternalSchema]:
        """Get quote with rate limiting."""
        try:
            # Check rate limit
            if not await self.rate_limiter.can_consume(APIProvider.FMP):
                wait_time = self.rate_limiter.get_wait_time(APIProvider.FMP)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                
                if not await self.rate_limiter.can_consume(APIProvider.FMP):
                    return []
            
            # Make request
            url = f"{self.base_url}/quote-short/{symbol}?apikey={self.api_key}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                if not data:
                    return []
                
                quote = data[0]
                
                return [self.normalize_data({
                    'symbol': symbol,
                    'price': quote.get('price', 0),
                    'volume': quote.get('volume', 0),
                    'change': quote.get('change', 0),
                    'change_percent': quote.get('changesPercentage', 0)
                })]
                
        except Exception as e:
            print(f"FMP data fetch error: {e}")
            return []
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize FMP data."""
        return UnifiedInternalSchema(
            data_type=DataType.EQUITY,
            source=self.source_name,
            source_type=self.source_type,
            symbol=raw_data.get('symbol', ''),
            timestamp=datetime.now(timezone.utc),
            price=Decimal(str(raw_data.get('price', 0))),
            volume=Decimal(str(raw_data.get('volume', 0))),
            change=Decimal(str(raw_data.get('change', 0))),
            change_percent=Decimal(str(raw_data.get('change_percent', 0))),
            raw_data=raw_data,
            processing_latency_ms=2.2
        )


class FinMindProvider(TradFiBaseProvider):
    """FinMind provider with 3000/day limit."""
    
    def __init__(self):
        super().__init__("finmind", SourceType.REST)
        self.base_url = "https://api.finmindtrade.com/v4"
        self.secrets = get_secrets_manager()
        self.api_key = None
        self.rate_limiter = get_token_bucket_limiter()
        
    async def connect(self) -> bool:
        """Connect with API key."""
        try:
            self.api_key = self.secrets.get_secret("FINMIND_API_KEY")
            await super().connect()
            
            # Test connection (FinMind works without API key for basic data)
            test_url = f"{self.base_url}/data?dataset=TaiwanStockPrice&data_id=2330&start_date=2024-01-01"
            async with self.session.get(test_url) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"FinMind connection error: {e}")
            return False
    
    async def get_data(self, symbol: str, **kwargs) -> List[UnifiedInternalSchema]:
        """Get Taiwan stock data with rate limiting."""
        try:
            # Check rate limit
            if not await self.rate_limiter.can_consume(APIProvider.FINMIND):
                wait_time = self.rate_limiter.get_wait_time(APIProvider.FINMIND)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                
                if not await self.rate_limiter.can_consume(APIProvider.FINMIND):
                    return []
            
            # Make request
            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            url = f"{self.base_url}/data?dataset=TaiwanStockPrice&data_id={symbol}&start_date={today}"
            
            if self.api_key:
                url += f"&token={self.api_key}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                if 'data' not in data or not data['data']:
                    return []
                
                latest = data['data'][-1]
                
                return [self.normalize_data({
                    'symbol': symbol,
                    'price': latest.get('close', 0),
                    'open': latest.get('open', 0),
                    'high': latest.get('high', 0),
                    'low': latest.get('low', 0),
                    'volume': latest.get('Trading_Volume', 0),
                    'date': latest.get('date', '')
                })]
                
        except Exception as e:
            print(f"FinMind data fetch error: {e}")
            return []
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize FinMind data."""
        date_str = raw_data.get('date', '')
        if date_str:
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except:
                dt = datetime.now(timezone.utc)
        else:
            dt = datetime.now(timezone.utc)
        
        return UnifiedInternalSchema(
            data_type=DataType.EQUITY,
            source=self.source_name,
            source_type=self.source_type,
            symbol=raw_data.get('symbol', ''),
            timestamp=dt,
            price=Decimal(str(raw_data.get('price', 0))),
            open_price=Decimal(str(raw_data.get('open', 0))),
            high_price=Decimal(str(raw_data.get('high', 0))),
            low_price=Decimal(str(raw_data.get('low', 0))),
            volume=Decimal(str(raw_data.get('volume', 0))),
            raw_data=raw_data,
            processing_latency_ms=2.8
        )


class FREDAuthProvider(TradFiBaseProvider):
    """FRED authenticated provider with higher limits."""
    
    def __init__(self):
        super().__init__("fred_auth", SourceType.REST)
        self.base_url = "https://api.stlouisfed.org/fred"
        self.secrets = get_secrets_manager()
        self.api_key = None
        self.rate_limiter = get_token_bucket_limiter()
        
    async def connect(self) -> bool:
        """Connect with API key."""
        try:
            self.api_key = self.secrets.get_secret("FRED_API_KEY")
            if not self.api_key:
                print("FRED API key not found")
                return False
            
            await super().connect()
            
            # Test API key
            test_url = f"{self.base_url}/series/observations?series_id=GDP&api_key={self.api_key}&limit=1"
            async with self.session.get(test_url) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"FRED Auth connection error: {e}")
            return False
    
    async def get_data(self, series_id: str, **kwargs) -> List[UnifiedInternalSchema]:
        """Get economic data with rate limiting."""
        try:
            # Check rate limit
            if not await self.rate_limiter.can_consume(APIProvider.FRED_AUTH):
                wait_time = self.rate_limiter.get_wait_time(APIProvider.FRED_AUTH)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                
                if not await self.rate_limiter.can_consume(APIProvider.FRED_AUTH):
                    return []
            
            # Make request
            url = f"{self.base_url}/series/observations?series_id={series_id}&api_key={self.api_key}&limit=1&sort_order=desc"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                if 'observations' not in data or not data['observations']:
                    return []
                
                latest = data['observations'][0]
                
                return [self.normalize_data({
                    'series_id': series_id,
                    'value': latest.get('value', 0),
                    'date': latest.get('date', '')
                })]
                
        except Exception as e:
            print(f"FRED Auth data fetch error: {e}")
            return []
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize FRED Auth data."""
        date_str = raw_data.get('date', '')
        if date_str:
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except:
                dt = datetime.now(timezone.utc)
        else:
            dt = datetime.now(timezone.utc)
        
        return UnifiedInternalSchema(
            data_type=DataType.MACRO,
            source=self.source_name,
            source_type=self.source_type,
            symbol=raw_data.get('series_id', ''),
            timestamp=dt,
            value=Decimal(str(raw_data.get('value', 0))),
            raw_data=raw_data,
            processing_latency_ms=1.8
        )


# Factory for authenticated providers
class AuthenticatedProviderFactory:
    """Factory for authenticated API providers."""
    
    def __init__(self):
        self._providers = {
            "alpha_vantage": AlphaVantageProvider,
            "finnhub": FinnhubProvider,
            "twelve_data": TwelveDataProvider,
            "market_stack": MarketStackProvider,
            "fmp": FMPProvider,
            "finmind": FinMindProvider,
            "fred_auth": FREDAuthProvider,
        }
    
    def create_provider(self, name: str) -> TradFiBaseProvider:
        """Create an authenticated provider instance."""
        if name not in self._providers:
            raise ValueError(f"Unknown authenticated provider: {name}")
        
        return self._providers[name]()
    
    def list_providers(self) -> List[str]:
        """List available authenticated providers."""
        return list(self._providers.keys())


# Global factory instance
_authenticated_provider_factory: Optional[AuthenticatedProviderFactory] = None


def get_authenticated_provider_factory() -> AuthenticatedProviderFactory:
    """Get global authenticated provider factory."""
    global _authenticated_provider_factory
    if _authenticated_provider_factory is None:
        _authenticated_provider_factory = AuthenticatedProviderFactory()
    return _authenticated_provider_factory


async def main():
    """Test authenticated providers."""
    factory = get_authenticated_provider_factory()
    
    print("Testing Authenticated API Providers")
    print("=" * 50)
    
    # Test Alpha Vantage (very limited)
    print("\n1. Testing Alpha Vantage:")
    try:
        provider = factory.create_provider("alpha_vantage")
        connected = await provider.connect()
        if connected:
            data = await provider.get_data("IBM")  # Use IBM as test
            print(f"   Connected: {connected}, Data: {len(data)} items")
            if data:
                print(f"   IBM Price: {data[0].price}")
        await provider.disconnect()
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test Finnhub
    print("\n2. Testing Finnhub:")
    try:
        provider = factory.create_provider("finnhub")
        connected = await provider.connect()
        if connected:
            data = await provider.get_data("AAPL")
            print(f"   Connected: {connected}, Data: {len(data)} items")
            if data:
                print(f"   AAPL Price: {data[0].price}")
        await provider.disconnect()
    except Exception as e:
        print(f"   Error: {e}")
    
    # Show rate limiter status
    print("\n3. Rate Limiter Status:")
    from token_bucket_limiter import get_token_bucket_limiter
    limiter = get_token_bucket_limiter()
    status = limiter.get_all_status()
    for provider_name, provider_status in status.items():
        print(f"   {provider_name:15} | {provider_status['tokens']:6.1f}/{provider_status['max_tokens']:6.1f} | Daily: {provider_status['daily_tokens']:3}/{provider_status['daily_limit']:3}")


if __name__ == "__main__":
    asyncio.run(main())
