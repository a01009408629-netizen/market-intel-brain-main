import os

# Manual mapping of function names to replace
function_mappings = {
    "NewsCatcherAPI": "register_news_catcher_api",
    "GoogleNewsScraper": "register_google_news_scraper", 
    "EconDB": "register_econ_db",
    "TradingEconomics": "register_trading_economics",
    "MarketStack": "register_market_stack",
    "FinMind": "register_fin_mind",
    "TwelveData": "register_twelve_data",
    "Finnhub": "register_finnhub",
    "FinancialModelingPrep": "register_financial_modeling_prep",
    "EuroStatFeeds": "register_euro_stat_feeds",
    "IMFJsonFeeds": "register_imf_json_feeds"
}

base_path = "services/data_ingestion/sources"

for source, old_function in function_mappings.items():
    init_file = os.path.join(base_path, source, "__init__.py")
    
    if os.path.exists(init_file):
        # Read current content
        with open(init_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace function name to just register()
        content = content.replace(f"async def {old_function}():", "async def register():")
        
        # Write back
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Fixed register() in {source} (was {old_function})")
    else:
        print(f"Missing {source}")

print("All function names fixed!")
