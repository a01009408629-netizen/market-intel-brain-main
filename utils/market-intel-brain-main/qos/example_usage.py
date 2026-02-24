"""
QoS & Priority Queueing - Example Usage

This file demonstrates how to use the QoS system to prioritize
user requests over background tasks while maintaining fair resource allocation.
"""

import asyncio
import time
import random
from typing import Dict, Any

from qos import (
    QoSScheduler,
    TaskDispatcher,
    Priority,
    create_task,
    high_priority_task,
    low_priority_task,
    get_scheduler,
    submit_user_request,
    submit_background_task
)
from qos.priority import TaskBuilder
from qos.task_dispatcher import DispatcherConfig


# Example functions to be executed as tasks
async def user_api_request(user_id: str, request_data: Dict[str, Any]):
    """Simulate a user API request."""
    print(f"    📱 Processing user {user_id} request: {request_data}")
    
    # Simulate API processing time
    await asyncio.sleep(random.uniform(0.1, 0.5))
    
    result = {
        "user_id": user_id,
        "status": "success",
        "data": f"Processed {request_data}",
        "timestamp": time.time()
    }
    
    print(f"    ✅ User {user_id} request completed")
    return result


async def background_data_sync(data_type: str, record_count: int):
    """Simulate background data synchronization."""
    print(f"    🔄 Starting background sync: {data_type} ({record_count} records)")
    
    # Simulate longer processing time for background tasks
    await asyncio.sleep(random.uniform(2.0, 5.0))
    
    result = {
        "data_type": data_type,
        "records_processed": record_count,
        "status": "completed",
        "timestamp": time.time()
    }
    
    print(f"    ✅ Background sync completed: {data_type}")
    return result


async def background_cache_refresh(cache_key: str):
    """Simulate background cache refresh."""
    print(f"    🗄️ Refreshing cache: {cache_key}")
    
    # Simulate cache refresh time
    await asyncio.sleep(random.uniform(1.0, 3.0))
    
    result = {
        "cache_key": cache_key,
        "status": "refreshed",
        "timestamp": time.time()
    }
    
    print(f"    ✅ Cache refreshed: {cache_key}")
    return result


async def long_running_analysis(analysis_type: str):
    """Simulate a long-running analysis task."""
    print(f"    📊 Starting analysis: {analysis_type}")
    
    # Simulate very long processing time
    await asyncio.sleep(random.uniform(10.0, 20.0))
    
    result = {
        "analysis_type": analysis_type,
        "status": "completed",
        "insights": f"Analysis results for {analysis_type}",
        "timestamp": time.time()
    }
    
    print(f"    ✅ Analysis completed: {analysis_type}")
    return result


async def demonstrate_basic_priority_handling():
    """Demonstrate basic priority handling."""
    print("=== Basic Priority Handling ===\n")
    
    # Create scheduler with custom configuration
    from qos.scheduler import SchedulerConfig
    
    config = SchedulerConfig(
        auto_start=True,
        max_low_priority_delay=5.0,
        low_priority_throttle_rate=0.5  # Max 2 low priority tasks per second
    )
    
    scheduler = QoSScheduler(config)
    await scheduler.start()
    
    try:
        print("1. Submitting mixed priority tasks:")
        
        # Submit some background tasks first
        bg_task1 = await scheduler.submit_background_task(
            background_data_sync,
            "user_profiles",
            1000
        )
        print(f"   Background task 1 submitted: {bg_task1[:8]}")
        
        bg_task2 = await scheduler.submit_background_task(
            background_cache_refresh,
            "user_sessions"
        )
        print(f"   Background task 2 submitted: {bg_task2[:8]}")
        
        # Wait a bit
        await asyncio.sleep(1)
        
        # Submit high priority user request
        user_task1 = await scheduler.submit_user_request(
            user_api_request,
            "user123",
            {"action": "get_profile"}
        )
        print(f"   User request 1 submitted: {user_task1[:8]} (HIGH PRIORITY)")
        
        # Submit another user request immediately
        user_task2 = await scheduler.submit_user_request(
            user_api_request,
            "user456",
            {"action": "update_settings"}
        )
        print(f"   User request 2 submitted: {user_task2[:8]} (HIGH PRIORITY)")
        
        # Submit another background task
        bg_task3 = await scheduler.submit_background_task(
            background_data_sync,
            "analytics_data",
            5000
        )
        print(f"   Background task 3 submitted: {bg_task3[:8]} (will wait)")
        
        # Wait for some tasks to complete
        print("\n2. Waiting for task completion...")
        await asyncio.sleep(8)
        
        # Show queue status
        queue_sizes = scheduler.get_queue_sizes()
        print(f"\n3. Queue status: {queue_sizes}")
        
    finally:
        await scheduler.stop()


