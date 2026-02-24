"""
MAIFA v3 EuroStat Feeds Data Source
EuroStat API integration for European economic data
"""

from .fetcher import EuroStatFeedsFetcher
from .parser import EuroStatFeedsParser
from .validator import EuroStatFeedsValidator
from .normalizer import EuroStatFeedsNormalizer

async def register():
    """Register EuroStat Feeds data source"""
    from ..registry import source_registry
    
    fetcher = EuroStatFeedsFetcher()
    parser = EuroStatFeedsParser()
    validator = EuroStatFeedsValidator()
    normalizer = EuroStatFeedsNormalizer()
    
    config = {
        "name": "EuroStatFeeds",
        "description": "EuroStat API for European economic data",
        "api_key_required": False,
        "rate_limit": 100,  # requests per minute
        "timeout": 30.0
    }
    
    await source_registry.register_source(
        "EuroStatFeeds",
        fetcher,
        parser,
        validator,
        normalizer,
        config
    )
