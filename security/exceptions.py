"""
Zero-Trust Secrets Manager Exceptions

Custom exceptions for secrets management and security operations.
"""


class SecretsError(Exception):
    """Base exception for all secrets management errors."""
    
    def __init__(self, message: str, secret_name: str = None, provider: str = None):
        super().__init__(message)
        self.secret_name = secret_name
        self.provider = provider
        self.message = message


class SecurityError(SecretsError):
    """Raised when security violations occur."""
    
    def __init__(self, message: str, violation_type: str = None):
        message = f"Security violation: {message}"
        super().__init__(message)
        self.violation_type = violation_type
        self.message = message


class ConfigurationError(SecretsError):
    """Raised when secrets configuration is invalid."""
    
    def __init__(self, parameter: str, value: any, reason: str = None):
        message = f"Invalid configuration for '{parameter}': {value}"
        if reason:
            message += f" ({reason})"
        super().__init__(message)
        self.parameter = parameter
        self.value = value
        self.reason = reason


class ProviderError(SecretsError):
    """Raised when external provider operations fail."""
    
    def __init__(self, message: str, provider_name: str = None, operation: str = None):
        message = f"Provider error: {message}"
        super().__init__(message, provider_name, operation)
        self.provider_name = provider_name
        self.operation = operation
        self.message = message


class EncryptionError(SecretsError):
    """Raised when encryption/decryption operations fail."""
    
    def __init__(self, message: str, operation: str = None):
        message = f"Encryption error: {message}"
        super().__init__(message)
        self.operation = operation
        self.message = message


class ValidationError(SecretsError):
    """Raised when secret validation fails."""
    
    def __init__(self, message: str, field_name: str = None, secret_value: any = None):
        message = f"Validation error: {message}"
        super().__init__(message)
        self.field_name = field_name
        self.secret_value = secret_value
        self.message = message


class AccessDeniedError(SecretsError):
    """Raised when access to secrets is denied."""
    
    def __init__(self, message: str, user_id: str = None, resource: str = None):
        message = f"Access denied: {message}"
        super().__init__(message)
        self.user_id = user_id
        self.resource = resource
        self.message = message


class RotationError(SecretsError):
    """Raised when secret rotation fails."""
    
    def __init__(self, message: str, secret_name: str = None, rotation_type: str = None):
        message = f"Rotation error: {message}"
        super().__init__(message)
        self.secret_name = secret_name
        self.rotation_type = rotation_type
        self.message = message


class StorageError(SecretsError):
    """Raised when secure storage operations fail."""
    
    def __init__(self, message: str, storage_type: str = None):
        message = f"Storage error: {message}"
        super().__init__(message)
        self.storage_type = storage_type
        self.message = message


class AuditError(SecretsError):
    """Raised when audit logging fails."""
    
    def __init__(self, message: str, audit_type: str = None):
        message = f"Audit error: {message}"
        super().__init__(message)
        self.audit_type = audit_type
        self.message = message


class IntegrityError(SecretsError):
    """Raised when secrets integrity is compromised."""
    
    def __init__(self, message: str, integrity_check: str = None):
        message = f"Integrity error: {message}"
        super().__init__(message)
        self.integrity_check = integrity_check
        self.message = message


class ExpirationError(SecretsError):
    """Raised when secret expiration operations fail."""
    
    def __init__(self, message: str, secret_name: str = None):
        message = f"Expiration error: {message}"
        super().__init__(message)
        self.secret_name = secret_name
        self.message = message
