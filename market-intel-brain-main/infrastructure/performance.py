"""
Enterprise Performance & Scalability System
Load balancing, Redis clustering, connection pooling, and caching strategies
"""

import asyncio
import logging
import time
import json
import hashlib
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from functools import wraps
import aioredis
from aioredis import ConnectionPool
import aiohttp
import aiofiles
from pathlib import Path
import pickle
import zlib
import os

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Configuration for caching."""
    ttl_seconds: int = 3600  # 1 hour default
    max_size: int = 1000
    compression: bool = True
    serialization: str = "json"  # json, pickle


@dataclass
class LoadBalancerConfig:
    """Configuration for load balancing."""
    strategy: str = "round_robin"  # round_robin, least_connections, weighted
    health_check_interval: int = 30
    max_retries: int = 3
    timeout: int = 30


@dataclass
class BackendServer:
    """Backend server configuration."""
    id: str
    host: str
    port: int
    weight: int = 1
    healthy: bool = True
    last_health_check: Optional[datetime] = None
    active_connections: int = 0


class EnterpriseCache:
    """Enterprise-grade caching with Redis clustering and local fallback."""
    
    def __init__(self, redis_pool: ConnectionPool, local_cache_size: int = 1000):
        self.redis_pool = redis_pool
        self.redis_client = None
        self.local_cache = {}
        self.local_cache_size = local_cache_size
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "redis_hits": 0,
            "local_hits": 0,
            "errors": 0
        }
    
    async def initialize(self):
        """Initialize cache system."""
        try:
            self.redis_client = aioredis.Redis(connection_pool=self.redis_pool)
            await self.redis_client.ping()
            logger.info("✅ Enterprise Cache initialized")
        except Exception as e:
            logger.error(f"❌ Cache initialization failed: {e}")
            raise
    
    def _generate_cache_key(self, key: str, namespace: str = "default") -> str:
        """Generate cache key with namespace."""
        return f"{namespace}:{hashlib.md5(key.encode()).hexdigest()}"
    
    def _serialize_value(self, value: Any, compression: bool = True) -> bytes:
        """Serialize value for storage."""
        try:
            data = json.dumps(value, default=str).encode('utf-8')
            if compression:
                data = zlib.compress(data)
            return data
        except Exception as e:
            logger.error(f"Serialization failed: {e}")
            raise
    
    def _deserialize_value(self, data: bytes, compression: bool = True) -> Any:
        """Deserialize value from storage."""
        try:
            if compression:
                data = zlib.decompress(data)
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            logger.error(f"Deserialization failed: {e}")
            raise
    
    async def get(self, key: str, namespace: str = "default", config: CacheConfig = None) -> Optional[Any]:
        """Get value from cache (local first, then Redis)."""
        cache_key = self._generate_cache_key(key, namespace)
        config = config or CacheConfig()
        
        try:
            # Check local cache first
            if cache_key in self.local_cache:
                item = self.local_cache[cache_key]
                if item["expires_at"] > datetime.now(timezone.utc):
                    self.cache_stats["hits"] += 1
                    self.cache_stats["local_hits"] += 1
                    return item["value"]
                else:
                    del self.local_cache[cache_key]
            
            # Check Redis cache
            if self.redis_client:
                data = await self.redis_client.get(cache_key)
                if data:
                    value = self._deserialize_value(data, config.compression)
                    
                    # Store in local cache
                    self._store_local(cache_key, value, config.ttl_seconds)
                    
                    self.cache_stats["hits"] += 1
                    self.cache_stats["redis_hits"] += 1
                    return value
            
            self.cache_stats["misses"] += 1
            return None
            
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, namespace: str = "default", config: CacheConfig = None):
        """Set value in cache (both local and Redis)."""
        cache_key = self._generate_cache_key(key, namespace)
        config = config or CacheConfig()
        
        try:
            # Store in local cache
            self._store_local(cache_key, value, config.ttl_seconds)
            
            # Store in Redis
            if self.redis_client:
                data = self._serialize_value(value, config.compression)
                await self.redis_client.setex(cache_key, config.ttl_seconds, data)
            
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.error(f"Cache set error: {e}")
    
    def _store_local(self, cache_key: str, value: Any, ttl_seconds: int):
        """Store value in local cache with LRU eviction."""
        # Remove oldest item if cache is full
        if len(self.local_cache) >= self.local_cache_size:
            oldest_key = min(self.local_cache.keys(), 
                           key=lambda k: self.local_cache[k]["created_at"])
            del self.local_cache[oldest_key]
        
        self.local_cache[cache_key] = {
            "value": value,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        }
    
    async def delete(self, key: str, namespace: str = "default"):
        """Delete value from cache."""
        cache_key = self._generate_cache_key(key, namespace)
        
        try:
            # Remove from local cache
            if cache_key in self.local_cache:
                del self.local_cache[cache_key]
            
            # Remove from Redis
            if self.redis_client:
                await self.redis_client.delete(cache_key)
                
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.error(f"Cache delete error: {e}")
    
    async def clear_namespace(self, namespace: str = "default"):
        """Clear all values in namespace."""
        try:
            # Clear local cache
            keys_to_remove = [k for k in self.local_cache.keys() if k.startswith(f"{namespace}:")]
            for key in keys_to_remove:
                del self.local_cache[key]
            
            # Clear Redis namespace
            if self.redis_client:
                pattern = f"{namespace}:*"
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                    
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.error(f"Cache clear error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.cache_stats,
            "hit_rate_percent": round(hit_rate, 2),
            "local_cache_size": len(self.local_cache)
        }


class EnterpriseLoadBalancer:
    """Enterprise load balancer with multiple strategies."""
    
    def __init__(self, config: LoadBalancerConfig = None):
        self.config = config or LoadBalancerConfig()
        self.backends: List[BackendServer] = []
        self.current_index = 0
        self.health_check_task = None
        self.stats = {
            "total_requests": 0,
            "failed_requests": 0,
            "backend_requests": {}
        }
    
    def add_backend(self, backend: BackendServer):
        """Add backend server."""
        self.backends.append(backend)
        self.stats["backend_requests"][backend.id] = 0
        logger.info(f"Added backend: {backend.id} ({backend.host}:{backend.port})")
    
    def remove_backend(self, backend_id: str):
        """Remove backend server."""
        self.backends = [b for b in self.backends if b.id != backend_id]
        if backend_id in self.stats["backend_requests"]:
            del self.stats["backend_requests"][backend_id]
        logger.info(f"Removed backend: {backend_id}")
    
    def get_healthy_backends(self) -> List[BackendServer]:
        """Get list of healthy backends."""
        return [b for b in self.backends if b.healthy]
    
    def select_backend(self) -> Optional[BackendServer]:
        """Select backend based on strategy."""
        healthy_backends = self.get_healthy_backends()
        
        if not healthy_backends:
            logger.warning("No healthy backends available")
            return None
        
        if self.config.strategy == "round_robin":
            backend = healthy_backends[self.current_index % len(healthy_backends)]
            self.current_index += 1
            
        elif self.config.strategy == "least_connections":
            backend = min(healthy_backends, key=lambda b: b.active_connections)
            
        elif self.config.strategy == "weighted":
            # Weighted round robin
            total_weight = sum(b.weight for b in healthy_backends)
            if total_weight == 0:
                return healthy_backends[0]
            
            import random
            rand = random.uniform(0, total_weight)
            current_weight = 0
            for backend in healthy_backends:
                current_weight += backend.weight
                if rand <= current_weight:
                    break
            backend = backend
        else:
            backend = healthy_backends[0]
        
        backend.active_connections += 1
        self.stats["backend_requests"][backend.id] += 1
        
        return backend
    
    def release_backend(self, backend: BackendServer):
        """Release backend connection."""
        if backend.active_connections > 0:
            backend.active_connections -= 1
    
    async def health_check(self):
        """Perform health check on all backends."""
        for backend in self.backends:
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                    url = f"http://{backend.host}:{backend.port}/health"
                    async with session.get(url) as response:
                        if response.status == 200:
                            backend.healthy = True
                            backend.last_health_check = datetime.now(timezone.utc)
                        else:
                            backend.healthy = False
            except Exception as e:
                backend.healthy = False
                logger.warning(f"Health check failed for {backend.id}: {e}")
    
    async def start_health_checks(self):
        """Start periodic health checks."""
        if self.health_check_task:
            return
        
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Load balancer health checks started")
    
    async def stop_health_checks(self):
        """Stop health checks."""
        if self.health_check_task:
            self.health_check_task.cancel()
            self.health_check_task = None
        logger.info("Load balancer health checks stopped")
    
    async def _health_check_loop(self):
        """Health check loop."""
        while True:
            try:
                await self.health_check()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(self.config.health_check_interval)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get load balancer statistics."""
        return {
            **self.stats,
            "total_backends": len(self.backends),
            "healthy_backends": len(self.get_healthy_backends()),
            "strategy": self.config.strategy,
            "backends": [
                {
                    "id": b.id,
                    "host": b.host,
                    "port": b.port,
                    "healthy": b.healthy,
                    "active_connections": b.active_connections,
                    "weight": b.weight
                }
                for b in self.backends
            ]
        }


