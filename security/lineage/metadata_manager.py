"""
Metadata Manager

This module provides comprehensive metadata management for data lineage
and provenance tracking with UUID-based identification.
"""

import asyncio
import logging
import time
import json
import hashlib
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
from collections import defaultdict, deque
import threading
import uuid
from datetime import datetime, timezone

from .exceptions import (
    MetadataError,
    ValidationError,
    StorageError,
    SerializationError,
    IntegrityError,
    AuditError
)


class MetadataType(Enum):
    """Types of metadata."""
    SOURCE = "source"
    TRANSFORMATION = "transformation"
    QUALITY = "quality"
    BUSINESS = "business"
    TECHNICAL = "technical"
    COMPLIANCE = "compliance"
    SECURITY = "security"
    PERFORMANCE = "performance"
    AUDIT = "audit"
    CUSTOM = "custom"


@dataclass
class MetadataEntry:
    """Metadata entry with comprehensive information."""
    object_id: str
    metadata_type: MetadataType
    key: str
    value: Any
    timestamp: datetime
    source_system: str
    user_id: Optional[str]
    version: int
    checksum: str
    tags: List[str]
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetadataSchema:
    """Schema definition for metadata validation."""
    field_name: str
    field_type: str
    required: bool = True
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    allowed_values: Optional[List[Any]] = None
    regex_pattern: Optional[str] = None
    default_value: Optional[Any] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)


class BaseMetadataStorage(ABC):
    """Abstract base class for metadata storage."""
    
    @abstractmethod
    async def store_metadata(self, entry: MetadataEntry) -> bool:
        """Store metadata entry."""
        pass
    
    @abstractmethod
    async def retrieve_metadata(self, object_id: str, metadata_type: Optional[MetadataType] = None) -> List[MetadataEntry]:
        """Retrieve metadata entries."""
        pass
    
    @abstractmethod
    async def update_metadata(self, object_id: str, key: str, value: Any, user_id: Optional[str] = None) -> bool:
        """Update metadata entry."""
        pass
    
    @abstractmethod
    async def delete_metadata(self, object_id: str, key: str, user_id: Optional[str] = None) -> bool:
        """Delete metadata entry."""
        pass
    
    @abstractmethod
    async def search_metadata(self, criteria: Dict[str, Any]) -> List[MetadataEntry]:
        """Search metadata entries."""
        pass
    
    @abstractmethod
    async def get_metadata_history(self, object_id: str, key: str) -> List[MetadataEntry]:
        """Get metadata change history."""
        pass


