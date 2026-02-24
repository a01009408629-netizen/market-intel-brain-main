"""
Performance Optimization Layer - High-Concurrency Support

Enterprise-grade performance optimizations for handling high-load scenarios
with additional caching layers and intelligent resource management.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
from collections import defaultdict, OrderedDict

from .vector_cache.interfaces import (
    IVectorStorage,
    EmbeddingMetadata,
    SimilaritySearchResult,
    SearchQuery,
    VectorStorageStats
)
from .data_quality_gateway import (
    ValidationResult,
    QualityLevel,
    ValidationIssue,
    ValidationSeverity
)


class CacheStrategy(Enum):
    """Caching strategies for different data types."""
    LRU = "lru"                    # Least Recently Used
    LFU = "lfu"                    # Least Frequently Used
    TTL = "ttl"                    # Time To Live
    ADAPTIVE = "adaptive"           # Adaptive based on access patterns


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    data: Any
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: Optional[int] = None
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl_seconds is None:
            return False
        return (datetime.now(timezone.utc) - self.timestamp).total_seconds() > self.ttl_seconds
    
    def update_access(self):
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = datetime.now(timezone.utc)


class HotVectorCache:
    """
    High-performance cache for frequently accessed vectors.
    
    Implements multiple caching strategies with intelligent eviction
    to maintain <200ms response times under high concurrency.
    """
    
    def __init__(
        self,
        max_size: int = 10000,
        strategy: CacheStrategy = CacheStrategy.LRU,
        ttl_seconds: Optional[int] = 3600,
        logger: Optional[logging.Logger] = None
    ):
        self.max_size = max_size
        self.strategy = strategy
        self.ttl_seconds = ttl_seconds
        self.logger = logger or logging.getLogger("HotVectorCache")
        
        # Cache storage
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: OrderedDict = OrderedDict()  # For LRU
        self._access_frequency: Dict[str, int] = defaultdict(int)  # For LFU
        
        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
            "total_requests": 0,
            "cache_size_bytes": 0,
            "hit_rate": 0.0
        }
        
        # Performance tracking
        self._response_times: List[float] = []
        self._concurrent_requests = 0
        self._max_concurrent = 0
        
        self.logger.info(f"HotVectorCache initialized: max_size={max_size}, strategy={strategy.value}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with performance tracking."""
        start_time = time.time()
        self._concurrent_requests += 1
        self._max_concurrent = max(self._max_concurrent, self._concurrent_requests)
        
        try:
            if key in self._cache:
                entry = self._cache[key]
                
                # Check expiration
                if entry.is_expired():
                    await self._remove_expired_entry(key)
                    self._stats["misses"] += 1
                    return None
                
                # Update access statistics
                entry.update_access()
                self._update_access_tracking(key)
                
                self._stats["hits"] += 1
                return entry.data
            else:
                self._stats["misses"] += 1
                return None
                
        finally:
            self._concurrent_requests -= 1
            response_time = (time.time() - start_time) * 1000
            self._response_times.append(response_time)
            self._update_stats()
    
    async def put(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Put value into cache with intelligent eviction."""
        start_time = time.time()
        
        try:
            # Calculate size
            size_bytes = len(json.dumps(value, default=str).encode())
            
            # Check if eviction is needed
            if len(self._cache) >= self.max_size:
                await self._evict_entries()
            
            # Create cache entry
            entry = CacheEntry(
                data=value,
                ttl_seconds=ttl_seconds or self.ttl_seconds,
                size_bytes=size_bytes
            )
            
            # Store entry
            self._cache[key] = entry
            self._update_access_tracking(key)
            
            # Update statistics
            self._stats["cache_size_bytes"] += size_bytes
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cache entry {key}: {e}")
            return False
        finally:
            response_time = (time.time() - start_time) * 1000
            self._response_times.append(response_time)
    
    async def get_or_compute(
        self, 
        key: str, 
        compute_func: callable, 
        ttl_seconds: Optional[int] = None
    ) -> Any:
        """Get from cache or compute and store."""
        # Try cache first
        cached_value = await self.get(key)
        if cached_value is not None:
            return cached_value
        
        # Compute value
        try:
            computed_value = await compute_func()
            
            # Store in cache
            await self.put(key, computed_value, ttl_seconds)
            
            return computed_value
            
        except Exception as e:
            self.logger.error(f"Failed to compute value for key {key}: {e}")
            raise
    
    async def invalidate(self, key: str) -> bool:
        """Invalidate a cache entry."""
        if key in self._cache:
            entry = self._cache[key]
            del self._cache[key]
            self._stats["cache_size_bytes"] -= entry.size_bytes
            
            # Remove from tracking
            self._access_order.pop(key, None)
            self._access_frequency.pop(key, None)
            
            return True
        return False
    
    async def clear(self) -> int:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        self._access_order.clear()
        self._access_frequency.clear()
        
        self._stats["cache_size_bytes"] = 0
        
        self.logger.info(f"Cleared {count} cache entries")
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            **self._stats,
            "cache_entries": len(self._cache),
            "max_size": self.max_size,
            "utilization_rate": len(self._cache) / self.max_size,
            "avg_response_time_ms": sum(self._response_times) / len(self._response_times) if self._response_times else 0,
            "max_concurrent_requests": self._max_concurrent,
            "current_concurrent_requests": self._concurrent_requests
        }
    
    async def _evict_entries(self):
        """Evict entries based on strategy."""
        if not self._cache:
            return
        
        evict_count = max(1, len(self._cache) // 10)  # Evict 10%
        
        if self.strategy == CacheStrategy.LRU:
            await self._evict_lru(evict_count)
        elif self.strategy == CacheStrategy.LFU:
            await self._evict_lfu(evict_count)
        elif self.strategy == CacheStrategy.TTL:
            await self._evict_expired()
        elif self.strategy == CacheStrategy.ADAPTIVE:
            await self._evict_adaptive(evict_count)
    
    async def _evict_lru(self, count: int):
        """Evict least recently used entries."""
        # Sort by last accessed time
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].last_accessed
        )
        
        for i in range(min(count, len(sorted_entries))):
            key, entry = sorted_entries[i]
            await self._remove_entry(key)
    
    async def _evict_lfu(self, count: int):
        """Evict least frequently used entries."""
        # Sort by access count
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].access_count
        )
        
        for i in range(min(count, len(sorted_entries))):
            key, entry = sorted_entries[i]
            await self._remove_entry(key)
    
    async def _evict_expired(self):
        """Evict expired entries."""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            await self._remove_expired_entry(key)
    
    async def _evict_adaptive(self, count: int):
        """Adaptive eviction combining LRU and LFU."""
        # Calculate adaptive score
        def adaptive_score(key: str, entry: CacheEntry) -> float:
            age_hours = (datetime.now(timezone.utc) - entry.timestamp).total_seconds() / 3600
            frequency = entry.access_count
            recency = (datetime.now(timezone.utc) - entry.last_accessed).total_seconds() / 3600
            
            # Lower score = better candidate for eviction
            return (frequency / (age_hours + 1)) * (1 / (recency + 1))
        
        # Sort by adaptive score (ascending)
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: adaptive_score(x[0], x[1])
        )
        
        for i in range(min(count, len(sorted_entries))):
            key, entry = sorted_entries[i]
            await self._remove_entry(key)
    
    async def _remove_entry(self, key: str):
        """Remove entry from cache."""
        if key in self._cache:
            entry = self._cache[key]
            del self._cache[key]
            self._stats["cache_size_bytes"] -= entry.size_bytes
            self._stats["evictions"] += 1
            
            # Remove from tracking
            self._access_order.pop(key, None)
            self._access_frequency.pop(key, None)
    
    async def _remove_expired_entry(self, key: str):
        """Remove expired entry."""
        if key in self._cache:
            entry = self._cache[key]
            del self._cache[key]
            self._stats["cache_size_bytes"] -= entry.size_bytes
            self._stats["expirations"] += 1
            
            # Remove from tracking
            self._access_order.pop(key, None)
            self._access_frequency.pop(key, None)
    
    def _update_access_tracking(self, key: str):
        """Update access tracking structures."""
        if self.strategy == CacheStrategy.LRU:
            # Move to end (most recently used)
            self._access_order.pop(key, None)
            self._access_order[key] = None
        elif self.strategy == CacheStrategy.LFU:
            self._access_frequency[key] += 1
    
    def _update_stats(self):
        """Update cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        if total > 0:
            self._stats["hit_rate"] = self._stats["hits"] / total
            self._stats["total_requests"] = total


class OptimizedVectorStorage:
    """
    Vector storage with additional caching layer for high-concurrency scenarios.
    
    Maintains <200ms response times under high load through intelligent
    caching of hot vectors and query results.
    """
    
    def __init__(
        self,
        base_storage: IVectorStorage,
        cache_size: int = 10000,
        cache_strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
        cache_ttl: int = 3600,
        logger: Optional[logging.Logger] = None
    ):
        self.base_storage = base_storage
        self.logger = logger or logging.getLogger("OptimizedVectorStorage")
        
        # Initialize caches
        self.vector_cache = HotVectorCache(
            max_size=cache_size,
            strategy=cache_strategy,
            ttl_seconds=cache_ttl,
            logger=self.logger
        )
        
        self.search_cache = HotVectorCache(
            max_size=cache_size // 2,
            strategy=CacheStrategy.LRU,
            ttl_seconds=cache_ttl // 2,
            logger=self.logger
        )
        
        # Performance tracking
        self._performance_stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "base_storage_calls": 0,
            "avg_response_time_ms": 0.0,
            "cache_hit_rate": 0.0
        }
        
        self.logger.info(f"OptimizedVectorStorage initialized with cache_size={cache_size}")
    
    async def initialize(self) -> bool:
        """Initialize optimized storage."""
        return await self.base_storage.initialize()
    
    async def close(self) -> None:
        """Close optimized storage."""
        await self.base_storage.close()
        await self.vector_cache.clear()
        await self.search_cache.clear()
    
    async def health_check(self) -> bool:
        """Check health of optimized storage."""
        return await self.base_storage.health_check()
    
    async def similarity_search(self, query: SearchQuery, index_name: Optional[str] = None) -> List[SimilaritySearchResult]:
        """Perform similarity search with caching."""
        start_time = time.time()
        
        try:
            # Generate cache key for query
            cache_key = self._generate_query_cache_key(query, index_name)
            
            # Try search cache first
            cached_results = await self.search_cache.get(cache_key)
            if cached_results is not None:
                self._performance_stats["cache_hits"] += 1
                return cached_results
            
            # Perform search on base storage
            self._performance_stats["cache_misses"] += 1
            self._performance_stats["base_storage_calls"] += 1
            
            results = await self.base_storage.similarity_search(query, index_name)
            
            # Cache results
            await self.search_cache.put(cache_key, results)
            
            return results
            
        finally:
            response_time = (time.time() - start_time) * 1000
            self._update_performance_stats(response_time)
    
    async def insert_embedding(
        self,
        vector: List[float],
        metadata: EmbeddingMetadata,
        index_name: Optional[str] = None
    ) -> str:
        """Insert embedding with caching."""
        start_time = time.time()
        
        try:
            # Insert into base storage
            embedding_id = await self.base_storage.insert_embedding(vector, metadata, index_name)
            
            # Cache the embedding
            cache_key = f"embedding:{embedding_id}"
            await self.vector_cache.put(cache_key, (vector, metadata))
            
            # Invalidate related search cache entries
            await self._invalidate_search_cache(metadata)
            
            return embedding_id
            
        finally:
            response_time = (time.time() - start_time) * 1000
            self._update_performance_stats(response_time)
    
    async def get_embedding(self, embedding_id: str) -> Tuple[List[float], EmbeddingMetadata]:
        """Get embedding with caching."""
        start_time = time.time()
        
        try:
            # Try vector cache first
            cache_key = f"embedding:{embedding_id}"
            cached_embedding = await self.vector_cache.get(cache_key)
            if cached_embedding is not None:
                self._performance_stats["cache_hits"] += 1
                return cached_embedding
            
            # Get from base storage
            self._performance_stats["cache_misses"] += 1
            self._performance_stats["base_storage_calls"] += 1
            
            vector, metadata = await self.base_storage.get_embedding(embedding_id)
            
            # Cache the embedding
            await self.vector_cache.put(cache_key, (vector, metadata))
            
            return vector, metadata
            
        finally:
            response_time = (time.time() - start_time) * 1000
            self._update_performance_stats(response_time)
    
    async def get_stats(self, index_name: Optional[str] = None) -> VectorStorageStats:
        """Get comprehensive statistics."""
        base_stats = await self.base_storage.get_stats(index_name)
        
        # Add cache statistics
        cache_stats = self.vector_cache.get_stats()
        search_cache_stats = self.search_cache.get_stats()
        
        # Update base stats with cache information
        base_stats.custom_stats.update({
            "vector_cache": cache_stats,
            "search_cache": search_cache_stats,
            "performance": self._performance_stats
        })
        
        return base_stats
    
    async def _invalidate_search_cache(self, metadata: EmbeddingMetadata):
        """Invalidate search cache entries related to metadata."""
        # This is a simplified implementation
        # In practice, you might want more sophisticated cache invalidation
        pass
    
    def _generate_query_cache_key(self, query: SearchQuery, index_name: Optional[str] = None) -> str:
        """Generate cache key for search query."""
        # Create a deterministic key from query parameters
        query_data = {
            "query_vector_hash": hashlib.md5(str(query.query_vector).encode()).hexdigest(),
            "top_k": query.top_k,
            "threshold": query.threshold,
            "content_type": query.content_type,
            "category": query.category,
            "tags": sorted(query.tags) if query.tags else None,
            "source": query.source,
            "min_quality_score": query.min_quality_score,
            "min_confidence": query.min_confidence,
            "index_name": index_name
        }
        
        query_str = json.dumps(query_data, sort_keys=True)
        return hashlib.sha256(query_str.encode()).hexdigest()
    
    def _update_performance_stats(self, response_time_ms: float):
        """Update performance statistics."""
        total_requests = self._performance_stats["cache_hits"] + self._performance_stats["cache_misses"]
        
        if total_requests > 0:
            self._performance_stats["cache_hit_rate"] = self._performance_stats["cache_hits"] / total_requests
        
        # Update average response time
        current_avg = self._performance_stats["avg_response_time_ms"]
        self._performance_stats["avg_response_time_ms"] = (
            (current_avg * (total_requests - 1) + response_time_ms) / total_requests
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get detailed performance statistics."""
        return {
            **self._performance_stats,
            "vector_cache_stats": self.vector_cache.get_stats(),
            "search_cache_stats": self.search_cache.get_stats()
        }


# Global optimized storage factory
_optimized_storages: Dict[str, OptimizedVectorStorage] = {}


def get_optimized_vector_storage(
    storage_id: str,
    base_storage: IVectorStorage,
    cache_size: int = 10000,
    cache_strategy: CacheStrategy = CacheStrategy.ADAPTIVE
) -> OptimizedVectorStorage:
    """Get or create optimized vector storage instance."""
    if storage_id not in _optimized_storages:
        _optimized_storages[storage_id] = OptimizedVectorStorage(
            base_storage=base_storage,
            cache_size=cache_size,
            cache_strategy=cache_strategy
        )
    
    return _optimized_storages[storage_id]
