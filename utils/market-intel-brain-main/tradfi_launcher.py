"""
TradFi & Macro Economics Production Launcher
Complete system with Tiered Scheduler and Parquet Storage
"""

import asyncio
import signal
import sys
import time
import json
from typing import Dict, Any
from datetime import datetime, timezone

# Import TradFi components
from tiered_scheduler import get_tiered_scheduler, ScheduleFrequency
from parquet_storage import get_parquet_storage
from tradfi_providers import get_tradfi_provider_factory
from infrastructure.secrets_manager import get_secrets_manager


class TradFiLauncher:
    """Complete TradFi & Macro Economics launcher."""
    
    def __init__(self):
        self.scheduler = get_tiered_scheduler()
        self.storage = get_parquet_storage()
        self.provider_factory = get_tradfi_provider_factory()
        self.secrets_manager = get_secrets_manager()
        
        self._running = False
        self._monitoring_task = None
        
        # Performance metrics
        self._metrics = {
            "start_time": None,
            "total_items_stored": 0,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "errors": [],
            "warnings": []
        }
    
    async def initialize(self):
        """Initialize TradFi system."""
        print("=" * 80)
        print("TRADFI & MACRO ECONOMICS LAUNCHER")
        print("=" * 80)
        print("System Architecture:")
        print("- Async Polling (No WebSockets)")
        print("- Tiered Scheduler (1min to 24h)")
        print("- Parquet Storage with 512MB Buffer")
        print("- Circuit Breaker & Adaptive Jitter")
        print("=" * 80)
        
        start_time = time.time()
        
        # Step 1: Initialize secrets
        print("Step 1: Initializing secrets manager...")
        try:
            # Test key availability
            fred_key = self.secrets_manager.get_secret("FRED_API_KEY")
            if fred_key:
                print("  FRED API key found")
            else:
                print("  WARNING: FRED API key not found (using open data)")
            
        except Exception as e:
            self._metrics["errors"].append(f"Secrets init failed: {e}")
            print(f"  ERROR: {e}")
            return False
        
        # Step 2: Initialize storage
        print("Step 2: Initializing Parquet storage...")
        try:
            await self.storage.start()
            print("  Parquet storage started")
            
            # Get storage stats
            stats = self.storage.get_storage_stats()
            print(f"  Buffer size: {stats['buffer_stats']['buffer_size_mb']:.2f}MB")
            print(f"  Compression: {stats['config']['compression']}")
            
        except Exception as e:
            self._metrics["errors"].append(f"Storage init failed: {e}")
            print(f"  ERROR: {e}")
            return False
        
        # Step 3: Test providers
        print("Step 3: Testing keyless providers...")
        try:
            # Test Yahoo Finance
            yahoo_provider = self.provider_factory.create_provider("yahoo_finance")
            yahoo_connected = await yahoo_provider.connect()
            print(f"  Yahoo Finance: {'CONNECTED' if yahoo_connected else 'FAILED'}")
            
            # Test FRED
            fred_provider = self.provider_factory.create_provider("fred")
            fred_connected = await fred_provider.connect()
            print(f"  FRED: {'CONNECTED' if fred_connected else 'FAILED'}")
            
            # Test RSS News
            rss_provider = self.provider_factory.create_provider("rss_news")
            rss_connected = await rss_provider.connect()
            print(f"  RSS News: {'CONNECTED' if rss_connected else 'FAILED'}")
            
            # Test Google News (scraper)
            google_provider = self.provider_factory.create_provider("google_news")
            google_connected = await google_provider.connect()
            print(f"  Google News: {'CONNECTED' if google_connected else 'FAILED'}")
            
            # Test EconDB
            econdb_provider = self.provider_factory.create_provider("econdb")
            econdb_connected = await econdb_provider.connect()
            print(f"  EconDB: {'CONNECTED' if econdb_connected else 'FAILED'}")
            
            # Test EuroStat
            eurostat_provider = self.provider_factory.create_provider("eurostat")
            eurostat_connected = await eurostat_provider.connect()
            print(f"  EuroStat: {'CONNECTED' if eurostat_connected else 'FAILED'}")
            
            # Test IMF
            imf_provider = self.provider_factory.create_provider("imf")
            imf_connected = await imf_provider.connect()
            print(f"  IMF: {'CONNECTED' if imf_connected else 'FAILED'}")
            
            provider_count = sum([yahoo_connected, fred_connected, rss_connected, 
                               google_connected, econdb_connected, eurostat_connected, imf_connected])
            
            print(f"  Successfully connected: {provider_count}/7 providers")
            
        except Exception as e:
            self._metrics["errors"].append(f"Providers test failed: {e}")
            print(f"  ERROR: {e}")
            return False
        
        init_time = time.time() - start_time
        print(f"Step 4: Initialization complete in {init_time:.2f}s")
        
        return provider_count >= 5  # At least 5 providers should work
    
    async def start_data_collection(self):
        """Start tiered scheduler for data collection."""
        print("\nStarting Tiered Scheduler...")
        
        try:
            await self.scheduler.start()
            
            # Start monitoring
            self._monitoring_task = asyncio.create_task(self._monitor_system())
            
            print("Tiered scheduler started successfully")
            
        except Exception as e:
            self._metrics["errors"].append(f"Scheduler start failed: {e}")
            print(f"ERROR: {e}")
            return False
        
        return True
    
    async def _monitor_system(self):
        """Monitor system performance and health."""
        import psutil
        
        while self._running:
            try:
                # Get system metrics
                memory = psutil.virtual_memory()
                cpu = psutil.cpu_percent(interval=1)
                disk = psutil.disk_usage('/')
                
                # Get scheduler stats
                scheduler_stats = self.scheduler.get_scheduler_stats()
                
                # Get storage stats
                storage_stats = self.storage.get_storage_stats()
                
                # Check thresholds
                memory_usage = memory.percent
                if memory_usage > 80:
                    self._metrics["warnings"].append(f"High memory usage: {memory_usage:.1f}%")
                
                if cpu > 75:
                    self._metrics["warnings"].append(f"High CPU usage: {cpu:.1f}%")
                
                buffer_usage = storage_stats['buffer_stats']['buffer_size_mb']
                if buffer_usage > 400:  # 80% of 512MB
                    self._metrics["warnings"].append(f"High buffer usage: {buffer_usage:.1f}MB")
                
                # Print status every 60 seconds
                if int(time.time()) % 60 == 0:
                    self._print_status_summary(memory, cpu, scheduler_stats, storage_stats)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self._metrics["errors"].append(f"Monitor error: {e}")
                await asyncio.sleep(60)
    
    def _print_status_summary(self, memory, cpu, scheduler_stats, storage_stats):
        """Print comprehensive status summary."""
        print(f"\n{'='*60}")
        print(f"TRADFI STATUS - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        print(f"Memory: {memory.percent:.1f}% ({memory.used/1024/1024:.1f}MB used)")
        print(f"CPU: {cpu:.1f}%")
        print(f"Buffer: {storage_stats['buffer_stats']['buffer_size_mb']:.1f}MB")
        print(f"Tasks: {scheduler_stats['enabled_tasks']}/{scheduler_stats['total_tasks']} enabled")
        print(f"Items Stored: {self._metrics['total_items_stored']:,}")
        print(f"Success Rate: {self._get_success_rate():.1%}")
        print(f"Errors: {len(self._metrics['errors'])}")
        print(f"Warnings: {len(self._metrics['warnings'])}")
        
        # Task performance
        print("\nTask Performance:")
        for task_name, task_stats in scheduler_stats['tasks'].items():
            if task_stats['success_count'] > 0 or task_stats['error_count'] > 0:
                success_rate = task_stats['success_count'] / (task_stats['success_count'] + task_stats['error_count'])
                print(f"  {task_name:20} | {task_stats['success_count']:3} success | {task_stats['error_count']:3} errors | {success_rate:.1%}")
    
    def _get_success_rate(self) -> float:
        """Calculate overall success rate."""
        total = self._metrics['successful_requests'] + self._metrics['failed_requests']
        if total == 0:
            return 0.0
        return self._metrics['successful_requests'] / total
    
    async def run(self):
        """Run TradFi launcher."""
        # Initialize
        if not await self.initialize():
            print("Initialization failed. Exiting.")
            return False
        
        # Start data collection
        self._running = True
        self._metrics["start_time"] = time.time()
        
        if not await self.start_data_collection():
            print("Data collection start failed. Exiting.")
            return False
        
        print(f"\n{'='*80}")
        print("TRADFI SYSTEM RUNNING - LIVE_PRODUCTION MODE")
        print("Press Ctrl+C to stop gracefully")
        print(f"{'='*80}")
        
        try:
            # Keep running
            while self._running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nShutdown signal received...")
        
        return await self._shutdown()
    
    async def _shutdown(self):
        """Graceful shutdown."""
        print("Initiating graceful shutdown...")
        self._running = False
        
        # Cancel monitoring
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Stop scheduler
        await self.scheduler.stop()
        
        # Final storage flush
        await self.storage.flush_buffer()
        await self.storage.stop()
        
        # Print final summary
        self._print_final_summary()
        
        print("Graceful shutdown complete.")
        return True
    
    def _print_final_summary(self):
        """Print final execution summary."""
        if self._metrics["start_time"]:
            total_time = time.time() - self._metrics["start_time"]
            
            print(f"\n{'='*80}")
            print("FINAL EXECUTION SUMMARY")
            print(f"{'='*80}")
            print(f"Total Runtime: {total_time:.2f} seconds")
            print(f"Items Stored: {self._metrics['total_items_stored']:,}")
            print(f"Total Requests: {self._metrics['total_requests']:,}")
            print(f"Success Rate: {self._get_success_rate():.1%}")
            print(f"Errors: {len(self._metrics['errors'])}")
            print(f"Warnings: {len(self._metrics['warnings'])}")
            
            if self._metrics["errors"]:
                print("\nErrors:")
                for error in self._metrics["errors"][-10:]:  # Last 10 errors
                    print(f"  - {error}")
            
            if self._metrics["warnings"]:
                print("\nWarnings:")
                for warning in self._metrics["warnings"][-10:]:  # Last 10 warnings
                    print(f"  - {warning}")
            
            # Save summary
            summary = {
                "runtime_seconds": total_time,
                "items_stored": self._metrics["total_items_stored"],
                "total_requests": self._metrics["total_requests"],
                "success_rate": self._get_success_rate(),
                "errors": self._metrics["errors"],
                "warnings": self._metrics["warnings"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            with open("tradfi_summary.json", "w") as f:
                json.dump(summary, f, indent=2, default=str)
            
            print(f"\nSummary saved to: tradfi_summary.json")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print(f"\nReceived signal {signum}")
    sys.exit(0)


async def main():
    """Main entry point."""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run TradFi launcher
    launcher = TradFiLauncher()
    success = await launcher.run()
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
