"""
Example usage of TieredCacheManager with SWR (Stale-While-Revalidate)

This file demonstrates how to use the advanced tiered cache system
with real-world scenarios including API calls, database queries, and
background refresh functionality.
"""

import asyncio
import logging
import time
from typing import Dict, Any

from tiered_cache_manager import TieredCacheManager, CacheConfig, cached

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataService:
    """Example service demonstrating cache usage"""
    
    def __init__(self):
        # Configure cache with custom settings
        cache_config = CacheConfig(
            l1_max_size=500,
            l1_ttl=120,  # 2 minutes for L1
            l2_ttl=1800,  # 30 minutes for L2
            stale_while_revalidate_window=30,  # 30 seconds stale window
            enable_swr=True,
            background_refresh=True,
            redis_url="redis://localhost:6379"
        )
        
        self.cache_manager = TieredCacheManager(cache_config, logger)
    
    async def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """
        Get user data with SWR caching.
        If data is stale, returns cached data immediately while
        refreshing in background.
        """
        async def fetch_fresh_user_data():
            """Simulate API call to fetch fresh user data"""
            logger.info(f"Fetching fresh user data for user {user_id}")
            await asyncio.sleep(1)  # Simulate API latency
            return {
                "user_id": user_id,
                "name": f"User {user_id}",
                "email": f"user{user_id}@example.com",
                "last_updated": time.time(),
                "data": {"preferences": {"theme": "dark"}}
            }
        
        # Try to get from cache first
        cached_data = await self.cache_manager.get(
            f"user:{user_id}",
            namespace="users",
            refresh_func=fetch_fresh_user_data
        )
        
        if cached_data:
            return cached_data
        
        # Cache miss - fetch fresh data
        fresh_data = await fetch_fresh_user_data()
        await self.cache_manager.set(
            f"user:{user_id}",
            fresh_data,
            ttl=600,  # 10 minutes
            namespace="users"
        )
        
        return fresh_data
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get market data with aggressive caching.
        Market data changes frequently, so we use shorter TTL.
        """
        async def fetch_market_data():
            """Simulate market data API call"""
            logger.info(f"Fetching fresh market data for {symbol}")
            await asyncio.sleep(0.5)  # Simulate API latency
            return {
                "symbol": symbol,
                "price": 100.0 + (hash(symbol) % 50),
                "volume": 1000000 + (hash(symbol) % 500000),
                "timestamp": time.time()
            }
        
        # Use shorter TTL for market data
        cached_data = await self.cache_manager.get(
            f"market:{symbol}",
            namespace="market",
            refresh_func=fetch_market_data
        )
        
        if cached_data:
            return cached_data
        
        fresh_data = await fetch_market_data()
        await self.cache_manager.set(
            f"market:{symbol}",
            fresh_data,
            ttl=60,  # 1 minute for market data
            namespace="market"
        )
        
        return fresh_data


# Example using the cached decorator
@cached(
    key_template="product:{product_id}",
    ttl=300,  # 5 minutes
    namespace="products"
)
async def get_product_details(product_id: int) -> Dict[str, Any]:
    """Example function with caching decorator"""
    logger.info(f"Fetching product details for {product_id}")
    await asyncio.sleep(0.8)  # Simulate database query
    return {
        "product_id": product_id,
        "name": f"Product {product_id}",
        "price": 29.99 + product_id,
        "stock": 100 - product_id,
        "description": f"Description for product {product_id}"
    }


async def demonstrate_swr_behavior():
    """Demonstrate SWR (Stale-While-Revalidate) behavior"""
    print("\n=== SWR Behavior Demonstration ===")
    
    service = DataService()
    
    # First request - cache miss
    print("\n1. First request (cache miss):")
    start_time = time.time()
    user_data = await service.get_user_data(123)
    elapsed = time.time() - start_time
    print(f"   Response time: {elapsed:.2f}s")
    print(f"   Data: {user_data['name']}")
    
    # Second request - cache hit
    print("\n2. Second request (L1 cache hit):")
    start_time = time.time()
    user_data = await service.get_user_data(123)
    elapsed = time.time() - start_time
    print(f"   Response time: {elapsed:.2f}s")
    print(f"   Data: {user_data['name']}")
    
    # Wait for data to become stale but not expired
    print("\n3. Waiting for data to become stale...")
    await asyncio.sleep(35)  # Wait past stale window (30s)
    
    # Third request - stale data served, background refresh triggered
    print("\n4. Third request (stale data served, background refresh):")
    start_time = time.time()
    user_data = await service.get_user_data(123)
    elapsed = time.time() - start_time
    print(f"   Response time: {elapsed:.2f}s (should be fast - stale data)")
    print(f"   Data: {user_data['name']}")
    
    # Wait a bit for background refresh to complete
    await asyncio.sleep(2)
    
    # Fourth request - fresh data from cache
    print("\n5. Fourth request (fresh data after background refresh):")
    start_time = time.time()
    user_data = await service.get_user_data(123)
    elapsed = time.time() - start_time
    print(f"   Response time: {elapsed:.2f}s")
    print(f"   Data timestamp: {user_data['last_updated']}")


async def demonstrate_concurrent_access():
    """Demonstrate concurrent access and background refresh coordination"""
    print("\n=== Concurrent Access Demonstration ===")
    
    service = DataService()
    
    async def make_request(request_id: int):
        """Simulate multiple concurrent requests"""
        start_time = time.time()
        data = await service.get_user_data(456)
        elapsed = time.time() - start_time
        print(f"   Request {request_id}: {elapsed:.3f}s - {data['name']}")
        return data
    
    # Make initial request to populate cache
    await make_request(0)
    
    # Wait for data to become stale
    await asyncio.sleep(35)
    
    # Make multiple concurrent requests to the same stale data
    print("\nConcurrent requests to stale data:")
    tasks = [make_request(i) for i in range(1, 6)]
    await asyncio.gather(*tasks)
    
    # Check cache statistics
    stats = service.cache_manager.get_stats()
    print(f"\nCache Statistics:")
    print(f"   L1 hits: {stats['l1_stats']['hits']}")
    print(f"   L2 hits: {stats['l2_stats']['hits']}")
    print(f"   Stale hits: {stats['swr_stats']['stale_hits']}")
    print(f"   Background refreshes: {stats['swr_stats']['background_refreshes']}")


async def demonstrate_decorator_usage():
    """Demonstrate the cached decorator usage"""
    print("\n=== Cached Decorator Demonstration ===")
    
    # First call - cache miss
    print("\n1. First product call (cache miss):")
    start_time = time.time()
    product = await get_product_details(789)
    elapsed = time.time() - start_time
    print(f"   Response time: {elapsed:.2f}s")
    print(f"   Product: {product['name']}")
    
    # Second call - cache hit
    print("\n2. Second product call (cache hit):")
    start_time = time.time()
    product = await get_product_details(789)
    elapsed = time.time() - start_time
    print(f"   Response time: {elapsed:.2f}s")
    print(f"   Product: {product['name']}")


async def demonstrate_health_and_stats():
    """Demonstrate health checking and statistics"""
    print("\n=== Health Check and Statistics ===")
    
    service = DataService()
    
    # Perform some operations
    await service.get_user_data(111)
    await service.get_user_data(222)
    await service.get_market_data("AAPL")
    await service.get_market_data("GOOGL")
    
    # Get comprehensive statistics
    stats = service.cache_manager.get_stats()
    print("\nCache Statistics:")
    print(f"   L1 utilization: {stats['l1_stats']['utilization']:.2%}")
    print(f"   Overall hit rate: {stats['overall_stats']['hit_rate']:.2%}")
    print(f"   Total requests: {stats['overall_stats']['total_requests']}")
    
    # Perform health check
    health = await service.cache_manager.health_check()
    print(f"\nHealth Check:")
    print(f"   Overall health: {'✓' if health['healthy'] else '✗'}")
    print(f"   L1 healthy: {'✓' if health['l1_healthy'] else '✗'}")
    print(f"   L2 healthy: {'✓' if health['l2_healthy'] else '✗'}")
    
    # Clean up
    await service.cache_manager.close()


async def main():
    """Main demonstration function"""
    print("TieredCacheManager with SWR Demonstration")
    print("=" * 50)
    
    try:
        # Run all demonstrations
        await demonstrate_swr_behavior()
        await demonstrate_concurrent_access()
        await demonstrate_decorator_usage()
        await demonstrate_health_and_stats()
        
        print("\n" + "=" * 50)
        print("Demonstration completed successfully!")
        
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        raise
    
    finally:
        # Clean up any remaining resources
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())
