"""
Vector Cache Foundation - Abstract Layer for Vector Database Readiness

Enterprise-grade vector storage abstraction with dependency injection
for embeddings and similarity search without vendor lock-in.
"""

from .interfaces import (
    IVectorStorage,
    VectorStorageConfig,
    EmbeddingMetadata,
    SimilaritySearchResult,
    SearchQuery,
    VectorStorageStats
)

from .factory import (
    VectorStorageFactory,
    StorageType,
    get_vector_storage
)

from .mock_storage import (
    MockVectorStorage,
    MockEmbeddingGenerator
)

__all__ = [
    # Interfaces
    "IVectorStorage",
    "VectorStorageConfig",
    "EmbeddingMetadata",
    "SimilaritySearchResult",
    "SearchQuery",
    "VectorStorageStats",
    
    # Factory
    "VectorStorageFactory",
    "StorageType",
    "get_vector_storage",
    
    # Mock Implementation
    "MockVectorStorage",
    "MockEmbeddingGenerator"
]
