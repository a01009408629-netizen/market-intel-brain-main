"""
Secrets Settings

This module provides Pydantic-based settings for secure secrets management
with zero-trust principles and secure credential handling.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from pydantic import BaseSettings, Field, SecretStr, validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .exceptions import ConfigurationError, SecurityError


class SecuritySettings(BaseSettings):
    """Security configuration settings."""
    
    enable_encryption: bool = Field(default=True, description="Enable encryption for secrets")
    encryption_algorithm: str = Field(default="AES-256-GCM", description="Encryption algorithm")
    key_derivation_iterations: int = Field(default=100000, description="PBKDF2 iterations")
    enable_audit_logging: bool = Field(default=True, description="Enable audit logging")
    audit_log_file: str = Field(default="logs/secrets_audit.log", description="Audit log file path")
    enable_integrity_checks: bool = Field(default=True, description="Enable integrity checks")
    enable_rotation: bool = Field(default=True, description="Enable automatic rotation")
    rotation_interval_days: int = Field(default=90, description="Rotation interval in days")
    max_access_attempts: int = Field(default=3, description="Max access attempts before lockout")
    lockout_duration_minutes: int = Field(default=15, description="Lockout duration in minutes")
    enable_zero_trust: bool = Field(default=True, description="Enable zero-trust principles")
    session_timeout_minutes: int = Field(default=30, description="Session timeout in minutes")
    require_mfa: bool = Field(default=False, description="Require multi-factor authentication")
    allowed_ip_ranges: List[str] = Field(default_factory=list, description="Allowed IP ranges")


class ProviderSettings(BaseSettings):
    """External provider settings."""
    
    aws_region: str = Field(default="us-east-1", description="AWS region")
    aws_access_key_id: str = Field(description="AWS access key ID")
    aws_secret_access_key: str = Field(description="AWS secret access key")
    azure_tenant_id: str = Field(description="Azure tenant ID")
    azure_client_id: str = Field(description="Azure client ID")
    azure_client_secret: str = Field(description="Azure client secret")
    gcp_project_id: str = Field(description="GCP project ID")
    gcp_credentials_path: str = Field(description="GCP credentials path")
    hashicorp_vault_url: str = Field(default="http://localhost:8200", description="HashiCorp Vault URL")
    hashicorp_vault_token: str = Field(description="HashiCorp Vault token")
    custom_provider_url: str = Field(description="Custom provider URL")
    custom_provider_token: str = Field(description="Custom provider token")


class SecretsSettings(BaseSettings):
    """
    Main secrets settings class using Pydantic BaseSettings.
    
    This class provides secure configuration management with zero-trust principles,
    ensuring secrets are never stored as plain text in memory.
    """
    
    # Application settings
    app_name: str = Field(default="market-intel-brain", description="Application name")
    environment: str = Field(default="development", description="Environment (development/staging/production)")
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # Security settings
    security: SecuritySettings = Field(default_factory=SecuritySettings, description="Security configuration")
    
    # Database settings (secrets)
    database_url: SecretStr = Field(description="Database connection URL")
    database_username: SecretStr = Field(description="Database username")
    database_password: SecretStr = Field(description="Database password")
    database_host: SecretStr = Field(description="Database host")
    database_port: int = Field(default=5432, description="Database port")
    database_name: SecretStr = Field(description="Database name")
    
    # API keys (secrets)
    finnhub_api_key: SecretStr = Field(description="Finnhub API key")
    alpha_vantage_api_key: SecretStr = Field(description="Alpha Vantage API key")
    polygon_api_key: SecretStr = Field(description="Polygon API key")
    yahoo_finance_api_key: SecretStr = Field(description="Yahoo Finance API key")
    binance_api_key: SecretStr = Field(description="Binance API key")
    binance_api_secret: SecretStr = Field(description="Binance API secret")
    
    # External service credentials
    redis_url: SecretStr = Field(description="Redis connection URL")
    redis_password: SecretStr = Field(description="Redis password")
    
    # JWT settings
    jwt_secret_key: SecretStr = Field(description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(default=60, description="JWT expiration in minutes")
    
    # External provider settings
    providers: ProviderSettings = Field(default_factory=ProviderSettings, description="External provider settings")
    
    # File paths
    secrets_file: str = Field(default="secrets.yaml", description="Secrets configuration file")
    encryption_key_file: str = Field(default=".encryption_key", description="Encryption key file")
    audit_log_file: str = Field(default="logs/secrets_audit.log", description="Audit log file")
    
    # Environment-specific settings
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        secrets_dir = "secrets/"
        validate_assignment = True
    
    @validator("environment")
    def validate_environment(cls, v):
        if v not in ["development", "staging", "production"]:
            raise ValueError("Environment must be one of: development, staging, production")
        return v
    
    @validator("debug")
    def validate_debug_in_production(cls, v, values):
        if values.get("environment") == "production" and v:
            raise ValueError("Debug mode cannot be enabled in production")
        return v
    
    @validator("security.enable_encryption")
    def validate_encryption_enabled(cls, v, values):
        if values.get("environment") == "production" and not v:
            raise ValueError("Encryption must be enabled in production")
        return v
    
    @validator("security.enable_audit_logging")
    def validate_audit_logging_in_production(cls, v, values):
        if values.get("environment") == "production" and not v:
            raise ValueError("Audit logging must be enabled in production")
        return v
    
    def __init__(self, **kwargs):
        """Initialize secrets settings with security validation."""
        super().__init__(**kwargs)
        
        # Initialize logger
        self._logger = logging.getLogger("SecretsSettings")
        
        # Validate security requirements
        self._validate_security_requirements()
        
        self._logger.info(f"SecretsSettings initialized for environment: {self.environment}")
    
    def _validate_security_requirements(self):
        """Validate security requirements based on environment."""
        if self.environment == "production":
            # Production security requirements
            if not self.security.enable_encryption:
                raise SecurityError("Encryption must be enabled in production", "encryption_disabled")
            
            if not self.security.enable_audit_logging:
                raise SecurityError("Audit logging must be enabled in production", "audit_logging_disabled")
            
            if not self.security.enable_integrity_checks:
                raise SecurityError("Integrity checks must be enabled in production", "integrity_checks_disabled")
            
            if not self.security.enable_zero_trust:
                raise SecurityError("Zero-trust must be enabled in production", "zero_trust_disabled")
            
            if self.debug:
                raise SecurityError("Debug mode cannot be enabled in production", "debug_in_production")
        
        self._logger.info(f"Security requirements validated for {self.environment}")
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration with secrets."""
        return {
            "url": self.database_url.get_secret_value(),
            "username": self.database_username.get_secret_value(),
            "password": self.database_password.get_secret_value(),
            "host": self.database_host.get_secret_value(),
            "port": self.database_port,
            "database": self.database_name.get_secret_value()
        }
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a specific provider."""
        api_keys = {
            "finnhub": self.finnhub_api_key,
            "alpha_vantage": self.alpha_vantage_api_key,
            "polygon": self.polygon_api_key,
            "yahoo_finance": self.yahoo_finance_api_key,
            "binance": self.binance_api_key
        }
        
        return api_keys.get(provider)
    
    def get_binance_credentials(self) -> Dict[str, str]:
        """Get Binance API credentials."""
        return {
            "api_key": self.binance_api_key.get_secret_value(),
            "api_secret": self.binance_api_secret.get_secret_value()
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration with secrets."""
        return {
            "url": self.redis_url.get_secret_value(),
            "password": self.redis_password.get_secret_value() if self.redis_password else None
        }
    
    def get_jwt_config(self) -> Dict[str, Any]:
        """Get JWT configuration with secrets."""
        return {
            "secret_key": self.jwt_secret_key.get_secret_value(),
            "algorithm": self.jwt_algorithm,
            "expiration_minutes": self.jwt_expiration_minutes
        }
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for external provider."""
        if provider == "aws":
            return {
                "region": self.providers.aws_region,
                "access_key_id": self.providers.aws_access_key_id,
                "secret_access_key": self.providers.aws_secret_access_key
            }
        elif provider == "azure":
            return {
                "tenant_id": self.providers.azure_tenant_id,
                "client_id": self.providers.azure_client_id,
                "client_secret": self.providers.azure_client_secret
            }
        elif provider == "gcp":
            return {
                "project_id": self.providers.gcp_project_id,
                "credentials_path": self.providers.gcp_credentials_path
            }
        elif provider == "hashicorp":
            return {
                "url": self.providers.hashicorp_vault_url,
                "token": self.providers.hashicorp_vault_token
            }
        elif provider == "custom":
            return {
                "url": self.providers.custom_provider_url,
                "token": self.providers.custom_provider_token
            }
        else:
            raise ConfigurationError("provider", provider, f"Unknown provider: {provider}")
    
    def validate_secret(self, secret_name: str, secret_value: str) -> bool:
        """Validate a secret value according to security policies."""
        if not secret_value:
            return False
        
        # Check minimum length
        if len(secret_value) < 8:
            return False
        
        # Check complexity requirements
        has_upper = any(c.isupper() for c in secret_value)
        has_lower = any(c.islower() for c in secret_value)
        has_digit = any(c.isdigit() for c in secret_value)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:'<>,.?/" for c in secret_value)
        
        complexity_score = sum([has_upper, has_lower, has_digit, has_special])
        
        if complexity_score < 3:
            return False
        
        # Check for common weak patterns
        weak_patterns = ["password", "123456", "qwerty", "admin", "root"]
        if any(pattern in secret_value.lower() for pattern in weak_patterns):
            return False
        
        return True
    
    def mask_secret(self, secret_value: str, mask_char: str = "*", visible_chars: int = 4) -> str:
        """Mask a secret value for logging."""
        if not secret_value or len(secret_value) <= visible_chars:
            return mask_char * len(secret_value)
        
        return secret_value[:visible_chars] + mask_char * (len(secret_value) - visible_chars)
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security configuration summary."""
        return {
            "environment": self.environment,
            "encryption_enabled": self.security.enable_encryption,
            "audit_logging_enabled": self.security.enable_audit_logging,
            "integrity_checks_enabled": self.security.enable_integrity_checks,
            "zero_trust_enabled": self.security.enable_zero_trust,
            "mfa_required": self.security.require_mfa,
            "session_timeout": self.security.session_timeout_minutes,
            "max_access_attempts": self.security.max_access_attempts,
            "lockout_duration": self.security.lockout_duration_minutes
        }


