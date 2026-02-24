"""
Schema Guard

This module provides a comprehensive schema evolution guard system that
monitors API responses, detects schema changes, and alerts developers.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum

from .fingerprint import SchemaFingerprint, get_fingerprinter, SchemaRegistry
from .diff_analyzer import DiffResult, get_analyzer
from .exceptions import (
    SchemaDriftError,
    SchemaValidationError,
    AlertError,
    InterceptorError
)


class AlertLevel(Enum):
    """Alert severity levels."""
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class GuardConfig:
    """Configuration for schema guard."""
    enable_validation: bool = True
    enable_fingerprinting: bool = True
    enable_diff_analysis: bool = True
    enable_alerting: bool = True
    enable_interception: bool = True
    alert_on_new_fields: bool = True
    alert_on_removed_fields: bool = True
    alert_on_type_changes: bool = True
    alert_on_breaking_changes: bool = True
    log_level: str = "INFO"
    storage_backend: str = "memory"  # "memory" or "redis"
    redis_url: str = "redis://localhost:6379"
    max_stored_versions: int = 10


@dataclass
class ValidationResult:
    """Result of schema validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    field_count: int
    validation_time: float


@dataclass
class GuardStatus:
    """Current status of the schema guard."""
    providers_monitored: int
    schemas_stored: int
    alerts_sent: int
    drifts_detected: int
    last_check: float
    uptime: float


