import asyncio
import logging
from typing import Dict, Any, Optional, Type, Set
from importlib import import_module
import weakref
from datetime import datetime

from ..base_adapter_v2 import BaseSourceAdapter
from ..adapters import (
    FinnhubAdapter, YahooFinanceAdapter, MarketStackAdapter,
    FinancialModelingPrepAdapter, NewsCatcherAdapter,
    EconDBAdapter, TradingEconomicsAdapter
)
from ..error_contract import MaifaIngestionError


class AdapterRegistry:
    """
    Registry/Factory pattern for managing data provider adapters.
    
    Features:
    - Dynamic adapter registration and discovery
    - Singleton pattern for connection pool reuse
    - Lazy loading and initialization
    - SWR integration points (stubs)
    - Smart TTL integration points (stubs)
    """
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.logger = logging.getLogger("AdapterRegistry")
        
        # Registry for adapter classes
        self._adapter_classes: Dict[str, Type[BaseSourceAdapter]] = {}
        
        # Singleton instances using weak references for automatic cleanup
        self._adapter_instances: Dict[str, weakref.ref] = {}
        
        # SWR cache registry (integration point)
        self._swr_engines: Dict[str, Any] = {}
        
        # Smart TTL configuration (integration point)
        self._ttl_config: Dict[str, Dict[str, int]] = {}
        
        # Initialize built-in adapters
        self._register_builtin_adapters()
        
        # Initialize default TTL configuration
        self._initialize_default_ttl()
    
    def _register_builtin_adapters(self):
        """Register built-in adapter classes"""
        builtin_adapters = {
            "finnhub": FinnhubAdapter,
            "yahoo_finance": YahooFinanceAdapter,
            "marketstack": MarketStackAdapter,
            "financial_modeling_prep": FinancialModelingPrepAdapter,
            "news_catcher": NewsCatcherAdapter,
            "econdb": EconDBAdapter,
            "trading_economics": TradingEconomicsAdapter
        }
        
        for name, adapter_class in builtin_adapters.items():
            self.register_adapter(name, adapter_class)
            self.logger.debug(f"Registered built-in adapter: {name}")
    
    def _initialize_default_ttl(self):
        """Initialize default Smart TTL configuration"""
        # Default TTL values in seconds (can be overridden via config)
        self._ttl_config = {
            "finnhub": {"fresh": 10, "stale": 60},      # Fast updates
            "yahoo_finance": {"fresh": 15, "stale": 120},
            "marketstack": {"fresh": 20, "stale": 180},
            "financial_modeling_prep": {"fresh": 25, "stale": 300},
            "news_catcher": {"fresh": 300, "stale": 1800},  # News changes slower
            "econdb": {"fresh": 600, "stale": 3600},      # Economic data static
            "trading_economics": {"fresh": 120, "stale": 720}
        }
    
    def register_adapter(self, name: str, adapter_class: Type[BaseSourceAdapter]):
        """
        Register a new adapter class
        
        Args:
            name: Adapter name (lowercase, alphanumeric + underscores)
            adapter_class: Class inheriting from BaseSourceAdapter
        """
        if not issubclass(adapter_class, BaseSourceAdapter):
            raise MaifaIngestionError(
                message=f"Adapter {adapter_class.__name__} must inherit from BaseSourceAdapter",
                provider_name="AdapterRegistry",
                is_transient=False
            )
        
        # Validate adapter name
        if not name or not name.replace('_', '').isalnum():
            raise MaifaIngestionError(
                message=f"Invalid adapter name: {name}. Must be alphanumeric with underscores",
                provider_name="AdapterRegistry",
                is_transient=False
            )
        
        self._adapter_classes[name.lower()] = adapter_class
        self.logger.info(f"Registered adapter: {name} -> {adapter_class.__name__}")
    
    def unregister_adapter(self, name: str):
        """Unregister an adapter and cleanup its instance"""
        name_lower = name.lower()
        
        if name_lower in self._adapter_classes:
            del self._adapter_classes[name_lower]
            self.logger.info(f"Unregistered adapter: {name}")
        
        # Cleanup singleton instance
        if name_lower in self._adapter_instances:
            instance_ref = self._adapter_instances[name_lower]
            instance = instance_ref() if instance_ref else None
            
            if instance and hasattr(instance, 'close'):
                # Close adapter asynchronously
                asyncio.create_task(self._safe_close_adapter(instance))
            
            del self._adapter_instances[name_lower]
        
        # Cleanup SWR engine
        if name_lower in self._swr_engines:
            del self._swr_engines[name_lower]
    
    async def _safe_close_adapter(self, adapter: BaseSourceAdapter):
        """Safely close an adapter instance"""
        try:
            await adapter.close()
            self.logger.debug(f"Closed adapter: {adapter.provider_name}")
        except Exception as e:
            self.logger.error(f"Error closing adapter {adapter.provider_name}: {e}")
    
    def list_adapters(self) -> Dict[str, str]:
        """List all registered adapters"""
        return {
            name: adapter_class.__name__ 
            for name, adapter_class in self._adapter_classes.items()
        }
    
    def is_adapter_registered(self, name: str) -> bool:
        """Check if an adapter is registered"""
        return name.lower() in self._adapter_classes
    
    async def get_adapter(
        self, 
        provider_name: str, 
        config: Optional[Dict[str, Any]] = None,
        force_new: bool = False
    ) -> BaseSourceAdapter:
        """
        Get or create an adapter instance (singleton pattern)
        
        Args:
            provider_name: Name of the provider/adapter
            config: Configuration dictionary for the adapter
            force_new: Force creation of new instance even if cached
        
        Returns:
            BaseSourceAdapter instance
        """
        provider_name_lower = provider_name.lower()
        
        if not self.is_adapter_registered(provider_name_lower):
            # Try to dynamically load the adapter
            await self._load_adapter_dynamically(provider_name_lower)
        
        if not self.is_adapter_registered(provider_name_lower):
            raise MaifaIngestionError(
                message=f"Adapter not found: {provider_name}",
                provider_name="AdapterRegistry",
                suggested_action=f"Register {provider_name} adapter or check spelling",
                is_transient=False,
                context={"available_adapters": list(self._adapter_classes.keys())}
            )
        
        # Return cached instance if available and not forced to create new
        if not force_new and provider_name_lower in self._adapter_instances:
            instance_ref = self._adapter_instances[provider_name_lower]
            instance = instance_ref() if instance_ref else None
            
            if instance:
                self.logger.debug(f"Returning cached adapter instance: {provider_name}")
                return instance
        
        # Create new instance
        adapter_class = self._adapter_classes[provider_name_lower]
        adapter_config = config or {}
        
        try:
            # Inject Redis client and other dependencies
            instance = adapter_class(
                redis_client=self.redis_client,
                **adapter_config
            )
            
            # Store instance using weak reference for automatic cleanup
            self._adapter_instances[provider_name_lower] = weakref.ref(instance)
            
            # Initialize SWR engine for this adapter (integration point)
            await self._initialize_swr_engine(provider_name_lower, instance)
            
            self.logger.info(f"Created adapter instance: {provider_name}")
            return instance
        
        except Exception as e:
            raise MaifaIngestionError(
                message=f"Failed to create adapter {provider_name}: {str(e)}",
                provider_name="AdapterRegistry",
                is_transient=False,
                context={"config": adapter_config, "error": str(e)}
            )
    
    async def _initialize_swr_engine(self, provider_name: str, adapter: BaseSourceAdapter):
        """
        Initialize SWR engine for adapter (integration stub)
        
        This is where SWR (Stale-While-Revalidate) would be initialized
        for each adapter. The SWR engine would handle:
        - Cache key generation using MAIFAFingerprint
        - Background refresh logic
        - Stale-while-revalidate patterns
        """
        # SWR Integration Point
        # Example: self._swr_engines[provider_name] = SWREngine(adapter)
        self.logger.debug(f"SWR engine initialization point for: {provider_name}")
    
    async def _load_adapter_dynamically(self, provider_name: str):
        """Dynamically load an adapter from module"""
        try:
            # Try to import from adapters package
            module_name = f"..adapters.{provider_name}"
            module = import_module(module_name, package=__package__)
            
            # Look for adapter class (e.g., FinnhubAdapter, YahooFinanceAdapter)
            adapter_class_name = self._convert_to_class_name(provider_name)
            adapter_class = getattr(module, adapter_class_name, None)
            
            if adapter_class and issubclass(adapter_class, BaseSourceAdapter):
                self.register_adapter(provider_name, adapter_class)
                self.logger.info(f"Dynamically loaded adapter: {provider_name}")
            else:
                self.logger.warning(f"No valid adapter class found in module: {module_name}")
        
        except ImportError as e:
            self.logger.debug(f"Could not import adapter module for {provider_name}: {e}")
        except Exception as e:
            self.logger.error(f"Error loading adapter {provider_name}: {e}")
    
    def _convert_to_class_name(self, provider_name: str) -> str:
        """Convert provider name to class name (e.g., yahoo_finance -> YahooFinanceAdapter)"""
        parts = provider_name.split('_')
        class_name = ''.join(part.title() for part in parts) + 'Adapter'
        return class_name
    
    def get_ttl_config(self, provider_name: str) -> Dict[str, int]:
        """
        Get Smart TTL configuration for provider (integration stub)
        
        This is where Smart TTL would be integrated:
        - Fresh TTL for immediate serving
        - Stale TTL for background refresh window
        - Provider-specific optimization
        """
        provider_name_lower = provider_name.lower()
        return self._ttl_config.get(provider_name_lower, {"fresh": 30, "stale": 300})
    
    def set_ttl_config(self, provider_name: str, fresh_ttl: int, stale_ttl: int):
        """Set Smart TTL configuration for provider"""
        provider_name_lower = provider_name.lower()
        self._ttl_config[provider_name_lower] = {
            "fresh": fresh_ttl,
            "stale": stale_ttl
        }
        self.logger.info(f"Updated TTL config for {provider_name}: fresh={fresh_ttl}s, stale={stale_ttl}s")
    
    async def close_all_adapters(self):
        """Close all adapter instances"""
        close_tasks = []
        
        for name, instance_ref in self._adapter_instances.items():
            instance = instance_ref() if instance_ref else None
            if instance and hasattr(instance, 'close'):
                close_tasks.append(self._safe_close_adapter(instance))
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        self._adapter_instances.clear()
        self.logger.info("Closed all adapter instances")
    
    async def get_adapter_health(self, provider_name: str) -> Dict[str, Any]:
        """Get health status of a specific adapter"""
        try:
            adapter = await self.get_adapter(provider_name)
            
            if hasattr(adapter, 'get_adapter_health'):
                return await adapter.get_adapter_health()
            else:
                # Basic health check
                return {
                    "provider": provider_name,
                    "healthy": True,
                    "message": "Adapter instance exists and is accessible",
                    "metrics": adapter.get_metrics() if hasattr(adapter, 'get_metrics') else {},
                    "ttl_config": self.get_ttl_config(provider_name),
                    "swr_enabled": provider_name in self._swr_engines
                }
        
        except Exception as e:
            return {
                "provider": provider_name,
                "healthy": False,
                "error": str(e),
                "ttl_config": self.get_ttl_config(provider_name)
            }
    
    async def get_all_adapter_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all registered adapters"""
        health_status = {}
        
        for provider_name in self._adapter_classes.keys():
            health_status[provider_name] = await self.get_adapter_health(provider_name)
        
        return health_status
    
    def get_registry_metrics(self) -> Dict[str, Any]:
        """Get registry metrics"""
        active_instances = 0
        for instance_ref in self._adapter_instances.values():
            if instance_ref():
                active_instances += 1
        
        return {
            "registered_adapters": len(self._adapter_classes),
            "active_instances": active_instances,
            "available_adapters": list(self._adapter_classes.keys()),
            "active_instances_list": [
                name for name, instance_ref in self._adapter_instances.items() 
                if instance_ref()
            ],
            "swr_engines": len(self._swr_engines),
            "ttl_configs": len(self._ttl_config)
        }


# Global registry instance
_global_registry: Optional[AdapterRegistry] = None


def get_adapter_registry(redis_client=None) -> AdapterRegistry:
    """Get or create the global adapter registry"""
    global _global_registry
    if _global_registry is None:
        _global_registry = AdapterRegistry(redis_client)
    return _global_registry


async def get_adapter(provider_name: str, config: Optional[Dict[str, Any]] = None) -> BaseSourceAdapter:
    """Convenience function to get an adapter from the global registry"""
    registry = get_adapter_registry()
    return await registry.get_adapter(provider_name, config)