async def demonstrate_qos_policies():
    """Demonstrate QoS policies in action."""
    print("\n=== QoS Policies Demonstration ===\n")
    
    # Create dispatcher with resource allocation
    dispatcher_config = DispatcherConfig(
        max_concurrent_tasks=5,
        high_priority_resource_ratio=0.8,  # 80% for HIGH priority
        max_concurrent_tasks=5
    )
    
    dispatcher = TaskDispatcher(dispatcher_config)
    await dispatcher.start()
    
    try:
        print("1. Submitting tasks to test resource allocation:")
        
        # Submit high priority tasks (should get 80% of resources)
        high_tasks = []
        for i in range(8):  # Submit 8 high priority tasks
            task = high_priority_task(
                user_api_request,
                f"user{i}",
                {"action": f"request_{i}"}
            )
            task_id = await dispatcher.submit_task(task)
            high_tasks.append(task_id)
            print(f"   High priority task {i}: {task_id[:8]}")
        
        # Submit low priority tasks (should get 20% of resources)
        low_tasks = []
        for i in range(2):  # Submit 2 low priority tasks
            task = low_priority_task(
                background_data_sync,
                "data_type",
                100 * i
            )
            task_id = await dispatcher.submit_task(task)
            low_tasks.append(task_id)
            print(f"   Low priority task {i}: {task_id[:8]}")
        
        print("\n2. Resource allocation status:")
        status = dispatcher.get_queue_status()
        print(f"   Running tasks: {status['running_tasks']}")
        print(f"   High priority running: {status['high_priority_running']}")
        print(f"   Low priority running: {status['low_priority_running']}")
        print(f"   Available capacity: {status['capacity']['available']}")
        print(f"   High priority capacity: {status['capacity']['high_priority_available']}")
        
        # Wait for some tasks to complete
        print("\n3. Waiting for task completion...")
        await asyncio.sleep(10)
        
        # Show performance stats
        stats = dispatcher.get_performance_stats()
        print(f"\n4. Performance statistics:")
        print(f"   Tasks completed: {stats['tasks_completed']}")
        print(f"   Success rate: {stats['success_rate']:.2%}")
        print(f"   Average execution time: {stats['average_execution_time']:.2f}s")
        
    finally:
        await dispatcher.stop()


async def demonstrate_task_builder():
    """Demonstrate task builder pattern."""
    print("\n=== Task Builder Pattern ===\n")
    
    scheduler = get_scheduler()
    await scheduler.start()
    
    try:
        print("1. Creating tasks with builder pattern:")
        
        # Create a complex task using builder
        task = (TaskBuilder(user_api_request, Priority.HIGH)
                 .with_args("user789", {"action": "complex_operation"})
                 .with_timeout(30.0)
                 .with_retries(3, 2.0)
                 .with_resource_weight(2.0)
                 .with_metadata({"category": "critical", "department": "sales"})
                 .with_user("user789")
                 .on_success(lambda task: print(f"   ✅ Success callback: {task.task_id[:8]}"))
                 .on_failure(lambda task, error: print(f"   ❌ Failure callback: {task.task_id[:8]}: {error}"))
                 .build())
        
        task_id = await scheduler.submit_user_request(task.func, *task.args, timeout=task.timeout)
        print(f"   Complex task submitted: {task_id[:8]}")
        
        # Create a background task with builder
        bg_task = (TaskBuilder(background_data_sync, Priority.LOW)
                   .with_args("inventory", 5000)
                   .with_timeout(60.0)
                   .with_retries(5, 5.0)
                   .with_metadata({"category": "maintenance", "system": "inventory"})
                   .build())
        
        bg_task_id = await scheduler.submit_background_task(bg_task.func, *bg_task.args)
        print(f"   Background task submitted: {bg_task_id[:8]}")
        
        # Wait for completion
        print("\n2. Waiting for task completion...")
        await asyncio.sleep(5)
        
    finally:
        await scheduler.stop()