class SchemaGuard:
    """
    Comprehensive schema evolution guard system.
    
    This class monitors API responses, detects schema changes,
    and provides early warnings to developers without blocking operations.
    """
    
    def __init__(
        self,
        config: Optional[GuardConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize schema guard.
        
        Args:
            config: Guard configuration
            logger: Logger instance
        """
        self.config = config or GuardConfig()
        self.logger = logger or logging.getLogger("SchemaGuard")
        
        # Initialize components
        self.fingerprinter = get_fingerprinter()
        self.analyzer = get_analyzer()
        self.registry = SchemaRegistry(self.logger)
        
        # Alert callbacks
        self.alert_callbacks: Dict[AlertLevel, List[Callable]] = {
            AlertLevel.CRITICAL: [],
            AlertLevel.ERROR: [],
            AlertLevel.WARNING: [],
            AlertLevel.INFO: []
        }
        
        # Interceptor functions
        self.interceptors: List[Callable] = []
        
        # Statistics
        self._stats = {
            'providers_monitored': 0,
            'schemas_stored': 0,
            'alerts_sent': 0,
            'drifts_detected': 0,
            'validations_performed': 0,
            'interceptions_performed': 0,
            'start_time': time.time()
        }
        
        # Storage
        self._storage = None
        if self.config.storage_backend == "redis":
            self._init_redis_storage()
        
        self.logger.info("SchemaGuard initialized")
    
    def _init_redis_storage(self):
        """Initialize Redis storage backend."""
        try:
            import redis.asyncio as redis
            self._storage = redis.from_url(self.config.redis_url)
            self.logger.info(f"Connected to Redis storage: {self.config.redis_url}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis storage: {e}")
            raise Exception(f"Redis storage initialization failed: {e}")
    
    async def start(self):
        """Start the schema guard."""
        self.logger.info("SchemaGuard started")
    
    async def stop(self):
        """Stop the schema guard."""
        if self._storage:
            await self._storage.close()
            self._storage = None
        
        self.logger.info("SchemaGuard stopped")
    
    def register_alert_callback(self, level: AlertLevel, callback: Callable):
        """
        Register callback for alert level.
        
        Args:
            level: Alert level
            callback: Callback function
        """
        self.alert_callbacks[level].append(callback)
        self.logger.info(f"Registered alert callback for level: {level}")
    
    def register_interceptor(self, interceptor: Callable):
        """
        Register schema interceptor.
        
        Args:
            interceptor: Interceptor function
        """
        self.interceptors.append(interceptor)
        self.logger.info("Registered schema interceptor")
    
    async def validate_schema(
        self,
        provider: str,
        schema_data: Any,
        schema_version: str = "current",
        expected_fingerprint: Optional[SchemaFingerprint] = None
    ) -> ValidationResult:
        """
        Validate schema data against expected fingerprint.
        
        Args:
            provider: Provider name
            schema_data: Schema data to validate
            schema_version: Schema version
            expected_fingerprint: Expected fingerprint for comparison
            
        Returns:
            ValidationResult with detailed results
        """
        if not self.config.enable_validation:
            return ValidationResult(is_valid=True, errors=[], warnings=[], field_count=0, validation_time=time.time())
        
        start_time = time.time()
        errors = []
        warnings = []
        
        try:
            # Create fingerprint for current schema
            current_fingerprint = self.fingerprinter.create_fingerprint(schema_data, "validation")
            
            # Validate against expected fingerprint if provided
            if expected_fingerprint:
                if current_fingerprint.hash != expected_fingerprint.hash:
                    errors.append(
                        f"Schema fingerprint mismatch: expected {expected_fingerprint.hash[:16]}..., "
                        f"got {current_fingerprint.hash[:16]}..."
                    )
            
            # Run through interceptors
            if self.config.enable_interception:
                for interceptor in self.interceptors:
                    try:
                        result = await self._call_interceptor(
                            interceptor, provider, schema_data, current_fingerprint
                        )
                        if not result.get("valid", True):
                            errors.extend(result.get("errors", []))
                        warnings.extend(result.get("warnings", []))
                    except Exception as e:
                        self.logger.error(f"Interceptor error: {e}")
                        errors.append(f"Interceptor failed: {e}")
            
            # Field count
            field_count = current_fingerprint.field_count
            
            self._stats['validations_performed'] += 1
            
            validation_time = time.time() - start_time
            
            result = ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                field_count=field_count,
                validation_time=validation_time
            )
            
            # Log validation result
            if result.is_valid:
                self.logger.debug(f"Schema validation passed for {provider}")
            else:
                self.logger.warning(f"Schema validation failed for {provider}: {errors}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error validating schema: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {e}"],
                warnings=[],
                field_count=0,
                validation_time=time.time() - start_time
            )
    
    async def detect_schema_drift(
        self,
        provider: str,
        current_schema: Any,
        current_version: str = "current"
    ) -> DiffResult:
        """
        Detect schema drift by comparing with stored fingerprint.
        
        Args:
            provider: Provider name
            current_schema: Current schema data
            current_version: Current version
            
        Returns:
            DiffResult with detailed analysis
        """
        if not self.config.enable_fingerprinting:
            return DiffResult(
                provider=provider,
                schema_type="api_response",
                old_version="unknown",
                new_version=current_version,
                has_changes=False,
                changes=[],
                summary={},
                analysis_timestamp=time.time(),
                metadata={"fingerprinting_disabled": True}
            )
        
        try:
            # Get stored fingerprint
            stored_fingerprint = self.registry.get_fingerprint(provider, "api_response")
            
            if not stored_fingerprint:
                # No stored fingerprint, store current one
                current_fingerprint = self.fingerprinter.create_fingerprint(current_schema, "api_response")
                await self._store_fingerprint(provider, current_fingerprint, current_version)
                
                self._stats['schemas_stored'] += 1
                self._stats['providers_monitored'] += 1
                
                return DiffResult(
                    provider=provider,
                    schema_type="api_response",
                    old_version="none",
                    new_version=current_version,
                    has_changes=False,
                    changes=[],
                    summary={},
                    analysis_timestamp=time.time(),
                    metadata={"first_time": True}
                )
            
            # Compare with stored fingerprint
            diff_result = self.analyzer.analyze_diff(
                old_data=stored_fingerprint.metadata.get("original_data", {}),
                new_data=current_schema,
                provider=provider,
                schema_type="api_response",
                old_version=stored_fingerprint.metadata.get("version", "unknown"),
                new_version=current_version
            )
            
            if diff_result.has_changes:
                self._stats['drifts_detected'] += 1
                
                # Send alerts for schema drift
                await self._send_drift_alert(provider, diff_result)
                
                # Update stored fingerprint
                new_fingerprint = self.fingerprinter.create_fingerprint(current_schema, "api_response")
                await self._store_fingerprint(provider, new_fingerprint, current_version)
            
            return diff_result
            
        except Exception as e:
            self.logger.error(f"Error detecting schema drift: {e}")
            raise SchemaDriftError(f"Failed to detect schema drift: {e}")
    
    async def monitor_api_response(
        self,
        provider: str,
        response_data: Any,
        response_metadata: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Monitor API response for schema validation and drift detection.
        
        Args:
            provider: Provider name
            response_data: API response data
            response_metadata: Additional metadata
            
        Returns:
            ValidationResult with monitoring results
        """
        try:
            # Validate the response
            validation_result = await self.validate_schema(provider, response_data)
            
            # Detect drift
            if self.config.enable_diff_analysis:
                drift_result = await self.detect_schema_drift(provider, response_data)
                
                if drift_result.has_changes:
                    self.logger.warning(
                        f"Schema drift detected for {provider}: "
                        f"{self.analyzer.get_change_summary(drift_result)}"
                    )
            
            # Store fingerprint for future comparisons
            if self.config.enable_fingerprinting:
                fingerprint = self.fingerprinter.create_fingerprint(response_data, "api_response")
                await self._store_fingerprint(provider, fingerprint, "latest")
                self._stats['schemas_stored'] += 1
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error monitoring API response: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Monitoring error: {e}"],
                warnings=[],
                field_count=0,
                validation_time=time.time()
            )
    
    async def _call_interceptor(
        self,
        interceptor: Callable,
        provider: str,
        schema_data: Any,
        fingerprint: SchemaFingerprint
    ) -> Dict[str, Any]:
        """
        Call schema interceptor with error handling.
        
        Args:
            interceptor: Interceptor function
            provider: Provider name
            schema_data: Schema data
            fingerprint: Schema fingerprint
            
        Returns:
            Interceptor result
        """
        try:
            if asyncio.iscoroutinefunction(interceptor):
                result = await interceptor(provider, schema_data, fingerprint)
            else:
                result = interceptor(provider, schema_data, fingerprint)
            
            self._stats['interceptions_performed'] += 1
            return result or {"valid": True}
            
        except Exception as e:
            self.logger.error(f"Interceptor error: {e}")
            return {"valid": False, "errors": [str(e)]}
    
    async def _store_fingerprint(
        self,
        provider: str,
        fingerprint: SchemaFingerprint,
        version: str
    ):
        """Store fingerprint in storage backend."""
        try:
            if self.config.storage_backend == "redis":
                # Store in Redis
                key = f"schema_fingerprint:{provider}:{version}"
                fingerprint_data = {
                    "hash": fingerprint.hash,
                    "algorithm": fingerprint.algorithm,
                    "timestamp": fingerprint.timestamp,
                    "schema_type": fingerprint.schema_type,
                    "field_count": fingerprint.field_count,
                    "depth": fingerprint.depth,
                    "metadata": fingerprint.metadata,
                    "version": version,
                    "original_data": fingerprint.metadata.get("original_data", {})
                }
                
                import json
                await self._storage.setex(
                    key,
                    3600 * 24,  # 24 hours TTL
                    json.dumps(fingerprint_data)
                )
            
            else:
                # Store in memory (registry)
                self.registry.register_fingerprint(provider, fingerprint, version)
            
        except Exception as e:
            self.logger.error(f"Error storing fingerprint: {e}")
    
    async def _send_drift_alert(self, provider: str, diff_result: DiffResult):
        """Send alerts for detected schema drift."""
        if not self.config.enable_alerting:
            return
        
        try:
            # Categorize changes
            categorized = self.analyzer.categorize_changes(diff_result.changes)
            
            # Determine alert level
            alert_level = self._determine_alert_level(categorized)
            
            # Create alert message
            alert_message = self._create_alert_message(provider, diff_result, categorized)
            
            # Send to all registered callbacks
            for callback in self.alert_callbacks[alert_level]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(provider, alert_level, alert_message, diff_result)
                    else:
                        callback(provider, alert_level, alert_message, diff_result)
                    
                    self._stats['alerts_sent'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Alert callback error: {e}")
            
            # Log the alert
            log_level = getattr(logging, alert_level.lower(), logging.INFO)
            self.logger.log(log_level, f"Schema drift alert: {alert_message}")
            
        except Exception as e:
            self.logger.error(f"Error sending drift alert: {e}")
            raise AlertError(f"Failed to send drift alert: {e}")
    
    def _determine_alert_level(self, categorized: Dict[str, List]) -> AlertLevel:
        """Determine alert level based on categorized changes."""
        if categorized["breaking"]:
            return AlertLevel.CRITICAL
        elif categorized["unknown"]:
            return AlertLevel.ERROR
        elif categorized["non_breaking"]:
            return AlertLevel.WARNING
        else:
            return AlertLevel.INFO
    
    def _create_alert_message(
        self,
        provider: str,
        diff_result: DiffResult,
        categorized: Dict[str, List]
    ) -> str:
        """Create alert message for schema drift."""
        summary = self.analyzer.get_change_summary(diff_result)
        
        message_parts = [
            f"Schema drift detected for provider '{provider}'",
            f"Changes: {summary}",
            f"Breaking changes: {len(categorized['breaking'])}",
            f"Non-breaking changes: {len(categorized['non_breaking'])}"
        ]
        
        return " | ".join(message_parts)
    
    async def get_provider_status(self, provider: str) -> Dict[str, Any]:
        """Get status for a specific provider."""
        try:
            # Get stored fingerprint
            fingerprint = self.registry.get_fingerprint(provider, "api_response")
            
            # Get all versions
            versions = self.registry.get_provider_versions(provider, "api_response")
            
            return {
                "provider": provider,
                "monitored": fingerprint is not None,
                "current_version": versions[-1] if versions else "none",
                "available_versions": versions,
                "last_fingerprint": fingerprint.hash if fingerprint else None,
                "last_check": fingerprint.timestamp if fingerprint else None,
                "field_count": fingerprint.field_count if fingerprint else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting provider status: {e}")
            return {"provider": provider, "error": str(e)}
    
    def get_guard_status(self) -> GuardStatus:
        """Get overall guard status."""
        uptime = time.time() - self._stats['start_time']
        
        return GuardStatus(
            providers_monitored=self._stats['providers_monitored'],
            schemas_stored=self._stats['schemas_stored'],
            alerts_sent=self._stats['alerts_sent'],
            drifts_detected=self._stats['drifts_detected'],
            last_check=time.time(),
            uptime=uptime
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get guard statistics."""
        uptime = time.time() - self._stats['start_time']
        
        return {
            "uptime": uptime,
            "providers_monitored": self._stats['providers_monitored'],
            "schemas_stored": self._stats['schemas_stored'],
            "alerts_sent": self._stats['alerts_sent'],
            "drifts_detected": self._stats['drifts_detected'],
            "validations_performed": self._stats['validations_performed'],
            "interceptions_performed": self._stats['interceptions_performed'],
            "config": {
                "enable_validation": self.config.enable_validation,
                "enable_fingerprinting": self.config.enable_fingerprinting,
                "enable_diff_analysis": self.config.enable_diff_analysis,
                "enable_alerting": self.config.enable_alerting,
                "enable_interception": self.config.enable_interception,
                "alert_on_new_fields": self.config.alert_on_new_fields,
                "alert_on_removed_fields": self.config.alert_on_removed_fields,
                "alert_on_type_changes": self.config.alert_on_type_changes,
                "alert_on_breaking_changes": self.config.alert_on_breaking_changes
            }
        }
    
    def get_config(self) -> GuardConfig:
        """Get current configuration."""
        return self.config


# Global schema guard instance
_global_guard: Optional[SchemaGuard] = None


def get_guard(**kwargs) -> SchemaGuard:
    """
    Get or create the global schema guard.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global SchemaGuard instance
    """
    global _global_guard
    if _global_guard is None:
        _global_guard = SchemaGuard(**kwargs)
    return _global_guard


# Convenience functions for global usage
async def validate_schema_globally(provider: str, schema_data: Any) -> ValidationResult:
    """Validate schema using global guard."""
    guard = get_guard()
    return await guard.validate_schema(provider, schema_data)


async def monitor_response_globally(provider: str, response_data: Any) -> ValidationResult:
    """Monitor API response using global guard."""
    guard = get_guard()
    return await guard.monitor_api_response(provider, response_data)


def register_alert_callback_globally(level: AlertLevel, callback: Callable):
    """Register alert callback using global guard."""
    guard = get_guard()
    guard.register_alert_callback(level, callback)


def register_interceptor_globally(interceptor: Callable):
    """Register interceptor using global guard."""
    guard = get_guard()
    guard.register_interceptor(interceptor)
