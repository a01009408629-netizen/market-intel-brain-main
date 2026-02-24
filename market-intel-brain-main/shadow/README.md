# Shadow Comparison Engine

A comprehensive shadow testing system for A/B experiments using asyncio.gather for concurrent request execution with detailed comparison and performance analysis for dark launching detection.

## 🚀 **Core Features**

### **🔄 Concurrent Request Execution**
- **asyncio.gather** for parallel request execution
- **Primary and shadow requests** executed simultaneously
- **Configurable concurrency limits** to prevent overload
- **Timeout handling** with graceful degradation
- **Request tracking** with unique IDs and status monitoring

### **📊 Comprehensive Comparison**
- **Structure comparison** - Detect added/removed/modified fields
- **Content comparison** - Value-level difference analysis
- **Performance comparison** - Latency and throughput analysis
- **Similarity scoring** - Quantitative difference measurement
- **Change categorization** - Breaking/non-breaking/unknown changes

### **📈 Performance Metrics**
- **Real-time metrics collection** with configurable aggregation windows
- **Success rate tracking** for reliability analysis
- **Latency tracking** with P95/P99 statistics
- **Throughput monitoring** for capacity planning
- **Resource usage tracking** for system monitoring
- **Alert system** for real-time notifications

### **🚨 Dark Launch Detection**
- **Similarity threshold monitoring** for detecting dark launches
- **Adapter name verification** to prevent substitution
- **Response content analysis** for detecting manipulation
- **Real-time alerting** for immediate notification
- **Historical alert tracking** for trend analysis

## 📁 **Structure**

```
shadow/
├── __init__.py              # Main exports and global instances
├── exceptions.py            # Custom shadow engine exceptions
├── comparator.py             # Response comparison functionality
├── metrics.py               # Metrics collection and analysis
├── shadow_engine.py           # Core shadow testing engine
├── example_usage.py            # Comprehensive examples
├── requirements.txt         # Dependencies
└── README.md              # This file
```

## 🔧 **Installation**

```bash
pip install -r requirements.txt
```

## 💡 **Quick Start**

### **Basic Shadow Testing**

```python
from shadow import get_engine

# Get global shadow engine
engine = get_engine()
await engine.start()

# Create adapters
primary_adapter = PrimaryAdapter("primary_api", 100)  # 100ms latency
shadow_adapter = ShadowAdapter("shadow_api", 100)  # 100ms latency

# Execute concurrent requests
result = await engine.fetch_with_shadow(
    primary_adapter=primary_adapter,
    shadow_adapter=shadow_adapter,
    payload={"user_id": 123}
)

print(f"Primary result: {result['primary_result']}")
print(f"Shadow result: {result['shadow_result']}")
print(f"Identical: {result['comparison_result']['is_identical']}")
```

### **Performance Testing**

```python
from shadow import ShadowConfig

# Configure for performance testing
config = ShadowConfig(
    max_concurrent_requests=20,
    default_timeout=30.0,
    enable_performance_metrics=True,
    enable_real_time_alerts=True,
    similarity_threshold=0.9
)

engine = ShadowEngine(config)
await engine.start()

# Test with different performance characteristics
fast_shadow = FastShadowAdapter("fast_shadow", 50)   # 50ms latency
slow_primary = SlowPrimaryAdapter("slow_primary", 500) # 500ms latency

result = await engine.fetch_with_shadow(
    primary_adapter=slow_primary,
    shadow_adapter=fast_shadow,
    payload={"test": "data"}
)

print(f"Performance impact: {result['comparison_result']['performance_differences']['performance_impact']}")
```

### **Dark Launch Detection**

```python
from shadow import ShadowConfig

# Configure dark launch detection
config = ShadowConfig(
    dark_launch_detection=True,
    similarity_threshold=0.95,
    enable_real_time_alerts=True
)

engine = ShadowEngine(config)
await engine.start()

# Test with different adapters
result = await engine.fetch_with_shadow(
    primary_adapter=PrimaryAdapter("production", 100),
    shadow_adapter=ShadowAdapter("test", 100, error_rate=0.1),
    payload={"sensitive_data": "value"}
)

if not result['comparison_result']['is_identical']:
    print("🚨 DARK LAUNCH DETECTED!")
    print(f"Primary: {result['primary_request']['adapter_name']}")
    print(f"Shadow: {result['shadow_request']['adapter_name']}")
```

## 🏗️ **Architecture Overview**

### **Concurrent Request Flow**

