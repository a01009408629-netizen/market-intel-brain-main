"""
Production-Ready Data Normalization Factory
Adapter Pattern with UnifiedInternalSchema for Ticks and News
"""

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, Union, Type
from dataclasses import dataclass, asdict
from enum import Enum
import pydantic


class DataType(Enum):
    TICK = "tick"
    NEWS = "news"
    EQUITY = "equity"
    FOREX = "forex"
    MACRO = "macro"


class SourceType(Enum):
    REST = "rest"
    WEBSOCKET = "websocket"
    WEBSCRAPER = "webscraper"
    RSS = "rss"


@dataclass
class UnifiedInternalSchema:
    """Strictly typed unified internal schema for all data sources."""
    
    # Core fields
    data_type: DataType
    source: str
    source_type: SourceType
    symbol: str
    timestamp: datetime
    
    # Tick-specific fields
    price: Optional[Decimal] = None
    volume: Optional[Decimal] = None
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    open: Optional[Decimal] = None
    close: Optional[Decimal] = None
    
    # News-specific fields
    title: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    url: Optional[str] = None
    sentiment: Optional[str] = None
    relevance_score: Optional[float] = None
    tags: Optional[List[str]] = None
    
    # Metadata
    raw_data: Optional[Dict[str, Any]] = None
    processing_latency_ms: Optional[float] = None
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization."""
        result = asdict(self)
        # Convert datetime to ISO string
        if result['timestamp']:
            result['timestamp'] = result['timestamp'].isoformat()
        # Convert Decimal to string
        for field in ['price', 'volume', 'bid', 'ask', 'high', 'low', 'open', 'close']:
            if result[field] is not None:
                result[field] = str(result[field])
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class BaseProvider(ABC):
    """Abstract base provider for all data sources."""
    
    def __init__(self, source_name: str, source_type: SourceType):
        self.source_name = source_name
        self.source_type = source_type
        self._is_running = False
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the data source."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the data source."""
        pass
    
    @abstractmethod
    async def get_data(self, symbol: str, **kwargs) -> List[UnifiedInternalSchema]:
        """Get data for a specific symbol."""
        pass
    
    @abstractmethod
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize raw data to UnifiedInternalSchema."""
        pass
    
    async def start_streaming(self, symbols: List[str], callback) -> None:
        """Start streaming data for multiple symbols."""
        if self.source_type != SourceType.WEBSOCKET:
            raise ValueError("Streaming only supported for WebSocket sources")
        
        self._is_running = True
        while self._is_running:
            try:
                data = await self._get_stream_data(symbols)
                if data:
                    await callback(data)
                await asyncio.sleep(0.001)  # Minimal delay
            except Exception as e:
                print(f"Streaming error in {self.source_name}: {e}")
                await asyncio.sleep(1)
    
    async def stop_streaming(self) -> None:
        """Stop streaming data."""
        self._is_running = False
    
    @abstractmethod
    async def _get_stream_data(self, symbols: List[str]) -> List[UnifiedInternalSchema]:
        """Get streaming data for symbols."""
        pass


class BinanceWebSocketProvider(BaseProvider):
    """Mock Binance WebSocket provider implementation."""
    
    def __init__(self):
        super().__init__("binance", SourceType.WEBSOCKET)
        self._ws_url = "wss://stream.binance.com:9443/ws"
        self._symbols = set()
        self._price_cache: Dict[str, Decimal] = {}
    
    async def connect(self) -> bool:
        """Connect to Binance WebSocket."""
        print(f"Connecting to {self.source_name} WebSocket...")
        # Mock connection - in production, establish real WebSocket connection
        await asyncio.sleep(0.1)
        print(f"Connected to {self.source_name} WebSocket")
        return True
    
    async def disconnect(self) -> None:
        """Disconnect from Binance WebSocket."""
        print(f"Disconnecting from {self.source_name} WebSocket...")
        self._is_running = False
        self._symbols.clear()
        self._price_cache.clear()
    
    async def get_data(self, symbol: str, **kwargs) -> List[UnifiedInternalSchema]:
        """Get current tick data for symbol."""
        # Mock data generation
        base_price = Decimal("50000.00") if "BTC" in symbol else Decimal("3000.00")
        variation = Decimal("0.001") * Decimal(str(hash(symbol) % 1000))
        price = base_price + variation
        
        tick = UnifiedInternalSchema(
            data_type=DataType.TICK,
            source=self.source_name,
            source_type=self.source_type,
            symbol=symbol.upper(),
            timestamp=datetime.now(timezone.utc),
            price=price,
            volume=Decimal("1.5"),
            bid=price - Decimal("0.01"),
            ask=price + Decimal("0.01"),
            processing_latency_ms=0.5,
            correlation_id=f"binance_{symbol}_{int(datetime.now().timestamp() * 1000)}"
        )
        
        return [tick]
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize Binance WebSocket data to UnifiedInternalSchema."""
        return UnifiedInternalSchema(
            data_type=DataType.TICK,
            source=self.source_name,
            source_type=self.source_type,
            symbol=raw_data.get('s', '').upper(),
            timestamp=datetime.fromtimestamp(raw_data.get('E', 0) / 1000, timezone.utc),
            price=Decimal(str(raw_data.get('c', '0'))),
            volume=Decimal(str(raw_data.get('v', '0'))),
            bid=Decimal(str(raw_data.get('b', '0'))),
            ask=Decimal(str(raw_data.get('a', '0'))),
            high=Decimal(str(raw_data.get('h', '0'))),
            low=Decimal(str(raw_data.get('l', '0'))),
            raw_data=raw_data,
            processing_latency_ms=0.1
        )
    
    async def _get_stream_data(self, symbols: List[str]) -> List[UnifiedInternalSchema]:
        """Get streaming data for symbols."""
        results = []
        current_time = datetime.now(timezone.utc)
        
        for symbol in symbols:
            # Generate realistic price movement
            base_price = self._price_cache.get(symbol, Decimal("50000.00"))
            change = Decimal("0.0001") * Decimal(str(hash(f"{symbol}_{current_time.second}") % 100 - 50))
            new_price = base_price + change
            
            self._price_cache[symbol] = new_price
            
            tick = UnifiedInternalSchema(
                data_type=DataType.TICK,
                source=self.source_name,
                source_type=self.source_type,
                symbol=symbol.upper(),
                timestamp=current_time,
                price=new_price,
                volume=Decimal("0.8"),
                bid=new_price - Decimal("0.01"),
                ask=new_price + Decimal("0.01"),
                processing_latency_ms=0.2,
                correlation_id=f"binance_ws_{symbol}_{int(current_time.timestamp() * 1000)}"
            )
            
            results.append(tick)
        
        return results


