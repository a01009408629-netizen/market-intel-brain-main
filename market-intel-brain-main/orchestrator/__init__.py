"""
Dynamic Adapter Orchestrator

This module provides a plug-and-play system for managing data source adapters
with automatic discovery, registration, and dynamic loading capabilities.
"""

from .registry import AdapterRegistry, register_adapter
from .loader import AdapterLoader
from .orchestrator import AdapterOrchestrator

__all__ = [
    'AdapterRegistry',
    'register_adapter',
    'AdapterLoader', 
    'AdapterOrchestrator'
]

# Initialize the global registry instance
registry = AdapterRegistry()
