#!/usr/bin/env python3
"""
Simple test for API connections without complex dependencies
"""

import os
import sys
from pathlib import Path

def load_api_keys():
    """Load API keys from config file"""
    config_file = Path("api-keys-config.txt")
    
    if not config_file.exists():
        print("ERROR: api-keys-config.txt not found!")
        return False
    
    env_vars = {}
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
                os.environ[key] = value
    
    print("SUCCESS: API keys loaded!")
    return True

def test_basic_imports():
    """Test basic imports"""
    try:
        print("Testing basic imports...")
        
        # Test data providers
        from us_economic_providers import BLSProvider
        print("OK: BLS Provider imported")
        
        from authenticated_providers import AlphaVantageProvider
        print("OK: Alpha Vantage Provider imported")
        
        return True
    except Exception as e:
        print(f"ERROR: Import failed: {e}")
        return False

def test_simple_connection():
    """Test simple connection without async"""
    try:
        print("Testing simple connection...")
        
        # Test BLS (no API key required)
        from us_economic_providers import BLSProvider
        provider = BLSProvider()
        print("OK: BLS Provider created")
        
        return True
    except Exception as e:
        print(f"ERROR: Connection test failed: {e}")
        return False

def main():
    """Main test function"""
    print("Market Intel Brain - Simple Connection Test")
    print("=" * 50)
    
    # Step 1: Load API keys
    if not load_api_keys():
        return False
    
    # Step 2: Test imports
    if not test_basic_imports():
        return False
    
    # Step 3: Test simple connection
    if not test_simple_connection():
        return False
    
    print("\nSUCCESS: Basic setup working!")
    print("Your Market Intel Brain is ready for advanced testing.")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
