# Chaos Engineering Suite

A comprehensive chaos engineering framework for testing system resilience with circuit breaker patterns, fault injection, and graceful degradation validation.

## 🚀 **Core Features**

### **⚡ Circuit Breaker Pattern**
- **State management** with CLOSED, OPEN, HALF_OPEN states
- **Configurable thresholds** for failure and recovery
- **Fallback mechanisms** with automatic activation
- **Metrics collection** and state persistence
- **Sliding window** for success rate calculation

### **🌪 Chaos Engine**
- **Multiple fault types**: latency, error, packet loss, corruption
- **Resource exhaustion**: CPU, memory, disk, network
- **Network partitioning** with configurable strategies
- **Service unavailability** simulation
- **Experiment management** with real-time control

### **🛡️ Resilience Testing**
- **Redis connection failure** testing with L1 cache fallback
- **Circuit breaker state** transition validation
- **Fallback mechanism** verification
- **Graceful degradation** scenario testing
- **Performance under load** testing
- **Error handling** validation
- **Timeout handling** verification

## 📁 **Structure**

```
tests/chaos/
├── __init__.py              # Main exports and global instances
├── exceptions.py            # Custom chaos engineering exceptions
├── circuit_breaker.py       # Circuit breaker implementation
├── chaos_engine.py          # Chaos engine with fault injection
├── resilience_tests.py      # Comprehensive test suite
├── example_usage.py          # Complete usage examples
├── requirements.txt         # Dependencies
└── README.md              # This file
```

## 🔧 **Installation**

```bash
pip install -r requirements.txt
```

## 💡 **Quick Start**

### **Circuit Breaker Usage**

```python
from chaos import get_circuit_breaker

# Get circuit breaker
circuit_breaker = get_circuit_breaker()

# Create circuit with configuration
from chaos.circuit_breaker import CircuitConfig, CircuitBreaker
config = CircuitConfig(
    name="api_circuit",
    failure_threshold=5,
    recovery_timeout=60.0,
    success_threshold=3,
    fallback_enabled=True
)

circuit = CircuitBreaker(config)

# Use circuit breaker
result = await circuit.call(api_function, fallback=fallback_function)
print(f"Success: {result.success}, State: {result.circuit_state}")
```

### **Chaos Engine Usage**

```python
from chaos import get_chaos_engine

# Get chaos engine
chaos_engine = get_chaos_engine()

# Create chaos experiment
from chaos.chaos_engine import ChaosExperiment, ChaosType
experiment = ChaosExperiment(
    id="latency_test",
    name="Latency Injection Test",
    chaos_type=ChaosType.LATENCY,
    target="api_service",
    configuration={
        "latency_range": (1.0, 5.0),
        "duration": 300.0,
        "affected_endpoints": ["/api/*"]
    }
)

# Start experiment
experiment_id = await chaos_engine.start_experiment(experiment)
print(f"Started chaos experiment: {experiment_id}")

# Stop experiment
await chaos_engine.stop_experiment(experiment_id)
```

### **Resilience Testing**

```python
from chaos import get_resilience_test_suite
from chaos.resilience_tests import ResilienceTestType

# Get test suite
test_suite = get_resilience_test_suite()

# Run all tests
results = await test_suite.run_all_tests()
print(f"Tests passed: {results['summary']['passed_tests']}/{results['summary']['total_tests']}")

# Run specific test
redis_test = await test_suite.run_specific_test(ResilienceTestType.REDIS_CONNECTION)
print(f"Redis test result: {redis_test.status}")
```

## 🏗️ **Architecture Overview**

### **Circuit Breaker Flow**

```python
# Request flow through circuit breaker
async def call_with_circuit_breaker():
    # Check circuit state
    if circuit.state == CircuitState.OPEN:
        return await fallback_function()
    
    # Execute function with monitoring
    try:
        result = await protected_function()
        circuit.record_success()
        return result
    except Exception as e:
        circuit.record_failure()
        
        # Check if circuit should open
        if circuit.should_open():
            circuit.state = CircuitState.OPEN
        
        return await fallback_function()
```

### **Chaos Experiment Flow**

