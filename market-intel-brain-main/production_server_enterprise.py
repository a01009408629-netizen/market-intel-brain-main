"""
Production Server Integration with Enterprise Infrastructure
Enhanced production server with all enterprise components integrated
"""

import asyncio
import signal
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
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
        get_api_gateway, get_io_optimizer, get_db_manager,
        get_auth_manager, initialize_monitoring, cleanup_monitoring,
        initialize_performance, cleanup_performance,
        initialize_data_pipeline, cleanup_data_pipeline,
        enterprise_metrics, enterprise_logger, enterprise_cache,
        enterprise_load_balancer, enterprise_pipeline,
        get_postgres_session, get_redis_client,
        get_current_user, require_permission, UserRole, Permission
    )
    from infrastructure.data_normalization import UnifiedInternalSchema, DataType
    from fastapi import FastAPI, Depends, HTTPException, status
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi.security import HTTPBearer
    INFRASTRUCTURE_AVAILABLE = True
    logger.info("Enterprise infrastructure components loaded successfully")
except ImportError as e:
    logger.warning(f"Enterprise infrastructure components not available: {e}")
    INFRASTRUCTURE_AVAILABLE = False

# Import FastAPI components
try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi.security import HTTPBearer
    FASTAPI_AVAILABLE = True
    logger.info("FastAPI components loaded successfully")
except ImportError as e:
    logger.warning(f"FastAPI components not available: {e}")
    FASTAPI_AVAILABLE = False


