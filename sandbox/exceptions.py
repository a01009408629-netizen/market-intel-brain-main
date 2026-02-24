"""
Mock Sandbox Exceptions

Custom exceptions for the mock sandbox system.
"""


class SandboxError(Exception):
    """Base exception for all sandbox errors."""
    
    def __init__(self, message: str, provider_name: str = None, endpoint: str = None):
        super().__init__(message)
        self.provider_name = provider_name
        self.endpoint = endpoint
        self.message = message


class ConfigurationError(SandboxError):
    """Raised when sandbox configuration is invalid."""
    
    def __init__(self, parameter: str, value: any, reason: str = None):
        message = f"Invalid configuration for '{parameter}': {value}"
        if reason:
            message += f" ({reason})"
        super().__init__(message)
        self.parameter = parameter
        self.value = value
        self.reason = reason


class ProviderError(SandboxError):
    """Raised when mock provider operations fail."""
    
    def __init__(self, message: str, provider_name: str = None, operation: str = None):
        message = f"Provider error: {message}"
        super().__init__(message, provider_name, operation)
        self.provider_name = provider_name
        self.operation = operation
        self.message = message


class RandomnessError(SandboxError):
    """Raised when deterministic randomness fails."""
    
    def __init__(self, message: str, seed: str = None):
        message = f"Randomness error: {message}"
        super().__init__(message)
        self.seed = seed
        self.message = message


class EndpointError(SandboxError):
    """Raised when mock endpoint operations fail."""
    
    def __init__(self, message: str, endpoint: str = None, method: str = None):
        message = f"Endpoint error: {message}"
        super().__init__(message, endpoint, method)
        self.endpoint = endpoint
        self.method = method
        self.message = message


class DataGenerationError(SandboxError):
    """Raised when mock data generation fails."""
    
    def __init__(self, message: str, data_type: str = None):
        message = f"Data generation error: {message}"
        super().__init__(message)
        self.data_type = data_type
        self.message = message


class StateError(SandboxError):
    """Raised when sandbox state operations fail."""
    
    def __init__(self, message: str, state_name: str = None):
        message = f"State error: {message}"
        super().__init__(message)
        self.state_name = state_name
        self.message = message


class ValidationError(SandboxError):
    """Raised when request validation fails."""
    
    def __init__(self, message: str, field_name: str = None, value: any = None):
        message = f"Validation error: {message}"
        super().__init__(message)
        self.field_name = field_name
        self.value = value
        self.message = message


class SimulationError(SandboxError):
    """Raised when simulation operations fail."""
    
    def __init__(self, message: str, simulation_type: str = None):
        message = f"Simulation error: {message}"
        super().__init__(message)
        self.simulation_type = simulation_type
        self.message = message