class BloombergRESTProvider(BaseProvider):
    """Mock Bloomberg REST provider implementation."""
    
    def __init__(self):
        super().__init__("bloomberg", SourceType.REST)
        self._base_url = "https://api.bloomberg.com"
        self._api_key = None
    
    async def connect(self) -> bool:
        """Connect to Bloomberg API."""
        print(f"Connecting to {self.source_name} REST API...")
        # Mock API key retrieval
        from infrastructure.secrets_manager import get_secrets_manager
        secrets = get_secrets_manager()
        self._api_key = secrets.get_secret("BLOOMBERG_API_KEY")
        await asyncio.sleep(0.05)
        print(f"Connected to {self.source_name} REST API")
        return True
    
    async def disconnect(self) -> None:
        """Disconnect from Bloomberg API."""
        print(f"Disconnecting from {self.source_name} REST API...")
        self._api_key = None
    
    async def get_data(self, symbol: str, **kwargs) -> List[UnifiedInternalSchema]:
        """Get news data for symbol."""
        # Mock news data generation
        news_items = [
            UnifiedInternalSchema(
                data_type=DataType.NEWS,
                source=self.source_name,
                source_type=self.source_type,
                symbol=symbol.upper(),
                timestamp=datetime.now(timezone.utc),
                title=f"Market Update: {symbol} Shows Strong Performance",
                content=f"Latest analysis indicates {symbol} is performing well in current market conditions.",
                author="Bloomberg Analytics",
                url=f"https://bloomberg.com/news/{symbol.lower()}_{int(datetime.now().timestamp())}",
                sentiment="positive",
                relevance_score=0.85,
                tags=["market", "analysis", symbol.lower()],
                processing_latency_ms=15.0,
                correlation_id=f"bloomberg_{symbol}_{int(datetime.now().timestamp() * 1000)}"
            )
        ]
        
        return news_items
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize Bloomberg REST data to UnifiedInternalSchema."""
        return UnifiedInternalSchema(
            data_type=DataType.NEWS,
            source=self.source_name,
            source_type=self.source_type,
            symbol=raw_data.get('symbol', '').upper(),
            timestamp=datetime.fromisoformat(raw_data.get('timestamp', datetime.now(timezone.utc).isoformat())),
            title=raw_data.get('headline', ''),
            content=raw_data.get('body', ''),
            author=raw_data.get('author', ''),
            url=raw_data.get('url', ''),
            sentiment=raw_data.get('sentiment', 'neutral'),
            relevance_score=raw_data.get('relevance', 0.5),
            tags=raw_data.get('tags', []),
            raw_data=raw_data,
            processing_latency_ms=5.0
        )


class DataNormalizationFactory:
    """Factory for creating and managing data providers."""
    
    def __init__(self):
        self._providers: Dict[str, Type[BaseProvider]] = {}
        self._instances: Dict[str, BaseProvider] = {}
        self._register_default_providers()
    
    def _register_default_providers(self):
        """Register default providers."""
        self.register_provider("binance_ws", BinanceWebSocketProvider)
        self.register_provider("bloomberg_rest", BloombergRESTProvider)
    
    def register_provider(self, name: str, provider_class: Type[BaseProvider]):
        """Register a new provider."""
        self._providers[name] = provider_class
    
    def create_provider(self, name: str) -> BaseProvider:
        """Create a provider instance."""
        if name not in self._providers:
            raise ValueError(f"Provider '{name}' not registered")
        
        if name not in self._instances:
            self._instances[name] = self._providers[name]()
        
        return self._instances[name]
    
    def get_provider(self, name: str) -> BaseProvider:
        """Get existing provider instance."""
        if name not in self._instances:
            return self.create_provider(name)
        return self._instances[name]
    
    async def connect_all(self) -> Dict[str, bool]:
        """Connect all registered providers."""
        results = {}
        for name, provider in self._instances.items():
            try:
                results[name] = await provider.connect()
            except Exception as e:
                print(f"Failed to connect {name}: {e}")
                results[name] = False
        return results
    
    async def disconnect_all(self):
        """Disconnect all providers."""
        for name, provider in self._instances.items():
            try:
                await provider.disconnect()
            except Exception as e:
                print(f"Failed to disconnect {name}: {e}")
    
    def list_providers(self) -> List[str]:
        """List all registered providers."""
        return list(self._providers.keys())
    
    def get_active_instances(self) -> Dict[str, str]:
        """Get active provider instances with their types."""
        return {name: type(provider).__name__ for name, provider in self._instances.items()}


# Global factory instance
_data_factory: Optional[DataNormalizationFactory] = None


def get_data_factory() -> DataNormalizationFactory:
    """Get global data factory instance."""
    global _data_factory
    if _data_factory is None:
        _data_factory = DataNormalizationFactory()
    return _data_factory


async def main():
    """Example usage."""
    factory = get_data_factory()
    
    # Create providers
    binance_provider = factory.create_provider("binance_ws")
    bloomberg_provider = factory.create_provider("bloomberg_rest")
    
    # Connect all providers
    connections = await factory.connect_all()
    print(f"Connection results: {connections}")
    
    # Get data from providers
    binance_data = await binance_provider.get_data("BTCUSDT")
    bloomberg_data = await bloomberg_provider.get_data("BTCUSDT")
    
    print(f"Binance data: {len(binance_data)} items")
    print(f"Bloomberg data: {len(bloomberg_data)} items")
    
    # Disconnect all providers
    await factory.disconnect_all()


if __name__ == "__main__":
    asyncio.run(main())
