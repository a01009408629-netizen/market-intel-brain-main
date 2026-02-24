"""
Simple test for MAIFA Data Ingestion Orchestrator
"""

import asyncio
import logging
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def simple_test():
    """Simple test of orchestrator functionality"""
    print("Testing MAIFA Data Ingestion Orchestrator - Simple Test")
    print("=" * 60)
    
    try:
        # Test importing the orchestrator
        from services.data_ingestion.orchestrator import DataIngestionOrchestrator
        
        # Create instance
        test_orchestrator = DataIngestionOrchestrator()
        
        print("✅ Orchestrator imported successfully")
        
        # Test basic functionality
        status = await test_orchestrator.get_source_status()
        print(f"✅ Status check: {status}")
        
        health = await test_orchestrator.health_check()
        print(f"✅ Health check: {health}")
        
        print("\nORCHESTRATOR BASIC TEST PASSED!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ORCHESTRATOR TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(simple_test())
    sys.exit(0 if success else 1)
