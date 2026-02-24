"""
Zero-Trust Secrets Manager

This module provides secure secrets management with Pydantic settings,
zero-trust principles, and external provider integration.
"""

from .settings import SecretsSettings, get_settings
from .providers import SecretsProvider, get_provider
from .manager import SecretsManager, get_manager
from .exceptions import SecretsError, SecurityError

__all__ = [
    # Core classes
    'SecretsSettings',
    'SecretsProvider',
    'SecretsManager',
    
    # Convenience functions
    'get_settings',
    'get_provider',
    'get_manager',
    
    # Exceptions
    'SecretsError',
    'SecurityError'
]

# Global instances
_global_settings = None
_global_provider = None
_global_manager = None


def get_global_settings(**kwargs) -> SecretsSettings:
    """Get or create global secrets settings."""
    global _global_settings
    if _global_settings is None:
        _global_settings = SecretsSettings(**kwargs)
    return _global_settings


def get_global_provider(**kwargs) -> SecretsProvider:
    """Get or create global secrets provider."""
    global _global_provider
    if _global_provider is None:
        _global_provider = SecretsProvider(**kwargs)
    return _global_provider


def get_global_manager(**kwargs) -> SecretsManager:
    """Get or create global secrets manager."""
    global _global_manager
    if _global_manager is None:
        _global_manager = SecretsManager(**kwargs)
    return _global_manager
