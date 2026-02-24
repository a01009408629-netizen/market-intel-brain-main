"""
Adapter Orchestrator - Main Orchestration Logic

This module provides the main orchestration logic that combines the registry
and loader to provide a complete plug-and-play adapter management system.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Type, Union
from datetime import datetime

from .registry import AdapterRegistry, register_adapter, AdapterNotFoundError
from .loader import AdapterLoader, AdapterLoadError


class AdapterOrchestrator:
    """
    Main orchestrator for managing adapters with plug-and-play functionality.
    
    This class combines the registry and loader to provide a complete system
    for managing adapters with automatic discovery, registration, and runtime
    management capabilities.
    """
    
    def __init__(
        self, 
        adapters_directory: str = None,
        auto_load: bool = True,
        registry: AdapterRegistry = None
    ):
        """
        Initialize the adapter orchestrator.
        
        Args:
            adapters_directory: Path to adapters directory
            auto_load: Whether to automatically load adapters on initialization
            registry: Custom registry instance (creates new if None)
        """
        self.registry = registry or AdapterRegistry()
        self.loader = AdapterLoader(adapters_directory, self.registry)
        self.logger = logging.getLogger("AdapterOrchestrator")
        
        # Track loading state
        self._loaded = False
        self._load_time = None
        self._load_results = None
        
        self.logger.info("AdapterOrchestrator initialized")
        
        if auto_load:
            self.load_adapters()
    
    def load_adapters(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load all adapters from the adapters directory.
        
        Args:
            force_reload: Whether to force reload even if already loaded
            
        Returns:
            Dictionary with loading results
        """
        if self._loaded and not force_reload:
            self.logger.info("Adapters already loaded, skipping load")
            return self._load_results or {}
        
        self.logger.info("Loading adapters...")
        self._load_time = datetime.now()
        
        try:
            self._load_results = self.loader.load_all_adapters()
            self._loaded = True
            
            self.logger.info(
                f"Adapter loading completed: "
                f"{self._load_results['total_adapters_registered']} adapters registered"
            )
            
            return self._load_results
            
        except Exception as e:
            self.logger.error(f"Failed to load adapters: {e}")
            self._loaded = False
            raise
    
    def get_adapter(self, name: str, **kwargs) -> Any:
        """
        Get an adapter instance by name.
        
        Args:
            name: Name of the adapter
            **kwargs: Arguments to pass to adapter constructor
            
        Returns:
            Adapter instance
            
        Raises:
            AdapterNotFoundError: If adapter is not registered
        """
        if not self._loaded:
            self.logger.warning("Adapters not loaded, attempting to load now")
            self.load_adapters()
        
        return self.registry.create_instance(name, **kwargs)
    
    def list_available_adapters(self) -> List[str]:
        """
        Get a list of all available adapter names.
        
        Returns:
            List of adapter names
        """
        if not self._loaded:
            self.load_adapters()
        
        return self.registry.list_adapters()
    
    def get_adapter_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific adapter.
        
        Args:
            name: Name of the adapter
            
        Returns:
            Adapter metadata or None if not found
        """
        if not self._loaded:
            self.load_adapters()
        
        return self.registry.get_metadata(name)
    
    def get_all_adapter_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all registered adapters.
        
        Returns:
            Dictionary of all adapter metadata
        """
        if not self._loaded:
            self.load_adapters()
        
        return self.registry.get_all_metadata()
    
    def reload_adapter(self, name: str) -> Dict[str, Any]:
        """
        Reload a specific adapter.
        
        Args:
            name: Name of the adapter to reload
            
        Returns:
            Dictionary with reload result
        """
        if not self._loaded:
            self.load_adapters()
        
        self.logger.info(f"Reloading adapter: {name}")
        return self.loader.reload_adapter(name)
    
    def reload_all_adapters(self) -> Dict[str, Any]:
        """
        Reload all adapters.
        
        Returns:
            Dictionary with reload results
        """
        self.logger.info("Reloading all adapters...")
        self._loaded = False
        return self.load_adapters(force_reload=True)
    
    def register_adapter(self, name: str, adapter_class: Type, **metadata) -> None:
        """
        Manually register an adapter class.
        
        Args:
            name: Name for the adapter
            adapter_class: Adapter class to register
            **metadata: Additional metadata
        """
        self.registry.register(name, adapter_class, **metadata)
        self.logger.info(f"Manually registered adapter: {name}")
    
    def unregister_adapter(self, name: str) -> bool:
        """
        Unregister an adapter.
        
        Args:
            name: Name of the adapter to unregister
            
        Returns:
            True if adapter was unregistered
        """
        result = self.registry.unregister(name)
        if result:
            self.logger.info(f"Unregistered adapter: {name}")
        return result
    
    def is_adapter_available(self, name: str) -> bool:
        """
        Check if an adapter is available.
        
        Args:
            name: Name of the adapter
            
        Returns:
            True if adapter is registered
        """
        if not self._loaded:
            self.load_adapters()
        
        return self.registry.is_registered(name)
    
    def get_adapter_class(self, name: str) -> Optional[Type]:
        """
        Get the adapter class without creating an instance.
        
        Args:
            name: Name of the adapter
            
        Returns:
            Adapter class or None if not found
        """
        if not self._loaded:
            self.load_adapters()
        
        return self.registry.get(name)
    
    def validate_adapter(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        Validate an adapter by attempting to create an instance.
        
        Args:
            name: Name of the adapter
            **kwargs: Arguments for adapter constructor
            
        Returns:
            Dictionary with validation result
        """
        result = {
            'adapter_name': name,
            'valid': False,
            'error': None,
            'instance_created': False
        }
        
        try:
            # Try to create instance
            instance = self.get_adapter(name, **kwargs)
            result['instance_created'] = True
            result['valid'] = True
            
            # Basic validation checks
            if hasattr(instance, '__dict__'):
                result['attributes'] = list(instance.__dict__.keys())
            
            self.logger.info(f"Adapter '{name}' validation passed")
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Adapter '{name}' validation failed: {e}")
        
        return result
    
    def get_orchestrator_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of the orchestrator.
        
        Returns:
            Dictionary with orchestrator status
        """
        return {
            'loaded': self._loaded,
            'load_time': self._load_time.isoformat() if self._load_time else None,
            'adapters_directory': self.loader.adapters_directory,
            'registry_info': self.registry.get_registry_info(),
            'loading_statistics': self.loader.get_loading_statistics(),
            'load_results': self._load_results
        }
    
    async def test_adapter_async(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        Test an adapter asynchronously.
        
        Args:
            name: Name of the adapter
            **kwargs: Arguments for adapter constructor
            
        Returns:
            Dictionary with test result
        """
        result = {
            'adapter_name': name,
            'test_passed': False,
            'error': None,
            'execution_time': None
        }
        
        start_time = datetime.now()
        
        try:
            # Create adapter instance
            adapter = self.get_adapter(name, **kwargs)
            
            # Try to call common methods if they exist
            test_methods = ['test_connection', 'ping', 'health_check', 'status']
            
            for method_name in test_methods:
                if hasattr(adapter, method_name):
                    method = getattr(adapter, method_name)
                    if callable(method):
                        if asyncio.iscoroutinefunction(method):
                            await method()
                        else:
                            method()
                        result['tested_method'] = method_name
                        break
            
            result['test_passed'] = True
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Async test for adapter '{name}' failed: {e}")
        
        finally:
            result['execution_time'] = (datetime.now() - start_time).total_seconds()
        
        return result
    
    def search_adapters(self, query: str) -> List[str]:
        """
        Search for adapters by name or metadata.
        
        Args:
            query: Search query
            
        Returns:
            List of matching adapter names
        """
        if not self._loaded:
            self.load_adapters()
        
        query_lower = query.lower()
        matches = []
        
        for adapter_name in self.registry.list_adapters():
            metadata = self.registry.get_metadata(adapter_name)
            
            # Search in name
            if query_lower in adapter_name.lower():
                matches.append(adapter_name)
                continue
            
            # Search in metadata
            if metadata:
                for key, value in metadata.items():
                    if isinstance(value, str) and query_lower in value.lower():
                        matches.append(adapter_name)
                        break
        
        return matches
    
    def get_adapters_by_type(self, adapter_type: str) -> List[str]:
        """
        Get adapters filtered by type.
        
        Args:
            adapter_type: Type filter (e.g., 'financial', 'news', 'crypto')
            
        Returns:
            List of adapter names of specified type
        """
        if not self._loaded:
            self.load_adapters()
        
        matching_adapters = []
        
        for adapter_name in self.registry.list_adapters():
            metadata = self.registry.get_metadata(adapter_name)
            
            if metadata and 'type' in metadata:
                if metadata['type'].lower() == adapter_type.lower():
                    matching_adapters.append(adapter_name)
            else:
                # Try to infer type from name
                if adapter_type.lower() in adapter_name.lower():
                    matching_adapters.append(adapter_name)
        
        return matching_adapters


# Global orchestrator instance for easy access
_global_orchestrator = None


def get_global_orchestrator(**kwargs) -> AdapterOrchestrator:
    """
    Get or create the global orchestrator instance.
    
    Args:
        **kwargs: Arguments for orchestrator initialization
        
    Returns:
        Global AdapterOrchestrator instance
    """
    global _global_orchestrator
    
    if _global_orchestrator is None:
        _global_orchestrator = AdapterOrchestrator(**kwargs)
    
    return _global_orchestrator


def reset_global_orchestrator():
    """Reset the global orchestrator instance."""
    global _global_orchestrator
    _global_orchestrator = None
