"""
Simple Phase 2 Test - Debug Import Issues
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

print("Simple Phase 2 Test")
print("=" * 50)

# Test imports one by one
print("\n1. Testing basic imports...")
try:
    import asyncio
    import aiohttp
    print("   Basic async imports: OK")
except Exception as e:
    print(f"   Basic async imports failed: {e}")

print("\n2. Testing token bucket limiter...")
try:
    import token_bucket_limiter
    print("   Token bucket limiter: OK")
except Exception as e:
    print(f"   Token bucket limiter failed: {e}")

print("\n3. Testing infrastructure...")
try:
    from infrastructure.data_normalization import UnifiedInternalSchema, DataType, SourceType
    from infrastructure.secrets_manager import get_secrets_manager
    print("   Infrastructure: OK")
except Exception as e:
    print(f"   Infrastructure failed: {e}")

print("\n4. Testing tradfi providers...")
try:
    import tradfi_providers
    print("   TradFi providers: OK")
except Exception as e:
    print(f"   TradFi providers failed: {e}")
    import traceback
    traceback.print_exc()

print("\n5. Testing authenticated providers...")
try:
    import authenticated_providers
    print("   Authenticated providers: OK")
except Exception as e:
    print(f"   Authenticated providers failed: {e}")
    import traceback
    traceback.print_exc()

print("\n6. Testing other components...")
try:
    import provider_registry
    import network_optimizer
    import parquet_storage
    print("   Other components: OK")
except Exception as e:
    print(f"   Other components failed: {e}")

print("\nTest completed!")
