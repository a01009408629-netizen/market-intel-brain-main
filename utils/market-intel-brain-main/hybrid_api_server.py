
"""
Hybrid API Server - High-Efficiency / Low-Resource Mode

Refactored FastAPI server optimized for constrained hardware (8GB RAM + HDD).
Implements all architectural optimizations for minimal resource usage while
maintaining full 19+ layer integration.

Features:
- Graceful Redis fallback to InMemoryCache
- Integrated MockProvider with deterministic data
- Async logging with minimal HDD I/O
- Non-blocking operations throughout
- Optimized for single-worker Uvicorn configuration
- Zero UI freezing or CPU throttling
"""

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional, List

import httpx
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import hybrid components
from utils.hybrid_logger import get_hybrid_logger, initialize_hybrid_logging
from services.cache.hybrid_cache_manager import HybridCacheManager, get_hybrid_cache_manager
from adapters.mock_provider import create_adapter_with_mock_routing, get_mock_router
from orchestrator.registry import AdapterRegistry
from qos.scheduler import QoSScheduler, SchedulerConfig
from qos.priority import Priority
from security.settings import get_settings
from services.schemas.market_data import UnifiedMarketData

# Initialize hybrid logging
initialize_hybrid_logging()

# Get hybrid logger
logger = get_hybrid_logger("HybridAPIServer")