```python
# Chaos experiment execution
async def run_chaos_experiment():
    # Configure chaos based on type
    chaos_config = configure_chaos(experiment)
    
    # Apply chaos to target
    while experiment.is_running:
        await apply_chaos(experiment.target, chaos_config)
        await asyncio.sleep(experiment.update_interval)
        
        # Update metrics
        record_chaos_metrics(experiment)
        
        # Check if experiment should stop
        if time.time() > experiment.end_time:
            experiment.status = ExperimentStatus.COMPLETED
```

### **Resilience Test Flow**

```python
# Resilience test execution
async def run_resilience_test():
    # Setup test environment
    setup_mocks_and_dependencies()
    
    # Execute test scenario
    try:
        result = await test_function()
        
        # Validate expected behavior
        if result.matches_expected_behavior():
            test.status = TestResult.PASSED
        else:
            test.status = TestResult.FAILED
            
    except Exception as e:
        test.status = TestResult.ERROR
        test.error = str(e)
    
    # Cleanup test environment
    cleanup_test_environment()
```

## 🎯 **Advanced Usage**

### **Custom Circuit Breaker Configuration**

```python
from chaos.circuit_breaker import CircuitConfig

config = CircuitConfig(
    name="custom_circuit",
    failure_threshold=10,           # 10 failures before opening
    recovery_timeout=120.0,          # 2 minutes recovery time
    success_threshold=5,            # 5 successes before closing
    monitoring_period=30.0,         # 30 second monitoring window
    enable_sliding_window=True,       # Use sliding window for metrics
    window_size=100,                # 100 request window
    fallback_enabled=True,           # Enable fallback mechanism
    fallback_timeout=30.0,          # 30 second fallback timeout
    enable_state_persistence=True,    # Persist state to Redis
    redis_url="redis://localhost:6379"
)
```

### **Chaos Experiment Types**

```python
# Latency injection
latency_experiment = ChaosExperiment(
    chaos_type=ChaosType.LATENCY,
    configuration={
        "latency_range": (2.0, 8.0),     # 2-8 second latency
        "latency_distribution": "normal",   # Normal distribution
        "target_latency": 5.0,            # Target 5 second latency
        "jitter": True,                     # Add jitter to latency
        "affected_endpoints": ["/api/*"]   # Affect all API endpoints
    }
)

# Error injection
error_experiment = ChaosExperiment(
    chaos_type=ChaosType.ERROR,
    configuration={
        "error_types": ["timeout", "connection_error", "http_error"],
        "error_rate": 0.1,               # 10% error rate
        "error_distribution": "random",       # Random error distribution
        "target_services": ["user_service", "order_service"]
    }
)

# Network partition
partition_experiment = ChaosExperiment(
    chaos_type=ChaosType.NETWORK_PARTITION,
    configuration={
        "partition_strategy": "random",       # Random partition strategy
        "affected_subnets": ["10.0.0.0/8", "192.168.1.0/16"],
        "drop_rate": 0.1,                   # 10% packet drop rate
        "isolation_duration": 60.0,          # 1 minute isolation
        "affected_hosts": ["service1", "service2"]
    }
)
```

### **Resilience Test Scenarios**

```python
# Redis connection failure test
async def test_redis_connection_failure():
    # Mock Redis connection failure
    with unittest.mock.patch('redis.asyncio.from_url') as mock_redis:
        mock_redis.side_effect = Exception("Connection refused")
        
        # Test that system falls back to L1 cache
        result = await cache_service.get_data("key")
        
        # Verify fallback behavior
        assert result.source == "l1_cache"
        assert result.data is not None

# Circuit breaker state transitions
async def test_circuit_breaker_states():
    # Create circuit breaker
    circuit = CircuitBreaker(config)
    
    # Cause failures to open circuit
    for i in range(5):
        await circuit.call(failing_function)
    
    # Verify circuit is open
    assert circuit.get_state() == CircuitState.OPEN
    
    # Wait for recovery timeout
    await asyncio.sleep(config.recovery_timeout + 1)
    
    # Verify circuit is half-open
    result = await circuit.call(success_function)
    assert circuit.get_state() == CircuitState.HALF_OPEN
    
    # Cause successes to close circuit
    for i in range(3):
        await circuit.call(success_function)
    
    # Verify circuit is closed
    assert circuit.get_state() == CircuitState.CLOSED
```

