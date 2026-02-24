"""
QoS Scheduler - High-Level Scheduling Interface

This module provides a high-level scheduler that manages task dispatching
with QoS policies to ensure optimal user experience.
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass

from .priority import Task, Priority, create_task, high_priority_task, low_priority_task
from .task_dispatcher import TaskDispatcher, DispatcherConfig, get_dispatcher
from .exceptions import SchedulerError, ConfigurationError


@dataclass
class SchedulerConfig:
    """Configuration for QoS scheduler."""
    
    # Dispatcher configuration
    dispatcher_config: Optional[DispatcherConfig] = None
    
    # Scheduling policies
    auto_start: bool = True
    enable_monitoring: bool = True
    monitoring_interval: float = 5.0  # seconds
    
    # User experience protection
    max_low_priority_delay: float = 10.0  # seconds
    low_priority_throttle_rate: float = 0.1  # tasks per second
    
    # Callbacks
    on_task_completed: Optional[Callable] = None
    on_task_failed: Optional[Callable] = None
    on_queue_full: Optional[Callable] = None
    
    def __post_init__(self):
        """Validate configuration."""
        if self.max_low_priority_delay <= 0:
            raise ConfigurationError(
                "max_low_priority_delay",
                self.max_low_priority_delay,
                "must be positive"
            )
        
        if not 0.0 <= self.low_priority_throttle_rate <= 1.0:
            raise ConfigurationError(
                "low_priority_throttle_rate",
                self.low_priority_throttle_rate,
                "must be between 0.0 and 1.0"
            )


class QoSScheduler:
    """
    High-level QoS scheduler that protects user experience.
    
    This scheduler ensures that high priority tasks (user requests)
    are processed immediately while low priority tasks (background sync)
    are processed during idle periods or with controlled throttling.
    """
    
    def __init__(
        self,
        config: Optional[SchedulerConfig] = None,
        dispatcher: Optional[TaskDispatcher] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize QoS scheduler.
        
        Args:
            config: Scheduler configuration
            dispatcher: External task dispatcher (creates new if None)
            logger: Logger instance
        """
        self.config = config or SchedulerConfig()
        self.logger = logger or logging.getLogger("QoSScheduler")
        
        # Initialize or use provided dispatcher
        if dispatcher:
            self.dispatcher = dispatcher
        else:
            self.dispatcher = TaskDispatcher(
                self.config.dispatcher_config,
                self.logger
            )
        
        # Scheduling state
        self._running = False
        self._monitor_task = None
        
        # Low priority throttling
        self._last_low_priority_time = 0.0
        self._low_priority_count = 0
        
        # Statistics
        self._stats = {
            'tasks_submitted': 0,
            'high_priority_submitted': 0,
            'low_priority_submitted': 0,
            'tasks_rejected': 0,
            'low_priority_delayed': 0,
            'start_time': time.time()
        }
        
        # Start automatically if configured
        if self.config.auto_start:
            asyncio.create_task(self.start())
        
        self.logger.info("QoSScheduler initialized")
    
    async def start(self):
        """Start the scheduler."""
        if self._running:
            return
        
        self._running = True
        
        # Start the dispatcher
        await self.dispatcher.start()
        
        # Start monitoring if enabled
        if self.config.enable_monitoring:
            self._monitor_task = asyncio.create_task(self._monitoring_loop())
        
        self.logger.info("QoSScheduler started")
    
    async def stop(self):
        """Stop the scheduler."""
        if not self._running:
            return
        
        self._running = False
        
        # Stop monitoring
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        # Stop dispatcher
        await self.dispatcher.stop()
        
        self.logger.info("QoSScheduler stopped")
    
    async def submit_user_request(
        self,
        func: Callable,
        *args,
        timeout: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Submit a high priority user request.
        
        Args:
            func: Function to execute
            *args: Function arguments
            timeout: Task timeout
            **kwargs: Function keyword arguments
            
        Returns:
            Task ID
        """
        task = high_priority_task(
            func,
            *args,
            timeout=timeout,
            **kwargs
        )
        
        # Add user request metadata
        task.metadata.update({
            'request_type': 'user_request',
            'submitted_at': time.time()
        })
        
        return await self._submit_task(task)
    
    async def submit_background_task(
        self,
        func: Callable,
        *args,
        timeout: Optional[float] = None,
        priority: Priority = Priority.LOW,
        **kwargs
    ) -> str:
        """
        Submit a background task.
        
        Args:
            func: Function to execute
            *args: Function arguments
            timeout: Task timeout
            priority: Task priority (default LOW)
            **kwargs: Function keyword arguments
            
        Returns:
            Task ID
        """
        task = create_task(
            func,
            priority,
            *args,
            timeout=timeout,
            **kwargs
        )
        
        # Add background task metadata
        task.metadata.update({
            'request_type': 'background_task',
            'submitted_at': time.time()
        })
        
        return await self._submit_task(task)
    
    async def _submit_task(self, task: Task) -> str:
        """
        Submit a task with QoS policies.
        
        Args:
            task: Task to submit
            
        Returns:
            Task ID
        """
        self._stats['tasks_submitted'] += 1
        
        if task.is_high_priority():
            self._stats['high_priority_submitted'] += 1
            # High priority tasks are submitted immediately
            return await self.dispatcher.submit_task(task)
        
        else:
            self._stats['low_priority_submitted'] += 1
            
            # Apply QoS policies for low priority tasks
            if not await self._can_submit_low_priority():
                self._stats['tasks_rejected'] += 1
                
                # Call queue full callback if provided
                if self.config.on_queue_full:
                    try:
                        if asyncio.iscoroutinefunction(self.config.on_queue_full):
                            await self.config.on_queue_full(task)
                        else:
                            self.config.on_queue_full(task)
                    except Exception as e:
                        self.logger.error(f"Queue full callback error: {e}")
                
                raise SchedulerError(
                    f"Cannot submit low priority task {task.task_id}: "
                    f"QoS policies prevent submission"
                )
            
            # Apply throttling if needed
            if self.config.low_priority_throttle_rate < 1.0:
                await self._apply_throttling()
            
            self._last_low_priority_time = time.time()
            return await self.dispatcher.submit_task(task)
    
    async def _can_submit_low_priority(self) -> bool:
        """
        Check if low priority task can be submitted.
        
        Returns:
            True if submission is allowed
        """
        # Check if high priority queue is empty
        queue_status = self.dispatcher.get_queue_status()
        high_priority_queue_size = queue_status.get('queue_stats', {}).get('queue_sizes', {}).get('high', 0)
        
        if high_priority_queue_size == 0:
            return True
        
        # Check if we have available capacity for low priority tasks
        low_priority_available = queue_status.get('capacity', {}).get('low_priority_available', 0)
        
        if low_priority_available > 0:
            return True
        
        # Check delay policy
        time_since_last_high = time.time() - self._last_low_priority_time
        if time_since_last_high > self.config.max_low_priority_delay:
            return True
        
        return False
    
    async def _apply_throttling(self):
        """Apply throttling to low priority tasks."""
        if self.config.low_priority_throttle_rate >= 1.0:
            return
        
        # Calculate delay based on throttle rate
        min_interval = 1.0 / self.config.low_priority_throttle_rate
        
        time_since_last = time.time() - self._last_low_priority_time
        if time_since_last < min_interval:
            delay = min_interval - time_since_last
            self.logger.debug(f"Throttling low priority task for {delay:.2f}s")
            await asyncio.sleep(delay)
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while self._running:
            try:
                await self._collect_metrics()
                await asyncio.sleep(self.config.monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(1.0)
    
    async def _collect_metrics(self):
        """Collect and log performance metrics."""
        queue_status = self.dispatcher.get_queue_status()
        performance_stats = self.dispatcher.get_performance_stats()
        
        # Log key metrics
        self.logger.info(
            f"QoS Metrics - "
            f"Queue: H={queue_status.get('queue_stats', {}).get('queue_sizes', {}).get('high', 0)}, "
            f"L={queue_status.get('queue_stats', {}).get('queue_sizes', {}).get('low', 0)}, "
            f"Running: {queue_status.get('running_tasks', 0)}, "
            f"Completed: {performance_stats.get('tasks_completed', 0)}, "
            f"Success Rate: {performance_stats.get('success_rate', 0):.2%}"
        )
        
        # Check for potential issues
        await self._check_performance_issues(queue_status, performance_stats)
    
    async def _check_performance_issues(self, queue_status: Dict, performance_stats: Dict):
        """Check for performance issues and alert if needed."""
        # Check for queue buildup
        high_queue_size = queue_status.get('queue_stats', {}).get('queue_sizes', {}).get('high', 0)
        if high_queue_size > 100:  # Configurable threshold
            self.logger.warning(
                f"High priority queue buildup detected: {high_queue_size} tasks"
            )
        
        # Check for low success rate
        success_rate = performance_stats.get('success_rate', 1.0)
        if success_rate < 0.9:  # 90% success rate threshold
            self.logger.warning(
                f"Low success rate detected: {success_rate:.2%}"
            )
        
        # Check for high average execution time
        avg_execution_time = performance_stats.get('average_execution_time', 0)
        if avg_execution_time > 30.0:  # 30 seconds threshold
            self.logger.warning(
                f"High average execution time: {avg_execution_time:.2f}s"
            )
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get comprehensive scheduler status."""
        queue_status = self.dispatcher.get_queue_status()
        performance_stats = self.dispatcher.get_performance_stats()
        
        return {
            'running': self._running,
            'config': {
                'auto_start': self.config.auto_start,
                'max_low_priority_delay': self.config.max_low_priority_delay,
                'low_priority_throttle_rate': self.config.low_priority_throttle_rate
            },
            'queue_status': queue_status,
            'performance_stats': performance_stats,
            'scheduler_stats': {
                'tasks_submitted': self._stats['tasks_submitted'],
                'high_priority_submitted': self._stats['high_priority_submitted'],
                'low_priority_submitted': self._stats['low_priority_submitted'],
                'tasks_rejected': self._stats['tasks_rejected'],
                'low_priority_delayed': self._stats['low_priority_delayed'],
                'uptime': time.time() - self._stats['start_time']
            }
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
        return await self.dispatcher.get_pending_tasks(priority, limit)
    
    def get_queue_sizes(self) -> Dict[str, int]:
        """Get current queue sizes."""
        queue_status = self.dispatcher.get_queue_status()
        queue_sizes = queue_status.get('queue_stats', {}).get('queue_sizes', {})
        
        return {
            'high_priority': queue_sizes.get('high', 0),
            'low_priority': queue_sizes.get('low', 0),
            'total': queue_sizes.get('total', 0)
        }
    
    def is_healthy(self) -> bool:
        """Check if the scheduler is healthy."""
        if not self._running:
            return False
        
        queue_status = self.dispatcher.get_queue_status()
        performance_stats = self.dispatcher.get_performance_stats()
        
        # Check for critical issues
        high_queue_size = queue_status.get('queue_stats', {}).get('queue_sizes', {}).get('high', 0)
        success_rate = performance_stats.get('success_rate', 1.0)
        
        # Healthy if no critical issues
        return high_queue_size < 1000 and success_rate > 0.8
    
    async def force_process_low_priority(self):
        """Force processing of low priority tasks (emergency override)."""
        self.logger.warning("Forcing low priority task processing")
        
        # Temporarily disable throttling
        original_throttle_rate = self.config.low_priority_throttle_rate
        self.config.low_priority_throttle_rate = 1.0
        
        try:
            # Submit a dummy task to trigger processing
            async def dummy_task():
                pass
            
            await self.submit_background_task(dummy_task)
            
        finally:
            # Restore original throttle rate
            await asyncio.sleep(0.1)
            self.config.low_priority_throttle_rate = original_throttle_rate
    
    def update_config(self, **kwargs):
        """Update scheduler configuration."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                self.logger.info(f"Updated config: {key} = {value}")
    
    def get_config(self) -> SchedulerConfig:
        """Get current configuration."""
        return self.config


# Global scheduler instance
_global_scheduler: Optional[QoSScheduler] = None


def get_scheduler(**kwargs) -> QoSScheduler:
    """
    Get or create the global QoS scheduler.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global QoSScheduler instance
    """
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = QoSScheduler(**kwargs)
    return _global_scheduler


# Convenience functions for global usage
async def submit_user_request(func: Callable, *args, **kwargs) -> str:
    """Submit a user request using global scheduler."""
    scheduler = get_scheduler()
    return await scheduler.submit_user_request(func, *args, **kwargs)


async def submit_background_task(func: Callable, *args, **kwargs) -> str:
    """Submit a background task using global scheduler."""
    scheduler = get_scheduler()
    return await scheduler.submit_background_task(func, *args, **kwargs)


async def start_scheduler(**kwargs):
    """Start the global scheduler."""
    scheduler = get_scheduler(**kwargs)
    await scheduler.start()


async def stop_scheduler():
    """Stop the global scheduler."""
    scheduler = get_scheduler()
    await scheduler.stop()


def get_queue_status():
    """Get queue status from global scheduler."""
    scheduler = get_scheduler()
    return scheduler.get_queue_sizes()


def is_scheduler_healthy():
    """Check if global scheduler is healthy."""
    scheduler = get_scheduler()
    return scheduler.is_healthy()
