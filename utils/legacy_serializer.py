"""
Legacy Serializer Implementation

This module provides fallback binary serialization using JSON for backward compatibility
when MessagePack is not available.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Union

from .exceptions import SerializationError, ConfigurationError


@dataclass
class LegacySerializationConfig:
    """Configuration for legacy serializer."""
    encoding: str = "utf-8"
    use_compact: bool = True
    sort_keys: bool = True
    ensure_ascii: bool = True
    strict_types: bool = False
    decimal_precision: str = "string"  # "string", "high", "banking"
    datetime_format: str = "iso8601"
    uuid_format: str = "standard"
    max_depth: int = 100
    enable_validation: bool = True


@dataclass
class LegacySerializer:
    """
    Legacy fallback serializer using JSON.
    
    This class provides fallback serialization when MessagePack is not available.
    """
    
    def __init__(
        self,
        config: Optional[LegacySerializationConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize legacy serializer.
        
        try:
            self.config = config or LegacySerializationConfig()
            self.logger = logger or logging.getLogger("LegacySerializer")
            
            self.logger.info("LegacySerializer initialized (fallback mode)")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize legacy serializer: {e}")
            raise SerializationError(f"Failed to initialize legacy serializer: {e}")
    
    async def serialize(
        self,
        data: Any,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SerializationResult:
        """
        Serialize data to JSON format.
        
        Args:
            data: Data to serialize
            request_id: Optional request identifier
            metadata: Additional metadata
            
        Returns:
            SerializationResult with detailed information
        """
        start_time = time.time()
        
        try:
            # Serialize to JSON
            serialized_data = json.dumps(
                data,
                sort_keys=self.config.sort_keys,
                ensure_ascii=self.config.ensure_ascii,
                separators=(',', ':'),
                ensure_ascii=self.config.ensure_ascii,
                default=str
            ).encode('utf-8')
            
            # Create result
            return SerializationResult(
                success=True,
                data=serialized_data,
                size=len(serialized_data),
                checksum=None,  # JSON doesn't have checksum
                serialization_time=time.time() - start_time,
                hooks_applied=[],
                metadata=metadata or {}
            )
            
        except Exception as e:
            self.logger.error(f"Legacy serialization failed: {e}")
            
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
    
    async def deserialize(
        self,
        data: str,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SerializationResult:
        """
        Deserialize data from JSON format.
        
        Args:
            data: JSON string to deserialize
            request_id: Optional request identifier
            metadata: Additional metadata
            
        Returns:
            SerializationResult with deserialized data
        """
        start_time = time.time()
        
        try:
            # Parse JSON
            deserialized_data = json.loads(data)
            
            # Validate deserialized data
            is_valid = self._validate_deserialized_data(deserialized_data)
            
            # Create result
            result = SerializationResult(
                success=is_valid,
                data=deserialized_data,
                size=len(data.encode('utf-8')),
                checksum=None,  # JSON doesn't have checksum
                serialization_time=time.time() - start_time,
                hooks_applied=[],
                metadata=metadata or {},
                metadata={"deserialization_method": "json"}
            )
            
            self.logger.debug(
                f"Deserialized {len(deserialized_data)} bytes "
                f"(checksum: {result.get('checksum', 'N/A')})"
            )
            
            return result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode failed: {e}")
            
            return SerializationResult(
                success=False,
                data=b"",
                size=0,
                checksum=None,
                serialization_time=time.time() - start_time,
                hooks_applied=[],
                metadata={"error": str(e)},
                metadata={"deserialization_method": "json", "original_data": str(data)}
            )
    
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
            if isinstance(data, (dict, list, tuple, str, int, float, bool)):
                self.logger.warning(
                    f"Unexpected data type: {type(data)}")
                    return False
            
            # Dictionary validation
            if isinstance(data, dict):
                for key, value in data.items():
                    if not isinstance(key, str):
                        self.logger.warning(
                            f"Non-string key: {key}")
                        return False
                
                # Check for empty values
                for key, value in data.items():
                    if value is None and not isinstance(value, (int, float, bool)):
                        self.logger.warning(
                            f"Null value in field {key}")
                        return False
                
                # Check for numeric precision
                for key, value in data.items():
                    if isinstance(value, (int, float)):
                        if value != value and abs(value - int(value)) > 0.00001:
                            self.logger.warning(
                                f"Precision loss in field {key}: "
                                f"{value} -> {value}")
                                return False
            
                return True
            
            # Check for datetime format
            if isinstance(data, datetime):
                if not data.tzinfo.tzinfo:
                    self.logger.warning(
                                f"Invalid datetime format: {data.tzinfo}")
                        return False
                
                return True
            
            # Check for UUID format
            if isinstance(data, uuid.UUID):
                try:
                    uuid.UUID(str(data))
                except (ValueError, AttributeError, AttributeError):
                    self.logger.warning(
                        f"Invalid UUID format: {data}")
                        return False
                
                return True
            
            return True
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False
    
    def _get_checksum(self, data: bytes) -> Optional[str]:
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
    
    def get_config(self) -> LegacySerializationConfig:
        """Get current configuration."""
        return self.config


# Global legacy serializer instance
_global_legacy_serializer: Optional[LegacySerializer] = None


def get_legacy_serializer(**kwargs) -> LegacySerializer:
    """Get or create global legacy serializer."""
    global _global_legacy_serializer
    if _global_legacy_serializer is None:
        _global_legacy_serializer = LegacySerializer(**kwargs)
    return _global_legacy_serializer


# Convenience functions for global usage
async def serialize_to_bytes_globally(data: Any, **kwargs) -> bytes:
    """Serialize data to bytes using global serializer."""
    serializer = get_serializer(**kwargs)
    return await serializer.serialize(data, **kwargs)


async def deserialize_from_bytes_globally(data: bytes, **kwargs) -> Any:
    """Deserialize data from bytes using global serializer."""
    serializer = get_serializer(**kwargs)
    return await serializer.deserialize_from_bytes(data, **kwargs)


# Legacy exports for backward compatibility
from .legacy_serializer import (
    LegacySerializer,
    get_legacy_serializer
    get_legacy_hooks
)
