"""
Quality of Service (QoS) & Priority Queueing System

This module provides a priority-based task scheduling system that ensures
user requests take priority over background tasks while maintaining
fair resource allocation.
"""

from .priority import Priority, Task
from .queue_manager import PriorityQueueManager, RedisQueueManager
from .task_dispatcher import TaskDispatcher, get_dispatcher
from .scheduler import QoSScheduler, get_scheduler
from .exceptions import (
    QoSError,
    QueueFullError,
    TaskTimeoutError,
    InvalidPriorityError
)

__all__ = [
    # Core classes
    'Priority',
    'Task',
    'PriorityQueueManager',
    'RedisQueueManager',
    'TaskDispatcher',
    'QoSScheduler',
    
    # Convenience functions
    'get_dispatcher',
    'get_scheduler',
    
    # Exceptions
    'QoSError',
    'QueueFullError',
    'TaskTimeoutError',
    'InvalidPriorityError'
]

# Global instances
_global_dispatcher = None
_global_scheduler = None


def get_global_dispatcher(**kwargs) -> TaskDispatcher:
    """Get or create the global task dispatcher."""
    global _global_dispatcher
    if _global_dispatcher is None:
        _global_dispatcher = TaskDispatcher(**kwargs)
    return _global_dispatcher


def get_global_scheduler(**kwargs) -> QoSScheduler:
    """Get or create the global QoS scheduler."""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = QoSScheduler(**kwargs)
    return _global_scheduler
