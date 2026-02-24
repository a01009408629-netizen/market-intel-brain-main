"""
Test script for MAIFA Data Ingestion Orchestrator
"""

import asyncio
import logging
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.data_ingestion.orchestrator import orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_orchestrator():
    """Test the orchestrator functionality"""
    print("Testing MAIFA Data Ingestion Orchestrator")
    print("=" * 60)
    
    try:
        # Test 1: Load sources
        print("\n1. Loading all 13 data sources...")
        load_success = await orchestrator.load_sources()
        print(f"   Sources loaded: {'SUCCESS' if load_success else 'FAILED'}")
        
        # Get status
        status = await orchestrator.get_source_status()
        print(f"   Total sources: {status['total_sources']}")
        print(f"   Source list: {', '.join(status['source_list'])}")
        
        # Test 2: Health check
        print("\n2. Performing health check...")
        health = await orchestrator.health_check()
        print(f"   Overall health: {health['overall_health']}")
        
        # Test 3: Fetch data (small test)
        print("\n3. Testing data fetch (limited to 3 sources)...")
        test_symbols = ["AAPL", "GOOGL"]
        
        # Just test with a few sources to avoid API limits
        fetch_results = await orchestrator.fetch_all(
            symbols=test_symbols, 
            timeout=10.0,
            test_mode=True  # Add this param to limit sources
        )
        
        print(f"   Fetch results: {len(fetch_results)} sources responded")
        for source, result in list(fetch_results.items())[:3]:  # Show first 3
            status = result.get('status', 'unknown')
            print(f"   - {source}: {status}")
        
        # Test 4: Validate data
        print("\n4. Testing data validation...")
        validation_results = await orchestrator.validate_all(fetch_results)
        print(f"   Validation results: {len(validation_results)} sources validated")
        
        # Test 5: Normalize data
        print("\n5. Testing data normalization...")
        normalization_results = await orchestrator.normalize_all(validation_results)
        print(f"   Normalization results: {len(normalization_results)} sources normalized")
        
        print("\nORCHESTRATOR TEST COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\nORCHESTRATOR TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_orchestrator())
    sys.exit(0 if success else 1)
