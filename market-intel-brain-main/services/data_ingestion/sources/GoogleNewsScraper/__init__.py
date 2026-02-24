"""
MAIFA v3 Google News Scraper Data Source
Google News scraper for news data
"""

from .fetcher import GoogleNewsScraperFetcher
from .parser import GoogleNewsScraperParser
from .validator import GoogleNewsScraperValidator
from .normalizer import GoogleNewsScraperNormalizer

async def register():
    """Register Google News Scraper data source"""
    from ..registry import source_registry
    
    fetcher = GoogleNewsScraperFetcher()
    parser = GoogleNewsScraperParser()
    validator = GoogleNewsScraperValidator()
    normalizer = GoogleNewsScraperNormalizer()
    
    config = {
        "name": "GoogleNewsScraper",
        "description": "Google News scraper for news data",
        "api_key_required": False,
        "rate_limit": 60,  # requests per minute
        "timeout": 30.0
    }
    
    await source_registry.register_source(
        "GoogleNewsScraper",
        fetcher,
        parser,
        validator,
        normalizer,
        config
    )
