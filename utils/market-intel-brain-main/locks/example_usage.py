"""
Distributed Lock Manager - Example Usage

This file demonstrates how to use the distributed lock manager to prevent
cache stampede and provide safe distributed locking with auto-release.
"""

import asyncio
import time
import random
from typing import Dict, Any

from locks import (
    LockManager, 
    get_lock, 
    distributed_lock,
    cache_stampede_protect,
    get_global_manager
)


# Example data store (simulating external API/database)
class DataStore:
    def __init__(self):
        self.data = {}
        self.api_call_count = 0
        self.lock = asyncio.Lock()
    
    async def fetch_expensive_data(self, key: str) -> Dict[str, Any]:
        """Simulate expensive API call."""
        async with self.lock:
            self.api_call_count += 1
        
        print(f"    📡 API CALL #{self.api_call_count}: Fetching {key}")
        
        # Simulate network latency
        await asyncio.sleep(1.0)
        
        # Simulate data
        return {
            "key": key,
            "value": f"data_for_{key}",
            "timestamp": time.time(),
            "api_call": self.api_call_count
        }


async def demonstrate_basic_locking():
    """Demonstrate basic distributed locking."""
    print("=== Basic Distributed Locking ===\n")
    
    manager = LockManager()
    data_store = DataStore()
    
    async def worker(worker_id: int):
        """Worker that tries to access shared resource."""
        try:
            async with manager.get_lock("shared_resource", timeout=2.0) as lock_wrapper:
                if lock_wrapper.has_lock():
                    print(f"Worker {worker_id}: Acquired lock, processing...")
                    
                    # Simulate work
                    result = await data_store.fetch_expensive_data("resource_1")
                    print(f"Worker {worker_id}: Got result: {result['api_call']}")
                    
                    await asyncio.sleep(0.5)
                    print(f"Worker {worker_id}: Processing complete")
                else:
                    print(f"Worker {worker_id}: Using stale data")
                    
        except Exception as e:
            print(f"Worker {worker_id}: Error - {e}")
    
    # Run multiple workers concurrently
    print("Starting 5 workers to compete for lock...")
    tasks = [worker(i) for i in range(5)]
    await asyncio.gather(*tasks)
    
    print(f"\nTotal API calls made: {data_store.api_call_count}")
    print("Expected: 1 (due to lock protection)")


async def demonstrate_cache_stampede_protection():
    """Demonstrate cache stampede protection."""
    print("\n=== Cache Stampede Protection ===\n")
    
    manager = LockManager()
    data_store = DataStore()
    
    async def fetch_data_with_protection(key: str):
        """Fetch data with cache stampede protection."""
        return await manager.protect_cache_stampede(
            cache_key=key,
            data_fetcher=data_store.fetch_expensive_data,
            key,
            timeout=3.0,
            return_stale=True
        )
    
    async def worker(worker_id: int):
        """Worker that fetches data."""
        try:
            result = await fetch_data_with_protection("protected_data")
            print(f"Worker {worker_id}: Got data from API call #{result['api_call']}")
            
        except Exception as e:
            print(f"Worker {worker_id}: Error - {e}")
    
    # Run multiple workers concurrently
    print("Starting 5 workers to fetch protected data...")
    tasks = [worker(i) for i in range(5)]
    await asyncio.gather(*tasks)
    
    print(f"\nTotal API calls made: {data_store.api_call_count}")
    print("Expected: 1 (cache stampede prevented)")


async def demonstrate_stale_data_fallback():
    """Demonstrate stale data fallback when lock can't be acquired."""
    print("\n=== Stale Data Fallback ===\n")
    
    manager = LockManager()
    data_store = DataStore()
    
    # Pre-populate stale data
    stale_data = {"key": "stale_key", "value": "stale_data", "timestamp": time.time() - 300}
    manager._set_stale_data("stale_key", stale_data)
    
    async def fetch_with_stale_fallback():
        """Fetch data with stale data fallback."""
        try:
            async with manager.get_lock(
                "stale_key", 
                timeout=0.1,  # Very short timeout
                return_stale=True
            ) as lock_wrapper:
                
                if lock_wrapper.has_lock():
                    print("    🔒 Lock acquired, fetching fresh data")
                    return await data_store.fetch_expensive_data("stale_key")
                else:
                    print("    📄 Using stale data")
                    return lock_wrapper.get_stale_data()
                    
        except Exception as e:
            print(f"    ❌ Error: {e}")
            return None
    
    # First call - should get stale data (lock timeout)
    print("1. First call (should get stale data):")
    result1 = await fetch_with_stale_fallback()
    print(f"   Result: {result1.get('value', 'No data')}")
    
    # Wait and try again
    await asyncio.sleep(0.2)
    
    print("\n2. Second call (should get fresh data):")
    result2 = await fetch_with_stale_fallback()
    print(f"   Result: {result2.get('value', 'No data')}")
    print(f"   API call: #{result2.get('api_call', 'N/A')}")


