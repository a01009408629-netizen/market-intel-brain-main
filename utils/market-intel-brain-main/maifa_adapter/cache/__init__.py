"""
MAIFA Source Adapter - Cache System

This module provides tiered caching with SWR (Stale-While-Revalidate)
logic using L1 (memory) and L2 (Redis) cache layers.
"""

from .tiered_cache import TieredCacheManager
from .swr_engine import SWREngine, SWRConfig

__all__ = [
    "TieredCacheManager",
    "SWREngine",
    "SWRConfig"
]
