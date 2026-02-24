"""
Minimal Phase 2 Test - No complex imports
"""

print("Minimal Phase 2 Test")
print("=" * 50)

# Test 1: Basic Python functionality
print("\n1. Testing basic functionality...")
try:
    import asyncio
    import time
    from datetime import datetime, timezone
    from decimal import Decimal
    
    print("   Basic imports: OK")
    
    # Test basic async
    async def test_async():
        await asyncio.sleep(0.1)
        return "async works"
    
    result = asyncio.run(test_async())
    print(f"   Async test: {result}")
    
except Exception as e:
    print(f"   Basic functionality failed: {e}")

# Test 2: Token bucket limiter
print("\n2. Testing token bucket limiter...")
try:
    import token_bucket_limiter
    from token_bucket_limiter import get_token_bucket_limiter, APIProvider
    
    limiter = get_token_bucket_limiter()
    status = limiter.get_status(APIProvider.ALPHA_VANTAGE)
    print(f"   Token bucket: OK")
    print(f"   Alpha Vantage tokens: {status['tokens']:.1f}/{status['max_tokens']}")
    
except Exception as e:
    print(f"   Token bucket failed: {e}")

# Test 3: Infrastructure
print("\n3. Testing infrastructure...")
try:
    from infrastructure.data_normalization import DataType, SourceType
    from infrastructure.secrets_manager import get_secrets_manager
    
    print(f"   Infrastructure: OK")
    print(f"   DataType.EQUITY: {DataType.EQUITY}")
    print(f"   SourceType.REST: {SourceType.REST}")
    
except Exception as e:
    print(f"   Infrastructure failed: {e}")

# Test 4: Simple data creation
print("\n4. Testing data creation...")
try:
    from infrastructure.data_normalization import UnifiedInternalSchema
    
    # Create test data
    test_data = UnifiedInternalSchema(
        data_type=DataType.EQUITY,
        source="test",
        source_type=SourceType.REST,
        symbol="AAPL",
        timestamp=datetime.now(timezone.utc),
        price=Decimal("150.25"),
        volume=1000000
    )
    
    print(f"   Data creation: OK")
    print(f"   Symbol: {test_data.symbol}, Price: {test_data.price}")
    
except Exception as e:
    print(f"   Data creation failed: {e}")

print("\nMinimal test completed!")