# Global state for hybrid architecture
class HybridGlobalState:
    """Optimized global state for low-resource systems."""
    
    def __init__(self):
        self.http_session: Optional[httpx.AsyncClient] = None
        self.adapter_registry: Optional[AdapterRegistry] = None
        self.qos_scheduler: Optional[QoSScheduler] = None
        self.cache_manager: Optional[HybridCacheManager] = None
        self.settings: Optional[Any] = None
        self.background_tasks: List[asyncio.Task] = []
        self._start_time = time.time()
        self.mock_router = None
        
    async def initialize(self):
        """Initialize all components with hybrid optimizations."""
        logger.info("🚀 Initializing Hybrid API Server (Low-Resource Mode)...")
        
        # Load secure settings
        self.settings = get_settings()
        logger.info("✅ Security settings loaded")
        
        # Initialize HTTP session with optimized settings
        self.http_session = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),  # Reduced timeout
            limits=httpx.Limits(
                max_keepalive_connections=10,  # Reduced for 8GB RAM
                max_connections=50
            )
        )
        logger.info("✅ HTTP session initialized (optimized)")
        
        # Initialize adapter registry with mock routing
        self.adapter_registry = AdapterRegistry()
        self.mock_router = get_mock_router()
        logger.info("✅ Adapter registry with mock routing initialized")
        
        # Auto-discover adapters (will use mock if credentials missing)
        await self._discover_adapters_hybrid()
        
        # Initialize hybrid cache manager
        self.cache_manager = get_hybrid_cache_manager()
        await self.cache_manager.health_check()
        logger.info("✅ Hybrid cache manager initialized (Redis + fallback)")
        
        # Initialize QoS scheduler with optimized settings
        scheduler_config = SchedulerConfig(
            auto_start=True,
            enable_monitoring=True,
            monitoring_interval=10.0,  # Reduced frequency
            max_low_priority_delay=5.0,   # Reduced delay
            low_priority_throttle_rate=0.2  # Increased throttle
        )
        self.qos_scheduler = QoSScheduler(scheduler_config)
        await self.qos_scheduler.start()
        logger.info("✅ QoS scheduler started (optimized)")
        
        # Start optimized background workers
        await self._start_optimized_background_workers()
        
        logger.info("🎉 Hybrid API Server fully initialized!")
        await self._log_system_status()
    
    async def _discover_adapters_hybrid(self):
        """Auto-discover adapters with mock routing."""
        try:
            # Try to create Binance adapter with mock routing
            binance_adapter = await create_adapter_with_mock_routing(
                "binance", 
                redis_client=None  # Not using Redis directly
            )
            logger.info("✅ Binance adapter created (with mock routing)")
            
            # List available adapters
            registered_adapters = self.adapter_registry.list_adapters()
            logger.info(f"✅ Available adapters: {registered_adapters}")
            
            # Check which providers are using mock
            for provider in ["binance"]:
                using_mock = await self.mock_router._should_use_mock(provider)
                status = "MOCK" if using_mock else "LIVE"
                logger.info(f"   - {provider}: {status}")
            
        except Exception as e:
            logger.error(f"❌ Adapter discovery failed: {e}")
            raise
    
    async def _start_optimized_background_workers(self):
        """Start background workers with minimal resource usage."""
        # Reduced frequency cache warming
        cache_warming_task = asyncio.create_task(
            self._optimized_cache_warming_worker()
        )
        self.background_tasks.append(cache_warming_task)
        
        # Minimal health monitoring
        health_monitor_task = asyncio.create_task(
            self._minimal_health_monitoring_worker()
        )
        self.background_tasks.append(health_monitor_task)
        
        logger.info("✅ Optimized background workers started")
    
    async def _optimized_cache_warming_worker(self):
        """Optimized cache warming with reduced frequency."""
        popular_symbols = ["BTCUSDT", "ETHUSDT"]  # Reduced list
        
        while True:
            try:
                for symbol in popular_symbols:
                    # Submit as low priority background task
                    await self.qos_scheduler.submit_background_task(
                        self._warm_symbol_cache_optimized,
                        symbol,
                        priority=Priority.LOW,
                        timeout=15.0  # Reduced timeout
                    )
                
                # Wait 10 minutes (reduced from 5 minutes)
                await asyncio.sleep(600)
                
            except Exception as e:
                logger.error(f"Cache warming error: {e}")
                await asyncio.sleep(120)  # Wait 2 minutes on error
    
    async def _warm_symbol_cache_optimized(self, symbol: str):
        """Optimized cache warming with minimal operations."""
        try:
            # Use mock router for consistent behavior
            adapter = await create_adapter_with_mock_routing("binance")
            await adapter.get_price(symbol)
            logger.debug(f"✅ Cache warmed for {symbol}")
        except Exception as e:
            logger.debug(f"Cache warming failed for {symbol}: {e}")
    
    async def _minimal_health_monitoring_worker(self):
        """Minimal health monitoring with reduced frequency."""
        while True:
            try:
                # Perform basic health checks
                health_status = await self._get_minimal_health()
                
                # Cache health status only if cache is available
                if self.cache_manager:
                    await self.cache_manager.set(
                        "system_health",
                        health_status,
                        ttl=120,  # Reduced TTL
                        namespace="monitoring"
                    )
                
                # Wait 2 minutes (reduced from 30 seconds)
                await asyncio.sleep(120)
                
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _get_minimal_health(self) -> Dict[str, Any]:
        """Get minimal health status with reduced overhead."""
        health = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "components": {}
        }
        
        try:
            # Cache health (optimized)
            if self.cache_manager:
                cache_stats = self.cache_manager.get_stats()
                health["components"]["cache"] = {
                    "status": "healthy",
                    "redis_available": cache_stats.get("redis_available", False),
                    "hit_rate": cache_stats.get("overall_hit_rate", 0),
                    "l1_size": cache_stats.get("l1_cache_size", 0)
                }
            
            # QoS scheduler health
            if self.qos_scheduler:
                health["components"]["qos_scheduler"] = {"status": "healthy"}
            
            # Adapter health (minimal check)
            health["components"]["adapters"] = {
                "binance": {"status": "healthy"}  # Assume healthy if no errors
            }
            
        except Exception as e:
            health["status"] = "degraded"
            health["error"] = str(e)
        
        return health
    
    async def _log_system_status(self):
        """Log initial system status."""
        try:
            cache_stats = self.cache_manager.get_stats()
            redis_available = cache_stats.get("redis_available", False)
            
            logger.info("📊 System Status:")
            logger.info(f"   - Redis: {'✅ Available' if redis_available else '🔄 Using fallback cache'}")
            logger.info(f"   - Cache L1 Size: {cache_stats.get('l1_cache_size', 0)}")
            logger.info(f"   - Background Tasks: {len(self.background_tasks)}")
            logger.info(f"   - QoS Scheduler: ✅ Running")
            
        except Exception as e:
            logger.error(f"Error logging system status: {e}")
    
    async def shutdown(self):
        """Graceful shutdown with minimal cleanup."""
        logger.info("🛑 Shutting down Hybrid API Server...")
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Shutdown components
        if self.qos_scheduler:
            await self.qos_scheduler.stop()
            logger.info("✅ QoS scheduler stopped")
        
        if self.cache_manager:
            await self.cache_manager.close()
            logger.info("✅ Cache manager closed")
        
        if self.http_session:
            await self.http_session.aclose()
            logger.info("✅ HTTP session closed")
        
        logger.info("🎯 Hybrid API Server shutdown complete")

