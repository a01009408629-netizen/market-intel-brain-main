"""
Schema Guard Exceptions

Custom exceptions for the schema evolution guard system.
"""


class GuardError(Exception):
    """Base exception for all schema guard errors."""
    
    def __init__(self, message: str, provider: str = None, schema_version: str = None):
        super().__init__(message)
        self.provider = provider
        self.schema_version = schema_version
        self.message = message


class SchemaDriftError(GuardError):
    """Raised when schema drift is detected."""
    
    def __init__(
        self,
        provider: str,
        expected_version: str,
        actual_version: str,
        changes: dict
    ):
        message = (
            f"Schema drift detected for provider '{provider}': "
            f"expected v{expected_version}, got v{actual_version}, "
            f"changes: {len(changes)} items"
        )
        super().__init__(message, provider, actual_version)
        self.expected_version = expected_version
        self.actual_version = actual_version
        self.changes = changes


class SchemaValidationError(GuardError):
    """Raised when schema validation fails."""
    
    def __init__(
        self,
        provider: str,
        field_path: str,
        validation_error: str,
        actual_value: any = None,
        expected_type: str = None
    ):
        message = (
            f"Schema validation failed for provider '{provider}' "
            f"at field '{field_path}': {validation_error}"
        )
        super().__init__(message, provider)
        self.field_path = field_path
        self.validation_error = validation_error
        self.actual_value = actual_value
        self.expected_type = expected_type


class ConfigurationError(GuardError):
    """Raised when guard configuration is invalid."""
    
    def __init__(self, parameter: str, value: any, reason: str = None):
        message = f"Invalid configuration for '{parameter}': {value}"
        if reason:
            message += f" ({reason})"
        super().__init__(message)
        self.parameter = parameter
        self.value = value
        self.reason = reason


class FingerprintError(GuardError):
    """Raised when schema fingerprinting fails."""
    
    def __init__(self, message: str, provider: str = None, data_sample: str = None):
        super().__init__(message, provider)
        self.data_sample = data_sample
        self.message = message


class DiffAnalysisError(GuardError):
    """Raised when schema difference analysis fails."""
    
    def __init__(self, message: str, provider: str = None, diff_data: dict = None):
        super().__init__(message, provider)
        self.diff_data = diff_data
        self.message = message


class StorageError(GuardError):
    """Raised when schema storage operations fail."""
    
    def __init__(self, message: str, operation: str = None, storage_key: str = None):
        super().__init__(message)
        self.operation = operation
        self.storage_key = storage_key
        self.message = message


class AlertError(GuardError):
    """Raised when alert system fails."""
    
    def __init__(self, message: str, alert_type: str = None, recipient: str = None):
        super().__init__(message)
        self.alert_type = alert_type
        self.recipient = recipient
        self.message = message


class InterceptorError(GuardError):
    """Raised when schema interceptor fails."""
    
    def __init__(self, message: str, interceptor_type: str = None):
        super().__init__(message)
        self.interceptor_type = interceptor_type
        self.message = message
