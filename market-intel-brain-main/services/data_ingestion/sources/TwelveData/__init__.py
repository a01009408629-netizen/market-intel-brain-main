"""
MAIFA v3 Twelve Data Data Source
Twelve Data API integration for financial data
"""

from .fetcher import TwelveDataFetcher
from .parser import TwelveDataParser
from .validator import TwelveDataValidator
from .normalizer import TwelveDataNormalizer

async def register():
    """Register Twelve Data data source"""
    from ..registry import source_registry
    
    fetcher = TwelveDataFetcher()
    parser = TwelveDataParser()
    validator = TwelveDataValidator()
    normalizer = TwelveDataNormalizer()
    
    config = {
        "name": "TwelveData",
        "description": "Twelve Data API for financial market data",
        "api_key_required": True,
        "api_key_placeholder": "YOUR_TWELVE_DATA_API_KEY",
        "rate_limit": 8,  # requests per minute for free tier
        "timeout": 30.0
    }
    
    await source_registry.register_source(
        "TwelveData",
        fetcher,
        parser,
        validator,
        normalizer,
        config
    )
