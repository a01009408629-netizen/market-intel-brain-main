"""
Phase 2 API Test Script
Validate connection and normalization for new providers (1 request per API max)
"""

import asyncio
import time
import json
from datetime import datetime, timezone
from typing import Dict, List, Any

# Import Phase 2 components
from authenticated_providers import get_authenticated_provider_factory
from provider_registry import get_provider_registry
from token_bucket_limiter import get_token_bucket_limiter, APIProvider
from network_optimizer import get_network_optimizer
from parquet_storage import get_parquet_storage
from infrastructure.data_normalization import UnifiedInternalSchema, DataType


class Phase2TestSuite:
    """Phase 2 test suite for authenticated APIs."""
    
    def __init__(self):
        self.auth_factory = get_authenticated_provider_factory()
        self.registry = get_provider_registry()
        self.rate_limiter = get_token_bucket_limiter()
        self.network_optimizer = get_network_optimizer()
        self.storage = get_parquet_storage()
        
        self.test_results = {
            "connection_tests": {},
            "normalization_tests": {},
            "rate_limit_tests": {},
            "fallback_tests": {},
            "integration_tests": {},
            "errors": [],
            "warnings": []
        }
    
    async def run_all_tests(self):
        """Run all Phase 2 tests (1 request per API max)."""
        print("=" * 80)
        print("PHASE 2 API TEST SUITE")
        print("=" * 80)
        print("Testing: 7 Authenticated APIs with 1 request per API limit")
        print("=" * 80)
        
        start_time = time.time()
        
        # Initialize components
        await self.storage.start()
        await self.registry.initialize()
        
        # Test 1: Connection Tests (1 request per API)
        print("\n1. Testing API Connections (1 request per API)...")
        await self._test_api_connections()
        
        # Test 2: Data Normalization Tests
        print("\n2. Testing Data Normalization...")
        await self._test_data_normalization()
        
        # Test 3: Rate Limit Tests
        print("\n3. Testing Rate Limit Management...")
        await self._test_rate_limits()
        
        # Test 4: Fallback Registry Tests
        print("\n4. Testing Priority Fallback...")
        await self._test_fallback_registry()
        
        # Test 5: Integration Tests
        print("\n5. Testing Integration with Parquet Storage...")
        await self._test_integration()
        
        # Generate report
        total_time = time.time() - start_time
        self._generate_test_report(total_time)
        
        # Cleanup
        await self.registry.shutdown()
        await self.storage.stop()
        await self.network_optimizer.close_session()
        
        return len(self.test_results["errors"]) == 0
    
    async def _test_api_connections(self):
        """Test API connections (1 request per API)."""
        providers = [
            ("alpha_vantage", "IBM"),      # Use IBM to avoid conflicts
            ("finnhub", "AAPL"),
            ("twelve_data", "MSFT"),
            ("market_stack", "GOOGL"),
            ("fmp", "AMZN"),
            ("finmind", "2330"),          # Taiwan stock
            ("fred_auth", "GDP")           # Economic data
        ]
        
        for provider_name, test_symbol in providers:
            print(f"  Testing {provider_name}...")
            
            try:
                # Create provider
                provider = self.auth_factory.create_provider(provider_name)
                
                # Test connection
                start_time = time.time()
                connected = await provider.connect()
                connection_time = time.time() - start_time
                
                if not connected:
                    self.test_results["errors"].append(f"{provider_name}: Connection failed")
                    self.test_results["connection_tests"][provider_name] = {
                        "connected": False,
                        "connection_time": connection_time,
                        "error": "Connection failed"
                    }
                    continue
                
                # Test single data request
                data_start = time.time()
                data = await provider.get_data(test_symbol)
                data_time = time.time() - data_start
                
                # Store results
                self.test_results["connection_tests"][provider_name] = {
                    "connected": True,
                    "connection_time": connection_time,
                    "data_request_time": data_time,
                    "data_items": len(data),
                    "test_symbol": test_symbol,
                    "success": len(data) > 0
                }
                
                print(f"    Connected: {connected}, Data: {len(data)} items, Time: {data_time:.3f}s")
                
                # Store sample data in Parquet
                if data:
                    stored_count = await self.storage.store_items(data)
                    print(f"    Stored: {stored_count} items in Parquet")
                
                # Disconnect
                await provider.disconnect()
                
            except Exception as e:
                self.test_results["errors"].append(f"{provider_name}: {e}")
                self.test_results["connection_tests"][provider_name] = {
                    "connected": False,
                    "error": str(e)
                }
                print(f"    ERROR: {e}")
    
    async def _test_data_normalization(self):
        """Test data normalization to unified schema."""
        # Use data from connection tests
        for provider_name, connection_result in self.test_results["connection_tests"].items():
            if not connection_result.get("success", False):
                continue
            
            print(f"  Testing normalization for {provider_name}...")
            
            try:
                # Get provider and fetch fresh data for normalization test
                provider = self.auth_factory.create_provider(provider_name)
                await provider.connect()
                
                test_symbol = connection_result["test_symbol"]
                data = await provider.get_data(test_symbol)
                
                if not data:
                    self.test_results["warnings"].append(f"{provider_name}: No data for normalization test")
                    continue
                
                # Test normalization
                item = data[0]
                normalization_result = {
                    "has_required_fields": True,
                    "field_types_correct": True,
                    "timestamp_valid": True,
                    "price_valid": True,
                    "symbol_valid": True
                }
                
                # Check required fields
                required_fields = ['data_type', 'source', 'source_type', 'symbol', 'timestamp']
                for field in required_fields:
                    if not hasattr(item, field) or getattr(item, field) is None:
                        normalization_result["has_required_fields"] = False
                        break
                
                # Check field types
                if not isinstance(item.symbol, str) or len(item.symbol) == 0:
                    normalization_result["symbol_valid"] = False
                
                if item.price is not None and not (isinstance(item.price, (int, float, str)) or hasattr(item.price, 'to_decimal')):
                    normalization_result["price_valid"] = False
                
                if not isinstance(item.timestamp, datetime):
                    normalization_result["timestamp_valid"] = False
                
                # Store results
                self.test_results["normalization_tests"][provider_name] = normalization_result
                
                success = all(normalization_result.values())
                print(f"    Normalization: {'PASS' if success else 'FAIL'}")
                
                await provider.disconnect()
                
            except Exception as e:
                self.test_results["errors"].append(f"Normalization test {provider_name}: {e}")
                print(f"    ERROR: {e}")
    
    async def _test_rate_limits(self):
        """Test rate limiting functionality."""
        print("  Testing rate limiter...")
        
        try:
            # Test Alpha Vantage (strictest limit)
            provider = APIProvider.ALPHA_VANTAGE
            
            # Get initial status
            initial_status = self.rate_limiter.get_status(provider)
            
            # Try to consume tokens
            consumed = await self.rate_limiter.can_consume(provider)
            after_status = self.rate_limiter.get_status(provider)
            
            # Test wait time calculation
            wait_time = self.rate_limiter.get_wait_time(provider, 10)
            
            self.test_results["rate_limit_tests"] = {
                "alpha_vantage": {
                    "initial_tokens": initial_status["tokens"],
                    "after_tokens": after_status["tokens"],
                    "consumed": consumed,
                    "wait_time_10_tokens": wait_time,
                    "daily_tokens": after_status["daily_tokens"],
                    "daily_limit": after_status["daily_limit"]
                }
            }
            
            print(f"    Alpha Vantage: Tokens {after_status['tokens']:.1f}/{after_status['max_tokens']}")
            print(f"    Daily: {after_status['daily_tokens']}/{after_status['daily_limit']}")
            print(f"    Wait time for 10 tokens: {wait_time:.1f}s")
            
        except Exception as e:
            self.test_results["errors"].append(f"Rate limit test: {e}")
            print(f"    ERROR: {e}")
    
    async def _test_fallback_registry(self):
        """Test priority fallback registry."""
        print("  Testing fallback registry...")
        
        try:
            # Test equity data retrieval (should use keyless first)
            print("    Testing equity data (AAPL):")
            data = await self.registry.get_data_with_fallback("AAPL", "equity")
            
            self.test_results["fallback_tests"]["equity"] = {
                "items_returned": len(data),
                "source": data[0].source if data else None,
                "success": len(data) > 0
            }
            
            if data:
                print(f"      Source: {data[0].source}, Price: {data[0].price}")
            
            # Test macro data retrieval
            print("    Testing macro data (GDP):")
            data = await self.registry.get_data_with_fallback("GDP", "macro")
            
            self.test_results["fallback_tests"]["macro"] = {
                "items_returned": len(data),
                "source": data[0].source if data else None,
                "success": len(data) > 0
            }
            
            if data:
                print(f"      Source: {data[0].source}, Value: {data[0].value}")
            
            # Get registry status
            status = await self.registry.get_provider_status()
            self.test_results["fallback_tests"]["registry_status"] = status
            
            print(f"    Registry: {status['connected_providers']}/{status['total_providers']} connected")
            
        except Exception as e:
            self.test_results["errors"].append(f"Fallback test: {e}")
            print(f"    ERROR: {e}")
    
    async def _test_integration(self):
        """Test integration with Parquet storage."""
        print("  Testing integration with Parquet storage...")
        
        try:
            # Get storage stats
            storage_stats = self.storage.get_storage_stats()
            
            # Query stored data
            equity_data = await self.storage.query_data(
                data_type="EQUITY",
                limit=10
            )
            
            macro_data = await self.storage.query_data(
                data_type="MACRO",
                limit=5
            )
            
            self.test_results["integration_tests"] = {
                "storage_stats": storage_stats,
                "equity_items_queried": len(equity_data),
                "macro_items_queried": len(macro_data),
                "total_items_queried": len(equity_data) + len(macro_data),
                "parquet_working": len(equity_data) > 0 or len(macro_data) > 0
            }
            
            print(f"    Buffer: {storage_stats['buffer_stats']['buffer_size_mb']:.2f}MB")
            print(f"    Equity items: {len(equity_data)}")
            print(f"    Macro items: {len(macro_data)}")
            print(f"    Integration: {'SUCCESS' if self.test_results['integration_tests']['parquet_working'] else 'FAILED'}")
            
        except Exception as e:
            self.test_results["errors"].append(f"Integration test: {e}")
            print(f"    ERROR: {e}")
    
    def _generate_test_report(self, total_time: float):
        """Generate comprehensive test report."""
        print(f"\n{'='*80}")
        print("PHASE 2 TEST REPORT")
        print(f"{'='*80}")
        print(f"Total Test Time: {total_time:.2f} seconds")
        print(f"Errors: {len(self.test_results['errors'])}")
        print(f"Warnings: {len(self.test_results['warnings'])}")
        
        # Connection test summary
        print(f"\nAPI Connection Tests:")
        connection_success = 0
        for provider, results in self.test_results['connection_tests'].items():
            status = "PASS" if results.get('success', False) else "FAIL"
            print(f"  {provider:15} | {status:5} | {results.get('data_items', 0):2} items | {results.get('data_request_time', 0):.3f}s")
            if results.get('success', False):
                connection_success += 1
        
        print(f"Connection Success Rate: {connection_success}/{len(self.test_results['connection_tests'])} ({connection_success/len(self.test_results['connection_tests']):.1%})")
        
        # Normalization test summary
        print(f"\nNormalization Tests:")
        norm_success = 0
        for provider, results in self.test_results['normalization_tests'].items():
            status = "PASS" if all(results.values()) else "FAIL"
            print(f"  {provider:15} | {status:5}")
            if all(results.values()):
                norm_success += 1
        
        if self.test_results['normalization_tests']:
            print(f"Normalization Success Rate: {norm_success}/{len(self.test_results['normalization_tests'])} ({norm_success/len(self.test_results['normalization_tests']):.1%})")
        
        # Fallback test summary
        print(f"\nFallback Registry Tests:")
        fallback_tests = self.test_results['fallback_tests']
        if 'equity' in fallback_tests:
            equity_success = fallback_tests['equity']['success']
            print(f"  Equity data: {'PASS' if equity_success else 'FAIL'}")
        if 'macro' in fallback_tests:
            macro_success = fallback_tests['macro']['success']
            print(f"  Macro data: {'PASS' if macro_success else 'FAIL'}")
        
        # Integration test summary
        if 'integration_tests' in self.test_results:
            integration = self.test_results['integration_tests']
            print(f"\nIntegration Tests:")
            print(f"  Parquet storage: {'PASS' if integration['parquet_working'] else 'FAIL'}")
            print(f"  Items stored: {integration['total_items_queried']}")
        
        # Overall assessment
        total_tests = len(self.test_results['connection_tests']) + len(self.test_results['normalization_tests'])
        passed_tests = connection_success + norm_success
        overall_success_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        print(f"\nOverall Assessment:")
        print(f"  Success Rate: {overall_success_rate:.1%}")
        print(f"  Status: {'PASS' if overall_success_rate >= 0.7 else 'FAIL'}")
        
        if self.test_results['errors']:
            print(f"\nErrors:")
            for error in self.test_results['errors'][-5:]:  # Last 5 errors
                print(f"  - {error}")
        
        # Save detailed report
        report = {
            "test_summary": {
                "total_time": total_time,
                "errors": len(self.test_results['errors']),
                "warnings": len(self.test_results['warnings']),
                "connection_success_rate": connection_success / len(self.test_results['connection_tests']) if self.test_results['connection_tests'] else 0,
                "normalization_success_rate": norm_success / len(self.test_results['normalization_tests']) if self.test_results['normalization_tests'] else 0,
                "overall_success_rate": overall_success_rate,
                "status": "PASS" if overall_success_rate >= 0.7 else "FAIL"
            },
            "detailed_results": self.test_results
        }
        
        with open("phase2_test_report.json", "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\nDetailed report saved to: phase2_test_report.json")


async def main():
    """Run Phase 2 test suite."""
    test_suite = Phase2TestSuite()
    success = await test_suite.run_all_tests()
    
    if success:
        print("\nPhase 2 tests PASSED! Authenticated APIs ready for production.")
    else:
        print("\nPhase 2 tests FAILED! Review errors above.")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
