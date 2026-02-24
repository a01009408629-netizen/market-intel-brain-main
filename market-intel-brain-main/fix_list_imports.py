import os
import re

# List of all sources
sources = [
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

base_path = "services/data_ingestion/sources"

for source in sources:
    source_path = os.path.join(base_path, source)
    
    if os.path.exists(source_path):
        # Process all Python files in source directory
        for file in os.listdir(source_path):
            if file.endswith('.py') and file != '__pycache__':
                file_path = os.path.join(source_path, file)
                
                # Read file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if List is used but not imported
                if 'List[' in content and 'from typing import' in content:
                    if 'List' not in content.split('from typing import')[1].split('\n')[0]:
                        # Add List to existing typing import
                        content = re.sub(
                            r'from typing import ([^\n]+)',
                            lambda m: f'from typing import List, {m.group(1).strip()}',
                            content
                        )
                        
                        # Write back
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        print(f"Fixed List import in {source}/{file}")
                    
print("All List imports fixed!")
