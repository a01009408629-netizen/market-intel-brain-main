from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, Union
import asyncio
import logging
import httpx
import random
from datetime import datetime
from pydantic import BaseModel


class RequestMetrics:
    """Metrics collection for HTTP requests"""
    
    def __init__(self):
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        self.status_codes: Dict[int, int] = {}
    
    def record_request(self, status_code: int, response_time: float) -> None:
        """Record a request"""
        self.request_count += 1
        self.total_response_time += response_time
        
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
        
        if 200 <= status_code < 300:
            self.success_count += 1
        else:
            self.error_count += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get request metrics"""
        avg_response_time = self.total_response_time / self.request_count if self.request_count > 0 else 0
        success_rate = self.success_count / self.request_count if self.request_count > 0 else 0
        
        return {
            "request_count": self.request_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": success_rate,
            "average_response_time": avg_response_time,
            "status_codes": self.status_codes
        }


class UserAgentRotator:
    """Rotates User-Agent headers to avoid detection"""
    
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/121.0.0.0"
        ]
    
    def get_random_user_agent(self) -> str:
        """Get a random User-Agent"""
        return random.choice(self.user_agents)


class BaseSourceAdapter(ABC):
    """Abstract base class for all source adapters"""
    
    def __init__(
        self,
        provider_name: str,
        base_url: str,
        timeout: float = 30.0,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        logger: Optional[logging.Logger] = None
    ):
        self.provider_name = provider_name
        self.base_url = base_url
        self.timeout = timeout
        self.logger = logger or logging.getLogger(f"Adapter.{provider_name}")
        
        # HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(
                max_keepalive_connections=max_keepalive_connections,
                max_connections=max_connections
            )
        )
        
        # User agent rotator for fingerprint safety
        self.user_agent_rotator = UserAgentRotator()
        
        # Metrics collection
        self.metrics = RequestMetrics()
        
        # Lifecycle hooks
        self.on_request_start: Optional[Callable] = None
        self.on_request_success: Optional[Callable] = None
        self.on_request_error: Optional[Callable] = None
    
    @abstractmethod
    async def fetch(self, params: BaseModel) -> Dict[str, Any]:
        """Main fetch method to be implemented by concrete adapters"""
        pass
    
    @abstractmethod
    async def validate_params(self, params: BaseModel) -> bool:
        """Validate request parameters"""
        pass
    
    @abstractmethod
    async def normalize_response(self, raw_data: Any) -> Dict[str, Any]:
        """Normalize response data to standard format"""
        pass
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[str, Dict[str, Any]]] = None,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with connection pooling and fingerprint-safe headers"""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        # Prepare headers with rotating User-Agent for fingerprint safety
        request_headers = {
            "User-Agent": self.user_agent_rotator.get_random_user_agent(),
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site"
        }
        
        if headers:
            request_headers.update(headers)
        
        start_time = asyncio.get_event_loop().time()
        request_id = f"{self.provider_name}_{datetime.utcnow().timestamp()}"
        
        # Lifecycle hook: on_request_start
        if self.on_request_start:
            await self._call_lifecycle_hook(
                self.on_request_start,
                request_id=request_id,
                method=method,
                url=url,
                headers={k: v for k, v in request_headers.items() if k.lower() != "user-agent"},
                params=params
            )
        
        self.logger.info(f"[REQUEST_START] {method} {url}", extra={
            "request_id": request_id,
            "provider": self.provider_name,
            "method": method,
            "url": url,
            "params": params
        })
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                params=params,
                headers=request_headers,
                data=data,
                **kwargs
            )
            
            response_time = asyncio.get_event_loop().time() - start_time
            self.metrics.record_request(response.status_code, response_time)
            
            # Lifecycle hook: on_request_success
            if self.on_request_success:
                await self._call_lifecycle_hook(
                    self.on_request_success,
                    request_id=request_id,
                    response=response,
                    response_time=response_time
                )
            
            self.logger.info(f"[REQUEST_SUCCESS] {method} {url} - {response.status_code} ({response_time:.3f}s)", extra={
                "request_id": request_id,
                "provider": self.provider_name,
                "method": method,
                "url": url,
                "status_code": response.status_code,
                "response_time": response_time
            })
            
            return response
        
        except httpx.TimeoutException as e:
            response_time = asyncio.get_event_loop().time() - start_time
            self.metrics.record_request(0, response_time)  # 0 for timeout
            
            # Lifecycle hook: on_request_error
            if self.on_request_error:
                await self._call_lifecycle_hook(
                    self.on_request_error,
                    request_id=request_id,
                    error_type="timeout",
                    error_message=str(e),
                    response_time=response_time
                )
            
            self.logger.error(f"[REQUEST_TIMEOUT] {method} {url} ({response_time:.3f}s)", extra={
                "request_id": request_id,
                "provider": self.provider_name,
                "method": method,
                "url": url,
                "timeout": self.timeout,
                "response_time": response_time
            })
            
            raise
        
        except httpx.NetworkError as e:
            response_time = asyncio.get_event_loop().time() - start_time
            self.metrics.record_request(0, response_time)  # 0 for network error
            
            # Lifecycle hook: on_request_error
            if self.on_request_error:
                await self._call_lifecycle_hook(
                    self.on_request_error,
                    request_id=request_id,
                    error_type="network",
                    error_message=str(e),
                    response_time=response_time
                )
            
            self.logger.error(f"[REQUEST_NETWORK_ERROR] {method} {url}: {e}", extra={
                "request_id": request_id,
                "provider": self.provider_name,
                "method": method,
                "url": url,
                "error": str(e),
                "response_time": response_time
            })
            
            raise
        
        except Exception as e:
            response_time = asyncio.get_event_loop().time() - start_time
            self.metrics.record_request(0, response_time)  # 0 for other errors
            
            # Lifecycle hook: on_request_error
            if self.on_request_error:
                await self._call_lifecycle_hook(
                    self.on_request_error,
                    request_id=request_id,
                    error_type="unknown",
                    error_message=str(e),
                    response_time=response_time
                )
            
            self.logger.error(f"[REQUEST_ERROR] {method} {url}: {e}", extra={
                "request_id": request_id,
                "provider": self.provider_name,
                "method": method,
                "url": url,
                "error": str(e),
                "response_time": response_time
            })
            
            raise
    
    async def _call_lifecycle_hook(self, hook: Callable, **kwargs):
        """Safely call lifecycle hook"""
        try:
            if asyncio.iscoroutinefunction(hook):
                await hook(**kwargs)
            else:
                hook(**kwargs)
        except Exception as e:
            self.logger.warning(f"[LIFECYCLE_HOOK_ERROR] {hook.__name__}: {e}")
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> httpx.Response:
        """Make GET request"""
        return await self._request("GET", endpoint, params=params, **kwargs)
    
    async def post(self, endpoint: str, data: Optional[Union[str, Dict[str, Any]]] = None, **kwargs) -> httpx.Response:
        """Make POST request"""
        return await self._request("POST", endpoint, data=data, **kwargs)
    
    async def put(self, endpoint: str, data: Optional[Union[str, Dict[str, Any]]] = None, **kwargs) -> httpx.Response:
        """Make PUT request"""
        return await self._request("PUT", endpoint, data=data, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> httpx.Response:
        """Make DELETE request"""
        return await self._request("DELETE", endpoint, **kwargs)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get adapter metrics"""
        return {
            "provider_name": self.provider_name,
            "http_metrics": self.metrics.get_metrics(),
            "client_config": {
                "timeout": self.timeout,
                "max_connections": self.client.limits.max_connections,
                "max_keepalive_connections": self.client.limits.max_keepalive_connections
            }
        }
    
    async def close(self) -> None:
        """Close HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
