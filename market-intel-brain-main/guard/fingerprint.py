"""
Schema Fingerprinting

This module provides schema fingerprinting functionality using hashlib
to create unique identifiers for JSON schemas and API responses.
"""

import hashlib
import json
import logging
import time
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .exceptions import FingerprintError, ConfigurationError


@dataclass
class FingerprintConfig:
    """Configuration for schema fingerprinting."""
    hash_algorithm: str = "sha256"  # sha256, md5, sha1
    include_metadata: bool = True
    include_types: bool = True
    include_nulls: bool = False
    sort_keys: bool = True
    normalize_whitespace: bool = True
    case_sensitive: bool = True
    max_depth: int = 100  # Maximum depth for nested objects


@dataclass
class SchemaFingerprint:
    """Schema fingerprint result."""
    hash: str
    algorithm: str
    timestamp: float
    schema_type: str
    field_count: int
    depth: int
    metadata: Dict[str, Any]


class BaseFingerprinter(ABC):
    """Abstract base class for schema fingerprinters."""
    
    @abstractmethod
    def create_fingerprint(self, data: Union[Dict, List], schema_type: str = "unknown") -> SchemaFingerprint:
        """Create fingerprint for schema data."""
        pass
    
    @abstractmethod
    def compare_fingerprints(self, fp1: SchemaFingerprint, fp2: SchemaFingerprint) -> bool:
        """Compare two fingerprints."""
        pass


