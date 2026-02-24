"""
Data Quality System Exceptions

Custom exceptions and warnings for the DQS system.
"""

import warnings


class DataQualityError(Exception):
    """Base exception for all data quality errors."""
    
    def __init__(self, message: str, asset_id: str = None, value: float = None):
        super().__init__(message)
        self.asset_id = asset_id
        self.value = value
        self.message = message


class InsufficientDataError(DataQualityError):
    """Raised when there's insufficient data for statistical calculations."""
    
    def __init__(self, asset_id: str, required_count: int, actual_count: int):
        message = (
            f"Insufficient data for asset '{asset_id}': "
            f"need at least {required_count} samples, got {actual_count}"
        )
        super().__init__(message, asset_id)
        self.required_count = required_count
        self.actual_count = actual_count


class StatisticalError(DataQualityError):
    """Raised when statistical calculations fail."""
    
    def __init__(self, message: str, asset_id: str = None, operation: str = None):
        super().__init__(message, asset_id)
        self.operation = operation


class AnomalyDetectedWarning(UserWarning):
    """Warning raised when an anomaly is detected in data."""
    
    def __init__(
        self, 
        asset_id: str, 
        value: float, 
        z_score: float, 
        threshold: float,
        timestamp: float = None
    ):
        self.asset_id = asset_id
        self.value = value
        self.z_score = z_score
        self.threshold = threshold
        self.timestamp = timestamp
        
        message = (
            f"Anomaly detected for asset '{asset_id}': "
            f"value={value}, z-score={z_score:.3f} (threshold={threshold})"
        )
        super().__init__(message)


class OutlierRejectedError(DataQualityError):
    """Raised when an outlier is rejected."""
    
    def __init__(self, asset_id: str, value: float, z_score: float, threshold: float):
        message = (
            f"Outlier rejected for asset '{asset_id}': "
            f"value={value}, z-score={z_score:.3f} exceeds threshold={threshold}"
        )
        super().__init__(message, asset_id, value)
        self.z_score = z_score
        self.threshold = threshold


class ConfigurationError(DataQualityError):
    """Raised when DQS configuration is invalid."""
    
    def __init__(self, parameter: str, value: any, reason: str = None):
        message = f"Invalid configuration for '{parameter}': {value}"
        if reason:
            message += f" ({reason})"
        super().__init__(message)
        self.parameter = parameter
        self.value = value
        self.reason = reason


class StateError(DataQualityError):
    """Raised when there's an issue with the internal state."""
    
    def __init__(self, message: str, asset_id: str = None):
        super().__init__(message, asset_id)