class InMemoryMetadataStorage(BaseMetadataStorage):
    """In-memory metadata storage for development and testing."""
    
    def __init__(self):
        self._metadata: Dict[str, List[MetadataEntry]] = defaultdict(list)
        self._lock = threading.RLock()
    
    async def store_metadata(self, entry: MetadataEntry) -> bool:
        """Store metadata entry in memory."""
        try:
            with self._lock:
                self._metadata[entry.object_id].append(entry)
                return True
        except Exception as e:
            raise StorageError(f"Failed to store metadata: {e}", "in_memory", entry.object_id)
    
    async def retrieve_metadata(self, object_id: str, metadata_type: Optional[MetadataType] = None) -> List[MetadataEntry]:
        """Retrieve metadata entries from memory."""
        try:
            with self._lock:
                entries = self._metadata.get(object_id, [])
                
                if metadata_type:
                    entries = [e for e in entries if e.metadata_type == metadata_type]
                
                # Update access count and last accessed
                for entry in entries:
                    entry.access_count += 1
                    entry.last_accessed = datetime.now(timezone.utc)
                
                return entries
        except Exception as e:
            raise StorageError(f"Failed to retrieve metadata: {e}", "in_memory", object_id)
    
    async def update_metadata(self, object_id: str, key: str, value: Any, user_id: Optional[str] = None) -> bool:
        """Update metadata entry in memory."""
        try:
            with self._lock:
                entries = self._metadata.get(object_id, [])
                
                for entry in entries:
                    if entry.key == key:
                        # Create new version
                        old_entry = entry
                        new_entry = MetadataEntry(
                            object_id=object_id,
                            metadata_type=entry.metadata_type,
                            key=key,
                            value=value,
                            timestamp=datetime.now(timezone.utc),
                            source_system=entry.source_system,
                            user_id=user_id,
                            version=entry.version + 1,
                            checksum=self._calculate_checksum(value),
                            tags=entry.tags,
                            expires_at=entry.expires_at,
                            created_by=entry.created_by,
                            updated_by=user_id,
                            metadata=entry.metadata
                        )
                        
                        # Replace old entry
                        entries.remove(entry)
                        entries.append(new_entry)
                        
                        return True
                
                return False
        except Exception as e:
            raise StorageError(f"Failed to update metadata: {e}", "in_memory", object_id)
    
    async def delete_metadata(self, object_id: str, key: str, user_id: Optional[str] = None) -> bool:
        """Delete metadata entry from memory."""
        try:
            with self._lock:
                entries = self._metadata.get(object_id, [])
                
                for entry in entries:
                    if entry.key == key:
                        entries.remove(entry)
                        return True
                
                return False
        except Exception as e:
            raise StorageError(f"Failed to delete metadata: {e}", "in_memory", object_id)
    
    async def search_metadata(self, criteria: Dict[str, Any]) -> List[MetadataEntry]:
        """Search metadata entries in memory."""
        try:
            with self._lock:
                results = []
                
                for object_id, entries in self._metadata.items():
                    for entry in entries:
                        if self._matches_criteria(entry, criteria):
                            results.append(entry)
                
                return results
        except Exception as e:
            raise StorageError(f"Failed to search metadata: {e}", "in_memory")
    
    async def get_metadata_history(self, object_id: str, key: str) -> List[MetadataEntry]:
        """Get metadata change history from memory."""
        try:
            with self._lock:
                entries = self._metadata.get(object_id, [])
                history = [e for e in entries if e.key == key]
                
                # Sort by timestamp
                history.sort(key=lambda x: x.timestamp)
                
                return history
        except Exception as e:
            raise StorageError(f"Failed to get metadata history: {e}", "in_memory", object_id)
    
    def _matches_criteria(self, entry: MetadataEntry, criteria: Dict[str, Any]) -> bool:
        """Check if entry matches search criteria."""
        for key, value in criteria.items():
            if hasattr(entry, key):
                entry_value = getattr(entry, key)
                if entry_value != value:
                    return False
            else:
                return False
        
        return True
    
    def _calculate_checksum(self, value: Any) -> str:
        """Calculate checksum for metadata value."""
        try:
            serialized = json.dumps(value, sort_keys=True, default=str)
            return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
        except Exception:
            return hashlib.sha256(str(value).encode('utf-8')).hexdigest()


