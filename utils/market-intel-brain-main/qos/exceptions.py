"""
QoS System Exceptions

Custom exceptions for the Quality of Service and priority queueing system.
"""


class QoSError(Exception):
    """Base exception for all QoS-related errors."""
    
    def __init__(self, message: str, task_id: str = None):
        super().__init__(message)
        self.task_id = task_id
        self.message = message


class QueueFullError(QoSError):
    """Raised when a queue is at capacity."""
    
    def __init__(self, queue_name: str, capacity: int, task_id: str = None):
        message = f"Queue '{queue_name}' is full (capacity: {capacity})"
        super().__init__(message, task_id)
        self.queue_name = queue_name
        self.capacity = capacity


class TaskTimeoutError(QoSError):
    """Raised when a task times out."""
    
    def __init__(self, task_id: str, timeout: float, message: str = None):
        if message is None:
            message = f"Task '{task_id}' timed out after {timeout}s"
        else:
            message = f"Task '{task_id}' timed out after {timeout}s: {message}"
        super().__init__(message, task_id)
        self.timeout = timeout


class InvalidPriorityError(QoSError):
    """Raised when an invalid priority is specified."""
    
    def __init__(self, priority: str, task_id: str = None):
        message = f"Invalid priority '{priority}'. Must be one of: HIGH, LOW"
        super().__init__(message, task_id)
        self.priority = priority


class DispatcherError(QoSError):
    """Raised when task dispatcher encounters an error."""
    
    def __init__(self, message: str, task_id: str = None, operation: str = None):
        super().__init__(message, task_id)
        self.operation = operation


class QueueError(QoSError):
    """Raised when queue operations fail."""
    
    def __init__(self, message: str, queue_name: str = None, operation: str = None):
        super().__init__(message)
        self.queue_name = queue_name
        self.operation = operation


class ResourceExhaustionError(QoSError):
    """Raised when system resources are exhausted."""
    
    def __init__(self, resource_type: str, current_usage: float, limit: float):
        message = (
            f"Resource exhaustion: {resource_type} usage "
            f"({current_usage:.2f}) exceeds limit ({limit:.2f})"
        )
        super().__init__(message)
        self.resource_type = resource_type
        self.current_usage = current_usage
        self.limit = limit


class ConfigurationError(QoSError):
    """Raised when QoS configuration is invalid."""
    
    def __init__(self, parameter: str, value: any, reason: str = None):
        message = f"Invalid configuration for '{parameter}': {value}"
        if reason:
            message += f" ({reason})"
        super().__init__(message)
        self.parameter = parameter
        self.value = value
        self.reason = reason


class SchedulerError(QoSError):
    """Raised when scheduler encounters an error."""
    
    def __init__(self, message: str, task_id: str = None):
        super().__init__(message, task_id)