## 📊 **Configuration Options**

### **Circuit Breaker Configuration**

```python
config = CircuitConfig(
    name="circuit_name",
    failure_threshold=5,              # Failures before opening
    recovery_timeout=60.0,              # Recovery timeout in seconds
    success_threshold=3,                # Successes before closing
    monitoring_period=10.0,             # Metrics collection period
    enable_sliding_window=True,           # Use sliding window
    window_size=100,                    # Sliding window size
    fallback_enabled=True,                # Enable fallback
    fallback_timeout=30.0,               # Fallback timeout
    enable_state_persistence=False,        # Persist state to Redis
    redis_url=None                       # Redis URL for persistence
)
```

### **Chaos Engine Configuration**

```python
config = ChaosConfig(
    enable_chaos=True,                   # Enable chaos experiments
    default_latency_range=(0.1, 1.0),     # Default latency range
    default_error_rate=0.01,              # Default error rate
    enable_redis=False,                     # Enable Redis for state
    redis_url=None,                         # Redis URL
    experiment_timeout=300.0,               # Experiment timeout
    max_concurrent_experiments=5,           # Max concurrent experiments
    enable_metrics=True,                    # Enable metrics collection
    enable_state_persistence=False,           # Enable state persistence
    enable_safety_checks=True,              # Enable safety checks
    dry_run_mode=False                      # Dry run mode
)
```

## 🧪 **Testing**

### **Run Tests with Pytest**

```bash
# Run all chaos tests
pytest tests/chaos/ -v

# Run specific test file
pytest tests/chaos/test_circuit_breaker.py -v

# Run with coverage
pytest tests/chaos/ --cov=chaos --cov-report=html
```

### **Run Resilience Tests**

```python
# Run all resilience tests
python tests/chaos/example_usage.py

# Run specific test type
python -c "
import asyncio
from chaos import get_resilience_test_suite
from chaos.resilience_tests import ResilienceTestType

async def main():
    suite = get_resilience_test_suite()
    result = await suite.run_specific_test(ResilienceTestType.REDIS_CONNECTION)
    print(f"Test result: {result.status}")

asyncio.run(main())
"
```

## 🚨 **Production Features**

- **Non-destructive chaos** with safety checks and dry run mode
- **Real-time experiment control** with start/stop/pause capabilities
- **Comprehensive metrics** collection and analysis
- **State persistence** for experiment recovery
- **Fallback mechanisms** with automatic activation
- **Graceful degradation** with configurable thresholds
- **Circuit breaker patterns** with state management

## 📈 **Performance Characteristics**

- **Circuit breaker overhead**: <1ms per call
- **Chaos injection latency**: <10ms per injection
- **Test execution**: Variable based on test complexity
- **Memory usage**: <50MB for typical test suite
- **Concurrent experiments**: Up to 5 simultaneous

## 🛡️ **Best Practices**

### **Circuit Breaker Usage**

```python
# Set appropriate thresholds
failure_threshold = max(1, expected_rps * 0.05)  # 5% of RPS
recovery_timeout = max(30, expected_response_time * 10)  # 10x response time

# Enable fallback for critical services
fallback_enabled = True for critical_services

# Use sliding window for burst handling
enable_sliding_window = True for bursty_workloads
```

### **Chaos Engineering**

```python
# Start with dry run mode
dry_run_mode = True for first_experiments

# Use safety checks
enable_safety_checks = True for production_chaos

# Monitor experiments closely
enable_metrics = True for all_experiments

# Set reasonable timeouts
experiment_timeout = 300  # 5 minutes max
```

### **Resilience Testing**

```python
# Test all failure scenarios
test_scenarios = [
    "redis_connection_failure",
    "circuit_breaker_states",
    "fallback_mechanism",
    "graceful_degradation",
    "performance_under_load"
]

# Validate expected behaviors
expected_behaviors = {
    "redis_failure": "fallback_to_l1_cache",
    "circuit_open": "no_requests_allowed",
    "fallback_activation": "graceful_degradation"
}
```

The chaos engineering suite provides comprehensive testing capabilities for validating system resilience under various failure scenarios.
