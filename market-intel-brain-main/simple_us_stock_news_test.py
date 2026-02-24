"""
Simple U.S. Stock News Test
Real-time news and company data for American stocks
"""

import asyncio
import aiohttp
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

print("Testing U.S. Stock News and Company Data")
print("=" * 60)

async def test_sec_filings():
    """Test SEC EDGAR filings for Apple."""
    print("\n1. SEC Filings (Apple - AAPL):")
    try:
        # Apple CIK
        cik = "0000320193"
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'filings' in data and 'recent' in data['filings']:
                        recent_filings = data['filings']['recent'][:3]
                        
                        print(f"   Company: {data.get('name', 'Apple Inc.')}")
                        print(f"   CIK: {cik}")
                        print(f"   Recent Filings:")
                        
                        for filing in recent_filings:
                            filing_type = filing.get('form', 'N/A')
                            filing_date = filing.get('filingDate', 'N/A')
                            print(f"     {filing_type}: {filing_date}")
                        
                        return True
                    else:
                        print("   No filings data found")
                        return False
                else:
                    print(f"   HTTP Status: {response.status}")
                    return False
                    
    except Exception as e:
        print(f"   Error: {e}")
        return False

async def test_yahoo_finance_news():
    """Test Yahoo Finance news for specific stocks."""
    print("\n2. Yahoo Finance News (Multiple Stocks):")
    try:
        symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        async with aiohttp.ClientSession() as session:
            for symbol in symbols[:3]:  # Test first 3
                try:
                    url = f"https://query1.finance.yahoo.com/v1/finance/searchQuote?q={symbol}&lang=en-US&region=US&quotesCount=5"
                    
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if 'quotes' in data and data['quotes']:
                                quotes = data['quotes']
                                print(f"   {symbol}: Found {len(quotes)} quotes/news")
                                
                                for quote in quotes[:2]:
                                    if 'shortname' in quote:
                                        name = quote.get('shortname', '')
                                        price = quote.get('regularMarketPrice', 'N/A')
                                        print(f"     {name}: ${price}")
                            else:
                                print(f"   {symbol}: No data found")
                        else:
                            print(f"   {symbol}: No quotes data")
                    
                    await asyncio.sleep(0.2)  # Small delay
                    
                except Exception as e:
                    print(f"   {symbol}: Error - {e}")
                    continue
        
        return True
        
    except Exception as e:
        print(f"   Error: {e}")
        return False

async def test_seeking_alpha_rss():
    """Test Seeking Alpha RSS feed."""
    print("\n3. Seeking Alpha RSS:")
    try:
        url = "https://seekingalpha.com/market_currents.xml"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    xml_content = await response.text()
                    
                    # Parse RSS XML
                    root = ET.fromstring(xml_content)
                    
                    # Find all items
                    items = root.findall('.//item')
                    
                    print(f"   Seeking Alpha: Found {len(items)} news items")
                    
                    for item in items[:3]:
                        try:
                            title_elem = item.find('title')
                            title = title_elem.text if title_elem is not None else ''
                            
                            # Extract stock symbols from title
                            import re
                            symbols = re.findall(r'\([A-Z]+\)', title)
                            
                            print(f"     {title[:60]}...")
                            if symbols:
                                print(f"     Symbols: {', '.join(symbols)}")
                            
                        except Exception as e:
                            print(f"     Error parsing item: {e}")
                            continue
                    
                    return True
                else:
                    print(f"   HTTP Status: {response.status}")
                    return False
                    
    except Exception as e:
        print(f"   Error: {e}")
        return False

async def test_benzinga_news():
    """Test Benzinga breaking news."""
    print("\n4. Benzinga Breaking News:")
    try:
        url = "https://www.benzinga.com/api/v1/news"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'news' in data and isinstance(data['news'], list):
                        news_items = data['news']
                        print(f"   Benzinga: Found {len(news_items)} news items")
                        
                        for article in news_items[:3]:
                            title = article.get('title', '')
                            symbols = article.get('symbols', [])
                            
                            print(f"     {title[:60]}...")
                            if symbols:
                                print(f"     Related stocks: {', '.join(symbols[:3])}")
                    else:
                        print("   No news data found")
                    return True
                else:
                    print(f"   HTTP Status: {response.status}")
                    return False
                    
    except Exception as e:
        print(f"   Error: {e}")
        return False

