"""
MAIFA Source Adapter - Core Module

This module contains the foundational classes and standardized exceptions
that form the backbone of the MAIFA data ingestion system.
"""

from .base_adapter import BaseSourceAdapter
from .exceptions import (
    TransientAdapterError,
    FatalAdapterError,
    AdapterConfigurationError,
    AdapterValidationError
)

__all__ = [
    "BaseSourceAdapter",
    "TransientAdapterError", 
    "FatalAdapterError",
    "AdapterConfigurationError",
    "AdapterValidationError"
]
