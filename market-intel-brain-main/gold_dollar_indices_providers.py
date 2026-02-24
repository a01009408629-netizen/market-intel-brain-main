"""
Gold, Dollar, and U.S. Indices Providers
Real-time prices for gold, USD, and major indices
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timezone
from decimal import Decimal

from tradfi_providers import TradFiBaseProvider, AsyncJitter
from infrastructure.data_normalization import UnifiedInternalSchema, DataType, SourceType


class GoldPriceProvider(TradFiBaseProvider):
    """Gold price provider - multiple sources."""
    
    def __init__(self):
        super().__init__("gold_price", SourceType.REST)
        self.sources = {
            "financialtimes": "https://markets.ft.com/data/cookies/quote/634909",
            "investing": "https://www.investing.com/api/financialdata/1/historical/chart?symbol=8830&resolution=1D&count=1",
            "goldapi": "https://www.goldapi.io/api/XAU/USD",
            "yahoo": "https://query1.finance.yahoo.com/v8/finance/chart/GC=F"
        }
        
    async def connect(self) -> bool:
        """Test gold price sources."""
        try:
            await super().connect()
            
            # Test Yahoo Finance for Gold
            url = self.sources["yahoo"]
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            async with self.session.get(url, headers=headers) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"Gold price connection error: {e}")
            return False
    
    async def get_data(self, symbol: str = "XAUUSD", **kwargs) -> List[UnifiedInternalSchema]:
        """Get gold price data."""
        try:
            # Use Yahoo Finance for Gold Futures
            url = self.sources["yahoo"]
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                if 'chart' in data and data['chart']['result']:
                    result = data['chart']['result'][0]
                    if 'meta' in result:
                        price = result['meta'].get('regularMarketPrice', '0')
                        currency = result['meta'].get('currency', 'USD')
                        
                        return [self.normalize_data({
                            'symbol': 'XAUUSD',
                            'price': price,
                            'currency': currency,
                            'source': 'yahoo_finance',
                            'commodity': 'gold',
                            'unit': 'troy ounce'
                        })]
                
                return []
                
        except Exception as e:
            print(f"Gold price fetch error: {e}")
            return []
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize gold price data."""
        return UnifiedInternalSchema(
            data_type=DataType.FOREX,
            source=self.source_name,
            source_type=self.source_type,
            symbol=raw_data.get('symbol', 'XAUUSD'),
            timestamp=datetime.now(timezone.utc),
            price=Decimal(str(raw_data.get('price', '0'))),
            raw_data=raw_data,
            processing_latency_ms=2.0
        )


