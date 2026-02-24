"""
MAIFA Source Adapter - Identity System

This module provides stealth identity management with TLS fingerprinting
and proxy rotation for bypassing anti-bot protections.
"""

from .fingerprint_provider import FingerprintProvider, AsyncSessionManager
from .proxy_manager import ProxyManager, ProxyRotationStrategy
from .blacklist_manager import BlacklistManager

__all__ = [
    "FingerprintProvider",
    "AsyncSessionManager",
    "ProxyManager", 
    "ProxyRotationStrategy",
    "BlacklistManager"
]
