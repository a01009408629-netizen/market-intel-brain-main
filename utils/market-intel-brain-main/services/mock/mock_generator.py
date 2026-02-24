"""
Mock Generator - Deterministic Market Data Simulation

Generates realistic market data with deterministic randomness for consistent
testing and development without network overhead. Optimized for low-resource
systems with minimal CPU and memory footprint.

Features:
- Deterministic randomness using time-based seeds
- Realistic market data patterns
- Zero network overhead
- Consistent behavior across restarts
- Support for multiple asset types
- Minimal resource usage
"""

import math
import random
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from services.schemas.market_data import (
    UnifiedMarketData, MarketDataSymbol, DataSource, 
    create_market_data, PricePoint
)


class AssetType(Enum):
    """Supported asset types for mock data generation"""
    CRYPTO = "crypto"
    STOCK = "stock"
    FOREX = "forex"
    COMMODITY = "commodity"


@dataclass
class MockAssetConfig:
    """Configuration for mock asset data generation"""
    symbol: str
    asset_type: AssetType
    base_price: float
    volatility: float = 0.02  # 2% default volatility
    trend: float = 0.0  # Trend direction (-1 to 1)
    volume_base: int = 1000000
    exchange: str = "mock_exchange"
    
    # Price bounds for realistic data
    min_price: Optional[float] = None
    max_price: Optional[float] = None


