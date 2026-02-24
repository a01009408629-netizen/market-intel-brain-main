"""
Script to update all 13 sources with MAIFA error wrapping
"""

import os
import re

# List of all 13 sources
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

def update_fetcher(source_name):
    """Update fetcher.py for a specific source"""
    fetcher_path = f"services/data_ingestion/sources/{source_name}/fetcher.py"
    
    if not os.path.exists(fetcher_path):
        print(f"Missing fetcher for {source_name}")
        return False
    
    # Read the file
    with open(fetcher_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add error import if not present
    if "from ...errors import FetchError" not in content:
        # Find the imports section and add our import
        content = re.sub(
            r'(from \.\.\.interfaces import DataFetcher)',
            r'\1\nfrom ...errors import FetchError',
            content
        )
    
    # Replace exception handling in fetch method
    # Pattern to match the except blocks
    old_exception_pattern = r'except Exception as e:\s*\n.*?return\s*\{[^}]*\}'
    
    # Replace with MAIFA error wrapping
    new_exception_block = '''except Exception as e:
            raise FetchError(
                source="{source_name}",
                stage="fetch",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=True
            )'''.format(source_name=source_name)
    
    content = re.sub(old_exception_pattern, new_exception_block, content, flags=re.DOTALL)
    
    # Also handle TimeoutError if present
    timeout_pattern = r'except asyncio\.TimeoutError:\s*\n.*?return\s*\{[^}]*\}'
    new_timeout_block = '''except asyncio.TimeoutError:
            raise FetchError(
                source="{source_name}",
                stage="fetch",
                error_type="TimeoutError",
                message="Request timed out",
                retryable=True
            )'''.format(source_name=source_name)
    
    content = re.sub(timeout_pattern, new_timeout_block, content, flags=re.DOTALL)
    
    # Write back
    with open(fetcher_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Updated fetcher for {source_name}")
    return True

def update_validator(source_name):
    """Update validator.py for a specific source"""
    validator_path = f"services/data_ingestion/sources/{source_name}/validator.py"
    
    if not os.path.exists(validator_path):
        print(f"Missing validator for {source_name}")
        return False
    
    # Read the file
    with open(validator_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add error import if not present
    if "from ...errors import ValidationError" not in content:
        # Find the imports section and add our import
        content = re.sub(
            r'(from \.\.\.interfaces import DataValidator)',
            r'\1\nfrom ...errors import ValidationError',
            content
        )
    
    # Replace exception handling
    old_exception_pattern = r'except Exception as e:\s*\n.*?return\s*(False|True)'
    
    new_exception_block = '''except Exception as e:
            raise ValidationError(
                source="{source_name}",
                stage="validate",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )'''.format(source_name=source_name)
    
    content = re.sub(old_exception_pattern, new_exception_block, content, flags=re.DOTALL)
    
    # Write back
    with open(validator_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Updated validator for {source_name}")
    return True

def update_normalizer(source_name):
    """Update normalizer.py for a specific source"""
    normalizer_path = f"services/data_ingestion/sources/{source_name}/normalizer.py"
    
    if not os.path.exists(normalizer_path):
        print(f"Missing normalizer for {source_name}")
        return False
    
    # Read the file
    with open(normalizer_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add error import if not present
    if "from ...errors import NormalizationError" not in content:
        # Find the imports section and add our import
        content = re.sub(
            r'(from \.\.\.interfaces import DataNormalizer)',
            r'\1\nfrom ...errors import NormalizationError',
            content
        )
    
    # Replace exception handling
    old_exception_pattern = r'except Exception as e:\s*\n.*?return\s*\{[^}]*\}'
    
    new_exception_block = '''except Exception as e:
            raise NormalizationError(
                source="{source_name}",
                stage="normalize",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )'''.format(source_name=source_name)
    
    content = re.sub(old_exception_pattern, new_exception_block, content, flags=re.DOTALL)
    
    # Write back
    with open(normalizer_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Updated normalizer for {source_name}")
    return True

# Update all sources
print("Updating all 13 sources with MAIFA error wrapping...")
print("=" * 60)

for source in sources:
    print(f"\nProcessing {source}:")
    update_fetcher(source)
    update_validator(source)
    update_normalizer(source)

print("\n" + "=" * 60)
print("MAIFA error wrapping update completed for all 13 sources!")
