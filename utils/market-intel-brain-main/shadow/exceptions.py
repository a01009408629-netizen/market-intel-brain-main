"""
Shadow Comparison Engine Exceptions

Custom exceptions for the shadow comparison system.
"""


class ShadowError(Exception):
    """Base exception for all shadow engine errors."""
    
    def __init__(self, message: str, adapter_name: str = None, request_id: str = None):
        super().__init__(message)
        self.adapter_name = adapter_name
        self.request_id = request_id
        self.message = message


class ConfigurationError(ShadowError):
    """Raised when shadow engine configuration is invalid."""
    
    def __init__(self, parameter: str, value: any, reason: str = None):
        message = f"Invalid configuration for '{parameter}': {value}"
        if reason:
            message += f" ({reason})"
        super().__init__(message)
        self.parameter = parameter
        self.value = value
        self.reason = reason


class AdapterError(ShadowError):
    """Raised when adapter operations fail."""
    
    def __init__(self, message: str, adapter_name: str = None, request_id: str = None):
        super().__init__(message, adapter_name, request_id)
        self.adapter_name = adapter_name
        self.request_id = request_id
        self.message = message


class ComparatorError(ShadowError):
    """Raised when response comparison fails."""
    
    def __init__(self, message: str, comparator_type: str = None):
        super().__init__(message)
        self.comparator_type = comparator_type
        self.message = message


class MetricsError(ShadowError):
    """Raised when metrics collection fails."""
    
    def __init__(self, message: str, metric_type: str = None):
        super().__init__(message)
        self.metric_type = metric_type
        self.message = message


class RequestTimeoutError(ShadowError):
    """Raised when shadow request times out."""
    
    def __init__(self, adapter_name: str, timeout: float, request_id: str = None):
        message = (
            f"Shadow request timeout for adapter '{adapter_name}' "
            f"after {timeout}s"
        )
        super().__init__(message, adapter_name, request_id)
        self.timeout = timeout
        self.message = message


class DiffAnalysisError(ShadowError):
    """Raised when difference analysis fails."""
    
    def __init__(self, message: str, diff_type: str = None):
        super().__init__(message)
        self.diff_type = diff_type
        self.message = message


class StorageError(ShadowError):
    """Raised when shadow data storage operations fail."""
    
    def __init__(self, message: str, operation: str = None):
        super().__init__(message)
        self.operation = operation
        self.message = message


class DarkLaunchError(ShadowError):
    """Raised when dark launching is detected."""
    
    def __init__(self, message: str, adapter_name: str = None):
        super().__init__(message)
        self.adapter_name = adapter_name
        self.message = message
