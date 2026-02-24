"""
Schema Evolution Guard

This module provides schema evolution detection and validation system
that monitors API response changes and alerts developers to schema drift.
"""

from .schema_guard import SchemaGuard, get_guard
from .fingerprint import SchemaFingerprint, get_fingerprinter
from .diff_analyzer import DiffAnalyzer, get_analyzer
from .exceptions import (
    SchemaDriftError,
    SchemaValidationError,
    ConfigurationError,
    GuardError
)

__all__ = [
    # Core classes
    'SchemaGuard',
    'SchemaFingerprint',
    'DiffAnalyzer',
    
    # Convenience functions
    'get_guard',
    'get_fingerprinter',
    'get_analyzer',
    
    # Exceptions
    'SchemaDriftError',
    'SchemaValidationError',
    'ConfigurationError',
    'GuardError'
]

# Global instances
_global_guard = None
_global_fingerprinter = None
_global_analyzer = None


def get_global_guard(**kwargs) -> SchemaGuard:
    """Get or create the global schema guard."""
    global _global_guard
    if _global_guard is None:
        _global_guard = SchemaGuard(**kwargs)
    return _global_guard


def get_global_fingerprinter(**kwargs) -> SchemaFingerprint:
    """Get or create the global fingerprinter."""
    global _global_fingerprinter
    if _global_fingerprinter is None:
        _global_fingerprinter = SchemaFingerprint(**kwargs)
    return _global_fingerprinter


def get_global_analyzer(**kwargs) -> DiffAnalyzer:
    """Get or create the global diff analyzer."""
    global _global_analyzer
    if _global_analyzer is None:
        _global_analyzer = DiffAnalyzer(**kwargs)
    return _global_analyzer
