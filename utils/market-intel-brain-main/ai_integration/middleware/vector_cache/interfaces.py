"""
Vector Storage Interfaces - Abstract Layer for Vector Database Readiness

Enterprise-grade interfaces that maintain architectural flexibility
and control future vendor costs without hardcoding specific implementations.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
import numpy as np
from pydantic import BaseModel, Field, validator


class StorageType(Enum):
    """Vector storage implementation types."""
    MOCK = "mock"
    REDIS = "redis"
    PINECONE = "pinecone"
    CHROMA = "chroma"
    WEAVIATE = "weaviate"
    QDRANT = "qdrant"
    MILVUS = "milvus"
    CUSTOM = "custom"


class DistanceMetric(Enum):
    """Distance metrics for similarity search."""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"
    MANHATTAN = "manhattan"
    HAMMING = "hamming"


@dataclass
class VectorStorageConfig:
    """Configuration for vector storage implementations."""
    
    # Basic configuration
    storage_type: StorageType = StorageType.MOCK
    dimension: int = 1536  # Default for OpenAI embeddings
    metric: DistanceMetric = DistanceMetric.COSINE
    
    # Connection settings
    host: str = "localhost"
    port: int = 6379  # Default Redis port
    username: Optional[str] = None
    password: Optional[str] = None
    database: int = 0
    ssl: bool = False
    
    # Performance settings
    max_connections: int = 10
    connection_timeout_ms: int = 5000
    operation_timeout_ms: int = 10000
    
    # Index settings
    index_name: str = "default"
    create_index_if_not_exists: bool = True
    index_parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Batch settings
    batch_size: int = 100
    max_batch_size: int = 1000
    
    # Cache settings
    enable_cache: bool = True
    cache_ttl_seconds: int = 3600
    cache_size: int = 10000
    
    # Monitoring
    enable_metrics: bool = True
    metrics_interval_seconds: int = 60
    
    # Custom parameters for vendor-specific settings
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmbeddingMetadata:
    """Metadata for stored embeddings."""
    
    # Core identifiers
    embedding_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content_id: Optional[str] = None  # Reference to original content
    content_type: str = "unknown"  # Type of original content
    
    # Content metadata
    title: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    category: Optional[str] = None
    
    # Temporal metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    
    # Quality metadata
    quality_score: float = 1.0  # 0.0 to 1.0
    confidence: float = 1.0  # 0.0 to 1.0
    
    # Source metadata
    source: Optional[str] = None
    source_version: Optional[str] = None
    
    # Processing metadata
    embedding_model: str = "unknown"
    embedding_version: str = "1.0"
    processing_time_ms: float = 0.0
    
    # Custom metadata
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "embedding_id": self.embedding_id,
            "content_id": self.content_id,
            "content_type": self.content_type,
            "title": self.title,
            "summary": self.summary,
            "tags": self.tags,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "quality_score": self.quality_score,
            "confidence": self.confidence,
            "source": self.source,
            "source_version": self.source_version,
            "embedding_model": self.embedding_model,
            "embedding_version": self.embedding_version,
            "processing_time_ms": self.processing_time_ms,
            "custom_metadata": self.custom_metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddingMetadata":
        """Create from dictionary."""
        # Handle datetime fields
        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc)
        updated_at = datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(timezone.utc)
        expires_at = datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None
        
        return cls(
            embedding_id=data.get("embedding_id", str(uuid.uuid4())),
            content_id=data.get("content_id"),
            content_type=data.get("content_type", "unknown"),
            title=data.get("title"),
            summary=data.get("summary"),
            tags=data.get("tags", []),
            category=data.get("category"),
            created_at=created_at,
            updated_at=updated_at,
            expires_at=expires_at,
            quality_score=data.get("quality_score", 1.0),
            confidence=data.get("confidence", 1.0),
            source=data.get("source"),
            source_version=data.get("source_version"),
            embedding_model=data.get("embedding_model", "unknown"),
            embedding_version=data.get("embedding_version", "1.0"),
            processing_time_ms=data.get("processing_time_ms", 0.0),
            custom_metadata=data.get("custom_metadata", {})
        )


@dataclass
class SearchQuery:
    """Query for similarity search."""
    
    # Query vector
    query_vector: List[float]
    
    # Search parameters
    top_k: int = 10
    threshold: float = 0.0  # Minimum similarity threshold
    
    # Filters
    content_type: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    source: Optional[str] = None
    date_range: Optional[Tuple[datetime, datetime]] = None
    
    # Quality filters
    min_quality_score: float = 0.0
    min_confidence: float = 0.0
    
    # Custom filters
    custom_filters: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate query parameters."""
        if not self.query_vector:
            raise ValueError("Query vector cannot be empty")
        
        if self.top_k <= 0:
            raise ValueError("top_k must be positive")
        
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        
        if not 0.0 <= self.min_quality_score <= 1.0:
            raise ValueError("min_quality_score must be between 0.0 and 1.0")
        
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0.0 and 1.0")


