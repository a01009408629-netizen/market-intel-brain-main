#!/usr/bin/env python3
"""
Simple test server for Market Intel Brain
Tests basic functionality without unicode issues
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

async def test_basic_imports():
    """Test basic imports"""
    try:
        print("Testing basic imports...")
        
        # Test FastAPI
        import fastapi
        print("✓ FastAPI imported successfully")
        
        # Test uvicorn
        import uvicorn
        print("✓ Uvicorn imported successfully")
        
        # Test pydantic
        import pydantic
        print("✓ Pydantic imported successfully")
        
        return True
    except Exception as e:
        print(f"✗ Import test failed: {e}")
        return False

async def test_data_ingestion():
    """Test data ingestion service"""
    try:
        print("\nTesting data ingestion service...")
        
        from services.data_ingestion import get_orchestrator
        orchestrator = get_orchestrator()
        print("✓ Data ingestion orchestrator imported successfully")
        
        return True
    except Exception as e:
        print(f"✗ Data ingestion test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("=" * 60)
    print("MARKET INTEL BRAIN - SIMPLE TEST")
    print("=" * 60)
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("Data Ingestion", test_data_ingestion),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n[{test_name}]")
        result = await test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 60)
    print("TEST RESULTS:")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n✓ All tests passed! System is ready.")
        return True
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
