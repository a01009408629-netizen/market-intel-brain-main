"""
Queue Manager - Priority Queue Implementation

This module provides queue management for the QoS system with both
in-memory (asyncio.PriorityQueue) and Redis-based implementations.
"""

import asyncio
import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from collections import deque

from .priority import Task, Priority
from .exceptions import QueueFullError, QueueError


class BaseQueueManager(ABC):
    """Abstract base class for queue managers."""
    
    @abstractmethod
    async def put(self, task: Task) -> bool:
        """Add a task to the queue."""
        pass
    
    @abstractmethod
    async def get(self, priority: Optional[Priority] = None) -> Optional[Task]:
        """Get a task from the queue."""
        pass
    
    @abstractmethod
    async def size(self, priority: Optional[Priority] = None) -> int:
        """Get queue size."""
        pass
    
    @abstractmethod
    async def empty(self, priority: Optional[Priority] = None) -> bool:
        """Check if queue is empty."""
        pass
    
    @abstractmethod
    async def clear(self, priority: Optional[Priority] = None):
        """Clear the queue."""
        pass


class PriorityQueueManager(BaseQueueManager):
    """
    In-memory priority queue manager using asyncio.PriorityQueue.
    
    This implementation is suitable for single-process applications
    with high-performance requirements.
    """
    
    def __init__(
        self,
        max_size: int = 10000,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize priority queue manager.
        
        Args:
            max_size: Maximum queue size
            logger: Logger instance
        """
        self.max_size = max_size
        self.logger = logger or logging.getLogger("PriorityQueueManager")
        
        # Separate queues for each priority
        self._high_queue = asyncio.PriorityQueue(maxsize=max_size)
        self._low_queue = asyncio.PriorityQueue(maxsize=max_size)
        
        # Task tracking
        self._all_tasks = {}  # task_id -> Task
        self._queue_stats = {
            'high_put_count': 0,
            'low_put_count': 0,
            'high_get_count': 0,
            'low_get_count': 0,
            'total_put_count': 0,
            'total_get_count': 0
        }
        
        self.logger.info(f"PriorityQueueManager initialized (max_size={max_size})")
    
    async def put(self, task: Task) -> bool:
        """
        Add a task to the appropriate priority queue.
        
        Args:
            task: Task to add
            
        Returns:
            True if task was added successfully
            
        Raises:
            QueueFullError: If queue is at capacity
        """
        try:
            # Check queue capacity
            if await self.size() >= self.max_size:
                raise QueueFullError("priority_queue", self.max_size, task.task_id)
            
            # Add to appropriate queue
            priority_score = task.get_priority_score()
            queue_item = (priority_score, task)
            
            if task.is_high_priority():
                await self._high_queue.put(queue_item)
                self._queue_stats['high_put_count'] += 1
            else:
                await self._low_queue.put(queue_item)
                self._queue_stats['low_put_count'] += 1
            
            self._queue_stats['total_put_count'] += 1
            self._all_tasks[task.task_id] = task
            
            self.logger.debug(f"Task {task.task_id[:8]} added to {task.priority.value} queue")
            return True
            
        except asyncio.QueueFull:
            raise QueueFullError("priority_queue", self.max_size, task.task_id)
    
    async def get(self, priority: Optional[Priority] = None) -> Optional[Task]:
        """
        Get a task from the queue.
        
        Args:
            priority: Specific priority to get from (None for any)
            
        Returns:
            Task or None if queue is empty
        """
        try:
            task = None
            
            if priority == Priority.HIGH:
                # Get from high priority queue only
                if not self._high_queue.empty():
                    _, task = await self._high_queue.get()
                    self._queue_stats['high_get_count'] += 1
                    
            elif priority == Priority.LOW:
                # Get from low priority queue only
                if not self._low_queue.empty():
                    _, task = await self._low_queue.get()
                    self._queue_stats['low_get_count'] += 1
                    
            else:
                # Priority-based selection
                # Always check high priority first
                if not self._high_queue.empty():
                    _, task = await self._high_queue.get()
                    self._queue_stats['high_get_count'] += 1
                elif not self._low_queue.empty():
                    _, task = await self._low_queue.get()
                    self._queue_stats['low_get_count'] += 1
            
            if task:
                self._queue_stats['total_get_count'] += 1
                # Remove from tracking
                if task.task_id in self._all_tasks:
                    del self._all_tasks[task.task_id]
                
                self.logger.debug(f"Task {task.task_id[:8]} retrieved from {task.priority.value} queue")
            
            return task
            
        except asyncio.QueueEmpty:
            return None
    
    async def size(self, priority: Optional[Priority] = None) -> int:
        """
        Get queue size.
        
        Args:
            priority: Specific priority to check (None for total)
            
        Returns:
            Queue size
        """
        if priority == Priority.HIGH:
            return self._high_queue.qsize()
        elif priority == Priority.LOW:
            return self._low_queue.qsize()
        else:
            return self._high_queue.qsize() + self._low_queue.qsize()
    
    async def empty(self, priority: Optional[Priority] = None) -> bool:
        """
        Check if queue is empty.
        
        Args:
            priority: Specific priority to check (None for all)
            
        Returns:
            True if queue is empty
        """
        if priority == Priority.HIGH:
            return self._high_queue.empty()
        elif priority == Priority.LOW:
            return self._low_queue.empty()
        else:
            return self._high_queue.empty() and self._low_queue.empty()
    
    async def clear(self, priority: Optional[Priority] = None):
        """
        Clear the queue.
        
        Args:
            priority: Specific priority to clear (None for all)
        """
        if priority == Priority.HIGH or priority is None:
            while not self._high_queue.empty():
                try:
                    self._high_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        
        if priority == Priority.LOW or priority is None:
            while not self._low_queue.empty():
                try:
                    self._low_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        
        # Clear task tracking
        if priority is None:
            self._all_tasks.clear()
        else:
            # Remove tasks of specified priority from tracking
            to_remove = [
                task_id for task_id, task in self._all_tasks.items()
                if task.priority == priority
            ]
            for task_id in to_remove:
                del self._all_tasks[task_id]
        
        self.logger.info(f"Cleared {priority.value if priority else 'all'} queue")
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive queue statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            'queue_sizes': {
                'high': self._high_queue.qsize(),
                'low': self._low_queue.qsize(),
                'total': self._high_queue.qsize() + self._low_queue.qsize()
            },
            'queue_stats': self._queue_stats.copy(),
            'max_size': self.max_size,
            'utilization': (self._high_queue.qsize() + self._low_queue.qsize()) / self.max_size,
            'tracked_tasks': len(self._all_tasks)
        }
    
    async def get_pending_tasks(self, priority: Optional[Priority] = None, limit: int = 100) -> List[Task]:
        """
        Get list of pending tasks.
        
        Args:
            priority: Specific priority to filter (None for all)
            limit: Maximum number of tasks to return
            
        Returns:
            List of pending tasks
        """
        tasks = []
        
        if priority is None or priority == Priority.HIGH:
            # Get tasks from high priority queue
            temp_queue = asyncio.PriorityQueue()
            
            # Transfer and collect tasks
            while not self._high_queue.empty() and len(tasks) < limit:
                try:
                    _, task = self._high_queue.get_nowait()
                    tasks.append(task)
                    temp_queue.put_nowait((task.get_priority_score(), task))
                except asyncio.QueueEmpty:
                    break
            
            # Put tasks back
            while not temp_queue.empty():
                try:
                    _, task = temp_queue.get_nowait()
                    self._high_queue.put_nowait((task.get_priority_score(), task))
                except asyncio.QueueEmpty:
                    break
        
        if (priority is None or priority == Priority.LOW) and len(tasks) < limit:
            # Get tasks from low priority queue
            temp_queue = asyncio.PriorityQueue()
            
            while not self._low_queue.empty() and len(tasks) < limit:
                try:
                    _, task = self._low_queue.get_nowait()
                    tasks.append(task)
                    await temp_queue.put((task.get_priority_score(), task))
                except asyncio.QueueEmpty:
                    break
            
            # Put tasks back
            while not temp_queue.empty():
                try:
                    _, task = temp_queue.get_nowait()
                    await self._low_queue.put((task.get_priority_score(), task))
                except asyncio.QueueEmpty:
                    break
        
        return tasks[:limit]


class RedisQueueManager(BaseQueueManager):
    """
    Redis-based distributed queue manager.
    
    This implementation provides distributed queue functionality
    suitable for multi-process or multi-server deployments.
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        queue_prefix: str = "qos",
        max_size: int = 10000,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Redis queue manager.
        
        Args:
            redis_url: Redis connection URL
            queue_prefix: Prefix for queue keys
            max_size: Maximum queue size
            logger: Logger instance
        """
        self.redis_url = redis_url
        self.queue_prefix = queue_prefix
        self.max_size = max_size
        self.logger = logger or logging.getLogger("RedisQueueManager")
        
        self._redis_client = None
        self._queue_keys = {
            Priority.HIGH: f"{queue_prefix}:high",
            Priority.LOW: f"{queue_prefix}:low"
        }
        
        self.logger.info(f"RedisQueueManager initialized (redis={redis_url})")
    
    async def _get_redis_client(self):
        """Get or create Redis client."""
        if self._redis_client is None:
            import redis.asyncio as redis
            self._redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis_client
    
    async def put(self, task: Task) -> bool:
        """
        Add a task to the Redis queue.
        
        Args:
            task: Task to add
            
        Returns:
            True if task was added successfully
            
        Raises:
            QueueFullError: If queue is at capacity
        """
        try:
            client = await self._get_redis_client()
            
            # Check queue capacity
            current_size = await self.size()
            if current_size >= self.max_size:
                raise QueueFullError("redis_queue", self.max_size, task.task_id)
            
            # Serialize task
            task_data = json.dumps(task.to_dict())
            
            # Add to appropriate queue
            queue_key = self._queue_keys[task.priority]
            
            # Use Redis list with priority score
            await client.lpush(queue_key, task_data)
            
            # Trim queue if necessary
            await client.ltrim(queue_key, 0, self.max_size - 1)
            
            self.logger.debug(f"Task {task.task_id[:8]} added to Redis {task.priority.value} queue")
            return True
            
        except Exception as e:
            raise QueueError(f"Failed to put task in Redis queue: {e}")
    
    async def get(self, priority: Optional[Priority] = None) -> Optional[Task]:
        """
        Get a task from the Redis queue.
        
        Args:
            priority: Specific priority to get from (None for any)
            
        Returns:
            Task or None if queue is empty
        """
        try:
            client = await self._get_redis_client()
            
            task = None
            
            if priority == Priority.HIGH:
                # Get from high priority queue only
                queue_key = self._queue_keys[Priority.HIGH]
                task_data = await client.brpop(queue_key, timeout=1)
                if task_data:
                    task = self._deserialize_task(task_data[1])
                    
            elif priority == Priority.LOW:
                # Get from low priority queue only
                queue_key = self._queue_keys[Priority.LOW]
                task_data = await client.brpop(queue_key, timeout=1)
                if task_data:
                    task = self._deserialize_task(task_data[1])
                    
            else:
                # Priority-based selection with timeout
                # Try high priority first with shorter timeout
                queue_key = self._queue_keys[Priority.HIGH]
                task_data = await client.brpop(queue_key, timeout=0.1)
                if task_data:
                    task = self._deserialize_task(task_data[1])
                else:
                    # Try low priority queue
                    queue_key = self._queue_keys[Priority.LOW]
                    task_data = await client.brpop(queue_key, timeout=0.9)
                    if task_data:
                        task = self._deserialize_task(task_data[1])
            
            if task:
                self.logger.debug(f"Task {task.task_id[:8]} retrieved from Redis {task.priority.value} queue")
            
            return task
            
        except Exception as e:
            raise QueueError(f"Failed to get task from Redis queue: {e}")
    
    async def size(self, priority: Optional[Priority] = None) -> int:
        """
        Get Redis queue size.
        
        Args:
            priority: Specific priority to check (None for total)
            
        Returns:
            Queue size
        """
        try:
            client = await self._get_redis_client()
            
            if priority == Priority.HIGH:
                queue_key = self._queue_keys[Priority.HIGH]
                return await client.llen(queue_key)
            elif priority == Priority.LOW:
                queue_key = self._queue_keys[Priority.LOW]
                return await client.llen(queue_key)
            else:
                high_size = await client.llen(self._queue_keys[Priority.HIGH])
                low_size = await client.llen(self._queue_keys[Priority.LOW])
                return high_size + low_size
                
        except Exception as e:
            raise QueueError(f"Failed to get queue size: {e}")
    
    async def empty(self, priority: Optional[Priority] = None) -> bool:
        """
        Check if Redis queue is empty.
        
        Args:
            priority: Specific priority to check (None for all)
            
        Returns:
            True if queue is empty
        """
        return await self.size(priority) == 0
    
    async def clear(self, priority: Optional[Priority] = None):
        """
        Clear the Redis queue.
        
        Args:
            priority: Specific priority to clear (None for all)
        """
        try:
            client = await self._get_redis_client()
            
            if priority == Priority.HIGH or priority is None:
                await client.delete(self._queue_keys[Priority.HIGH])
            
            if priority == Priority.LOW or priority is None:
                await client.delete(self._queue_keys[Priority.LOW])
            
            self.logger.info(f"Cleared Redis {priority.value if priority else 'all'} queue")
            
        except Exception as e:
            raise QueueError(f"Failed to clear queue: {e}")
    
    def _deserialize_task(self, task_data: str) -> Task:
        """Deserialize task from JSON."""
        try:
            from .priority import Task, Priority
            data = json.loads(task_data)
            
            # Reconstruct task
            task = Task(
                task_id=data['task_id'],
                priority=Priority.get_value(data['priority']),
                created_at=data['created_at'],
                func=None,  # Function not serialized
                args=tuple(data.get('args', [])),
                kwargs=data.get('kwargs', {}),
                timeout=data.get('timeout'),
                retry_count=data.get('retry_count', 0),
                max_retries=data.get('max_retries', 0),
                retry_delay=data.get('retry_delay', 1.0),
                estimated_duration=data.get('estimated_duration'),
                resource_weight=data.get('resource_weight', 1.0),
                metadata=data.get('metadata', {}),
                user_id=data.get('user_id'),
                session_id=data.get('session_id')
            )
            
            return task
            
        except Exception as e:
            raise QueueError(f"Failed to deserialize task: {e}")
    
    async def close(self):
        """Close Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
