"""
Priority System and Task Definition

This module defines the priority levels and task structure for the QoS system.
"""

import time
import uuid
from enum import Enum
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass, field


class Priority(Enum):
    """Task priority levels."""
    HIGH = "HIGH"    # Live user requests
    LOW = "LOW"      # Background sync tasks
    
    @classmethod
    def get_value(cls, priority: str) -> 'Priority':
        """Get Priority enum from string value."""
        for p in cls:
            if p.value == priority.upper():
                return p
        raise ValueError(f"Invalid priority: {priority}")
    
    def __lt__(self, other: 'Priority') -> bool:
        """Compare priorities for sorting (HIGH < LOW for priority queue)."""
        priority_order = {Priority.HIGH: 0, Priority.LOW: 1}
        return priority_order[self] < priority_order[other]


@dataclass
class Task:
    """
    Task definition for the QoS system.
    
    Tasks are prioritized and scheduled based on their priority level
    and system resource allocation.
    """
    
    # Core identification
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: Priority = Priority.LOW
    created_at: float = field(default_factory=time.time)
    
    # Task content
    func: Callable = None
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    
    # Execution metadata
    timeout: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 0
    retry_delay: float = 1.0
    
    # Resource requirements
    estimated_duration: Optional[float] = None
    resource_weight: float = 1.0  # Resource consumption weight
    
    # Callbacks
    on_success: Optional[Callable] = None
    on_failure: Optional[Callable] = None
    on_timeout: Optional[Callable] = None
    
    # Execution tracking
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[Exception] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate task after initialization."""
        if self.func is None:
            raise ValueError("Task function cannot be None")
        
        if not isinstance(self.priority, Priority):
            if isinstance(self.priority, str):
                self.priority = Priority.get_value(self.priority)
            else:
                raise ValueError(f"Invalid priority type: {type(self.priority)}")
    
    def get_priority_score(self) -> tuple:
        """
        Get priority score for queue ordering.
        
        Returns:
            Tuple for priority queue sorting (lower score = higher priority)
        """
        # Higher priority tasks have lower scores
        priority_score = 0 if self.priority == Priority.HIGH else 1
        
        # Within same priority, earlier tasks get priority
        time_score = self.created_at
        
        return (priority_score, time_score)
    
    def is_high_priority(self) -> bool:
        """Check if task is high priority."""
        return self.priority == Priority.HIGH
    
    def is_low_priority(self) -> bool:
        """Check if task is low priority."""
        return self.priority == Priority.LOW
    
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.retry_count < self.max_retries
    
    def increment_retry(self):
        """Increment retry count."""
        self.retry_count += 1
    
    def mark_started(self):
        """Mark task as started."""
        self.started_at = time.time()
    
    def mark_completed(self, result: Any = None):
        """Mark task as completed successfully."""
        self.completed_at = time.time()
        self.result = result
    
    def mark_failed(self, error: Exception):
        """Mark task as failed."""
        self.completed_at = time.time()
        self.error = error
    
    def get_duration(self) -> Optional[float]:
        """Get task execution duration."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    def get_age(self) -> float:
        """Get task age (time since creation)."""
        return time.time() - self.created_at
    
    def is_expired(self) -> bool:
        """Check if task has expired its timeout."""
        if self.timeout is None:
            return False
        
        age = self.get_age()
        return age > self.timeout
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation."""
        return {
            'task_id': self.task_id,
            'priority': self.priority.value,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'timeout': self.timeout,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'estimated_duration': self.estimated_duration,
            'resource_weight': self.resource_weight,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'metadata': self.metadata,
            'age': self.get_age(),
            'duration': self.get_duration(),
            'status': self.get_status()
        }
    
    def get_status(self) -> str:
        """Get current task status."""
        if self.completed_at is None:
            if self.started_at is None:
                return 'pending'
            else:
                return 'running'
        else:
            if self.error is None:
                return 'completed'
            else:
                return 'failed'
    
    def __str__(self) -> str:
        """String representation."""
        return (
            f"Task(id={self.task_id[:8]}, "
            f"priority={self.priority.value}, "
            f"status={self.get_status()})"
        )
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return self.__str__()


class TaskBuilder:
    """Builder pattern for creating tasks with fluent interface."""
    
    def __init__(self, func: Callable, priority: Priority = Priority.LOW):
        self._task = Task(func=func, priority=priority)
    
    def with_args(self, *args) -> 'TaskBuilder':
        """Set positional arguments."""
        self._task.args = args
        return self
    
    def with_kwargs(self, **kwargs) -> 'TaskBuilder':
        """Set keyword arguments."""
        self._task.kwargs = kwargs
        return self
    
    def with_timeout(self, timeout: float) -> 'TaskBuilder':
        """Set task timeout."""
        self._task.timeout = timeout
        return self
    
    def with_retries(self, max_retries: int, retry_delay: float = 1.0) -> 'TaskBuilder':
        """Set retry configuration."""
        self._task.max_retries = max_retries
        self._task.retry_delay = retry_delay
        return self
    
    def with_resource_weight(self, weight: float) -> 'TaskBuilder':
        """Set resource consumption weight."""
        self._task.resource_weight = weight
        return self
    
    def with_metadata(self, **metadata) -> 'TaskBuilder':
        """Set metadata."""
        self._task.metadata.update(metadata)
        return self
    
    def with_user(self, user_id: str) -> 'TaskBuilder':
        """Set user ID."""
        self._task.user_id = user_id
        return self
    
    def with_session(self, session_id: str) -> 'TaskBuilder':
        """Set session ID."""
        self._task.session_id = session_id
        return self
    
    def on_success(self, callback: Callable) -> 'TaskBuilder':
        """Set success callback."""
        self._task.on_success = callback
        return self
    
    def on_failure(self, callback: Callable) -> 'TaskBuilder':
        """Set failure callback."""
        self._task.on_failure = callback
        return self
    
    def on_timeout(self, callback: Callable) -> 'TaskBuilder':
        """Set timeout callback."""
        self._task.on_timeout = callback
        return self
    
    def build(self) -> Task:
        """Build the task."""
        return self._task


# Convenience functions for creating tasks
def create_task(func: Callable, priority: Priority = Priority.LOW, **kwargs) -> Task:
    """
    Create a task with the given function and priority.
    
    Args:
        func: Function to execute
        priority: Task priority
        **kwargs: Additional task parameters
        
    Returns:
        Task instance
    """
    return Task(func=func, priority=priority, **kwargs)


def high_priority_task(func: Callable, **kwargs) -> Task:
    """Create a high priority task."""
    return create_task(func, Priority.HIGH, **kwargs)


def low_priority_task(func: Callable, **kwargs) -> Task:
    """Create a low priority task."""
    return create_task(func, Priority.LOW, **kwargs)


def task_builder(func: Callable, priority: Priority = Priority.LOW) -> TaskBuilder:
    """
    Create a task builder for fluent interface.
    
    Args:
        func: Function to execute
        priority: Task priority
        
    Returns:
        TaskBuilder instance
    """
    return TaskBuilder(func, priority)
