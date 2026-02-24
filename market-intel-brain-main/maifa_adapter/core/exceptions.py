"""
MAIFA Source Adapter - Standardized Exceptions

This module defines the exception hierarchy for the MAIFA data ingestion system.
All adapters must use these standardized exceptions for consistent error handling.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal


class TransientAdapterError(Exception):
    """
    Base exception for transient (retriable) adapter errors.
    
    These errors indicate temporary issues that may resolve themselves
    with retry (network issues, rate limits, temporary service outages).
    """
    
    def __init__(
        self,
        message: str,
        adapter_name: Optional[str] = None,
        retry_after: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.adapter_name = adapter_name
        self.retry_after = retry_after
        self.context = context or {}
        self.timestamp = datetime.utcnow()
        self.is_transient = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging and API responses."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "adapter_name": self.adapter_name,
            "is_transient": self.is_transient,
            "retry_after": self.retry_after,
            "context": self.context,
            "timestamp": self.timestamp.isoformat()
        }


class FatalAdapterError(Exception):
    """
    Base exception for fatal (non-retriable) adapter errors.
    
    These errors indicate permanent issues that will not resolve with retry
    (authentication failures, invalid configuration, malformed requests).
    """
    
    def __init__(
        self,
        message: str,
        adapter_name: Optional[str] = None,
        suggested_action: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.adapter_name = adapter_name
        self.suggested_action = suggested_action
        self.context = context or {}
        self.timestamp = datetime.utcnow()
        self.is_transient = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging and API responses."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "adapter_name": self.adapter_name,
            "is_transient": self.is_transient,
            "suggested_action": self.suggested_action,
            "context": self.context,
            "timestamp": self.timestamp.isoformat()
        }


class AdapterConfigurationError(FatalAdapterError):
    """
    Raised when adapter configuration is invalid or missing.
    
    This includes missing API keys, invalid URLs, malformed settings, etc.
    """
    
    def __init__(
        self,
        message: str,
        adapter_name: Optional[str] = None,
        missing_keys: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            adapter_name=adapter_name,
            suggested_action="Check adapter configuration and environment variables",
            context={**(context or {}), **({"missing_keys": missing_keys} if missing_keys else {})}
        )
        self.missing_keys = missing_keys or []


class AdapterValidationError(FatalAdapterError):
    """
    Raised when request validation fails.
    
    This includes invalid parameters, malformed requests, schema violations, etc.
    """
    
    def __init__(
        self,
        message: str,
        adapter_name: Optional[str] = None,
        validation_errors: Optional[Dict[str, str]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            adapter_name=adapter_name,
            suggested_action="Fix request parameters and retry",
            context={**(context or {}), **({"validation_errors": validation_errors} if validation_errors else {})}
        )
        self.validation_errors = validation_errors or {}


class AdapterTimeoutError(TransientAdapterError):
    """
    Raised when adapter request times out.
    
    Indicates the provider is responding too slowly or experiencing high load.
    """
    
    def __init__(
        self,
        message: str,
        adapter_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            adapter_name=adapter_name,
            context={**(context or {}), **({"timeout_seconds": timeout_seconds} if timeout_seconds else {})}
        )
        self.timeout_seconds = timeout_seconds


class AdapterRateLimitError(TransientAdapterError):
    """
    Raised when adapter hits rate limits.
    
    Indicates too many requests have been made in a given time period.
    """
    
    def __init__(
        self,
        message: str,
        adapter_name: Optional[str] = None,
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        period: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            adapter_name=adapter_name,
            retry_after=retry_after,
            context={**(context or {}), **({"limit": limit, "period": period} if limit or period else {})}
        )
        self.limit = limit
        self.period = period


class AdapterNetworkError(TransientAdapterError):
    """
    Raised when adapter experiences network connectivity issues.
    
    Includes DNS resolution failures, connection refused, etc.
    """
    
    def __init__(
        self,
        message: str,
        adapter_name: Optional[str] = None,
        network_error: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            adapter_name=adapter_name,
            context={**(context or {}), **({"network_error": network_error} if network_error else {})}
        )
        self.network_error = network_error


class AdapterAuthenticationError(FatalAdapterError):
    """
    Raised when adapter authentication fails.
    
    Includes invalid API keys, expired tokens, permission issues.
    """
    
    def __init__(
        self,
        message: str,
        adapter_name: Optional[str] = None,
        auth_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            adapter_name=adapter_name,
            suggested_action="Check API credentials and permissions",
            context={**(context or {}), **({"auth_type": auth_type} if auth_type else {})}
        )
        self.auth_type = auth_type


class AdapterDataError(FatalAdapterError):
    """
    Raised when adapter receives malformed or unexpected data.
    
    Includes schema violations, missing required fields, invalid data types.
    """
    
    def __init__(
        self,
        message: str,
        adapter_name: Optional[str] = None,
        data_details: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            adapter_name=adapter_name,
            suggested_action="Check API documentation and data format",
            context={**(context or {}), **({"data_details": data_details} if data_details else {})}
        )
        self.data_details = data_details


class AdapterServiceUnavailableError(TransientAdapterError):
    """
    Raised when adapter service is temporarily unavailable.
    
    Includes server errors, maintenance windows, service outages.
    """
    
    def __init__(
        self,
        message: str,
        adapter_name: Optional[str] = None,
        status_code: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            adapter_name=adapter_name,
            context={**(context or {}), **({"status_code": status_code} if status_code else {})}
        )
        self.status_code = status_code


# Utility functions for error handling
def is_transient_error(error: Exception) -> bool:
    """
    Check if an error is transient (retriable).
    
    Args:
        error: Exception to check
        
    Returns:
        True if error is transient and can be retried
    """
    return isinstance(error, TransientAdapterError)


def is_fatal_error(error: Exception) -> bool:
    """
    Check if an error is fatal (non-retriable).
    
    Args:
        error: Exception to check
        
    Returns:
        True if error is fatal and should not be retried
    """
    return isinstance(error, FatalAdapterError)


def get_retry_delay(error: Exception) -> Optional[int]:
    """
    Extract retry delay from error if available.
    
    Args:
        error: Exception to check
        
    Returns:
        Retry delay in seconds, or None if not available
    """
    if isinstance(error, (TransientAdapterError, AdapterRateLimitError)):
        return error.retry_after
    
    # Default delays for different error types
    if isinstance(error, AdapterTimeoutError):
        return int(error.timeout_seconds or 30)
    
    if isinstance(error, (AdapterNetworkError, AdapterServiceUnavailableError)):
        return 60  # Default 1 minute for network/service issues
    
    return None


def create_error_context(**kwargs) -> Dict[str, Any]:
    """
    Create standardized error context with common fields.
    
    Args:
        **kwargs: Additional context fields
        
    Returns:
        Dictionary with error context
    """
    context = {
        "timestamp": datetime.utcnow().isoformat(),
        **kwargs
    }
    
    # Remove None values
    return {k: v for k, v in context.items() if v is not None}
