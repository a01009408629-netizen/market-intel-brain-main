"""
MAIFA v3 IMF Json Feeds Data Source
IMF JSON Feeds API integration for international monetary data
"""

from .fetcher import IMFJsonFeedsFetcher
from .parser import IMFJsonFeedsParser
from .validator import IMFJsonFeedsValidator
from .normalizer import IMFJsonFeedsNormalizer

async def register():
    """Register IMF Json Feeds data source"""
    from ..registry import source_registry
    
    fetcher = IMFJsonFeedsFetcher()
    parser = IMFJsonFeedsParser()
    validator = IMFJsonFeedsValidator()
    normalizer = IMFJsonFeedsNormalizer()
    
    config = {
        "name": "IMFJsonFeeds",
        "description": "IMF JSON Feeds API for international monetary data",
        "api_key_required": False,
        "rate_limit": 100,  # requests per minute
        "timeout": 30.0
    }
    
    await source_registry.register_source(
        "IMFJsonFeeds",
        fetcher,
        parser,
        validator,
        normalizer,
        config
    )
