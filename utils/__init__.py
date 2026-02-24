"""
Binary Serialization System

This module provides high-performance binary serialization with custom MessagePack hooks
for handling decimal, datetime, and UUID serialization without blocking operations.
"""

from .binary_serializer import BinarySerializer, get_serializer
from .hooks import MessagePackHooks, register_hook, get_hooks
from .exceptions import SerializationError, ConfigurationError

__all__ = [
    # Core classes
    'BinarySerializer',
    'MessagePackHooks',
    'register_hook',
    'get_hooks',
    
    # Convenience functions
    'get_serializer',
    'serialize_to_bytes',
    'deserialize_from_bytes',
    'serialize_to_base64',
    'deserialize_from_base64'
]

# Legacy exports for backward compatibility
from .legacy_serializer import LegacySerializer, get_legacy_serializer
from .exceptions import SerializationError
