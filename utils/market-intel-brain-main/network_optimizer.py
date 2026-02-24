"""
Network Optimization for Concurrent REST Polling
aiohttp TCPConnector with Keep-Alive for 2 CPU cores
"""

import asyncio
import aiohttp
import ssl
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor


@dataclass
class NetworkConfig:
    """Network optimization configuration."""
    max_connections: int = 50
    keepalive_timeout: int = 30
    connect_timeout: int = 10
    read_timeout: int = 30
    total_timeout: int = 60
    limit_per_host: int = 10
    enable_cleanup_closed: bool = True
    use_dns_cache: bool = True
    family: int = 0  # IPv4+IPv6


class NetworkOptimizer:
    """Optimized HTTP client for concurrent REST polling."""
    
    def __init__(self, config: Optional[NetworkConfig] = None):
        self.config = config or NetworkConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Performance metrics
        self._metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_time": 0.0,
            "avg_response_time": 0.0,
            "connections_created": 0,
            "connections_reused": 0
        }
    
    async def create_session(self) -> aiohttp.ClientSession:
        """Create optimized HTTP session."""
        if self.session and not self.session.closed:
            return self.session
        
        # SSL context for better performance
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # TCP Connector with optimization
        connector = aiohttp.TCPConnector(
            limit=self.config.max_connections,  # Total connections
            limit_per_host=self.config.limit_per_host,  # Per host
            keepalive_timeout=self.config.keepalive_timeout,
            enable_cleanup_closed=self.config.enable_cleanup_closed,
            use_dns_cache=self.config.use_dns_cache,
            family=self.config.family,
            ssl=ssl_context,
            ttl_dns_cache=300,  # 5 minutes DNS cache
            use_dns_cache=True
        )
        
        # Timeout configuration
        timeout = aiohttp.ClientTimeout(
            total=self.config.total_timeout,
            connect=self.config.connect_timeout,
            sock_read=self.config.read_timeout
        )
        
        # Create session with optimized headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; TradFiBot/1.0)',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Keep-Alive': f'timeout={self.config.keepalive_timeout}'
        }
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers,
            cookie_jar=aiohttp.CookieJar(unsafe=True)  # Better performance
        )
        
        return self.session
    
    async def close_session(self):
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def make_request(self, method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make optimized HTTP request."""
        session = await self.create_session()
        
        start_time = time.time()
        self._metrics["total_requests"] += 1
        
        try:
            async with session.request(method, url, **kwargs) as response:
                # Check if connection was reused
                if response.connection and hasattr(response.connection, 'transport'):
                    if hasattr(response.connection.transport, '_sock'):
                        self._metrics["connections_reused"] += 1
                    else:
                        self._metrics["connections_created"] += 1
                else:
                    self._metrics["connections_created"] += 1
                
                # Update metrics
                response_time = time.time() - start_time
                self._metrics["total_time"] += response_time
                self._metrics["avg_response_time"] = self._metrics["total_time"] / self._metrics["total_requests"]
                
                if response.status == 200:
                    self._metrics["successful_requests"] += 1
                    
                    # Parse JSON response
                    content_type = response.headers.get('content-type', '').lower()
                    if 'application/json' in content_type:
                        data = await response.json()
                    else:
                        # Fallback to text
                        text = await response.text()
                        try:
                            import json
                            data = json.loads(text)
                        except:
                            data = {"raw_response": text}
                    
                    return data
                else:
                    self._metrics["failed_requests"] += 1
                    print(f"HTTP {response.status} for {url}")
                    return None
                    
        except asyncio.TimeoutError:
            self._metrics["failed_requests"] += 1
            print(f"Timeout for {url}")
            return None
        except Exception as e:
            self._metrics["failed_requests"] += 1
            print(f"Request error for {url}: {e}")
            return None
        finally:
            # Response is automatically closed by context manager
            pass
    
    async def make_concurrent_requests(self, requests: List[Dict[str, Any]]) -> List[Optional[Dict[str, Any]]]:
        """Make multiple concurrent requests."""
        tasks = []
        
        for request in requests:
            method = request.get('method', 'GET')
            url = request.get('url')
            kwargs = {k: v for k, v in request.items() if k not in ['method', 'url']}
            
            task = self.make_request(method, url, **kwargs)
            tasks.append(task)
        
        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to None
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append(None)
                self._metrics["failed_requests"] += 1
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get network performance metrics."""
        metrics = self._metrics.copy()
        
        if metrics["total_requests"] > 0:
            metrics["success_rate"] = metrics["successful_requests"] / metrics["total_requests"]
            metrics["failure_rate"] = metrics["failed_requests"] / metrics["total_requests"]
        else:
            metrics["success_rate"] = 0.0
            metrics["failure_rate"] = 0.0
        
        # Connection reuse rate
        total_connections = metrics["connections_created"] + metrics["connections_reused"]
        if total_connections > 0:
            metrics["connection_reuse_rate"] = metrics["connections_reused"] / total_connections
        else:
            metrics["connection_reuse_rate"] = 0.0
        
        # Requests per second
        if metrics["total_time"] > 0:
            metrics["requests_per_second"] = metrics["total_requests"] / metrics["total_time"]
        else:
            metrics["requests_per_second"] = 0.0
        
        return metrics
    
    def reset_metrics(self):
        """Reset performance metrics."""
        self._metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_time": 0.0,
            "avg_response_time": 0.0,
            "connections_created": 0,
            "connections_reused": 0
        }
    
    async def benchmark_performance(self, urls: List[str], concurrent_limit: int = 10) -> Dict[str, Any]:
        """Benchmark network performance."""
        print(f"Benchmarking network performance with {len(urls)} URLs...")
        
        # Reset metrics
        self.reset_metrics()
        
        # Create requests
        requests = [{"url": url, "method": "GET"} for url in urls]
        
        # Test different concurrency levels
        results = {}
        
        for concurrency in [1, 5, 10, 20, concurrent_limit]:
            if concurrency > len(urls):
                continue
            
            print(f"  Testing concurrency: {concurrency}")
            
            # Reset metrics for this test
            self.reset_metrics()
            
            # Split requests into batches
            start_time = time.time()
            
            for i in range(0, len(requests), concurrency):
                batch = requests[i:i + concurrency]
                await self.make_concurrent_requests(batch)
            
            total_time = time.time() - start_time
            metrics = self.get_metrics()
            
            results[f"concurrency_{concurrency}"] = {
                "total_time": total_time,
                "requests_per_second": len(requests) / total_time,
                "avg_response_time": metrics["avg_response_time"],
                "success_rate": metrics["success_rate"],
                "connection_reuse_rate": metrics["connection_reuse_rate"]
            }
            
            print(f"    Time: {total_time:.2f}s, RPS: {len(requests) / total_time:.1f}, "
                  f"Success: {metrics['success_rate']:.1%}, Reuse: {metrics['connection_reuse_rate']:.1%}")
        
        return results


