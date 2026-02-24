"""
Vector Storage Factory - Dependency Injection Container

Enterprise-grade factory pattern for vector database implementations
with vendor flexibility and cost control.
"""

import logging
from typing import Dict, Any, List, Optional, Type
from abc import ABC, abstractmethod

from .interfaces import (
    IVectorStorage,
    IVectorStorageFactory,
    VectorStorageConfig,
    StorageType,
    DistanceMetric
)
from .mock_storage import MockVectorStorage


# Import vendor-specific implementations (lazy loading)
# These would be implemented as needed
# from .redis_storage import RedisVectorStorage
# from .pinecone_storage import PineconeVectorStorage
# from .chroma_storage import ChromaVectorStorage


class VectorStorageFactory(IVectorStorageFactory):
    """
    Enterprise-grade factory for creating vector storage instances.
    
    Provides dependency injection and vendor flexibility while
    maintaining architectural control over costs.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("VectorStorageFactory")
        
        # Registry of storage implementations
        self._storage_registry: Dict[StorageType, Type[IVectorStorage]] = {
            StorageType.MOCK: MockVectorStorage,
            # Additional implementations would be registered here
            # StorageType.REDIS: RedisVectorStorage,
            # StorageType.PINECONE: PineconeVectorStorage,
            # StorageType.CHROMA: ChromaVectorStorage,
        }
        
        # Configuration templates for different storage types
        self._config_templates: Dict[StorageType, Dict[str, Any]] = {
            StorageType.MOCK: {
                "dimension": 1536,
                "metric": DistanceMetric.COSINE,
                "enable_cache": True,
                "cache_size": 1000
            },
            StorageType.REDIS: {
                "dimension": 1536,
                "metric": DistanceMetric.COSINE,
                "host": "localhost",
                "port": 6379,
                "max_connections": 10,
                "enable_cache": True
            },
            StorageType.PINECONE: {
                "dimension": 1536,
                "metric": DistanceMetric.COSINE,
                "batch_size": 100,
                "enable_metrics": True
            },
            StorageType.CHROMA: {
                "dimension": 1536,
                "metric": DistanceMetric.COSINE,
                "enable_cache": True,
                "create_index_if_not_exists": True
            }
        }
        
        # Cost tracking for vendor selection
        self._cost_per_1k_vectors: Dict[StorageType, float] = {
            StorageType.MOCK: 0.0,      # Free
            StorageType.REDIS: 0.001,   # Very low (self-hosted)
            StorageType.PINECONE: 0.70, # Medium (managed)
            StorageType.CHROMA: 0.0,    # Free (open source)
            StorageType.WEAVIATE: 0.50, # Medium (managed)
            StorageType.QDRANT: 0.30,   # Low (self-hosted available)
            StorageType.MILVUS: 0.0,   # Free (open source)
        }
    
    def create_storage(self, config: VectorStorageConfig) -> IVectorStorage:
        """Create a vector storage instance based on configuration."""
        try:
            # Validate configuration
            if not self.validate_config(config):
                raise ValueError(f"Invalid configuration for {config.storage_type.value}")
            
            # Get storage class
            storage_class = self._storage_registry.get(config.storage_type)
            if not storage_class:
                raise ValueError(f"Unsupported storage type: {config.storage_type.value}")
            
            # Log cost information
            cost_per_1k = self._cost_per_1k_vectors.get(config.storage_type, 0.0)
            if cost_per_1k > 0:
                self.logger.info(
                    f"💰 Creating {config.storage_type.value} storage "
                    f"(estimated cost: ${cost_per_1k:.3f} per 1K vectors)"
                )
            else:
                self.logger.info(f"🆓 Creating {config.storage_type.value} storage (free)")
            
            # Create and return instance
            return storage_class(config, self.logger)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create storage: {e}")
            raise
    
    def get_supported_types(self) -> List[StorageType]:
        """Get list of supported storage types."""
        return list(self._storage_registry.keys())
    
    def validate_config(self, config: VectorStorageConfig) -> bool:
        """Validate storage configuration."""
        try:
            # Check if storage type is supported
            if config.storage_type not in self._storage_registry:
                self.logger.error(f"Unsupported storage type: {config.storage_type.value}")
                return False
            
            # Validate basic configuration
            if config.dimension <= 0:
                self.logger.error("Dimension must be positive")
                return False
            
            if config.batch_size <= 0 or config.batch_size > config.max_batch_size:
                self.logger.error("Invalid batch size")
                return False
            
            # Type-specific validation
            if config.storage_type == StorageType.REDIS:
                if not config.host:
                    self.logger.error("Redis host is required")
                    return False
                if config.port <= 0 or config.port > 65535:
                    self.logger.error("Invalid Redis port")
                    return False
            
            elif config.storage_type == StorageType.PINECONE:
                if not config.custom_params.get("api_key"):
                    self.logger.error("Pinecone API key is required")
                    return False
                if not config.custom_params.get("environment"):
                    self.logger.error("Pinecone environment is required")
                    return False
            
            elif config.storage_type == StorageType.CHROMA:
                if not config.custom_params.get("path"):
                    self.logger.error("ChromaDB path is required")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration validation error: {e}")
            return False
    
    def register_storage_type(self, storage_type: StorageType, storage_class: Type[IVectorStorage]):
        """Register a new storage type implementation."""
        self._storage_registry[storage_type] = storage_class
        self.logger.info(f"✅ Registered storage type: {storage_type.value}")
    
    def unregister_storage_type(self, storage_type: StorageType):
        """Unregister a storage type implementation."""
        if storage_type in self._storage_registry:
            del self._storage_registry[storage_type]
            self.logger.info(f"🗑️ Unregistered storage type: {storage_type.value}")
    
    def get_config_template(self, storage_type: StorageType) -> Dict[str, Any]:
        """Get configuration template for a storage type."""
        return self._config_templates.get(storage_type, {}).copy()
    
    def update_config_template(self, storage_type: StorageType, template: Dict[str, Any]):
        """Update configuration template for a storage type."""
        self._config_templates[storage_type] = template.copy()
        self.logger.info(f"📝 Updated config template for {storage_type.value}")
    
    def get_cost_estimate(self, storage_type: StorageType, vector_count: int) -> float:
        """Get cost estimate for storing vectors."""
        cost_per_1k = self._cost_per_1k_vectors.get(storage_type, 0.0)
        return (vector_count / 1000) * cost_per_1k
    
    def compare_costs(self, vector_count: int) -> Dict[StorageType, float]:
        """Compare costs across all supported storage types."""
        costs = {}
        for storage_type in self.get_supported_types():
            costs[storage_type] = self.get_cost_estimate(storage_type, vector_count)
        return costs
    
    def get_cheapest_storage(self, vector_count: int) -> StorageType:
        """Get the cheapest storage option for a given vector count."""
        costs = self.compare_costs(vector_count)
        return min(costs, key=costs.get)
    
    def get_recommended_storage(
        self, 
        vector_count: int, 
        performance_requirement: str = "medium",
        budget_limit: Optional[float] = None
    ) -> StorageType:
        """Get recommended storage based on requirements."""
        supported_types = self.get_supported_types()
        
        # Filter by budget if specified
        if budget_limit is not None:
            affordable_types = []
            for storage_type in supported_types:
                cost = self.get_cost_estimate(storage_type, vector_count)
                if cost <= budget_limit:
                    affordable_types.append(storage_type)
            supported_types = affordable_types
        
        if not supported_types:
            # Fall back to mock if no affordable options
            return StorageType.MOCK
        
        # Performance-based recommendations
        if performance_requirement == "high":
            # Prefer managed solutions for high performance
            managed_types = [StorageType.PINECONE, StorageType.WEAVIATE]
            for storage_type in managed_types:
                if storage_type in supported_types:
                    return storage_type
        
        elif performance_requirement == "low":
            # Prefer free/open source for low performance requirements
            free_types = [StorageType.MOCK, StorageType.CHROMA, StorageType.MILVUS]
            for storage_type in free_types:
                if storage_type in supported_types:
                    return storage_type
        
        # Default: cheapest option
        return self.get_cheapest_storage(vector_count)
    
    def get_factory_info(self) -> Dict[str, Any]:
        """Get factory information and statistics."""
        return {
            "supported_types": [t.value for t in self.get_supported_types()],
            "registered_implementations": len(self._storage_registry),
            "cost_per_1k_vectors": {
                t.value: cost for t, cost in self._cost_per_1k_vectors.items()
                if t in self._storage_registry
            },
            "config_templates": {
                t.value: template for t, template in self._config_templates.items()
                if t in self._storage_registry
            }
        }


# Global factory instance
_vector_storage_factory: Optional[VectorStorageFactory] = None


def get_vector_storage_factory() -> VectorStorageFactory:
    """Get or create the global vector storage factory instance."""
    global _vector_storage_factory
    if _vector_storage_factory is None:
        _vector_storage_factory = VectorStorageFactory()
    return _vector_storage_factory


def get_vector_storage(config: Optional[VectorStorageConfig] = None) -> IVectorStorage:
    """
    Convenience function to get a vector storage instance.
    
    Args:
        config: Storage configuration. If None, uses mock storage.
        
    Returns:
        Configured vector storage instance.
    """
    factory = get_vector_storage_factory()
    
    if config is None:
        # Default to mock storage
        config = VectorStorageConfig(storage_type=StorageType.MOCK)
    
    return factory.create_storage(config)


# Dependency injection helper
class VectorStorageDI:
    """Dependency injection container for vector storage."""
    
    def __init__(self):
        self._factory: Optional[VectorStorageFactory] = None
        self._default_config: Optional[VectorStorageConfig] = None
        self._instances: Dict[str, IVectorStorage] = {}
    
    def set_factory(self, factory: VectorStorageFactory):
        """Set the storage factory."""
        self._factory = factory
    
    def set_default_config(self, config: VectorStorageConfig):
        """Set the default configuration."""
        self._default_config = config
    
    async def get_storage(self, name: str = "default", config: Optional[VectorStorageConfig] = None) -> IVectorStorage:
        """Get or create a storage instance."""
        if name in self._instances:
            return self._instances[name]
        
        if not self._factory:
            raise RuntimeError("Factory not set")
        
        storage_config = config or self._default_config
        if not storage_config:
            raise RuntimeError("No configuration available")
        
        storage = self._factory.create_storage(storage_config)
        await storage.initialize()
        
        self._instances[name] = storage
        return storage
    
    async def close_all(self):
        """Close all storage instances."""
        for storage in self._instances.values():
            await storage.close()
        self._instances.clear()


# Global DI container
_vector_storage_di: Optional[VectorStorageDI] = None


def get_vector_storage_di() -> VectorStorageDI:
    """Get the global dependency injection container."""
    global _vector_storage_di
    if _vector_storage_di is None:
        _vector_storage_di = VectorStorageDI()
        _vector_storage_di.set_factory(get_vector_storage_factory())
    return _vector_storage_di