class ConnectionPoolManager:
    """Enterprise connection pool manager."""
    
    def __init__(self):
        self.pools = {}
        self.pool_configs = {}
    
    async def create_pool(self, name: str, factory: Callable, **kwargs):
        """Create connection pool."""
        try:
            pool = await factory(**kwargs)
            self.pools[name] = pool
            self.pool_configs[name] = kwargs
            logger.info(f"Created connection pool: {name}")
            return pool
        except Exception as e:
            logger.error(f"Failed to create pool {name}: {e}")
            raise
    
    async def get_pool(self, name: str):
        """Get connection pool."""
        if name not in self.pools:
            raise ValueError(f"Pool {name} not found")
        return self.pools[name]
    
    async def close_pool(self, name: str):
        """Close connection pool."""
        if name in self.pools:
            pool = self.pools[name]
            if hasattr(pool, 'close'):
                await pool.close()
            elif hasattr(pool, 'disconnect'):
                await pool.disconnect()
            del self.pools[name]
            del self.pool_configs[name]
            logger.info(f"Closed connection pool: {name}")
    
    async def close_all(self):
        """Close all connection pools."""
        for name in list(self.pools.keys()):
            await self.close_pool(name)
        logger.info("All connection pools closed")


def cached(ttl_seconds: int = 3600, namespace: str = "default", key_func: Callable = None):
    """Decorator for caching function results."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cache = getattr(wrapper, '_cache', None)
            if cache:
                cached_result = await cache.get(cache_key, namespace)
                if cached_result is not None:
                    return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            if cache:
                config = CacheConfig(ttl_seconds=ttl_seconds)
                await cache.set(cache_key, result, namespace, config)
            
            return result
        
        return wrapper
    return decorator


# Global instances
enterprise_cache = None
enterprise_load_balancer = None
connection_pool_manager = ConnectionPoolManager()


async def initialize_performance(redis_pool: ConnectionPool):
    """Initialize performance components."""
    global enterprise_cache, enterprise_load_balancer
    
    try:
        # Initialize cache
        enterprise_cache = EnterpriseCache(redis_pool)
        await enterprise_cache.initialize()
        
        # Initialize load balancer
        enterprise_load_balancer = EnterpriseLoadBalancer()
        await enterprise_load_balancer.start_health_checks()
        
        logger.info("✅ Enterprise Performance system initialized")
        
    except Exception as e:
        logger.error(f"❌ Performance system initialization failed: {e}")
        raise


async def cleanup_performance():
    """Cleanup performance resources."""
    try:
        if enterprise_load_balancer:
            await enterprise_load_balancer.stop_health_checks()
        
        await connection_pool_manager.close_all()
        
        logger.info("✅ Enterprise Performance system cleaned up")
        
    except Exception as e:
        logger.error(f"❌ Performance system cleanup failed: {e}")