async def demonstrate_global_functions():
    """Demonstrate global convenience functions."""
    print("\n=== Global Functions ===\n")
    
    # Start global scheduler
    await start_scheduler()
    
    try:
        print("1. Using global submit functions:")
        
        # Submit user request globally
        task1_id = await submit_user_request(
            user_api_request,
            "global_user1",
            {"action": "global_test"}
        )
        print(f"   Global user request: {task1_id[:8]}")
        
        # Submit background task globally
        task2_id = await submit_background_task(
            background_cache_refresh,
            "global_cache"
        )
        print(f"   Global background task: {task2_id[:8]}")
        
        # Check global queue status
        print("\n2. Global queue status:")
        queue_status = get_queue_status()
        print(f"   High priority: {queue_status['high_priority']}")
        print(f"   Low priority: {queue_status['low_priority']}")
        print(f"   Total: {queue_status['total']}")
        
        # Check scheduler health
        print("\n3. Scheduler health:")
        is_healthy = is_scheduler_healthy()
        print(f"   Healthy: {is_healthy}")
        
        # Wait for completion
        print("\n4. Waiting for completion...")
        await asyncio.sleep(3)
        
    finally:
        await stop_scheduler()


async def demonstrate_monitoring():
    """Demonstrate monitoring and metrics."""
    print("\n=== Monitoring and Metrics ===\n")
    
    from qos.scheduler import SchedulerConfig
    
    config = SchedulerConfig(
        enable_monitoring=True,
        monitoring_interval=2.0,  # Monitor every 2 seconds
        on_task_completed=lambda task: print(f"   📊 Task completed: {task.task_id[:8]}"),
        on_queue_full=lambda task: print(f"   ⚠️ Queue full for task: {task.task_id[:8]}")
    )
    
    scheduler = QoSScheduler(config)
    await scheduler.start()
    
    try:
        print("1. Submitting tasks for monitoring:")
        
        # Submit a mix of tasks
        tasks = []
        
        # High priority tasks
        for i in range(3):
            task_id = await scheduler.submit_user_request(
                user_api_request,
                f"monitor_user{i}",
                {"priority": "high"}
            )
            tasks.append(task_id)
            print(f"   High priority task {i}: {task_id[:8]}")
        
        # Low priority tasks
        for i in range(5):
            task_id = await scheduler.submit_background_task(
                background_data_sync,
                f"monitor_data{i}",
                100 * i
            )
            tasks.append(task_id)
            print(f"   Low priority task {i}: {task_id[:8]}")
        
        print("\n2. Monitoring for 15 seconds...")
        await asyncio.sleep(15)
        
        # Show comprehensive status
        print("\n3. Comprehensive scheduler status:")
        status = scheduler.get_scheduler_status()
        
        print(f"   Queue sizes: {status['queue_status']['queue_stats']['queue_sizes']}")
        print(f"   Running tasks: {status['queue_status']['running_tasks']}")
        print(f"   Tasks submitted: {status['scheduler_stats']['tasks_submitted']}")
        print(f"   Success rate: {status['performance_stats']['success_rate']:.2%}")
        print(f"   Tasks per second: {status['performance_stats']['tasks_per_second']:.2f}")
        
    finally:
        await scheduler.stop()


