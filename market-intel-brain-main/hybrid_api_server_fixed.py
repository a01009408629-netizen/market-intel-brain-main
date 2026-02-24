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
        
        logger.info("🎯 Hybrid API Server initialization complete!")
    
    async def _discover_adapters_hybrid(self):
        """Auto-discover adapters with hybrid mock fallback."""
        try:
            # Try to create real adapters first
            binance_adapter = await create_adapter_with_mock_routing(
                "binance", 
                self.adapter_registry,
                self.mock_router
            )
            logger.info("✅ Binance adapter initialized (with mock fallback)")
        except Exception as e:
            logger.warning(f"⚠️ Binance adapter creation failed: {e}")
    
    async def cleanup(self):
        """Clean up all resources."""
        logger.info("🧹 Cleaning up Hybrid API Server...")
        
        # Cancel background tasks
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close HTTP session
        if self.http_session:
            await self.http_session.aclose()
        
        # Stop QoS scheduler
        if self.qos_scheduler:
            await self.qos_scheduler.stop()
        
        # Close cache manager
        if self.cache_manager:
            await self.cache_manager.close()
        
        logger.info("✅ Hybrid API Server cleanup complete")

# Global state instance
hybrid_global_state = HybridGlobalState()

# Pydantic models for API
class HybridDataResponse(BaseModel):
    """Response model for hybrid data endpoint."""
    success: bool
    provider: str
    symbol: str
    data: Optional[Dict[str, Any]] = None
    cached: bool = False
    mock_used: bool = False
    timestamp: datetime
    error: Optional[str] = None

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    uptime: float
    redis_available: bool
    mock_active: bool
    components: Dict[str, Any]

# FastAPI app with lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    await hybrid_global_state.initialize()
    yield
    # Shutdown
    await hybrid_global_state.cleanup()

# Create FastAPI app
app = FastAPI(
    title="Market Intel Brain - Hybrid API",
    description="High-efficiency API server for constrained hardware",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get global state
async def get_hybrid_state() -> HybridGlobalState:
    """Get hybrid global state."""
    return hybrid_global_state

# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(state: HybridGlobalState = Depends(get_hybrid_state)):
    """Comprehensive health check for hybrid system."""
    try:
        redis_available = False
        if state.cache_manager:
            redis_available = await state.cache_manager._check_redis_availability()
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            uptime=time.time() - state._start_time,
            redis_available=redis_available,
            mock_active=True,  # Always true in hybrid mode
            components={
                "cache_manager": state.cache_manager is not None,
                "qos_scheduler": state.qos_scheduler is not None,
                "adapter_registry": state.adapter_registry is not None,
                "http_session": state.http_session is not None
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            uptime=time.time() - state._start_time,
            redis_available=False,
            mock_active=True,
            components={"error": str(e)}
        )

# Main data endpoint
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
    try:
        start_time = time.time()
        
        # Check cache first
        cache_key = f"{provider}:{symbol}"
        cached_data = None
        if state.cache_manager:
            cached_data = await state.cache_manager.get(cache_key)
        
        if cached_data:
            logger.info(f"Cache hit for {provider}:{symbol}")
            return HybridDataResponse(
                success=True,
                provider=provider,
                symbol=symbol,
                data=cached_data,
                cached=True,
                mock_used=False,
                timestamp=datetime.utcnow()
            )
        
        # Get data from adapter (with mock fallback)
        adapter = state.mock_router.get_adapter(provider)
        if not adapter:
            raise HTTPException(status_code=404, detail=f"Provider {provider} not found")
        
        # Fetch data
        data = await adapter.fetch({"symbol": symbol})
        
        # Cache the result
        if state.cache_manager and data:
            await state.cache_manager.set(cache_key, data, ttl=60)
        
        processing_time = time.time() - start_time
        logger.info(f"Data fetched for {provider}:{symbol} in {processing_time:.3f}s")
        
        return HybridDataResponse(
            success=True,
            provider=provider,
            symbol=symbol,
            data=data,
            cached=False,
            mock_used=provider == "mock",
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Data fetch failed for {provider}:{symbol}: {e}")
        return HybridDataResponse(
            success=False,
            provider=provider,
            symbol=symbol,
            error=str(e),
            cached=False,
            mock_used=False,
            timestamp=datetime.utcnow()
        )

# System status endpoint
@app.get("/api/v1/system/status", tags=["System"])
async def system_status(state: HybridGlobalState = Depends(get_hybrid_state)):
    """Get detailed system status."""
    try:
        status = {
            "uptime": time.time() - state._start_time,
            "cache_stats": state.cache_manager.get_stats() if state.cache_manager else {},
            "qos_stats": state.qos_scheduler.get_stats() if state.qos_scheduler else {},
            "adapter_count": len(state.adapter_registry._adapters) if state.adapter_registry else 0,
            "background_tasks": len(state.background_tasks),
            "mode": "HYBRID_LOW_RESOURCE"
        }
        return {"success": True, "status": status}
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
        "hybrid_api_server_fixed:app",
        host="127.0.0.1",  # Localhost only
        port=8080,
        workers=1,           # Strictly 1 worker
        access_log=False,     # No access logs to reduce I/O
        log_level="info",     # Minimal logging
        loop="asyncio",      # Use asyncio event loop
        limit_concurrency=50, # Reduced concurrency
        timeout_keep_alive=5  # Reduced keep-alive
    )
