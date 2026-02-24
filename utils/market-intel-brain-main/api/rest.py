"""
MAIFA v3 REST API - Delivery Layer
FastAPI REST endpoints for external system integration
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import asyncio
import time
import logging
from datetime import datetime

# Import MAIFA components
from core.orchestrator import orchestrator
from core.governance import governance_manager
from core.context import context_manager
from services.agents.registry import agent_registry
from utils.logger import get_logger
from utils.rate_limiter import check_rate_limit

# Initialize logger
logger = get_logger("api.rest")

# Initialize FastAPI app
app = FastAPI(
    title="MAIFA v3 Financial Intelligence API",
    description="Multi-Agent Intelligence for Financial Analysis",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security
security = HTTPBearer(auto_error=False)

# Pydantic models
class AnalysisRequest(BaseModel):
    text: str = Field(..., description="Text to analyze", min_length=1, max_length=10000)
    symbol: str = Field(default="UNKNOWN", description="Financial symbol")
    agents: Optional[List[str]] = Field(default=None, description="Specific agents to run")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class AnalysisResponse(BaseModel):
    status: str
    symbol: str
    agent_results: Dict[str, Any]
    trading_signal: Optional[Dict[str, Any]]
    events_created: int
    system_metrics: Dict[str, Any]
    execution_time: float
    performance_target_met: bool
    timestamp: str

class AgentListResponse(BaseModel):
    agents: List[str]
    total_count: int
    registry_info: Dict[str, Any]

class SystemStatusResponse(BaseModel):
    orchestrator_status: Dict[str, Any]
    governance_status: Dict[str, Any]
    agent_registry_status: Dict[str, Any]
    system_metrics: Dict[str, Any]
    timestamp: str

class RateLimitResponse(BaseModel):
    allowed: bool
    remaining: int
    reset_time: float
    info: Dict[str, Any]

# Dependency functions
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from credentials"""
    # Simplified authentication - implement proper auth in production
    if credentials:
        return {"user_id": "authenticated_user", "permissions": ["read", "write"]}
    return {"user_id": "anonymous_user", "permissions": ["read"]}

async def rate_limit_check(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    """Rate limiting middleware"""
    client_ip = request.client.host
    user_id = user["user_id"]
    rate_limit_key = f"api:{user_id}:{client_ip}"
    
    allowed, info = check_rate_limit(rate_limit_key)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(info.get("config", {}).get("max_requests", 100)),
                "X-RateLimit-Remaining": str(info.get("available_tokens", 0)),
                "X-RateLimit-Reset": str(info.get("time_until_available", 0))
            }
        )
    
    return info