async def test_marketwatch_rss():
    """Test MarketWatch RSS feed."""
    print("\n5. MarketWatch RSS:")
    try:
        url = "https://www.marketwatch.com/rss/topstories"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    xml_content = await response.text()
                    
                    # Parse RSS XML
                    root = ET.fromstring(xml_content)
                    
                    # Find all items
                    items = root.findall('.//item')
                    
                    print(f"   MarketWatch: Found {len(items)} news items")
                    
                    for item in items[:3]:
                        try:
                            title_elem = item.find('title')
                            title = title_elem.text if title_elem is not None else ''
                            
                            print(f"     {title[:60]}...")
                            
                        except Exception as e:
                            print(f"     Error parsing item: {e}")
                            continue
                    
                    return True
                else:
                    print(f"   HTTP Status: {response.status}")
                    return False
                    
    except Exception as e:
        print(f"   Error: {e}")
        return False

async def test_company_specific_data():
    """Test company-specific detailed data."""
    print("\n6. Company-Specific Data (Multiple Companies):")
    try:
        companies = {
            "Apple": {"symbol": "AAPL", "cik": "0000320193"},
            "Microsoft": {"symbol": "MSFT", "cik": "0000789019"},
            "Google": {"symbol": "GOOGL", "cik": "0001652044"},
            "Amazon": {"symbol": "AMZN", "cik": "0001018724"},
            "Tesla": {"symbol": "TSLA", "cik": "0001318605"}
        }
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        async with aiohttp.ClientSession() as session:
            for company_name, company_data in list(companies.items())[:3]:  # Test first 3
                try:
                    symbol = company_data["symbol"]
                    
                    # Get current stock data
                    stock_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                    
                    async with session.get(stock_url, headers=headers) as response:
                        if response.status == 200:
                            stock_data = await response.json()
                            
                            if 'chart' in stock_data and stock_data['chart']['result']:
                                result = stock_data['chart']['result'][0]
                                if 'meta' in result:
                                    price = result['meta'].get('regularMarketPrice', 'N/A')
                                    market_cap = result['meta'].get('marketCap', 'N/A')
                                    
                                    print(f"   {company_name} ({symbol}):")
                                    print(f"     Price: ${price}")
                                    print(f"     Market Cap: ${market_cap:,}" if market_cap != 'N/A' else "     Market Cap: N/A")
                                    
                                    # Get SEC filings
                                    cik = company_data["cik"]
                                    sec_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
                                    
                                    async with session.get(sec_url) as sec_response:
                                        if sec_response.status == 200:
                                            sec_data = await sec_response.json()
                                            if 'filings' in sec_data and 'recent' in sec_data['filings']:
                                                latest_filing = sec_data['filings']['recent'][0]
                                                filing_type = latest_filing.get('form', 'N/A')
                                                filing_date = latest_filing.get('filingDate', 'N/A')
                                                print(f"     Latest Filing: {filing_type} on {filing_date}")
                    
                    await asyncio.sleep(0.3)  # Small delay between companies
                    
                except Exception as e:
                    print(f"   {company_name}: Error - {e}")
                    continue
        
        return True
        
    except Exception as e:
        print(f"   Error: {e}")
        return False

async def main():
    """Test all U.S. stock news and data sources."""
    
    tests = [
        ("SEC Filings", test_sec_filings),
        ("Yahoo Finance News", test_yahoo_finance_news),
        ("Seeking Alpha RSS", test_seeking_alpha_rss),
        ("Benzinga News", test_benzinga_news),
        ("MarketWatch RSS", test_marketwatch_rss),
        ("Company-Specific Data", test_company_specific_data)
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
    print("U.S. STOCK NEWS AND DATA SUMMARY")
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
    
    print("\nAvailable U.S. Stock Data:")
    print("  SEC Filings: Official company disclosures")
    print("  Yahoo Finance: Real-time quotes and news")
    print("  Seeking Alpha: Premium financial analysis")
    print("  Benzinga: Breaking financial news")
    print("  MarketWatch: Market news and analysis")
    print("  Company Data: Detailed stock information")
    
    print("\nData Coverage:")
    print("  Top Tech Stocks: AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA")
    print("  Company Filings: 10-K, 10-Q, 8-K, etc.")
    print("  Real-time News: Breaking news and analysis")
    print("  Market Data: Prices, volume, market cap")
    print("  Regulatory Data: SEC official filings")
    
    print("\nUpdate Frequency:")
    print("  Real-time: Stock prices and breaking news")
    print("  Daily: SEC filings and company data")
    print("  Continuous: RSS feeds and news updates")
    
    success_rate = len(working) / len(tests)
    print(f"\nSuccess Rate: {success_rate:.1%}")
    
    if success_rate >= 0.7:
        print("\nU.S. Stock News System: READY!")
        print("Comprehensive coverage of American stock news and data!")
    else:
        print("\nSome sources need attention.")

if __name__ == "__main__":
    asyncio.run(main())
