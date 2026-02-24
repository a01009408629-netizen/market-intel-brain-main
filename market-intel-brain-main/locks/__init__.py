"""
Distributed Lock Manager (DLM) - Redlock Implementation

This module provides a distributed locking system using the Redlock algorithm
with Redis to prevent cache stampede and ensure safe distributed operations.
"""

from .redlock import RedLock, DistributedLock
from .manager import LockManager, get_lock
from .exceptions import (
    LockError,
    LockAcquisitionError,
    LockReleaseError,
    LockTimeoutError,
    DeadlockError
)

__all__ = [
    # Core classes
    'RedLock',
    'DistributedLock',
    'LockManager',
    'get_lock',
    
    # Exceptions
    'LockError',
    'LockAcquisitionError', 
    'LockReleaseError',
    'LockTimeoutError',
    'DeadlockError'
]

# Global lock manager instance
_global_manager = None


def get_global_manager(**kwargs) -> LockManager:
    """Get or create the global lock manager instance."""
    global _global_manager
    if _global_manager is None:
        _global_manager = LockManager(**kwargs)
    return _global_manager