@distributed_lock("critical_operation_{user_id}", timeout=5.0)
async def critical_operation(user_id: int, operation: str) -> Dict[str, Any]:
    """Example function with distributed lock decorator."""
    print(f"    🔒 Executing critical operation for user {user_id}: {operation}")
    
    # Simulate critical work
    await asyncio.sleep(1.0)
    
    return {
        "user_id": user_id,
        "operation": operation,
        "timestamp": time.time(),
        "worker": asyncio.current_task().get_name()
    }


async def demonstrate_decorator_usage():
    """Demonstrate distributed lock decorator."""
    print("\n=== Distributed Lock Decorator ===\n")
    
    async def worker(worker_id: int, user_id: int):
        """Worker that performs critical operations."""
        try:
            result = await critical_operation(user_id, f"operation_by_worker_{worker_id}")
            print(f"Worker {worker_id}: Completed - {result['worker']}")
            
        except Exception as e:
            print(f"Worker {worker_id}: Error - {e}")
    
    # Multiple workers trying to access same user's critical operation
    print("Starting 3 workers for user 123...")
    tasks = [worker(i, 123) for i in range(3)]
    await asyncio.gather(*tasks)
    
    print("\nStarting 2 workers for user 456...")
    tasks = [worker(i, 456) for i in range(3, 5)]
    await asyncio.gather(*tasks)


@cache_stampede_protect("expensive_query_{symbol}", timeout=3.0)
async def expensive_stock_query(symbol: str) -> Dict[str, Any]:
    """Example expensive stock query with cache stampede protection."""
    print(f"    📈 Executing expensive query for {symbol}")
    
    # Simulate expensive database/API call
    await asyncio.sleep(1.5)
    
    return {
        "symbol": symbol,
        "price": 100.0 + random.random() * 50,
        "timestamp": time.time(),
        "query_id": random.randint(1000, 9999)
    }


async def demonstrate_cache_stampede_decorator():
    """Demonstrate cache stampede protection decorator."""
    print("\n=== Cache Stampede Protection Decorator ===\n")
    
    async def worker(worker_id: int, symbol: str):
        """Worker that queries stock data."""
        try:
            result = await expensive_stock_query(symbol)
            print(f"Worker {worker_id}: {symbol} = ${result['price']:.2f} (Query #{result['query_id']})")
            
        except Exception as e:
            print(f"Worker {worker_id}: Error - {e}")
    
    # Multiple workers querying same symbol
    print("Starting 5 workers to query AAPL...")
    tasks = [worker(i, "AAPL") for i in range(5)]
    await asyncio.gather(*tasks)
    
    print("\nStarting 3 workers to query GOOGL...")
    tasks = [worker(i, "GOOGL") for i in range(5, 8)]
    await asyncio.gather(*tasks)


async def demonstrate_lock_extension():
    """Demonstrate lock TTL extension."""
    print("\n=== Lock TTL Extension ===\n")
    
    manager = LockManager()
    
    async def long_running_task():
        """Task that extends its lock."""
        async with manager.get_lock("long_task", ttl=2000) as lock_wrapper:  # 2 second TTL
            if lock_wrapper.has_lock():
                print("    🔒 Lock acquired for long task")
                
                # Simulate work that takes longer than TTL
                for i in range(5):
                    await asyncio.sleep(0.6)  # Total 3 seconds
                    
                    if i == 2:  # Extend after 1.8 seconds
                        print("    ⏰ Extending lock TTL...")
                        await lock_wrapper.extend_lock(3000)  # Add 3 seconds
                        print("    ✅ Lock extended")
                    
                    print(f"    Working... step {i+1}/5")
                
                print("    ✅ Long task completed")
    
    # Try to acquire the same lock
    async def competing_task():
        """Task that tries to acquire the same lock."""
        await asyncio.sleep(1.0)  # Wait a bit
        print("    🔄 Competing task trying to acquire lock...")
        
        try:
            async with manager.get_lock("long_task", timeout=1.0) as lock_wrapper:
                if lock_wrapper.has_lock():
                    print("    🎉 Competing task got lock!")
                else:
                    print("    📄 Competing task got stale data")
        except Exception as e:
            print(f"    ❌ Competing task failed: {e}")
    
    # Run both tasks
    await asyncio.gather(long_running_task(), competing_task())