class MetadataManager:
    """
    Comprehensive metadata manager for data lineage and provenance.
    
    This class provides metadata management with UUID-based identification,
    comprehensive validation, and audit trail capabilities.
    """
    
    def __init__(
        self,
        storage: Optional[BaseMetadataStorage] = None,
        logger: Optional[logging.Logger] = None,
        schemas: Optional[Dict[str, List[MetadataSchema]]] = None
    ):
        """
        Initialize metadata manager.
        
        Args:
            storage: Metadata storage backend
            logger: Logger instance
            schemas: Metadata schemas for validation
        """
        self.storage = storage or InMemoryMetadataStorage()
        self.logger = logger or logging.getLogger("MetadataManager")
        self.schemas = schemas or {}
        
        # State management
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 300  # 5 minutes
        self._lock = threading.RLock()
        
        # Initialize default schemas
        self._initialize_default_schemas()
        
        self.logger.info("MetadataManager initialized")
    
    def _initialize_default_schemas(self):
        """Initialize default metadata schemas."""
        # Source metadata schema
        self.schemas["source"] = [
            MetadataSchema(
                field_name="trace_id",
                field_type="string",
                required=True,
                description="Unique trace identifier for data lineage"
            ),
            MetadataSchema(
                field_name="source_name",
                field_type="string",
                required=True,
                description="Name of the data source"
            ),
            MetadataSchema(
                field_name="fetch_timestamp",
                field_type="datetime",
                required=True,
                description="Timestamp when data was fetched (UTC)"
            ),
            MetadataSchema(
                field_name="adapter_version",
                field_type="string",
                required=True,
                description="Version of the adapter that fetched the data"
            )
        ]
        
        # Transformation metadata schema
        self.schemas["transformation"] = [
            MetadataSchema(
                field_name="transformation_type",
                field_type="string",
                required=True,
                allowed_values=["filter", "aggregate", "join", "sort", "custom"]
            ),
            MetadataSchema(
                field_name="input_objects",
                field_type="array",
                required=True,
                description="List of input object IDs"
            ),
            MetadataSchema(
                field_name="output_object",
                field_type="string",
                required=True,
                description="Output object ID"
            ),
            MetadataSchema(
                field_name="transformation_logic",
                field_type="string",
                required=False,
                description="Description of transformation logic"
            )
        ]
        
        # Quality metadata schema
        self.schemas["quality"] = [
            MetadataSchema(
                field_name="completeness_score",
                field_type="float",
                required=True,
                min_value=0.0,
                max_value=1.0,
                description="Data completeness score (0-1)"
            ),
            MetadataSchema(
                field_name="accuracy_score",
                field_type="float",
                required=True,
                min_value=0.0,
                max_value=1.0,
                description="Data accuracy score (0-1)"
            ),
            MetadataSchema(
                field_name="consistency_score",
                field_type="float",
                required=True,
                min_value=0.0,
                max_value=1.0,
                description="Data consistency score (0-1)"
            ),
            MetadataSchema(
                field_name="validity_score",
                field_type="float",
                required=True,
                min_value=0.0,
                max_value=1.0,
                description="Data validity score (0-1)"
            )
        ]
    
    async def add_metadata(
        self,
        object_id: str,
        metadata: Dict[str, Any],
        metadata_type: MetadataType,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add metadata to an object.
        
        Args:
            object_id: Object identifier
            metadata: Metadata dictionary
            metadata_type: Type of metadata
            context: Additional context information
            
        Returns:
            Metadata entry ID
        """
        try:
            # Validate metadata against schema
            await self._validate_metadata(metadata, metadata_type)
            
            # Create metadata entries
            entries = []
            for key, value in metadata.items():
                entry = MetadataEntry(
                    object_id=object_id,
                    metadata_type=metadata_type,
                    key=key,
                    value=value,
                    timestamp=datetime.now(timezone.utc),
                    source_system=context.get("source_system", "unknown") if context else "unknown",
                    user_id=context.get("user_id") if context else None,
                    version=1,
                    checksum=self._calculate_checksum(value),
                    tags=context.get("tags", []) if context else [],
                    expires_at=None,
                    created_by=context.get("user_id") if context else None,
                    metadata=context or {}
                )
                
                entries.append(entry)
            
            # Store metadata entries
            for entry in entries:
                await self.storage.store_metadata(entry)
            
            # Update cache
            self._update_cache(object_id, metadata, metadata_type)
            
            self.logger.info(f"Added {len(entries)} metadata entries for object {object_id}")
            
            return str(uuid.uuid4())
            
        except Exception as e:
            self.logger.error(f"Failed to add metadata for object {object_id}: {e}")
            raise MetadataError(f"Failed to add metadata: {e}", None, object_id)
    
    async def get_metadata(
        self,
        object_id: str,
        metadata_type: Optional[MetadataType] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get metadata for an object.
        
        Args:
            object_id: Object identifier
            metadata_type: Type of metadata to retrieve
            use_cache: Whether to use cached metadata
            
        Returns:
            Metadata dictionary
        """
        try:
            # Check cache first
            if use_cache:
                cached_metadata = self._get_from_cache(object_id, metadata_type)
                if cached_metadata is not None:
                    return cached_metadata
            
            # Retrieve from storage
            entries = await self.storage.retrieve_metadata(object_id, metadata_type)
            
            # Convert to dictionary
            metadata = {}
            for entry in entries:
                metadata[entry.key] = entry.value
            
            # Update cache
            if use_cache:
                self._update_cache(object_id, metadata, metadata_type)
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to get metadata for object {object_id}: {e}")
            raise MetadataError(f"Failed to get metadata: {e}", None, object_id)
    
    async def update_metadata(
        self,
        object_id: str,
        key: str,
        value: Any,
        metadata_type: Optional[MetadataType] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Update metadata for an object.
        
        Args:
            object_id: Object identifier
            key: Metadata key
            value: New metadata value
            metadata_type: Type of metadata
            user_id: User ID making the update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate metadata value
            if metadata_type:
                await self._validate_metadata_value(key, value, metadata_type)
            
            # Update in storage
            success = await self.storage.update_metadata(object_id, key, value, user_id)
            
            if success:
                # Update cache
                cached_metadata = self._get_from_cache(object_id, metadata_type)
                if cached_metadata is not None:
                    cached_metadata[key] = value
                    self._update_cache(object_id, cached_metadata, metadata_type)
                
                self.logger.info(f"Updated metadata {key} for object {object_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to update metadata for object {object_id}: {e}")
            raise MetadataError(f"Failed to update metadata: {e}", key, object_id)
    
    async def delete_metadata(
        self,
        object_id: str,
        key: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Delete metadata for an object.
        
        Args:
            object_id: Object identifier
            key: Metadata key
            user_id: User ID making the deletion
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete from storage
            success = await self.storage.delete_metadata(object_id, key, user_id)
            
            if success:
                # Update cache
                cached_metadata = self._get_from_cache(object_id)
                if cached_metadata is not None and key in cached_metadata:
                    del cached_metadata[key]
                    self._update_cache(object_id, cached_metadata)
                
                self.logger.info(f"Deleted metadata {key} for object {object_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to delete metadata for object {object_id}: {e}")
            raise MetadataError(f"Failed to delete metadata: {e}", key, object_id)
    
    async def search_metadata(
        self,
        criteria: Dict[str, Any],
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search metadata entries.
        
        Args:
            criteria: Search criteria
            limit: Maximum number of results
            
        Returns:
            List of metadata entries
        """
        try:
            # Search in storage
            entries = await self.storage.search_metadata(criteria)
            
            # Apply limit
            if limit:
                entries = entries[:limit]
            
            # Convert to dictionaries
            results = []
            for entry in entries:
                result = {
                    "object_id": entry.object_id,
                    "metadata_type": entry.metadata_type.value,
                    "key": entry.key,
                    "value": entry.value,
                    "timestamp": entry.timestamp.isoformat(),
                    "source_system": entry.source_system,
                    "user_id": entry.user_id,
                    "version": entry.version,
                    "checksum": entry.checksum,
                    "tags": entry.tags,
                    "access_count": entry.access_count,
                    "last_accessed": entry.last_accessed.isoformat() if entry.last_accessed else None,
                    "created_by": entry.created_by,
                    "updated_by": entry.updated_by,
                    "metadata": entry.metadata
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search metadata: {e}")
            raise MetadataError(f"Failed to search metadata: {e}")
    
    async def get_metadata_history(
        self,
        object_id: str,
        key: str
    ) -> List[Dict[str, Any]]:
        """
        Get metadata change history.
        
        Args:
            object_id: Object identifier
            key: Metadata key
            
        Returns:
            List of historical metadata entries
        """
        try:
            # Get history from storage
            entries = await self.storage.get_metadata_history(object_id, key)
            
            # Convert to dictionaries
            history = []
            for entry in entries:
                history_entry = {
                    "object_id": entry.object_id,
                    "metadata_type": entry.metadata_type.value,
                    "key": entry.key,
                    "value": entry.value,
                    "timestamp": entry.timestamp.isoformat(),
                    "source_system": entry.source_system,
                    "user_id": entry.user_id,
                    "version": entry.version,
                    "checksum": entry.checksum,
                    "tags": entry.tags,
                    "created_by": entry.created_by,
                    "updated_by": entry.updated_by,
                    "metadata": entry.metadata
                }
                history.append(history_entry)
            
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get metadata history for object {object_id}: {e}")
            raise MetadataError(f"Failed to get metadata history: {e}", key, object_id)
    
    async def get_metadata_summary(
        self,
        object_id: str,
        time_range: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get metadata summary for an object.
        
        Args:
            object_id: Object identifier
            time_range: Time range filter (ISO format)
            
        Returns:
            Metadata summary
        """
        try:
            # Get all metadata
            entries = await self.storage.retrieve_metadata(object_id)
            
            # Apply time filter if specified
            if time_range:
                # Parse time range (ISO format: "2023-01-01T00:00:00Z/2023-12-31T23:59:59Z")
                start_time, end_time = self._parse_time_range(time_range)
                entries = [
                    e for e in entries
                    if start_time <= e.timestamp <= end_time
                ]
            
            # Group by type
            metadata_by_type = defaultdict(list)
            for entry in entries:
                metadata_by_type[entry.metadata_type.value].append(entry)
            
            # Calculate statistics
            summary = {
                "object_id": object_id,
                "total_entries": len(entries),
                "metadata_types": {},
                "latest_update": None,
                "total_access_count": sum(e.access_count for e in entries),
                "unique_sources": list(set(e.source_system for e in entries)),
                "unique_users": list(set(e.user_id for e in entries if e.user_id)),
                "time_range": time_range
            }
            
            # Add type-specific statistics
            for metadata_type, type_entries in metadata_by_type.items():
                summary["metadata_types"][metadata_type] = {
                    "count": len(type_entries),
                    "latest_update": max(e.timestamp for e in type_entries).isoformat(),
                    "total_access_count": sum(e.access_count for e in type_entries),
                    "unique_keys": list(set(e.key for e in type_entries))
                }
            
            # Overall latest update
            if entries:
                summary["latest_update"] = max(e.timestamp for e in entries).isoformat()
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get metadata summary for object {object_id}: {e}")
            raise MetadataError(f"Failed to get metadata summary: {e}", None, object_id)
    
    async def _validate_metadata(self, metadata: Dict[str, Any], metadata_type: MetadataType):
        """Validate metadata against schema."""
        schemas = self.schemas.get(metadata_type.value, [])
        
        for schema in schemas:
            if schema.required and schema.field_name not in metadata:
                raise ValidationError(
                    f"Required field '{schema.field_name}' is missing",
                    schema.field_name
                )
            
            if schema.field_name in metadata:
                value = metadata[schema.field_name]
                
                # Type validation
                if not self._validate_type(value, schema.field_type):
                    raise ValidationError(
                        f"Field '{schema.field_name}' has invalid type. Expected {schema.field_type}",
                        schema.field_name
                    )
                
                # Length validation
                if isinstance(value, str):
                    if schema.min_length and len(value) < schema.min_length:
                        raise ValidationError(
                            f"Field '{schema.field_name}' is too short. Minimum length: {schema.min_length}",
                            schema.field_name
                        )
                    
                    if schema.max_length and len(value) > schema.max_length:
                        raise ValidationError(
                            f"Field '{schema.field_name}' is too long. Maximum length: {schema.max_length}",
                            schema.field_name
                        )
                
                # Allowed values validation
                if schema.allowed_values and value not in schema.allowed_values:
                    raise ValidationError(
                        f"Field '{schema.field_name}' has invalid value. Allowed values: {schema.allowed_values}",
                        schema.field_name
                    )
                
                # Regex pattern validation
                if schema.regex_pattern and isinstance(value, str):
                    import re
                    if not re.match(schema.regex_pattern, value):
                        raise ValidationError(
                            f"Field '{schema.field_name}' does not match pattern: {schema.regex_pattern}",
                            schema.field_name
                        )
    
    async def _validate_metadata_value(self, key: str, value: Any, metadata_type: MetadataType):
        """Validate a single metadata value."""
        schemas = self.schemas.get(metadata_type.value, [])
        
        for schema in schemas:
            if schema.field_name == key:
                # Type validation
                if not self._validate_type(value, schema.field_type):
                    raise ValidationError(
                        f"Field '{key}' has invalid type. Expected {schema.field_type}",
                        key
                )
                
                # Other validations
                if isinstance(value, str):
                    if schema.min_length and len(value) < schema.min_length:
                        raise ValidationError(
                            f"Field '{key}' is too short. Minimum length: {schema.min_length}",
                            key
                        )
                    
                    if schema.max_length and len(value) > schema.max_length:
                        raise ValidationError(
                            f"Field '{key}' is too long. Maximum length: {schema.max_length}",
                            key
                        )
                
                if schema.allowed_values and value not in schema.allowed_values:
                    raise ValidationError(
                        f"Field '{key}' has invalid value. Allowed values: {schema.allowed_values}",
                        key
                    )
                
                break
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate value type."""
        type_mapping = {
            "string": str,
            "integer": int,
            "float": float,
            "boolean": bool,
            "array": list,
            "object": dict,
            "datetime": (str, datetime)
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type:
            return isinstance(value, expected_python_type)
        
        return True  # Unknown type, assume valid
    
    def _calculate_checksum(self, value: Any) -> str:
        """Calculate checksum for metadata value."""
        try:
            serialized = json.dumps(value, sort_keys=True, default=str)
            return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
        except Exception:
            return hashlib.sha256(str(value).encode('utf-8')).hexdigest()
    
    def _parse_time_range(self, time_range: str) -> tuple:
        """Parse ISO time range string."""
        try:
            from datetime import datetime, timezone
            
            if "/" in time_range:
                start_str, end_str = time_range.split("/")
                start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                return start_time, end_time
            else:
                # Single timestamp
                timestamp = datetime.fromisoformat(time_range.replace("Z", "+00:00"))
                return timestamp, timestamp
                
        except Exception as e:
            raise ValidationError(f"Invalid time range format: {time_range}")
    
    def _get_from_cache(self, object_id: str, metadata_type: Optional[MetadataType] = None) -> Optional[Dict[str, Any]]:
        """Get metadata from cache."""
        with self._lock:
            cache_key = f"{object_id}:{metadata_type.value if metadata_type else 'all'}"
            
            if cache_key in self._cache:
                cached_item = self._cache[cache_key]
                
                # Check TTL
                if time.time() - cached_item["timestamp"] < self._cache_ttl:
                    return cached_item["data"]
                else:
                    # Remove expired cache entry
                    del self._cache[cache_key]
            
            return None
    
    def _update_cache(self, object_id: str, metadata: Dict[str, Any], metadata_type: Optional[MetadataType] = None):
        """Update metadata cache."""
        with self._lock:
            cache_key = f"{object_id}:{metadata_type.value if metadata_type else 'all'}"
            
            self._cache[cache_key] = {
                "data": metadata,
                "timestamp": time.time()
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get metadata manager status."""
        return {
            "storage_type": type(self.storage).__name__,
            "schemas_configured": len(self.schemas),
            "cache_size": len(self._cache),
            "cache_ttl": self._cache_ttl,
            "timestamp": time.time()
        }


# Global metadata manager instance
_global_metadata_manager: Optional[MetadataManager] = None


def get_metadata_manager(**kwargs) -> MetadataManager:
    """
    Get or create global metadata manager.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global MetadataManager instance
    """
    global _global_metadata_manager
    if _global_metadata_manager is None:
        _global_metadata_manager = MetadataManager(**kwargs)
    return _global_metadata_manager
