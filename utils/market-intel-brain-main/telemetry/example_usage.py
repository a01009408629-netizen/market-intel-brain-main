"""
Advanced Telemetry - Example Usage

This file demonstrates how to use the advanced telemetry system with
OpenTelemetry tracing and Prometheus metrics for comprehensive monitoring.
"""

import asyncio
import time
import random
from typing import Dict, Any

from telemetry import (
    OpenTelemetryTracer,
    PrometheusMetrics,
    TelemetryCollector,
    TelemetryMiddleware,
    get_tracer,
    get_metrics,
    get_collector,
    get_exporter,
    telemetry_decorator,
    instrument_adapter
)
from telemetry.middleware import instrument_adapter


# Example adapter classes to instrument
class BaseSourceAdapter:
    """Base adapter class for demonstration."""
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
    
    async def fetch_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch data for a symbol."""
        # Simulate API call
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Simulate occasional errors
        if random.random() < 0.1:  # 10% error rate
            raise Exception(f"API error for {symbol}")
        
        return {
            "symbol": symbol,
            "price": 100.0 + random.uniform(-5, 5),
            "timestamp": time.time(),
            "provider": self.provider_name
        }
    
    async def sync_data(self, data: Dict[str, Any]) -> bool:
        """Sync data to external system."""
        # Simulate sync operation
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # Simulate occasional failures
        if random.random() < 0.05:  # 5% failure rate
            raise Exception(f"Sync failed for {data}")
        
        return True


class FinnhubAdapter(BaseSourceAdapter):
    """Finnhub adapter implementation."""
    
    def __init__(self):
        super().__init__("finnhub")


class YahooFinanceAdapter(BaseSourceAdapter):
    """Yahoo Finance adapter implementation."""
    
    def __init__(self):
        super().__init__("yahoo_finance")


class AlphaVantageAdapter(BaseSourceAdapter):
    """Alpha Vantage adapter implementation."""
    
    def __init__(self):
        super().__init__("alpha_vantage")


async def demonstrate_basic_tracing():
    """Demonstrate basic OpenTelemetry tracing."""
    print("=== Basic OpenTelemetry Tracing ===\n")
    
    tracer = get_tracer(service_name="telemetry-demo")
    
    # Create a simple span
    with tracer.trace_async("demo_operation") as span:
        span.set_attribute("operation_type", "demo")
        span.set_attribute("user_id", "user123")
        
        # Simulate work
        await asyncio.sleep(0.1)
        
        # Add event to span
        tracer.add_span_event(span, "work_completed", {"items_processed": 10})
        
        print(f"   ✅ Span completed: {span}")
    
    # Use decorator for automatic tracing
    @tracer.trace_function("decorated_function")
    async def traced_function(x: int, y: int) -> int:
        result = x + y
        await asyncio.sleep(0.05)
        return result
    
    result = await traced_function(5, 3)
    print(f"   ✅ Traced function result: {result}")


async def demonstrate_adapter_instrumentation():
    """Demonstrate automatic adapter instrumentation."""
    print("\n=== Adapter Instrumentation ===\n")
    
    # Create middleware
    middleware = TelemetryMiddleware()
    
    # Instrument adapter classes
    instrumented_finnhub = middleware.instrument_class(FinnhubAdapter, "FinnhubAdapter")
    instrumented_yahoo = middleware.instrument_class(YahooFinanceAdapter, "YahooFinanceAdapter")
    
    # Create instances
    finnhub = instrumented_finnhub()
    yahoo = instrumented_yahoo()
    
    print("1. Using instrumented adapters:")
    
    # Use instrumented adapters (telemetry is automatic)
    try:
        result1 = await finnhub.fetch_data("AAPL")
        print(f"   Finnhub result: {result1['symbol']} = ${result1['price']:.2f}")
    except Exception as e:
        print(f"   Finnhub error: {e}")
    
    try:
        result2 = await yahoo.fetch_data("GOOGL")
        print(f"   Yahoo result: {result2['symbol']} = ${result2['price']:.2f}")
    except Exception as e:
        print(f"   Yahoo error: {e}")
    
    # Show telemetry statistics
    tracer_stats = tracer.get_trace_statistics()
    print(f"\n2. Tracer statistics:")
    print(f"   Service: {tracer_stats['service_name']}")
    print(f"   Enabled: {tracer_stats['enabled']}")
    print(f"   Sample rate: {tracer_stats['sample_rate']}")


async def demonstrate_prometheus_metrics():
    """Demonstrate Prometheus metrics collection."""
    print("\n=== Prometheus Metrics ===\n")
    
    metrics = get_metrics()
    
    print("1. Recording request metrics:")
    
    # Simulate successful requests
    for i in range(5):
        provider = f"provider_{i % 3}"
        operation = f"fetch_{i % 2}"
        duration = random.uniform(0.1, 0.5)
        
        metrics.record_request_success(provider, operation, duration)
        print(f"   ✅ Success: {provider}.{operation} ({duration:.3f}s)")
    
    # Simulate failed requests
    for i in range(2):
        provider = f"provider_{i % 3}"
        operation = f"fetch_{i % 2}"
        duration = random.uniform(0.1, 0.3)
        error_type = random.choice(["timeout", "connection_error", "api_error"])
        
        metrics.record_request_error(provider, operation, error_type, duration)
        print(f"   ❌ Error: {provider}.{operation} ({error_type})")
    
    # Record cache metrics
    print("\n2. Recording cache metrics:")
    metrics.record_cache_hit("provider_1", "l1_cache")
    metrics.record_cache_hit("provider_1", "l2_cache")
    metrics.record_cache_miss("provider_2", "l1_cache")
    metrics.record_cache_miss("provider_2", "l2_cache")
    print("   ✅ Cache hits: 2, Cache misses: 2")
    
    # Record data volume
    print("\n3. Recording data volume:")
    metrics.record_data_volume("provider_1", "json", 1024)
    metrics.record_data_volume("provider_2", "json", 2048)
    print("   ✅ Data volume: provider_1=1KB, provider_2=2KB")
    
    # Show metrics summary
    metrics_summary = metrics.get_metric_summary()
    print(f"\n4. Metrics summary:")
    print(f"   Namespace: {metrics_summary['namespace']}")
    print(f"   Prometheus available: {metrics_summary['prometheus_available']}")
    print(f"   Custom metrics: {metrics_summary['custom_metrics_count']}")


async def demonstrate_telemetry_decorator():
    """Demonstrate telemetry decorator."""
    print("\n=== Telemetry Decorator ===\n")
    
    # Create custom metrics
    metrics = get_metrics()
    
    # Custom counter for decorated functions
    custom_counter = metrics.create_custom_counter(
        "decorated_function_calls_total",
        "Total number of calls to decorated functions",
        ["function_name", "status"]
    )
    
    # Custom histogram for execution time
    custom_histogram = metrics.create_custom_histogram(
        "decorated_function_duration_seconds",
        "Execution time of decorated functions",
        ["function_name"],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
    )
    
    @telemetry_decorator(provider_name="decorated_demo")
    async def expensive_operation(data_size: int) -> Dict[str, Any]:
        """Expensive operation with telemetry."""
        start_time = time.time()
        
        # Simulate work
        await asyncio.sleep(data_size * 0.01)
        
        result = {
            "data_size": data_size,
            "processed_items": data_size * 10,
            "timestamp": time.time()
        }
        
        # Record metrics
        duration = time.time() - start_time
        custom_counter.labels(function_name="expensive_operation", status="success").inc()
        custom_histogram.labels(function_name="expensive_operation").observe(duration)
        
        return result
    
    # Use the decorated function
    print("1. Calling decorated function:")
    result = await expensive_operation(50)
    print(f"   ✅ Processed {result['processed_items']} items")
    
    result = await expensive_operation(100)
    print(f"   ✅ Processed {result['processed_items']} items")
    
    result = await expensive_operation(25)
    print(f"   ✅ Processed {result['processed_items']} items")
    
    # Simulate an error
    @telemetry_decorator(provider_name="decorated_demo")
    async def failing_operation():
        raise Exception("Simulated failure")
    
    try:
        await failing_operation()
    except Exception as e:
        custom_counter.labels(function_name="failing_operation", status="error").inc()
        print(f"   ❌ Captured error: {e}")


async def demonstrate_collector():
    """Demonstrate telemetry data collection."""
    print("\n=== Telemetry Collector ===\n")
    
    collector = get_collector()
    await collector.start()
    
    try:
        print("1. Adding various telemetry events:")
        
        # Add performance events
        collector.add_performance_event("api_call", 0.2, "finnhub", {"endpoint": "/quote"})
        collector.add_performance_event("database_query", 0.05, "postgres", {"table": "users"})
        
        # Add error events
        try:
            raise ValueError("Simulated error")
        except Exception as e:
            collector.add_error_event(e, "database", "user_lookup")
        
        # Add metric events
        collector.add_metric_event("cpu_usage", 75.5, {"host": "server1"}, "system")
        collector.add_metric_event("memory_usage", 1024, {"host": "server1"}, "system")
        
        # Add span events
        collector.add_span_event("trace123", "span456", "cache_hit", {"cache_key": "user:123"})
        
        print("   ✅ Added 5 telemetry events")
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Show statistics
        stats = collector.get_statistics()
        print(f"\n2. Collector statistics:")
        print(f"   Events collected: {stats['events_collected']}")
        print(f"   Events processed: {stats['events_processed']}")
        print(f"   Events dropped: {stats['events_dropped']}")
        print(f"   Current events: {stats['current_events']}")
        print(f"   Uptime: {stats['uptime']:.2f}s")
        
        # Get recent events
        recent_events = collector.get_recent_events(limit=5)
        print(f"\n3. Recent events:")
        for event in recent_events:
            print(f"   {event.event_type} from {event.source} at {event.timestamp:.2f}")
        
        # Get aggregated data
        aggregated = collector.get_aggregated_data()
        print(f"\n4. Aggregated data keys: {list(aggregated.keys())}")
        
    finally:
        await collector.stop()


async def demonstrate_prometheus_exporter():
    """Demonstrate Prometheus exporter."""
    print("\n=== Prometheus Exporter ===\n")
    
    exporter = get_exporter(port=8001)  # Use different port to avoid conflicts
    
    try:
        print("1. Starting Prometheus exporter:")
        await exporter.start()
        print(f"   ✅ Exporter started on port 8001")
        
        # Wait a bit
        await asyncio.sleep(2)
        
        # Get exporter status
        status = exporter.get_exporter_status()
        print(f"\n2. Exporter status:")
        print(f"   Running: {status['running']}")
        print(f"   Prometheus available: {status['prometheus_available']}")
        print(f"   Endpoint: http://{status['config']['host']}:{status['config']['port']}{status['config']['endpoint']}")
        
        # Get metrics data
        metrics_data = exporter.get_metrics_data()
        if "error" not in metrics_data:
            print(f"\n3. Available metrics: {len(metrics_data)} metric families")
        
        # Get registry info
        registry_info = exporter.get_registry_info()
        if "error" not in registry_info:
            print(f"   Registry collectors: {registry_info['total_collectors']}")
        
        print(f"\n4. Metrics endpoint available at:")
        print(f"   http://localhost:8001/metrics")
        print(f"   (Open in browser to see Prometheus metrics)")
        
        print("\n5. Exporter will continue running...")
        print("   Press Ctrl+C to stop the demonstration")
        
        # Keep running for demonstration
        for i in range(10):
            await asyncio.sleep(1)
            print(f"   Exporter running... ({i+1}/10)")
        
    finally:
        await exporter.stop()
        print("   ✅ Exporter stopped")


async def demonstrate_end_to_end_integration():
    """Demonstrate complete end-to-end integration."""
    print("\n=== End-to-End Integration ===\n")
    
    # Initialize all components
    tracer = get_tracer(service_name="integration-demo")
    metrics = get_metrics()
    collector = get_collector()
    middleware = TelemetryMiddleware(tracer, metrics)
    exporter = get_exporter(port=8002)
    
    # Start components
    await collector.start()
    await exporter.start()
    
    try:
        # Instrument adapter class
        instrumented_adapter = middleware.instrument_class(
            BaseSourceAdapter,
            "IntegrationAdapter"
        )
        
        # Create instance
        adapter = instrumented_adapter("integration_provider")
        
        print("1. Using fully instrumented adapter:")
        
        # Use the adapter (all telemetry is automatic)
        for i in range(5):
            try:
                result = await adapter.fetch_data(f"SYMBOL{i}")
                print(f"   ✅ Fetch {result['symbol']}: ${result['price']:.2f}")
            except Exception as e:
                print(f"   ❌ Fetch error: {e}")
        
        # Show comprehensive statistics
        print("\n2. Component statistics:")
        
        # Tracer stats
        tracer_stats = tracer.get_trace_statistics()
        print(f"   Tracer: {tracer_stats['service_name']} (enabled: {tracer_stats['enabled']})")
        
        # Metrics summary
        metrics_summary = metrics.get_metric_summary()
        print(f"   Metrics: {metrics_summary['custom_metrics_count']} custom metrics")
        
        # Collector stats
        collector_stats = collector.get_statistics()
        print(f"   Collector: {collector_stats['events_collected']} events collected")
        
        # Exporter status
        exporter_status = exporter.get_exporter_status()
        print(f"   Exporter: {'running' if exporter_status['running'] else 'stopped'} on port 8002")
        
        print(f"\n3. Integration complete!")
        print(f"   All components working together")
        print(f"   Metrics available at: http://localhost:8002/metrics")
        
        # Wait for some events to be processed
        await asyncio.sleep(3)
        
    finally:
        await collector.stop()
        await exporter.stop()


async def demonstrate_real_world_scenario():
    """Demonstrate a real-world scenario with multiple providers."""
    print("\n=== Real-World Scenario ===\n")
    
    # Initialize components
    tracer = get_tracer(service_name="market-intel-brain")
    metrics = get_metrics()
    collector = get_collector()
    
    await collector.start()
    
    try:
        print("1. Simulating market data fetching from multiple providers:")
        
        # Create adapters with instrumentation
        finnhub = instrument_adapter("finnhub")(FinnhubAdapter)
        yahoo = instrument_adapter("yahoo_finance")(YahooFinanceAdapter)
        alpha_vantage = instrument_adapter("alpha_vantage")(AlphaVantageAdapter)
        
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]
        
        # Fetch data from all providers
        tasks = []
        for provider in [finnhub, yahoo, alpha_vantage]:
            for symbol in symbols:
                task = provider.fetch_data(symbol)
                tasks.append(task)
        
        # Execute all requests concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        print(f"   ✅ Completed {len(tasks)} requests in {end_time - start_time:.2f}s")
        
        # Process results
        success_count = 0
        error_count = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_count += 1
                print(f"   ❌ Error {i}: {result}")
            else:
                success_count += 1
                print(f"   ✅ Success {i}: {result['symbol']} = ${result['price']:.2f}")
        
        print(f"\n2. Results summary:")
        print(f"   Success: {success_count}, Errors: {error_count}")
        print(f"   Success rate: {success_count / len(results):.2%}")
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Show collector statistics
        stats = collector.get_statistics()
        print(f"\n3. Collector statistics after scenario:")
        print(f"   Events collected: {stats['events_collected']}")
        print(f"   Events processed: {stats['events_processed']}")
        
        # Show recent performance events
        performance_events = collector.get_recent_events(
            event_type="performance",
            limit=5
        )
        
        print(f"\n4. Recent performance events:")
        for event in performance_events:
            duration = event.data.get('duration', 0)
            operation = event.operation or 'unknown'
            print(f"   {event.provider}.{operation}: {duration:.3f}s")
        
    finally:
        await collector.stop()


async def main():
    """Run all telemetry demonstrations."""
    print("Advanced Telemetry - Complete Demonstration")
    print("=" * 60)
    
    try:
        await demonstrate_basic_tracing()
        await demonstrate_adapter_instrumentation()
        await demonstrate_prometheus_metrics()
        await demonstrate_telemetry_decorator()
        await demonstrate_collector()
        await demonstrate_prometheus_exporter()
        await demonstrate_end_to_end_integration()
        await demonstrate_real_world_scenario()
        
        print("\n" + "=" * 60)
        print("All demonstrations completed successfully!")
        print("\nKey Features Demonstrated:")
        print("✓ OpenTelemetry distributed tracing with spans")
        print("✓ Prometheus metrics (Histogram, Counter, Gauge)")
        print("✓ Automatic adapter instrumentation")
        print("✓ Telemetry decorators for functions")
        print("✓ Centralized data collection and aggregation")
        print("✓ Prometheus HTTP exporter for Grafana")
        print("✓ End-to-end integration")
        print("✓ Real-world multi-provider scenario")
        print("✓ Performance monitoring and alerting")
        print("✓ Error tracking and analysis")
        
    except Exception as e:
        print(f"\nDemonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
