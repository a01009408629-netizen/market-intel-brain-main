"""
Shadow Comparison Engine - Example Usage

This file demonstrates how to use the shadow comparison engine for A/B testing
with concurrent requests and comprehensive analysis.
"""

import asyncio
import time
import random
from typing import Dict, Any, List

from shadow import (
    ShadowEngine,
    ShadowConfig,
    get_engine,
    fetch_with_shadow_globally,
    get_engine_statistics
)
from shadow.exceptions import ShadowError, RequestTimeoutError


# Example adapters to simulate different implementations
class PrimaryAdapter:
    """Primary adapter implementation."""
    
    def __init__(self, name: str, latency_ms: float = None):
        self.name = name
        self.latency_ms = latency_ms or random.uniform(50, 200)
    
    async def fetch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate API call."""
        # Simulate processing time
        await asyncio.sleep(self.latency_ms / 1000)
        
        # Simulate occasional errors
        if random.random() < 0.05:  # 5% error rate
            raise Exception(f"Simulated error in {self.name}")
        
        # Return mock data
        return {
            "data": f"data_from_{self.name}",
            "timestamp": time.time(),
            "adapter": self.name
        }


class ShadowAdapter:
    """Shadow adapter implementation."""
    
    def __init__(self, name: str, latency_ms: float = None, error_rate: float = 0.0):
        self.name = name
        self.latency_ms = latency_ms or random.uniform(100, 500)
        self.error_rate = error_rate
    
    async def fetch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate API call."""
        # Simulate processing time
        await asyncio.sleep(self.latency_ms / 1000)
        
        # Simulate errors based on error rate
        if random.random() < self.error_rate:
            raise Exception(f"Simulated error in {self.name}")
        
        # Return modified data to simulate differences
        data = payload.get("data", {})
        if "value" in data:
            # Modify some values to simulate differences
            if isinstance(data["value"], (int, float)):
                data["value"] *= random.uniform(0.8, 1.2)
            elif isinstance(data["value"], str):
                data["value"] += "_modified"
        
        return {
            "data": data,
            "timestamp": time.time(),
            "adapter": self.name
        }


class FastShadowAdapter:
    """Fast shadow adapter (potentially better performance)."""
    
    def __init__(self, name: str, latency_ms: float = None):
        self.name = name
        self.latency_ms = latency_ms or random.uniform(20, 100)
    
    async def fetch(self, payload: Dict[str, Any]) -> ShadowRequest:
        """Simulate fast API call."""
        await asyncio.sleep(self.latency_ms / 1000)
        
        return {
            "data": f"fast_data_from_{self.name}",
            "timestamp": time.time(),
            "adapter": self.name
        }


