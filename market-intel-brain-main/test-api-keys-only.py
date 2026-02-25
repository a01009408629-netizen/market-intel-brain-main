#!/usr/bin/env python3
"""
Test API keys only without complex imports
"""

import os
import sys
from pathlib import Path

def test_api_keys():
    """Test that API keys are loaded correctly"""
    
    print("Market Intel Brain - API Keys Test")
    print("=" * 40)
    
    # Load API keys from config
    config_file = Path("api-keys-config.txt")
    
    if not config_file.exists():
        print("ERROR: api-keys-config.txt not found!")
        return False
    
    # Read and check keys
    api_keys = {}
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                api_keys[key] = value
                os.environ[key] = value
    
    # Check critical keys
    critical_keys = [
        'FRED_API_KEY',
        'ALPHAVANTAGE_API_KEY',
        'FINNHUB_API_KEY',
        'TWITTER_DATA_API_KEY',
        'MARKETSTACK_API_KEY',
        'FINANCIALMODELING_API_KEY'
    ]
    
    print("Checking API Keys:")
    all_present = True
    
    for key in critical_keys:
        if key in api_keys and api_keys[key]:
            print(f"OK: {key}")
        else:
            print(f"ERROR: {key} missing or empty")
            all_present = False
    
    # Test environment variables
    print("\nTesting Environment Variables:")
    for key in critical_keys:
        env_value = os.environ.get(key)
        if env_value:
            print(f"OK: {key} = {env_value[:10]}...")
        else:
            print(f"ERROR: {key} not in environment")
            all_present = False
    
    if all_present:
        print("\nSUCCESS: All API keys are configured!")
        print("Your Market Intel Brain is ready for data sources.")
        return True
    else:
        print("\nERROR: Some API keys are missing!")
        return False

def test_simple_request():
    """Test a simple HTTP request to verify connectivity"""
    
    print("\nTesting Network Connectivity...")
    
    try:
        import urllib.request
        import json
        
        # Test FRED API (simple series info)
        fred_key = os.environ.get('FRED_API_KEY')
        if fred_key:
            url = f"https://api.stlouisfed.org/fred/series?series_id=GDP&api_key={fred_key}&file_type=json"
            
            try:
                with urllib.request.urlopen(url, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    
                    if 'seriess' in data:
                        print("OK: FRED API connection successful")
                        return True
                    else:
                        print("ERROR: FRED API response invalid")
                        return False
                        
            except Exception as e:
                print(f"ERROR: FRED API connection failed: {e}")
                return False
        else:
            print("ERROR: FRED API key not found")
            return False
            
    except ImportError:
        print("WARNING: Cannot test network - urllib not available")
        return True

def main():
    """Main test function"""
    
    # Test 1: API Keys
    if not test_api_keys():
        return False
    
    # Test 2: Network Connectivity
    if not test_simple_request():
        return False
    
    print("\n" + "=" * 40)
    print("SUCCESS: All tests passed!")
    print("Your Market Intel Brain is ready!")
    print("\nNext steps:")
    print("1. Run: python simple_api_server.py")
    print("2. Visit: http://localhost:8000/health")
    print("3. Check: http://localhost:8000/docs")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
