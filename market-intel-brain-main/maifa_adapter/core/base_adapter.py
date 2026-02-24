"""
MAIFA Source Adapter - Base Adapter Class

This module defines the abstract base class that all adapters must inherit from.
It provides the foundational interface and common functionality for data ingestion.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union, Callable
from datetime import datetime
from decimal import Decimal
import httpx
import msgpack

from .exceptions import (
    TransientAdapterError,
    FatalAdapterError,
    AdapterTimeoutError,
    AdapterValidationError,
    AdapterDataError
)


class BaseSourceAdapter(ABC):
    """
    Abstract base class for all MAIFA source adapters.
    
    All adapters must inherit from this class and implement the required methods.
    This class provides common functionality and enforces the MAIFA engineering standards.
    """
    
    def __init__(
        self,
        adapter_name: str,
        base_url: str,
        timeout: float = 30.0,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the base adapter.
        
        Args:
            adapter_name: Unique identifier for the adapter
            base_url: Base URL for the provider API
            timeout: Request timeout in seconds
            max_connections: Maximum HTTP connections
            max_keepalive_connections: Maximum keepalive connections
            logger: Logger instance for the adapter
        """
        self.adapter_name = adapter_name
        self.base_url = base_url
        self.timeout = timeout
        self.logger = logger or logging.getLogger(f"Adapter.{adapter_name}")
        
        # HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(
                max_keepalive_connections=max_keepalive_connections,
                max_connections=max_connections
            )
        )
        
        # Metrics collection
        self._metrics = {
            "request_count": 0,
            "success_count": 0,
            "error_count": 0,
            "total_response_time": 0.0,
            "last_request_time": None
        }
    
    @abstractmethod
    async def fetch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch data from the provider.
        
        This is the main method that adapters must implement.
        It should handle the complete data fetching process including
        validation, request execution, and data normalization.
        
        Args:
            params: Provider-specific parameters
            
        Returns:
            Normalized data dictionary
            
        Raises:
            TransientAdapterError: For retriable errors
            FatalAdapterError: For non-retriable errors
        """
        pass
    
    @abstractmethod
    async def validate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize request parameters.
        
        Args:
            params: Raw request parameters
            
        Returns:
            Validated and normalized parameters
            
        Raises:
            AdapterValidationError: If validation fails
        """
        pass
    
    @abstractmethod
    async def normalize_response(self, raw_data: Any) -> Dict[str, Any]:
        """
        Normalize raw provider response to standard format.
        
        Args:
            raw_data: Raw response from provider
            
        Returns:
            Normalized data dictionary
            
        Raises:
            AdapterDataError: If data normalization fails
        """
        pass
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[str, Dict[str, Any]]] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with error handling and metrics.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            headers: Request headers
            data: Request body
            **kwargs: Additional request parameters
            
        Returns:
            HTTP response
            
        Raises:
            AdapterTimeoutError: If request times out
            AdapterNetworkError: If network error occurs
            TransientAdapterError: For other retriable errors
            FatalAdapterError: For non-retriable errors
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        start_time = asyncio.get_event_loop().time()
        
        try:
            self._metrics["request_count"] += 1
            self.logger.debug(f"[{self.adapter_name}] {method} {url}")
            
            response = await self.client.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                data=data,
                **kwargs
            )
            
            # Update metrics
            response_time = asyncio.get_event_loop().time() - start_time
            self._metrics["total_response_time"] += response_time
            self._metrics["last_request_time"] = datetime.utcnow()
            
            if 200 <= response.status_code < 300:
                self._metrics["success_count"] += 1
                self.logger.debug(f"[{self.adapter_name}] Success: {response.status_code} ({response_time:.3f}s)")
            else:
                self._metrics["error_count"] += 1
                self.logger.warning(f"[{self.adapter_name}] HTTP Error: {response.status_code}")
            
            return response
            
        except httpx.TimeoutException as e:
            self._metrics["error_count"] += 1
            raise AdapterTimeoutError(
                message=f"Request timeout for {self.adapter_name}",
                adapter_name=self.adapter_name,
                timeout_seconds=self.timeout,
                context={"url": url, "method": method}
            ) from e
            
        except httpx.NetworkError as e:
            self._metrics["error_count"] += 1
            raise TransientAdapterError(
                message=f"Network error for {self.adapter_name}: {str(e)}",
                adapter_name=self.adapter_name,
                context={"url": url, "method": method, "network_error": str(e)}
            ) from e
            
        except Exception as e:
            self._metrics["error_count"] += 1
            raise TransientAdapterError(
                message=f"Unexpected error for {self.adapter_name}: {str(e)}",
                adapter_name=self.adapter_name,
                context={"url": url, "method": method, "error_type": type(e).__name__}
            ) from e
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> httpx.Response:
        """Make GET request."""
        return await self._make_request("GET", endpoint, params=params, **kwargs)
    
    async def post(self, endpoint: str, data: Optional[Union[str, Dict[str, Any]]] = None, **kwargs) -> httpx.Response:
        """Make POST request."""
        return await self._make_request("POST", endpoint, data=data, **kwargs)
    
    async def put(self, endpoint: str, data: Optional[Union[str, Dict[str, Any]]] = None, **kwargs) -> httpx.Response:
        """Make PUT request."""
        return await self._make_request("PUT", endpoint, data=data, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> httpx.Response:
        """Make DELETE request."""
        return await self._make_request("DELETE", endpoint, **kwargs)
    
    def serialize_data(self, data: Any) -> bytes:
        """
        Serialize data using MessagePack for internal caching/transport.
        
        Args:
            data: Data to serialize
            
        Returns:
            MessagePack-encoded bytes
        """
        try:
            return msgpack.packb(data, default=str)
        except Exception as e:
            raise AdapterDataError(
                message=f"Failed to serialize data for {self.adapter_name}",
                adapter_name=self.adapter_name,
                data_details=str(e)
            ) from e
    
    def deserialize_data(self, data: bytes) -> Any:
        """
        Deserialize MessagePack data.
        
        Args:
            data: MessagePack-encoded bytes
            
        Returns:
            Deserialized data
        """
        try:
            return msgpack.unpackb(data, raw=False)
        except Exception as e:
            raise AdapterDataError(
                message=f"Failed to deserialize data for {self.adapter_name}",
                adapter_name=self.adapter_name,
                data_details=str(e)
            ) from e
    
    def ensure_decimal(self, value: Union[str, int, float, Decimal]) -> Decimal:
        """
        Ensure value is a Decimal for financial precision.
        
        Args:
            value: Value to convert
            
        Returns:
            Decimal value
        """
        try:
            if isinstance(value, Decimal):
                return value
            elif isinstance(value, (int, str)):
                return Decimal(str(value))
            elif isinstance(value, float):
                # Convert float to string first to avoid precision issues
                return Decimal(str(value))
            else:
                raise AdapterDataError(
                    message=f"Cannot convert {type(value)} to Decimal",
                    adapter_name=self.adapter_name
                )
        except Exception as e:
            raise AdapterDataError(
                message=f"Decimal conversion failed for {self.adapter_name}",
                adapter_name=self.adapter_name,
                data_details=str(e)
            ) from e
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get adapter metrics.
        
        Returns:
            Dictionary with adapter metrics
        """
        total_requests = self._metrics["request_count"]
        avg_response_time = (
            self._metrics["total_response_time"] / total_requests 
            if total_requests > 0 else 0
        )
        success_rate = (
            self._metrics["success_count"] / total_requests 
            if total_requests > 0 else 0
        )
        
        return {
            "adapter_name": self.adapter_name,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "metrics": {
                **self._metrics,
                "average_response_time": avg_response_time,
                "success_rate": success_rate,
                "error_rate": 1 - success_rate
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the adapter.
        
        Returns:
            Health check results
        """
        try:
            # Try a simple request to check connectivity
            start_time = asyncio.get_event_loop().time()
            response = await self.get("/", timeout=5.0)
            response_time = asyncio.get_event_loop().time() - start_time
            
            return {
                "adapter_name": self.adapter_name,
                "healthy": True,
                "status_code": response.status_code,
                "response_time": response_time,
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": self.get_metrics()
            }
            
        except Exception as e:
            return {
                "adapter_name": self.adapter_name,
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": self.get_metrics()
            }
    
    async def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        await self.client.aclose()
        self.logger.info(f"[{self.adapter_name}] Adapter closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
