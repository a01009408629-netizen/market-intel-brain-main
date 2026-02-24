"""
Tiered Scheduler for TradFi & Macro Data
High-freq stocks: 1 minute, Low-freq macro: 24 hours
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum

from tradfi_providers import get_tradfi_provider_factory, TradFiBaseProvider
from parquet_storage import get_parquet_storage
from infrastructure.data_normalization import UnifiedInternalSchema


class ScheduleFrequency(Enum):
    """Scheduling frequency levels."""
    HIGH_FREQ = "high"      # 1 minute
    MEDIUM_FREQ = "medium"  # 15 minutes
    LOW_FREQ = "low"        # 1 hour
    DAILY_FREQ = "daily"    # 24 hours


@dataclass
class ScheduledTask:
    """Scheduled task configuration."""
    name: str
    provider: TradFiBaseProvider
    frequency: ScheduleFrequency
    symbols: List[str]
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True
    retry_count: int = 0
    max_retries: int = 3
    success_count: int = 0
    error_count: int = 0


class TieredScheduler:
    """Tiered scheduler for different data frequencies."""
    
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.scheduler_task: Optional[asyncio.Task] = None
        
        # Frequency intervals in seconds
        self.intervals = {
            ScheduleFrequency.HIGH_FREQ: 60,      # 1 minute
            ScheduleFrequency.MEDIUM_FREQ: 900,    # 15 minutes
            ScheduleFrequency.LOW_FREQ: 3600,      # 1 hour
            ScheduleFrequency.DAILY_FREQ: 86400    # 24 hours
        }
        
        # Initialize providers and storage
        self.provider_factory = get_tradfi_provider_factory()
        self.storage = get_parquet_storage()
        
        # Default task configurations
        self.default_tasks = {
            # High-frequency stock data (1 minute)
            "yahoo_finance_stocks": {
                "provider": "yahoo_finance",
                "frequency": ScheduleFrequency.HIGH_FREQ,
                "symbols": ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "BRK-B", "JPM", "V"]
            },
            
            # Medium-frequency forex data (15 minutes)
            "forex_data": {
                "provider": "yahoo_finance",  # Yahoo also has forex
                "frequency": ScheduleFrequency.MEDIUM_FREQ,
                "symbols": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X"]
            },
            
            # Low-frequency macro data (1 hour)
            "fred_gdp": {
                "provider": "fred",
                "frequency": ScheduleFrequency.LOW_FREQ,
                "symbols": ["GDP", "UNRATE", "CPIAUCSL", "FEDFUNDS"]
            },
            
            "econdb_indicators": {
                "provider": "econdb",
                "frequency": ScheduleFrequency.LOW_FREQ,
                "symbols": ["GDP", "CPI", "UNEMPLOYMENT", "INFLATION"]
            },
            
            "eurostat_data": {
                "provider": "eurostat",
                "frequency": ScheduleFrequency.LOW_FREQ,
                "symbols": ["namq_10_gdp", "sts_inpp_m", "irt_lt_cbby_m"]
            },
            
            "imf_data": {
                "provider": "imf",
                "frequency": ScheduleFrequency.LOW_FREQ,
                "symbols": ["GDP", "CPI", "UNEMPLOYMENT"]
            },
            
            # Daily news data (24 hours)
            "google_news": {
                "provider": "google_news",
                "frequency": ScheduleFrequency.DAILY_FREQ,
                "symbols": ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
            },
            
            "rss_news": {
                "provider": "rss_news",
                "frequency": ScheduleFrequency.DAILY_FREQ,
                "symbols": []  # All news
            }
        }
    
    async def start(self):
        """Start the scheduler."""
        if self.running:
            return
        
        print("Starting Tiered Scheduler...")
        
        # Initialize storage
        await self.storage.start()
        
        # Create default tasks
        await self._create_default_tasks()
        
        # Start scheduler loop
        self.running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        print(f"Tiered Scheduler started with {len(self.tasks)} tasks")
        self._print_schedule()
    
    async def stop(self):
        """Stop the scheduler."""
        if not self.running:
            return
        
        print("Stopping Tiered Scheduler...")
        self.running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect all providers
        for task in self.tasks.values():
            try:
                await task.provider.disconnect()
            except Exception as e:
                print(f"Error disconnecting {task.name}: {e}")
        
        # Stop storage
        await self.storage.stop()
        
        print("Tiered Scheduler stopped")
    
    async def _create_default_tasks(self):
        """Create default scheduled tasks."""
        for task_name, config in self.default_tasks.items():
            try:
                # Create provider
                provider = self.provider_factory.create_provider(config["provider"])
                
                # Connect provider
                connected = await provider.connect()
                if not connected:
                    print(f"Failed to connect provider for {task_name}")
                    continue
                
                # Create task
                task = ScheduledTask(
                    name=task_name,
                    provider=provider,
                    frequency=config["frequency"],
                    symbols=config["symbols"],
                    next_run=datetime.now(timezone.utc)
                )
                
                self.tasks[task_name] = task
                print(f"Created task: {task_name} ({config['frequency'].value})")
                
            except Exception as e:
                print(f"Error creating task {task_name}: {e}")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.running:
            try:
                current_time = datetime.now(timezone.utc)
                
                # Check each task
                for task_name, task in self.tasks.items():
                    if not task.enabled:
                        continue
                    
                    # Check if it's time to run
                    if current_time >= task.next_run:
                        await self._execute_task(task)
                
                # Sleep for a short interval
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                print(f"Scheduler loop error: {e}")
                await asyncio.sleep(30)
    
    async def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task."""
        print(f"Executing task: {task.name}")
        
        try:
            start_time = time.time()
            
            # Fetch data for all symbols
            all_data = []
            for symbol in task.symbols:
                try:
                    data = await task.provider.get_data(symbol)
                    all_data.extend(data)
                    
                    # Small delay between symbols to avoid rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    print(f"Error fetching {symbol} from {task.name}: {e}")
                    task.error_count += 1
            
            # Store data
            if all_data:
                stored_count = await self.storage.store_items(all_data)
                print(f"Stored {stored_count} items from {task.name}")
            
            # Update task status
            task.last_run = datetime.now(timezone.utc)
            task.next_run = task.last_run + timedelta(seconds=self.intervals[task.frequency])
            task.success_count += 1
            task.retry_count = 0
            
            execution_time = time.time() - start_time
            print(f"Task {task.name} completed in {execution_time:.2f}s")
            
        except Exception as e:
            print(f"Task {task.name} failed: {e}")
            task.error_count += 1
            task.retry_count += 1
            
            # Disable task after max retries
            if task.retry_count >= task.max_retries:
                task.enabled = False
                print(f"Task {task.name} disabled after {task.max_retries} retries")
            else:
                # Schedule retry with exponential backoff
                retry_delay = min(300, 60 * (2 ** task.retry_count))  # Max 5 minutes
                task.next_run = datetime.now(timezone.utc) + timedelta(seconds=retry_delay)
                print(f"Task {task.name} will retry in {retry_delay}s")
    
    def _print_schedule(self):
        """Print current schedule."""
        print("\nCurrent Schedule:")
        print("=" * 60)
        
        for task_name, task in self.tasks.items():
            status = "ENABLED" if task.enabled else "DISABLED"
            next_run = task.next_run.strftime("%H:%M:%S") if task.next_run else "N/A"
            
            print(f"{task_name:25} | {task.frequency.value:8} | {status:8} | {next_run}")
        
        print("=" * 60)
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        stats = {
            'total_tasks': len(self.tasks),
            'enabled_tasks': sum(1 for t in self.tasks.values() if t.enabled),
            'disabled_tasks': sum(1 for t in self.tasks.values() if not t.enabled),
            'tasks': {}
        }
        
        for task_name, task in self.tasks.items():
            stats['tasks'][task_name] = {
                'frequency': task.frequency.value,
                'enabled': task.enabled,
                'success_count': task.success_count,
                'error_count': task.error_count,
                'retry_count': task.retry_count,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'next_run': task.next_run.isoformat() if task.next_run else None,
                'symbols_count': len(task.symbols)
            }
        
        return stats
    
    async def add_task(self, name: str, provider_name: str, frequency: ScheduleFrequency, 
                     symbols: List[str]) -> bool:
        """Add a new task."""
        try:
            # Create provider
            provider = self.provider_factory.create_provider(provider_name)
            await provider.connect()
            
            # Create task
            task = ScheduledTask(
                name=name,
                provider=provider,
                frequency=frequency,
                symbols=symbols,
                next_run=datetime.now(timezone.utc)
            )
            
            self.tasks[name] = task
            print(f"Added task: {name}")
            return True
            
        except Exception as e:
            print(f"Error adding task {name}: {e}")
            return False
    
    async def remove_task(self, name: str) -> bool:
        """Remove a task."""
        if name not in self.tasks:
            return False
        
        task = self.tasks[name]
        
        try:
            await task.provider.disconnect()
            del self.tasks[name]
            print(f"Removed task: {name}")
            return True
            
        except Exception as e:
            print(f"Error removing task {name}: {e}")
            return False
    
    async def enable_task(self, name: str) -> bool:
        """Enable a task."""
        if name not in self.tasks:
            return False
        
        self.tasks[name].enabled = True
        self.tasks[name].next_run = datetime.now(timezone.utc)
        print(f"Enabled task: {name}")
        return True
    
    async def disable_task(self, name: str) -> bool:
        """Disable a task."""
        if name not in self.tasks:
            return False
        
        self.tasks[name].enabled = False
        print(f"Disabled task: {name}")
        return True


