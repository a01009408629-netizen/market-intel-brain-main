"""
Mock Vector Storage - Reference Implementation

Enterprise-grade mock implementation for testing and development.
Provides full IVectorStorage interface compliance without external dependencies.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import hashlib
import json

from .interfaces import (
    IVectorStorage,
    IEmbeddingGenerator,
    VectorStorageConfig,
    EmbeddingMetadata,
    SimilaritySearchResult,
    SearchQuery,
    VectorStorageStats,
    DistanceMetric,
    StorageType
)


class MockEmbeddingGenerator(IEmbeddingGenerator):
    """Mock embedding generator for testing."""
    
    def __init__(self, dimension: int = 1536, logger: Optional[logging.Logger] = None):
        self.dimension = dimension
        self.logger = logger or logging.getLogger("MockEmbeddingGenerator")
        self._model_info = {
            "name": "mock-embedding-model",
            "version": "1.0.0",
            "dimension": dimension,
            "max_tokens": 8192
        }
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate mock embedding for text."""
        await asyncio.sleep(0.01)  # Simulate processing time
        
        # Generate deterministic but pseudo-random embedding based on text hash
        hash_input = f"{text}_{self.dimension}"
        hash_obj = hashlib.sha256(hash_input.encode())
        
        # Convert hash to float values
        embedding = []
        for i in range(self.dimension):
            # Use different parts of the hash for each dimension
            byte_index = (i * 4) % 32
            hash_bytes = hash_obj.digest()[byte_index:byte_index + 4]
            
            # Convert to float between -1 and 1
            int_value = int.from_bytes(hash_bytes, byteorder='big', signed=True)
            normalized = int_value / (2**31 - 1)
            embedding.append(normalized)
        
        # Normalize the embedding
        norm = sum(x * x for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings for multiple texts."""
        tasks = [self.generate_embedding(text) for text in texts]
        return await asyncio.gather(*tasks)
    
    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return self.dimension
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return self._model_info.copy()


class MockVectorStorage(IVectorStorage):
    """
    Mock vector storage implementation for testing and development.
    
    Provides full IVectorStorage interface compliance without external dependencies.
    """
    
    def __init__(self, config: VectorStorageConfig, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        
        # In-memory storage
        self._embeddings: Dict[str, Tuple[List[float], EmbeddingMetadata]] = {}
        self._indexes: Dict[str, Dict[str, Any]] = {}
        
        # Statistics
        self._stats = VectorStorageStats()
        self._query_times: List[float] = []
        self._index_times: List[float] = []
        
        # Mock connection state
        self._is_connected = False
        self._connection_time = 0.0
        
        self.logger.info(f"MockVectorStorage initialized (dimension: {config.dimension})")
    
    async def initialize(self) -> bool:
        """Initialize the mock storage connection."""
        try:
            # Simulate connection time
            await asyncio.sleep(0.05)
            self._is_connected = True
            self._connection_time = time.time()
            
            # Create default index if needed
            if self.config.create_index_if_not_exists:
                await self.create_index(
                    self.config.index_name,
                    self.config.dimension,
                    self.config.metric
                )
            
            self.logger.info("✅ MockVectorStorage connected")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize MockVectorStorage: {e}")
            return False
    
    async def close(self) -> None:
        """Close the mock storage connection."""
        self._is_connected = False
        self.logger.info("✅ MockVectorStorage disconnected")
    
    async def health_check(self) -> bool:
        """Check if the mock storage is healthy."""
        return self._is_connected
    
    async def create_index(self, index_name: str, dimension: int, metric: DistanceMetric) -> bool:
        """Create a new vector index."""
        try:
            await asyncio.sleep(0.01)  # Simulate index creation time
            
            self._indexes[index_name] = {
                "name": index_name,
                "dimension": dimension,
                "metric": metric,
                "created_at": datetime.now(timezone.utc),
                "vector_count": 0
            }
            
            self.logger.debug(f"✅ Created index: {index_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create index {index_name}: {e}")
            return False
    
    async def drop_index(self, index_name: str) -> bool:
        """Drop a vector index."""
        try:
            await asyncio.sleep(0.01)  # Simulate index drop time
            
            if index_name in self._indexes:
                del self._indexes[index_name]
                
                # Remove embeddings associated with this index
                embeddings_to_remove = [
                    emb_id for emb_id, (_, meta) in self._embeddings.items()
                    if meta.custom_metadata.get("index_name") == index_name
                ]
                
                for emb_id in embeddings_to_remove:
                    del self._embeddings[emb_id]
                
                self.logger.debug(f"✅ Dropped index: {index_name}")
                return True
            else:
                self.logger.warning(f"⚠️ Index not found: {index_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Failed to drop index {index_name}: {e}")
            return False
    
    async def list_indexes(self) -> List[str]:
        """List all available indexes."""
        return list(self._indexes.keys())
    
    async def insert_embedding(
        self,
        vector: List[float],
        metadata: EmbeddingMetadata,
        index_name: Optional[str] = None
    ) -> str:
        """Insert a single embedding with metadata."""
        start_time = time.time()
        
        try:
            # Validate vector
            if len(vector) != self.config.dimension:
                raise ValueError(f"Vector dimension mismatch: expected {self.config.dimension}, got {len(vector)}")
            
            # Generate embedding ID
            embedding_id = metadata.embedding_id or str(uuid.uuid4())
            
            # Store embedding
            self._embeddings[embedding_id] = (vector.copy(), metadata)
            
            # Update index statistics
            if index_name and index_name in self._indexes:
                self._indexes[index_name]["vector_count"] += 1
            elif self.config.index_name in self._indexes:
                self._indexes[self.config.index_name]["vector_count"] += 1
            
            # Update statistics
            index_time = (time.time() - start_time) * 1000
            self._index_times.append(index_time)
            
            self.logger.debug(f"✅ Inserted embedding: {embedding_id}")
            return embedding_id
            
        except Exception as e:
            self.logger.error(f"❌ Failed to insert embedding: {e}")
            raise
    
    async def insert_embeddings_batch(
        self,
        vectors: List[List[float]],
        metadata_list: List[EmbeddingMetadata],
        index_name: Optional[str] = None
    ) -> List[str]:
        """Insert multiple embeddings with metadata."""
        start_time = time.time()
        
        try:
            if len(vectors) != len(metadata_list):
                raise ValueError("Vectors and metadata lists must have the same length")
            
            if len(vectors) > self.config.max_batch_size:
                raise ValueError(f"Batch size exceeds maximum: {self.config.max_batch_size}")
            
            embedding_ids = []
            
            # Insert each embedding
            for vector, metadata in zip(vectors, metadata_list):
                embedding_id = await self.insert_embedding(vector, metadata, index_name)
                embedding_ids.append(embedding_id)
            
            self.logger.debug(f"✅ Inserted {len(embedding_ids)} embeddings in batch")
            return embedding_ids
            
        except Exception as e:
            self.logger.error(f"❌ Failed to insert batch embeddings: {e}")
            raise
    
    async def update_embedding(
        self,
        embedding_id: str,
        vector: Optional[List[float]] = None,
        metadata: Optional[EmbeddingMetadata] = None
    ) -> bool:
        """Update an existing embedding."""
        try:
            if embedding_id not in self._embeddings:
                self.logger.warning(f"⚠️ Embedding not found: {embedding_id}")
                return False
            
            current_vector, current_metadata = self._embeddings[embedding_id]
            
            # Update vector if provided
            if vector is not None:
                if len(vector) != self.config.dimension:
                    raise ValueError(f"Vector dimension mismatch: expected {self.config.dimension}, got {len(vector)}")
                current_vector = vector.copy()
            
            # Update metadata if provided
            if metadata is not None:
                current_metadata = metadata
                current_metadata.updated_at = datetime.now(timezone.utc)
            
            # Store updated embedding
            self._embeddings[embedding_id] = (current_vector, current_metadata)
            
            self.logger.debug(f"✅ Updated embedding: {embedding_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to update embedding {embedding_id}: {e}")
            return False
    
    async def delete_embedding(self, embedding_id: str) -> bool:
        """Delete an embedding."""
        try:
            if embedding_id in self._embeddings:
                del self._embeddings[embedding_id]
                self.logger.debug(f"✅ Deleted embedding: {embedding_id}")
                return True
            else:
                self.logger.warning(f"⚠️ Embedding not found: {embedding_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Failed to delete embedding {embedding_id}: {e}")
            return False
    
    async def get_embedding(self, embedding_id: str) -> Tuple[List[float], EmbeddingMetadata]:
        """Get an embedding by ID."""
        try:
            if embedding_id in self._embeddings:
                vector, metadata = self._embeddings[embedding_id]
                return vector.copy(), metadata
            else:
                raise ValueError(f"Embedding not found: {embedding_id}")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to get embedding {embedding_id}: {e}")
            raise
    
    async def similarity_search(self, query: SearchQuery, index_name: Optional[str] = None) -> List[SimilaritySearchResult]:
        """Perform similarity search."""
        start_time = time.time()
        
        try:
            # Calculate similarities
            results = []
            
            for embedding_id, (vector, metadata) in self._embeddings.items():
                # Apply filters
                if not self._passes_filters(metadata, query):
                    continue
                
                # Calculate similarity
                similarity = self._calculate_similarity(query.query_vector, vector, self.config.metric)
                
                if similarity >= query.threshold:
                    result = SimilaritySearchResult(
                        embedding_id=embedding_id,
                        similarity_score=similarity,
                        rank=0,  # Will be set after sorting
                        metadata=metadata,
                        search_time_ms=0  # Will be set after timing
                    )
                    results.append(result)
            
            # Sort by similarity (descending)
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            
            # Apply top_k limit
            results = results[:query.top_k]
            
            # Set ranks and timing
            search_time = (time.time() - start_time) * 1000
            for i, result in enumerate(results):
                result.rank = i + 1
                result.search_time_ms = search_time
            
            # Update statistics
            self._query_times.append(search_time)
            
            self.logger.debug(f"✅ Similarity search: {len(results)} results in {search_time:.2f}ms")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Similarity search failed: {e}")
            raise
    
    async def hybrid_search(
        self,
        query_vector: List[float],
        text_query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        index_name: Optional[str] = None
    ) -> List[SimilaritySearchResult]:
        """Perform hybrid vector + text search."""
        # For mock implementation, just perform vector search
        query = SearchQuery(
            query_vector=query_vector,
            top_k=top_k,
            custom_filters=filters or {}
        )
        
        return await self.similarity_search(query, index_name)
    
    async def get_stats(self, index_name: Optional[str] = None) -> VectorStorageStats:
        """Get storage statistics."""
        try:
            # Basic statistics
            total_embeddings = len(self._embeddings)
            
            # Calculate storage size (rough estimate)
            storage_size = 0
            for vector, metadata in self._embeddings.values():
                storage_size += len(vector) * 4  # 4 bytes per float
                storage_size += len(json.dumps(metadata.to_dict()).encode())  # Metadata size
            
            # Performance statistics
            avg_query_time = sum(self._query_times) / len(self._query_times) if self._query_times else 0.0
            avg_index_time = sum(self._index_times) / len(self._index_times) if self._index_times else 0.0
            
            # Content statistics
            content_types = {}
            categories = {}
            sources = {}
            
            oldest_embedding = None
            newest_embedding = None
            
            avg_quality = 0.0
            avg_confidence = 0.0
            
            for _, metadata in self._embeddings.values():
                # Content type stats
                ct = metadata.content_type
                content_types[ct] = content_types.get(ct, 0) + 1
                
                # Category stats
                if metadata.category:
                    cat = metadata.category
                    categories[cat] = categories.get(cat, 0) + 1
                
                # Source stats
                if metadata.source:
                    src = metadata.source
                    sources[src] = sources.get(src, 0) + 1
                
                # Temporal stats
                if oldest_embedding is None or metadata.created_at < oldest_embedding:
                    oldest_embedding = metadata.created_at
                if newest_embedding is None or metadata.created_at > newest_embedding:
                    newest_embedding = metadata.created_at
                
                # Quality stats
                avg_quality += metadata.quality_score
                avg_confidence += metadata.confidence
            
            if total_embeddings > 0:
                avg_quality /= total_embeddings
                avg_confidence /= total_embeddings
            
            # Create stats object
            stats = VectorStorageStats(
                total_embeddings=total_embeddings,
                storage_size_bytes=storage_size,
                avg_query_time_ms=avg_query_time,
                avg_index_time_ms=avg_index_time,
                avg_quality_score=avg_quality,
                avg_confidence=avg_confidence,
                content_types=content_types,
                categories=categories,
                sources=sources,
                oldest_embedding=oldest_embedding,
                newest_embedding=newest_embedding,
                connection_status="connected" if self._is_connected else "disconnected",
                last_health_check=datetime.now(timezone.utc)
            )
            
            return stats
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get stats: {e}")
            return VectorStorageStats()
    
    async def cleanup_expired(self) -> int:
        """Clean up expired embeddings."""
        try:
            now = datetime.now(timezone.utc)
            expired_count = 0
            
            expired_ids = [
                emb_id for emb_id, (_, metadata) in self._embeddings.items()
                if metadata.expires_at and metadata.expires_at < now
            ]
            
            for emb_id in expired_ids:
                await self.delete_embedding(emb_id)
                expired_count += 1
            
            self.logger.debug(f"✅ Cleaned up {expired_count} expired embeddings")
            return expired_count
            
        except Exception as e:
            self.logger.error(f"❌ Failed to cleanup expired embeddings: {e}")
            return 0
    
    async def optimize_index(self, index_name: Optional[str] = None) -> bool:
        """Optimize the vector index."""
        try:
            await asyncio.sleep(0.1)  # Simulate optimization time
            self.logger.debug(f"✅ Optimized index: {index_name or 'default'}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to optimize index: {e}")
            return False
    
    def _calculate_similarity(self, vec1: List[float], vec2: List[float], metric: DistanceMetric) -> float:
        """Calculate similarity between two vectors."""
        if metric == DistanceMetric.COSINE:
            return self._cosine_similarity(vec1, vec2)
        elif metric == DistanceMetric.EUCLIDEAN:
            return self._euclidean_similarity(vec1, vec2)
        elif metric == DistanceMetric.DOT_PRODUCT:
            return self._dot_product_similarity(vec1, vec2)
        else:
            # Default to cosine
            return self._cosine_similarity(vec1, vec2)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _euclidean_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate Euclidean similarity (inverse of distance)."""
        distance = sum((a - b) ** 2 for a, b in zip(vec1, vec2)) ** 0.5
        return 1.0 / (1.0 + distance)  # Convert distance to similarity
    
    def _dot_product_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate dot product similarity."""
        return sum(a * b for a, b in zip(vec1, vec2))
    
    def _passes_filters(self, metadata: EmbeddingMetadata, query: SearchQuery) -> bool:
        """Check if metadata passes query filters."""
        # Content type filter
        if query.content_type and metadata.content_type != query.content_type:
            return False
        
        # Category filter
        if query.category and metadata.category != query.category:
            return False
        
        # Tags filter
        if query.tags:
            if not any(tag in metadata.tags for tag in query.tags):
                return False
        
        # Source filter
        if query.source and metadata.source != query.source:
            return False
        
        # Date range filter
        if query.date_range:
            start_date, end_date = query.date_range
            if not (start_date <= metadata.created_at <= end_date):
                return False
        
        # Quality filters
        if metadata.quality_score < query.min_quality_score:
            return False
        
        if metadata.confidence < query.min_confidence:
            return False
        
        # Custom filters
        for key, value in query.custom_filters.items():
            metadata_value = metadata.custom_metadata.get(key)
            if metadata_value != value:
                return False
        
        return True
