"""
Production Server - LIVE_PRODUCTION Mode
Enterprise Financial Intelligence Platform
Optimized for 8GB RAM + Mechanical HDD
"""

import asyncio
import signal
import sys
import os
from typing import Dict, Any, List
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import infrastructure components with error handling
try:
    from infrastructure import (
        get_secrets_manager, get_data_factory, get_rate_limiter, 
        get_api_gateway, get_io_optimizer
    )
    from infrastructure.data_normalization import UnifiedInternalSchema, DataType
    INFRASTRUCTURE_AVAILABLE = True
    logger.info("Infrastructure components loaded successfully")
except ImportError as e:
    logger.warning(f"Infrastructure components not available: {e}")
    INFRASTRUCTURE_AVAILABLE = False

# Import FastAPI components
try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
    logger.info("FastAPI components loaded successfully")
except ImportError as e:
    logger.warning(f"FastAPI components not available: {e}")
    FASTAPI_AVAILABLE = False


class ProductionServer:
    """Production server for LIVE_PRODUCTION mode with enterprise-grade error handling."""
    
    def __init__(self):
        self.app = None
        self.secrets_manager = None
        self.data_factory = None
        self.rate_limiter = None
        self.api_gateway = None
        self.io_optimizer = None
        
        # Initialize components with error handling
        self._initialize_components()
        
    def _initialize_components(self):
        """Initialize all components with comprehensive error handling."""
        try:
            # Initialize FastAPI app
            if FASTAPI_AVAILABLE:
                self.app = FastAPI(
                    title="Market Intel Brain - Production",
                    description="Enterprise Financial Intelligence Platform",
                    version="3.0.0",
                    docs_url="/docs",
                    redoc_url="/redoc"
                )
                
                # Add CORS middleware
                self.app.add_middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_credentials=True,
                    allow_methods=["*"],
                    allow_headers=["*"],
                )
                
                # Add health endpoint
                self.app.get("/health")(self.health_check)
                self.app.get("/")(self.root_endpoint)
                
                logger.info("FastAPI application initialized successfully")
            
            # Initialize infrastructure components
            if INFRASTRUCTURE_AVAILABLE:
                try:
                    self.secrets_manager = get_secrets_manager()
                    logger.info("Secrets manager initialized")
                except Exception as e:
                    logger.warning(f"Secrets manager initialization failed: {e}")
                
                try:
                    self.data_factory = get_data_factory()
                    logger.info("Data factory initialized")
                except Exception as e:
                    logger.warning(f"Data factory initialization failed: {e}")
                
                try:
                    self.rate_limiter = get_rate_limiter()
                    logger.info("Rate limiter initialized")
                except Exception as e:
                    logger.warning(f"Rate limiter initialization failed: {e}")
                
                try:
                    self.api_gateway = get_api_gateway()
                    logger.info("API gateway initialized")
                except Exception as e:
                    logger.warning(f"API gateway initialization failed: {e}")
                
                try:
                    self.io_optimizer = get_io_optimizer()
                    logger.info("I/O optimizer initialized")
                except Exception as e:
                    logger.warning(f"I/O optimizer initialization failed: {e}")
            else:
                logger.warning("Infrastructure components not available - running in minimal mode")
                
        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            raise
    
    async def health_check(self):
        """Health check endpoint for monitoring."""
        try:
            health_status = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "3.0.0",
                "components": {
                    "infrastructure": INFRASTRUCTURE_AVAILABLE,
                    "fastapi": FASTAPI_AVAILABLE,
                    "secrets_manager": self.secrets_manager is not None,
                    "data_factory": self.data_factory is not None,
                    "rate_limiter": self.rate_limiter is not None,
                    "api_gateway": self.api_gateway is not None,
                    "io_optimizer": self.io_optimizer is not None
                }
            }
            return JSONResponse(content=health_status)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(
                content={"status": "unhealthy", "error": str(e)},
                status_code=503
            )
    
    async def root_endpoint(self):
        """Root endpoint with system information."""
        try:
            return JSONResponse(content={
                "message": "Market Intel Brain - Production Server",
                "status": "running",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "3.0.0",
                "environment": os.getenv("ENVIRONMENT", "production")
            })
        except Exception as e:
            logger.error(f"Root endpoint failed: {e}")
            return JSONResponse(
                content={"error": "Internal server error"},
                status_code=500
            )
    
    async def start_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the production server."""
        try:
            if not self.app:
                raise RuntimeError("FastAPI application not initialized")
            
            logger.info(f"Starting production server on {host}:{port}")
            
            # Setup signal handlers
            def signal_handler(signum, frame):
                logger.info(f"Received signal {signum}, shutting down gracefully...")
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Start server
            import uvicorn
            await uvicorn.run(
                self.app,
                host=host,
                port=port,
                log_level="info",
                access_log=True
            )
            
        except Exception as e:
            logger.error(f"Server startup failed: {e}")
            raise


async def main():
    """Main entry point for production server."""
    try:
        logger.info("Starting Market Intel Brain Production Server...")
        
        # Create and initialize server
        server = ProductionServer()
        
        # Start server
        await server.start_server()
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
        
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
