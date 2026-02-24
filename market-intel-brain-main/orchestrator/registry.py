"""
Adapter Registry with Singleton Pattern

This module implements the adapter registry using the Singleton pattern
to manage adapter registration and retrieval throughout the application.
"""

import inspect
import logging
from typing import Dict, Type, Any, Optional, List, Callable
from functools import wraps
from threading import Lock


class AdapterRegistry:
    """
    Singleton registry for managing data source adapters.
    
    This class implements the Singleton pattern to ensure only one instance
    exists throughout the application. It provides methods for registering,
    retrieving, and managing adapters.
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        """Implement Singleton pattern with thread safety."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the registry if not already initialized."""
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._adapters: Dict[str, Type] = {}
        self._adapter_metadata: Dict[str, Dict[str, Any]] = {}
        self._logger = logging.getLogger("AdapterRegistry")
        self._initialized = True
        
        self._logger.info("AdapterRegistry initialized (Singleton)")
    
    def register(self, name: str, adapter_class: Type, **metadata) -> None:
        """
        Register an adapter class with the registry.
        
        Args:
            name: Unique name for the adapter
            adapter_class: The adapter class to register
            **metadata: Additional metadata about the adapter
            
        Raises:
            ValueError: If adapter name already exists or class is invalid
        """
        if name in self._adapters:
            raise ValueError(f"Adapter '{name}' is already registered")
        
        if not inspect.isclass(adapter_class):
            raise ValueError(f"Adapter must be a class, got {type(adapter_class)}")
        
        # Validate that the adapter has required methods
        self._validate_adapter_class(adapter_class)
        
        # Store adapter and metadata
        self._adapters[name] = adapter_class
        self._adapter_metadata[name] = {
            'name': name,
            'class_name': adapter_class.__name__,
            'module': adapter_class.__module__,
            'doc': adapter_class.__doc__,
            'registered_at': inspect.cleandoc(str(inspect.getframeinfo(inspect.currentframe()).lineno)),
            **metadata
        }
        
        self._logger.info(f"Registered adapter: {name} -> {adapter_class.__name__}")
    
    def _validate_adapter_class(self, adapter_class: Type) -> None:
        """
        Validate that the adapter class has required methods/attributes.
        
        Args:
            adapter_class: Class to validate
            
        Raises:
            ValueError: If class doesn't meet requirements
        """
        required_methods = ['__init__']
        
        for method_name in required_methods:
            if not hasattr(adapter_class, method_name):
                raise ValueError(f"Adapter class must have method: {method_name}")
            
            method = getattr(adapter_class, method_name)
            if not callable(method):
                raise ValueError(f"Adapter method '{method_name}' must be callable")
    
    def get(self, name: str) -> Optional[Type]:
        """
        Get an adapter class by name.
        
        Args:
            name: Name of the adapter to retrieve
            
        Returns:
            Adapter class or None if not found
        """
        return self._adapters.get(name)
    
    def create_instance(self, name: str, **kwargs) -> Any:
        """
        Create an instance of a registered adapter.
        
        Args:
            name: Name of the adapter
            **kwargs: Arguments to pass to adapter constructor
            
        Returns:
            Instance of the adapter
            
        Raises:
            ValueError: If adapter not found or instantiation fails
        """
        adapter_class = self.get(name)
        if adapter_class is None:
            raise ValueError(f"Adapter '{name}' not found in registry")
        
        try:
            return adapter_class(**kwargs)
        except Exception as e:
            raise ValueError(f"Failed to create instance of adapter '{name}': {e}") from e
    
    def list_adapters(self) -> List[str]:
        """
        Get a list of all registered adapter names.
        
        Returns:
            List of adapter names
        """
        return list(self._adapters.keys())
    
    def get_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific adapter.
        
        Args:
            name: Name of the adapter
            
        Returns:
            Metadata dictionary or None if not found
        """
        return self._adapter_metadata.get(name)
    
    def get_all_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Get metadata for all registered adapters.
        
        Returns:
            Dictionary of adapter metadata
        """
        return self._adapter_metadata.copy()
    
    def unregister(self, name: str) -> bool:
        """
        Unregister an adapter.
        
        Args:
            name: Name of the adapter to unregister
            
        Returns:
            True if adapter was unregistered, False if not found
        """
        if name in self._adapters:
            del self._adapters[name]
            if name in self._adapter_metadata:
                del self._adapter_metadata[name]
            self._logger.info(f"Unregistered adapter: {name}")
            return True
        return False
    
    def clear(self) -> None:
        """Clear all registered adapters."""
        self._adapters.clear()
        self._adapter_metadata.clear()
        self._logger.info("Cleared all adapters from registry")
    
    def is_registered(self, name: str) -> bool:
        """
        Check if an adapter is registered.
        
        Args:
            name: Name of the adapter
            
        Returns:
            True if registered, False otherwise
        """
        return name in self._adapters
    
    def get_adapter_count(self) -> int:
        """
        Get the number of registered adapters.
        
        Returns:
            Number of registered adapters
        """
        return len(self._adapters)
    
    def get_registry_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the registry.
        
        Returns:
            Registry information dictionary
        """
        return {
            'adapter_count': self.get_adapter_count(),
            'adapters': self.list_adapters(),
            'metadata': self.get_all_metadata(),
            'singleton_instance': id(self)
        }


def register_adapter(name: str, **metadata):
    """
    Decorator for registering adapter classes.
    
    This decorator automatically registers the decorated class with the
    global AdapterRegistry instance when the module is imported.
    
    Args:
        name: Name to register the adapter under
        **metadata: Additional metadata about the adapter
        
    Returns:
        Decorator function
        
    Example:
        @register_adapter('my_provider', version='1.0', description='My custom provider')
        class MyAdapter:
            def __init__(self, **kwargs):
                pass
    """
    def decorator(adapter_class: Type) -> Type:
        # Get the global registry instance
        registry = AdapterRegistry()
        
        # Register the adapter
        try:
            registry.register(name, adapter_class, **metadata)
        except Exception as e:
            # Log error but don't fail module import
            logger = logging.getLogger("register_adapter")
            logger.error(f"Failed to register adapter '{name}': {e}")
            # Re-raise to make the issue visible during development
            raise
        
        return adapter_class
    
    return decorator


class AdapterRegistryError(Exception):
    """Custom exception for adapter registry errors."""
    pass


class AdapterNotFoundError(AdapterRegistryError):
    """Raised when an adapter is not found in the registry."""
    
    def __init__(self, name: str):
        super().__init__(f"Adapter '{name}' not found in registry")
        self.name = name


class AdapterRegistrationError(AdapterRegistryError):
    """Raised when adapter registration fails."""
    
    def __init__(self, name: str, reason: str):
        super().__init__(f"Failed to register adapter '{name}': {reason}")
        self.name = name
        self.reason = reason


class AdapterInstantiationError(AdapterRegistryError):
    """Raised when adapter instantiation fails."""
    
    def __init__(self, name: str, reason: str):
        super().__init__(f"Failed to instantiate adapter '{name}': {reason}")
        self.name = name
        self.reason = reason
