"""
MAIFA v3 Trading Economics Data Source
Trading Economics API integration for economic data
"""

from .fetcher import TradingEconomicsFetcher
from .parser import TradingEconomicsParser
from .validator import TradingEconomicsValidator
from .normalizer import TradingEconomicsNormalizer

async def register():
    """Register Trading Economics data source"""
    from ..registry import source_registry
    
    fetcher = TradingEconomicsFetcher()
    parser = TradingEconomicsParser()
    validator = TradingEconomicsValidator()
    normalizer = TradingEconomicsNormalizer()
    
    config = {
        "name": "TradingEconomics",
        "description": "Trading Economics API for economic data",
        "api_key_required": True,
        "api_key_placeholder": "YOUR_TRADING_ECONOMICS_API_KEY",
        "rate_limit": 200,  # requests per minute
        "timeout": 30.0
    }
    
    await source_registry.register_source(
        "TradingEconomics",
        fetcher,
        parser,
        validator,
        normalizer,
        config
    )
