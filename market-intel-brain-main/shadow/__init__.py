"""
Shadow Comparison Engine

This module provides a shadow comparison system for A/B testing data
using concurrent requests to compare primary and shadow adapter responses.
"""

from .shadow_engine import ShadowEngine, get_engine
from .comparator import ResponseComparator, get_comparator
from .metrics import ShadowMetrics, get_metrics
from .exceptions import (
    ShadowError,
    ConfigurationError,
    ComparatorError,
    MetricsError
)

__all__ = [
    # Core classes
    'ShadowEngine',
    'ResponseComparator',
    'ShadowMetrics',
    
    # Convenience functions
    'get_engine',
    'get_comparator',
    'get_metrics',
    
    # Exceptions
    'ShadowError',
    'ConfigurationError',
    'ComparatorError',
    'MetricsError'
]

# Global instances
_global_engine = None
_global_comparator = None
_global_metrics = None


def get_global_engine(**kwargs) -> ShadowEngine:
    """Get or create the global shadow engine."""
    global _global_engine
    if _global_engine is None:
        _global_engine = ShadowEngine(**kwargs)
    return _global_engine


def get_global_comparator(**kwargs) -> ResponseComparator:
    """Get or create the global response comparator."""
    global _global_comparator
    if _global_comparator is None:
        _global_comparator = ResponseComparator(**kwargs)
    return _global_comparator


def get_global_metrics(**kwargs) -> ShadowMetrics:
    """Get or create the global shadow metrics collector."""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = ShadowMetrics(**kwargs)
    return _global_metrics
