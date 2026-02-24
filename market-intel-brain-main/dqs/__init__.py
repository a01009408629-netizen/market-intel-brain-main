"""
Data Quality System (DQS) - Sanity Checker

This module provides high-performance statistical analysis for data quality
with memory-efficient outlier detection using Welford's online algorithm.
"""

from .outlier_detector import OutlierDetector, AnomalyDetectedWarning
from .welford import WelfordStatistics
from .sanity_checker import SanityChecker, get_sanity_checker
from .exceptions import (
    DataQualityError,
    InsufficientDataError,
    StatisticalError
)

__all__ = [
    # Core classes
    'OutlierDetector',
    'WelfordStatistics',
    'SanityChecker',
    'get_sanity_checker',
    
    # Exceptions
    'AnomalyDetectedWarning',
    'DataQualityError',
    'InsufficientDataError',
    'StatisticalError'
]

# Global sanity checker instance
_global_checker = None


def get_global_checker(**kwargs) -> SanityChecker:
    """Get or create the global sanity checker instance."""
    global _global_checker
    if _global_checker is None:
        _global_checker = SanityChecker(**kwargs)
    return _global_checker