class JSONFingerprinter(BaseFingerprinter):
    """
    JSON schema fingerprinter using hashlib.
    
    This class creates unique fingerprints for JSON schemas and API responses
    to detect changes and evolution over time.
    """
    
    def __init__(
        self,
        config: Optional[FingerprintConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize JSON fingerprinter.
        
        Args:
            config: Fingerprinting configuration
            logger: Logger instance
        """
        self.config = config or FingerprintConfig()
        self.logger = logger or logging.getLogger("JSONFingerprinter")
        
        # Validate hash algorithm
        valid_algorithms = ["sha256", "sha1", "md5", "sha512", "sha384"]
        if self.config.hash_algorithm not in valid_algorithms:
            raise ConfigurationError(
                "hash_algorithm",
                self.config.hash_algorithm,
                f"Must be one of: {valid_algorithms}"
            )
        
        self.logger.info(f"JSONFingerprinter initialized (algorithm={self.config.hash_algorithm})")
    
    def create_fingerprint(self, data: Union[Dict, List], schema_type: str = "unknown") -> SchemaFingerprint:
        """
        Create fingerprint for JSON data.
        
        Args:
            data: JSON data to fingerprint
            schema_type: Type of schema (e.g., "api_response", "database_schema")
            
        Returns:
            SchemaFingerprint with hash and metadata
        """
        try:
            # Normalize data for consistent fingerprinting
            normalized_data = self._normalize_data(data)
            
            # Create canonical JSON string
            canonical_json = self._create_canonical_json(normalized_data)
            
            # Generate hash
            hash_value = self._generate_hash(canonical_json)
            
            # Calculate metadata
            metadata = self._calculate_metadata(normalized_data)
            
            fingerprint = SchemaFingerprint(
                hash=hash_value,
                algorithm=self.config.hash_algorithm,
                timestamp=time.time(),
                schema_type=schema_type,
                field_count=metadata["field_count"],
                depth=metadata["max_depth"],
                metadata=metadata
            )
            
            self.logger.debug(
                f"Created fingerprint for {schema_type}: {hash_value[:16]}... "
                f"(fields: {metadata['field_count']}, depth: {metadata['max_depth']})"
            )
            
            return fingerprint
            
        except Exception as e:
            self.logger.error(f"Error creating fingerprint: {e}")
            raise FingerprintError(f"Failed to create fingerprint: {e}")
    
    def compare_fingerprints(self, fp1: SchemaFingerprint, fp2: SchemaFingerprint) -> bool:
        """
        Compare two fingerprints for equality.
        
        Args:
            fp1: First fingerprint
            fp2: Second fingerprint
            
        Returns:
            True if fingerprints are equal
        """
        return (
            fp1.hash == fp2.hash and
            fp1.algorithm == fp2.algorithm and
            fp1.schema_type == fp2.schema_type
        )
    
    def _normalize_data(self, data: Union[Dict, List]) -> Union[Dict, List]:
        """
        Normalize data for consistent fingerprinting.
        
        Args:
            data: Data to normalize
            
        Returns:
            Normalized data
        """
        if isinstance(data, dict):
            return self._normalize_dict(data)
        elif isinstance(data, list):
            return self._normalize_list(data)
        else:
            return data
    
    def _normalize_dict(self, data: Dict) -> Dict:
        """Normalize dictionary for consistent fingerprinting."""
        normalized = {}
        
        # Sort keys if configured
        items = sorted(data.items()) if self.config.sort_keys else data.items()
        
        for key, value in items:
            # Apply case sensitivity
            norm_key = key if self.config.case_sensitive else key.lower()
            
            # Handle null values
            if value is None and not self.config.include_nulls:
                continue
            
            # Normalize value
            norm_value = self._normalize_value(value)
            
            normalized[norm_key] = norm_value
        
        return normalized
    
    def _normalize_list(self, data: List) -> List:
        """Normalize list for consistent fingerprinting."""
        normalized = []
        
        for item in data:
            if item is None and not self.config.include_nulls:
                continue
            
            normalized.append(self._normalize_value(item))
        
        return normalized
    
    def _normalize_value(self, value: Any) -> Any:
        """Normalize a value for fingerprinting."""
        if isinstance(value, str):
            # Normalize whitespace in strings
            if self.config.normalize_whitespace:
                value = ' '.join(value.split())
            
            return value if self.config.case_sensitive else value.lower()
        
        elif isinstance(value, (dict, list)):
            return self._normalize_data(value)
        
        elif isinstance(value, (int, float, bool)):
            return value
        
        elif isinstance(value, (type(None),)):
            return None
        
        else:
            # For other types, convert to string representation
            str_value = str(value)
            if self.config.normalize_whitespace:
                str_value = ' '.join(str_value.split())
            
            return str_value if self.config.case_sensitive else str_value.lower()
    
    def _create_canonical_json(self, data: Union[Dict, List]) -> str:
        """
        Create canonical JSON representation.
        
        Args:
            data: Normalized data
            
        Returns:
            Canonical JSON string
        """
        try:
            # Use json.dumps with sorted keys and consistent formatting
            canonical_json = json.dumps(
                data,
                sort_keys=self.config.sort_keys,
                separators=(',', ':'),  # Compact representation
                ensure_ascii=True
            )
            
            return canonical_json
            
        except Exception as e:
            self.logger.error(f"Error creating canonical JSON: {e}")
            raise FingerprintError(f"Failed to create canonical JSON: {e}")
    
    def _generate_hash(self, data: str) -> str:
        """
        Generate hash for data string.
        
        Args:
            data: Data string to hash
            
        Returns:
            Hash string
        """
        try:
            # Get hash algorithm
            if self.config.hash_algorithm == "sha256":
                hash_obj = hashlib.sha256()
            elif self.config.hash_algorithm == "sha1":
                hash_obj = hashlib.sha1()
            elif self.config.hash_algorithm == "md5":
                hash_obj = hashlib.md5()
            elif self.config.hash_algorithm == "sha512":
                hash_obj = hashlib.sha512()
            elif self.config.hash_algorithm == "sha384":
                hash_obj = hashlib.sha384()
            else:
                raise ConfigurationError(
                    "hash_algorithm",
                    self.config.hash_algorithm,
                    "Unsupported algorithm"
                )
            
            # Generate hash
            hash_obj.update(data.encode('utf-8'))
            hash_value = hash_obj.hexdigest()
            
            return hash_value
            
        except Exception as e:
            self.logger.error(f"Error generating hash: {e}")
            raise FingerprintError(f"Failed to generate hash: {e}")
    
    def _calculate_metadata(self, data: Union[Dict, List]) -> Dict[str, Any]:
        """
        Calculate metadata for the data.
        
        Args:
            data: Data to analyze
            
        Returns:
            Metadata dictionary
        """
        metadata = {}
        
        if self.config.include_metadata:
            # Count fields/elements
            if isinstance(data, dict):
                metadata["field_count"] = len(data)
            elif isinstance(data, list):
                metadata["field_count"] = len(data)
            else:
                metadata["field_count"] = 1
            
            # Calculate depth
            metadata["max_depth"] = self._calculate_depth(data)
            
            # Calculate size
            metadata["data_size"] = len(str(data))
            
            # Add data type information
            metadata["data_type"] = type(data).__name__
            
            # Add hash algorithm info
            metadata["hash_algorithm"] = self.config.hash_algorithm
        
        return metadata
    
    def _calculate_depth(self, data: Any, current_depth: int = 0) -> int:
        """
        Calculate maximum depth of nested data structure.
        
        Args:
            data: Data to analyze
            current_depth: Current depth in recursion
            
        Returns:
            Maximum depth
        """
        if current_depth >= self.config.max_depth:
            return current_depth
        
        if isinstance(data, dict):
            if not data:
                return current_depth
            
            max_child_depth = current_depth
            for value in data.values():
                child_depth = self._calculate_depth(value, current_depth + 1)
                max_child_depth = max(max_child_depth, child_depth)
            
            return max_child_depth
        
        elif isinstance(data, list):
            if not data:
                return current_depth
            
            max_child_depth = current_depth
            for item in data:
                child_depth = self._calculate_depth(item, current_depth + 1)
                max_child_depth = max(max_child_depth, child_depth)
            
            return max_child_depth
        
        else:
            return current_depth
    
    def get_fingerprint_summary(self, fingerprint: SchemaFingerprint) -> str:
        """
        Get human-readable summary of fingerprint.
        
        Args:
            fingerprint: Schema fingerprint
            
        Returns:
            Summary string
        """
        return (
            f"Fingerprint: {fingerprint.hash[:16]}... "
            f"(type: {fingerprint.schema_type}, "
            f"fields: {fingerprint.field_count}, "
            f"depth: {fingerprint.depth}, "
            f"algorithm: {fingerprint.algorithm})"
        )


class SchemaRegistry:
    """
    Registry for storing and managing schema fingerprints.
    
    This class maintains a collection of known schemas and their
    fingerprints for comparison and evolution tracking.
    """
    
    def __init__(
        self,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize schema registry.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger("SchemaRegistry")
        self._fingerprints: Dict[str, Dict[str, SchemaFingerprint]] = {}
        self._fingerprints["api_response"] = {}
        self._fingerprints["database_schema"] = {}
        self._fingerprints["config_schema"] = {}
        
        self.logger.info("SchemaRegistry initialized")
    
    def register_fingerprint(
        self,
        provider: str,
        fingerprint: SchemaFingerprint,
        version: Optional[str] = None
    ):
        """
        Register a schema fingerprint.
        
        Args:
            provider: Provider name
            fingerprint: Schema fingerprint
            version: Schema version
        """
        schema_type = fingerprint.schema_type
        
        if schema_type not in self._fingerprints:
            self._fingerprints[schema_type] = {}
        
        if provider not in self._fingerprints[schema_type]:
            self._fingerprints[schema_type][provider] = {}
        
        key = version or "latest"
        self._fingerprints[schema_type][provider][key] = fingerprint
        
        self.logger.info(
            f"Registered fingerprint for {provider} ({schema_type}): {fingerprint.hash[:16]}..."
        )
    
    def get_fingerprint(
        self,
        provider: str,
        schema_type: str = "api_response",
        version: Optional[str] = None
    ) -> Optional[SchemaFingerprint]:
        """
        Get registered fingerprint.
        
        Args:
            provider: Provider name
            schema_type: Type of schema
            version: Schema version
            
        Returns:
            Registered fingerprint or None
        """
        if (
            schema_type not in self._fingerprints or
            provider not in self._fingerprints[schema_type]
        ):
            return None
        
        key = version or "latest"
        return self._fingerprints[schema_type][provider].get(key)
    
    def get_all_fingerprints(
        self,
        schema_type: Optional[str] = None
    ) -> Dict[str, Dict[str, SchemaFingerprint]]:
        """
        Get all registered fingerprints.
        
        Args:
            schema_type: Filter by schema type
            
        Returns:
            All fingerprints (optionally filtered)
        """
        if schema_type:
            return {schema_type: self._fingerprints.get(schema_type, {})}
        
        return self._fingerprints.copy()
    
    def compare_with_registered(
        self,
        provider: str,
        fingerprint: SchemaFingerprint,
        schema_type: str = "api_response",
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare fingerprint with registered version.
        
        Args:
            provider: Provider name
            fingerprint: New fingerprint to compare
            schema_type: Type of schema
            version: Version to compare against
            
        Returns:
            Comparison result
        """
        registered_fp = self.get_fingerprint(provider, schema_type, version)
        
        if not registered_fp:
            return {
                "provider": provider,
                "schema_type": schema_type,
                "version": version,
                "registered": False,
                "matches": False,
                "message": "No registered fingerprint found"
            }
        
        matches = self._compare_fingerprints(registered_fp, fingerprint)
        
        return {
            "provider": provider,
            "schema_type": schema_type,
            "version": version,
            "registered": True,
            "matches": matches,
            "registered_hash": registered_fp.hash,
            "new_hash": fingerprint.hash,
            "registered_timestamp": registered_fp.timestamp,
            "new_timestamp": fingerprint.timestamp,
            "time_diff": fingerprint.timestamp - registered_fp.timestamp
        }
    
    def _compare_fingerprints(self, fp1: SchemaFingerprint, fp2: SchemaFingerprint) -> bool:
        """Compare two fingerprints."""
        return (
            fp1.hash == fp2.hash and
            fp1.algorithm == fp2.algorithm
        )
    
    def get_provider_versions(self, provider: str, schema_type: str = "api_response") -> List[str]:
        """
        Get all versions for a provider.
        
        Args:
            provider: Provider name
            schema_type: Type of schema
            
        Returns:
            List of available versions
        """
        if (
            schema_type not in self._fingerprints or
            provider not in self._fingerprints[schema_type]
        ):
            return []
        
        return list(self._fingerprints[schema_type][provider].keys())
    
    def cleanup_old_fingerprints(self, max_age_days: int = 30):
        """
        Clean up old fingerprints.
        
        Args:
            max_age_days: Maximum age in days
        """
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 3600
        
        removed_count = 0
        
        for schema_type in self._fingerprints:
            for provider in list(self._fingerprints[schema_type].keys()):
                for version in list(self._fingerprints[schema_type][provider].keys()):
                    fingerprint = self._fingerprints[schema_type][provider][version]
                    
                    if current_time - fingerprint.timestamp > max_age_seconds:
                        del self._fingerprints[schema_type][provider][version]
                        removed_count += 1
        
        self.logger.info(f"Cleaned up {removed_count} old fingerprints")


# Global fingerprinter instance
_global_fingerprinter: Optional[JSONFingerprinter] = None


def get_fingerprinter(**kwargs) -> JSONFingerprinter:
    """
    Get or create the global fingerprinter.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global JSONFingerprinter instance
    """
    global _global_fingerprinter
    if _global_fingerprinter is None:
        _global_fingerprinter = JSONFingerprinter(**kwargs)
    return _global_fingerprinter


# Utility functions
def create_fingerprint_from_json(
    json_string: str,
    config: Optional[FingerprintConfig] = None
) -> SchemaFingerprint:
    """
    Create fingerprint from JSON string.
    
    Args:
        json_string: JSON string to fingerprint
        config: Fingerprinting configuration
        
    Returns:
        SchemaFingerprint
    """
    try:
        data = json.loads(json_string)
        fingerprinter = get_fingerprinter(config)
        return fingerprinter.create_fingerprint(data, "json_string")
    except json.JSONDecodeError as e:
        raise FingerprintError(f"Invalid JSON: {e}")


def compare_json_schemas(
    json1: str,
    json2: str,
    config: Optional[FingerprintConfig] = None
) -> Dict[str, Any]:
    """
    Compare two JSON schemas.
    
    Args:
        json1: First JSON string
        json2: Second JSON string
        config: Fingerprinting configuration
        
    Returns:
        Comparison result
    """
    fingerprinter = get_fingerprinter(config)
    
    fp1 = create_fingerprint_from_json(json1, config)
    fp2 = create_fingerprint_from_json(json2, config)
    
    return {
        "json1_hash": fp1.hash,
        "json2_hash": fp2.hash,
        "identical": fp1.hash == fp2.hash,
        "algorithm": fp1.algorithm,
        "json1_metadata": fp1.metadata,
        "json2_metadata": fp2.metadata
    }
