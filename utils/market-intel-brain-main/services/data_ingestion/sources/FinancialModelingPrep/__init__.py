"""
MAIFA v3 Financial Modeling Prep Data Source
Financial Modeling Prep API integration for financial data
"""

from .fetcher import FinancialModelingPrepFetcher
from .parser import FinancialModelingPrepParser
from .validator import FinancialModelingPrepValidator
from .normalizer import FinancialModelingPrepNormalizer

async def register():
    """Register Financial Modeling Prep data source"""
    from ..registry import source_registry
    
    fetcher = FinancialModelingPrepFetcher()
    parser = FinancialModelingPrepParser()
    validator = FinancialModelingPrepValidator()
    normalizer = FinancialModelingPrepNormalizer()
    
    config = {
        "name": "FinancialModelingPrep",
        "description": "Financial Modeling Prep API for financial data",
        "api_key_required": True,
        "api_key_placeholder": "YOUR_FINANCIAL_MODELING_PREP_API_KEY",
        "rate_limit": 10,  # requests per minute for free tier
        "timeout": 30.0
    }
    
    await source_registry.register_source(
        "FinancialModelingPrep",
        fetcher,
        parser,
        validator,
        normalizer,
        config
    )