# Global scheduler instance
_tiered_scheduler: Optional[TieredScheduler] = None


def get_tiered_scheduler() -> TieredScheduler:
    """Get global tiered scheduler instance."""
    global _tiered_scheduler
    if _tiered_scheduler is None:
        _tiered_scheduler = TieredScheduler()
    return _tiered_scheduler


async def main():
    """Test tiered scheduler."""
    print("Testing Tiered Scheduler...")
    
    # Create scheduler
    scheduler = get_tiered_scheduler()
    
    try:
        # Start scheduler
        await scheduler.start()
        
        # Run for 2 minutes for testing
        print("Running scheduler for 2 minutes...")
        await asyncio.sleep(120)
        
        # Print stats
        stats = scheduler.get_scheduler_stats()
        print(f"\nScheduler Stats:")
        print(f"Total tasks: {stats['total_tasks']}")
        print(f"Enabled tasks: {stats['enabled_tasks']}")
        print(f"Disabled tasks: {stats['disabled_tasks']}")
        
        for task_name, task_stats in stats['tasks'].items():
            print(f"  {task_name}: {task_stats['success_count']} success, {task_stats['error_count']} errors")
        
    finally:
        # Stop scheduler
        await scheduler.stop()
    
    print("Tiered scheduler test completed!")


if __name__ == "__main__":
    asyncio.run(main())
