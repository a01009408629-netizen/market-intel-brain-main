"""
Stateful Mock Sandbox

This module provides a mock sandbox environment with FastAPI for testing
and development using deterministic randomness and mock data providers.
"""

from .mock_server import MockServer, get_server
from .mock_providers import MockProviderRegistry, get_provider_registry
from .randomness import DeterministicRandom, get_deterministic_random
from .exceptions import SandboxError, ConfigurationError

__all__ = [
    # Core classes
    'MockServer',
    'MockProviderRegistry',
    'DeterministicRandom',
    
    # Convenience functions
    'get_server',
    'get_provider_registry',
    'get_deterministic_random',
    
    # Exceptions
    'SandboxError',
    'ConfigurationError'
]

# Global instances
_global_server = None
_global_provider_registry = None
_global_deterministic_random = None


def get_global_server(**kwargs) -> MockServer:
    """Get or create the global mock server."""
    global _global_server
    if _global_server is None:
        _global_server = MockServer(**kwargs)
    return _global_server


def get_global_provider_registry(**kwargs) -> MockProviderRegistry:
    """Get or create the global provider registry."""
    global _global_provider_registry
    if _global_provider_registry is None:
        _global_provider_registry = MockProviderRegistry(**kwargs)
    return _global_provider_registry


def get_global_deterministic_random(**kwargs) -> DeterministicRandom:
    """Get or create the global deterministic random generator."""
    global _global_deterministic_random
    if _global_deterministic_random is None:
        _global_deterministic_random = DeterministicRandom(**kwargs)
    return _global_deterministic_random