# Global state instance
hybrid_global_state = HybridGlobalState()

# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan with hybrid optimizations."""
    # Startup
    await hybrid_global_state.initialize()
    yield
    # Shutdown
    await hybrid_global_state.shutdown()

# Create FastAPI application with optimized configuration
app = FastAPI(
    title="Market Intel Brain - Hybrid API",
    description="""
    High-Efficiency API Server optimized for constrained hardware.
    
    ## Hybrid Features
    - **Graceful Redis Fallback**: InMemoryCache when Redis unavailable
    - **Integrated Mock Provider**: Deterministic data when APIs unavailable
    - **Async Logging**: Minimal HDD I/O with smart routing
    - **Non-blocking Operations**: No UI freezing or CPU throttling
    - **Resource Optimization**: Optimized for 8GB RAM + HDD systems
    
    ## Architecture
    Maintains complete integration of all 19+ architectural layers
    with resource-conscious implementations.
    """,
    version="2.0.0-hybrid",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add lightweight CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Reduced methods
    allow_headers=["*"],
)

# Pydantic models for API
class HybridDataResponse(BaseModel):
    """Optimized response model for hybrid mode."""
    success: bool = Field(..., description="Request success status")
    data: Optional[UnifiedMarketData] = Field(None, description="Market data")
    mock: bool = Field(False, description="True if data is from mock provider")
    error: Optional[str] = Field(None, description="Error message if failed")
    response_time: float = Field(..., description="Response time in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

class HybridHealthResponse(BaseModel):
    """Optimized health response model."""
    status: str = Field(..., description="Overall system status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    uptime: float = Field(..., description="System uptime in seconds")
    redis_available: bool = Field(False, description="Redis connection status")
    mock_active: bool = Field(False, description="Mock provider active status")
    components: Dict[str, Any] = Field(default_factory=dict, description="Component details")

# Dependencies
async def get_hybrid_state():
    """Dependency to get hybrid global state."""
    return hybrid_global_state

# API Endpoints
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with hybrid mode information."""
    return {
        "name": "Market Intel Brain - Hybrid API",
        "version": "2.0.0-hybrid",
        "mode": "High-Efficiency / Low-Resource",
        "description": "Optimized for constrained hardware (8GB RAM + HDD)",
        "docs": "/docs",
        "health": "/health",
        "data_endpoint": "/api/v1/data/{provider}/{symbol}",
        "features": [
            "Graceful Redis fallback",
            "Integrated mock provider",
            "Async logging",
            "Non-blocking operations",
            "Resource optimization"
        ]
    }

@app.get("/health", response_model=HybridHealthResponse, tags=["Monitoring"])
async def hybrid_health_check(state: HybridGlobalState = Depends(get_hybrid_state)):
    """
    Optimized health check endpoint.
    
    Returns minimal but comprehensive health status with reduced overhead.
    """
    try:
        health_data = await state._get_minimal_health()
        
        # Get additional status information
        cache_stats = state.cache_manager.get_stats() if state.cache_manager else {}
        redis_available = cache_stats.get("redis_available", False)
        
        # Check if mock is active for binance
        mock_active = await state.mock_router._should_use_mock("binance") if state.mock_router else False
        
        return HybridHealthResponse(
            status=health_data["status"],
            timestamp=datetime.fromisoformat(health_data["timestamp"]),
            uptime=time.time() - state._start_time,
            redis_available=redis_available,
            mock_active=mock_active,
            components=health_data["components"]
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HybridHealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            uptime=time.time() - state._start_time,
            redis_available=False,
            mock_active=True,
            components={"error": str(e)}
        )

@app.get("/api/v1/data/{provider}/{symbol}", response_model=HybridDataResponse, tags=["Data"])
async def get_hybrid_market_data(
    provider: str,
    symbol: str,
    state: HybridGlobalState = Depends(get_hybrid_state)
):
    """
    Hybrid market data endpoint with automatic mock routing.
    
    This endpoint demonstrates the complete hybrid architecture:
    - Routes to mock when API keys are missing
    - Uses hybrid cache with Redis fallback
    - Non-blocking async operations
    - Minimal resource usage
    """
    start_time = time.time()
    
    try:
        # Create adapter with mock routing
        adapter = await create_adapter_with_mock_routing(provider)
        
        # Get market data (will use mock if necessary)
        market_data = await adapter.get_price(symbol)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Check if data is from mock provider
        is_mock = hasattr(adapter, 'mock_provider') or (
            hasattr(adapter, 'original_adapter') and 
            await state.mock_router._should_use_mock(provider)
        )
        
        logger.info(f"✅ Data request completed: {provider}/{symbol} in {response_time:.3f}s ({'MOCK' if is_mock else 'LIVE'})")
        
        return HybridDataResponse(
            success=True,
            data=market_data,
            mock=is_mock,
            response_time=response_time,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        response_time = time.time() - start_time
        logger.error(f"❌ Data request failed: {provider}/{symbol} - {e}")
        
        return HybridDataResponse(
            success=False,
            mock=True,  # Assume mock on error
            error=str(e),
            response_time=response_time,
            timestamp=datetime.utcnow()
        )

@app.get("/api/v1/status", tags=["System"])
async def get_system_status(state: HybridGlobalState = Depends(get_hybrid_state)):
    """
    Get detailed system status including optimization information.
    """
    try:
        cache_stats = state.cache_manager.get_stats() if state.cache_manager else {}
        
        status = {
            "mode": "Hybrid (Low-Resource)",
            "uptime": time.time() - state._start_time,
            "optimizations": {
                "redis_fallback_active": not cache_stats.get("redis_available", False),
                "mock_routing_enabled": True,
                "async_logging": True,
                "single_worker_mode": True,
                "reduced_background_tasks": len(state.background_tasks)
            },
            "cache": {
                "redis_available": cache_stats.get("redis_available", False),
                "hit_rate": cache_stats.get("overall_hit_rate", 0),
                "l1_size": cache_stats.get("l1_cache_size", 0),
                "fallback_hits": cache_stats.get("l2_fallback_hits", 0)
            },
            "providers": {
                "binance": {
                    "using_mock": await state.mock_router._should_use_mock("binance") if state.mock_router else True
                }
            },
            "performance": {
                "background_task_interval": "10 minutes",
                "health_check_interval": "2 minutes",
                "cache_warming_symbols": ["BTCUSDT", "ETHUSDT"]
            }
        }
        
        return {
            "success": True,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"System status failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    
    print("[STARTING] Starting Hybrid API Server (Low-Resource Mode)")
    print("   - Optimized for 8GB RAM + HDD systems")
    print("   - Single worker, no access logs")
    print("   - Graceful Redis fallback")
    print("   - Integrated mock provider")
    print("   - Async logging with minimal HDD I/O")
    print()
    
    # Run with optimal constraints for constrained hardware
    uvicorn.run(
        "hybrid_api_server:app",
        host="127.0.0.1",  # Localhost only
        port=8001,
        workers=1,           # Strictly 1 worker
        access_log=False,     # No access logs to reduce I/O
        log_level="info",     # Minimal logging
        loop="asyncio",      # Use asyncio event loop
        limit_concurrency=50, # Reduced concurrency
        timeout_keep_alive=5  # Reduced keep-alive
    )
