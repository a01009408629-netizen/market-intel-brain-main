"""
Production Server - LIVE_PRODUCTION Mode
13 Financial/News Data Sources Integration
8GB RAM + Mechanical HDD Optimized
"""

import asyncio
import signal
import sys
from typing import Dict, Any, List
from datetime import datetime

# Import infrastructure components
from infrastructure import (
    get_secrets_manager, get_data_factory, get_rate_limiter, 
    get_api_gateway, get_io_optimizer
)
from infrastructure.data_normalization import UnifiedInternalSchema, DataType


class ProductionServer:
    """Production server for LIVE_PRODUCTION mode."""
    
    def __init__(self):
        self.secrets_manager = get_secrets_manager()
        self.data_factory = get_data_factory()
        self.rate_limiter = get_rate_limiter()
        self.api_gateway = get_api_gateway()
        self.io_optimizer = get_io_optimizer()
        
        self._running = False
        self._providers = {}
        self._streaming_tasks = []
        
        # Production data sources
        self.production_sources = [
            "binance_ws", "binance_rest", "okx_rest", "coinbase_rest",
            "kraken_ws", "huobi_ws", "bloomberg_rest", "reuters_rest",
            "coindesk_rest", "cryptocompare_rest", "messari_rest",
            "glassnode_rest", "coinmetrics_rest"
        ]
    
    async def initialize(self):
        """Initialize production server."""
        print("🚀 Initializing Production Server - LIVE_PRODUCTION Mode")
        print("Hardware: 8GB RAM + Mechanical HDD")
        print(f"Data Sources: {len(self.production_sources)} sources")
        
        # Initialize secrets
        print("🔐 Loading encrypted secrets...")
        # Secrets are loaded automatically
        
        # Initialize data providers
        print("📊 Initializing data providers...")
        for source in self.production_sources:
            try:
                provider = self.data_factory.create_provider(source)
                self._providers[source] = provider
                print(f"   ✅ {source}")
            except Exception as e:
                print(f"   ❌ {source}: {e}")
        
        # Connect all providers
        print("🔌 Connecting to data sources...")
        connections = await self.data_factory.connect_all()
        for source, connected in connections.items():
            status = "✅" if connected else "❌"
            print(f"   {status} {source}")
        
        # Start I/O optimizer
        print("💾 Starting I/O optimizer...")
        await self.io_optimizer.start()
        
        print("✅ Production server initialized")
    
    async def start_data_collection(self):
        """Start data collection from all sources."""
        print("📡 Starting data collection...")
        
        # Start WebSocket streams
        ws_sources = ["binance_ws", "kraken_ws", "huobi_ws"]
        for source in ws_sources:
            if source in self._providers:
                provider = self._providers[source]
                if hasattr(provider, 'start_streaming'):
                    task = asyncio.create_task(
                        self._stream_data(provider, ["BTCUSDT", "ETHUSDT", "BNBUSDT"])
                    )
                    self._streaming_tasks.append(task)
                    print(f"   📡 {source} streaming started")
        
        # Start REST polling
        rest_sources = ["binance_rest", "okx_rest", "coinbase_rest", "bloomberg_rest"]
        for source in rest_sources:
            if source in self._providers:
                task = asyncio.create_task(self._poll_rest_data(source))
                self._streaming_tasks.append(task)
                print(f"   🔄 {source} polling started")
        
        print("✅ Data collection started")
    
    async def _stream_data(self, provider, symbols: List[str]):
        """Stream data from WebSocket provider."""
        async def data_callback(data_items: List[UnifiedInternalSchema]):
            for item in data_items:
                await self.io_optimizer.put_item(item)
        
        try:
            await provider.start_streaming(symbols, data_callback)
        except Exception as e:
            print(f"Streaming error: {e}")
    
    async def _poll_rest_data(self, source: str):
        """Poll data from REST provider."""
        provider = self._providers[source]
        
        while self._running:
            try:
                # Rate limited request
                success, data = await self.api_gateway.make_request(
                    source, 
                    provider.get_data, 
                    "BTCUSDT"
                )
                
                if success and data:
                    for item in data:
                        await self.io_optimizer.put_item(item)
                
                # Polling interval based on source
                if "news" in source or "bloomberg" in source:
                    await asyncio.sleep(60)  # News sources: 1 minute
                else:
                    await asyncio.sleep(5)   # Market data: 5 seconds
                    
            except Exception as e:
                print(f"Polling error for {source}: {e}")
                await asyncio.sleep(10)
    
    async def monitor_performance(self):
        """Monitor system performance."""
        while self._running:
            try:
                # Get stats
                io_stats = self.io_optimizer.get_stats()
                rate_stats = self.rate_limiter.get_all_status()
                
                # Memory usage check
                ring_utilization = io_stats["ring_buffer"]["utilization"]
                if ring_utilization > 0.9:
                    print(f"⚠️  High ring buffer utilization: {ring_utilization:.2%}")
                
                # Rate limiting check
                for endpoint, status in rate_stats.items():
                    if status["status"]["utilization"] > 0.8:
                        print(f"⚠️  High rate limit utilization: {endpoint} {status['status']['utilization']:.2%}")
                
                # Print summary every 30 seconds
                if int(asyncio.get_event_loop().time()) % 30 == 0:
                    await self._print_performance_summary(io_stats, rate_stats)
                
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                await asyncio.sleep(10)
    
    async def _print_performance_summary(self, io_stats: Dict, rate_stats: Dict):
        """Print performance summary."""
        print(f"\n📊 Performance Summary - {datetime.now().strftime('%H:%M:%S')}")
        print(f"   Ring Buffer: {io_stats['ring_buffer']['utilization']:.2%} utilization")
        print(f"   Items Processed: {io_stats['overall']['items_processed']}")
        print(f"   Items Written: {io_stats['overall']['items_written']}")
        print(f"   Drop Rate: {io_stats['overall']['drop_rate']:.2%}")
        print(f"   AOF Compression: {io_stats['aof_writer']['compression_ratio']:.2%}")
    
    async def run(self):
        """Run production server."""
        await self.initialize()
        await self.start_data_collection()
        
        self._running = True
        
        # Start monitoring
        monitor_task = asyncio.create_task(self.monitor_performance())
        
        print("\n🎯 Production Server Running - LIVE_PRODUCTION Mode")
        print("Press Ctrl+C to stop")
        
        try:
            # Keep server running
            while self._running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
        
        # Cleanup
        self._running = False
        monitor_task.cancel()
        
        for task in self._streaming_tasks:
            task.cancel()
        
        await self.io_optimizer.stop()
        await self.data_factory.disconnect_all()
        
        print("✅ Production server stopped")


async def main():
    """Main entry point."""
    # Setup signal handlers
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run production server
    server = ProductionServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
