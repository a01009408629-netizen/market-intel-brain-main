"""
MAIFA v3 Yahoo Finance Data Source
Yahoo Finance API integration for financial data
"""

from .fetcher import YahooFinanceFetcher
from .parser import YahooFinanceParser
from .validator import YahooFinanceValidator
from .normalizer import YahooFinanceNormalizer

async def register():
    """Register Yahoo Finance data source"""
    from ..registry import source_registry
    
    fetcher = YahooFinanceFetcher()
    parser = YahooFinanceParser()
    validator = YahooFinanceValidator()
    normalizer = YahooFinanceNormalizer()
    
    config = {
        "name": "YahooFinance",
        "description": "Yahoo Finance API for stock market data",
        "api_key_required": False,
        "rate_limit": 100,  # requests per minute
        "timeout": 30.0
    }
    
    await source_registry.register_source(
        "YahooFinance",
        fetcher,
        parser,
        validator,
        normalizer,
        config
    )
