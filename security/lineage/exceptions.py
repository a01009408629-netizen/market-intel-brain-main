"""
Data Lineage and Provenance Tracker Exceptions

Custom exceptions for lineage tracking, metadata management, and provenance tracking.
"""


class LineageError(Exception):
    """Base exception for all lineage tracking errors."""
    
    def __init__(self, message: str, object_id: str = None, operation: str = None):
        super().__init__(message)
        self.object_id = object_id
        self.operation = operation
        self.message = message


class MetadataError(LineageError):
    """Raised when metadata operations fail."""
    
    def __init__(self, message: str, metadata_key: str = None, object_id: str = None):
        message = f"Metadata error: {message}"
        super().__init__(message, object_id, "metadata")
        self.metadata_key = metadata_key
        self.message = message


class ProvenanceError(LineageError):
    """Raised when provenance tracking fails."""
    
    def __init__(self, message: str, provenance_type: str = None, object_id: str = None):
        message = f"Provenance error: {message}"
        super().__init__(message, object_id, "provenance")
        self.provenance_type = provenance_type
        self.message = message


class ValidationError(LineageError):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field_name: str = None, object_id: str = None):
        message = f"Validation error: {message}"
        super().__init__(message, object_id, "validation")
        self.field_name = field_name
        self.message = message


class StorageError(LineageError):
    """Raised when storage operations fail."""
    
    def __init__(self, message: str, storage_type: str = None, object_id: str = None):
        message = f"Storage error: {message}"
        super().__init__(message, object_id, "storage")
        self.storage_type = storage_type
        self.message = message


class ConfigurationError(LineageError):
    """Raised when configuration is invalid."""
    
    def __init__(self, message: str, parameter: str = None, value: any = None):
        message = f"Configuration error: {message}"
        super().__init__(message, None, "configuration")
        self.parameter = parameter
        self.value = value
        self.message = message


class SerializationError(LineageError):
    """Raised when serialization/deserialization fails."""
    
    def __init__(self, message: str, data_type: str = None, object_id: str = None):
        message = f"Serialization error: {message}"
        super().__init__(message, object_id, "serialization")
        self.data_type = data_type
        self.message = message


class IntegrityError(LineageError):
    """Raised when data integrity is compromised."""
    
    def __init__(self, message: str, checksum: str = None, object_id: str = None):
        message = f"Integrity error: {message}"
        super().__init__(message, object_id, "integrity")
        self.checksum = checksum
        self.message = message


class AuditError(LineageError):
    """Raised when audit operations fail."""
    
    def __init__(self, message: str, audit_type: str = None, object_id: str = None):
        message = f"Audit error: {message}"
        super().__init__(message, object_id, "audit")
        self.audit_type = audit_type
        self.message = message


class PerformanceError(LineageError):
    """Raised when performance thresholds are exceeded."""
    
    def __init__(self, message: str, metric: str = None, threshold: any = None):
        message = f"Performance error: {message}"
        super().__init__(message, None, "performance")
        self.metric = metric
        self.threshold = threshold
        self.message = message


class ConcurrencyError(LineageError):
    """Raised when concurrency conflicts occur."""
    
    def __init__(self, message: str, conflict_type: str = None, object_id: str = None):
        message = f"Concurrency error: {message}"
        super().__init__(message, object_id, "concurrency")
        self.conflict_type = conflict_type
        self.message = message


class VersionError(LineageError):
    """Raised when version conflicts occur."""
    
    def __init__(self, message: str, version: str = None, object_id: str = None):
        message = f"Version error: {message}"
        super().__init__(message, object_id, "version")
        self.version = version
        self.message = message


class TransformationError(LineageError):
    """Raised when data transformations fail."""
    
    def __init__(self, message: str, transformation_type: str = None, object_id: str = None):
        message = f"Transformation error: {message}"
        super().__init__(message, object_id, "transformation")
        self.transformation_type = transformation_type
        self.message = message


class ComplianceError(LineageError):
    """Raised when compliance requirements are not met."""
    
    def __init__(self, message: str, compliance_type: str = None, object_id: str = None):
        message = f"Compliance error: {message}"
        super().__init__(message, object_id, "compliance")
        self.compliance_type = compliance_type
        self.message = message


class RetentionError(LineageError):
    """Raised when retention policies are violated."""
    
    def __init__(self, message: str, retention_policy: str = None, object_id: str = None):
        message = f"Retention error: {message}"
        super().__init__(message, object_id, "retention")
        self.retention_policy = retention_policy
        self.message = message


class AccessError(LineageError):
    """Raised when access is denied."""
    
    def __init__(self, message: str, user_id: str = None, resource: str = None):
        message = f"Access error: {message}"
        super().__init__(message, None, "access")
        self.user_id = user_id
        self.resource = resource
        self.message = message


class BackupError(LineageError):
    """Raised when backup operations fail."""
    
    def __init__(self, message: str, backup_type: str = None, object_id: str = None):
        message = f"Backup error: {message}"
        super().__init__(message, object_id, "backup")
        self.backup_type = backup_type
        self.message = message


class RecoveryError(LineageError):
    """Raised when recovery operations fail."""
    
    def __init__(self, message: str, recovery_type: str = None, object_id: str = None):
        message = f"Recovery error: {message}"
        super().__init__(message, object_id, "recovery")
        self.recovery_type = recovery_type
        self.message = message
