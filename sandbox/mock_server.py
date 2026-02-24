"""
Mock FastAPI Server

This module provides a FastAPI-based mock server with configurable endpoints
for testing and development without external dependencies.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi import status
from pydantic import BaseModel

from .mock_providers import get_provider_registry
from .randomness import get_deterministic_random
from .exceptions import SandboxError, EndpointError


@dataclass
class ServerConfig:
    """Configuration for mock server."""
    host: str = "0.0.0.0"
    port: int = 8000
    enable_cors: bool = True
    enable_request_logging: bool = True
    enable_latency_injection: bool = True
    enable_error_injection: bool = True
    error_injection_rate: float = 0.05
    latency_injection_range: tuple = (0.0, 5.0)  # Seconds
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    enable_control_plane: bool = True
    enable_metrics: bool = True


@dataclass
class RequestLog:
    """Request log entry."""
    timestamp: float
    method: str
    path: str
    query_params: Dict[str, Any]
    headers: Dict[str, str]
    body_size: int
    response_status: int
    processing_time: float
    provider: str
    error: Optional[str] = None


@dataclass
class ServerMetrics:
    """Server metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    requests_per_second: float = 0.0
    error_rate: float = 0.0
    top_endpoints: Dict[str, int] = field(default_factory=dict)
    last_reset: float = field(default_factory=time.time)


