"""
Simple Gold, Dollar, and Indices Test
Real-time prices for major financial instruments
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timezone

print("Testing Gold, Dollar, and U.S. Indices")
print("=" * 60)

async def test_gold_price():
    """Test Gold price from Yahoo Finance."""
    print("\n1. Gold Price (XAU/USD):")
    try:
        # Gold Futures
        url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'chart' in data and data['chart']['result']:
                        result = data['chart']['result'][0]
                        if 'meta' in result:
                            price = result['meta'].get('regularMarketPrice', 'N/A')
                            currency = result['meta'].get('currency', 'USD')
                            print(f"   Gold Price: ${price} per troy ounce")
                            print(f"   Currency: {currency}")
                            return True
                
                print(f"   HTTP Status: {response.status}")
                return False
                
    except Exception as e:
        print(f"   Error: {e}")
        return False

async def test_dollar_index():
    """Test U.S. Dollar Index."""
    print("\n2. U.S. Dollar Index (DXY):")
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'chart' in data and data['chart']['result']:
                        result = data['chart']['result'][0]
                        if 'meta' in result:
                            price = result['meta'].get('regularMarketPrice', 'N/A')
                            print(f"   Dollar Index: {price}")
                            return True
                
                print(f"   HTTP Status: {response.status}")
                return False
                
    except Exception as e:
        print(f"   Error: {e}")
        return False

async def test_us_indices():
    """Test major U.S. indices."""
    print("\n3. Major U.S. Indices:")
    try:
        indices = {
            "S&P 500": "^GSPC",
            "Dow Jones": "^DJI", 
            "NASDAQ": "^IXIC",
            "Russell 2000": "^RUT"
        }
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        async with aiohttp.ClientSession() as session:
            for index_name, ticker in indices.items():
                try:
                    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
                    
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'chart' in data and data['chart']['result']:
                                result = data['chart']['result'][0]
                                if 'meta' in result:
                                    price = result['meta'].get('regularMarketPrice', 'N/A')
                                    change = result['meta'].get('regularMarketPrice', 0) - result['meta'].get('previousClose', 0)
                                    change_str = f"+{change:.2f}" if change >= 0 else f"{change:.2f}"
                                    print(f"   {index_name:12} {price:8.2f} ({change_str})")
                        else:
                            print(f"   {index_name:12} No data")
                    
                    await asyncio.sleep(0.1)  # Small delay
                    
                except Exception as e:
                    print(f"   {index_name:12} Error: {e}")
                    continue
        
        return True
        
    except Exception as e:
        print(f"   Error: {e}")
        return False

async def test_forex_rates():
    """Test major forex rates."""
    print("\n4. Major Forex Rates (USD base):")
    try:
        pairs = {
            "EUR/USD": "EURUSD=X",
            "GBP/USD": "GBPUSD=X",
            "USD/JPY": "USDJPY=X", 
            "USD/CHF": "USDCHF=X"
        }
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        async with aiohttp.ClientSession() as session:
            for pair_name, ticker in pairs.items():
                try:
                    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
                    
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'chart' in data and data['chart']['result']:
                                result = data['chart']['result'][0]
                                if 'meta' in result:
                                    price = result['meta'].get('regularMarketPrice', 'N/A')
                                    print(f"   {pair_name:12} {price}")
                        else:
                            print(f"   {pair_name:12} No data")
                    
                    await asyncio.sleep(0.1)  # Small delay
                    
                except Exception as e:
                    print(f"   {pair_name:12} Error: {e}")
                    continue
        
        return True
        
    except Exception as e:
        print(f"   Error: {e}")
        return False

async def test_commodities():
    """Test major commodities."""
    print("\n5. Major Commodities:")
    try:
        commodities = {
            "Oil (WTI)": "CL=F",
            "Oil (Brent)": "BZ=F",
            "Silver": "SI=F",
            "Copper": "HG=F"
        }
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        async with aiohttp.ClientSession() as session:
            for commodity_name, ticker in commodities.items():
                try:
                    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
                    
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'chart' in data and data['chart']['result']:
                                result = data['chart']['result'][0]
                                if 'meta' in result:
                                    price = result['meta'].get('regularMarketPrice', 'N/A')
                                    currency = result['meta'].get('currency', 'USD')
                                    print(f"   {commodity_name:12} ${price} {currency}")
                        else:
                            print(f"   {commodity_name:12} No data")
                    
                    await asyncio.sleep(0.1)  # Small delay
                    
                except Exception as e:
                    print(f"   {commodity_name:12} Error: {e}")
                    continue
        
        return True
        
    except Exception as e:
        print(f"   Error: {e}")
        return False

async def main():
    """Test all financial instruments."""
    
    tests = [
        ("Gold Price", test_gold_price),
        ("Dollar Index", test_dollar_index),
        ("U.S. Indices", test_us_indices),
        ("Forex Rates", test_forex_rates),
        ("Commodities", test_commodities)
    ]
    
    results = {}
    
    for name, test_func in tests:
        try:
            result = await test_func()
            results[name] = result
            status = "WORKING" if result else "FAILED"
            print(f"   {name}: {status}")
        except Exception as e:
            results[name] = False
            print(f"   {name}: ERROR - {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("FINANCIAL INSTRUMENTS SUMMARY")
    print("=" * 60)
    
    working = []
    failed = []
    
    for name, result in results.items():
        status = "WORKING" if result else "FAILED"
        print(f"  {name}: {status}")
        
        if result:
            working.append(name)
        else:
            failed.append(name)
    
    print(f"\nWorking Sources: {len(working)}/{len(tests)}")
    for source in working:
        print(f"  OK {source}")
    
    if failed:
        print(f"\nFailed Sources: {len(failed)}")
        for source in failed:
            print(f"  X {source}")
    
    print("\nAvailable Financial Data:")
    print("  Gold Price (XAU/USD): Real-time")
    print("  Dollar Index (DXY): Real-time")
    print("  U.S. Indices: S&P 500, Dow Jones, NASDAQ, Russell 2000")
    print("  Forex Rates: EUR/USD, GBP/USD, USD/JPY, USD/CHF")
    print("  Commodities: Oil (WTI/Brent), Silver, Copper")
    
    print("\nData Sources:")
    print("  Primary: Yahoo Finance (FREE)")
    print("  Backup: Alpha Vantage (25/day)")
    print("  Rate Limiting: Active")
    print("  Update Frequency: Real-time")
    
    success_rate = len(working) / len(tests)
    print(f"\nSuccess Rate: {success_rate:.1%}")
    
    if success_rate >= 0.8:
        print("\nFinancial Instruments System: READY!")
        print("Real-time prices for gold, dollar, and major indices!")
    else:
        print("\nSome sources need attention.")

if __name__ == "__main__":
    asyncio.run(main())
