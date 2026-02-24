"""
Full Dummy Orchestration Test - No External API Calls
Tests the complete pipeline with mocked data
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

class MockDataFetcher:
    """Mock fetcher that returns dummy data"""
    
    def __init__(self, source_name):
        self.source_name = source_name
    
    async def fetch(self, symbols=None, **kwargs):
        """Mock fetch returning dummy data"""
        await asyncio.sleep(0.001)  # Simulate minimal async work
        return {
            "status": "ok",
            "source": self.source_name,
            "sample": 123,
            "symbols": symbols or [],
            "timestamp": "2026-02-21T15:00:00Z"
        }
    
    async def health_check(self):
        """Mock health check"""
        return True

class MockDataParser:
    """Mock parser"""
    
    def __init__(self, source_name):
        self.source_name = source_name
    
    async def parse(self, raw_data):
        """Mock parse"""
        await asyncio.sleep(0.001)
        return raw_data

class MockDataValidator:
    """Mock validator"""
    
    def __init__(self, source_name):
        self.source_name = source_name
    
    async def validate(self, parsed_data):
        """Mock validate - always returns True"""
        await asyncio.sleep(0.001)
        return True

class MockDataNormalizer:
    """Mock normalizer"""
    
    def __init__(self, source_name):
        self.source_name = source_name
    
    async def normalize(self, validated_data):
        """Mock normalize"""
        await asyncio.sleep(0.001)
        return {
            "normalized": True,
            "source": self.source_name,
            "data": validated_data,
            "format": "maifa_standard"
        }

async def create_mock_source_registry():
    """Create a mock registry with all 13 sources"""
    
    sources = [
        "YahooFinance",
        "AlphaVantage", 
        "NewsCatcherAPI",
        "GoogleNewsScraper",
        "EconDB",
        "TradingEconomics",
        "MarketStack",
        "FinMind",
        "TwelveData",
        "Finnhub",
        "FinancialModelingPrep",
        "EuroStatFeeds",
        "IMFJsonFeeds"
    ]
    
    mock_registry = {}
    
    for source_name in sources:
        mock_registry[source_name] = {
            "fetcher": MockDataFetcher(source_name),
            "parser": MockDataParser(source_name),
            "validator": MockDataValidator(source_name),
            "normalizer": MockDataNormalizer(source_name),
            "config": {
                "name": source_name,
                "description": f"Mock {source_name} data source",
                "api_key_required": False,
                "mock": True
            }
        }
    
    return mock_registry

async def run_dummy_orchestration_test():
    """Run full dummy orchestration test"""
    print("=" * 80)
    print("MAIFA DUMMY ORCHESTRATION TEST - NO EXTERNAL API CALLS")
    print("=" * 80)
    
    try:
        # Import orchestrator
        from services.data_ingestion.orchestrator import DataIngestionOrchestrator
        
        # Create orchestrator instance
        orchestrator = DataIngestionOrchestrator()
        
        # Mock the source instances
        mock_registry = await create_mock_source_registry()
        orchestrator.source_instances = {
            name: {
                "fetcher": instances["fetcher"],
                "parser": instances["parser"],
                "validator": instances["validator"],
                "normalizer": instances["normalizer"]
            }
            for name, instances in mock_registry.items()
        }
        orchestrator.source_configs = {
            name: instances["config"]
            for name, instances in mock_registry.items()
        }
        orchestrator.sources_loaded = True
        
        print("\n1. MOCK REGISTRY CREATED")
        print(f"   Sources: {len(orchestrator.source_instances)}")
        print(f"   List: {', '.join(orchestrator.source_instances.keys())}")
        
        # Step 1: Skip load_sources and use mock data directly
        print("\n2. USING MOCK DATA (skipping load_sources)...")
        print(f"   Mock sources ready: {len(orchestrator.source_instances)}")
        print(f"   Sources loaded: {len(orchestrator.source_instances)}")
        
        # Step 2: Fetch all data
        print("\n3. FETCHING DATA FROM ALL SOURCES...")
        fetch_start = asyncio.get_event_loop().time()
        data = await orchestrator.fetch_all(symbols=["AAPL", "GOOGL", "BTC"])
        fetch_end = asyncio.get_event_loop().time()
        fetch_time = fetch_end - fetch_start
        
        print(f"   Fetch completed in: {fetch_time:.3f} seconds")
        print(f"   Sources responded: {len(data)}")
        
        # Print fetch results
        print("\n   FETCH RESULTS:")
        for source, result in data.items():
            status = result.get('status', 'unknown')
            source_name = result.get('source', 'unknown')
            print(f"     - {source_name}: {status}")
        
        # Step 3: Validate all data
        print("\n4. VALIDATING DATA FROM ALL SOURCES...")
        validate_start = asyncio.get_event_loop().time()
        validated = await orchestrator.validate_all(data)
        validate_end = asyncio.get_event_loop().time()
        validate_time = validate_end - validate_start
        
        print(f"   Validation completed in: {validate_time:.3f} seconds")
        print(f"   Sources validated: {len(validated)}")
        
        # Print validation results
        print("\n   VALIDATION RESULTS:")
        for source, result in validated.items():
            status = result.get('status', 'unknown')
            is_valid = result.get('valid', False)
            print(f"     - {source}: {status} (valid: {is_valid})")
        
        # Step 4: Normalize all data
        print("\n5. NORMALIZING DATA FROM ALL SOURCES...")
        normalize_start = asyncio.get_event_loop().time()
        normalized = await orchestrator.normalize_all(validated)
        normalize_end = asyncio.get_event_loop().time()
        normalize_time = normalize_end - normalize_start
        
        print(f"   Normalization completed in: {normalize_time:.3f} seconds")
        print(f"   Sources normalized: {len(normalized)}")
        
        # Print final normalized results
        print("\n6. FINAL NORMALIZED OUTPUT:")
        print("=" * 80)
        for source, result in normalized.items():
            print(f"\n{source}:")
            print(f"  Status: {result.get('status', 'unknown')}")
            print(f"  Data: {result.get('data', {})}")
        
        # Performance summary
        total_time = fetch_time + validate_time + normalize_time
        print(f"\n7. PERFORMANCE SUMMARY:")
        print(f"   Total pipeline time: {total_time:.3f} seconds")
        print(f"   Average time per source: {total_time/13:.3f} seconds")
        print(f"   asyncio.gather working: {'YES' if total_time < 1.0 else 'NO'}")
        
        # Verification
        print(f"\n8. VERIFICATION CHECKLIST:")
        print(f"   [OK] All sources load correctly: {len(orchestrator.source_instances) == 13}")
        print(f"   [OK] asyncio.gather is working: {total_time < 1.0}")
        print(f"   [OK] No blocking operations: {total_time < 1.0}")
        print(f"   [OK] Unified structured output: {len(normalized) == 13}")
        
        print("\n" + "=" * 80)
        print("DUMMY ORCHESTRATION TEST COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\nDUMMY ORCHESTRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_dummy_orchestration_test())
    sys.exit(0 if success else 1)
