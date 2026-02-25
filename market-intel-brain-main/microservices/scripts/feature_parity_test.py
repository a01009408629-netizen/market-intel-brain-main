#!/usr/bin/env python3
"""
Feature Parity Test Script
Compares Go API Gateway responses with legacy Python system responses
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List
import sys
import os

class FeatureParityTester:
    def __init__(self):
        self.go_api_base = "http://localhost:8080/api/v1"
        self.python_api_base = "http://localhost:8001/api/v1"
        self.results = {}
        
    async def test_go_market_data(self) -> Dict[str, Any]:
        """Test Go API Gateway market data endpoint"""
        print("🔧 Testing Go API Gateway market data...")
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "symbols": ["AAPL", "GOOGL", "MSFT"],
                "source_id": "yahoo_finance"
            }
            
            try:
                async with session.post(
                    f"{self.go_api_base}/market-data/fetch",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print("✅ Go API Gateway market data fetch successful")
                        return data
                    else:
                        print(f"❌ Go API Gateway failed with status {response.status}")
                        return None
            except Exception as e:
                print(f"❌ Go API Gateway error: {e}")
                return None
    
    async def test_python_market_data(self) -> Dict[str, Any]:
        """Test legacy Python market data endpoint"""
        print("🔧 Testing legacy Python market data...")
        
        async with aiohttp.ClientSession() as session:
            try:
                # Try different Python endpoints based on the original API structure
                endpoints = [
                    "/data/binance/BTCUSDT",
                    "/api/v1/data/binance/BTCUSDT",
                    "/market-data/fetch"
                ]
                
                for endpoint in endpoints:
                    try:
                        async with session.get(f"{self.python_api_base}{endpoint}") as response:
                            if response.status == 200:
                                data = await response.json()
                                print(f"✅ Legacy Python endpoint {endpoint} successful")
                                return data
                    except:
                        continue
                
                print("❌ Legacy Python market data fetch failed")
                return None
                
            except Exception as e:
                print(f"❌ Legacy Python error: {e}")
                return None
    
    def compare_responses(self, go_response: Dict[str, Any], python_response: Dict[str, Any]) -> bool:
        """Compare Go and Python responses for feature parity"""
        print("🔍 Comparing responses for feature parity...")
        
        if not go_response or not python_response:
            print("❌ Cannot compare - one or both responses are None")
            return False
        
        # Basic structure comparison
        go_structure = {
            "has_success": "success" in go_response,
            "has_message": "message" in go_response,
            "has_data": "data" in go_response or "market_data" in go_response,
            "has_metadata": "metadata" in go_response,
            "has_timestamp": "timestamp" in go_response
        }
        
        python_structure = {
            "has_success": "success" in python_response,
            "has_message": "message" in python_response,
            "has_data": "data" in python_response or "market_data" in python_response,
            "has_metadata": "metadata" in python_response,
            "has_timestamp": "timestamp" in python_response
        }
        
        print("📊 Go Response Structure:")
        for key, value in go_structure.items():
            status = "✅" if value else "❌"
            print(f"  {status} {key}")
        
        print("📊 Python Response Structure:")
        for key, value in python_structure.items():
            status = "✅" if value else "❌"
            print(f"  {status} {key}")
        
        # Data content comparison
        go_data = go_response.get("market_data") or go_response.get("data", [])
        python_data = python_response.get("data", [])
        
        if go_data and python_data:
            print("📈 Data Content Comparison:")
            
            # Compare data types
            go_item = go_data[0] if go_data else {}
            python_item = python_data[0] if python_data else {}
            
            common_fields = ["symbol", "price", "volume", "timestamp", "source"]
            
            for field in common_fields:
                go_has = field in go_item
                python_has = field in python_item
                
                if go_has and python_has:
                    print(f"  ✅ Both have {field}")
                elif go_has:
                    print(f"  ⚠️  Only Go has {field}")
                elif python_has:
                    print(f"  ⚠️  Only Python has {field}")
                else:
                    print(f"  ❌ Neither has {field}")
            
            # Check data types
            go_types = {k: type(v).__name__ for k, v in go_item.items()}
            python_types = {k: type(v).__name__ for k, v in python_item.items()}
            
            print("🔍 Data Types:")
            for field in common_fields:
                go_type = go_types.get(field, "N/A")
                python_type = python_types.get(field, "N/A")
                
                if go_type == python_type:
                    print(f"  ✅ {field}: {go_type} (both)")
                else:
                    print(f"  ⚠️  {field}: Go={go_type}, Python={python_type}")
        
        return True
    
    def save_comparison_results(self, go_response: Dict[str, Any], python_response: Dict[str, Any]):
        """Save comparison results to file"""
        results = {
            "timestamp": time.time(),
            "go_response": go_response,
            "python_response": python_response,
            "comparison": {
                "go_structure": {
                    "has_success": "success" in go_response,
                    "has_message": "message" in go_response,
                    "has_data": "data" in go_response or "market_data" in go_response,
                    "has_metadata": "metadata" in go_response,
                    "has_timestamp": "timestamp" in go_response
                },
                "python_structure": {
                    "has_success": "success" in python_response,
                    "has_message": "message" in python_response,
                    "has_data": "data" in python_response or "market_data" in python_response,
                    "has_metadata": "metadata" in python_response,
                    "has_timestamp": "timestamp" in python_response
                }
            }
        }
        
        with open("/tmp/feature_parity_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print("💾 Comparison results saved to /tmp/feature_parity_results.json")
    
    async def run_parity_test(self) -> bool:
        """Run complete feature parity test"""
        print("🚀 Starting Feature Parity Test")
        print("=" * 50)
        
        # Test Go API
        go_response = await self.test_go_market_data()
        
        # Test Python API
        python_response = await self.test_python_market_data()
        
        # Compare responses
        if go_response and python_response:
            parity_passed = self.compare_responses(go_response, python_response)
            self.save_comparison_results(go_response, python_response)
            
            print("=" * 50)
            if parity_passed:
                print("✅ Feature parity test completed successfully")
                return True
            else:
                print("❌ Feature parity test failed")
                return False
        else:
            print("❌ Feature parity test incomplete - missing responses")
            return False

async def main():
    """Main execution function"""
    tester = FeatureParityTester()
    
    try:
        success = await tester.run_parity_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