# Global network optimizer instance
_network_optimizer: Optional[NetworkOptimizer] = None


def get_network_optimizer() -> NetworkOptimizer:
    """Get global network optimizer."""
    global _network_optimizer
    if _network_optimizer is None:
        _network_optimizer = NetworkOptimizer()
    return _network_optimizer


async def main():
    """Test network optimizer."""
    optimizer = get_network_optimizer()
    
    print("Testing Network Optimizer")
    print("=" * 50)
    
    # Test URLs
    test_urls = [
        "https://httpbin.org/json",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/status/200",
        "https://api.github.com/users/python",
        "https://jsonplaceholder.typicode.com/posts/1"
    ]
    
    # Test single requests
    print("\n1. Testing single requests:")
    for url in test_urls[:3]:
        start = time.time()
        result = await optimizer.make_request("GET", url)
        elapsed = time.time() - start
        print(f"  {url[:30]}... | {elapsed:.2f}s | {'Success' if result else 'Failed'}")
    
    # Test concurrent requests
    print("\n2. Testing concurrent requests:")
    requests = [{"url": url, "method": "GET"} for url in test_urls]
    start = time.time()
    results = await optimizer.make_concurrent_requests(requests)
    elapsed = time.time() - start
    
    success_count = sum(1 for r in results if r is not None)
    print(f"  {len(requests)} requests in {elapsed:.2f}s")
    print(f"  Success: {success_count}/{len(requests)}")
    print(f"  RPS: {len(requests) / elapsed:.1f}")
    
    # Show metrics
    print("\n3. Network metrics:")
    metrics = optimizer.get_metrics()
    print(f"  Total requests: {metrics['total_requests']}")
    print(f"  Success rate: {metrics['success_rate']:.1%}")
    print(f"  Avg response time: {metrics['avg_response_time']:.3f}s")
    print(f"  Connection reuse rate: {metrics['connection_reuse_rate']:.1%}")
    print(f"  Requests per second: {metrics['requests_per_second']:.1f}")
    
    # Benchmark performance
    print("\n4. Performance benchmark:")
    benchmark_urls = test_urls * 2  # Duplicate for more requests
    benchmark_results = await optimizer.benchmark_performance(benchmark_urls, concurrent_limit=10)
    
    # Show best performance
    best_concurrency = max(benchmark_results.keys(), 
                          key=lambda k: benchmark_results[k]['requests_per_second'])
    best_performance = benchmark_results[best_concurrency]
    
    print(f"\nBest performance: {best_concurrency}")
    print(f"  RPS: {best_performance['requests_per_second']:.1f}")
    print(f"  Success rate: {best_performance['success_rate']:.1%}")
    print(f"  Connection reuse: {best_performance['connection_reuse_rate']:.1%}")
    
    # Cleanup
    await optimizer.close_session()


if __name__ == "__main__":
    asyncio.run(main())
