"""
Distributed Lock Manager Exceptions

Custom exceptions for the distributed locking system.
"""


class LockError(Exception):
    """Base exception for all lock-related errors."""
    
    def __init__(self, message: str, lock_name: str = None):
        super().__init__(message)
        self.lock_name = lock_name
        self.message = message


class LockAcquisitionError(LockError):
    """Raised when lock acquisition fails."""
    
    def __init__(self, lock_name: str, reason: str = None):
        message = f"Failed to acquire lock '{lock_name}'"
        if reason:
            message += f": {reason}"
        super().__init__(message, lock_name)
        self.reason = reason


class LockReleaseError(LockError):
    """Raised when lock release fails."""
    
    def __init__(self, lock_name: str, reason: str = None):
        message = f"Failed to release lock '{lock_name}'"
        if reason:
            message += f": {reason}"
        super().__init__(message, lock_name)
        self.reason = reason


class LockTimeoutError(LockAcquisitionError):
    """Raised when lock acquisition times out."""
    
    def __init__(self, lock_name: str, timeout: float):
        super().__init__(lock_name, f"Timeout after {timeout}s")
        self.timeout = timeout


class DeadlockError(LockError):
    """Raised when a deadlock is detected."""
    
    def __init__(self, lock_name: str, deadlock_info: dict = None):
        message = f"Deadlock detected for lock '{lock_name}'"
        super().__init__(message, lock_name)
        self.deadlock_info = deadlock_info or {}


class LockOwnershipError(LockError):
    """Raised when trying to release a lock owned by another process."""
    
    def __init__(self, lock_name: str, owner: str = None, current_owner: str = None):
        message = f"Lock '{lock_name}' is owned by another process"
        if current_owner:
            message += f" (owner: {current_owner})"
        super().__init__(message, lock_name)
        self.owner = owner
        self.current_owner = current_owner


class LockExpiredError(LockError):
    """Raised when trying to operate on an expired lock."""
    
    def __init__(self, lock_name: str, expired_at: float = None):
        message = f"Lock '{lock_name}' has expired"
        if expired_at:
            message += f" (expired at: {expired_at})"
        super().__init__(message, lock_name)
        self.expired_at = expired_at


class RedisConnectionError(LockError):
    """Raised when Redis connection fails."""
    
    def __init__(self, message: str, redis_url: str = None):
        super().__init__(message)
        self.redis_url = redis_url


class QuorumError(LockError):
    """Raised when quorum cannot be achieved across Redis instances."""
    
    def __init__(self, lock_name: str, successful: int, required: int):
        message = f"Quorum failed for lock '{lock_name}': {successful}/{required} nodes"
        super().__init__(message, lock_name)
        self.successful = successful
        self.required = required
