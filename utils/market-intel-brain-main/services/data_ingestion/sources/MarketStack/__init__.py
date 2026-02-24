"""
MAIFA v3 Market Stack Data Source
Market Stack API integration for financial data
"""

from .fetcher import MarketStackFetcher
from .parser import MarketStackParser
from .validator import MarketStackValidator
from .normalizer import MarketStackNormalizer

async def register():
    """Register Market Stack data source"""
    from ..registry import source_registry
    
    fetcher = MarketStackFetcher()
    parser = MarketStackParser()
    validator = MarketStackValidator()
    normalizer = MarketStackNormalizer()
    
    config = {
        "name": "MarketStack",
        "description": "Market Stack API for financial market data",
        "api_key_required": True,
        "api_key_placeholder": "YOUR_MARKET_STACK_API_KEY",
        "rate_limit": 1000,  # requests per minute
        "timeout": 30.0
    }
    
    await source_registry.register_source(
        "MarketStack",
        fetcher,
        parser,
        validator,
        normalizer,
        config
    )