class DollarIndexProvider(TradFiBaseProvider):
    """U.S. Dollar Index (DXY) provider."""
    
    def __init__(self):
        super().__init__("dollar_index", SourceType.REST)
        self.sources = {
            "yahoo": "https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB",
            "tradingview": "https://www.tradingview.com/symbols/INDEX:DXY/",
            "federalreserve": "https://www.federalreserve.gov/releases/h10/current"
        }
        
    async def connect(self) -> bool:
        """Test Dollar Index connection."""
        try:
            await super().connect()
            
            url = self.sources["yahoo"]
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            async with self.session.get(url, headers=headers) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"Dollar Index connection error: {e}")
            return False
    
    async def get_data(self, symbol: str = "DXY", **kwargs) -> List[UnifiedInternalSchema]:
        """Get Dollar Index data."""
        try:
            url = self.sources["yahoo"]
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                if 'chart' in data and data['chart']['result']:
                    result = data['chart']['result'][0]
                    if 'meta' in result:
                        price = result['meta'].get('regularMarketPrice', '0')
                        
                        return [self.normalize_data({
                            'symbol': 'DXY',
                            'price': price,
                            'index_name': 'U.S. Dollar Index',
                            'source': 'yahoo_finance'
                        })]
                
                return []
                
        except Exception as e:
            print(f"Dollar Index fetch error: {e}")
            return []
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize Dollar Index data."""
        return UnifiedInternalSchema(
            data_type=DataType.FOREX,
            source=self.source_name,
            source_type=self.source_type,
            symbol=raw_data.get('symbol', 'DXY'),
            timestamp=datetime.now(timezone.utc),
            price=Decimal(str(raw_data.get('price', '0'))),
            raw_data=raw_data,
            processing_latency_ms=2.0
        )


class USIndicesProvider(TradFiBaseProvider):
    """Major U.S. Indices provider."""
    
    def __init__(self):
        super().__init__("us_indices", SourceType.REST)
        self.indices = {
            "S&P500": "^GSPC",      # S&P 500
            "DowJones": "^DJI",      # Dow Jones Industrial Average
            "NASDAQ": "^IXIC",        # NASDAQ Composite
            "Russell2000": "^RUT",    # Russell 2000
            "VIX": "^VIX",           # CBOE Volatility Index
            "DollarIndex": "DX-Y.NYB" # U.S. Dollar Index
        }
        
    async def connect(self) -> bool:
        """Test U.S. indices connection."""
        try:
            await super().connect()
            
            # Test S&P 500
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{self.indices['S&P500']}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            async with self.session.get(url, headers=headers) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"U.S. indices connection error: {e}")
            return False
    
    async def get_data(self, symbol: str = "", **kwargs) -> List[UnifiedInternalSchema]:
        """Get U.S. indices data."""
        try:
            all_data = []
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            # Get data for all major indices
            for index_name, ticker in self.indices.items():
                try:
                    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
                    
                    async with self.session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if 'chart' in data and data['chart']['result']:
                                result = data['chart']['result'][0]
                                if 'meta' in result:
                                    price = result['meta'].get('regularMarketPrice', '0')
                                    change = result['meta'].get('regularMarketPrice', '0') - result['meta'].get('previousClose', '0')
                                    
                                    index_data = self.normalize_data({
                                        'symbol': ticker,
                                        'index_name': index_name,
                                        'price': price,
                                        'change': change,
                                        'source': 'yahoo_finance'
                                    })
                                    
                                    all_data.append(index_data)
                    
                    await asyncio.sleep(0.1)  # Small delay between requests
                    
                except Exception as e:
                    print(f"Error fetching {index_name}: {e}")
                    continue
            
            return all_data
            
        except Exception as e:
            print(f"U.S. indices fetch error: {e}")
            return []
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize U.S. indices data."""
        return UnifiedInternalSchema(
            data_type=DataType.EQUITY,
            source=self.source_name,
            source_type=self.source_type,
            symbol=raw_data.get('symbol', ''),
            timestamp=datetime.now(timezone.utc),
            price=Decimal(str(raw_data.get('price', '0'))),
            change=Decimal(str(raw_data.get('change', '0'))),
            raw_data=raw_data,
            processing_latency_ms=2.5
        )


