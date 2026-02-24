"""
Zero-Trust Secrets Manager

This module provides a zero-trust secrets manager with secure credential handling,
audit logging, and external provider integration.
"""

import asyncio
import logging
import time
import hashlib
import json
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import threading
import weakref

from .settings import SecretsSettings, get_settings
from .providers import SecretsProvider, get_provider, ProviderType, SecretValue
from .exceptions import (
    SecretsError,
    SecurityError,
    ProviderError,
    EncryptionError,
    ValidationError,
    AccessDeniedError,
    RotationError,
    AuditError,
    IntegrityError
)


class AccessLevel(Enum):
    """Access levels for secrets."""
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    ROTATE = "ROTATE"
    ADMIN = "ADMIN"


class SecurityContext:
    """Security context for access control."""
    
    def __init__(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        access_level: AccessLevel = AccessLevel.READ,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        timestamp: Optional[float] = None
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.access_level = access_level
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.timestamp = timestamp or time.time()


@dataclass
class AccessLog:
    """Access log entry."""
    timestamp: float
    user_id: str
    session_id: str
    secret_name: str
    operation: str
    access_level: AccessLevel
    ip_address: str
    user_agent: str
    success: bool
    error: Optional[str]
    metadata: Dict[str, Any]


@dataclass
class SecurityPolicy:
    """Security policy configuration."""
    max_failed_attempts: int = 3
    lockout_duration_minutes: int = 15
    session_timeout_minutes: int = 30
    require_mfa: bool = False
    allowed_ip_ranges: List[str] = field(default_factory=list)
    allowed_user_agents: List[str] = field(default_factory=list)
    secret_complexity_min_length: int = 8
    secret_complexity_require_upper: bool = True
    secret_complexity_require_lower: bool = True
    secret_complexity_require_digit: bool = True
    secret_complexity_require_special: bool = True
    audit_retention_days: int = 90
    encryption_key_rotation_days: int = 90


@dataclass
class AuditEvent:
    """Audit event for security logging."""
    timestamp: float
    event_type: str
    user_id: str
    secret_name: str
    operation: str
    success: bool
    details: Dict[str, Any]
    security_context: Dict[str, Any]


class SecretsManager:
    """
    Zero-trust secrets manager with comprehensive security features.
    
    This class provides secure credential management with zero-trust principles,
    ensuring secrets are never stored as plain text in memory and all access
    is properly audited and logged.
    """
    
    def __init__(
        self,
        settings: Optional[SecretsSettings] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize secrets manager.
        
        Args:
            settings: Secrets settings
            logger: Logger instance
        """
        self.settings = settings or get_settings()
        self.logger = logger or logging.getLogger("SecretsManager")
        
        # Security components
        self._security_policy = SecurityPolicy()
        self._encryption_key = self._generate_encryption_key()
        
        # State management
        self._access_logs: deque(maxlen=10000)  # Keep last 10k logs
        self._audit_events: deque(maxlen=5000)     # Keep last 5k events
        self._failed_attempts: Dict[str, int] = defaultdict(int)
        self._locked_users: Dict[str, float] = {}
        self._active_sessions: Dict[str, SecurityContext] = {}
        
        # External providers
        self._providers: Dict[ProviderType, SecretsProvider] = {}
        
        # Encryption
        self._encryption_algorithm = "AES-256-GCM"
        self._key_derivation_iterations = 100000
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Initialize providers
        self._initialize_providers()
        
        self.logger.info("Zero-Trust Secrets Manager initialized")
    
    def _generate_encryption_key(self) -> bytes:
        """Generate encryption key for secrets."""
        import os
        
        key_file = self.settings.encryption_key_file
        
        try:
            # Try to load existing key
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    key = f.read()
                    self.logger.info("Loaded existing encryption key")
                    return key
            
            # Generate new key
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.primitives.ciphers import hashes
            from cryptography.hazmat.backends.ciphers.aes import AESGCM
            
            # Generate random salt
            salt = os.urandom(32)
            
            # Derive key
            password = self.settings.app_name.encode('utf-8')
            key = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=self.settings.security.key_derivation_iterations,
                password=password
            )
            
            # Save key
            with open(key_file, 'wb') as f:
                f.write(salt + key)
            
            self.logger.info("Generated new encryption key")
            return key
            
        except Exception as e:
            self.logger.error(f"Failed to generate encryption key: {e}")
            raise EncryptionError(f"Failed to generate encryption key: {e}", "key_generation")
    
    def _initialize_providers(self):
        """Initialize external secrets providers."""
        try:
            # Initialize provider factory
            from .providers import SecretsProvider
            provider_factory = SecretsProvider(self.settings.providers.__dict__)
            
            # Initialize all configured providers
            for provider_type in ProviderType:
                if provider_type != ProviderType.LOCAL_FILE:
                    try:
                        provider_config = self.settings.get_provider_config(provider_type.value)
                        
                        if provider_config:
                            provider = provider_factory.create_provider(provider_type)
                            if provider:
                                success = await provider.initialize()
                                if success:
                                    self._providers[provider_type] = provider
                                    self.logger.info(f"Initialized provider: {provider_type.value}")
                                else:
                                    self.logger.warning(f"Failed to initialize provider: {provider_type.value}")
                    except Exception as e:
                        self.logger.error(f"Error initializing provider {provider_type.value}: {e}")
                        
        except Exception as e:
            self.logger.error(f"Failed to initialize providers: {e}")
    
    def _validate_security_context(self, context: SecurityContext) -> bool:
        """Validate security context for access control."""
        # Check if user is locked out
        if context.user_id in self._locked_users:
            lockout_time = self._locked_users[context.user_id]
            if time.time() < lockout_time:
                return False
        
        # Check IP restrictions
        if self._security_policy.allowed_ip_ranges:
            ip_allowed = False
            for ip_range in self._security_policy.allowed_ip_ranges:
                if self._ip_in_range(context.ip_address, ip_range):
                    ip_allowed = True
                    break
            
            if not ip_allowed:
                return False
        
        # Check user agent restrictions
        if self._security_policy.allowed_user_agents:
            ua_allowed = False
            for allowed_ua in self._security_policy.allowed_user_agents:
                if allowed_ua in context.user_agent:
                    ua_allowed = True
                    break
            
            if not ua_allowed:
                return False
        
        # Check session timeout
        if context.timestamp:
            session_age = time.time() - context.timestamp
            if session_age > self._security_policy.session_timeout_minutes * 60:
                return False
        
        return True
    
    def _ip_in_range(self, ip_address: str, ip_range: str) -> bool:
        """Check if IP address is in range."""
        try:
            import ipaddress
            
            ip = ipaddress.ip_address(ip_address)
            network = ipaddress.ip_network(ip_range)
            
            return ip in network
            
        except Exception:
            return False
    
    def _encrypt_secret(self, secret_value: str) -> tuple[str, str]:
        """Encrypt a secret value."""
        try:
            from cryptography.hazmat.primitives.ciphers.aes import AESGCM
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.primitives.ciphers import hashes
            
            # Generate random nonce
            nonce = os.urandom(12)
            
            # Derive encryption key
            password = self._encryption_key
            salt = b'salt'  # In production, use proper salt management
            key = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=self.settings.security.key_derivation_iterations,
                password=password
            )
            
            # Create cipher
            cipher = AESGCM(key)
            
            # Encrypt data
            encrypted_data = cipher.encrypt(nonce, secret_value.encode('utf-8'))
            
            # Return encrypted data with nonce and tag
            encrypted_value = encrypted_data[0].hex()
            nonce_hex = nonce.hex()
            tag_hex = encrypted_data[1].hex()
            
            return f"{nonce_hex}:{tag_hex}:{encrypted_value}"
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt secret: {e}")
            raise EncryptionError(f"Failed to encrypt secret: {e}", "encryption")
    
    def _decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt a secret value."""
        try:
            from cryptography.hazmat.primitives.ciphers.aes import AESGCM
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.primitives.ciphers import hashes
            
            # Parse encrypted secret
            parts = encrypted_secret.split(':')
            if len(parts) != 3:
                raise EncryptionError("Invalid encrypted secret format", "decryption")
            
            nonce_hex, tag_hex, encrypted_value_hex = parts
            nonce = bytes.fromhex(nonce_hex)
            tag = bytes.fromhex(tag_hex)
            encrypted_value = bytes.fromhex(encrypted_value_hex)
            
            # Derive decryption key
            password = self._encryption_key
            salt = b'salt'  # In production, use proper salt management
            key = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=self.settings.security.key_derivation_iterations,
                password=password
            )
            
            # Create cipher
            cipher = AESGCM(key)
            
            # Decrypt data
            decrypted_data = cipher.decrypt_and_verify(nonce, encrypted_value, tag)
            
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"Failed to decrypt secret: {e}")
            raise EncryptionError(f"Failed to decrypt secret: {e}", "decryption")
    
    def _calculate_checksum(self, value: str) -> str:
        """Calculate checksum for integrity verification."""
        return hashlib.sha256(value.encode('utf-8')).hexdigest()
    
    def _log_access(self, context: SecurityContext, secret_name: str, operation: str, success: bool, error: Optional[str] = None, metadata: Dict[str, Any] = None):
        """Log access attempt for audit trail."""
        try:
            access_log = AccessLog(
                timestamp=time.time(),
                user_id=context.user_id or "anonymous",
                session_id=context.session_id or "no_session",
                secret_name=secret_name,
                operation=operation,
                access_level=context.access_level,
                ip_address=context.ip_address or "unknown",
                user_agent=context.user_agent or "unknown",
                success=success,
                error=error,
                metadata=metadata or {}
            )
            
            with self._lock:
                self._access_logs.append(access_log)
                
                # Log to file if configured
                if self.settings.security.enable_audit_logging:
                    self._write_audit_log(access_log)
            
        except Exception as e:
            self.logger.error(f"Failed to log access: {e}")
            raise AuditError(f"Failed to log access: {e}", "access_logging")
    
    def _write_audit_log(self, access_log: AccessLog):
        """Write audit log to file."""
        try:
            log_entry = {
                "timestamp": access_log.timestamp,
                "user_id": access_log.user_id,
                "session_id": access_log.session_id,
                "secret_name": access_log.secret_name,
                "operation": access_log.operation,
                "access_level": access_log.access_level.value,
                "ip_address": access_log.ip_address,
                "user_agent": access_log.user_agent,
                "success": access_log.success,
                "error": access_log.error,
                "metadata": access_log.metadata
            }
            
            # Write to audit file
            with open(self.settings.security.audit_log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
        except Exception as e:
            self.logger.error(f"Failed to write audit log: {e}")
    
    def _log_audit_event(self, event: AuditEvent):
        """Log security event for audit trail."""
        try:
            with self._lock:
                self._audit_events.append(event)
                
                # Log to file if configured
                if self.settings.security.enable_audit_logging:
                    self._write_audit_event_log(event)
            
        except Exception as e:
            self.logger.error(f"Failed to log audit event: {e}")
            raise AuditError(f"Failed to log audit event: {e}", "audit_logging")
    
    def _write_audit_event_log(self, event: AuditEvent):
        """Write audit event to file."""
        try:
            event_entry = {
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "user_id": event.user_id,
                "secret_name": event.secret_name,
                "operation": event.operation,
                "success": event.success,
                "details": event.details,
                "security_context": event.security_context
            }
            
            # Write to audit file
            with open(self.settings.security.audit_log_file, 'a') as f:
                f.write(json.dumps(event_entry) + '\n')
            
        except Exception as e:
            self.logger.error(f"Failed to write audit event log: {e}")
    
    async def get_secret(self, secret_name: str, context: Optional[SecurityContext] = None) -> Optional[str]:
        """
        Get a secret with zero-trust validation.
        
        Args:
            secret_name: Name of the secret
            context: Security context for access control
            
        Returns:
            Secret value or None if access denied
        """
        if not context:
            context = SecurityContext()
        
        # Validate security context
        if not self._validate_security_context(context):
            self._log_access(context, secret_name, "GET", False, "Access denied: Invalid security context")
            raise AccessDeniedError("Access denied: Invalid security context", context.user_id, secret_name)
        
        # Check failed attempts
        if context.user_id:
            failed_attempts = self._failed_attempts.get(context.user_id, 0)
            if failed_attempts >= self._security_policy.max_failed_attempts:
                # Lock user
                self._locked_users[context.user_id] = time.time() + (self._security_policy.lockout_duration_minutes * 60)
                self._log_access(context, secret_name, "GET", False, "Account locked due to too many failed attempts")
                raise AccessDeniedError("Account locked due to too many failed attempts", context.user_id, secret_name)
        
        # Try each provider in order
        for provider_type in [ProviderType.LOCAL_FILE, ProviderType.AWS_SECRETS_MANAGER, ProviderType.AZURE_KEY_VAULT, ProviderType.HASHICORP_VAULT]:
            try:
                provider = self._providers.get(provider_type)
                if provider:
                    secret_value = await provider.get_secret(secret_name)
                    
                    if secret_value:
                        # Log successful access
                        self._log_access(context, secret_name, "GET", True, None, {"provider": provider_type.value})
                        
                        # Decrypt and return secret
                        if secret_value.is_encrypted:
                            return self._decrypt_secret(secret_value.value)
                        else:
                            return secret_value.value
                    else:
                        # Try next provider
                        continue
                
            except Exception as e:
                self.logger.error(f"Provider {provider_type.value} failed for secret {secret_name}: {e}")
                # Try next provider
                continue
        
        # Log failed access
        self._log_access(context, secret_name, "GET", False, f"Secret not found in any provider")
        
        # Increment failed attempts
        if context.user_id:
            self._failed_attempts[context.user_id] += 1
        
        return None
    
    async def set_secret(self, secret_name: str, secret_value: str, context: Optional[SecurityContext] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Set a secret with zero-trust validation.
        
        Args:
            secret_name: Name of the secret
            secret_value: Secret value
            context: Security context for access control
            metadata: Additional metadata
            
        Returns:
            True if successful, False otherwise
        """
        if not context:
            context = SecurityContext(access_level=AccessLevel.WRITE)
        
        # Validate security context
        if not self._validate_security_context(context):
            self._log_access(context, secret_name, "SET", False, "Access denied: Invalid security context")
            raise AccessDeniedError("Access denied: Invalid security context", context.user_id, secret_name)
        
        # Validate secret value
        if not self.settings.validate_secret(secret_name, secret_value):
            self._log_access(context, secret_name, "SET", False, f"Secret validation failed: {secret_name}")
            raise ValidationError(f"Secret validation failed: {secret_name}", secret_name, secret_value)
        
        # Encrypt secret
        encrypted_secret = self._encrypt_secret(secret_value)
        checksum = self._calculate_checksum(secret_value)
        
        secret_metadata = {
            "created_at": time.time(),
            "updated_at": time.time(),
            "description": metadata.get("description", "") if metadata else "",
            "tags": metadata.get("tags", {}) if metadata else {},
            "checksum": checksum,
            "is_encrypted": True
        }
        
        # Try each provider in order
        for provider_type in [ProviderType.AWS_SECRETS_MANAGER, ProviderType.AZURE_KEY_VAULT, ProviderType.HASHICORP_VAULT, ProviderType.CUSTOM_PROVIDER]:
            try:
                provider = self._providers.get(provider_type)
                if provider:
                    # Create secret value with metadata
                    secret_with_metadata = SecretValue(
                        value=encrypted_secret,
                        metadata=SecretMetadata(
                            name=secret_name,
                            version="1",
                            created_at=time.time(),
                            updated_at=time.time(),
                            expires_at=None,
                            description=secret_metadata.get("description", ""),
                            tags=secret_metadata.get("tags", {}),
                            rotation_enabled=self.settings.security.enable_rotation,
                            last_rotated=None
                        ),
                        is_encrypted=True,
                        checksum=checksum
                    )
                    
                    success = await provider.set_secret(secret_name, secret_with_metadata.value, secret_metadata)
                    
                    if success:
                        # Log successful access
                        self._log_access(context, secret_name, "SET", True, None, {"provider": provider_type.value})
                        
                        # Reset failed attempts on success
                        if context.user_id and context.user_id in self._failed_attempts:
                            del self._failed_attempts[context.user_id]
                        
                        return True
                    else:
                        # Try next provider
                        continue
                
            except Exception as e:
                self.logger.error(f"Provider {provider_type.value} failed for secret {secret_name}: {e}")
                # Try next provider
                continue
        
        # Log failed access
        self._log_access(context, secret_name, "SET", False, f"Failed to set secret in any provider")
        
        # Increment failed attempts
        if context.user_id:
            self._failed_attempts[context.user_id] += 1
        
        return False
    
    async def delete_secret(self, secret_name: str, context: Optional[SecurityContext] = None) -> bool:
        """
        Delete a secret with zero-trust validation.
        
        Args:
            secret_name: Name of the secret
            context: Security context for access control
            
        Returns:
            True if successful, False otherwise
        """
        if not context:
            context = SecurityContext(access_level=AccessLevel.DELETE)
        
        # Validate security context
        if not self._validate_security_context(context):
            self._log_access(context, secret_name, "DELETE", False, "Access denied: Invalid security context")
            raise AccessDeniedError("Access denied: Invalid security context", context.user_id, secret_name)
        
        # Try each provider in order
        for provider_type in [ProviderType.AWS_SECRETS_MANAGER, ProviderType.AZURE_KEY_VAULT, ProviderType.HASHICORP_VAULT, ProviderType.CUSTOM_PROVIDER]:
            try:
                provider = self._providers.get(provider_type)
                if provider:
                    success = await provider.delete_secret(secret_name)
                    
                    if success:
                        # Log successful access
                        self._log_access(context, secret_name, "DELETE", True, None, {"provider": provider_type.value})
                        return True
                    else:
                        # Try next provider
                        continue
                
            except Exception as e:
                self.logger.error(f"Provider {provider_type.value} failed for secret {secret_name}: {e}")
                # Try next provider
                continue
        
        # Log failed access
        self._log_access(context, secret_name, "DELETE", False, f"Failed to delete secret from any provider")
        
        return False
    
    async def rotate_secret(self, secret_name: str, new_value: Optional[str] = None, context: Optional[SecurityContext] = None) -> bool:
        """
        Rotate a secret with zero-trust validation.
        
        Args:
            secret_name: Name of the secret
            new_value: New secret value (None for auto-generation)
            context: Security context for access control
            
        Returns:
            True if successful, False otherwise
        """
        if not context:
            context = SecurityContext(access_level=AccessLevel.ROTATE)
        
        # Validate security context
        if not self._validate_security_context(context):
            self._log_access(context, secret_name, "ROTATE", False, "Access denied: Invalid security context")
            raise AccessDeniedError("Access denied: Invalid security context", context.user_id, secret_name)
        
        # Get current secret
        current_secret = await self.get_secret(secret_name, context)
        
        if not current_secret:
            self._log_access(context, secret_name, "ROTATE", False, f"Secret not found for rotation")
            return False
        
        # Generate new value if not provided
        if not new_value:
            import secrets
            import string
            
            # Generate secure random password
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:'<>,.?/"
            new_value = ''.join(secrets.choice(alphabet) for _ in range(16))
        
        # Validate new value
        if not self.settings.validate_secret(secret_name, new_value):
            self._log_access(context, secret_name, "ROTATE", False, f"New secret validation failed: {secret_name}")
            raise ValidationError(f"New secret validation failed: {secret_name}", secret_name, new_value)
        
        # Set new secret
        success = await self.set_secret(secret_name, new_value, context, {"rotation": True})
        
        if success:
            # Log successful rotation
            self._log_access(context, secret_name, "ROTATE", True, None, {"rotation": "successful"})
            
            # Log audit event
            audit_event = AuditEvent(
                timestamp=time.time(),
                event_type="secret_rotation",
                user_id=context.user_id,
                secret_name=secret_name,
                operation="ROTATE",
                success=True,
                details={"old_value": self.mask_secret(current_secret), "new_value": self.mask_secret(new_value)},
                security_context={
                    "user_id": context.user_id,
                    "access_level": context.access_level.value,
                    "ip_address": context.ip_address,
                    "user_agent": context.user_agent,
                    "timestamp": context.timestamp
                }
            )
            self._log_audit_event(audit_event)
            
            return True
        else:
            # Log failed rotation
            self._log_access(context, secret_name, "ROTATE", False, f"Failed to rotate secret")
            return False
    
    def mask_secret(self, secret_value: str, mask_char: str = "*", visible_chars: int = 4) -> str:
        """Mask a secret value for logging."""
        if not secret_value or len(secret_value) <= visible_chars:
            return mask_char * len(secret_value)
        
        return secret_value[:visible_chars] + mask_char * (len(secret_value) - visible_chars)
    
    def get_access_logs(self, limit: int = 100) -> List[AccessLog]:
        """Get recent access logs."""
        with self._lock:
            return list(self._access_logs)[-limit:]
    
    def get_audit_events(self, limit: int = 100) -> List[AuditEvent]:
        """Get recent audit events."""
        with self._lock:
            return list(self._audit_events)[-limit:]
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get security status and statistics."""
        with self._lock:
            return {
                "active_sessions": len(self._active_sessions),
                "locked_users": len(self._locked_users),
                "failed_attempts": dict(self._failed_attempts),
                "access_log_count": len(self._access_logs),
                "audit_event_count": len(self._audit_events),
                "providers_configured": len(self._providers),
                "encryption_enabled": self.settings.security.enable_encryption,
                "audit_logging_enabled": self.settings.security.enable_audit_logging,
                "integrity_checks_enabled": self._settings.security.enable_integrity_checks,
                "zero_trust_enabled": self.settings.security.enable_zero_trust,
                "timestamp": time.time()
            }
    
    def cleanup_old_logs(self, days_to_keep: int = 90):
        """Clean up old access logs and audit events."""
        cutoff_time = time.time() - (days_to_keep * 24 * 3600)
        
        with self._lock:
            # Clean access logs
            self._access_logs = deque(
                [log for log in self._access_logs if log.timestamp >= cutoff_time],
                maxlen=10000
            )
            
            # Clean audit events
            self._audit_events = deque(
                [event for event in self._audit_events if event.timestamp >= cutoff_time],
                maxlen=5000
            )
        
        self.logger.info(f"Cleaned up logs older than {days_to_keep} days")


# Global secrets manager instance
_global_manager: Optional[SecretsManager] = None


def get_manager(**kwargs) -> SecretsManager:
    """
    Get or create global secrets manager.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global SecretsManager instance
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = SecretsManager(**kwargs)
    return _global_manager


# Convenience functions for global usage
async def get_secret_globally(secret_name: str, context: Optional[SecurityContext] = None) -> Optional[str]:
    """Get secret using global manager."""
    manager = get_manager()
    return await manager.get_secret(secret_name, context)


async def set_secret_globally(secret_name: str, secret_value: str, context: Optional[SecurityContext] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
    """Set secret using global manager."""
    manager = get_manager()
    return await manager.set_secret(secret_name, secret_value, context, metadata)


async def delete_secret_globally(secret_name: str, context: Optional[SecurityContext] = None) -> bool:
    """Delete secret using global manager."""
    manager = get_manager()
    return await manager.delete_secret(secret_name, context)


async def rotate_secret_globally(secret_name: str, new_value: Optional[str] = None, context: Optional[SecurityContext] = None) -> bool:
    """Rotate secret using global manager."""
    manager = get_manager()
    return await manager.rotate_secret(secret_name, new_value, context)


def get_security_status_globally() -> Dict[str, Any]:
    """Get security status using global manager."""
    manager = get_manager()
    return manager.get_security_status()
