import os

# List of all sources that need register function fix
sources = [
    "AlphaVantage",
    "NewsCatcherAPI",
    "GoogleNewsScraper", 
    "EconDB",
    "TradingEconomics",
    "MarketStack",
    "FinMind",
    "TwelveData",
    "Finnhub",
    "FinancialModelingPrep",
    "EuroStatFeeds",
    "IMFJsonFeeds"
]

base_path = "services/data_ingestion/sources"

for source in sources:
    init_file = os.path.join(base_path, source, "__init__.py")
    
    if os.path.exists(init_file):
        # Read current content
        with open(init_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace function name to just register()
        content = content.replace(f"async def register_{source.lower().replace(' ', '_')}():", "async def register():")
        
        # Write back
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Fixed register() in {source}")
    else:
        print(f"Missing {source}")

print("All register functions fixed!")
