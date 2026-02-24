"""
MAIFA v3 Alpha Vantage Data Source
Alpha Vantage API integration for financial data
"""

from .fetcher import AlphaVantageFetcher
from .parser import AlphaVantageParser
from .validator import AlphaVantageValidator
from .normalizer import AlphaVantageNormalizer

async def register():
    """Register Alpha Vantage data source"""
    from ..registry import source_registry
    
    fetcher = AlphaVantageFetcher()
    parser = AlphaVantageParser()
    validator = AlphaVantageValidator()
    normalizer = AlphaVantageNormalizer()
    
    config = {
        "name": "AlphaVantage",
        "description": "Alpha Vantage API for financial market data",
        "api_key_required": True,
        "api_key_placeholder": "YOUR_ALPHA_VANTAGE_API_KEY",
        "rate_limit": 5,  # requests per minute for free tier
        "timeout": 30.0
    }
    
    await source_registry.register_source(
        "AlphaVantage",
        fetcher,
        parser,
        validator,
        normalizer,
        config
    )