@dataclass
class SimilaritySearchResult:
    """Result from similarity search."""
    
    # Result metadata
    embedding_id: str
    similarity_score: float
    rank: int
    
    # Embedding metadata
    metadata: EmbeddingMetadata
    
    # Search context
    query_id: Optional[str] = None
    search_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "embedding_id": self.embedding_id,
            "similarity_score": self.similarity_score,
            "rank": self.rank,
            "metadata": self.metadata.to_dict(),
            "query_id": self.query_id,
            "search_time_ms": self.search_time_ms
        }


@dataclass
class VectorStorageStats:
    """Statistics for vector storage operations."""
    
    # Storage statistics
    total_embeddings: int = 0
    storage_size_bytes: int = 0
    index_size_bytes: int = 0
    
    # Performance statistics
    avg_query_time_ms: float = 0.0
    avg_index_time_ms: float = 0.0
    queries_per_second: float = 0.0
    
    # Quality statistics
    avg_quality_score: float = 0.0
    avg_confidence: float = 0.0
    
    # Content statistics
    content_types: Dict[str, int] = field(default_factory=dict)
    categories: Dict[str, int] = field(default_factory=dict)
    sources: Dict[str, int] = field(default_factory=dict)
    
    # Temporal statistics
    oldest_embedding: Optional[datetime] = None
    newest_embedding: Optional[datetime] = None
    
    # Health statistics
    connection_status: str = "unknown"
    last_health_check: Optional[datetime] = None
    
    # Custom statistics
    custom_stats: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_embeddings": self.total_embeddings,
            "storage_size_bytes": self.storage_size_bytes,
            "index_size_bytes": self.index_size_bytes,
            "avg_query_time_ms": self.avg_query_time_ms,
            "avg_index_time_ms": self.avg_index_time_ms,
            "queries_per_second": self.queries_per_second,
            "avg_quality_score": self.avg_quality_score,
            "avg_confidence": self.avg_confidence,
            "content_types": self.content_types,
            "categories": self.categories,
            "sources": self.sources,
            "oldest_embedding": self.oldest_embedding.isoformat() if self.oldest_embedding else None,
            "newest_embedding": self.newest_embedding.isoformat() if self.newest_embedding else None,
            "connection_status": self.connection_status,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "custom_stats": self.custom_stats
        }


