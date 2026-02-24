"""
Binary Serializer Implementation

This module provides high-performance binary serialization using MessagePack with custom hooks
for decimal, datetime, and UUID serialization without blocking operations.
"""

import asyncio
import time
import logging
import json
import uuid
import hashlib
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from collections import defaultdict
from abc import ABC, abstractmethod

from .exceptions import (
    SerializationError,
    ConfigurationError,
    ValidationError
    TypeMismatchError,
    IntegrityError
)
from .hooks import get_hooks, MessagePackHooks


@dataclass
class SerializationConfig:
    """Configuration for binary serializer."""
    pack_encoding: str = "utf-8"
    use_compact: bool = True
    sort_keys: bool = True
    ensure_ascii: bool = True
    max_depth: int = 100
    enable_checksum: bool = True
    checksum_algorithm: str = "sha256"
    enable_hooks: bool = True
    decimal_precision: str = "string"  # "string", "high", "banking"
    datetime_format: str = "iso8601"
    uuid_format: str = "standard"  # "standard", "compact", "hex"
    max_payload_size: int = 10 * 1024 * 1024  # 10MB
    enable_validation: bool = True
    enable_integrity_check: bool = True


@dataclass
class SerializationResult:
    """Result of serialization operation."""
    success: bool
    data: bytes
    size: int
    checksum: Optional[str] = None
    metadata: Dict[str, Any]
    error: Optional[str] = None
    serialization_time: float
    hooks_applied: List[str]
    metadata: Dict[str, Any]


