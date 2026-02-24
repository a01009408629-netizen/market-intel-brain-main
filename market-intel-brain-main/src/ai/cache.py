"""
Semantic Caching Layer - Vector DB Interface

Enterprise-grade semantic caching with Redis Vector Search
for identical analysis detection and cost optimization.
"""

import asyncio
import logging
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

from ..middleware.redis_client import RedisClient


class CacheStrategy(Enum):
    """Caching strategy enumeration."""
    EXACT_MATCH = "exact_match"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    HYBRID = "hybrid"


class EmbeddingModel(Enum):
    """Supported embedding models."""
    MINILM = "all-MiniLM-L6-v2"
    MPNET = "all-mpnet-base-v2"
    SBERT = "all-distilroberta-v1"
    FAST = "paraphrase-MiniLM-L3-v2"


@dataclass
class CacheEntry:
    """Cache entry structure."""
    cache_id: str
    query_hash: str
    embedding_hash: str
    query_text: str
    response_text: str
    embedding: List[float]
    similarity_threshold: float
    ttl_seconds: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    accessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        return {
            "cache_id": self.cache_id,
            "query_hash": self.query_hash,
            "embedding_hash": self.embedding_hash,
            "query_text": self.query_text,
            "response_text": self.response_text,
            "embedding": json.dumps(self.embedding),
            "similarity_threshold": self.similarity_threshold,
            "ttl_seconds": self.ttl_seconds,
            "created_at": self.created_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "access_count": self.access_count,
            "metadata": json.dumps(self.metadata)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Create from dictionary."""
        return cls(
            cache_id=data["cache_id"],
            query_hash=data["query_hash"],
            embedding_hash=data["embedding_hash"],
            query_text=data["query_text"],
            response_text=data["response_text"],
            embedding=json.loads(data["embedding"]),
            similarity_threshold=data["similarity_threshold"],
            ttl_seconds=data["ttl_seconds"],
            created_at=datetime.fromisoformat(data["created_at"]),
            accessed_at=datetime.fromisoformat(data["accessed_at"]),
            access_count=data["access_count"],
            metadata=json.loads(data["metadata"])
        )


@dataclass
class CacheResult:
    """Cache query result."""
    hit: bool
    entry: Optional[CacheEntry] = None
    similarity_score: Optional[float] = None
    query_time_ms: float = 0.0
    cache_stats: Optional[Dict[str, Any]] = None


class VectorCache:
    """
    Vector-based semantic caching with Redis.
    
    Features:
    - Vector similarity search
    - Exact hash matching
    - TTL-based expiration
    - Performance monitoring
    - Redis Vector Search integration
    """
    
    def __init__(
        self,
        redis_client: RedisClient,
        embedding_model: EmbeddingModel = EmbeddingModel.MINILM,
        similarity_threshold: float = 0.85,
        default_ttl: int = 300,  # 5 minutes
        max_cache_size: int = 10000,
        logger: Optional[logging.Logger] = None
    ):
        self.redis_client = redis_client
        self.embedding_model_name = embedding_model
        self.similarity_threshold = similarity_threshold
        self.default_ttl = default_ttl
        self.max_cache_size = max_cache_size
        self.logger = logger or logging.getLogger("VectorCache")
        
        # Initialize embedding model
        self.embedding_model = None
        self._initialize_embedding_model()
        
        # Cache keys
        self.cache_key_prefix = "semantic_cache"
        self.index_key = f"{self.cache_key_prefix}:index"
        self.metadata_key = f"{self.cache_key_prefix}:metadata"
        
        # Performance metrics
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_sets = 0
        self.avg_query_time_ms = 0.0
        self.total_queries = 0
        
        self.logger.info(f"VectorCache initialized: model={embedding_model.value}")
    
    def _initialize_embedding_model(self):
        """Initialize sentence transformer model."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            self.logger.warning("sentence-transformers not available, using hash-based caching only")
            return
        
        try:
            self.embedding_model = SentenceTransformer(self.embedding_model_name.value)
            self.logger.info(f"Loaded embedding model: {self.embedding_model_name.value}")
        except Exception as e:
            self.logger.error(f"Failed to load embedding model: {e}")
            self.embedding_model = None
    
    async def initialize(self) -> bool:
        """Initialize cache infrastructure."""
        try:
            # Create Redis index for vector search
            await self._create_vector_index()
            
            # Initialize cache metadata
            await self._initialize_metadata()
            
            self.logger.info("VectorCache infrastructure initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize cache: {e}")
            return False
    
    async def _create_vector_index(self):
        """Create Redis vector search index."""
        # This would use Redis RediSearch module
        # For now, we'll simulate with regular Redis operations
        await self.redis_client.hset(self.metadata_key, "index_created", "true")
        await self.redis_client.hset(self.metadata_key, "vector_dimension", "384")  # MiniLM dimension
        await self.redis_client.hset(self.metadata_key, "similarity_threshold", str(self.similarity_threshold))
    
    async def _initialize_metadata(self):
        """Initialize cache metadata."""
        metadata = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "cache_size": "0",
            "max_cache_size": str(self.max_cache_size),
            "default_ttl": str(self.default_ttl),
            "embedding_model": self.embedding_model_name.value,
            "total_queries": "0",
            "cache_hits": "0",
            "cache_misses": "0"
        }
        
        for key, value in metadata.items():
            await self.redis_client.hset(self.metadata_key, key, value)
    
    async def get(self, query: str, strategy: CacheStrategy = CacheStrategy.HYBRID) -> CacheResult:
        """
        Get cached response for query.
        
        Args:
            query: Query text
            strategy: Caching strategy
            
        Returns:
            Cache result with hit/miss information
        """
        import time
        start_time = time.time()
        
        try:
            # Generate query hash
            query_hash = self._generate_hash(query)
            
            # Try exact match first
            if strategy in [CacheStrategy.EXACT_MATCH, CacheStrategy.HYBRID]:
                exact_result = await self._get_exact_match(query_hash)
                if exact_result.hit:
                    self.cache_hits += 1
                    return exact_result
            
            # Try semantic similarity
            if strategy in [CacheStrategy.SEMANTIC_SIMILARITY, CacheStrategy.HYBRID]:
                if self.embedding_model:
                    semantic_result = await self._get_semantic_match(query)
                    if semantic_result.hit:
                        self.cache_hits += 1
                        return semantic_result
            
            # Cache miss
            self.cache_misses += 1
            query_time = (time.time() - start_time) * 1000
            self._update_query_time(query_time)
            
            return CacheResult(
                hit=False,
                query_time_ms=query_time,
                cache_stats=await self._get_cache_stats()
            )
            
        except Exception as e:
            self.logger.error(f"Cache get failed: {e}")
            self.cache_misses += 1
            return CacheResult(hit=False, query_time_ms=0)
    
    async def set(
        self,
        query: str,
        response: str,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Cache response for query.
        
        Args:
            query: Query text
            response: Response text
            ttl_seconds: TTL in seconds
            metadata: Additional metadata
            
        Returns:
            Cache entry ID
        """
        try:
            # Generate hashes
            query_hash = self._generate_hash(query)
            cache_id = str(uuid.uuid4())
            
            # Generate embedding
            embedding = await self._generate_embedding(query)
            embedding_hash = self._generate_hash(json.dumps(embedding))
            
            # Create cache entry
            entry = CacheEntry(
                cache_id=cache_id,
                query_hash=query_hash,
                embedding_hash=embedding_hash,
                query_text=query,
                response_text=response,
                embedding=embedding,
                similarity_threshold=self.similarity_threshold,
                ttl_seconds=ttl_seconds or self.default_ttl,
                metadata=metadata or {}
            )
            
            # Store in Redis
            await self._store_cache_entry(entry)
            
            # Update metrics
            self.cache_sets += 1
            await self._update_cache_metadata()
            
            self.logger.debug(f"Cached entry: {cache_id}")
            return cache_id
            
        except Exception as e:
            self.logger.error(f"Cache set failed: {e}")
            raise
    
    async def _get_exact_match(self, query_hash: str) -> CacheResult:
        """Get exact match by query hash."""
        import time
        start_time = time.time()
        
        try:
            # Look up by query hash
            cache_key = f"{self.cache_key_prefix}:hash:{query_hash}"
            cache_id = await self.redis_client.get(cache_key)
            
            if cache_id:
                # Get full entry
                entry = await self._get_cache_entry(cache_id)
                if entry:
                    # Update access stats
                    await self._update_access_stats(entry)
                    
                    query_time = (time.time() - start_time) * 1000
                    return CacheResult(
                        hit=True,
                        entry=entry,
                        similarity_score=1.0,
                        query_time_ms=query_time
                    )
            
            return CacheResult(hit=False, query_time_ms=(time.time() - start_time) * 1000)
            
        except Exception as e:
            self.logger.error(f"Exact match lookup failed: {e}")
            return CacheResult(hit=False, query_time_ms=0)
    
    async def _get_semantic_match(self, query: str) -> CacheResult:
        """Get semantic match by embedding similarity."""
        import time
        start_time = time.time()
        
        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)
            
            # Search for similar embeddings
            similar_entries = await self._search_similar_embeddings(query_embedding)
            
            if similar_entries:
                # Get best match
                best_entry, best_score = similar_entries[0]
                
                if best_score >= self.similarity_threshold:
                    # Update access stats
                    await self._update_access_stats(best_entry)
                    
                    query_time = (time.time() - start_time) * 1000
                    return CacheResult(
                        hit=True,
                        entry=best_entry,
                        similarity_score=best_score,
                        query_time_ms=query_time
                    )
            
            return CacheResult(hit=False, query_time_ms=(time.time() - start_time) * 1000)
            
        except Exception as e:
            self.logger.error(f"Semantic match lookup failed: {e}")
            return CacheResult(hit=False, query_time_ms=0)
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if not self.embedding_model:
            # Fallback to hash-based embedding
            hash_obj = hashlib.sha256(text.encode('utf-8'))
            hash_hex = hash_obj.hexdigest()
            # Convert to numeric vector
            embedding = [float(int(hash_hex[i:i+2], 16)) / 255.0 for i in range(0, min(len(hash_hex), 768), 2)]
            # Pad or truncate to standard size
            while len(embedding) < 384:
                embedding.append(0.0)
            return embedding[:384]
        
        # Use sentence transformer
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    async def _search_similar_embeddings(self, query_embedding: List[float]) -> List[Tuple[CacheEntry, float]]:
        """Search for similar embeddings in cache."""
        # This would use Redis Vector Search in production
        # For now, we'll implement a simple similarity search
        
        similar_entries = []
        
        try:
            # Get all cache entries (simplified - in production use vector index)
            all_keys = await self.redis_client.keys(f"{self.cache_key_prefix}:entry:*")
            
            for key in all_keys[:100]:  # Limit search for performance
                entry_data = await self.redis_client.hgetall(key)
                if entry_data:
                    entry = CacheEntry.from_dict(entry_data)
                    
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(query_embedding, entry.embedding)
                    
                    if similarity >= self.similarity_threshold:
                        similar_entries.append((entry, similarity))
            
            # Sort by similarity (descending)
            similar_entries.sort(key=lambda x: x[1], reverse=True)
            
            return similar_entries
            
        except Exception as e:
            self.logger.error(f"Similarity search failed: {e}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not NUMPY_AVAILABLE:
            # Fallback calculation
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = sum(a * a for a in vec1) ** 0.5
            magnitude2 = sum(b * b for b in vec2) ** 0.5
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
        
        # Use numpy for efficiency
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        magnitude1 = np.linalg.norm(v1)
        magnitude2 = np.linalg.norm(v2)
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def _store_cache_entry(self, entry: CacheEntry):
        """Store cache entry in Redis."""
        # Store full entry
        entry_key = f"{self.cache_key_prefix}:entry:{entry.cache_id}"
        entry_data = entry.to_dict()
        
        for field, value in entry_data.items():
            await self.redis_client.hset(entry_key, field, value)
        
        # Set TTL
        await self.redis_client.expire(entry_key, entry.ttl_seconds)
        
        # Store hash mapping
        hash_key = f"{self.cache_key_prefix}:hash:{entry.query_hash}"
        await self.redis_client.set(hash_key, entry.cache_id, ex=entry.ttl_seconds)
        
        # Store embedding mapping (for similarity search)
        embedding_key = f"{self.cache_key_prefix}:embedding:{entry.embedding_hash}"
        await self.redis_client.set(embedding_key, entry.cache_id, ex=entry.ttl_seconds)
    
    async def _get_cache_entry(self, cache_id: str) -> Optional[CacheEntry]:
        """Get cache entry by ID."""
        try:
            entry_key = f"{self.cache_key_prefix}:entry:{cache_id}"
            entry_data = await self.redis_client.hgetall(entry_key)
            
            if entry_data:
                return CacheEntry.from_dict(entry_data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get cache entry {cache_id}: {e}")
            return None
    
    async def _update_access_stats(self, entry: CacheEntry):
        """Update access statistics for entry."""
        try:
            entry_key = f"{self.cache_key_prefix}:entry:{entry.cache_id}"
            
            # Update access count and timestamp
            await self.redis_client.hincrby(entry_key, "access_count", 1)
            await self.redis_client.hset(entry_key, "accessed_at", datetime.now(timezone.utc).isoformat())
            
        except Exception as e:
            self.logger.error(f"Failed to update access stats: {e}")
    
    async def _update_cache_metadata(self):
        """Update cache metadata."""
        try:
            # Get current cache size
            cache_size = await self.redis_client.keys(f"{self.cache_key_prefix}:entry:*")
            
            # Update metadata
            await self.redis_client.hset(self.metadata_key, "cache_size", str(len(cache_size)))
            await self.redis_client.hset(self.metadata_key, "total_queries", str(self.total_queries))
            await self.redis_client.hset(self.metadata_key, "cache_hits", str(self.cache_hits))
            await self.redis_client.hset(self.metadata_key, "cache_misses", str(self.cache_misses))
            
        except Exception as e:
            self.logger.error(f"Failed to update cache metadata: {e}")
    
    async def _get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            metadata = await self.redis_client.hgetall(self.metadata_key)
            
            return {
                "cache_size": int(metadata.get("cache_size", 0)),
                "max_cache_size": self.max_cache_size,
                "total_queries": int(metadata.get("total_queries", 0)),
                "cache_hits": int(metadata.get("cache_hits", 0)),
                "cache_misses": int(metadata.get("cache_misses", 0)),
                "hit_rate": self.cache_hits / max(self.total_queries, 1),
                "default_ttl": self.default_ttl,
                "embedding_model": self.embedding_model_name.value
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get cache stats: {e}")
            return {}
    
    def _generate_hash(self, text: str) -> str:
        """Generate SHA-256 hash."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def _update_query_time(self, query_time: float):
        """Update average query time."""
        self.total_queries += 1
        self.avg_query_time_ms = (
            (self.avg_query_time_ms * (self.total_queries - 1) + query_time) /
            self.total_queries
        )
    
    async def clear(self):
        """Clear all cache entries."""
        try:
            # Get all cache keys
            all_keys = await self.redis_client.keys(f"{self.cache_key_prefix}:*")
            
            # Delete all keys
            if all_keys:
                await self.redis_client.delete(*all_keys)
            
            # Reset metadata
            await self._initialize_metadata()
            
            # Reset metrics
            self.cache_hits = 0
            self.cache_misses = 0
            self.cache_sets = 0
            self.total_queries = 0
            self.avg_query_time_ms = 0.0
            
            self.logger.info("Cache cleared")
            
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics."""
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_sets": self.cache_sets,
            "total_queries": self.total_queries,
            "hit_rate": self.cache_hits / max(self.total_queries, 1),
            "avg_query_time_ms": self.avg_query_time_ms,
            "embedding_model": self.embedding_model_name.value,
            "similarity_threshold": self.similarity_threshold,
            "default_ttl": self.default_ttl,
            "max_cache_size": self.max_cache_size
        }


class SemanticCache:
    """
    High-level semantic caching interface.
    
    Features:
    - Automatic cache management
    - Performance monitoring
    - Cost optimization tracking
    - Multiple caching strategies
    """
    
    def __init__(
        self,
        redis_client: RedisClient,
        embedding_model: EmbeddingModel = EmbeddingModel.MINILM,
        cache_ttl: int = 300,  # 5 minutes
        logger: Optional[logging.Logger] = None
    ):
        self.redis_client = redis_client
        self.cache_ttl = cache_ttl
        self.logger = logger or logging.getLogger("SemanticCache")
        
        # Initialize vector cache
        self.vector_cache = VectorCache(
            redis_client=redis_client,
            embedding_model=embedding_model,
            default_ttl=cache_ttl,
            logger=logger
        )
        
        # Cost tracking
        self.total_cost_saved = 0.0
        self.avg_llm_cost_per_query = 0.01  # Estimated cost
        self.cache_enabled = True
        
        self.logger.info("SemanticCache initialized")
    
    async def initialize(self) -> bool:
        """Initialize semantic cache."""
        return await self.vector_cache.initialize()
    
    async def get_cached_response(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        strategy: CacheStrategy = CacheStrategy.HYBRID
    ) -> Optional[str]:
        """
        Get cached response for query.
        
        Args:
            query: Query text
            context: Additional context
            strategy: Caching strategy
            
        Returns:
            Cached response or None
        """
        if not self.cache_enabled:
            return None
        
        try:
            # Include context in query for caching
            full_query = self._build_full_query(query, context)
            
            # Get from cache
            result = await self.vector_cache.get(full_query, strategy)
            
            if result.hit and result.entry:
                self.logger.debug(f"Cache hit for query: {query[:50]}...")
                
                # Update cost savings
                cost_saved = self.avg_llm_cost_per_query
                self.total_cost_saved += cost_saved
                
                return result.entry.response_text
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get cached response: {e}")
            return None
    
    async def cache_response(
        self,
        query: str,
        response: str,
        context: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Cache response for query.
        
        Args:
            query: Query text
            response: Response text
            context: Additional context
            ttl_seconds: TTL override
            
        Returns:
            Success status
        """
        if not self.cache_enabled:
            return False
        
        try:
            # Include context in query for caching
            full_query = self._build_full_query(query, context)
            
            # Cache the response
            cache_id = await self.vector_cache.set(
                query=full_query,
                response=response,
                ttl_seconds=ttl_seconds or self.cache_ttl,
                metadata={"original_query": query, "context": context}
            )
            
            self.logger.debug(f"Cached response: {cache_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cache response: {e}")
            return False
    
    def _build_full_query(self, query: str, context: Optional[Dict[str, Any]]) -> str:
        """Build full query including context."""
        if not context:
            return query
        
        # Serialize context and include in query
        context_str = json.dumps(context, sort_keys=True)
        return f"{query}|{context_str}"
    
    async def get_cache_analytics(self) -> Dict[str, Any]:
        """Get comprehensive cache analytics."""
        vector_metrics = self.vector_cache.get_metrics()
        
        return {
            "cache_metrics": vector_metrics,
            "cost_optimization": {
                "total_cost_saved": self.total_cost_saved,
                "avg_llm_cost_per_query": self.avg_llm_cost_per_query,
                "queries_saved_from_llm": vector_metrics["cache_hits"],
                "estimated_monthly_savings": self.total_cost_saved * 30  # Rough estimate
            },
            "performance": {
                "cache_enabled": self.cache_enabled,
                "cache_ttl": self.cache_ttl,
                "avg_query_time_ms": vector_metrics["avg_query_time_ms"],
                "hit_rate": vector_metrics["hit_rate"]
            }
        }
    
    async def clear_cache(self):
        """Clear all cached responses."""
        await self.vector_cache.clear()
        self.total_cost_saved = 0.0
        self.logger.info("Semantic cache cleared")
    
    def enable_cache(self):
        """Enable caching."""
        self.cache_enabled = True
        self.logger.info("Semantic cache enabled")
    
    def disable_cache(self):
        """Disable caching."""
        self.cache_enabled = False
        self.logger.info("Semantic cache disabled")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get semantic cache metrics."""
        vector_metrics = self.vector_cache.get_metrics()
        
        return {
            **vector_metrics,
            "cost_optimization": {
                "total_cost_saved": self.total_cost_saved,
                "queries_saved_from_llm": vector_metrics["cache_hits"]
            },
            "cache_enabled": self.cache_enabled
        }


# Global instances
_semantic_cache: Optional[SemanticCache] = None


def get_semantic_cache(redis_client: RedisClient) -> SemanticCache:
    """Get or create global semantic cache."""
    global _semantic_cache
    if _semantic_cache is None:
        _semantic_cache = SemanticCache(redis_client)
    return _semantic_cache
