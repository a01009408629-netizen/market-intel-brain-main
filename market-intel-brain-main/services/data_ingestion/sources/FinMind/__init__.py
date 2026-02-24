"""
MAIFA v3 FinMind Data Source
FinMind API integration for financial data
"""

from .fetcher import FinMindFetcher
from .parser import FinMindParser
from .validator import FinMindValidator
from .normalizer import FinMindNormalizer

async def register():
    """Register FinMind data source"""
    from ..registry import source_registry
    
    fetcher = FinMindFetcher()
    parser = FinMindParser()
    validator = FinMindValidator()
    normalizer = FinMindNormalizer()
    
    config = {
        "name": "FinMind",
        "description": "FinMind API for financial data",
        "api_key_required": True,
        "api_key_placeholder": "YOUR_FINMIND_API_KEY",
        "rate_limit": 300,  # requests per minute
        "timeout": 30.0
    }
    
    await source_registry.register_source(
        "FinMind",
        fetcher,
        parser,
        validator,
        normalizer,
        config
    )