class BinarySerializer:
    """
    High-performance binary serializer using MessagePack with custom hooks.
    
    This class provides fast binary serialization with support for custom hooks
    for special data types without blocking operations.
    """
    
    def __init__(
        self,
        config: Optional[SerializationConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize binary serializer.
        
        try:
            import msgpack
            self.msgpack = msgpack.Pack(
                pack_encoding=config.pack_encoding,
                use_compact=config.use_compact,
                sort_keys=config.sort_keys,
                ensure_ascii=config.ensure_ascii,
                strict_types=False
            )
        except ImportError:
            self.logger.error("msgpack not available, using fallback JSON")
            import json
            self.msgpack = None
        
        self.config = config or SerializationConfig()
        self.logger = logger or logging.getLogger("BinarySerializer")
        
        self._hooks = get_hooks()
        
        self.logger.info("BinarySerializer initialized")
    
    async def serialize(
        self,
        data: Any,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SerializationResult:
        """
        Serialize data to binary format.
        
        Args:
            data: Data to serialize
            request_id: Optional request identifier
            metadata: Additional metadata
            
        Returns:
            SerializationResult with detailed information
        """
        start_time = time.time()
        
        try:
            # Call before hooks
            context = HookContext(
                request_id=request_id or str(uuid.uuid4()),
                adapter_name="binary_serializer",
                operation="serialize",
                data=data,
                metadata=metadata or {}
            )
            
            await self._call_hooks("before_serialize", context)
            
            # Serialize based on hook results
            if all(r.get("status") == "continue"):
                # Perform actual serialization
                if self.msgpack:
                    serialized_data = self.msgpack.packb(
                        data,
                        use_compact=self.config.use_compact,
                        sort_keys=self.config.sort_keys,
                        ensure_ascii=self.config.ensure_ascii
                        strict_types=self.config.strict_types
                    )
                else:
                    # Fallback to JSON
                    serialized_data = json.dumps(
                        data,
                        sort_keys=self.config.sort_keys,
                        ensure_ascii=self.config.ensure_ascii
                        separators=(',', ':')
                    ).encode('utf-8')
                
                # Calculate checksum
                checksum = self._calculate_checksum(serialized_data)
                
                # Create result
                result = SerializationResult(
                    success=True,
                    data=serialized_data,
                    size=len(serialized_data),
                    checksum=checksum,
                    serialization_time=time.time() - start_time,
                    hooks_applied=self._get_applied_hooks("before_serialize"),
                    metadata=metadata or {}
                )
                
                self.logger.debug(
                    f"Serialized {len(data)} bytes "
                    f"(checksum: {checksum[:16]}...)"
                )
                
                return result
                
        except Exception as e:
            self.logger.error(f"Serialization failed: {e}")
            
            return SerializationResult(
                success=False,
                data=b"",
                size=0,
                checksum=None,
                serialization_time=time.time() - start_time,
                hooks_applied=[],
                metadata={"error": str(e)},
                metadata={"original_data": str(data)}
            )
    
    def deserialize(
        self,
        data: bytes,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SerializationResult:
        """
        Deserialize data from binary format.
        
        Args:
            data: Binary data to deserialize
            request_id: Optional request identifier
            metadata: Additional metadata
            
        Returns:
            SerializationResult with deserialized data
        """
        start_time = time.time()
        
        try:
            # Call before hooks
            context = HookContext(
                request_id=request_id or str(uuid.uuid4()),
                adapter_name="binary_serializer",
                operation="deserialize",
                data=data,
                metadata=metadata or {}
            )
            
            await self._call_hooks("before_deserialize", context)
            
            # Deserialize based on hook results
            if all(r.get("status") == "continue"):
                # Perform actual deserialization
                if self.msgpack:
                    try:
                        deserialized_data = self.msgpack.unpackb(data, strict=False)
                    deserialized_data = self._validate_deserialized_data(deserialized_data)
                else:
                    # Fallback to JSON
                        deserialized_data = json.loads(data.decode('utf-8'))
                        deserialized_data = self._validate_deserialized_data(deserialized_data)
                
                result = SerializationResult(
                    success=True,
                    data=deserialized_data,
                    size=len(data),
                    checksum=self._calculate_checksum(data),
                    serialization_time=time.time() - start_time,
                    hooks_applied=self._get_applied_hooks("before_deserialize"),
                    metadata=metadata or {},
                    metadata={"deserialization_method": "msgpack" if self.msgpack else "json"}
                )
                
                self.logger.debug(
                    f"Deserialized {len(deserialized_data)} bytes "
                    f"(checksum: {self._calculate_checksum(deserialized_data)[:16]}...)"
                )
                
                return result
                
        except Exception as e:
            self.logger.error(f"Deserialization failed: {e}")
            
            return SerializationResult(
                success=False,
                data=b"",
                size=0,
                checksum=None,
                serialization_time=time.time() - start_time,
                hooks_applied=[],
                metadata={"error": str(e)},
                metadata={"original_data": str(data)}
            )
    
    def _calculate_checksum(self, data: bytes) -> Optional[str]:
        """
        Calculate checksum for data integrity verification.
        
        Args:
            data: Data to calculate checksum for
            
        Returns:
            Checksum string or None if not available
        """
        if not self.config.enable_checksum:
            return None
        
        try:
            if self.config.checksum_algorithm == "sha256":
                return hashlib.sha256(data).hexdigest()
            elif self.config.checksum_algorithm == "md5":
                return hashlib.md5(data).hexdigest()
            elif self.config.checksum_algorithm == "sha1":
                return hashlib.sha1(data).hexdigest()
            else:
                return hashlib.sha256(data).hexdigest()
                
        except Exception as e:
            self.logger.error(f"Checksum calculation failed: {e}")
            return None
    
    def _validate_deserialized_data(self, data: Any) -> bool:
        """
        Validate deserialized data integrity.
        
        Args:
            data: Deserialized data to validate
            
        Returns:
            True if data is valid
        """
        try:
            # Basic type checking
            if not isinstance(data, (dict, list, tuple, str, int, float, bool)):
                self.logger.warning(f"Unexpected data type: {type(data)}")
                return False
            
            # Dictionary validation
            if isinstance(data, dict):
                for key, value in data.items():
                    if not isinstance(key, str):
                        self.logger.warning(f"Non-string key: {key}")
                        return False
                
                # Check for required fields
                required_fields = ["id", "timestamp", "data"]
                for field in required_fields:
                    if field not in data:
                        self.logger.warning(f"Missing required field: {field}")
                        return False
                
                # Check for data types
                if value is not None and not isinstance(value, (int, float, str, bool)):
                    self.logger.warning(f"Unexpected type for field {key}: {type(value)}")
                        return False
                
                return True
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False
    
    def _get_applied_hooks(self, hook_type: str) -> List[str]:
        """Get list of applied hooks by type."""
        return [h.__class__.__name__ for h in self._hooks.get(hook_type, [])]
    
    def _get_applied_hooks(self, hook_type: str) -> List[str]:
        """Get list of applied hooks by type."""
        return [h.__name__ for h in self._get_applied_hooks(hook_type, [])]
    
    def _store_applied_hook(self, hook_type: str, hook_class: str):
        """Store applied hook in registry."""
        self._hooks[hook_type].append(hook_class)
        self.logger.info(f"Stored applied hook: {hook_class.__name__}")
    
    def _clear_applied_hooks(self, hook_type: str):
        """Clear applied hooks by type."""
        if hook_type in self._hooks:
            self._hooks[hook_type] = []
    
    def _store_applied_hook(self, hook_type: str, hook_class: str):
        """Store specific applied hook."""
        self._hooks[hook_type].append(hook_class)
        self.logger.info(f"Stored specific applied hook: {hook_class.__name__}")
    
    def _clear_all_applied_hooks(self):
        """Clear all applied hooks."""
        self._hooks.clear()
        self.logger.info("Cleared all applied hooks")


# Global hooks registry
_global_hooks: Optional[MessagePackHooks] = None


def get_hooks(**kwargs) -> MessagePackHooks:
    """Get or create global hooks registry."""
    global _global_hooks
    if _global_hooks is None:
        _global_hooks = MessagePackHooks(**kwargs)
    return _global_hooks


def register_hook(hook_type: str, hook_class: type, **kwargs):
    """
    Register a hook using global registry.
    
    Args:
        hook_type: Type of hook
        hook_class: Hook class to register
        **kwargs: Additional parameters for hook class
    """
    global _global_hooks = get_global_hooks()
    _global_hooks.register_hook(hook_type, hook_class)
    print(f"Registered {hook_type} hook: {hook_class.__name__}")


# Convenience functions for global usage
async def call_hooks_before(hook_type: str, context: HookContext) -> List[Dict[str, Any]]:
    """Call all before hooks of a type using global registry."""
    global _global_hooks = get_global_hooks()
    return await _global_hooks.call_before(hook_type, context)


async def call_hooks_after(
    hook_type: str,
    context: HookContext,
    serialized_data: bytes,
    original_data: Any
) -> List[Dict[str, Any]]:
    """Call all after hooks of a type using global registry."""
    global _global_hooks = get_global_hooks()
    return await _global_hooks.call_after(hook_type, context, serialized_data, original_data)


def register_global_hook(hook_type: str, hook_class: type, **kwargs):
    """Register hook using global registry."""
    global _global_hooks = get_global_hooks()
    _global_hooks.register_hook(hook_type, hook_class, **kwargs)
    print(f"Registered global {hook_type} hook: {hook_class.__name__}")


# Legacy exports for backward compatibility
from .legacy_serializer import (
    LegacySerializer,
    get_legacy_serializer,
    get_legacy_hooks
)