class ForexProvider(TradFiBaseProvider):
    """Forex rates provider - USD based pairs."""
    
    def __init__(self):
        super().__init__("forex_rates", SourceType.REST)
        self.pairs = {
            "EURUSD": "EURUSD=X",
            "GBPUSD": "GBPUSD=X", 
            "USDJPY": "USDJPY=X",
            "USDCHF": "USDCHF=X",
            "USDCAD": "USDCAD=X",
            "AUDUSD": "AUDUSD=X",
            "NZDUSD": "NZDUSD=X"
        }
        
    async def connect(self) -> bool:
        """Test forex connection."""
        try:
            await super().connect()
            
            # Test EUR/USD
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{self.pairs['EURUSD']}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            async with self.session.get(url, headers=headers) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"Forex connection error: {e}")
            return False
    
    async def get_data(self, symbol: str = "", **kwargs) -> List[UnifiedInternalSchema]:
        """Get forex rates data."""
        try:
            all_data = []
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            # Get data for major forex pairs
            for pair_name, ticker in self.pairs.items():
                try:
                    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
                    
                    async with self.session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if 'chart' in data and data['chart']['result']:
                                result = data['chart']['result'][0]
                                if 'meta' in result:
                                    price = result['meta'].get('regularMarketPrice', '0')
                                    
                                    forex_data = self.normalize_data({
                                        'symbol': pair_name,
                                        'price': price,
                                        'pair_name': pair_name,
                                        'source': 'yahoo_finance'
                                    })
                                    
                                    all_data.append(forex_data)
                    
                    await asyncio.sleep(0.1)  # Small delay between requests
                    
                except Exception as e:
                    print(f"Error fetching {pair_name}: {e}")
                    continue
            
            return all_data
            
        except Exception as e:
            print(f"Forex rates fetch error: {e}")
            return []
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize forex data."""
        return UnifiedInternalSchema(
            data_type=DataType.FOREX,
            source=self.source_name,
            source_type=self.source_type,
            symbol=raw_data.get('symbol', ''),
            timestamp=datetime.now(timezone.utc),
            price=Decimal(str(raw_data.get('price', '0'))),
            raw_data=raw_data,
            processing_latency_ms=2.0
        )


# Factory for Gold, Dollar, and Indices providers
class GoldDollarIndicesFactory:
    """Factory for gold, dollar, and indices providers."""
    
    def __init__(self):
        self._providers = {
            "gold_price": GoldPriceProvider,
            "dollar_index": DollarIndexProvider,
            "us_indices": USIndicesProvider,
            "forex_rates": ForexProvider,
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
_gold_dollar_indices_factory: Optional[GoldDollarIndicesFactory] = None


def get_gold_dollar_indices_factory() -> GoldDollarIndicesFactory:
    """Get global factory instance."""
    global _gold_dollar_indices_factory
    if _gold_dollar_indices_factory is None:
        _gold_dollar_indices_factory = GoldDollarIndicesFactory()
    return _gold_dollar_indices_factory


async def main():
    """Test gold, dollar, and indices providers."""
    factory = get_gold_dollar_indices_factory()
    
    print("Testing Gold, Dollar, and U.S. Indices Providers")
    print("=" * 60)
    
    # Test Gold Price
    print("\n1. Testing Gold Price (XAU/USD):")
    try:
        provider = factory.create_provider("gold_price")
        connected = await provider.connect()
        if connected:
            data = await provider.get_data()
            print(f"   Connected: {connected}, Data: {len(data)} items")
            if data:
                print(f"   Gold Price: ${data[0].price}")
        await provider.disconnect()
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test Dollar Index
    print("\n2. Testing U.S. Dollar Index (DXY):")
    try:
        provider = factory.create_provider("dollar_index")
        connected = await provider.connect()
        if connected:
            data = await provider.get_data()
            print(f"   Connected: {connected}, Data: {len(data)} items")
            if data:
                print(f"   Dollar Index: {data[0].price}")
        await provider.disconnect()
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test U.S. Indices
    print("\n3. Testing U.S. Indices:")
    try:
        provider = factory.create_provider("us_indices")
        connected = await provider.connect()
        if connected:
            data = await provider.get_data()
            print(f"   Connected: {connected}, Data: {len(data)} items")
            for item in data:
                index_name = item.raw_data.get('index_name', item.symbol)
                print(f"   {index_name}: {item.price}")
        await provider.disconnect()
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test Forex Rates
    print("\n4. Testing Forex Rates:")
    try:
        provider = factory.create_provider("forex_rates")
        connected = await provider.connect()
        if connected:
            data = await provider.get_data()
            print(f"   Connected: {connected}, Data: {len(data)} items")
            for item in data[:4]:  # Show first 4 pairs
                pair_name = item.raw_data.get('pair_name', item.symbol)
                print(f"   {pair_name}: {item.price}")
        await provider.disconnect()
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\nGold, Dollar, and Indices providers test completed!")


if __name__ == "__main__":
    asyncio.run(main())
