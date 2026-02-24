"""
MAIFA v3 Data Ingestion Test - Standalone
Tests complete data ingestion system
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from services.data_ingestion.sources import register_all_sources
from services.data_ingestion.orchestrator import DataIngestionOrchestrator
from services.data_ingestion.registry import source_registry

async def test_data_ingestion():
    """Test complete data ingestion system"""
    print("MAIFA v3 Data Ingestion Test")
    print("=" * 50)
    
    try:
        # Register all sources
        print("Registering all data sources...")
        await register_all_sources()
        
        # Get registry info
        registry_info = await source_registry.get_registry_info()
        print(f"Total sources registered: {registry_info['total_sources']}")
        print(f"Enabled sources: {registry_info['enabled_sources']}")
        
        # List all sources
        sources = await source_registry.list_sources()
        print("\nRegistered Data Sources:")
        for source in sources:
            print(f"  - {source}")
        
        # Test ingestion with sample parameters
        print("\nTesting data ingestion...")
        test_params = {
            "symbol": "AAPL",
            "query": "business",
            "language": "en",
            "country": "US",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        orchestrator = DataIngestionOrchestrator()
        results = await orchestrator.ingest_all_sources(test_params)
        
        print(f"\nIngestion Results:")
        print(f"  Total sources: {results.get('total_sources', 0)}")
        print(f"  Successful: {results.get('successful', 0)}")
        print(f"  Failed: {results.get('failed', 0)}")
        
        # Show individual source results
        source_results = results.get('results', {})
        for source_name, result in source_results.items():
            status = result.get('status', 'unknown')
            print(f"  {source_name}: {status}")
            
            if status == 'success':
                print(f"    Data points: {len(result.get('data', {}).get('data', []))}")
            else:
                print(f"    Error: {result.get('error', 'Unknown error')}")
        
        print("\nData ingestion test completed successfully")
        return True
        
    except Exception as e:
        print(f"\nData ingestion test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_data_ingestion())
    sys.exit(0 if success else 1)
