import asyncio
import logging
from typing import Dict, Any, Optional, Type
from importlib import import_module
import redis.asyncio as redis

from ..base_adapter_v2 import BaseSourceAdapter
from ..adapters.finnhub import FinnhubAdapter
from ..error_contract import MaifaIngestionError


class AdapterRegistry:
    """Factory pattern / Registry for dynamic, lazy-loading of adapters"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self._adapters: Dict[str, Type[BaseSourceAdapter]] = {}
        self._instances: Dict[str, BaseSourceAdapter] = {}
        self.logger = logging.getLogger("AdapterRegistry")
        
        # Register built-in adapters
        self._register_builtin_adapters()
    
    def _register_builtin_adapters(self):
        """Register built-in adapters"""
        self._adapters.update({
            "finnhub": FinnhubAdapter,
            # Add more built-in adapters here as they are implemented
            # "yahoo": YahooFinanceAdapter,
            # "alpha_vantage": AlphaVantageAdapter,
            # "marketstack": MarketStackAdapter,
        })
    
    def register_adapter(self, name: str, adapter_class: Type[BaseSourceAdapter]):
        """Register a new adapter class"""
        if not issubclass(adapter_class, BaseSourceAdapter):
            raise MaifaIngestionError(
                message=f"Adapter {adapter_class.__name__} must inherit from BaseSourceAdapter",
                provider_name="AdapterRegistry",
                is_transient=False
            )
        
        self._adapters[name.lower()] = adapter_class
        self.logger.info(f"Registered adapter: {name}")
    
    def unregister_adapter(self, name: str):
        """Unregister an adapter"""
        name_lower = name.lower()
        if name_lower in self._adapters:
            del self._adapters[name_lower]
            self.logger.info(f"Unregistered adapter: {name}")
        
        # Remove cached instance if exists
        if name_lower in self._instances:
            del self._instances[name_lower]
    
    def list_adapters(self) -> Dict[str, str]:
        """List all registered adapters"""
        return {
            name: adapter_class.__name__ 
            for name, adapter_class in self._adapters.items()
        }
    
    def is_adapter_registered(self, name: str) -> bool:
        """Check if an adapter is registered"""
        return name.lower() in self._adapters
    
    async def get_adapter(
        self, 
        provider_name: str, 
        config: Optional[Dict[str, Any]] = None,
        force_new: bool = False
    ) -> BaseSourceAdapter:
        """
        Get or create an adapter instance
        
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
                context={"available_adapters": list(self._adapters.keys())}
            )
        
        # Return cached instance if available and not forced to create new
        if not force_new and provider_name_lower in self._instances:
            return self._instances[provider_name_lower]
        
        # Create new instance
        adapter_class = self._adapters[provider_name_lower]
        adapter_config = config or {}
        
        try:
            # Inject Redis client and other dependencies
            instance = adapter_class(
                redis_client=self.redis_client,
                **adapter_config
            )
            
            # Cache the instance
            self._instances[provider_name_lower] = instance
            
            self.logger.info(f"Created adapter instance: {provider_name}")
            return instance
        
        except Exception as e:
            raise MaifaIngestionError(
                message=f"Failed to create adapter {provider_name}: {str(e)}",
                provider_name="AdapterRegistry",
                is_transient=False,
                context={"config": adapter_config, "error": str(e)}
            )
    
    async def _load_adapter_dynamically(self, provider_name: str):
        """Dynamically load an adapter from module"""
        try:
            # Try to import from adapters package
            module_name = f"..adapters.{provider_name}"
            module = import_module(module_name, package=__package__)
            
            # Look for adapter class (e.g., FinnhubAdapter, YahooFinanceAdapter)
            adapter_class_name = f"{provider_name.title()}Adapter"
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
    
    async def close_all_adapters(self):
        """Close all adapter instances"""
        for name, instance in self._instances.items():
            try:
                if hasattr(instance, 'close'):
                    await instance.close()
                self.logger.info(f"Closed adapter: {name}")
            except Exception as e:
                self.logger.error(f"Error closing adapter {name}: {e}")
        
        self._instances.clear()
    
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
                    "metrics": adapter.get_metrics() if hasattr(adapter, 'get_metrics') else {}
                }
        
        except Exception as e:
            return {
                "provider": provider_name,
                "healthy": False,
                "error": str(e)
            }
    
    async def get_all_adapter_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all registered adapters"""
        health_status = {}
        
        for provider_name in self._adapters.keys():
            health_status[provider_name] = await self.get_adapter_health(provider_name)
        
        return health_status
    
    def get_registry_metrics(self) -> Dict[str, Any]:
        """Get registry metrics"""
        return {
            "registered_adapters": len(self._adapters),
            "active_instances": len(self._instances),
            "available_adapters": list(self._adapters.keys()),
            "active_instances_list": list(self._instances.keys())
        }


# Global registry instance (will be initialized with Redis client)
_adapter_registry: Optional[AdapterRegistry] = None


def get_adapter_registry(redis_client: redis.Redis) -> AdapterRegistry:
    """Get or create the global adapter registry"""
    global _adapter_registry
    if _adapter_registry is None:
        _adapter_registry = AdapterRegistry(redis_client)
    return _adapter_registry


async def get_adapter(provider_name: str, config: Optional[Dict[str, Any]] = None) -> BaseSourceAdapter:
    """Convenience function to get an adapter from the global registry"""
    if _adapter_registry is None:
        raise MaifaIngestionError(
            message="Adapter registry not initialized. Call get_adapter_registry() first.",
            provider_name="AdapterRegistry",
            is_transient=False
        )
    
    return await _adapter_registry.get_adapter(provider_name, config)
