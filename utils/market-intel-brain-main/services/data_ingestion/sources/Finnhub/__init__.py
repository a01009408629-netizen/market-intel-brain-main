"""
MAIFA v3 Finnhub Data Source
Finnhub API integration for financial data
"""

from .fetcher import FinnhubFetcher
from .parser import FinnhubParser
from .validator import FinnhubValidator
from .normalizer import FinnhubNormalizer

async def register():
    """Register Finnhub data source"""
    from ..registry import source_registry
    
    fetcher = FinnhubFetcher()
    parser = FinnhubParser()
    validator = FinnhubValidator()
    normalizer = FinnhubNormalizer()
    
    config = {
        "name": "Finnhub",
        "description": "Finnhub API for financial market data",
        "api_key_required": True,
        "api_key_placeholder": "YOUR_FINNHUB_API_KEY",
        "rate_limit": 60,  # requests per minute for free tier
        "timeout": 30.0
    }
    
    await source_registry.register_source(
        "Finnhub",
        fetcher,
        parser,
        validator,
        normalizer,
        config
    )
