from abc import ABC, abstractmethod
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field
from enum import Enum


class ErrorSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MaifaIngestionError(Exception, ABC):
    """Base error class for MAIFA Data Ingestion System"""
    
    def __init__(
        self,
        message: str,
        provider_name: str,
        suggested_action: Optional[str] = None,
        is_transient: bool = False,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.provider_name = provider_name
        self.suggested_action = suggested_action
        self.is_transient = is_transient
        self.severity = severity
        self.context = context or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "provider_name": self.provider_name,
            "suggested_action": self.suggested_action,
            "is_transient": self.is_transient,
            "severity": self.severity,
            "context": self.context
        }


class ProviderTimeoutError(MaifaIngestionError):
    def __init__(self, provider_name: str, timeout_seconds: float, **kwargs):
        super().__init__(
            message=f"Provider {provider_name} timed out after {timeout_seconds}s",
            provider_name=provider_name,
            suggested_action="Increase timeout or check provider status",
            is_transient=True,
            severity=ErrorSeverity.HIGH,
            context={"timeout_seconds": timeout_seconds},
            **kwargs
        )


class ProviderRateLimitError(MaifaIngestionError):
    def __init__(self, provider_name: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(
            message=f"Rate limit exceeded for provider {provider_name}",
            provider_name=provider_name,
            suggested_action=f"Wait {retry_after}s before retry" if retry_after else "Implement rate limiting",
            is_transient=True,
            severity=ErrorSeverity.MEDIUM,
            context={"retry_after": retry_after},
            **kwargs
        )


class ProviderAuthenticationError(MaifaIngestionError):
    def __init__(self, provider_name: str, **kwargs):
        super().__init__(
            message=f"Authentication failed for provider {provider_name}",
            provider_name=provider_name,
            suggested_action="Check API credentials and permissions",
            is_transient=False,
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )


class ProviderNotFoundError(MaifaIngestionError):
    def __init__(self, provider_name: str, resource: str, **kwargs):
        super().__init__(
            message=f"Resource '{resource}' not found for provider {provider_name}",
            provider_name=provider_name,
            suggested_action="Verify resource exists and is accessible",
            is_transient=False,
            severity=ErrorSeverity.LOW,
            context={"resource": resource},
            **kwargs
        )


class ProviderServerError(MaifaIngestionError):
    def __init__(self, provider_name: str, status_code: int, **kwargs):
        super().__init__(
            message=f"Server error from provider {provider_name}: HTTP {status_code}",
            provider_name=provider_name,
            suggested_action="Check provider status and retry later",
            is_transient=True,
            severity=ErrorSeverity.HIGH,
            context={"status_code": status_code},
            **kwargs
        )


class ProviderValidationError(MaifaIngestionError):
    def __init__(self, provider_name: str, validation_errors: Dict[str, Any], **kwargs):
        super().__init__(
            message=f"Validation failed for provider {provider_name}",
            provider_name=provider_name,
            suggested_action="Fix request parameters",
            is_transient=False,
            severity=ErrorSeverity.MEDIUM,
            context={"validation_errors": validation_errors},
            **kwargs
        )


class ProviderConfigurationError(MaifaIngestionError):
    def __init__(self, provider_name: str, missing_config: str, **kwargs):
        super().__init__(
            message=f"Missing configuration for provider {provider_name}: {missing_config}",
            provider_name=provider_name,
            suggested_action=f"Provide {missing_config} in configuration",
            is_transient=False,
            severity=ErrorSeverity.CRITICAL,
            context={"missing_config": missing_config},
            **kwargs
        )


class ProviderNetworkError(MaifaIngestionError):
    def __init__(self, provider_name: str, network_error: str, **kwargs):
        super().__init__(
            message=f"Network error for provider {provider_name}: {network_error}",
            provider_name=provider_name,
            suggested_action="Check network connectivity and DNS",
            is_transient=True,
            severity=ErrorSeverity.MEDIUM,
            context={"network_error": network_error},
            **kwargs
        )