class MockGenerator:
    """
    Deterministic Mock Data Generator.
    
    Generates realistic market data using mathematical functions and
    deterministic randomness based on time-based seeds.
    """
    
    # Base configurations for popular assets
    ASSET_CONFIGS = {
        "BTCUSDT": MockAssetConfig(
            symbol="BTCUSDT",
            asset_type=AssetType.CRYPTO,
            base_price=50000.0,
            volatility=0.03,  # 3% volatility for BTC
            trend=0.001,  # Slight upward trend
            volume_base=1000000,
            exchange="mock_binance",
            min_price=1000.0,
            max_price=200000.0
        ),
        "ETHUSDT": MockAssetConfig(
            symbol="ETHUSDT",
            asset_type=AssetType.CRYPTO,
            base_price=3000.0,
            volatility=0.035,  # 3.5% volatility for ETH
            trend=0.0008,
            volume_base=2000000,
            exchange="mock_binance",
            min_price=100.0,
            max_price=20000.0
        ),
        "BNBUSDT": MockAssetConfig(
            symbol="BNBUSDT",
            asset_type=AssetType.CRYPTO,
            base_price=300.0,
            volatility=0.04,  # 4% volatility for BNB
            trend=0.0005,
            volume_base=500000,
            exchange="mock_binance",
            min_price=10.0,
            max_price=2000.0
        ),
        "AAPL": MockAssetConfig(
            symbol="AAPL",
            asset_type=AssetType.STOCK,
            base_price=150.0,
            volatility=0.02,  # 2% volatility for stocks
            trend=0.0002,
            volume_base=50000000,
            exchange="mock_nasdaq",
            min_price=50.0,
            max_price=500.0
        ),
        "EURUSD": MockAssetConfig(
            symbol="EURUSD",
            asset_type=AssetType.FOREX,
            base_price=1.08,
            volatility=0.01,  # 1% volatility for forex
            trend=0.0,
            volume_base=100000000,
            exchange="mock_forex",
            min_price=0.5,
            max_price=2.0
        )
    }
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize mock generator with deterministic seed.
        
        Args:
            seed: Random seed (uses current hour if None)
        """
        if seed is None:
            # Use current hour as seed for consistency within the hour
            current_time = datetime.utcnow()
            seed = current_time.year * 1000000 + current_time.month * 10000 + \
                   current_time.day * 100 + current_time.hour
        
        self.seed = seed
        self.rng = random.Random(seed)
        
        # Cache for generated data to ensure consistency
        self._price_cache: Dict[str, float] = {}
        self._last_update = time.time()
        
        print(f"[MockGenerator] Initialized with deterministic seed: {seed}")
    
    def _get_deterministic_random(self, symbol: str, minute_offset: int = 0) -> float:
        """
        Generate deterministic random value based on symbol and time.
        
        Args:
            symbol: Asset symbol
            minute_offset: Minutes offset from current time
            
        Returns:
            Deterministic random value between 0 and 1
        """
        # Create deterministic seed from symbol and time
        current_time = datetime.utcnow()
        time_key = current_time.year * 1000000 + current_time.month * 10000 + \
                   current_time.day * 100 + current_time.hour * 60 + current_time.minute + minute_offset
        
        # Combine with symbol hash and base seed
        combined_seed = hash(f"{self.seed}:{symbol}:{time_key}") % (2**31)
        
        # Generate random value
        local_rng = random.Random(combined_seed)
        return local_rng.random()
    
    def _generate_price_movement(
        self, 
        config: MockAssetConfig, 
        minutes_ago: int = 0
    ) -> float:
        """
        Generate realistic price movement using mathematical functions.
        
        Args:
            config: Asset configuration
            minutes_ago: Minutes ago for historical data
            
        Returns:
            Price multiplier (1.0 = no change)
        """
        # Get deterministic random values
        random_walk = self._get_deterministic_random(config.symbol, minutes_ago)
        trend_component = self._get_deterministic_random(config.symbol, minutes_ago + 1000)
        volatility_component = self._get_deterministic_random(config.symbol, minutes_ago + 2000)
        
        # Apply mathematical functions for realistic movement
        # Random walk component
        walk_factor = (random_walk - 0.5) * config.volatility
        
        # Trend component (gradual drift)
        trend_factor = config.trend * minutes_ago / 60.0  # Convert minutes to hours
        
        # Volatility component (using sine wave for cyclical patterns)
        volatility_factor = math.sin(volatility_component * 2 * math.pi) * config.volatility * 0.5
        
        # Combine all factors
        price_multiplier = 1.0 + walk_factor + trend_factor + volatility_factor
        
        return price_multiplier
    
    def _clamp_price(self, price: float, config: MockAssetConfig) -> float:
        """Clamp price to configured bounds."""
        if config.min_price is not None:
            price = max(price, config.min_price)
        if config.max_price is not None:
            price = min(price, config.max_price)
        return price
    
    def generate_price(self, symbol: str, minutes_ago: int = 0) -> Optional[float]:
        """
        Generate price for a symbol at a specific time offset.
        
        Args:
            symbol: Asset symbol
            minutes_ago: Minutes ago from current time (0 = current)
            
        Returns:
            Generated price or None if symbol not supported
        """
        config = self.ASSET_CONFIGS.get(symbol.upper())
        if not config:
            # Generate generic config for unknown symbols
            config = MockAssetConfig(
                symbol=symbol.upper(),
                asset_type=AssetType.CRYPTO,
                base_price=100.0,
                volatility=0.02,
                exchange="mock_generic"
            )
        
        # Generate price movement
        price_multiplier = self._generate_price_movement(config, minutes_ago)
        price = config.base_price * price_multiplier
        
        # Clamp to bounds
        price = self._clamp_price(price, config)
        
        # Cache for consistency
        cache_key = f"{symbol}:{minutes_ago}"
        if cache_key not in self._price_cache:
            self._price_cache[cache_key] = price
        
        return price
    
    def generate_volume(self, symbol: str, minutes_ago: int = 0) -> Optional[int]:
        """
        Generate realistic volume for a symbol.
        
        Args:
            symbol: Asset symbol
            minutes_ago: Minutes ago from current time
            
        Returns:
            Generated volume or None if symbol not supported
        """
        config = self.ASSET_CONFIGS.get(symbol.upper())
        if not config:
            return None
        
        # Generate volume with deterministic randomness
        volume_random = self._get_deterministic_random(symbol, minutes_ago + 3000)
        volume_multiplier = 0.5 + volume_random  # 0.5x to 1.5x base volume
        
        # Apply time-of-day pattern (higher volume during market hours)
        current_time = datetime.utcnow()
        hour = current_time.hour
        
        if config.asset_type == AssetType.STOCK:
            # Stock market hours pattern (9 AM - 4 PM EST)
            market_hour = (hour - 14) % 24  # Convert to EST
            if 9 <= market_hour <= 16:
                volume_multiplier *= 1.5
            else:
                volume_multiplier *= 0.3
        elif config.asset_type == AssetType.CRYPTO:
            # Crypto has more consistent volume with slight peaks
            if 12 <= hour <= 18:  # UTC active hours
                volume_multiplier *= 1.2
        
        volume = int(config.volume_base * volume_multiplier)
        return max(volume, 1)  # Ensure minimum volume
    
    def generate_market_data(
        self, 
        symbol: str, 
        minutes_ago: int = 0
    ) -> Optional[UnifiedMarketData]:
        """
        Generate complete UnifiedMarketData for a symbol.
        
        Args:
            symbol: Asset symbol
            minutes_ago: Minutes ago from current time
            
        Returns:
            UnifiedMarketData or None if generation fails
        """
        try:
            # Get configuration
            config = self.ASSET_CONFIGS.get(symbol.upper())
            if not config:
                config = MockAssetConfig(
                    symbol=symbol.upper(),
                    asset_type=AssetType.CRYPTO,
                    base_price=100.0,
                    volatility=0.02,
                    exchange="mock_generic"
                )
            
            # Generate price
            price = self.generate_price(symbol, minutes_ago)
            if price is None:
                return None
            
            # Generate volume
            volume = self.generate_volume(symbol, minutes_ago)
            
            # Generate timestamp
            timestamp = datetime.utcnow() - timedelta(minutes=minutes_ago)
            
            # Create price point
            price_point = PricePoint(
                value=Decimal(str(round(price, 6))),
                currency="USDT" if symbol.endswith("USDT") else "USD"
            )
            
            # Determine asset type and source
            asset_type_map = {
                AssetType.CRYPTO: MarketDataSymbol.CRYPTO,
                AssetType.STOCK: MarketDataSymbol.STOCK,
                AssetType.FOREX: MarketDataSymbol.FOREX,
                AssetType.COMMODITY: MarketDataSymbol.COMMODITY
            }
            
            source_map = {
                "mock_binance": DataSource.BINANCE,
                "mock_nasdaq": DataSource.NASDAQ,
                "mock_forex": DataSource.FOREX_COM,
                "mock_generic": DataSource.MOCK
            }
            
            # Create market data
            market_data = create_market_data(
                symbol=symbol.replace("USDT", "") if symbol.endswith("USDT") else symbol,
                asset_type=asset_type_map.get(config.asset_type, MarketDataSymbol.CRYPTO),
                exchange=config.exchange,
                price_str=str(price_point.value),
                currency=price_point.currency,
                source=source_map.get(config.exchange, DataSource.MOCK),
                timestamp=timestamp,
                volume=volume
            )
            
            return market_data
            
        except Exception as e:
            print(f"[MockGenerator] Error generating market data for {symbol}: {e}")
            return None
    
    def generate_ohlcv(
        self, 
        symbol: str, 
        interval_minutes: int = 60,
        periods: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Generate OHLCV data for historical analysis.
        
        Args:
            symbol: Asset symbol
            interval_minutes: Candlestick interval in minutes
            periods: Number of periods to generate
            
        Returns:
            List of OHLCV dictionaries
        """
        ohlcv_data = []
        
        for i in range(periods):
            minutes_ago = (periods - i - 1) * interval_minutes
            
            # Generate price for this period
            price = self.generate_price(symbol, minutes_ago)
            if price is None:
                continue
            
            # Generate OHLC with realistic patterns
            open_price = price
            close_price = self.generate_price(symbol, minutes_ago - interval_minutes // 2)
            high_price = max(open_price, close_price) * (1 + abs(self._get_deterministic_random(symbol, minutes_ago + 4000)) * 0.01)
            low_price = min(open_price, close_price) * (1 - abs(self._get_deterministic_random(symbol, minutes_ago + 5000)) * 0.01)
            
            # Generate volume for this period
            volume = self.generate_volume(symbol, minutes_ago)
            
            timestamp = datetime.utcnow() - timedelta(minutes=minutes_ago)
            
            ohlcv_data.append({
                "timestamp": timestamp.isoformat(),
                "open": round(open_price, 6),
                "high": round(high_price, 6),
                "low": round(low_price, 6),
                "close": round(close_price, 6),
                "volume": volume
            })
        
        return ohlcv_data
    
    def get_supported_symbols(self) -> List[str]:
        """Get list of supported symbols with predefined configurations."""
        return list(self.ASSET_CONFIGS.keys())
    
    def add_asset_config(self, config: MockAssetConfig):
        """Add or update asset configuration."""
        self.ASSET_CONFIGS[config.symbol.upper()] = config
    
    def clear_cache(self):
        """Clear internal price cache."""
        self._price_cache.clear()
        self._last_update = time.time()


# Global mock generator instance
_mock_generator: Optional[MockGenerator] = None


def get_mock_generator(seed: Optional[int] = None) -> MockGenerator:
    """Get or create global mock generator instance."""
    global _mock_generator
    if _mock_generator is None:
        _mock_generator = MockGenerator(seed)
    return _mock_generator


def generate_mock_market_data(symbol: str, minutes_ago: int = 0) -> Optional[UnifiedMarketData]:
    """
    Convenience function to generate mock market data.
    
    Args:
        symbol: Asset symbol
        minutes_ago: Minutes ago from current time
        
    Returns:
        UnifiedMarketData or None
    """
    generator = get_mock_generator()
    return generator.generate_market_data(symbol, minutes_ago)


def generate_mock_price(symbol: str, minutes_ago: int = 0) -> Optional[float]:
    """
    Convenience function to generate mock price.
    
    Args:
        symbol: Asset symbol
        minutes_ago: Minutes ago from current time
        
    Returns:
        Generated price or None
    """
    generator = get_mock_generator()
    return generator.generate_price(symbol, minutes_ago)