class EnterpriseProductionServer:
    """Enterprise production server with all infrastructure components integrated."""
    
    def __init__(self):
        self.app = None
        self.secrets_manager = None
        self.data_factory = None
        self.rate_limiter = None
        self.api_gateway = None
        self.io_optimizer = None
        self.db_manager = None
        self.auth_manager = None
        self._running = False
        self._providers = {}
        self._streaming_tasks = []
        self._startup_time = datetime.now(timezone.utc)
        
        # Production data sources
        self.production_sources = [
            "binance_ws", "binance_rest", "okx_rest", "coinbase_rest",
            "kraken_ws", "huobi_ws", "bloomberg_rest", "reuters_rest",
            "coindesk_rest", "cryptocompare_rest", "messari_rest",
            "glassnode_rest", "coinmetrics_rest"
        ]
        
        # Initialize components with error handling
        self._initialize_components()
        
    def _initialize_components(self):
        """Initialize all components with comprehensive error handling."""
        try:
            # Initialize FastAPI app
            if FASTAPI_AVAILABLE:
                self.app = FastAPI(
                    title="Market Intel Brain - Enterprise Production",
                    description="Enterprise Financial Intelligence Platform with Full Infrastructure",
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
                
                # Add middleware for metrics
                if INFRASTRUCTURE_AVAILABLE:
                    from infrastructure.monitoring import MetricsMiddleware
                    self.app.middleware("http")(MetricsMiddleware(self.app, enterprise_metrics))
                
                # Add endpoints
                self._setup_endpoints()
                
                logger.info("FastAPI application initialized successfully")
            
            # Initialize infrastructure components
            if INFRASTRUCTURE_AVAILABLE:
                self._initialize_infrastructure_components()
            else:
                logger.warning("Enterprise infrastructure not available - running in minimal mode")
                
        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            raise
    
    def _initialize_infrastructure_components(self):
        """Initialize enterprise infrastructure components."""
        try:
            # Database Manager
            try:
                self.db_manager = get_db_manager()
                logger.info("Database manager initialized")
            except Exception as e:
                logger.warning(f"Database manager initialization failed: {e}")
            
            # Auth Manager
            try:
                self.auth_manager = get_auth_manager()
                logger.info("Auth manager initialized")
            except Exception as e:
                logger.warning(f"Auth manager initialization failed: {e}")
            
            # Secrets Manager
            try:
                self.secrets_manager = get_secrets_manager()
                logger.info("Secrets manager initialized")
            except Exception as e:
                logger.warning(f"Secrets manager initialization failed: {e}")
            
            # Data Factory
            try:
                self.data_factory = get_data_factory()
                logger.info("Data factory initialized")
            except Exception as e:
                logger.warning(f"Data factory initialization failed: {e}")
            
            # Rate Limiter
            try:
                self.rate_limiter = get_rate_limiter()
                logger.info("Rate limiter initialized")
            except Exception as e:
                logger.warning(f"Rate limiter initialization failed: {e}")
            
            # API Gateway
            try:
                self.api_gateway = get_api_gateway()
                logger.info("API gateway initialized")
            except Exception as e:
                logger.warning(f"API gateway initialization failed: {e}")
            
            # I/O Optimizer
            try:
                self.io_optimizer = get_io_optimizer()
                logger.info("I/O optimizer initialized")
            except Exception as e:
                logger.warning(f"I/O optimizer initialization failed: {e}")
                
        except Exception as e:
            logger.error(f"Infrastructure initialization failed: {e}")
    
    def _setup_endpoints(self):
        """Setup API endpoints."""
        
        @self.app.get("/health")
        async def health_check():
            """Comprehensive health check endpoint."""
            try:
                health_status = {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "version": "3.0.0",
                    "uptime_seconds": (datetime.now(timezone.utc) - self._startup_time).total_seconds(),
                    "components": {
                        "infrastructure": INFRASTRUCTURE_AVAILABLE,
                        "fastapi": FASTAPI_AVAILABLE,
                        "database": self.db_manager is not None,
                        "auth": self.auth_manager is not None,
                        "cache": enterprise_cache is not None,
                        "monitoring": enterprise_metrics is not None,
                        "data_pipeline": enterprise_pipeline is not None
                    },
                    "data_sources": {
                        "total": len(self.production_sources),
                        "connected": len(self._providers),
                        "streaming": len(self._streaming_tasks)
                    }
                }
                
                # Add database health if available
                if self.db_manager:
                    db_health = await self.db_manager.health_check()
                    health_status["database_health"] = db_health
                
                # Add cache stats if available
                if enterprise_cache:
                    cache_stats = enterprise_cache.get_stats()
                    health_status["cache_stats"] = cache_stats
                
                # Add pipeline stats if available
                if enterprise_pipeline:
                    pipeline_stats = enterprise_pipeline.get_stats()
                    health_status["pipeline_stats"] = pipeline_stats
                
                return JSONResponse(content=health_status)
                
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return JSONResponse(
                    content={"status": "unhealthy", "error": str(e)},
                    status_code=503
                )
        
        @self.app.get("/")
        async def root_endpoint():
            """Root endpoint with system information."""
            try:
                return JSONResponse(content={
                    "message": "Market Intel Brain - Enterprise Production Server",
                    "status": "running",
                    "timestamp": datetime.utcnow().isoformat(),
                    "version": "3.0.0",
                    "environment": os.getenv("ENVIRONMENT", "production"),
                    "uptime_seconds": (datetime.now(timezone.utc) - self._startup_time).total_seconds(),
                    "features": {
                        "enterprise_database": self.db_manager is not None,
                        "enterprise_auth": self.auth_manager is not None,
                        "enterprise_monitoring": enterprise_metrics is not None,
                        "enterprise_cache": enterprise_cache is not None,
                        "enterprise_pipeline": enterprise_pipeline is not None,
                        "data_sources_count": len(self.production_sources)
                    }
                })
            except Exception as e:
                logger.error(f"Root endpoint failed: {e}")
                return JSONResponse(
                    content={"error": "Internal server error"},
                    status_code=500
                )
        
        @self.app.get("/metrics")
        async def metrics_endpoint():
            """Prometheus metrics endpoint."""
            if not INFRASTRUCTURE_AVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Metrics not available"
                )
            
            metrics_data = enterprise_metrics.get_metrics()
            return Response(
                content=metrics_data,
                media_type="text/plain"
            )
        
        @self.app.get("/admin/stats")
        async def admin_stats(current_user = Depends(get_current_user)):
            """Admin statistics endpoint."""
            if not INFRASTRUCTURE_AVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Admin features not available"
                )
            
            # Check admin permission
            if current_user.role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )
            
            try:
                stats = {
                    "system": {
                        "uptime_seconds": (datetime.now(timezone.utc) - self._startup_time).total_seconds(),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    "data_sources": {
                        "total": len(self.production_sources),
                        "connected": len(self._providers),
                        "streaming": len(self._streaming_tasks)
                    }
                }
                
                # Add database stats
                if self.db_manager:
                    db_health = await self.db_manager.health_check()
                    stats["database"] = db_health
                
                # Add cache stats
                if enterprise_cache:
                    stats["cache"] = enterprise_cache.get_stats()
                
                # Add pipeline stats
                if enterprise_pipeline:
                    stats["data_pipeline"] = enterprise_pipeline.get_stats()
                
                # Add load balancer stats
                if enterprise_load_balancer:
                    stats["load_balancer"] = enterprise_load_balancer.get_stats()
                
                return JSONResponse(content=stats)
                
            except Exception as e:
                logger.error(f"Admin stats failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get admin stats"
                )
        
        @self.app.post("/auth/login")
        async def login(username: str, password: str):
            """Authentication endpoint."""
            if not self.auth_manager:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication not available"
                )
            
            try:
                user = await self.auth_manager.authenticate_user(username, password)
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid credentials"
                    )
                
                access_token = await self.auth_manager.create_access_token(user)
                refresh_token = await self.auth_manager.create_refresh_token(user)
                
                # Log authentication
                if self.db_manager:
                    await self.db_manager.log_audit_event(
                        user_id=user.id,
                        action="login",
                        resource="auth",
                        details={"method": "password"}
                    )
                
                return JSONResponse(content={
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "role": user.role
                    }
                })
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Login failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authentication failed"
                )
    
    async def initialize(self):
        """Initialize production server with all enterprise components."""
        try:
            logger.info("🚀 Initializing Enterprise Production Server")
            logger.info("Hardware: 8GB RAM + Mechanical HDD")
            logger.info(f"Data Sources: {len(self.production_sources)} sources")
            
            # Initialize monitoring
            if INFRASTRUCTURE_AVAILABLE:
                try:
                    await initialize_monitoring()
                    logger.info("✅ Monitoring system initialized")
                except Exception as e:
                    logger.warning(f"Monitoring initialization failed: {e}")
                
                # Initialize performance components
                try:
                    if enterprise_cache:
                        await initialize_performance(enterprise_cache.redis_pool)
                        logger.info("✅ Performance system initialized")
                except Exception as e:
                    logger.warning(f"Performance initialization failed: {e}")
                
                # Initialize data pipeline
                try:
                    await initialize_data_pipeline()
                    logger.info("✅ Data pipeline initialized")
                except Exception as e:
                    logger.warning(f"Data pipeline initialization failed: {e}")
            
            # Initialize secrets
            logger.info("🔐 Loading encrypted secrets...")
            # Secrets are loaded automatically
            
            # Initialize data providers
            if self.data_factory:
                logger.info("📊 Initializing data providers...")
                for source in self.production_sources:
                    try:
                        provider = self.data_factory.create_provider(source)
                        self._providers[source] = provider
                        logger.info(f"   ✅ {source}")
                    except Exception as e:
                        logger.warning(f"   ❌ {source}: {e}")
                
                # Connect all providers
                logger.info("🔌 Connecting to data sources...")
                connections = await self.data_factory.connect_all()
                for source, connected in connections.items():
                    status = "✅" if connected else "❌"
                    logger.info(f"   {status} {source}")
            
            # Start I/O optimizer
            if self.io_optimizer:
                logger.info("💾 Starting I/O optimizer...")
                await self.io_optimizer.start()
            
            logger.info("✅ Enterprise Production Server initialized")
            
        except Exception as e:
            logger.error(f"Production server initialization failed: {e}")
            raise
    
    async def start_data_collection(self):
        """Start data collection from all sources."""
        try:
            logger.info("📡 Starting data collection...")
            
            if not self._providers:
                logger.warning("No providers available for data collection")
                return
            
            # Start streaming for all providers
            for source, provider in self._providers.items():
                try:
                    if hasattr(provider, 'start_streaming'):
                        task = asyncio.create_task(provider.start_streaming())
                        self._streaming_tasks.append(task)
                        logger.info(f"   📡 Started streaming from {source}")
                except Exception as e:
                    logger.warning(f"Failed to start streaming from {source}: {e}")
            
            logger.info(f"✅ Data collection started from {len(self._streaming_tasks)} sources")
            
        except Exception as e:
            logger.error(f"Data collection startup failed: {e}")
            raise
    
    async def start_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the enterprise production server."""
        try:
            if not self.app:
                raise RuntimeError("FastAPI application not initialized")
            
            logger.info(f"Starting Enterprise Production Server on {host}:{port}")
            
            # Setup signal handlers
            def signal_handler(signum, frame):
                logger.info(f"Received signal {signum}, shutting down gracefully...")
                self._running = False
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Initialize server
            await self.initialize()
            
            # Start data collection
            await self.start_data_collection()
            
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
    
    async def shutdown(self):
        """Graceful shutdown of all components."""
        try:
            logger.info("🔄 Shutting down Enterprise Production Server...")
            
            # Stop data collection
            for task in self._streaming_tasks:
                task.cancel()
            
            # Cleanup infrastructure components
            if INFRASTRUCTURE_AVAILABLE:
                try:
                    await cleanup_data_pipeline()
                    logger.info("✅ Data pipeline cleaned up")
                except Exception as e:
                    logger.warning(f"Data pipeline cleanup failed: {e}")
                
                try:
                    await cleanup_performance()
                    logger.info("✅ Performance system cleaned up")
                except Exception as e:
                    logger.warning(f"Performance cleanup failed: {e}")
                
                try:
                    await cleanup_monitoring()
                    logger.info("✅ Monitoring system cleaned up")
                except Exception as e:
                    logger.warning(f"Monitoring cleanup failed: {e}")
            
            # Close database connections
            if self.db_manager:
                await self.db_manager.close()
                logger.info("✅ Database connections closed")
            
            logger.info("✅ Enterprise Production Server shutdown complete")
            
        except Exception as e:
            logger.error(f"Shutdown failed: {e}")


async def main():
    """Main entry point for enterprise production server."""
    try:
        logger.info("Starting Market Intel Brain Enterprise Production Server...")
        
        # Create and initialize server
        server = EnterpriseProductionServer()
        
        # Setup graceful shutdown
        def handle_shutdown():
            logger.info("Initiating graceful shutdown...")
            asyncio.create_task(server.shutdown())
        
        # Start server
        await server.start_server()
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
