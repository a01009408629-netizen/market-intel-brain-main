"""
Data Lineage and Provenance Tracker

This module provides comprehensive data lineage and provenance tracking
using UUID for unique identification and datetime for audit trails.
"""

from .lineage_tracker import DataLineageTracker, get_tracker
from .metadata_manager import MetadataManager, get_metadata_manager
from .provenance_tracker import ProvenanceTracker, get_provenance_tracker
from .exceptions import LineageError, MetadataError, ProvenanceError

__all__ = [
    # Core classes
    'DataLineageTracker',
    'MetadataManager',
    'ProvenanceTracker',
    
    # Convenience functions
    'get_tracker',
    'get_metadata_manager',
    'get_provenance_tracker',
    
    # Exceptions
    'LineageError',
    'MetadataError',
    'ProvenanceError'
]

# Global instances
_global_tracker = None
_global_metadata_manager = None
_global_provenance_tracker = None


def get_global_tracker(**kwargs) -> DataLineageTracker:
    """Get or create global lineage tracker."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = DataLineageTracker(**kwargs)
    return _global_tracker


def get_global_metadata_manager(**kwargs) -> MetadataManager:
    """Get or create global metadata manager."""
    global _global_metadata_manager
    if _global_metadata_manager is None:
        _global_metadata_manager = MetadataManager(**kwargs)
    return _global_metadata_manager


def get_global_provenance_tracker(**kwargs) -> ProvenanceTracker:
    """Get or create global provenance tracker."""
    global _global_provenance_tracker
    if _global_provenance_tracker is None:
        _global_provenance_tracker = ProvenanceTracker(**kwargs)
    return _global_provenance_tracker


# Convenience functions for global usage
async def track_data_lineage_globally(
    provider_name: str,
    data: Any,
    operation: str,
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Track data lineage using global tracker."""
    tracker = get_global_tracker()
    return await tracker.track_data_lineage(
        provider_name, data, operation, context, metadata
    )


async def add_metadata_globally(
    object_id: str,
    metadata: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> str:
    """Add metadata using global manager."""
    manager = get_global_metadata_manager()
    return await manager.add_metadata(object_id, metadata, context)


async def track_provenance_globally(
    object_id: str,
    provenance_type: str,
    details: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> str:
    """Track provenance using global tracker."""
    tracker = get_global_provenance_tracker()
    return await tracker.track_provenance(
        object_id, provenance_type, details, context
    )


def get_lineage_summary_globally(
    object_id: str,
    provider_name: str,
    operation: str
) -> Dict[str, Any]:
    """Get lineage summary using global tracker."""
    tracker = get_global_tracker()
    return await tracker.get_lineage_summary(
        object_id, provider_name, operation
    )


def get_provenance_summary_globally(
    object_id: str,
    provenance_type: str,
    time_range: Optional[str] = None
) -> Dict[str, Any]:
    """Get provenance summary using global tracker."""
    tracker = get_global_provenance_tracker()
    return await tracker.get_provenance_summary(
        object_id, provenance_type, time_range
    )


def get_metadata_summary_globally(
    object_id: str,
    time_range: Optional[str] = None
) -> Dict[str, Any]:
    """Get metadata summary using global manager."""
    manager = get_global_metadata_manager()
    return await manager.get_metadata_summary(
        object_id, time_range
    )


def get_full_data_history_globally(
    object_id: str,
    time_range: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Get full data history using global tracker."""
    tracker = get_global_tracker()
    return await tracker.get_full_data_history(
        object_id, time_range, limit
    )


def get_full_provenance_history_globally(
    object_id: str,
    time_range: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Get full provenance history using global tracker."""
    tracker = get_global_provenance_tracker()
    return await tracker.get_full_provenance_history(
        object_id, time_range, limit
    )


def get_system_status_globally() -> Dict[str, Any]:
    """Get system status using global components."""
    tracker = get_global_tracker()
    metadata_manager = get_metadata_manager()
    provenance_tracker = get_global_provenance_tracker()
    
    return {
        "lineage_tracker": tracker.get_status(),
        "metadata_manager": metadata_manager.get_status(),
        "provenance_tracker": provenance_tracker.get_status(),
        "timestamp": time.time()
    }
