SMART_TTL = {
    "YahooFinance": 15,              # Prices update fast
    "AlphaVantage": 25,              # Slower free-tier
    "NewsCatcherAPI": 60,            # News doesn't change per second
    "GoogleNewsScraper": 90,         # Scraping slower + rate limit
    "EconDB": 300,                   # Economic data static
    "TradingEconomics": 120,
    "MarketStack": 20,
    "FinMind": 30,
    "TwelveData": 15,
    "Finnhub": 10,                   # Fastest updates
    "FinancialModelingPrep": 20,
    "EuroStatFeeds": 600,            # Static datasets
    "IMFJsonFeeds": 600             # Static datasets
}

import json
with open("services/data_ingestion/smart_ttl.json", "w") as f:
    json.dump(SMART_TTL, f, indent=4)

print("MAIFA Smart TTL Engine created successfully.")
