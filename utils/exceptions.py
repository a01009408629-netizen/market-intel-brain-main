"""
Binary Serialization Exceptions

Custom exceptions for the binary serialization system.
"""


class SerializationError(Exception):
    """Base exception for all serialization errors."""
    
    def __init__(self, message: str, operation: str = None, data_sample: Any = None):
        super().__init__(message)
        self.operation = operation
        self.data_sample = data_sample
        self.message = message


class ConfigurationError(SerializationError):
    """Raised when serialization configuration is invalid."""
    
    def __init__(self, parameter: str, value: any, reason: str = None):
        message = f"Invalid configuration for '{parameter}': {value}"
        if reason:
            message += f" ({reason})"
        super().__init__(message)
        self.parameter = parameter
        self.value = value
        self.reason = reason


class EncodingError(SerializationError):
    """Raised when data encoding/decoding fails."""
    
    def __init__(self, message: str, encoding_type: str = None, data_sample: Any = None):
        super().__init__(message)
        self.encoding_type = encoding_type
        self.data_sample = data_sample
        self.message = message


class DecodingError(SerializationError):
    """Raised when data decoding fails."""
    
    def __init__(self, message: str, encoding_type: str = None, data_sample: Any = None):
        super().__init__(message)
        self.encoding_type = encoding_type
        self.data_sample = data_sample
        self.message = message


class ValidationError(SerializationError):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field_path: str = None, validation_error: str = None):
        super().__init__(message)
        self.field_path = field_path
        self.validation_error = validation_error
        self.message = message


class TypeMismatchError(SerializationError):
    """Raised when type mismatches expected type."""
    
    def __init__(self, expected_type: str, actual_type: str, field_path: str = None):
        message = f"Type mismatch at {field_path}: expected {expected_type}, got {actual_type}"
        super().__init__(message))
        self.expected_type = expected_type
        self.actual_type = actual_type
        self.field_path = field_path


class IntegrityError(SerializationError):
    """Raised when data integrity is compromised."""
    
    def __init__(self, message: str, checksum: str = None, expected_checksum: str = None):
        message = f"Integrity error: {message}"
        super().__init__(message)
        self.checksum = checksum
        self.expected_checksum = expected_checksum
        self.message = message


class SizeLimitError(SerializationError):
    """Raised when data exceeds size limits."""
    
    def __init__(self, message: str, size_limit: int, actual_size: int):
        message = f"Size limit exceeded: {actual_size} (limit: {size_limit})"
        super().__init__(message)
        self.size_limit = size_limit
        self.actual_size = actual_size


class FormatError(SerializationError):
    """Raised when data format is invalid."""
    
    def __init__(self, message: str, format_type: str = None):
        super().__init__(message)
        self.format_type = format_type
        self.message = message


class SecurityError(SerializationError):
    """Raised when security issues are detected."""
    
    def __init__(self, message: str, security_type: str = None):
        super().__init__(message)
        self.security_type = security_type
        self.message = message


class StorageError(SerializationError):
    """Raised when storage operations fail."""
    
    def __init__(self, message: str, operation: str = None):
        super().__init__(message)
        self.operation = operation
        self.message = message