async def demonstrate_global_manager():
    """Demonstrate global lock manager usage."""
    print("\n=== Global Lock Manager ===\n")
    
    # Get global manager
    manager1 = get_global_manager()
    manager2 = get_global_manager()
    
    print(f"Manager 1 ID: {id(manager1)}")
    print(f"Manager 2 ID: {id(manager2)}")
    print(f"Same instance: {manager1 is manager2}")
    
    # Use global manager
    async with get_lock("global_test", timeout=2.0) as lock_wrapper:
        if lock_wrapper.has_lock():
            print("    🔒 Global lock acquired")
            await asyncio.sleep(0.5)
            print("    ✅ Global lock released")
    
    # Show statistics
    stats = manager1.get_statistics()
    print(f"\nGlobal manager statistics: {stats}")


async def demonstrate_error_handling():
    """Demonstrate error handling scenarios."""
    print("\n=== Error Handling ===\n")
    
    manager = LockManager()
    
    # Test timeout
    print("1. Testing lock timeout:")
    try:
        async with manager.get_lock("timeout_test", timeout=0.1) as lock_wrapper:
            if lock_wrapper.has_lock():
                # Hold lock longer than timeout for next attempt
                await asyncio.sleep(0.2)
    except Exception as e:
        print(f"   Expected error: {type(e).__name__}")
    
    # Try to acquire same lock with short timeout
    try:
        async with manager.get_lock("timeout_test", timeout=0.1) as lock_wrapper:
            print("   Unexpected success!")
    except Exception as e:
        print(f"   Expected timeout: {type(e).__name__}")
    
    # Test invalid operations
    print("\n2. Testing lock operations:")
    lock_info = None
    try:
        # Try to extend non-existent lock
        await manager.redlock.extend(lock_info, 1000)
    except Exception as e:
        print(f"   Expected error for invalid extension: {type(e).__name__}")


async def demonstrate_swor_integration():
    """Demonstrate integration with SWR (Stale-While-Revalidate)."""
    print("\n=== SWR Integration ===\n")
    
    manager = LockManager()
    data_store = DataStore()
    
    async def swr_fetch(key: str) -> Dict[str, Any]:
        """SWR-style fetch with lock protection."""
        # Try to get fresh data with lock
        try:
            return await manager.refresh_with_lock(
                key=key,
                refresh_func=data_store.fetch_expensive_data,
                key,
                timeout=2.0
            )
        except Exception as e:
            print(f"    ⚠️ Refresh failed, getting stale data: {e}")
            # Return stale data if refresh fails
            return manager._get_stale_data(key, 300) or {"error": "No data available"}
    
    # First call - should fetch fresh data
    print("1. First SWR call (fresh data):")
    result1 = await swr_fetch("swr_key")
    print(f"   Result: API call #{result1.get('api_call', 'N/A')}")
    
    # Second call immediately - should get stale data while refresh happens
    print("\n2. Second SWR call (stale data + background refresh):")
    
    async def concurrent_call():
        return await swr_fetch("swr_key")
    
    # Run concurrent calls
    results = await asyncio.gather(swr_fetch("swr_key"), concurrent_call())
    print(f"   Results: API calls #{[r.get('api_call', 'N/A') for r in results]}")


async def main():
    """Run all demonstrations."""
    print("Distributed Lock Manager - Complete Demonstration")
    print("=" * 60)
    
    try:
        await demonstrate_basic_locking()
        await demonstrate_cache_stampede_protection()
        await demonstrate_stale_data_fallback()
        await demonstrate_decorator_usage()
        await demonstrate_cache_stampede_decorator()
        await demonstrate_lock_extension()
        await demonstrate_global_manager()
        await demonstrate_error_handling()
        await demonstrate_swor_integration()
        
        print("\n" + "=" * 60)
        print("All demonstrations completed successfully!")
        print("\nKey Features Demonstrated:")
        print("✓ Redlock algorithm implementation")
        print("✓ Cache stampede protection")
        print("✓ Stale data fallback")
        print("✓ Auto-release TTL to prevent deadlocks")
        print("✓ Context manager (async with) usage")
        print("✓ Distributed lock decorators")
        print("✓ Lock TTL extension")
        print("✓ Global manager instance")
        print("✓ Error handling and timeouts")
        print("✓ SWR integration")
        
    except Exception as e:
        print(f"\nDemonstration failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up global manager
        try:
            global_manager = get_global_manager()
            await global_manager.close()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())
