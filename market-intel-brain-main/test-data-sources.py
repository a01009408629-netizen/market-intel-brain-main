#!/usr/bin/env python3
"""
🧪 Market Intel Brain - Data Sources Test Script
Test all configured data providers and API connections
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add current directory to Python path
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

async def test_fred_api():
    """Test FRED API connection"""
    print("🏛️ Testing FRED API...")
    
    try:
        from us_economic_providers import FREDProvider
        
        provider = FREDProvider()
        connected = await provider.connect()
        
        if connected:
            # Test getting GDP data
            data = await provider.get_data("GDP")
            print(f"✅ FRED: Connected - Retrieved {len(data)} GDP records")
            return True
        else:
            print("❌ FRED: Connection failed")
            return False
            
    except Exception as e:
        print(f"❌ FRED Error: {e}")
        return False

async def test_alpha_vantage():
    """Test Alpha Vantage API connection"""
    print("📈 Testing Alpha Vantage API...")
    
    try:
        from authenticated_providers import AlphaVantageProvider
        
        provider = AlphaVantageProvider()
        connected = await provider.connect()
        
        if connected:
            # Test getting stock quote
            data = await provider.get_data("AAPL")
            print(f"✅ Alpha Vantage: Connected - Retrieved AAPL data")
            return True
        else:
            print("❌ Alpha Vantage: Connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Alpha Vantage Error: {e}")
        return False

async def test_finnhub():
    """Test Finnhub API connection"""
    print("📊 Testing Finnhub API...")
    
    try:
        from authenticated_providers import FinnhubProvider
        
        provider = FinnhubProvider()
        connected = await provider.connect()
        
        if connected:
            # Test getting stock quote
            data = await provider.get_data("AAPL")
            print(f"✅ Finnhub: Connected - Retrieved AAPL data")
            return True
        else:
            print("❌ Finnhub: Connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Finnhub Error: {e}")
        return False

async def test_marketstack():
    """Test MarketStack API connection"""
    print("📋 Testing MarketStack API...")
    
    try:
        from authenticated_providers import MarketStackProvider
        
        provider = MarketStackProvider()
        connected = await provider.connect()
        
        if connected:
            # Test getting stock data
            data = await provider.get_data("AAPL")
            print(f"✅ MarketStack: Connected - Retrieved AAPL data")
            return True
        else:
            print("❌ MarketStack: Connection failed")
            return False
            
    except Exception as e:
        print(f"❌ MarketStack Error: {e}")
        return False

async def test_financial_modeling():
    """Test Financial Modeling Prep API connection"""
    print("💰 Testing Financial Modeling Prep API...")
    
    try:
        from authenticated_providers import FinancialModelingProvider
        
        provider = FinancialModelingProvider()
        connected = await provider.connect()
        
        if connected:
            # Test getting stock data
            data = await provider.get_data("AAPL")
            print(f"✅ Financial Modeling: Connected - Retrieved AAPL data")
            return True
        else:
            print("❌ Financial Modeling: Connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Financial Modeling Error: {e}")
        return False

async def test_news_sources():
    """Test news data sources"""
    print("📰 Testing News Sources...")
    
    try:
        from us_economic_providers import ReutersProvider, APNewsProvider
        
        # Test Reuters
        reuters = ReutersProvider()
        reuters_data = await reuters.get_data()
        print(f"✅ Reuters: Retrieved {len(reuters_data)} news items")
        
        # Test AP News
        ap_news = APNewsProvider()
        ap_data = await ap_news.get_data()
        print(f"✅ AP News: Retrieved {len(ap_data)} news items")
        
        return True
        
    except Exception as e:
        print(f"❌ News Sources Error: {e}")
        return False

async def test_data_ingestion_service():
    """Test the main data ingestion service"""
    print("🔄 Testing Data Ingestion Service...")
    
    try:
        from services.data_ingestion import get_orchestrator
        
        orchestrator = get_orchestrator()
        await orchestrator.initialize()
        
        print("✅ Data Ingestion Service: Initialized successfully")
        
        # Test getting some data
        market_data = await orchestrator.get_market_data("AAPL")
        news_data = await orchestrator.get_news_data()
        
        print(f"📊 Market Data: {len(market_data)} records")
        print(f"📰 News Data: {len(news_data)} records")
        
        return True
        
    except Exception as e:
        print(f"❌ Data Ingestion Service Error: {e}")
        return False

async def main():
    """Main test function"""
    
    print("🧪 Market Intel Brain - Data Sources Test")
    print("=" * 60)
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load environment variables
    try:
        from setup_api_keys import setup_environment
        setup_environment()
        print("🔑 Environment variables loaded")
    except Exception as e:
        print(f"⚠️ Warning: Could not load environment: {e}")
    
    print()
    
    # Test all data sources
    tests = [
        ("FRED API", test_fred_api),
        ("Alpha Vantage", test_alpha_vantage),
        ("Finnhub", test_finnhub),
        ("MarketStack", test_marketstack),
        ("Financial Modeling", test_financial_modeling),
        ("News Sources", test_news_sources),
        ("Data Ingestion Service", test_data_ingestion_service),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}: Critical error - {e}")
            results.append((test_name, False))
        print()
    
    # Summary
    print("=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print()
    print(f"📈 Total: {passed}/{total} tests passed")
    print(f"🎯 Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 All tests passed! Your Market Intel Brain is ready!")
        print("🚀 You can now start the main application:")
        print("   python simple_api_server.py")
    else:
        print(f"\n⚠️ {total-passed} tests failed. Check your API keys and network connection.")
        print("🔧 Run the setup script again:")
        print("   python setup-api-keys.py")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
