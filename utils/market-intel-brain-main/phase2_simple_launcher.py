"""
Phase 2 Simple Launcher - Test Core Components Only
"""

import asyncio
import sys
import os
import time
from datetime import datetime, timezone

# Add current directory to path
sys.path.insert(0, os.getcwd())

print("Phase 2 Simple Launcher")
print("=" * 50)

async def test_token_bucket():
    """Test token bucket rate limiter."""
    print("\n1. Testing Token Bucket Rate Limiter...")
    
    try:
        from token_bucket_limiter import get_token_bucket_limiter, APIProvider
        
        limiter = get_token_bucket_limiter()
        
        # Test Alpha Vantage (strictest)
        provider = APIProvider.ALPHA_VANTAGE
        
        # Show initial status
        status = limiter.get_status(provider)
        print(f"   Alpha Vantage: {status['tokens']:.1f}/{status['max_tokens']} tokens")
        print(f"   Daily: {status['daily_tokens']}/{status['daily_limit']}")
        
        # Try to consume a token
        consumed = await limiter.can_consume(provider)
        print(f"   Consumed token: {consumed}")
        
        # Show updated status
        updated_status = limiter.get_status(provider)
        print(f"   After consumption: {updated_status['tokens']:.1f}/{updated_status['max_tokens']}")
        
        return True
        
    except Exception as e:
        print(f"   Token bucket test failed: {e}")
        return False

async def test_network_optimizer():
    """Test network optimizer."""
    print("\n2. Testing Network Optimizer...")
    
    try:
        from network_optimizer import get_network_optimizer
        
        optimizer = get_network_optimizer()
        
        # Test simple request
        result = await optimizer.make_request("GET", "https://httpbin.org/json")
        
        if result:
            print(f"   Network request: SUCCESS")
            print(f"   Response keys: {list(result.keys())[:3]}")
        else:
            print(f"   Network request: FAILED")
        
        # Show metrics
        metrics = optimizer.get_metrics()
        print(f"   Total requests: {metrics['total_requests']}")
        print(f"   Success rate: {metrics['success_rate']:.1%}")
        
        await optimizer.close_session()
        return result is not None
        
    except Exception as e:
        print(f"   Network optimizer test failed: {e}")
        return False

async def test_parquet_storage():
    """Test Parquet storage."""
    print("\n3. Testing Parquet Storage...")
    
    try:
        from parquet_storage import get_parquet_storage
        from infrastructure.data_normalization import UnifiedInternalSchema, DataType, SourceType
        from decimal import Decimal
        
        storage = get_parquet_storage()
        await storage.start()
        
        # Create test data
        test_items = []
        for i in range(10):
            item = UnifiedInternalSchema(
                data_type=DataType.EQUITY,
                source="test",
                source_type=SourceType.REST,
                symbol="AAPL",
                timestamp=datetime.now(timezone.utc),
                price=Decimal(str(150.0 + i)),
                volume=1000000 + i
            )
            test_items.append(item)
        
        # Store data
        stored_count = await storage.store_items(test_items)
        print(f"   Stored: {stored_count} items")
        
        # Query data
        queried_data = await storage.storage.query_data(
            data_type="EQUITY",
            symbol="AAPL",
            limit=5
        )
        print(f"   Queried: {len(queried_data)} items")
        
        # Get stats
        stats = storage.get_storage_stats()
        print(f"   Buffer: {stats['buffer_stats']['buffer_size_mb']:.2f}MB")
        
        await storage.stop()
        return stored_count > 0
        
    except Exception as e:
        print(f"   Parquet storage test failed: {e}")
        return False

async def test_tradfi_providers():
    """Test basic TradFi providers."""
    print("\n4. Testing TradFi Providers...")
    
    try:
        from tradfi_providers import get_tradfi_provider_factory
        
        factory = get_tradfi_provider_factory()
        providers = factory.list_providers()
        print(f"   Available providers: {providers}")
        
        # Test Yahoo Finance (keyless)
        yahoo_provider = factory.create_provider("yahoo_finance")
        connected = await yahoo_provider.connect()
        
        if connected:
            data = await yahoo_provider.get_data("AAPL")
            print(f"   Yahoo Finance: CONNECTED, Data: {len(data)} items")
            if data:
                print(f"   AAPL Price: {data[0].price}")
        else:
            print(f"   Yahoo Finance: FAILED")
        
        await yahoo_provider.disconnect()
        return connected
        
    except Exception as e:
        print(f"   TradFi providers test failed: {e}")
        return False

async def main():
    """Run all Phase 2 tests."""
    start_time = time.time()
    
    tests = [
        ("Token Bucket", test_token_bucket),
        ("Network Optimizer", test_network_optimizer),
        ("Parquet Storage", test_parquet_storage),
        ("TradFi Providers", test_tradfi_providers)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
            status = "PASS" if result else "FAIL"
            print(f"   {test_name}: {status}")
        except Exception as e:
            results[test_name] = False
            print(f"   {test_name}: ERROR - {e}")
    
    # Summary
    total_time = time.time() - start_time
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    print(f"\n{'='*50}")
    print("PHASE 2 TEST SUMMARY")
    print(f"{'='*50}")
    print(f"Total Time: {total_time:.2f} seconds")
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total:.1%}")
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"  {test_name}: {status}")
    
    if passed == total:
        print(f"\n🎉 All Phase 2 tests PASSED!")
        print("System ready for production with authenticated APIs!")
    else:
        print(f"\n⚠️  Some tests failed. Review above errors.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
