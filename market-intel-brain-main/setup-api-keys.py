#!/usr/bin/env python3
"""
🚀 Market Intel Brain - API Keys Setup Script
Configure all API providers with your keys
"""

import os
import sys
from pathlib import Path

def setup_environment():
    """Setup environment variables from API keys config"""
    
    # Read API keys from config file
    config_file = Path("api-keys-config.txt")
    
    if not config_file.exists():
        print("Error: api-keys-config.txt not found!")
        print("Please make sure the file exists with your API keys.")
        return False
    
    # Read and parse config
    env_vars = {}
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
    
    # Set environment variables
    print("Setting up API keys...")
    
    # Critical API Keys
    critical_keys = [
        'FRED_API_KEY',
        'ALPHAVANTAGE_API_KEY', 
        'FINNHUB_API_KEY',
        'TWITTER_DATA_API_KEY',
        'MARKETSTACK_API_KEY',
        'FINANCIALMODELING_API_KEY'
    ]
    
    for key in critical_keys:
        if key in env_vars:
            os.environ[key] = env_vars[key]
            print(f"OK: {key}: Set")
        else:
            print(f"ERROR: {key}: Not found in config")
    
    # Application settings
    app_settings = [
        'REDIS_URL',
        'APP_NAME',
        'ENVIRONMENT',
        'DATABASE_URL'
    ]
    
    for key in app_settings:
        if key in env_vars:
            os.environ[key] = env_vars[key]
            print(f"OK: {key}: Set")
    
    print("\nEnvironment setup complete!")
    return True

def test_api_connections():
    """Test all API connections"""
    
    print("\nTesting API connections...")
    
    # Test Alpha Vantage
    try:
        from authenticated_providers import AlphaVantageProvider
        import asyncio
        
        async def test_alpha_vantage():
            provider = AlphaVantageProvider()
            result = await provider.connect()
            print(f"Alpha Vantage: {'OK Connected' if result else 'ERROR Failed'}")
            return result
        
        av_result = asyncio.run(test_alpha_vantage())
    except Exception as e:
        print(f"ERROR Alpha Vantage Error: {e}")
        av_result = False
    
    # Test FRED
    try:
        from us_economic_providers import FREDProvider
        
        async def test_fred():
            provider = FREDProvider()
            result = await provider.connect()
            print(f"FRED: {'OK Connected' if result else 'ERROR Failed'}")
            return result
        
        fred_result = asyncio.run(test_fred())
    except Exception as e:
        print(f"ERROR FRED Error: {e}")
        fred_result = False
    
    # Test Finnhub
    try:
        from authenticated_providers import FinnhubProvider
        
        async def test_finnhub():
            provider = FinnhubProvider()
            result = await provider.connect()
            print(f"Finnhub: {'OK Connected' if result else 'ERROR Failed'}")
            return result
        
        finnhub_result = asyncio.run(test_finnhub())
    except Exception as e:
        print(f"ERROR Finnhub Error: {e}")
        finnhub_result = False
    
    # Summary
    total_tests = 3
    passed = sum([av_result, fred_result, finnhub_result])
    
    print(f"\nTest Results: {passed}/{total_tests} APIs working")
    
    if passed == total_tests:
        print("SUCCESS: All APIs are working! Ready for data ingestion.")
    else:
        print("WARNING: Some APIs failed. Check your keys and network connection.")
    
    return passed == total_tests

def create_env_file():
    """Create .env file from config"""
    
    print("\nCreating .env file...")
    
    config_file = Path("api-keys-config.txt")
    env_file = Path(".env")
    
    if not config_file.exists():
        print("ERROR: api-keys-config.txt not found!")
        return False
    
    # Read config and create .env
    with open(config_file, 'r') as f:
        content = f.read()
    
    # Remove comments and empty lines
    env_content = []
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            env_content.append(line)
    
    # Write to .env file
    with open(env_file, 'w') as f:
        f.write('\n'.join(env_content))
    
    print("SUCCESS: .env file created successfully!")
    print("WARNING: Make sure .env is in your .gitignore file!")
    
    return True

def main():
    """Main setup function"""
    
    print("Market Intel Brain - API Keys Setup")
    print("=" * 50)
    
    # Step 1: Setup environment
    if not setup_environment():
        print("ERROR: Environment setup failed!")
        return False
    
    # Step 2: Create .env file
    if not create_env_file():
        print("ERROR: .env file creation failed!")
        return False
    
    # Step 3: Test API connections
    if not test_api_connections():
        print("ERROR: Some API connections failed!")
        return False
    
    print("\nSUCCESS: Setup completed successfully!")
    print("Your Market Intel Brain is now ready with real data sources!")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
