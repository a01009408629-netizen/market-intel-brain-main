"""
MAIFA v3 Data Ingestion Services
Unified data ingestion architecture for 13 news & financial data sources
"""

from .orchestrator import DataIngestionOrchestrator
from .registry import SourceRegistry
from .interfaces import DataFetcher, DataParser, DataValidator, DataNormalizer
from .interface import DataIngestionInterface

# Global instances
source_registry = SourceRegistry()
data_orchestrator = DataIngestionOrchestrator()
data_interface = DataIngestionInterface()

def get_registry():
    """Get global source registry"""
    return source_registry

def get_orchestrator():
    """Get global data orchestrator"""
    return data_orchestrator

def get_interface():
    """Get unified data interface"""
    return data_interface

# Convenience exports
__all__ = [
    'DataIngestionOrchestrator',
    'SourceRegistry', 
    'DataFetcher',
    'DataParser',
    'DataValidator',
    'DataNormalizer',
    'DataIngestionInterface',
    'source_registry',
    'data_orchestrator',
    'data_interface',
    'get_registry',
    'get_orchestrator',
    'get_interface'
]
