"""
Security Configuration - Environment-based Security Settings

Enterprise-grade security configuration with environment variable
integration and zero-trust principles.
"""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

try:
    from pydantic import BaseSettings, Field, validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    
    # Fallback implementation
    class BaseSettings:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    def Field(default=None, **kwargs):
        return default
    
    def validator(field_name, *args, **kwargs):
        def decorator(func):
            return func
        return decorator


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms."""
    AES_256_GCM = "aes-256-gcm"
    AES_256_CBC = "aes-256-cbc"
    CHACHA20_POLY1305 = "chacha20-poly1305"


class AuditLevel(Enum):
    """Audit logging levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AuthMethod(Enum):
    """Authentication methods."""
    JWT = "jwt"
    MTLS = "mtls"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"


@dataclass
class SecurityConfig:
    """Enterprise security configuration."""
    
    # Feature flags from environment
    enable_encryption: bool = field(default_factory=lambda: os.getenv("ENABLE_ENCRYPTION", "true").lower() == "true")
    enable_audit_logging: bool = field(default_factory=lambda: os.getenv("ENABLE_AUDIT_LOGGING", "true").lower() == "true")
    enable_zero_trust: bool = field(default_factory=lambda: os.getenv("ENABLE_ZERO_TRUST", "true").lower() == "true")
    enable_observability: bool = field(default_factory=lambda: os.getenv("ENABLE_OBSERVABILITY", "true").lower() == "true")
    
    # Encryption configuration
    encryption_algorithm: EncryptionAlgorithm = field(default=EncryptionAlgorithm.AES_256_GCM)
    encryption_key: Optional[str] = field(default_factory=lambda: os.getenv("ENCRYPTION_KEY"))
    key_rotation_interval_hours: int = field(default_factory=lambda: int(os.getenv("KEY_ROTATION_INTERVAL_HOURS", "24")))
    secure_memory_pool_size: int = field(default_factory=lambda: int(os.getenv("SECURE_MEMORY_POOL_SIZE", "100")))
    
    # Audit logging configuration
    audit_level: AuditLevel = field(default_factory=lambda: AuditLevel(os.getenv("AUDIT_LEVEL", "medium")))
    audit_buffer_size: int = field(default_factory=lambda: int(os.getenv("AUDIT_BUFFER_SIZE", "1000")))
    audit_flush_interval_seconds: int = field(default_factory=lambda: int(os.getenv("AUDIT_FLUSH_INTERVAL_SECONDS", "5")))
    audit_retention_days: int = field(default_factory=lambda: int(os.getenv("AUDIT_RETENTION_DAYS", "30")))
    audit_log_path: str = field(default_factory=lambda: os.getenv("AUDIT_LOG_PATH", "logs/audit.log"))
    audit_siem_endpoint: Optional[str] = field(default_factory=lambda: os.getenv("AUDIT_SIEM_ENDPOINT"))
    
    # Zero Trust configuration
    auth_method: AuthMethod = field(default_factory=lambda: AuthMethod(os.getenv("AUTH_METHOD", "jwt")))
    jwt_secret_key: Optional[str] = field(default_factory=lambda: os.getenv("JWT_SECRET_KEY"))
    jwt_expiry_hours: int = field(default_factory=lambda: int(os.getenv("JWT_EXPIRY_HOURS", "1")))
    mtls_cert_path: Optional[str] = field(default_factory=lambda: os.getenv("MTLS_CERT_PATH"))
    mtls_key_path: Optional[str] = field(default_factory=lambda: os.getenv("MTLS_KEY_PATH"))
    mtls_ca_path: Optional[str] = field(default_factory=lambda: os.getenv("MTLS_CA_PATH"))
    
    # Service-to-service authentication
    service_id: str = field(default_factory=lambda: os.getenv("SERVICE_ID", "market-intel-brain"))
    service_namespace: str = field(default_factory=lambda: os.getenv("SERVICE_NAMESPACE", "production"))
    trusted_services: List[str] = field(default_factory=lambda: os.getenv("TRUSTED_SERVICES", "ingestion,ai,api").split(","))
    
    # Observability configuration
    otel_service_name: str = field(default_factory=lambda: os.getenv("OTEL_SERVICE_NAME", "market-intel-brain"))
    otel_service_version: str = field(default_factory=lambda: os.getenv("OTEL_SERVICE_VERSION", "1.0.0"))
    otel_endpoint: Optional[str] = field(default_factory=lambda: os.getenv("OTEL_ENDPOINT"))
    otel_headers: Dict[str, str] = field(default_factory=lambda: dict(
        header.split("=") for header in os.getenv("OTEL_HEADERS", "").split(",") if "=" in header
    ))
    
    # Performance and security thresholds
    max_encryption_time_ms: float = field(default_factory=lambda: float(os.getenv("MAX_ENCRYPTION_TIME_MS", "50")))
    max_auth_time_ms: float = field(default_factory=lambda: float(os.getenv("MAX_AUTH_TIME_MS", "100")))
    max_audit_log_time_ms: float = field(default_factory=lambda: float(os.getenv("MAX_AUDIT_LOG_TIME_MS", "10")))
    
    # Rate limiting
    auth_rate_limit_per_second: int = field(default_factory=lambda: int(os.getenv("AUTH_RATE_LIMIT_PER_SECOND", "100")))
    encryption_rate_limit_per_second: int = field(default_factory=lambda: int(os.getenv("ENCRYPTION_RATE_LIMIT_PER_SECOND", "1000")))
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_encryption_config()
        self._validate_audit_config()
        self._validate_zero_trust_config()
    
    def _validate_encryption_config(self):
        """Validate encryption configuration."""
        if self.enable_encryption:
            if not self.encryption_key:
                raise ValueError("ENCRYPTION_KEY is required when ENABLE_ENCRYPTION=true")
            
            if len(self.encryption_key) not in [32, 44, 64]:  # 256-bit key in different formats
                raise ValueError("ENCRYPTION_KEY must be 32, 44, or 64 characters long")
            
            if self.key_rotation_interval_hours < 1:
                raise ValueError("KEY_ROTATION_INTERVAL_HOURS must be at least 1")
        else:
            # Skip validation when encryption is disabled
            pass
    
    def _validate_audit_config(self):
        """Validate audit logging configuration."""
        if self.enable_audit_logging:
            if self.audit_buffer_size < 100:
                raise ValueError("AUDIT_BUFFER_SIZE must be at least 100")
            
            if self.audit_flush_interval_seconds < 1:
                raise ValueError("AUDIT_FLUSH_INTERVAL_SECONDS must be at least 1")
            
            if self.audit_retention_days < 1:
                raise ValueError("AUDIT_RETENTION_DAYS must be at least 1")
    
    def _validate_zero_trust_config(self):
        """Validate zero trust configuration."""
        if self.enable_zero_trust:
            if self.auth_method == AuthMethod.JWT and not self.jwt_secret_key:
                raise ValueError("JWT_SECRET_KEY is required when AUTH_METHOD=jwt")
            
            if self.auth_method == AuthMethod.MTLS:
                if not self.mtls_cert_path or not self.mtls_key_path:
                    raise ValueError("MTLS_CERT_PATH and MTLS_KEY_PATH are required when AUTH_METHOD=mtls")
            
            if not self.service_id:
                raise ValueError("SERVICE_ID is required when ENABLE_ZERO_TRUST=true")
    
    @classmethod
    def from_env(cls) -> "SecurityConfig":
        """Create configuration from environment variables."""
        return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "enable_encryption": self.enable_encryption,
            "enable_audit_logging": self.enable_audit_logging,
            "enable_zero_trust": self.enable_zero_trust,
            "enable_observability": self.enable_observability,
            "encryption_algorithm": self.encryption_algorithm.value,
            "key_rotation_interval_hours": self.key_rotation_interval_hours,
            "secure_memory_pool_size": self.secure_memory_pool_size,
            "audit_level": self.audit_level.value,
            "audit_buffer_size": self.audit_buffer_size,
            "audit_flush_interval_seconds": self.audit_flush_interval_seconds,
            "audit_retention_days": self.audit_retention_days,
            "auth_method": self.auth_method.value,
            "jwt_expiry_hours": self.jwt_expiry_hours,
            "service_id": self.service_id,
            "service_namespace": self.service_namespace,
            "trusted_services": self.trusted_services,
            "otel_service_name": self.otel_service_name,
            "otel_service_version": self.otel_service_version,
            "max_encryption_time_ms": self.max_encryption_time_ms,
            "max_auth_time_ms": self.max_auth_time_ms,
            "max_audit_log_time_ms": self.max_audit_log_time_ms
        }


# Global configuration instance
_security_config: Optional[SecurityConfig] = None


def get_security_config() -> SecurityConfig:
    """Get or create global security configuration."""
    global _security_config
    if _security_config is None:
        _security_config = SecurityConfig.from_env()
    return _security_config


def reload_security_config() -> SecurityConfig:
    """Reload security configuration from environment."""
    global _security_config
    _security_config = SecurityConfig.from_env()
    return _security_config
