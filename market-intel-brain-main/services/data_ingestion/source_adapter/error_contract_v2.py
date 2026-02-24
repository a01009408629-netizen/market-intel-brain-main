import httpx
from typing import Optional, Dict, Any
from datetime import datetime


class ProviderBaseError(Exception):
    """
    Base exception for all provider-related errors.
    
    This is the root of the unified exception hierarchy for the MAIFA
    data ingestion system. All provider-specific errors inherit from this base.
    """
    
    def __init__(
        self,
        provider_name: str,
        message: str,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        suggested_action: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.provider_name = provider_name
        self.endpoint = endpoint
        self.status_code = status_code
        self.message = message
        self.suggested_action = suggested_action
        self.context = context or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging and API responses"""
        return {
            "error_type": self.__class__.__name__,
            "provider_name": self.provider_name,
            "message": self.message,
            "endpoint": self.endpoint,
            "status_code": self.status_code,
            "suggested_action": self.suggested_action,
            "context": self.context,
            "timestamp": self.timestamp.isoformat()
        }
    
    def __str__(self) -> str:
        """String representation for logging"""
        parts = [f"[{self.__class__.__name__}]"]
        parts.append(f"Provider: {self.provider_name}")
        
        if self.endpoint:
            parts.append(f"Endpoint: {self.endpoint}")
        
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        
        parts.append(f"Message: {self.message}")
        
        return " | ".join(parts)


class ProviderTimeoutError(ProviderBaseError):
    """
    Raised when a provider request times out.
    
    Indicates the provider is responding too slowly or is experiencing
    high load. These errors are typically transient and can be retried.
    """
    
    def __init__(
        self,
        provider_name: str,
        timeout_seconds: float,
        endpoint: Optional[str] = None,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        if message is None:
            message = f"Provider {provider_name} timed out after {timeout_seconds} seconds"
        
        super().__init__(
            provider_name=provider_name,
            message=message,
            endpoint=endpoint,
            status_code=None,
            suggested_action="Retry with exponential backoff or increase timeout",
            context={**({"timeout_seconds": timeout_seconds}), **(context or {})}
        )


class ProviderRateLimitError(ProviderBaseError):
    """
    Raised when a provider rate limit is exceeded.
    
    Indicates too many requests have been made in a given time period.
    The response should include retry information when available.
    """
    
    def __init__(
        self,
        provider_name: str,
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        endpoint: Optional[str] = None,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        if message is None:
            message = f"Rate limit exceeded for provider {provider_name}"
            if retry_after:
                message += f". Retry after {retry_after} seconds"
            if limit:
                message += f". Limit: {limit} requests"
        
        suggested_action = f"Wait {retry_after} seconds" if retry_after else "Implement rate limiting"
        
        super().__init__(
            provider_name=provider_name,
            message=message,
            endpoint=endpoint,
            status_code=429,
            suggested_action=suggested_action,
            context={**({"retry_after": retry_after, "limit": limit}), **(context or {})}
        )


class ProviderAuthError(ProviderBaseError):
    """
    Raised when provider authentication fails.
    
    Indicates invalid API keys, expired tokens, or permission issues.
    These errors are typically non-transient and require configuration changes.
    """
    
    def __init__(
        self,
        provider_name: str,
        auth_type: str = "API Key",
        endpoint: Optional[str] = None,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        if message is None:
            message = f"Authentication failed for provider {provider_name} ({auth_type})"
        
        super().__init__(
            provider_name=provider_name,
            message=message,
            endpoint=endpoint,
            status_code=401,
            suggested_action="Check API credentials and permissions",
            context={**({"auth_type": auth_type}), **(context or {})}
        )


class ProviderBadResponseError(ProviderBaseError):
    """
    Raised when a provider returns malformed or unexpected data.
    
    Indicates the provider response format has changed or contains invalid data.
    These errors may be transient (temporary API issues) or permanent
    (API contract changes).
    """
    
    def __init__(
        self,
        provider_name: str,
        response_details: Optional[str] = None,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        if message is None:
            message = f"Bad response from provider {provider_name}"
            if response_details:
                message += f": {response_details}"
        
        super().__init__(
            provider_name=provider_name,
            message=message,
            endpoint=endpoint,
            status_code=status_code,
            suggested_action="Check API documentation and response format",
            context={**({"response_details": response_details}), **(context or {})}
        )


class ProviderDownError(ProviderBaseError):
    """
    Raised when a provider is completely unavailable.
    
    Indicates the provider service is down, experiencing an outage,
    or completely unreachable. These errors are typically transient.
    """
    
    def __init__(
        self,
        provider_name: str,
        error_details: Optional[str] = None,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        if message is None:
            message = f"Provider {provider_name} is down or unavailable"
            if error_details:
                message += f": {error_details}"
        
        # Default to 503 for service unavailable
        if status_code is None:
            status_code = 503
        
        super().__init__(
            provider_name=provider_name,
            message=message,
            endpoint=endpoint,
            status_code=status_code,
            suggested_action="Retry with exponential backoff and monitor provider status",
            context={**({"error_details": error_details}), **(context or {})}
        )


class ProviderNotFoundError(ProviderBaseError):
    """
    Raised when a requested resource is not found.
    
    Indicates the requested symbol, endpoint, or resource doesn't exist.
    These errors are typically non-transient (404).
    """
    
    def __init__(
        self,
        provider_name: str,
        resource: str,
        endpoint: Optional[str] = None,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        if message is None:
            message = f"Resource not found: {resource}"
        
        super().__init__(
            provider_name=provider_name,
            message=message,
            endpoint=endpoint,
            status_code=404,
            suggested_action="Verify resource exists and is accessible",
            context={**({"resource": resource}), **(context or {})}
        )


class ProviderValidationError(ProviderBaseError):
    """
    Raised when request validation fails.
    
    Indicates invalid parameters, malformed requests, or validation errors.
    These errors are typically non-transient and require request changes.
    """
    
    def __init__(
        self,
        provider_name: str,
        validation_errors: Dict[str, Any],
        endpoint: Optional[str] = None,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        if message is None:
            message = f"Validation failed for provider {provider_name}"
        
        super().__init__(
            provider_name=provider_name,
            message=message,
            endpoint=endpoint,
            status_code=400,
            suggested_action="Fix request parameters",
            context={**({"validation_errors": validation_errors}), **(context or {})}
        )


def map_httpx_error_to_provider_error(
    err: Exception,
    provider_name: str,
    endpoint: Optional[str] = None
) -> ProviderBaseError:
    """
    Translate raw HTTPX/network errors into unified domain errors.
    
    This helper function converts low-level HTTPX exceptions into the
    unified ProviderBaseError hierarchy, providing consistent error
    handling across all adapters.
    
    Args:
        err: The original exception (HTTPX or network error)
        provider_name: Name of the provider for context
        endpoint: Optional endpoint being accessed
        
    Returns:
        ProviderBaseError: Appropriate unified error
    """
    
    # HTTPX Timeout Errors
    if isinstance(err, httpx.TimeoutException):
        if isinstance(err, httpx.ReadTimeout):
            return ProviderTimeoutError(
                provider_name=provider_name,
                timeout_seconds=getattr(err, 'timeout', None),
                endpoint=endpoint,
                message=f"Read timeout for provider {provider_name}",
                context={"timeout_type": "read", "original_error": str(err)}
            )
        elif isinstance(err, httpx.WriteTimeout):
            return ProviderTimeoutError(
                provider_name=provider_name,
                timeout_seconds=getattr(err, 'timeout', None),
                endpoint=endpoint,
                message=f"Write timeout for provider {provider_name}",
                context={"timeout_type": "write", "original_error": str(err)}
            )
        elif isinstance(err, httpx.ConnectTimeout):
            return ProviderTimeoutError(
                provider_name=provider_name,
                timeout_seconds=getattr(err, 'timeout', None),
                endpoint=endpoint,
                message=f"Connection timeout for provider {provider_name}",
                context={"timeout_type": "connect", "original_error": str(err)}
            )
        else:
            return ProviderTimeoutError(
                provider_name=provider_name,
                timeout_seconds=getattr(err, 'timeout', None),
                endpoint=endpoint,
                message=f"Timeout for provider {provider_name}",
                context={"timeout_type": "general", "original_error": str(err)}
            )
    
    # HTTPX Network Errors
    elif isinstance(err, httpx.NetworkError):
        if isinstance(err, httpx.ConnectError):
            return ProviderDownError(
                provider_name=provider_name,
                error_details="Connection failed",
                endpoint=endpoint,
                message=f"Connection failed for provider {provider_name}",
                context={"network_error_type": "connect", "original_error": str(err)}
            )
        elif isinstance(err, httpx.HTTPError):
            return ProviderDownError(
                provider_name=provider_name,
                error_details="HTTP protocol error",
                endpoint=endpoint,
                message=f"HTTP error for provider {provider_name}",
                context={"network_error_type": "http", "original_error": str(err)}
            )
        elif isinstance(err, httpx.RequestError):
            return ProviderBadResponseError(
                provider_name=provider_name,
                response_details="Request error",
                endpoint=endpoint,
                message=f"Request error for provider {provider_name}",
                context={"network_error_type": "request", "original_error": str(err)}
            )
        else:
            return ProviderDownError(
                provider_name=provider_name,
                error_details="Network error",
                endpoint=endpoint,
                message=f"Network error for provider {provider_name}",
                context={"network_error_type": "general", "original_error": str(err)}
            )
    
    # HTTP Status Code Errors (from HTTPX Response)
    elif hasattr(err, 'response') and hasattr(err.response, 'status_code'):
        status_code = err.response.status_code
        
        if status_code == 401:
            return ProviderAuthError(
                provider_name=provider_name,
                endpoint=endpoint,
                message=f"Authentication failed for provider {provider_name}",
                context={"http_status": status_code, "original_error": str(err)}
            )
        elif status_code == 403:
            return ProviderAuthError(
                provider_name=provider_name,
                auth_type="Permission",
                endpoint=endpoint,
                message=f"Access forbidden for provider {provider_name}",
                context={"http_status": status_code, "original_error": str(err)}
            )
        elif status_code == 404:
            return ProviderNotFoundError(
                provider_name=provider_name,
                resource="Requested resource",
                endpoint=endpoint,
                message=f"Resource not found for provider {provider_name}",
                context={"http_status": status_code, "original_error": str(err)}
            )
        elif status_code == 429:
            retry_after = None
            if hasattr(err.response, 'headers'):
                retry_after = err.response.headers.get('Retry-After')
                if retry_after:
                    try:
                        retry_after = int(retry_after)
                    except ValueError:
                        pass
            
            return ProviderRateLimitError(
                provider_name=provider_name,
                retry_after=retry_after,
                endpoint=endpoint,
                message=f"Rate limit exceeded for provider {provider_name}",
                context={"http_status": status_code, "original_error": str(err)}
            )
        elif 500 <= status_code < 600:
            return ProviderDownError(
                provider_name=provider_name,
                error_details=f"Server error {status_code}",
                endpoint=endpoint,
                status_code=status_code,
                message=f"Server error for provider {provider_name}",
                context={"http_status": status_code, "original_error": str(err)}
            )
        else:
            return ProviderBadResponseError(
                provider_name=provider_name,
                response_details=f"HTTP {status_code}",
                endpoint=endpoint,
                status_code=status_code,
                message=f"HTTP error {status_code} for provider {provider_name}",
                context={"http_status": status_code, "original_error": str(err)}
            )
    
    # Fallback for unknown errors
    else:
        return ProviderBadResponseError(
            provider_name=provider_name,
            response_details=f"Unexpected error: {type(err).__name__}",
            endpoint=endpoint,
            message=f"Unexpected error for provider {provider_name}: {str(err)}",
            context={"error_type": type(err).__name__, "original_error": str(err)}
        )


# Helper function to check if an error is transient (retryable)
def is_transient_error(error: ProviderBaseError) -> bool:
    """
    Determine if a provider error is transient (can be retried).
    
    Args:
        error: ProviderBaseError instance
        
    Returns:
        bool: True if error is transient and can be retried
    """
    transient_errors = (
        ProviderTimeoutError,
        ProviderRateLimitError,
        ProviderDownError
    )
    
    return isinstance(error, transient_errors)


# Helper function to extract retry delay from error
def get_retry_delay(error: ProviderBaseError) -> Optional[int]:
    """
    Extract retry delay from provider error if available.
    
    Args:
        error: ProviderBaseError instance
        
    Returns:
        Optional[int]: Retry delay in seconds, or None if not available
    """
    if isinstance(error, ProviderRateLimitError):
        return error.context.get("retry_after")
    
    # Default retry delays for different error types
    if isinstance(error, ProviderTimeoutError):
        return error.context.get("timeout_seconds", 30)
    
    if isinstance(error, ProviderDownError):
        return 60  # Default 1 minute for provider downtime
    
    return None