# API Routes
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "message": "MAIFA v3 Financial Intelligence API",
        "version": "3.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health check endpoint"""
    try:
        # Check orchestrator
        orchestrator_status = await orchestrator.get_orchestrator_status()
        
        # Check agent registry
        agent_health = await agent_registry.health_check_all()
        
        # Check governance
        governance_status = await governance_manager.get_governance_status()
        
        overall_status = "healthy"
        if not all(agent_health.values()):
            overall_status = "degraded"
        if orchestrator_status.get("status") != "running":
            overall_status = "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "components": {
                "orchestrator": orchestrator_status.get("status", "unknown"),
                "agents": agent_health,
                "governance": governance_status.get("active_rules", 0)
            }
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    rate_info: Dict[str, Any] = Depends(rate_limit_check),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Analyze text using MAIFA intelligence pipeline
    
    This endpoint processes text through the complete 5-stage MAIFA pipeline:
    1. Preprocessing - Data cleaning and validation
    2. Event Classification - Event type identification
    3. Multi-Agent Analysis - Parallel agent execution
    4. Aggregation - Result fusion and intelligence generation
    5. Final Report - Comprehensive intelligence report
    """
    try:
        start_time = time.time()
        
        logger.info(f"Analysis request from {user['user_id']} for symbol {request.symbol}")
        
        # Process through orchestrator
        result = await orchestrator.process_request(
            text=request.text,
            symbol=request.symbol,
            agent_filter=request.agents
        )
        
        execution_time = time.time() - start_time
        
        # Log performance
        logger.info(f"Analysis completed in {execution_time:.3f}s for {request.symbol}")
        
        # Add background task for cleanup if needed
        background_tasks.add_task(log_analysis_metrics, user["user_id"], request.symbol, execution_time)
        
        return AnalysisResponse(
            status=result.status.value if hasattr(result.status, 'value') else str(result.status),
            symbol=result.symbol,
            agent_results=result.agent_results,
            trading_signal=result.trading_signal.__dict__ if result.trading_signal else None,
            events_created=result.events_created,
            system_metrics=result.system_metrics,
            execution_time=result.execution_time,
            performance_target_met=result.performance_target_met,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/agents", response_model=AgentListResponse)
async def list_agents(user: Dict[str, Any] = Depends(get_current_user)):
    """List all available agents"""
    try:
        agents = await agent_registry.list_agents()
        registry_info = await agent_registry.get_registry_info()
        
        return AgentListResponse(
            agents=agents,
            total_count=len(agents),
            registry_info=registry_info
        )
    
    except Exception as e:
        logger.error(f"Agent listing failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to list agents")

@app.get("/agents/{agent_name}/stats")
async def get_agent_stats(
    agent_name: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get statistics for specific agent"""
    try:
        stats = await agent_registry.get_agent_stats(agent_name)
        
        if not stats:
            raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
        
        return {
            "agent_name": agent_name,
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent stats failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get agent stats")

@app.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status(user: Dict[str, Any] = Depends(get_current_user)):
    """Get comprehensive system status"""
    try:
        # Get status from all components
        orchestrator_status = await orchestrator.get_orchestrator_status()
        governance_status = await governance_manager.get_governance_status()
        registry_status = await agent_registry.get_registry_info()
        
        # Get system metrics
        system_metrics = {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": time.time() - getattr(orchestrator, '_start_time', time.time()),
            "total_requests": orchestrator_status.get("system_metrics", {}).get("total_requests", 0),
            "avg_response_time": orchestrator_status.get("system_metrics", {}).get("avg_response_time", 0.0),
            "active_agents": registry_status.get("total_agents", 0)
        }
        
        return SystemStatusResponse(
            orchestrator_status=orchestrator_status,
            governance_status=governance_status,
            agent_registry_status=registry_status,
            system_metrics=system_metrics,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"System status failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system status")

@app.get("/governance/rules")
async def get_governance_rules(user: Dict[str, Any] = Depends(get_current_user)):
    """Get governance rules"""
    try:
        rules = await governance_manager.get_governance_status()
        return rules
    
    except Exception as e:
        logger.error(f"Governance rules failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get governance rules")

@app.get("/rate-limit/{key}")
async def get_rate_limit_status(
    key: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get rate limit status for key"""
    try:
        from utils.rate_limiter import rate_limiter
        status = rate_limiter.get_status(key)
        return status
    
    except Exception as e:
        logger.error(f"Rate limit status failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get rate limit status")

@app.post("/admin/agents/{agent_name}/block")
async def block_agent(
    agent_name: str,
    reason: str = "Administrative action",
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Block an agent (admin only)"""
    if "admin" not in user.get("permissions", []):
        raise HTTPException(status_code=403, detail="Admin permissions required")
    
    try:
        await governance_manager.block_agent(agent_name, reason)
        return {"message": f"Agent {agent_name} blocked", "reason": reason}
    
    except Exception as e:
        logger.error(f"Agent blocking failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to block agent")

@app.post("/admin/agents/{agent_name}/unblock")
async def unblock_agent(
    agent_name: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Unblock an agent (admin only)"""
    if "admin" not in user.get("permissions", []):
        raise HTTPException(status_code=403, detail="Admin permissions required")
    
    try:
        await governance_manager.unblock_agent(agent_name)
        return {"message": f"Agent {agent_name} unblocked"}
    
    except Exception as e:
        logger.error(f"Agent unblocking failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to unblock agent")

@app.get("/metrics")
async def get_metrics(user: Dict[str, Any] = Depends(get_current_user)):
    """Get system metrics"""
    try:
        # Get metrics from various components
        orchestrator_metrics = await orchestrator.get_orchestrator_status()
        agent_metrics = await agent_registry.get_registry_info()
        governance_metrics = await governance_manager.get_governance_status()
        
        return {
            "orchestrator": orchestrator_metrics.get("system_metrics", {}),
            "agents": {
                "total": agent_metrics.get("total_agents", 0),
                "modern": agent_metrics.get("modern_agents", 0),
                "legacy": agent_metrics.get("legacy_agents", 0)
            },
            "governance": {
                "active_rules": governance_metrics.get("active_rules", 0),
                "blocked_agents": len(governance_metrics.get("blocked_agents", [])),
                "blocked_ips": len(governance_metrics.get("blocked_ips", []))
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Metrics failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")

# Background tasks
async def log_analysis_metrics(user_id: str, symbol: str, execution_time: float):
    """Log analysis metrics in background"""
    try:
        # This could be sent to a monitoring system
        logger.info(f"Analysis metrics - User: {user_id}, Symbol: {symbol}, Time: {execution_time:.3f}s")
    except Exception as e:
        logger.error(f"Metrics logging failed: {e}")

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": datetime.now().isoformat()
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "timestamp": datetime.now().isoformat()
            }
        }
    )

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize API on startup"""
    logger.info("Starting MAIFA v3 REST API...")
    
    try:
        # Initialize orchestrator
        await orchestrator.initialize()
        
        # Start rate limiter cleanup
        from utils.rate_limiter import rate_limiter
        rate_limiter.start_background_cleanup()
        
        logger.info("MAIFA v3 REST API started successfully")
        
    except Exception as e:
        logger.error(f"API startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down MAIFA v3 REST API...")
    
    try:
        # Stop rate limiter cleanup
        from utils.rate_limiter import rate_limiter
        rate_limiter.stop_background_cleanup()
        
        logger.info("MAIFA v3 REST API shutdown complete")
        
    except Exception as e:
        logger.error(f"API shutdown failed: {e}")

# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests"""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} in {process_time:.3f}s")
    
    # Add custom headers
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-API-Version"] = "3.0.0"
    
    return response

# Add rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting"""
    # Skip rate limiting for health checks and docs
    if request.url.path in ["/health", "/docs", "/redoc", "/"]:
        return await call_next(request)
    
    # Get client identifier
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")
    rate_limit_key = f"global:{client_ip}:{hash(user_agent) % 1000}"
    
    # Check rate limit
    from utils.rate_limiter import check_rate_limit
    allowed, info = check_rate_limit(rate_limit_key)
    
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": 429,
                    "message": "Rate limit exceeded",
                    "retry_after": info.get("time_until_available", 60)
                }
            },
            headers={
                "Retry-After": str(int(info.get("time_until_available", 60)))
            }
        )
    
    return await call_next(request)

if __name__ == "__main__":
    import uvicorn
    
    # Run the API server
    uvicorn.run(
        "api.rest:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
