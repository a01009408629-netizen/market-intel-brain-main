"""
MAIFA v3 EconDB Data Source
EconDB API integration for economic data
"""

from .fetcher import EconDBFetcher
from .parser import EconDBParser
from .validator import EconDBValidator
from .normalizer import EconDBNormalizer

async def register():
    """Register EconDB data source"""
    from ..registry import source_registry
    
    fetcher = EconDBFetcher()
    parser = EconDBParser()
    validator = EconDBValidator()
    normalizer = EconDBNormalizer()
    
    config = {
        "name": "EconDB",
        "description": "EconDB API for economic data",
        "api_key_required": True,
        "api_key_placeholder": "YOUR_EconDB_API_KEY",
        "rate_limit": 100,  # requests per minute
        "timeout": 30.0
    }
    
    await source_registry.register_source(
        "EconDB",
        fetcher,
        parser,
        validator,
        normalizer,
        config
    )
