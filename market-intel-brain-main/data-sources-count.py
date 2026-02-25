#!/usr/bin/env python3
"""
Count all data providers in Market Intel Brain
"""

import os
import sys
from pathlib import Path

def count_providers():
    """Count all data providers"""
    
    print("Market Intel Brain - Data Sources Count")
    print("=" * 50)
    
    # Provider files
    provider_files = [
        'authenticated_providers.py',
        'us_economic_providers.py', 
        'us_stock_news_providers.py',
        'tradfi_providers.py',
        'gold_dollar_indices_providers.py',
        'data_brokerage_system.py'
    ]
    
    total_providers = 0
    provider_details = []
    
    for file_name in provider_files:
        file_path = Path(file_name)
        
        if not file_path.exists():
            print(f"WARNING: {file_name} not found")
            continue
            
        print(f"\nFILE: {file_name}:")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find all provider classes
            lines = content.split('\n')
            file_providers = []
            
            for i, line in enumerate(lines):
                if 'class' in line and 'Provider' in line and '(' in line:
                    # Extract class name
                    class_line = line.strip()
                    if class_line.startswith('class '):
                        class_name = class_line.split('class ')[1].split('(')[0]
                        
                        # Get description from next lines
                        description = ""
                        for j in range(i+1, min(i+5, len(lines))):
                            if '"""' in lines[j]:
                                desc_line = lines[j].strip()
                                description = desc_line.replace('"""', '').strip()
                                break
                        
                        file_providers.append({
                            'name': class_name,
                            'description': description,
                            'file': file_name
                        })
            
            # Display providers for this file
            for provider in file_providers:
                print(f"  OK: {provider['name']}")
                if provider['description']:
                    print(f"     DESC: {provider['description']}")
                total_providers += 1
                provider_details.append(provider)
                
        except Exception as e:
            print(f"ERROR reading {file_name}: {e}")
    
    # Summary by category
    print(f"\n" + "=" * 50)
    print("SUMMARY BY CATEGORY")
    print("=" * 50)
    
    categories = {
        'Authenticated APIs': [],
        'Economic Data': [],
        'Stock News': [],
        'Traditional Finance': [],
        'Indices & Forex': [],
        'Comprehensive': []
    }
    
    for provider in provider_details:
        file_name = provider['file']
        
        if 'authenticated' in file_name:
            categories['Authenticated APIs'].append(provider)
        elif 'economic' in file_name:
            categories['Economic Data'].append(provider)
        elif 'news' in file_name:
            categories['Stock News'].append(provider)
        elif 'tradfi' in file_name:
            categories['Traditional Finance'].append(provider)
        elif 'gold_dollar' in file_name:
            categories['Indices & Forex'].append(provider)
        elif 'brokerage' in file_name:
            categories['Comprehensive'].append(provider)
    
    for category, providers in categories.items():
        if providers:
            print(f"\n{category}: {len(providers)} providers")
            for provider in providers:
                print(f"   - {provider['name']}")
    
    # API Keys status
    print(f"\n" + "=" * 50)
    print("API KEYS STATUS")
    print("=" * 50)
    
    api_keys = [
        ('FRED_API_KEY', 'FRED Economic Data'),
        ('ALPHAVANTAGE_API_KEY', 'Alpha Vantage'),
        ('FINNHUB_API_KEY', 'Finnhub'),
        ('TWITTER_DATA_API_KEY', 'Twitter Data'),
        ('MARKETSTACK_API_KEY', 'MarketStack'),
        ('FINANCIALMODELING_API_KEY', 'Financial Modeling Prep')
    ]
    
    configured_keys = 0
    for key, description in api_keys:
        value = os.environ.get(key)
        if value:
            print(f"OK: {description}: Configured")
            configured_keys += 1
        else:
            print(f"ERROR: {description}: Not configured")
    
    # Final summary
    print(f"\n" + "=" * 50)
    print("FINAL COUNT")
    print("=" * 50)
    print(f"Total Data Providers: {total_providers}")
    print(f"Configured API Keys: {configured_keys}/{len(api_keys)}")
    print(f"Provider Files: {len([f for f in provider_files if Path(f).exists()])}")
    
    if configured_keys == len(api_keys):
        print("\nSUCCESS: ALL API KEYS CONFIGURED!")
        print("Your Market Intel Brain is fully ready!")
    else:
        print(f"\nWARNING: {len(api_keys) - configured_keys} API keys missing")
        print("Run: python setup-api-keys.py")
    
    return total_providers, configured_keys

if __name__ == "__main__":
    count_providers()
