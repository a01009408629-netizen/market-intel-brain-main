"""
Security Settings - Legacy Compatibility

This module provides backward compatibility for existing security settings imports.
"""

from . import SecuritySettings, get_settings

# Re-export for direct import
__all__ = ['SecuritySettings', 'get_settings']
