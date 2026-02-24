"""
Task Dispatcher - QoS-Aware Task Execution

This module provides a task dispatcher that respects QoS policies
by prioritizing user requests over background tasks.
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass

from .priority import Task, Priority
from .queue_manager import BaseQueueManager, PriorityQueueManager, RedisQueueManager
from .exceptions import (
    DispatcherError,
    TaskTimeoutError,
    ResourceExhaustionError,
    ConfigurationError
)


@dataclass
class DispatcherConfig:
    """Configuration for task dispatcher."""
    
    # Resource allocation
    high_priority_resource_ratio: float = 0.8  # 80% for HIGH priority
    max_concurrent_tasks: int = 10
    max_high_priority_tasks: Optional[int] = None  # Calculated from ratio if None
    
    # Queue management
    queue_type: str = "memory"  # "memory" or "redis"
    redis_url: str = "redis://localhost:6379"
    queue_max_size: int = 10000
    
    # Task execution
    default_task_timeout: float = 300.0  # 5 minutes
    task_retry_delay: float = 1.0
    max_task_retries: int = 3
    
    # Monitoring
    enable_metrics: bool = True
    metrics_interval: float = 10.0  # seconds
    
    def __post_init__(self):
        """Validate configuration."""
        if not 0.0 <= self.high_priority_resource_ratio <= 1.0:
            raise ConfigurationError(
                "high_priority_resource_ratio",
                self.high_priority_resource_ratio,
                "must be between 0.0 and 1.0"
            )
        
        if self.max_concurrent_tasks <= 0:
            raise ConfigurationError(
                "max_concurrent_tasks",
                self.max_concurrent_tasks,
                "must be positive"
            )
        
        # Calculate max high priority tasks if not specified
        if self.max_high_priority_tasks is None:
            self.max_high_priority_tasks = int(
                self.max_concurrent_tasks * self.high_priority_resource_ratio
            )
        
        if self.max_high_priority_tasks >= self.max_concurrent_tasks:
            raise ConfigurationError(
                "max_high_priority_tasks",
                self.max_high_priority_tasks,
                "must be less than max_concurrent_tasks"
            )


class TaskDispatcher:
    """
    QoS-aware task dispatcher.
    
    This dispatcher ensures that high priority tasks (user requests)
    get preferential treatment over low priority tasks (background sync)
    while maintaining fair resource allocation.
    """
    
    def __init__(
        self,
        config: Optional[DispatcherConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize task dispatcher.
        
        Args:
            config: Dispatcher configuration
            logger: Logger instance
        """
        self.config = config or DispatcherConfig()
        self.logger = logger or logging.getLogger("TaskDispatcher")
        
        # Initialize queue manager
        self._queue_manager = self._create_queue_manager()
        
        # Execution state
        self._running_tasks = {}  # task_id -> asyncio.Task
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_tasks)
        self._high_priority_semaphore = asyncio.Semaphore(self.config.max_high_priority_tasks)
        
        # Statistics
        self._stats = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'tasks_timed_out': 0,
            'high_priority_completed': 0,
            'low_priority_completed': 0,
            'total_execution_time': 0.0,
            'average_execution_time': 0.0,
            'start_time': time.time()
        }
        
        # Background task for processing
        self._processor_task = None
        self._running = False
        
        self.logger.info(
            f"TaskDispatcher initialized: "
            f"max_concurrent={self.config.max_concurrent_tasks}, "
            f"max_high_priority={self.config.max_high_priority_tasks}, "
            f"resource_ratio={self.config.high_priority_resource_ratio:.1%}"
        )
    
    def _create_queue_manager(self) -> BaseQueueManager:
        """Create appropriate queue manager based on configuration."""
        if self.config.queue_type == "memory":
            return PriorityQueueManager(
                max_size=self.config.queue_max_size,
                logger=self.logger
            )
        elif self.config.queue_type == "redis":
            return RedisQueueManager(
                redis_url=self.config.redis_url,
                max_size=self.config.queue_max_size,
                logger=self.logger
            )
        else:
            raise ConfigurationError(
                "queue_type",
                self.config.queue_type,
                "must be 'memory' or 'redis'"
            )
    
    async def start(self):
        """Start the task dispatcher."""
        if self._running:
            return
        
        self._running = True
        self._processor_task = asyncio.create_task(self._processing_loop())
        
        self.logger.info("TaskDispatcher started")
    
    async def stop(self):
        """Stop the task dispatcher."""
        if not self._running:
            return
        
        self._running = False
        
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        # Wait for running tasks to complete
        if self._running_tasks:
            await asyncio.gather(
                *self._running_tasks.values(),
                return_exceptions=True
            )
        
        self.logger.info("TaskDispatcher stopped")
    
    async def submit_task(self, task: Task) -> str:
        """
        Submit a task for execution.
        
        Args:
            task: Task to execute
            
        Returns:
            Task ID
            
        Raises:
            DispatcherError: If task submission fails
        """
        try:
            # Set default timeout if not specified
            if task.timeout is None:
                task.timeout = self.config.default_task_timeout
            
            # Set default retry settings if not specified
            if task.max_retries == 0:
                task.max_retries = self.config.max_task_retries
                task.retry_delay = self.config.task_retry_delay
            
            # Add to queue
            success = await self._queue_manager.put(task)
            if not success:
                raise DispatcherError(f"Failed to queue task {task.task_id}")
            
            self.logger.debug(f"Task {task.task_id[:8]} submitted ({task.priority.value})")
            return task.task_id
            
        except Exception as e:
            raise DispatcherError(f"Failed to submit task: {e}")
    
    async def _processing_loop(self):
        """Main processing loop for task execution."""
        while self._running:
            try:
                # Get next task with QoS logic
                task = await self._get_next_task()
                
                if task is None:
                    # No tasks available, wait a bit
                    await asyncio.sleep(0.1)
                    continue
                
                # Execute task
                await self._execute_task(task)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in processing loop: {e}")
                await asyncio.sleep(1.0)
    
    async def _get_next_task(self) -> Optional[Task]:
        """
        Get the next task following QoS policies.
        
        Returns:
            Next task to execute or None
        """
        # Check if we can execute more tasks
        if len(self._running_tasks) >= self.config.max_concurrent_tasks:
            return None
        
        # Priority-based selection
        # Always prefer high priority tasks
        high_priority_task = await self._queue_manager.get(Priority.HIGH)
        if high_priority_task:
            return high_priority_task
        
        # Check if we have capacity for low priority tasks
        high_priority_running = sum(
            1 for task in self._running_tasks.values()
            if task.is_high_priority()
        )
        
        if high_priority_running >= self.config.max_high_priority_tasks:
            # No capacity for low priority tasks
            return None
        
        # Get low priority task
        low_priority_task = await self._queue_manager.get(Priority.LOW)
        return low_priority_task
    
    async def _execute_task(self, task: Task):
        """
        Execute a task with proper resource management.
        
        Args:
            task: Task to execute
        """
        # Choose appropriate semaphore
        semaphore = self._high_priority_semaphore if task.is_high_priority() else self._semaphore
        
        async with semaphore:
            # Check if task has already timed out
            if task.is_expired():
                await self._handle_task_timeout(task)
                return
            
            # Mark task as started
            task.mark_started()
            self._running_tasks[task.task_id] = asyncio.current_task()
            
            execution_start = time.time()
            
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    self._run_task_func(task),
                    timeout=task.timeout
                )
                
                # Mark as completed
                task.mark_completed(result)
                await self._handle_task_success(task)
                
            except asyncio.TimeoutError:
                await self._handle_task_timeout(task)
                
            except Exception as e:
                task.mark_failed(e)
                await self._handle_task_failure(task, e)
                
            finally:
                # Update statistics
                execution_time = time.time() - execution_start
                self._update_stats(task, execution_time)
                
                # Clean up
                if task.task_id in self._running_tasks:
                    del self._running_tasks[task.task_id]
    
    async def _run_task_func(self, task: Task) -> Any:
        """
        Run the task function.
        
        Args:
            task: Task to execute
            
        Returns:
            Task result
        """
        try:
            if asyncio.iscoroutinefunction(task.func):
                return await task.func(*task.args, **task.kwargs)
            else:
                return task.func(*task.args, **task.kwargs)
        except Exception as e:
            self.logger.error(f"Task function error: {e}")
            raise
    
    async def _handle_task_success(self, task: Task):
        """Handle successful task completion."""
        self._stats['tasks_completed'] += 1
        
        if task.is_high_priority():
            self._stats['high_priority_completed'] += 1
        else:
            self._stats['low_priority_completed'] += 1
        
        # Call success callback if provided
        if task.on_success:
            try:
                if asyncio.iscoroutinefunction(task.on_success):
                    await task.on_success(task)
                else:
                    task.on_success(task)
            except Exception as e:
                self.logger.error(f"Success callback error: {e}")
        
        self.logger.info(f"Task {task.task_id[:8]} completed successfully")
    
    async def _handle_task_failure(self, task: Task, error: Exception):
        """Handle task failure."""
        self._stats['tasks_failed'] += 1
        
        # Check if we should retry
        if task.can_retry():
            task.increment_retry()
            
            self.logger.warning(
                f"Task {task.task_id[:8]} failed, retrying "
                f"({task.retry_count}/{task.max_retries}): {error}"
            )
            
            # Schedule retry
            await asyncio.sleep(task.retry_delay)
            await self.submit_task(task)
        else:
            self.logger.error(
                f"Task {task.task_id[:8]} failed permanently: {error}"
            )
            
            # Call failure callback if provided
            if task.on_failure:
                try:
                    if asyncio.iscoroutinefunction(task.on_failure):
                        await task.on_failure(task, error)
                    else:
                        task.on_failure(task, error)
                except Exception as e:
                    self.logger.error(f"Failure callback error: {e}")
    
    async def _handle_task_timeout(self, task: Task):
        """Handle task timeout."""
        self._stats['tasks_timed_out'] += 1
        
        timeout_error = TaskTimeoutError(
            task.task_id,
            task.timeout,
            f"Task execution exceeded {task.timeout}s"
        )
        
        self.logger.error(f"Task {task.task_id[:8]} timed out")
        
        # Call timeout callback if provided
        if task.on_timeout:
            try:
                if asyncio.iscoroutinefunction(task.on_timeout):
                    await task.on_timeout(task)
                else:
                    task.on_timeout(task)
            except Exception as e:
                self.logger.error(f"Timeout callback error: {e}")
    
    def _update_stats(self, task: Task, execution_time: float):
        """Update execution statistics."""
        self._stats['total_execution_time'] += execution_time
        completed_tasks = (
            self._stats['tasks_completed'] + 
            self._stats['tasks_failed'] + 
            self._stats['tasks_timed_out']
        )
        
        if completed_tasks > 0:
            self._stats['average_execution_time'] = (
                self._stats['total_execution_time'] / completed_tasks
            )
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        queue_stats = self._queue_manager.get_queue_stats() if hasattr(self._queue_manager, 'get_queue_stats') else {}
        
        return {
            'queue_stats': queue_stats,
            'running_tasks': len(self._running_tasks),
            'high_priority_running': sum(
                1 for task in self._running_tasks.values()
                if task.is_high_priority()
            ),
            'low_priority_running': sum(
                1 for task in self._running_tasks.values()
                if task.is_low_priority()
            ),
            'capacity': {
                'total': self.config.max_concurrent_tasks,
                'high_priority': self.config.max_high_priority_tasks,
                'available': self.config.max_concurrent_tasks - len(self._running_tasks),
                'high_priority_available': (
                    self.config.max_high_priority_tasks - 
                    sum(1 for task in self._running_tasks.values() if task.is_high_priority())
                )
            }
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        current_time = time.time()
        uptime = current_time - self._stats['start_time']
        
        return {
            'uptime': uptime,
            'tasks_completed': self._stats['tasks_completed'],
            'tasks_failed': self._stats['tasks_failed'],
            'tasks_timed_out': self._stats['tasks_timed_out'],
            'high_priority_completed': self._stats['high_priority_completed'],
            'low_priority_completed': self._stats['low_priority_completed'],
            'total_execution_time': self._stats['total_execution_time'],
            'average_execution_time': self._stats['average_execution_time'],
            'tasks_per_second': self._stats['tasks_completed'] / uptime if uptime > 0 else 0,
            'success_rate': (
                self._stats['tasks_completed'] / 
                (self._stats['tasks_completed'] + self._stats['tasks_failed'] + self._stats['tasks_timed_out'])
                if (self._stats['tasks_completed'] + self._stats['tasks_failed'] + self._stats['tasks_timed_out']) > 0
                else 0
            )
        }
    
    async def get_pending_tasks(self, priority: Optional[Priority] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get list of pending tasks.
        
        Args:
            priority: Filter by priority (None for all)
            limit: Maximum number of tasks to return
            
        Returns:
            List of task dictionaries
        """
        if hasattr(self._queue_manager, 'get_pending_tasks'):
            tasks = await self._queue_manager.get_pending_tasks(priority, limit)
            return [task.to_dict() for task in tasks]
        else:
            return []
    
    def is_running(self) -> bool:
        """Check if dispatcher is running."""
        return self._running
    
    def get_config(self) -> DispatcherConfig:
        """Get current configuration."""
        return self.config


# Global dispatcher instance
_global_dispatcher: Optional[TaskDispatcher] = None


def get_dispatcher(**kwargs) -> TaskDispatcher:
    """
    Get or create the global task dispatcher.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global TaskDispatcher instance
    """
    global _global_dispatcher
    if _global_dispatcher is None:
        _global_dispatcher = TaskDispatcher(**kwargs)
    return _global_dispatcher


# Convenience functions for global usage
async def submit_high_priority_task(func: Callable, *args, **kwargs) -> str:
    """Submit a high priority task using global dispatcher."""
    from .priority import high_priority_task
    
    task = high_priority_task(func, *args, **kwargs)
    dispatcher = get_dispatcher()
    return await dispatcher.submit_task(task)


async def submit_low_priority_task(func: Callable, *args, **kwargs) -> str:
    """Submit a low priority task using global dispatcher."""
    from .priority import low_priority_task
    
    task = low_priority_task(func, *args, **kwargs)
    dispatcher = get_dispatcher()
    return await dispatcher.submit_task(task)


async def start_dispatcher(**kwargs):
    """Start the global dispatcher."""
    dispatcher = get_dispatcher(**kwargs)
    await dispatcher.start()


async def stop_dispatcher():
    """Stop the global dispatcher."""
    dispatcher = get_dispatcher()
    await dispatcher.stop()
