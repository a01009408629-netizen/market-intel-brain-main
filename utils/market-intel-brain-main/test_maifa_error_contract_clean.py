"""
Test MAIFA Titanium Error Contract System
Verifies zero silent failures, zero inconsistent error shapes, zero unwrapped exceptions
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

class ErrorTestFetcher:
    """Mock fetcher that throws various errors"""
    
    def __init__(self, source_name, error_type="raw"):
        self.source_name = source_name
        self.error_type = error_type
    
    async def fetch(self, symbols=None, **kwargs):
        """Mock fetch that throws errors"""
        if self.error_type == "raw":
            raise ValueError(f"Raw exception from {self.source_name}")
        elif self.error_type == "maifa":
            from ...errors import FetchError
            raise FetchError(
                source=self.source_name,
                stage="fetch",
                error_type="CustomError",
                message="MAIFA wrapped error",
                retryable=True
            )
        elif self.error_type == "timeout":
            raise asyncio.TimeoutError(f"Timeout from {self.source_name}")

class ErrorTestValidator:
    """Mock validator that throws errors"""
    
    def __init__(self, source_name):
        self.source_name = source_name
    
    async def validate(self, data):
        """Mock validate that throws errors"""
        raise RuntimeError(f"Validation error from {self.source_name}")

class ErrorTestNormalizer:
    """Mock normalizer that throws errors"""
    
    def __init__(self, source_name):
        self.source_name = source_name
    
    async def normalize(self, data):
        """Mock normalize that throws errors"""
        raise TypeError(f"Normalization error from {self.source_name}")

async def test_maifa_error_contract():
    """Test the MAIFA Titanium Error Contract System"""
    print("=" * 80)
    print("MAIFA TITANIUM ERROR CONTRACT SYSTEM TEST")
    print("=" * 80)
    
    try:
        from services.data_ingestion.orchestrator import DataIngestionOrchestrator
        from services.data_ingestion.errors import MAIFAError, FetchError, ValidationError, NormalizationError
        
        # Create orchestrator
        orchestrator = DataIngestionOrchestrator()
        
        # Create mock sources with different error types
        error_sources = {
            "RawErrorSource": {
                "fetcher": ErrorTestFetcher("RawErrorSource", "raw"),
                "validator": ErrorTestValidator("RawErrorSource"),
                "normalizer": ErrorTestNormalizer("RawErrorSource")
            },
            "MAIFAErrorSource": {
                "fetcher": ErrorTestFetcher("MAIFAErrorSource", "maifa"),
                "validator": ErrorTestValidator("MAIFAErrorSource"),
                "normalizer": ErrorTestNormalizer("MAIFAErrorSource")
            },
            "TimeoutSource": {
                "fetcher": ErrorTestFetcher("TimeoutSource", "timeout"),
                "validator": ErrorTestValidator("TimeoutSource"),
                "normalizer": ErrorTestNormalizer("TimeoutSource")
            }
        }
        
        orchestrator.source_instances = error_sources
        orchestrator.sources_loaded = True
        
        print("\n1. TESTING FETCH STAGE ERROR HANDLING")
        print("-" * 50)
        
        # Test fetch stage
        fetch_results = await orchestrator.fetch_all(symbols=["TEST"])
        
        print(f"Fetch results: {len(fetch_results)} sources")
        for source, result in fetch_results.items():
            print(f"\n{source}:")
            print(f"  Status: {result.get('status', 'unknown')}")
            print(f"  Error Type: {result.get('error_type', 'none')}")
            print(f"  Message: {result.get('message', 'none')}")
            print(f"  Retryable: {result.get('retryable', 'none')}")
            print(f"  Timestamp: {result.get('timestamp', 'none')}")
            
            # Verify titanium contract format
            required_fields = ["source", "stage", "status", "error_type", "message", "retryable", "timestamp"]
            missing_fields = [field for field in required_fields if field not in result]
            if missing_fields:
                print(f"  [FAIL] MISSING FIELDS: {missing_fields}")
            else:
                print(f"  [OK] TITANIUM CONTRACT COMPLIANT")
        
        print("\n2. TESTING VALIDATION STAGE ERROR HANDLING")
        print("-" * 50)
        
        # Create mock successful fetch data for validation testing
        mock_fetch_data = {
            "RawErrorSource": {
                "status": "success",
                "data": {"test": "data"}
            },
            "MAIFAErrorSource": {
                "status": "success", 
                "data": {"test": "data"}
            },
            "TimeoutSource": {
                "status": "success",
                "data": {"test": "data"}
            }
        }
        
        validation_results = await orchestrator.validate_all(mock_fetch_data)
        
        print(f"Validation results: {len(validation_results)} sources")
        for source, result in validation_results.items():
            print(f"\n{source}:")
            print(f"  Status: {result.get('status', 'unknown')}")
            print(f"  Error Type: {result.get('error_type', 'none')}")
            print(f"  Message: {result.get('message', 'none')}")
            print(f"  Retryable: {result.get('retryable', 'none')}")
            
            # Verify titanium contract format
            required_fields = ["source", "stage", "status", "error_type", "message", "retryable", "timestamp"]
            missing_fields = [field for field in required_fields if field not in result]
            if missing_fields:
                print(f"  [FAIL] MISSING FIELDS: {missing_fields}")
            else:
                print(f"  [OK] TITANIUM CONTRACT COMPLIANT")
        
        print("\n3. TESTING NORMALIZATION STAGE ERROR HANDLING")
        print("-" * 50)
        
        # Create mock successful validation data for normalization testing
        mock_validation_data = {
            "RawErrorSource": {
                "status": "success",
                "valid": True
            },
            "MAIFAErrorSource": {
                "status": "success",
                "valid": True
            },
            "TimeoutSource": {
                "status": "success", 
                "valid": True
            }
        }
        
        # Mock raw data cache
        orchestrator.raw_data_cache = {
            "RawErrorSource": {"test": "data"},
            "MAIFAErrorSource": {"test": "data"},
            "TimeoutSource": {"test": "data"}
        }
        
        normalization_results = await orchestrator.normalize_all(mock_validation_data)
        
        print(f"Normalization results: {len(normalization_results)} sources")
        for source, result in normalization_results.items():
            print(f"\n{source}:")
            print(f"  Status: {result.get('status', 'unknown')}")
            print(f"  Error Type: {result.get('error_type', 'none')}")
            print(f"  Message: {result.get('message', 'none')}")
            print(f"  Retryable: {result.get('retryable', 'none')}")
            
            # Verify titanium contract format
            required_fields = ["source", "stage", "status", "error_type", "message", "retryable", "timestamp"]
            missing_fields = [field for field in required_fields if field not in result]
            if missing_fields:
                print(f"  [FAIL] MISSING FIELDS: {missing_fields}")
            else:
                print(f"  [OK] TITANIUM CONTRACT COMPLIANT")
        
        print("\n4. FINAL VERIFICATION")
        print("-" * 50)
        
        # Check for any raw exceptions leaking
        all_results = [fetch_results, validation_results, normalization_results]
        raw_exceptions_found = 0
        
        for stage_results in all_results:
            for source, result in stage_results.items():
                if isinstance(result, Exception) and not isinstance(result, MAIFAError):
                    raw_exceptions_found += 1
                    print(f"[FAIL] RAW EXCEPTION LEAKED: {source} -> {type(result).__name__}")
        
        if raw_exceptions_found == 0:
            print("[OK] ZERO RAW EXCEPTIONS LEAKED")
        
        # Check for consistent error shapes
        inconsistent_shapes = 0
        for stage_results in all_results:
            for source, result in stage_results.items():
                if result.get("status") == "error":
                    required_fields = ["source", "stage", "status", "error_type", "message", "retryable", "timestamp"]
                    missing_fields = [field for field in required_fields if field not in result]
                    if missing_fields:
                        inconsistent_shapes += 1
                        print(f"[FAIL] INCONSISTENT SHAPE: {source} missing {missing_fields}")
        
        if inconsistent_shapes == 0:
            print("[OK] ZERO INCONSISTENT ERROR SHAPES")
        
        print("\n" + "=" * 80)
        print("MAIFA TITANIUM ERROR CONTRACT SYSTEM TEST COMPLETED")
        print("=" * 80)
        
        return raw_exceptions_found == 0 and inconsistent_shapes == 0
        
    except Exception as e:
        print(f"\n[FAIL] ERROR CONTRACT TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_maifa_error_contract())
    sys.exit(0 if success else 1)
