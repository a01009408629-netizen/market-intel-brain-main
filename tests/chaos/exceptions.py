"""
Chaos Engineering Exceptions

Custom exceptions for the chaos engineering suite.
"""


class ChaosError(Exception):
    """Base exception for all chaos engineering errors."""
    
    def __init__(self, message: str, chaos_type: str = None, component: str = None):
        super().__init__(message)
        self.chaos_type = chaos_type
        self.component = component
        self.message = message


class ConfigurationError(ChaosError):
    """Raised when chaos configuration is invalid."""
    
    def __init__(self, parameter: str, value: any, reason: str = None):
        message = f"Invalid configuration for '{parameter}': {value}"
        if reason:
            message += f" ({reason})"
        super().__init__(message)
        self.parameter = parameter
        self.value = value
        self.reason = reason


class CircuitBreakerError(ChaosError):
    """Raised when circuit breaker operations fail."""
    
    def __init__(self, message: str, circuit_name: str = None, state: str = None):
        message = f"Circuit breaker error: {message}"
        super().__init__(message)
        self.circuit_name = circuit_name
        self.state = state
        self.message = message


class ChaosEngineError(ChaosError):
    """Raised when chaos engine operations fail."""
    
    def __init__(self, message: str, experiment_id: str = None):
        message = f"Chaos engine error: {message}"
        super().__init__(message)
        self.experiment_id = experiment_id
        self.message = message


class ResilienceTestError(ChaosError):
    """Raised when resilience tests fail."""
    
    def __init__(self, message: str, test_name: str = None):
        message = f"Resilience test error: {message}"
        super().__init__(message)
        self.test_name = test_name
        self.message = message


class FaultInjectionError(ChaosError):
    """Raised when fault injection fails."""
    
    def __init__(self, message: str, fault_type: str = None, target: str = None):
        message = f"Fault injection error: {message}"
        super().__init__(message)
        self.fault_type = fault_type
        self.target = target
        self.message = message


class RedisConnectionError(ChaosError):
    """Raised when Redis connection fails during chaos experiments."""
    
    def __init__(self, message: str, redis_url: str = None):
        message = f"Redis connection error: {message}"
        super().__init__(message)
        self.redis_url = redis_url
        self.message = message


class ExperimentError(ChaosError):
    """Raised when chaos experiment fails."""
    
    def __init__(self, message: str, experiment_id: str = None):
        message = f"Experiment error: {message}"
        super().__init__(message)
        self.experiment_id = experiment_id
        self.message = message


class ValidationError(ChaosError):
    """Raised when chaos validation fails."""
    
    def __init__(self, message: str, field: str = None, value: any = None):
        message = f"Validation error: {message}"
        super().__init__(message)
        self.field = field
        self.value = value
        self.message = message


class MetricsCollectionError(ChaosError):
    """Raised when metrics collection fails."""
    
    def __init__(self, message: str, metric_type: str = None):
        message = f"Metrics collection error: {message}"
        super().__init__(message)
        self.metric_type = metric_type
        self.message = message