class IEmbeddingGenerator(ABC):
    """Abstract interface for embedding generation."""
    
    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        pass
    
    @abstractmethod
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Get embedding dimension."""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        pass


class IVectorStorage(ABC):
    """
    Abstract interface for vector storage implementations.
    
    This interface provides vendor-agnostic access to vector database
    functionality while maintaining architectural flexibility.
    """
    
    def __init__(self, config: VectorStorageConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(f"VectorStorage-{config.storage_type.value}")
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the vector storage connection."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the vector storage connection."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the vector storage is healthy."""
        pass
    
    @abstractmethod
    async def create_index(self, index_name: str, dimension: int, metric: DistanceMetric) -> bool:
        """Create a new vector index."""
        pass
    
    @abstractmethod
    async def drop_index(self, index_name: str) -> bool:
        """Drop a vector index."""
        pass
    
    @abstractmethod
    async def list_indexes(self) -> List[str]:
        """List all available indexes."""
        pass
    
    @abstractmethod
    async def insert_embedding(
        self,
        vector: List[float],
        metadata: EmbeddingMetadata,
        index_name: Optional[str] = None
    ) -> str:
        """Insert a single embedding with metadata."""
        pass
    
    @abstractmethod
    async def insert_embeddings_batch(
        self,
        vectors: List[List[float]],
        metadata_list: List[EmbeddingMetadata],
        index_name: Optional[str] = None
    ) -> List[str]:
        """Insert multiple embeddings with metadata."""
        pass
    
    @abstractmethod
    async def update_embedding(
        self,
        embedding_id: str,
        vector: Optional[List[float]] = None,
        metadata: Optional[EmbeddingMetadata] = None
    ) -> bool:
        """Update an existing embedding."""
        pass
    
    @abstractmethod
    async def delete_embedding(self, embedding_id: str) -> bool:
        """Delete an embedding."""
        pass
    
    @abstractmethod
    async def get_embedding(self, embedding_id: str) -> Tuple[List[float], EmbeddingMetadata]:
        """Get an embedding by ID."""
        pass
    
    @abstractmethod
    async def similarity_search(self, query: SearchQuery, index_name: Optional[str] = None) -> List[SimilaritySearchResult]:
        """Perform similarity search."""
        pass
    
    @abstractmethod
    async def hybrid_search(
        self,
        query_vector: List[float],
        text_query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        index_name: Optional[str] = None
    ) -> List[SimilaritySearchResult]:
        """Perform hybrid vector + text search."""
        pass
    
    @abstractmethod
    async def get_stats(self, index_name: Optional[str] = None) -> VectorStorageStats:
        """Get storage statistics."""
        pass
    
    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Clean up expired embeddings."""
        pass
    
    @abstractmethod
    async def optimize_index(self, index_name: Optional[str] = None) -> bool:
        """Optimize the vector index."""
        pass


class IVectorStorageFactory(ABC):
    """Abstract factory for creating vector storage instances."""
    
    @abstractmethod
    def create_storage(self, config: VectorStorageConfig) -> IVectorStorage:
        """Create a vector storage instance."""
        pass
    
    @abstractmethod
    def get_supported_types(self) -> List[StorageType]:
        """Get list of supported storage types."""
        pass
    
    @abstractmethod
    def validate_config(self, config: VectorStorageConfig) -> bool:
        """Validate storage configuration."""
        pass


class VectorStorageManager:
    """
    Enterprise-grade manager for vector storage operations with
    dependency injection and lifecycle management.
    """
    
    def __init__(self, factory: IVectorStorageFactory, logger: Optional[logging.Logger] = None):
        self.factory = factory
        self.logger = logger or logging.getLogger("VectorStorageManager")
        self._storage_instances: Dict[str, IVectorStorage] = {}
        self._default_config: Optional[VectorStorageConfig] = None
    
    async def initialize_default(self, config: VectorStorageConfig) -> bool:
        """Initialize default storage instance."""
        try:
            if not self.factory.validate_config(config):
                raise ValueError("Invalid configuration")
            
            storage = self.factory.create_storage(config)
            if await storage.initialize():
                self._storage_instances["default"] = storage
                self._default_config = config
                self.logger.info(f"✅ Default vector storage initialized: {config.storage_type.value}")
                return True
            else:
                raise RuntimeError("Failed to initialize storage")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize default storage: {e}")
            return False
    
    async def get_storage(self, name: str = "default") -> IVectorStorage:
        """Get a storage instance by name."""
        if name not in self._storage_instances:
            raise ValueError(f"Storage instance '{name}' not found")
        return self._storage_instances[name]
    
    async def create_storage(self, name: str, config: VectorStorageConfig) -> bool:
        """Create and initialize a new storage instance."""
        try:
            if not self.factory.validate_config(config):
                raise ValueError("Invalid configuration")
            
            storage = self.factory.create_storage(config)
            if await storage.initialize():
                self._storage_instances[name] = storage
                self.logger.info(f"✅ Storage instance '{name}' created: {config.storage_type.value}")
                return True
            else:
                raise RuntimeError("Failed to initialize storage")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to create storage '{name}': {e}")
            return False
    
    async def close_all(self) -> None:
        """Close all storage instances."""
        for name, storage in self._storage_instances.items():
            try:
                await storage.close()
                self.logger.info(f"✅ Storage instance '{name}' closed")
            except Exception as e:
                self.logger.error(f"❌ Failed to close storage '{name}': {e}")
        
        self._storage_instances.clear()
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Health check for all storage instances."""
        results = {}
        for name, storage in self._storage_instances.items():
            try:
                results[name] = await storage.health_check()
            except Exception as e:
                self.logger.error(f"❌ Health check failed for '{name}': {e}")
                results[name] = False
        return results
    
    def list_instances(self) -> List[str]:
        """List all storage instance names."""
        return list(self._storage_instances.keys())
    
    def get_factory(self) -> IVectorStorageFactory:
        """Get the storage factory."""
        return self.factory
