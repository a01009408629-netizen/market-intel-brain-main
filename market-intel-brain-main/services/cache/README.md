# Tiered Cache Manager with SWR (Stale-While-Revalidate)

A sophisticated two-tier caching system designed for high-performance applications with intelligent cache management and background refresh capabilities.

## Features

### 🚀 **Two-Tier Architecture**
- **L1 (Memory)**: `cachetools.TTLCache` for instant responses
- **L2 (Redis)**: Shared cache across workers/servers using `redis.asyncio`

### ⚡ **SWR (Stale-While-Revalidate)**
- Serve stale data immediately for fast responses
- Background refresh using `asyncio.create_task`
- Configurable stale window for optimal freshness

### 🛠 **Advanced Features**
- Async-first design with proper task management
- Comprehensive statistics and health monitoring
- Namespace isolation for different data types
- Background refresh coordination to prevent thundering herd
- Easy integration with decorators

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### Basic Usage

```python
import asyncio
from tiered_cache_manager import TieredCacheManager, CacheConfig

async def main():
    # Configure cache
    config = CacheConfig(
        l1_max_size=1000,
        l1_ttl=300,      # 5 minutes
        l2_ttl=3600,     # 1 hour
        stale_while_revalidate_window=60,  # 1 minute stale window
        enable_swr=True,
        redis_url="redis://localhost:6379"
    )
    
    # Create cache manager
    cache = TieredCacheManager(config)
    
    # Set value
    await cache.set("user:123", {"name": "John", "age": 30})
    
    # Get value (with SWR logic)
    data = await cache.get("user:123")
    print(data)  # {"name": "John", "age": 30}
    
    # Clean up
    await cache.close()

asyncio.run(main())
```

### SWR with Background Refresh

```python
async def get_user_data(user_id: int):
    async def fetch_fresh_data():
        # Simulate API call
        await asyncio.sleep(1)
        return {"user_id": user_id, "name": f"User {user_id}"}
    
    # Get from cache, trigger background refresh if stale
    cached_data = await cache.get(
        f"user:{user_id}",
        refresh_func=fetch_fresh_data
    )
    
    return cached_data
```

### Using the Cached Decorator

```python
from tiered_cache_manager import cached

@cached(
    key_template="product:{product_id}",
    ttl=300,  # 5 minutes
    namespace="products"
)
async def get_product_details(product_id: int):
    # Simulate database query
    await asyncio.sleep(0.5)
    return {"id": product_id, "name": f"Product {product_id}"}
```

## Configuration

### CacheConfig Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `l1_max_size` | int | 1000 | Maximum items in L1 cache |
| `l1_ttl` | int | 300 | L1 cache TTL in seconds |
| `l2_ttl` | int | 3600 | L2 cache TTL in seconds |
| `stale_while_revalidate_window` | int | 60 | Stale window in seconds |
| `enable_swr` | bool | True | Enable SWR logic |
| `background_refresh` | bool | True | Enable background refresh |
| `redis_url` | str | "redis://localhost:6379" | Redis connection URL |

## SWR (Stale-While-Revalidate) Behavior

The cache implements SWR logic as follows:

1. **Fresh Data** (timestamp < stale_at): Return immediately
2. **Stale Data** (stale_at ≤ timestamp < expired): 
   - Return stale data immediately for fast response
   - Trigger background refresh using `asyncio.create_task`
3. **Expired Data** (timestamp ≥ expired): Cache miss, fetch fresh data

### Timeline Example

```
Time: 0s        - Data cached (fresh)
Time: 0-240s    - Fresh data returned instantly
Time: 240-300s  - Stale data returned + background refresh
Time: 300s+     - Data expired, cache miss
```

## Advanced Usage

### Namespace Isolation

```python
# User data
await cache.set("user:123", user_data, namespace="users")

# Product data
await cache.set("product:456", product_data, namespace="products")

# Clear only user cache
await cache.clear_namespace("users")
```

### Statistics and Monitoring

```python
# Get comprehensive statistics
stats = cache.get_stats()
print(f"Hit rate: {stats['overall_stats']['hit_rate']:.2%}")
print(f"L1 utilization: {stats['l1_stats']['utilization']:.2%}")

# Health check
health = await cache.health_check()
print(f"Cache healthy: {health['healthy']}")
```

### Manual Cache Management

```python
# Invalidate specific key
await cache.invalidate("user:123", namespace="users")

# Clear entire namespace
await cache.clear_namespace("users")

# Clear all cache
await cache.clear_all()
```

## Real-World Examples

### API Response Caching

```python
class APIClient:
    def __init__(self):
        self.cache = TieredCacheManager()
    
    async def get_user_profile(self, user_id: int):
        async def fetch_profile():
            # Actual API call
            response = await self.api.get(f"/users/{user_id}")
            return response.json()
        
        return await self.cache.get(
            f"profile:{user_id}",
            namespace="api",
            refresh_func=fetch_profile
        )
```

### Database Query Caching

```python
@cached(
    key_template="query:{table}:{filters_hash}",
    ttl=600,  # 10 minutes
    namespace="database"
)
async def execute_query(table: str, filters: Dict):
    # Database query logic
    result = await db.query(table, **filters)
    return result
```

## Performance Considerations

### L1 Cache (Memory)
- ✅ Instant access (microseconds)
- ✅ No network latency
- ❌ Limited by memory
- ❌ Not shared across processes

### L2 Cache (Redis)
- ✅ Shared across workers/servers
- ✅ Persistent across restarts
- ❌ Network latency (milliseconds)
- ❌ Requires Redis infrastructure

### SWR Benefits
- ✅ Always-fast responses (serve stale data)
- ✅ Background updates don't block requests
- ✅ Reduces cache stampede effects
- ✅ Improves user experience

## Monitoring and Debugging

### Logging

The cache manager provides detailed logging at different levels:

```python
import logging

# Enable debug logging
logging.getLogger("TieredCacheManager").setLevel(logging.DEBUG)
```

### Statistics

Monitor cache performance:

```python
stats = cache.get_stats()
# {
#     'l1_stats': {'hits': 150, 'misses': 50, 'utilization': 0.15},
#     'l2_stats': {'hits': 30, 'misses': 20},
#     'swr_stats': {'stale_hits': 25, 'background_refreshes': 25},
#     'overall_stats': {'hit_rate': 0.72, 'total_requests': 200}
# }
```

## Best Practices

### 1. Choose Appropriate TTLs
- **L1 TTL**: Shorter (2-5 minutes) for memory efficiency
- **L2 TTL**: Longer (30-60 minutes) for persistence
- **Stale Window**: 10-25% of TTL for optimal freshness

### 2. Use Namespaces
- Separate different data types
- Enable selective cache clearing
- Improve organization and debugging

### 3. Monitor Hit Rates
- Target >70% overall hit rate
- Adjust TTLs based on access patterns
- Monitor L1 utilization

### 4. Handle Redis Failures
- Cache gracefully degrades to L1-only
- Implement Redis connection retry logic
- Monitor Redis health separately

## Testing

Run the example demonstration:

```bash
python example_usage.py
```

Run tests:

```bash
pytest -v
```

## Dependencies

- `cachetools>=5.0.0` - L1 cache implementation
- `redis[asyncio]>=4.5.0` - L2 cache with async support
- `msgpack>=1.0.0` - Optional fast serialization

## License

This cache system is part of the Market Intel Brain project.
