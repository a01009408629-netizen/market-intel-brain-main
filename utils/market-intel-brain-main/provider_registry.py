"""
Provider Registry with Priority Fallback
Keyless providers first, authenticated APIs as fallback
"""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from tradfi_providers import get_tradfi_provider_factory, TradFiBaseProvider
from authenticated_providers import get_authenticated_provider_factory
from infrastructure.data_normalization import UnifiedInternalSchema


class ProviderPriority(Enum):
    """Provider priority levels."""
    PRIMARY = 1      # Keyless providers (Yahoo Finance, RSS, etc.)
    SECONDARY = 2    # Authenticated APIs (conservative usage)
    FALLBACK = 3     # Last resort


@dataclass
class ProviderConfig:
    """Provider configuration with priority and capabilities."""
    name: str
    priority: ProviderPriority
    factory_type: str  # "keyless" or "authenticated"
    data_types: List[str]  # ["equity", "forex", "macro", "news"]
    rate_limit_per_hour: int
    reliability_score: float  # 0.0 to 1.0
    enabled: bool = True


class ProviderRegistry:
    """Registry with intelligent fallback logic."""
    
    def __init__(self):
        self.keyless_factory = get_tradfi_provider_factory()
        self.auth_factory = get_authenticated_provider_factory()
        
        # Provider configurations with priority
        self.provider_configs = {
            # Primary (Keyless) - Use first
            "yahoo_finance": ProviderConfig(
                name="yahoo_finance",
                priority=ProviderPriority.PRIMARY,
                factory_type="keyless",
                data_types=["equity", "forex"],
                rate_limit_per_hour=2000,  # Unofficial but reasonable
                reliability_score=0.9
            ),
            "rss_news": ProviderConfig(
                name="rss_news",
                priority=ProviderPriority.PRIMARY,
                factory_type="keyless",
                data_types=["news"],
                rate_limit_per_hour=100,
                reliability_score=0.8
            ),
            "google_news": ProviderConfig(
                name="google_news",
                priority=ProviderPriority.PRIMARY,
                factory_type="keyless",
                data_types=["news"],
                rate_limit_per_hour=50,
                reliability_score=0.7
            ),
            "fred": ProviderConfig(
                name="fred",
                priority=ProviderPriority.PRIMARY,
                factory_type="keyless",
                data_types=["macro"],
                rate_limit_per_hour=120,
                reliability_score=0.85
            ),
            "econdb": ProviderConfig(
                name="econdb",
                priority=ProviderPriority.PRIMARY,
                factory_type="keyless",
                data_types=["macro"],
                rate_limit_per_hour=100,
                reliability_score=0.8
            ),
            "eurostat": ProviderConfig(
                name="eurostat",
                priority=ProviderPriority.PRIMARY,
                factory_type="keyless",
                data_types=["macro"],
                rate_limit_per_hour=50,
                reliability_score=0.75
            ),
            "imf": ProviderConfig(
                name="imf",
                priority=ProviderPriority.PRIMARY,
                factory_type="keyless",
                data_types=["macro"],
                rate_limit_per_hour=50,
                reliability_score=0.8
            ),
            
            # Secondary (Authenticated) - Use as fallback
            "finnhub": ProviderConfig(
                name="finnhub",
                priority=ProviderPriority.SECONDARY,
                factory_type="authenticated",
                data_types=["equity"],
                rate_limit_per_hour=3600,  # 1/sec
                reliability_score=0.95
            ),
            "twelve_data": ProviderConfig(
                name="twelve_data",
                priority=ProviderPriority.SECONDARY,
                factory_type="authenticated",
                data_types=["equity", "forex"],
                rate_limit_per_hour=480,  # 8/min
                reliability_score=0.9
            ),
            "fmp": ProviderConfig(
                name="fmp",
                priority=ProviderPriority.SECONDARY,
                factory_type="authenticated",
                data_types=["equity"],
                rate_limit_per_hour=250,  # 250/day
                reliability_score=0.85
            ),
            "alpha_vantage": ProviderConfig(
                name="alpha_vantage",
                priority=ProviderPriority.SECONDARY,
                factory_type="authenticated",
                data_types=["equity"],
                rate_limit_per_hour=25,  # 25/day
                reliability_score=0.9
            ),
            "fred_auth": ProviderConfig(
                name="fred_auth",
                priority=ProviderPriority.SECONDARY,
                factory_type="authenticated",
                data_types=["macro"],
                rate_limit_per_hour=7200,  # 2/sec
                reliability_score=0.95
            ),
            "market_stack": ProviderConfig(
                name="market_stack",
                priority=ProviderPriority.FALLBACK,
                factory_type="authenticated",
                data_types=["equity"],
                rate_limit_per_hour=33,  # 1000/month
                reliability_score=0.8
            ),
            "finmind": ProviderConfig(
                name="finmind",
                priority=ProviderPriority.FALLBACK,
                factory_type="authenticated",
                data_types=["equity"],
                rate_limit_per_hour=3000,  # 3000/day
                reliability_score=0.75
            )
        }
        
        # Provider instances cache
        self._provider_instances: Dict[str, TradFiBaseProvider] = {}
        self._connection_status: Dict[str, bool] = {}
        
        # Performance tracking
        self._provider_stats: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self):
        """Initialize all providers and test connections."""
        print("Initializing Provider Registry...")
        
        for provider_name, config in self.provider_configs.items():
            if not config.enabled:
                continue
            
            try:
                # Create provider instance
                if config.factory_type == "keyless":
                    provider = self.keyless_factory.create_provider(provider_name)
                else:
                    provider = self.auth_factory.create_provider(provider_name)
                
                # Test connection
                connected = await provider.connect()
                
                if connected:
                    self._provider_instances[provider_name] = provider
                    self._connection_status[provider_name] = True
                    self._provider_stats[provider_name] = {
                        "requests": 0,
                        "successes": 0,
                        "failures": 0,
                        "last_used": None
                    }
                    print(f"  {provider_name}: CONNECTED ({config.priority.name})")
                else:
                    self._connection_status[provider_name] = False
                    print(f"  {provider_name}: FAILED")
                    await provider.disconnect()
                
            except Exception as e:
                self._connection_status[provider_name] = False
                print(f"  {provider_name}: ERROR - {e}")
    
    async def get_data_with_fallback(self, symbol: str, data_type: str = "equity") -> List[UnifiedInternalSchema]:
        """Get data with intelligent fallback logic."""
        
        # Get providers for this data type, sorted by priority
        providers = self._get_providers_by_data_type(data_type)
        
        if not providers:
            print(f"No providers available for data type: {data_type}")
            return []
        
        # Try providers in priority order
        for provider_name in providers:
            try:
                # Update stats
                self._provider_stats[provider_name]["requests"] += 1
                self._provider_stats[provider_name]["last_used"] = asyncio.get_event_loop().time()
                
                # Check if provider is connected
                if not self._connection_status.get(provider_name, False):
                    continue
                
                provider = self._provider_instances[provider_name]
                
                # Get data
                data = await provider.get_data(symbol)
                
                if data:
                    self._provider_stats[provider_name]["successes"] += 1
                    
                    # Log fallback usage
                    config = self.provider_configs[provider_name]
                    if config.priority != ProviderPriority.PRIMARY:
                        print(f"Fallback to {provider_name} for {symbol} (priority: {config.priority.name})")
                    
                    return data
                else:
                    self._provider_stats[provider_name]["failures"] += 1
                    continue
                    
            except Exception as e:
                self._provider_stats[provider_name]["failures"] += 1
                print(f"Error with {provider_name}: {e}")
                continue
        
        print(f"All providers failed for {symbol}")
        return []
    
    def _get_providers_by_data_type(self, data_type: str) -> List[str]:
        """Get providers sorted by priority for a data type."""
        
        # Filter providers by data type
        valid_providers = []
        for provider_name, config in self.provider_configs.items():
            if (config.enabled and 
                data_type in config.data_types and 
                self._connection_status.get(provider_name, False)):
                valid_providers.append((provider_name, config))
        
        # Sort by priority and reliability
        valid_providers.sort(key=lambda x: (
            x[1].priority.value,
            -x[1].reliability_score  # Higher reliability first
        ))
        
        return [provider[0] for provider in valid_providers]
    
    async def get_provider_status(self) -> Dict[str, Any]:
        """Get comprehensive provider status."""
        status = {
            "total_providers": len(self.provider_configs),
            "connected_providers": len(self._provider_instances),
            "connection_status": self._connection_status,
            "provider_stats": self._provider_stats,
            "priority_distribution": {
                "primary": 0,
                "secondary": 0,
                "fallback": 0
            }
        }
        
        # Count by priority
        for provider_name, instance in self._provider_instances.items():
            config = self.provider_configs[provider_name]
            if config.priority == ProviderPriority.PRIMARY:
                status["priority_distribution"]["primary"] += 1
            elif config.priority == ProviderPriority.SECONDARY:
                status["priority_distribution"]["secondary"] += 1
            else:
                status["priority_distribution"]["fallback"] += 1
        
        return status
    
    def get_provider_config(self, provider_name: str) -> Optional[ProviderConfig]:
        """Get provider configuration."""
        return self.provider_configs.get(provider_name)
    
    def enable_provider(self, provider_name: str) -> bool:
        """Enable a provider."""
        if provider_name in self.provider_configs:
            self.provider_configs[provider_name].enabled = True
            return True
        return False
    
    def disable_provider(self, provider_name: str) -> bool:
        """Disable a provider."""
        if provider_name in self.provider_configs:
            self.provider_configs[provider_name].enabled = False
            return True
        return False
    
    async def reconnect_provider(self, provider_name: str) -> bool:
        """Reconnect a specific provider."""
        if provider_name not in self._provider_instances:
            return False
        
        try:
            provider = self._provider_instances[provider_name]
            await provider.disconnect()
            
            connected = await provider.connect()
            self._connection_status[provider_name] = connected
            
            return connected
            
        except Exception as e:
            print(f"Error reconnecting {provider_name}: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown all providers."""
        print("Shutting down Provider Registry...")
        
        for provider_name, provider in self._provider_instances.items():
            try:
                await provider.disconnect()
                print(f"  {provider_name}: Disconnected")
            except Exception as e:
                print(f"  {provider_name}: Error disconnecting - {e}")
        
        self._provider_instances.clear()
        self._connection_status.clear()


# Global registry instance
_provider_registry: Optional[ProviderRegistry] = None


def get_provider_registry() -> ProviderRegistry:
    """Get global provider registry."""
    global _provider_registry
    if _provider_registry is None:
        _provider_registry = ProviderRegistry()
    return _provider_registry


async def main():
    """Test provider registry with fallback."""
    registry = get_provider_registry()
    
    print("Testing Provider Registry with Fallback")
    print("=" * 50)
    
    # Initialize registry
    await registry.initialize()
    
    # Get status
    status = await registry.get_provider_status()
    print(f"\nRegistry Status:")
    print(f"  Total providers: {status['total_providers']}")
    print(f"  Connected: {status['connected_providers']}")
    print(f"  Priority distribution: {status['priority_distribution']}")
    
    # Test data retrieval with fallback
    print(f"\nTesting data retrieval with fallback:")
    
    # Test equity data (should use Yahoo Finance first)
    print("1. Testing equity data (AAPL):")
    data = await registry.get_data_with_fallback("AAPL", "equity")
    print(f"   Data items: {len(data)}")
    if data:
        print(f"   Source: {data[0].source}, Price: {data[0].price}")
    
    # Test macro data (should use FRED first)
    print("\n2. Testing macro data (GDP):")
    data = await registry.get_data_with_fallback("GDP", "macro")
    print(f"   Data items: {len(data)}")
    if data:
        print(f"   Source: {data[0].source}, Value: {data[0].value}")
    
    # Test news data (should use RSS first)
    print("\n3. Testing news data:")
    data = await registry.get_data_with_fallback("", "news")
    print(f"   Data items: {len(data)}")
    if data:
        print(f"   Source: {data[0].source}, Title: {data[0].title[:50]}...")
    
    # Show provider stats
    print(f"\nProvider Stats:")
    for provider_name, stats in status['provider_stats'].items():
        if stats['requests'] > 0:
            success_rate = stats['successes'] / stats['requests']
            print(f"  {provider_name:15} | {stats['requests']:3} requests | {success_rate:.1%} success")
    
    # Shutdown
    await registry.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