# Global settings instance
_global_settings: Optional[SecretsSettings] = None


def get_settings(**kwargs) -> SecretsSettings:
    """
    Get or create global secrets settings.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global SecretsSettings instance
    """
    global _global_settings
    if _global_settings is None:
        _global_settings = SecretsSettings(**kwargs)
    return _global_settings


# Convenience functions for global usage
def get_database_config() -> Dict[str, Any]:
    """Get database configuration using global settings."""
    settings = get_settings()
    return settings.get_database_config()


def get_api_key_globally(provider: str) -> Optional[str]:
    """Get API key using global settings."""
    settings = get_settings()
    return settings.get_api_key(provider)


def get_redis_config_globally() -> Dict[str, Any]:
    """Get Redis configuration using global settings."""
    settings = get_settings()
    return settings.get_redis_config()


def get_jwt_config_globally() -> Dict[str, Any]:
    """Get JWT configuration using global settings."""
    settings = get_settings()
    return settings.get_jwt_config()


def get_provider_config_globally(provider: str) -> Dict[str, Any]:
    """Get provider configuration using global settings."""
    settings = get_settings()
    return settings.get_provider_config(provider)


def validate_secret_globally(secret_name: str, secret_value: str) -> bool:
    """Validate secret using global settings."""
    settings = get_settings()
    return settings.validate_secret(secret_name, secret_value)


def mask_secret_globally(secret_value: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """Mask secret using global settings."""
    settings = get_settings()
    return settings.mask_secret(secret_value, mask_char, visible_chars)
