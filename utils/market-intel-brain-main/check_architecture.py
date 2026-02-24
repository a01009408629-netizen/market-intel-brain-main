import os
import importlib

BASE = "services.data_ingestion.sources"

SOURCES = [
    "YahooFinance",
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

REQUIRED_FILES = ["fetcher.py", "parser.py", "validator.py", "normalizer.py", "__init__.py"]

errors = []

for src in SOURCES:
    path = f"services/data_ingestion/sources/{src}"
    
    # Check folder exists
    if not os.path.isdir(path):
        errors.append(f"[MISSING FOLDER] {src}")
        continue
    
    # Check files
    for f in REQUIRED_FILES:
        if not os.path.isfile(os.path.join(path, f)):
            errors.append(f"[MISSING FILE] {src}/{f}")
    
    # Check import + register()
    try:
        module = importlib.import_module(f"{BASE}.{src}")
        if not hasattr(module, "register"):
            errors.append(f"[MISSING register()] {src}")
    except Exception as e:
        errors.append(f"[IMPORT ERROR] {src}: {e}")

if errors:
    print("\n[ERROR] ARCHITECTURE ERRORS FOUND:\n")
    for e in errors:
        print(" -", e)
else:
    print("[SUCCESS] B-FAST-ULTRA CHECK PASSED - ALL 13 SOURCES ARE ARCHITECTURALLY PERFECT.")
