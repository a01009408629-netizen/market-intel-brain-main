"""
MAIFA v3 News Catcher API Data Source
News Catcher API integration for news data
"""

from .fetcher import NewsCatcherAPIFetcher
from .parser import NewsCatcherAPIParser
from .validator import NewsCatcherAPIValidator
from .normalizer import NewsCatcherAPINormalizer

async def register():
    """Register News Catcher API data source"""
    from ..registry import source_registry
    
    fetcher = NewsCatcherAPIFetcher()
    parser = NewsCatcherAPIParser()
    validator = NewsCatcherAPIValidator()
    normalizer = NewsCatcherAPINormalizer()
    
    config = {
        "name": "NewsCatcherAPI",
        "description": "News Catcher API for news data",
        "api_key_required": True,
        "api_key_placeholder": "YOUR_NEWSCATCHER_API_KEY",
        "rate_limit": 100,  # requests per minute
        "timeout": 30.0
    }
    
    await source_registry.register_source(
        "NewsCatcherAPI",
        fetcher,
        parser,
        validator,
        normalizer,
        config
    )
