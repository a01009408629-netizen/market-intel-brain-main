from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Union
from datetime import datetime
import asyncio
import logging
import httpx
import random
from pydantic import BaseModel

from .error_contract import MaifaIngestionError, ProviderTimeoutError, ProviderRateLimitError, ProviderNetworkError
from .circuit_breaker import DistributedCircuitBreaker, CircuitBreakerConfig
from .retry_engine import RetryEngineWithMetrics, RetryConfig


class RequestMetrics:
    """Metrics collection for HTTP requests"""
    
    def __init__(self):
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        self.status_codes = {}
    
    def record_request(self, status_code: int, response_time: float):
        """Record a request"""
        self.request_count += 1
        self.total_response_time += response_time
        
        if status_code in self.status_codes:
            self.status_codes[status_code] += 1
        else:
            self.status_codes[status_code] = 1
        
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
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0"
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
        redis_client,
        timeout: float = 30.0,
        max_retries: int = 3,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.provider_name = provider_name
        self.base_url = base_url
        self.timeout = timeout
        self.logger = logger or logging.getLogger(f"Adapter.{provider_name}")
        
        # HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
        
        # Circuit breaker
        self.circuit_breaker = DistributedCircuitBreaker(
            provider_name=provider_name,
            redis_client=redis_client,
            config=circuit_breaker_config or CircuitBreakerConfig(),
            logger=self.logger
        )
        
        # Retry engine
        retry_config = RetryConfig(max_attempts=max_retries)
        self.retry_engine = RetryEngineWithMetrics(retry_config, self.logger)
        
        # User agent rotator
        self.user_agent_rotator = UserAgentRotator()
        
        # Metrics
        self.metrics = RequestMetrics()
    
    async def fetch(self, params: BaseModel) -> Dict[str, Any]:
        """Main fetch method to be implemented by concrete adapters"""
        return await self.circuit_breaker.execute(self._fetch_with_retry, params)
    
    async def _fetch_with_retry(self, params: BaseModel) -> Dict[str, Any]:
        """Fetch with retry logic"""
        return await self.retry_engine.execute_with_retry(self._fetch_internal, params)
    
    @abstractmethod
    async def _fetch_internal(self, params: BaseModel) -> Dict[str, Any]:
        """Internal fetch method to be implemented by concrete adapters"""
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
        """Make HTTP request with integrated circuit breaker and retry"""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        # Prepare headers with rotating User-Agent
        request_headers = {
            "User-Agent": self.user_agent_rotator.get_random_user_agent(),
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }
        
        if headers:
            request_headers.update(headers)
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            self.logger.info(f"[REQUEST_START] {method} {url}", extra={
                "provider": self.provider_name,
                "method": method,
                "url": url,
                "params": params,
                "headers": {k: v for k, v in request_headers.items() if k.lower() != "user-agent"}
            })
            
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
            
            self.logger.info(f"[REQUEST_SUCCESS] {method} {url} - {response.status_code} ({response_time:.3f}s)", extra={
                "provider": self.provider_name,
                "method": method,
                "url": url,
                "status_code": response.status_code,
                "response_time": response_time
            })
            
            # Handle HTTP errors
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise ProviderRateLimitError(
                    provider_name=self.provider_name,
                    retry_after=int(retry_after) if retry_after else None
                )
            elif 400 <= response.status_code < 500:
                raise MaifaIngestionError(
                    message=f"Client error: HTTP {response.status_code}",
                    provider_name=self.provider_name,
                    suggested_action="Check request parameters",
                    is_transient=False,
                    context={"status_code": response.status_code, "response": response.text}
                )
            elif response.status_code >= 500:
                raise MaifaIngestionError(
                    message=f"Server error: HTTP {response.status_code}",
                    provider_name=self.provider_name,
                    suggested_action="Retry later",
                    is_transient=True,
                    context={"status_code": response.status_code, "response": response.text}
                )
            
            return response
        
        except httpx.TimeoutException as e:
            response_time = asyncio.get_event_loop().time() - start_time
            self.metrics.record_request(0, response_time)  # 0 for timeout
            
            self.logger.error(f"[REQUEST_TIMEOUT] {method} {url} ({response_time:.3f}s)", extra={
                "provider": self.provider_name,
                "method": method,
                "url": url,
                "timeout": self.timeout,
                "response_time": response_time
            })
            
            raise ProviderTimeoutError(
                provider_name=self.provider_name,
                timeout_seconds=self.timeout
            )
        
        except httpx.NetworkError as e:
            response_time = asyncio.get_event_loop().time() - start_time
            self.metrics.record_request(0, response_time)  # 0 for network error
            
            self.logger.error(f"[REQUEST_NETWORK_ERROR] {method} {url}: {e}", extra={
                "provider": self.provider_name,
                "method": method,
                "url": url,
                "error": str(e),
                "response_time": response_time
            })
            
            raise ProviderNetworkError(
                provider_name=self.provider_name,
                network_error=str(e)
            )
        
        except MaifaIngestionError:
            # Re-raise MAIFA errors as-is
            raise
        
        except Exception as e:
            response_time = asyncio.get_event_loop().time() - start_time
            self.metrics.record_request(0, response_time)  # 0 for other errors
            
            self.logger.error(f"[REQUEST_ERROR] {method} {url}: {e}", extra={
                "provider": self.provider_name,
                "method": method,
                "url": url,
                "error": str(e),
                "response_time": response_time
            })
            
            raise MaifaIngestionError(
                message=f"Unexpected error: {str(e)}",
                provider_name=self.provider_name,
                suggested_action="Check logs and retry",
                is_transient=True,
                context={"original_error": str(e), "type": type(e).__name__}
            )
    
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
            "circuit_breaker_metrics": asyncio.create_task(self.circuit_breaker.get_metrics()),
            "retry_metrics": self.retry_engine.metrics.get_metrics()
        }
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