class SlowShadowAdapter:
    """Slow shadow adapter (potentially worse performance)."""
    
    def __init__(self, name: str, latency_ms: float = None):
        self.name = name
        self.latency_ms = latency_ms or random.uniform(500, 2000)
    
    async def fetch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate slow API call."""
        await asyncio.sleep(self.latency_ms / 1000)
        
        return {
            "data": f"slow_data_from_{self.name}",
            "timestamp": time.time(),
            "adapter": self.name
        }


# Example payloads for testing
PAYLOADS = {
    "user_profile": {
        "user_id": 123,
        "username": "john_doe",
        "email": "john@example.com",
        "preferences": {
            "theme": "dark",
            "notifications": True
        }
    },
    "stock_data": {
        "symbol": "AAPL",
        "price": 150.0,
        "volume": 1000000,
        "timestamp": "2024-01-01T12:00:00Z"
    },
    "search_results": {
        "query": "test",
        "results": [
            {"id": 1, "title": "Result 1"},
            {"id": 2, "title": "Result 2"}
        ]
    }
}


async def demonstrate_basic_shadow_testing():
    """Demonstrate basic shadow testing."""
    print("=== Basic Shadow Testing ===\n")
    
    engine = get_engine()
    await engine.start()
    
    try:
        print("1. Testing with identical adapters:")
        
        # Create identical adapters
        primary = PrimaryAdapter("primary", 100)  # 100ms latency
        shadow = PrimaryAdapter("shadow", 100)  # 100ms latency
        
        payload = PAYLOADS["user_profile"]
        
        result = await engine.fetch_with_shadow(primary, shadow, payload)
        
        print(f"   Primary result: {result['primary_result']['data']}")
        print(f"   Shadow result: {result['shadow_result']['data']}")
        print(f"   Identical: {result['comparison_result']['is_identical']}")
        print(f"   Similarity: {result['comparison_result']['similarity_score']:.3f}")
        print(f"   Primary latency: {result['primary_latency_ms']:.1f}ms")
        print(f"   Shadow latency: {result['shadow_latency_ms']:.1f}ms")
        
    finally:
        await engine.stop()


async def demonstrate_performance_differences():
    """Demonstrate performance differences between adapters."""
    print("\n=== Performance Differences ===\n")
    
    engine = get_engine()
    await engine.start()
    
    try:
        print("1. Testing with different performance characteristics:")
        
        # Fast shadow vs slow primary
        fast_shadow = FastShadowAdapter("fast_shadow", 50)
        slow_primary = SlowShadowAdapter("slow_primary", 200)
        
        payload = PAYLOADS["stock_data"]
        
        result1 = await engine.fetch_with_shadow(slow_primary, fast_shadow, payload)
        result2 = await engine.fetch_with_shadow(fast_shadow, slow_primary, payload)
        
        print(f"   Slow primary vs Fast shadow:")
        print(f"      Primary latency: {result1['primary_latency_ms']:.1f}ms")
        print(f"      Shadow latency: {result1['shadow_latency_ms']:.1f}ms")
        print(f"      Performance impact: {result1['comparison_result']['performance_differences']['performance_impact']:.2f}")
        
        print(f"   Fast primary vs Slow shadow:")
        print(f"      Primary latency: {result2['primary_latency_ms']:.1f}ms")
        print(f"      Shadow latency: {result2['shadow_latency_ms'].1f}ms")
        print(f"      Performance impact: {result2['comparison_result']['performance_differences']['performance_impact']:.2f}")
        
    finally:
        await engine.stop()


async def demonstrate_content_differences():
    """Demonstrate content differences between responses."""
    print("\n=== Content Differences ===\n")
    
    engine = get_engine()
    await engine.start()
    
    try:
        print("1. Testing with content modifications:")
        
        # Primary adapter returns original data
        primary = PrimaryAdapter("primary", 100)
        
        # Shadow adapter modifies data
        shadow = ShadowAdapter("shadow", 100, error_rate=0.0)
        
        payload = PAYLOADS["search_results"]
        
        result = await engine.fetch_with_shadow(primary, shadow, payload)
        
        print(f"   Primary results: {result['primary_result']['data']['results']}")
        print(f"   Shadow results: {result['shadow_result']['data']['results']}")
        print(f"   Content differences: {len(result['comparison_result']['content_differences'])}")
        
        # Show specific differences
        for diff in result['comparison_result']['content_differences']:
            print(f"   - {diff['path']}: {diff['old_value']} -> {diff['new_value']}")
        
    finally:
        await engine.stop()


async def demonstrate_error_scenarios():
    """Demonstrate error handling."""
    print("\n=== Error Scenarios ===\n")
    
    engine = get_engine()
    await engine.start()
    
    try:
        print("1. Testing timeout handling:")
        
        # Create adapter that times out
        timeout_adapter = PrimaryAdapter("timeout", 100)
        
        payload = PAYLOADS["user_profile"]
        
        result = await engine.fetch_with_shadow(
            primary=PrimaryAdapter("primary", 100),
            shadow=timeout_adapter,
            payload=payload,
            timeout=0.5  # Short timeout for demo
        )
        
        print(f"   Primary result: {result['primary_result']['status']}")
        print(f"   Shadow result: {result['shadow_result']['status']}")
        print(f"   Primary timeout: {result['primary_result'].get('error', 'No response')}")
        print(f"   Shadow timeout: {result['shadow_result'].get('error', 'No response')}")
        
        print("\n2. Testing error handling:")
        
        error_adapter = PrimaryAdapter("error", 100, error_rate=1.0)
        
        result = await engine.fetch_with_shadow(
            primary=PrimaryAdapter("primary", 100),
            shadow=error_adapter,
            payload=payload
        )
        
        print(f"   Primary result: {result['primary_result']['status']}")
        print(f"   Shadow result: {result['shadow_result']['status']}")
        print(f"   Primary error: {result['primary_result'].get('error', 'No error')}")
        print(f"   Shadow error: {result['shadow_result'].get('error', 'No response')}")
        
    finally:
        await engine.stop()


async def demonstrate_dark_launch_detection():
    """Demonstrate dark launch detection."""
    print("\n=== Dark Launch Detection ===\n")
    
    # Configure with dark launch detection
    config = ShadowConfig(
        dark_launch_detection=True,
        similarity_threshold=0.95
        enable_real_time_alerts=True
    )
    
    engine = ShadowEngine(config)
    await engine.start()
    
    try:
        print("1. Testing with different adapters (potential dark launch):")
        
        # Primary adapter returns user data
        primary = PrimaryAdapter("primary", 100)
        
        # Shadow adapter returns modified data
        shadow = ShadowAdapter("shadow", 100)
        
        payload = PAYLOADS["user_profile"]
        
        result = await engine.fetch_with_shadow(primary, shadow, payload)
        
        print(f"   Primary adapter: {result['primary_request']['adapter_name']}")
        print(f"   Shadow adapter: {result['shadow_request']['adapter_name']}")
        print(f"   Identical: {result['comparison_result']['is_identical']}")
        print(f"   Similarity: {result['comparison_result']['similarity_score']:.3f}")
        
        if not result['comparison_result']['is_identical']:
            print(f"   🚨 DARK LAUNCH DETECTED!")
            print(f"   Primary: {result['primary_result']['data']}")
            print(f"   Shadow: {result['shadow_result']['data']}")
        
    finally:
        await engine.stop()


async def demonstrate_concurrent_load_testing():
    """Demonstrate concurrent load testing."""
    print("\n=== Concurrent Load Testing ===\n")
    
    engine = get_engine(
        max_concurrent_requests=20
    )
    await engine.start()
    
    try:
        print("1. Testing concurrent requests:")
        
        # Create multiple shadow adapters
        shadow_adapters = [
            ShadowAdapter(f"shadow_{i}", 50 + i * 10)
            for i in range(5)
        ]
        
        primary = PrimaryAdapter("primary", 150)
        payload = PAYLOADS["stock_data"]
        
        # Create tasks for concurrent execution
        tasks = []
        
        # Primary request
        tasks.append(engine._execute_request(primary, ShadowRequest(
            request_id=f"concurrent_primary",
            adapter_name="primary",
            payload=payload,
            timeout=5.0
        ))
        
        # Shadow requests
        for i, shadow_adapter in enumerate(shadow_adapters):
            tasks.append(engine._execute_request(shadow_adapter, ShadowRequest(
                request_id=f"concurrent_shadow_{i}",
                adapter_name=shadow_adapter.name,
                payload=payload,
                timeout=5.0
            ))
        
        # Execute all concurrently
        results = await asyncio.gather(*tasks)
        
        print(f"   Completed {len(results)} requests")
        
        # Analyze results
        primary_results = [r for r in results if r.adapter_name == "primary"]
        shadow_results = [r for r in results if r.adapter_name.startswith("shadow_")]
        
        primary_success_rate = len([r for r in primary_results if r.status == RequestStatus.COMPLETED])
        shadow_success_rate = len([r for r in shadow_results if r.status == RequestStatus.COMPLETED])
        
        print(f"   Primary success rate: {primary_success_rate}/{len(primary_results)}")
        print(f"   Shadow success rate: {shadow_success_rate}/{len(shadow_results)}")
        
        # Show latencies
        primary_latencies = [r.latency_ms for r in primary_results if r.latency_ms is not None]
        shadow_latencies = [r.latency_ms for r in shadow_results if r.latency_ms is not None]
        
        if primary_latencies:
            print(f"   Primary avg latency: {sum(primary_latencies) / len(primary_latencies):.1f}ms")
        
        if shadow_latencies:
            print(f"   Shadow avg latency: {sum(shadow_latencies) / len(shadow_latencies):.1f}ms")
        
    finally:
        await engine.stop()


async def demonstrate_metrics_collection():
    """Demonstrate metrics collection and analysis."""
    print("\n=== Metrics Collection ===\n")
    
    engine = get_engine(
        enable_metrics=True,
        enable_real_time_alerts=True,
        alert_thresholds={
            "error_rate": 0.05,
            "latency_p95": 1000.0,
            "similarity_threshold": 0.9
        }
    )
    await engine.start()
    
    try:
        print("1. Generating test data for metrics:")
        
        # Generate some test requests
        for i in range(10):
            payload = PAYLOADS["user_profile"]
            await engine.fetch_with_shadow(
                PrimaryAdapter("primary", random.uniform(50, 150)),
                PrimaryAdapter(f"primary_{i}", random.uniform(50, 150)),
                payload=payload
            )
        
        # Wait for aggregation
        await asyncio.sleep(5)
        
        print("\n2. Getting aggregated metrics:")
        
        # Get metrics for 5-second window
        metrics_5s = engine.metrics.get_aggregated_metrics(window_seconds=5)
        
        print(f"   5-second window:")
        print(f"     Total requests: {metrics_5s['total_requests']}")
        print(f"     Success rate: {metrics_5s['primary_metrics']['success_rate']:.2%}")
        print(f"     Avg latency: {metrics_5s['primary_metrics']['avg_latency_ms']:.1f}ms")
        print(f"     P95 latency: {metrics_5s['primary_metrics']['p95_latency_ms']:.1f}ms")
        
        # Get metrics for 30-second window
        metrics_30s = engine.metrics.get_aggregated_metrics(window_seconds=30)
        
        print(f"   30-second window:")
        print(f"     Total requests: {metrics_30s['total_requests']}")
        print(f"     Success rate: {metrics_30s['primary_metrics']['success_rate']:.2%}")
        print(f"     Avg latency: {metrics_30s['primary_metrics']['avg_latency_ms']:.1f}ms}")
        print(f"     P95 latency: {metrics_30s['primary_metrics']['p95_latency_ms']:.1f}ms}")
        
        print("\n3. Engine statistics:")
        stats = engine.get_statistics()
        print(f"   Total requests: {stats['requests_completed']}")
        print(f"   Success rate: {stats['requests_completed'] / max(stats['requests_initiated'], 1):.2%}")
        print(f"   Alerts triggered: {stats['alerts_triggered']}")
        
    finally:
        await engine.stop()


async def demonstrate_real_world_scenario():
    """Demonstrate real-world A/B testing scenario."""
    print("\n=== Real-World A/B Testing Scenario ===\n")
    
    # Configure for production-like testing
    config = ShadowConfig(
        max_concurrent_requests=50,
        default_timeout=10.0,
        enable_comparison=True,
        enable_metrics=True,
        enable_background_diff=True,
        enable_real_time_alerts=True,
        dark_launch_detection=True,
        similarity_threshold=0.95
    )
    
    engine = ShadowEngine(config)
    await engine.start()
    
    try:
        print("1. Simulating production traffic pattern:")
        
        # Simulate burst of requests
        for i in range(20):
            # Mix of different user requests
            user_type = random.choice(["user_profile", "stock_data", "search_results"])
            payload = PAYLOADS[user_type]
            
            # Randomly choose adapter (70% primary, 30% shadow)
            if random.random() < 0.7:
                primary_adapter = PrimaryAdapter("primary", random.uniform(50, 150))
                shadow_adapter = ShadowAdapter("shadow", random.uniform(100, 300))
            else:
                primary_adapter = PrimaryAdapter("primary", random.uniform(50, 150))
                shadow_adapter = PrimaryAdapter("shadow", random.uniform(50, 300))
            
            result = await engine.fetch_with_shadow(primary_adapter, shadow_adapter, payload)
            
            print(f"   Request {i+1}: "
            print(f"      Primary: {result['primary_result']['status']}")
            print(f"      Shadow: {result['shadow_result']['status']}")
            
            if not result['comparison_result']['is_identical']:
                print(f"      Differences: {result['comparison_result']['summary']['total_differences']}")
        
        await asyncio.sleep(0.1)
        
        print("\n2. Analysis of results:")
        
        stats = engine.get_statistics()
        print(f"   Total requests: {stats['requests_completed']}")
        print(f"   Success rate: {stats['requests_completed'] / max(stats['requests_initiated'], 1):.2%}")
        print(f"   Dark launches detected: {stats['dark_launches_detected']}")
        
        # Get recent metrics
        recent_metrics = engine.get_metrics(request_count=20, comparison_count=10)
        print(f"   Recent requests: {len(recent_metrics['recent_requests'])}")
        print(f"   Recent comparisons: {len(recent_metrics['recent_comparisons'])}")
        
    finally:
        await engine.stop()


async def main():
    """Run all shadow testing demonstrations."""
    print("Shadow Comparison Engine - Complete Demonstration")
    print("=" * 60)
    
    try:
        await demonstrate_basic_shadow_testing()
        await demonstrate_performance_differences()
        await demonstrate_content_differences()
        await demonstrate_error_scenarios()
        await demonstrate_dark_launch_detection()
        await demonstrate_concurrent_load_testing()
        await demonstrate_metrics_collection()
        await demonstrate_real_world_scenario()
        
        print("\n" + "=" * 60)
        print("All demonstrations completed successfully!")
        print("\nKey Features Demonstrated:")
        print("✓ Concurrent request execution with asyncio.gather")
        print("✓ Primary and shadow adapter comparison")
        ✓ Detailed difference analysis (structure, content, performance)")
        print("✓ Real-time metrics collection and aggregation")
        print("✓ Configurable alert thresholds")
        print("✓ Dark launch detection for A/B testing")
        print("✓ Comprehensive error handling and timeout management")
        print("✓ Performance impact analysis")
        print("✓ Non-blocking operation (no system shutdown)")
        print("✓ Request history and statistics tracking")
        print("✓ Similarity scoring and drift detection")
        
    except Exception as e:
        print(f"\nDemonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