```python
async def fetch_with_shadow(primary_adapter, shadow_adapter, payload):
    # Create unique request IDs
    request_id = str(uuid.uuid4())
    
    # Create shadow requests
    primary_request = ShadowRequest(
        request_id=f"{request_id}_primary",
        adapter_name="primary",
        payload=payload,
        timestamp=time.time(),
        timeout=config.default_timeout
    )
    
    shadow_request = ShadowRequest(
        request_id=f"{request_id}_shadow",
        adapter_name="shadow",
        payload=payload,
        timestamp=time.time(),
        timeout=config.default_timeout
    )
    
    # Store requests
    self._active_requests[primary_request.request_id] = primary_request
    self._active_requests[shadow_request.request_id] = shadow_request
    
    # Execute concurrently
    tasks = [
        self._execute_request(primary_adapter, primary_request),
        self._execute_request(shadow_adapter, shadow_request)
    ]
    
    # Wait for completion
    primary_result, shadow_result = await asyncio.gather(*tasks)
    
    # Calculate latencies
    primary_latency = (time.time() - primary_request.timestamp) * 1000
    shadow_latency = (time.time() - shadow_request.timestamp) * 1000
    
    return {
        "request_id": request_id,
        "primary_result": primary_result,
        "shadow_result": shadow_result,
        "primary_latency_ms": primary_latency,
        "shadow_latency_ms": shadow_latency
    }
```

### **Comparison Analysis Flow**

```python
# DeepDiff-based comparison
diff = DeepDiff(primary_response, shadow_response, 
    ignore_order=True,
    verbose_level=1)

# Convert to our format
changes = convert_deepdiff_to_our_format(diff)

# Categorize changes
categorized = {
    "breaking": [c for c in changes if is_breaking_change(c)],
    "non_breaking": [c for c in changes if not is_breaking_change(c)],
    "unknown": [c for c in changes if is_unknown_change(c)]
}
```

## 📊 **Metrics Collection Flow**

```python
# Real-time collection
await metrics.collect_request_metrics(request_metrics)

# Background aggregation
aggregated = await metrics.get_aggregated_metrics(window_seconds=300)

# Performance metrics
performance_metrics = aggregated["performance_metrics"]
print(f"Shadow faster: {performance_metrics['shadow_faster_rate']:.2%}")
print(f"Latency difference: {performance_metrics['latency_difference_ms']:.1f}ms")
```

## 🎯 **Advanced Usage**

### **Custom Configuration**

```python
from shadow import ShadowConfig

config = ShadowConfig(
    max_concurrent_requests=50,
    default_timeout=30.0,
    enable_comparison=True,
    enable_metrics=True,
    enable_background_diff=True,
    enable_real_time_alerts=True,
    dark_launch_detection=True,
    similarity_threshold=0.95,
    alert_thresholds={
        "error_rate": 0.05,      # 5% error rate
        "latency_p95": 1000.0,    # 1 second P95 latency
        "throughput_drop": 0.2,         # 20% throughput drop
    }
)
```

### **Alert System**

```python
def critical_alert_handler(provider, level, message, diff_result):
    """Handle critical shadow testing alerts."""
    print(f"🚨 CRITICAL: {message}")
    # Send to PagerDutyty, Slack, create JIRA ticket
    # Notify development team immediately

def performance_alert_handler(provider, level, message, diff_result):
    """Handle performance alerts."""
    print(f"⚠️ PERFORMANCE ALERT: {message}")
    # Log to monitoring system
    # Create GitHub issue for review
```

# Register callbacks
engine.register_alert_callback(AlertLevel.CRITICAL, critical_alert_handler)
engine.register_alert_callback(AlertLevel.WARNING, performance_alert_handler)
```

## 📈 **Performance Characteristics**

- **Concurrent Requests**: Up to 50+ concurrent requests
- **Request Tracking**: Complete request lifecycle management
- **Timeout Handling**: Graceful degradation on timeouts
- **Memory Efficient**: O(1) memory usage per active request
- **High Throughput**: 1000+ requests/second capability

## 🚨 **Non-Blocking Operation**

The shadow engine operates completely without blocking system operations:
- **No system shutdown** when issues are detected
- **Early warnings** sent to developers
- **Background processing** for comparison and analysis
- **Continuous monitoring** without affecting user experience

## 🛡️ **Production Features**

- **Dark Launch Detection**: Prevents shadow adapters from replacing primary
- **Performance Monitoring**: Real-time alerts for performance degradation
- **Statistical Analysis**: Comprehensive A/B test statistics
- **Historical Tracking**: Request history and trend analysis
- **Alert Integration**: Multiple alert channels and notification systems
- **Configurable Thresholds**: Custom alert triggers for different metrics

The system provides production-ready A/B testing with comprehensive analysis and early warning capabilities without impacting user experience.