class MockServer:
    """
    Mock FastAPI server for testing and development.
    
    This server provides configurable mock endpoints with realistic
    data generation and injection capabilities for testing.
    """
    
    def __init__(
        self,
        config: Optional[ServerConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize mock server.
        
        Args:
            config: Server configuration
            logger: Logger instance
        """
        self.config = config or ServerConfig()
        self.logger = logger or logging.getLogger("MockServer")
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="Mock API Server",
            description="Mock server for testing and development",
            version="1.0.0"
        )
        
        # Components
        self._provider_registry = get_provider_registry()
        self._random = get_deterministic_random()
        self._request_logs: List[RequestLog] = []
        self._metrics = ServerMetrics()
        
        # Setup middleware
        self._setup_middleware()
        self._setup_routes()
        
        self.logger.info(f"MockServer initialized on {self.config.host}:{self.config.port}")
    
    def _setup_middleware(self):
        """Setup FastAPI middleware."""
        # CORS middleware
        if self.config.enable_cors:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"]
            )
        
        # Request logging middleware
        if self.config.enable_request_logging:
            @self.app.middleware("http")
            async def log_requests(request: Request, call_next):
                start_time = time.time()
                
                response = await call_next(request)
                
                # Log request
                self._log_request(request, response, start_time)
                
                return response
        
        # Error injection middleware
        if self.config.enable_error_injection:
            @self.app.middleware("http")
            async def inject_errors(request: Request, call_next):
                # Inject errors based on rate
                if self._random.next_float() < self.config.error_injection_rate:
                    # Simulate server error
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Service temporarily unavailable"
                    )
                
                response = await call_next(request)
                return response
        
        # Latency injection middleware
        if self.config.enable_latency_injection:
            @self.app.middleware("http")
            async def inject_latency(request: Request, call_next):
                start_time = time.time()
                
                response = await call_next(request)
                
                # Add artificial latency
                latency = self._random.next_float(*self.config.latency_injection_range)
                await asyncio.sleep(latency)
                
                # Update response time
                if hasattr(response, 'headers'):
                    response.headers["x-processing-time"] = str(time.time() - start_time)
                
                return response
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        # Health check
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "timestamp": time.time(),
                "version": "1.0.0",
                "uptime": time.time() - self._metrics.last_reset,
                "metrics": self._get_metrics_summary()
            }
        
        # Control plane
        if self.config.enable_control_plane:
            self._setup_control_plane()
        
        # Mock provider endpoints
        self._setup_provider_endpoints()
        
        # Sandbox control endpoints
        self._setup_sandbox_endpoints()
        
        # Metrics endpoints
        if self.config.enable_metrics:
            self._setup_metrics_endpoints()
    
    def _setup_control_plane(self):
        """Setup control plane endpoints."""
        
        @self.app.get("/control/status")
        async def control_status():
            return {
                "server": "running",
                "config": self.config.__dict__,
                "providers": self._provider_registry.list_providers(),
                "randomness": {
                    "seed": self._random.get_state().seed,
                    "deterministic": True
                },
                "timestamp": time.time()
            }
        
        @self.app.post("/control/reset")
        async def control_reset():
            # Reset metrics
            self._metrics = ServerMetrics()
            self._request_logs.clear()
            
            # Reset randomness
            self._random = get_deterministic_random()
            
            return {"message": "Server reset completed"}
        
        @self.app.post("/control/inject_error")
        async def control_inject_error(request: Request):
            data = await request.json()
            error_rate = data.get("error_rate", 0.1)
            
            # Temporarily modify error injection rate
            old_rate = self.config.error_injection_rate
            self.config.error_injection_rate = error_rate
            
            return {
                "message": f"Error injection rate set to {error_rate}",
                "previous_rate": old_rate,
                "new_rate": error_rate
            }
    
    def _setup_provider_endpoints(self):
        """Setup mock provider endpoints."""
        
        @self.app.get("/providers")
        async def list_providers():
            return {
                "providers": self._provider_registry.list_providers(),
                "details": {
                    name: self._provider_registry.get_provider_info(name)
                    for name in self._provider_registry.list_providers()
                }
            }
        
        @self.app.get("/providers/{provider_name}")
        async def get_provider_info(provider_name: str):
            info = self._provider_registry.get_provider_info(provider_name)
            if not info:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Provider {provider_name} not found"
                )
            return info
        
        @self.app.post("/providers/{provider_name}/fetch")
        async def fetch_from_provider(
            provider_name: str,
            request: Request,
            endpoint: str = "/default"
        ):
            provider = self._provider_registry.get_provider(provider_name)
            if not provider:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Provider {provider_name} not found"
                )
            
            try:
                # Get request data
                request_data = await request.json()
                params = request_data.get("params", {})
                request_id = request_data.get("request_id", str(uuid.uuid4()))
                
                # Fetch data from provider
                response = await provider.fetch_data(
                    request_id=request_id,
                    endpoint=endpoint,
                    params=params
                )
                
                # Log the interaction
                self.logger.info(
                    f"Provider {provider_name} fetch: "
                    f"endpoint={endpoint}, "
                    f"params={params}, "
                    f"success={response.success}, "
                    f"processing_time={response.processing_time}"
                )
                
                return response
                
            except Exception as e:
                self.logger.error(f"Provider {provider_name} error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Provider {provider_name} error: {str(e)}"
                )
    
    def _setup_sandbox_endpoints(self):
        """Setup sandbox control endpoints."""
        
        @self.app.post("/sandbox/inject_fault")
        async def inject_fault(request: Request):
            data = await request.json()
            
            fault_type = data.get("type", "latency")
            provider_name = data.get("provider", "all")
            endpoint = data.get("endpoint", "all")
            
            if fault_type == "latency":
                # Inject high latency
                old_range = self.config.latency_injection_range
                self.config.latency_injection_range = (5.0, 10.0)
                
                return {
                    "message": f"Latency injection enabled: {self.config.latency_injection_range}",
                    "previous_range": old_range,
                    "affected_providers": provider_name,
                    "affected_endpoints": endpoint
                }
            
            return {"message": "Fault injection completed"}
        
        @self.app.post("/sandbox/set_seed")
        async def set_random_seed(request: Request):
            data = await request.json()
            seed = data.get("seed")
            
            # Set deterministic seed
            self._random.initialize(seed)
            
            return {
                "message": f"Random seed set to {seed}",
                "current_state": self._random.get_state()
            }
        
        @self.app.get("/sandbox/state")
        async def get_sandbox_state():
            return {
                "randomness": self._random.get_state(),
                "providers": {
                    name: provider.get_config()
                    for name, provider in self._provider_registry._providers.items()
                },
                "timestamp": time.time()
            }
    
    def _setup_metrics_endpoints(self):
        """Setup metrics endpoints."""
        
        @self.app.get("/metrics")
        async def get_metrics():
            return self._get_metrics_summary()
        
        @self.app.get("/metrics/requests")
        async def get_request_logs():
            return {
                "logs": self._request_logs[-100:],  # Last 100 requests
                "total": len(self._request_logs),
                "summary": self._get_request_summary()
            }
        
        @self.app.post("/metrics/reset")
        async def reset_metrics():
            self._metrics = ServerMetrics()
            self._request_logs.clear()
            return {"message": "Metrics reset"}
    
    def _log_request(self, request: Request, response: Response, start_time: float):
        """Log a request for metrics."""
        processing_time = time.time() - start_time
        
        # Extract provider from request
        provider = "unknown"
        if request.url.path.startswith("/providers/"):
            parts = request.url.path.split("/")
            if len(parts) >= 3:
                provider = parts[2]
        
        # Create log entry
        log_entry = RequestLog(
            timestamp=start_time,
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            headers=dict(request.headers),
            body_size=len(request.body) if request.body else 0,
            response_status=response.status_code,
            processing_time=processing_time,
            provider=provider,
            error=None
        )
        
        # Add error if present
        if response.status_code >= 400:
            log_entry.error = f"HTTP {response.status_code}"
        
        self._request_logs.append(log_entry)
        
        # Update metrics
        self._update_metrics(log_entry)
        
        # Keep only last 1000 logs
        if len(self._request_logs) > 1000:
            self._request_logs = self._request_logs[-1000:]
    
    def _update_metrics(self, log_entry: RequestLog):
        """Update server metrics."""
        self._metrics.total_requests += 1
        
        if log_entry.response_status < 400:
            self._metrics.successful_requests += 1
        else:
            self._metrics.failed_requests += 1
        
        # Update average response time
        total_processed = self._metrics.successful_requests + self._metrics.failed_requests
        if total_processed > 0:
            self._metrics.avg_response_time = (
                (self._metrics.avg_response_time * (total_processed - 1) + log_entry.processing_time)
                / total_processed
            )
        
        # Update requests per second
        current_time = time.time()
        time_window = 60.0  # 1 minute window
        recent_requests = [
            log for log in self._request_logs
            if current_time - log.timestamp <= time_window
        ]
        self._metrics.requests_per_second = len(recent_requests) / time_window
        
        # Update error rate
        self._metrics.error_rate = self._metrics.failed_requests / max(total_processed, 1)
        
        # Update top endpoints
        if log_entry.path not in self._metrics.top_endpoints:
            self._metrics.top_endpoints[log_entry.path] = 0
        self._metrics.top_endpoints[log_entry.path] += 1
    
    def _get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            "total_requests": self._metrics.total_requests,
            "successful_requests": self._metrics.successful_requests,
            "failed_requests": self._metrics.failed_requests,
            "avg_response_time": self._metrics.avg_response_time,
            "requests_per_second": self._metrics.requests_per_second,
            "error_rate": self._metrics.error_rate,
            "top_endpoints": dict(sorted(
                self._metrics.top_endpoints.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),
            "uptime": time.time() - self._metrics.last_reset
        }
    
    def _get_request_summary(self) -> Dict[str, Any]:
        """Get request logs summary."""
        if not self._request_logs:
            return {}
        
        # Count by status code
        status_counts = {}
        for log in self._request_logs:
            status = log.response_status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count by provider
        provider_counts = {}
        for log in self._request_logs:
            provider = log.provider
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
        
        # Count by endpoint
        endpoint_counts = {}
        for log in self._request_logs:
            endpoint = log.path
            endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
        
        return {
            "status_distribution": status_counts,
            "provider_distribution": provider_counts,
            "endpoint_distribution": endpoint_counts,
            "total_requests": len(self._request_logs)
        }
    
    @asynccontextmanager
    async def lifespan(self, app):
        """Manage server lifespan."""
        self.logger.info("MockServer starting up")
        self._metrics.last_reset = time.time()
        
        yield
        
        self.logger.info("MockServer shutting down")
    
    async def start(self):
        """Start the mock server."""
        import uvicorn
        
        config = uvicorn.Config(
            app=self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info"
        )
        
        self.logger.info(f"Starting mock server on {self.config.host}:{self.config.port}")
        
        server = uvicorn.Server(config)
        await server.serve()
    
    def get_app(self) -> FastAPI:
        """Get the FastAPI app instance."""
        return self.app
    
    def get_config(self) -> ServerConfig:
        """Get current configuration."""
        return self.config
    
    def get_metrics(self) -> ServerMetrics:
        """Get current metrics."""
        return self._metrics


# Global server instance
_global_server: Optional[MockServer] = None


def get_server(**kwargs) -> MockServer:
    """
    Get or create global mock server.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global MockServer instance
    """
    global _global_server
    if _global_server is None:
        _global_server = MockServer(**kwargs)
    return _global_server
