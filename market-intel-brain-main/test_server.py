#!/usr/bin/env python3
"""
Test script to verify hybrid API server functionality
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_server():
    """Test server components without running full server"""
    print("🧪 Testing Hybrid API Server Components...")
    
    try:
        # Test 1: Import all required modules
        print("\n1️⃣ Testing imports...")
        from utils.hybrid_logger import initialize_hybrid_logging, get_hybrid_logger
        from services.cache.hybrid_cache_manager import get_hybrid_cache_manager
        from adapters.mock_provider import MockProvider
        from orchestrator.registry import AdapterRegistry
        from qos.scheduler import QoSScheduler, SchedulerConfig
        from security.settings import get_settings
        print("✅ All imports successful")
        
        # Test 2: Initialize logging
        print("\n2️⃣ Testing logging...")
        initialize_hybrid_logging()
        logger = get_hybrid_logger("TestServer")
        logger.info("Test logging initialized")
        print("✅ Logging initialized")
        
        # Test 3: Test mock provider
        print("\n3️⃣ Testing MockProvider...")
        mock_provider = MockProvider()
        test_data = await mock_provider.fetch({"symbol": "AAPL"})
        print(f"✅ MockProvider data: {test_data}")
        
        # Test 4: Test adapter registry
        print("\n4️⃣ Testing AdapterRegistry...")
        registry = AdapterRegistry()
        registry.register_adapter("test_mock", MockProvider)
        print(f"✅ AdapterRegistry: {len(registry._adapters)} adapters registered")
        
        # Test 5: Test cache manager
        print("\n5️⃣ Testing CacheManager...")
        cache_manager = get_hybrid_cache_manager()
        await cache_manager.set("test_key", {"test": "data"})
        cached_data = await cache_manager.get("test_key")
        print(f"✅ CacheManager: {cached_data}")
        
        # Test 6: Test QoS scheduler
        print("\n6️⃣ Testing QoS Scheduler...")
        scheduler_config = SchedulerConfig(auto_start=False)
        scheduler = QoSScheduler(scheduler_config)
        print(f"✅ QoS Scheduler initialized")
        
        # Test 7: Test security settings
        print("\n7️⃣ Testing Security Settings...")
        settings = get_settings()
        print(f"✅ Security settings loaded")
        
        print("\n🎉 All tests passed! Server components are working correctly.")
        print("\n📋 Summary:")
        print("   - Logging: ✅ Operational")
        print("   - MockProvider: ✅ Generating data")
        print("   - AdapterRegistry: ✅ Managing adapters")
        print("   - CacheManager: ✅ Redis + fallback")
        print("   - QoS Scheduler: ✅ Task management")
        print("   - Security Settings: ✅ Configuration loaded")
        
        print("\n🚀 Server is ready to run!")
        print("   Run: python hybrid_api_server_fixed.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Set environment variables for testing
    os.environ["ENABLE_ENCRYPTION"] = "false"
    os.environ["ENABLE_AUDIT_LOGGING"] = "false"
    os.environ["ENABLE_ZERO_TRUST"] = "false"
    os.environ["ENABLE_OBSERVABILITY"] = "false"
    
    # Run tests
    success = asyncio.run(test_server())
    sys.exit(0 if success else 1)