async def demonstrate_throttling():
    """Demonstrate low priority task throttling."""
    print("\n=== Low Priority Throttling ===\n")
    
    from qos.scheduler import SchedulerConfig
    
    config = SchedulerConfig(
        low_priority_throttle_rate=0.2,  # Max 1 task every 5 seconds
        max_low_priority_delay=3.0
    )
    
    scheduler = QoSScheduler(config)
    await scheduler.start()
    
    try:
        print("1. Submitting low priority tasks (should be throttled):")
        
        start_time = time.time()
        task_times = []
        
        # Submit multiple low priority tasks quickly
        for i in range(5):
            submit_time = time.time()
            task_id = await scheduler.submit_background_task(
                background_cache_refresh,
                f"throttled_cache_{i}"
            )
            task_times.append((task_id, submit_time))
            print(f"   Task {i} submitted at {submit_time - start_time:.2f}s: {task_id[:8]}")
        
        print("\n2. Throttling analysis:")
        for i, (task_id, submit_time) in enumerate(task_times):
            if i > 0:
                prev_time = task_times[i-1][1]
                interval = submit_time - prev_time
                expected_interval = 1.0 / config.low_priority_throttle_rate
                print(f"   Task {i} interval: {interval:.2f}s (expected: {expected_interval:.2f}s)")
        
        # Wait for tasks to complete
        print("\n3. Waiting for completion...")
        await asyncio.sleep(20)
        
    finally:
        await scheduler.stop()


async def demonstrate_emergency_override():
    """Demonstrate emergency override for low priority processing."""
    print("\n=== Emergency Override ===\n")
    
    from qos.scheduler import SchedulerConfig
    
    config = SchedulerConfig(
        max_low_priority_delay=1.0,  # Very short delay
        low_priority_throttle_rate=0.1  # Very aggressive throttling
    )
    
    scheduler = QoSScheduler(config)
    await scheduler.start()
    
    try:
        print("1. Submitting high priority tasks (will block low priority):")
        
        # Submit high priority tasks to keep system busy
        high_tasks = []
        for i in range(3):
            task_id = await scheduler.submit_user_request(
                long_running_analysis,
                f"emergency_analysis_{i}"
            )
            high_tasks.append(task_id)
            print(f"   High priority task {i}: {task_id[:8]}")
        
        # Wait a bit
        await asyncio.sleep(1)
        
        print("\n2. Attempting to submit low priority task (should be rejected):")
        try:
            low_task_id = await scheduler.submit_background_task(
                background_cache_refresh,
                "emergency_cache"
            )
            print(f"   Unexpected success: {low_task_id[:8]}")
        except Exception as e:
            print(f"   Expected rejection: {e}")
        
        print("\n3. Using emergency override:")
        await scheduler.force_process_low_priority()
        
        # Now try again
        low_task_id = await scheduler.submit_background_task(
            background_cache_refresh,
            "emergency_cache_override"
        )
        print(f"   Success after override: {low_task_id[:8]}")
        
        # Wait for completion
        print("\n4. Waiting for completion...")
        await asyncio.sleep(5)
        
    finally:
        await scheduler.stop()


async def main():
    """Run all demonstrations."""
    print("QoS & Priority Queueing - Complete Demonstration")
    print("=" * 60)
    
    try:
        await demonstrate_basic_priority_handling()
        await demonstrate_qos_policies()
        await demonstrate_task_builder()
        await demonstrate_global_functions()
        await demonstrate_monitoring()
        await demonstrate_throttling()
        await demonstrate_emergency_override()
        
        print("\n" + "=" * 60)
        print("All demonstrations completed successfully!")
        print("\nKey Features Demonstrated:")
        print("✓ Priority-based task scheduling")
        print("✓ QoS resource allocation (80% HIGH, 20% LOW)")
        print("✓ User request prioritization over background tasks")
        print("✓ Low priority task throttling")
        print("✓ asyncio.PriorityQueue implementation")
        print("✓ Redis distributed queue support")
        print("✓ Task builder pattern")
        print("✓ Global convenience functions")
        print("✓ Monitoring and metrics")
        print("✓ Emergency override capabilities")
        print("✓ User experience protection")
        
    except Exception as e:
        print(f"\nDemonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
