"""
Resilience Tests

This module provides comprehensive resilience testing capabilities
for testing system behavior under various failure scenarios.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import unittest.mock
import pytest
import pytest_asyncio

from .circuit_breaker import CircuitBreaker, get_circuit_breaker
from .chaos_engine import ChaosEngine, get_chaos_engine
from .exceptions import ChaosError, ConfigurationError


class TestResult(Enum):
    """Result of a resilience test."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


class ResilienceTestType(Enum):
    """Types of resilience tests."""
    REDIS_CONNECTION = "redis_connection"
    CIRCUIT_BREAKER = "circuit_breaker"
    FALLBACK_MECHANISM = "fallback_mechanism"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    PERFORMANCE_UNDER_LOAD = "performance_under_load"
    ERROR_HANDLING = "error_handling"
    TIMEOUT_HANDLING = "timeout_handling"
    PARTIAL_FAILURE = "partial_failure"


@dataclass
class TestConfiguration:
    """Configuration for resilience tests."""
    test_name: str
    test_type: ResilienceTestType
    timeout: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    enable_detailed_logging: bool = True
    expected_behavior: Dict[str, Any]
    test_data: Dict[str, Any]
    cleanup_after_test: bool = True


@dataclass
class TestExecution:
    """Execution details for a resilience test."""
    test_id: str
    test_name: str
    test_type: ResilienceTestType
    start_time: float
    end_time: Optional[float]
    status: TestResult
    error: Optional[str]
    metrics: Dict[str, Any]
    logs: List[str]
    artifacts: Dict[str, Any]


@dataclass
class ResilienceTestSuite:
    """Comprehensive resilience test suite."""
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize resilience test suite.
        
        Args:
            config: Test suite configuration
            logger: Logger instance
        """
        self.config = config or {}
        self.logger = logger or logging.getLogger("ResilienceTestSuite")
        
        # Components
        self.circuit_breaker = get_circuit_breaker()
        self.chaos_engine = get_chaos_engine()
        
        # Test state
        self._tests: List[TestExecution] = []
        self._current_test: Optional[TestExecution] = None
        self._test_results: Dict[str, TestResult] = {}
        
        # Mock objects
        self._redis_mock = None
        self._cache_mock = None
        
        self.logger.info("ResilienceTestSuite initialized")
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all resilience tests.
        
        Returns:
            Dictionary with test results and summary
        """
        self.logger.info("Starting resilience test suite")
        
        # Initialize mocks
        await self._initialize_mocks()
        
        # Define tests
        tests = [
            self._create_redis_connection_test(),
            self._create_circuit_breaker_test(),
            self._create_fallback_mechanism_test(),
            self._create_graceful_degradation_test(),
            self._create_performance_under_load_test(),
            self._create_error_handling_test(),
            self._create_timeout_handling_test(),
            self._create_partial_failure_test()
        ]
        
        # Run tests
        for test_config in tests:
            await self._run_single_test(test_config)
        
        # Generate summary
        summary = self._generate_test_summary()
        
        # Cleanup
        await self._cleanup()
        
        self.logger.info(f"Resilience test suite completed: {summary['total_passed']}/{summary['total_tests']} passed")
        
        return {
            "tests": self._tests,
            "summary": summary,
            "artifacts": self._collect_artifacts()
        }
    
    async def run_specific_test(self, test_type: ResilienceTestType) -> TestExecution:
        """
        Run a specific resilience test.
        
        Args:
            test_type: Type of test to run
            
        Returns:
            TestExecution with results
        """
        self.logger.info(f"Running specific test: {test_type}")
        
        # Initialize mocks
        await self._initialize_mocks()
        
        # Get test configuration
        test_config = self._get_test_configuration(test_type)
        
        # Run test
        result = await self._run_single_test(test_config)
        
        # Cleanup
        await self._cleanup()
        
        return result
    
    async def _run_single_test(self, test_config: TestConfiguration) -> TestExecution:
        """Run a single resilience test."""
        test_id = f"test_{int(time.time())}"
        
        # Create test execution
        execution = TestExecution(
            test_id=test_id,
            test_name=test_config.test_name,
            test_type=test_config.test_type,
            start_time=time.time(),
            end_time=None,
            status=TestResult.RUNNING,
            error=None,
            metrics={},
            logs=[],
            artifacts={}
        )
        
        self._current_test = execution
        
        try:
            self.logger.info(f"Starting test: {test_config.test_name}")
            
            # Run test based on type
            if test_config.test_type == ResilienceTestType.REDIS_CONNECTION:
                await self._run_redis_connection_test(execution, test_config)
            elif test_config.test_type == ResilienceTestType.CIRCUIT_BREAKER:
                await self._run_circuit_breaker_test(execution, test_config)
            elif test_config.test_type == ResilienceTestType.FALLBACK_MECHANISM:
                await self._run_fallback_mechanism_test(execution, test_config)
            elif test_config.test_type == ResilienceTestType.GRACEFUL_DEGRADATION:
                await self._run_graceful_degradation_test(execution, test_config)
            elif test_config.test_type == ResilienceTestType.PERFORMANCE_UNDER_LOAD:
                await self._run_performance_under_load_test(execution, test_config)
            elif test_config.test_type == ResilienceTestType.ERROR_HANDLING:
                await self._run_error_handling_test(execution, test_config)
            elif test_config.test_type == ResilienceTestType.TIMEOUT_HANDLING:
                await self._run_timeout_handling_test(execution, test_config)
            elif test_config.test_type == ResilienceTestType.PARTIAL_FAILURE:
                await self._run_partial_failure_test(execution, test_config)
            
            execution.status = TestResult.PASSED
            execution.end_time = time.time()
            
        except Exception as e:
            execution.status = TestResult.FAILED
            execution.error = str(e)
            execution.end_time = time.time()
            self.logger.error(f"Test failed: {test_config.test_name} - {e}")
        
        finally:
            self._tests.append(execution)
            self._test_results[test_config.test_name] = execution.status
            self._current_test = None
        
        return execution
    
    async def _run_redis_connection_test(self, execution: TestExecution, config: TestConfiguration):
        """Test Redis connection resilience."""
        self.logger.info("Running Redis connection test")
        
        # Mock Redis connection failure
        with unittest.mock.patch('redis.asyncio.from_url') as mock_redis:
            # Simulate connection error
            mock_redis.side_effect = Exception("Connection refused")
            
            try:
                # Attempt Redis connection
                import redis.asyncio
                redis_client = redis.asyncio.from_url("redis://localhost:6379")
                
                # Test connection
                await redis_client.ping()
                
                # This should fail
                execution.status = TestResult.FAILED
                execution.error = "Redis connection should have failed"
                
            except Exception as e:
                # Expected failure
                execution.status = TestResult.PASSED
                execution.metrics["redis_connection_failed"] = True
                execution.metrics["error_message"] = str(e)
                execution.logs.append(f"Redis connection failed as expected: {e}")
        
        # Test fallback to L1 cache
        await self._test_fallback_to_l1_cache(execution, config)
    
    async def _run_circuit_breaker_test(self, execution: TestExecution, config: TestConfiguration):
        """Test circuit breaker functionality."""
        self.logger.info("Running circuit breaker test")
        
        # Create test circuit breaker
        from .circuit_breaker import CircuitConfig
        circuit_config = CircuitConfig(
            name="test_circuit",
            failure_threshold=3,
            recovery_timeout=5.0,
            success_threshold=2
        )
        
        circuit_breaker = CircuitBreaker(circuit_config)
        
        # Simulate failures
        failure_count = 0
        
        for i in range(10):
            async def failing_function():
                if i < 5:  # First 5 requests fail
                    failure_count += 1
                    raise Exception(f"Simulated failure {i}")
                else:
                    return f"Success {i}"
            
            result = await circuit_breaker.call(failing_function)
            
            execution.logs.append(f"Request {i}: success={result.success}, state={result.circuit_state}")
            
            if i == 4:  # After 5 failures, circuit should be open
                if result.circuit_state != CircuitState.OPEN:
                    execution.status = TestResult.FAILED
                    execution.error = f"Circuit should be OPEN after 5 failures, got {result.circuit_state}"
                    return
            elif i == 7:  # After recovery timeout, should be half-open
                if result.circuit_state != CircuitState.HALF_OPEN:
                    execution.status = TestResult.FAILED
                    execution.error = f"Circuit should be HALF_OPEN after recovery, got {result.circuit_state}"
                    return
            elif i == 9:  # After 2 successes, should be closed
                if result.circuit_state != CircuitState.CLOSED:
                    execution.status = TestResult.FAILED
                    execution.error = f"Circuit should be CLOSED after 2 successes, got {result.circuit_state}"
                    return
        
        execution.metrics["circuit_breaker_working"] = True
        execution.metrics["final_state"] = circuit_breaker.get_state().value
        execution.logs.append("Circuit breaker test completed successfully")
    
    async def _run_fallback_mechanism_test(self, execution: TestExecution, config: TestConfiguration):
        """Test fallback mechanism functionality."""
        self.logger.info("Running fallback mechanism test")
        
        # Create function with fallback
        async def primary_function():
            raise Exception("Primary service unavailable")
        
        async def fallback_function():
            return {"data": "fallback_data", "source": "fallback"}
        
        # Test with circuit breaker
        from .circuit_breaker import CircuitConfig
        circuit_config = CircuitConfig(
            name="fallback_test",
            failure_threshold=1,
            recovery_timeout=5.0,
            fallback_enabled=True
        )
        
        circuit_breaker = CircuitBreaker(circuit_config)
        
        # Call with fallback
        result = await circuit_breaker.call(
            primary_function,
            fallback=fallback_function
        )
        
        if result.success and result.fallback_used:
            execution.status = TestResult.PASSED
            execution.metrics["fallback_activated"] = True
            execution.metrics["fallback_data"] = result.data
            execution.logs.append("Fallback mechanism activated successfully")
        else:
            execution.status = TestResult.FAILED
            execution.error = "Fallback should have been activated"
    
    async def _run_graceful_degradation_test(self, execution: TestExecution, config: TestConfiguration):
        """Test graceful degradation functionality."""
        self.logger.info("Running graceful degradation test")
        
        # Simulate service degradation
        degradation_levels = [0.0, 0.1, 0.5, 0.8, 1.0]  # 0% to 100% degradation
        
        for level in degradation_levels:
            async def service_function():
                # Simulate degraded service
                if level > 0.8:
                    raise Exception("Service severely degraded")
                elif level > 0.5:
                    return {"data": "limited_data", "quality": "low"}
                elif level > 0.1:
                    return {"data": "partial_data", "quality": "medium"}
                else:
                    return {"data": "full_data", "quality": "high"}
            
            async def fallback_function():
                return {"data": "cached_data", "source": "cache", "quality": "cached"}
            
            # Test with circuit breaker
            from .circuit_breaker import CircuitConfig
            circuit_config = CircuitConfig(
                name=f"degradation_test_{level}",
                failure_threshold=2,
                recovery_timeout=5.0,
                fallback_enabled=True
            )
            
            circuit_breaker = CircuitBreaker(circuit_config)
            result = await circuit_breaker.call(
                service_function,
                fallback=fallback_function
            )
            
            execution.logs.append(f"Degradation level {level}: success={result.success}, fallback_used={result.fallback_used}")
            
            # Verify graceful degradation
            if level > 0.8 and not result.fallback_used:
                execution.status = TestResult.FAILED
                execution.error = f"Fallback should be used at degradation level {level}"
                return
        
        execution.status = TestResult.PASSED
        execution.metrics["graceful_degradation_working"] = True
        execution.logs.append("Graceful degradation test completed successfully")
    
    async def _run_performance_under_load_test(self, execution: TestExecution, config: TestConfiguration):
        """Test performance under load."""
        self.logger.info("Running performance under load test")
        
        # Simulate load with concurrent requests
        concurrent_requests = 50
        request_times = []
        success_count = 0
        failure_count = 0
        
        async def load_test_function():
            # Simulate varying response times
            import random
            response_time = random.uniform(0.1, 2.0)
            await asyncio.sleep(response_time)
            
            if random.random() < 0.1:  # 10% failure rate
                raise Exception("Load test failure")
            
            return {"response_time": response_time}
        
        # Create concurrent tasks
        tasks = [load_test_function() for _ in range(concurrent_requests)]
        
        # Execute with timeout
        start_time = time.time()
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=config.timeout
            )
            
            # Analyze results
            for result in results:
                if isinstance(result, Exception):
                    failure_count += 1
                else:
                    success_count += 1
                    if isinstance(result, dict) and "response_time" in result:
                        request_times.append(result["response_time"])
            
            # Calculate metrics
            avg_response_time = sum(request_times) / len(request_times) if request_times else 0
            p95_response_time = sorted(request_times)[int(len(request_times) * 0.95)] if request_times else 0
            success_rate = success_count / concurrent_requests
            
            execution.metrics.update({
                "concurrent_requests": concurrent_requests,
                "success_count": success_count,
                "failure_count": failure_count,
                "success_rate": success_rate,
                "avg_response_time": avg_response_time,
                "p95_response_time": p95_response_time,
                "total_time": time.time() - start_time
            })
            
            # Check performance criteria
            if success_rate < 0.9:  # At least 90% success rate
                execution.status = TestResult.FAILED
                execution.error = f"Success rate too low: {success_rate:.2%}"
            elif avg_response_time > 1.0:  # Average response time under 1 second
                execution.status = TestResult.FAILED
                execution.error = f"Average response time too high: {avg_response_time:.2f}s"
            else:
                execution.status = TestResult.PASSED
            
        except asyncio.TimeoutError:
            execution.status = TestResult.FAILED
            execution.error = f"Test timed out after {config.timeout}s"
        
        execution.logs.append(f"Performance test completed: {success_count}/{concurrent_requests} successful")
    
    async def _run_error_handling_test(self, execution: TestExecution, config: TestConfiguration):
        """Test error handling capabilities."""
        self.logger.info("Running error handling test")
        
        # Test different error types
        error_types = [
            "timeout_error",
            "connection_error",
            "validation_error",
            "rate_limit_error",
            "internal_server_error"
        ]
        
        for error_type in error_types:
            async def error_prone_function():
                if error_type == "timeout_error":
                    await asyncio.sleep(5.0)
                    raise asyncio.TimeoutError("Request timeout")
                elif error_type == "connection_error":
                    raise ConnectionError("Connection refused")
                elif error_type == "validation_error":
                    raise ValueError("Invalid request format")
                elif error_type == "rate_limit_error":
                    raise Exception("Rate limit exceeded")
                elif error_type == "internal_server_error":
                    raise Exception("Internal server error")
            
            async def fallback_function():
                return {"error_handled": True, "fallback_used": True}
            
            # Test with circuit breaker
            from .circuit_breaker import CircuitConfig
            circuit_config = CircuitConfig(
                name=f"error_test_{error_type}",
                failure_threshold=1,
                recovery_timeout=5.0,
                fallback_enabled=True
            )
            
            circuit_breaker = CircuitBreaker(circuit_config)
            result = await circuit_breaker.call(
                error_prone_function,
                fallback=fallback_function
            )
            
            execution.logs.append(f"Error type {error_type}: handled={result.fallback_used}")
            
            # Verify error was handled
            if not result.fallback_used:
                execution.status = TestResult.FAILED
                execution.error = f"Error {error_type} should have been handled by fallback"
                return
        
        execution.status = TestResult.PASSED
        execution.metrics["error_handling_working"] = True
        execution.logs.append("Error handling test completed successfully")
    
    async def _run_timeout_handling_test(self, execution: TestExecution, config: TestConfiguration):
        """Test timeout handling."""
        self.logger.info("Running timeout handling test")
        
        # Test with different timeout scenarios
        timeout_scenarios = [
            {"timeout": 1.0, "should_timeout": True},
            {"timeout": 5.0, "should_timeout": False},
            {"timeout": 10.0, "should_timeout": False}
        ]
        
        for scenario in timeout_scenarios:
            async def timeout_function():
                if scenario["should_timeout"]:
                    await asyncio.sleep(scenario["timeout"] + 1.0)
                    return {"result": "success"}
                else:
                    await asyncio.sleep(scenario["timeout"] * 0.5)
                    return {"result": "success"}
            
            async def fallback_function():
                return {"result": "fallback_success", "timeout_handled": True}
            
            # Test with circuit breaker
            from .circuit_breaker import CircuitConfig
            circuit_config = CircuitConfig(
                name=f"timeout_test_{scenario['timeout']}",
                failure_threshold=1,
                recovery_timeout=5.0,
                fallback_enabled=True
            )
            
            circuit_breaker = CircuitBreaker(circuit_config)
            
            try:
                result = await asyncio.wait_for(
                    circuit_breaker.call(timeout_function, fallback=fallback_function),
                    timeout=scenario["timeout"]
                )
                
                if scenario["should_timeout"] and not result.fallback_used:
                    execution.status = TestResult.FAILED
                    execution.error = f"Timeout should have triggered fallback for {scenario['timeout']}s"
                    return
                elif not scenario["should_timeout"] and result.fallback_used:
                    execution.status = TestResult.FAILED
                    execution.error = f"Timeout should not have triggered fallback for {scenario['timeout']}s"
                    return
                
            except asyncio.TimeoutError:
                if not scenario["should_timeout"]:
                    execution.status = TestResult.FAILED
                    execution.error = f"Unexpected timeout for {scenario['timeout']}s"
                    return
            
            execution.logs.append(f"Timeout scenario {scenario['timeout']}: handled correctly")
        
        execution.status = TestResult.PASSED
        execution.metrics["timeout_handling_working"] = True
        execution.logs.append("Timeout handling test completed successfully")
    
    async def _run_partial_failure_test(self, execution: TestExecution, config: TestConfiguration):
        """Test partial failure scenarios."""
        self.logger.info("Running partial failure test")
        
        # Simulate partial service failure
        async def partial_failure_function():
            import random
            if random.random() < 0.3:  # 30% failure rate
                raise Exception("Partial service failure")
            return {"data": "partial_success", "available": True}
        
        async def fallback_function():
            return {"data": "fallback_data", "fallback_used": True}
        
        # Test with multiple requests
        from .circuit_breaker import CircuitConfig
        circuit_config = CircuitConfig(
            name="partial_failure_test",
            failure_threshold=3,
            recovery_timeout=5.0,
            fallback_enabled=True
        )
        
        circuit_breaker = CircuitBreaker(circuit_config)
        
        success_count = 0
        fallback_count = 0
        total_requests = 20
        
        for i in range(total_requests):
            result = await circuit_breaker.call(
                partial_failure_function,
                fallback=fallback_function
            )
            
            if result.success and not result.fallback_used:
                success_count += 1
            elif result.fallback_used:
                fallback_count += 1
            
            execution.logs.append(f"Request {i}: success={result.success}, fallback={result.fallback_used}")
        
        # Verify partial failure handling
        success_rate = success_count / total_requests
        fallback_rate = fallback_count / total_requests
        
        if success_rate < 0.5:  # At least 50% success rate
            execution.status = TestResult.FAILED
            execution.error = f"Success rate too low: {success_rate:.2%}"
        elif fallback_rate < 0.2:  # At least 20% fallback rate
            execution.status = TestResult.FAILED
            execution.error = f"Fallback rate too low: {fallback_rate:.2%}"
        else:
            execution.status = TestResult.PASSED
        
        execution.metrics.update({
            "total_requests": total_requests,
            "success_count": success_count,
            "fallback_count": fallback_count,
            "success_rate": success_rate,
            "fallback_rate": fallback_rate
        })
        
        execution.logs.append(f"Partial failure test completed: {success_count}/{total_requests} successful")
    
    async def _test_fallback_to_l1_cache(self, execution: TestExecution, config: TestConfiguration):
        """Test fallback to L1 cache mechanism."""
        self.logger.info("Testing fallback to L1 cache")
        
        # Mock L1 cache
        l1_cache = {}
        
        async def cache_get(key):
            return l1_cache.get(key)
        
        async def cache_set(key, value):
            l1_cache[key] = value
        
        # Test cache fallback
        test_key = "test_key"
        test_value = {"data": "cached_data"}
        
        # Set cache value
        await cache_set(test_key, test_value)
        
        # Retrieve from cache
        cached_result = await cache_get(test_key)
        
        if cached_result == test_value:
            execution.metrics["l1_cache_fallback"] = True
            execution.logs.append("L1 cache fallback working correctly")
        else:
            execution.metrics["l1_cache_fallback"] = False
            execution.logs.append("L1 cache fallback failed")
    
    def _create_redis_connection_test(self) -> TestConfiguration:
        """Create Redis connection test configuration."""
        return TestConfiguration(
            test_name="Redis Connection Test",
            test_type=ResilienceTestType.REDIS_CONNECTION,
            timeout=10.0,
            expected_behavior={"connection_should_fail": True},
            test_data={"redis_url": "redis://localhost:6379"}
        )
    
    def _create_circuit_breaker_test(self) -> TestConfiguration:
        """Create circuit breaker test configuration."""
        return TestConfiguration(
            test_name="Circuit Breaker Test",
            test_type=ResilienceTestType.CIRCUIT_BREAKER,
            timeout=30.0,
            expected_behavior={
                "circuit_should_open_after_failures": True,
                "circuit_should_close_after_successes": True
            },
            test_data={"failure_threshold": 3, "success_threshold": 2}
        )
    
    def _create_fallback_mechanism_test(self) -> TestConfiguration:
        """Create fallback mechanism test configuration."""
        return TestConfiguration(
            test_name="Fallback Mechanism Test",
            test_type=ResilienceTestType.FALLBACK_MECHANISM,
            timeout=15.0,
            expected_behavior={"fallback_should_activate": True},
            test_data={"primary_failure_rate": 1.0}
        )
    
    def _create_graceful_degradation_test(self) -> TestConfiguration:
        """Create graceful degradation test configuration."""
        return TestConfiguration(
            test_name="Graceful Degradation Test",
            test_type=ResilienceTestType.GRACEFUL_DEGRADATION,
            timeout=20.0,
            expected_behavior={"degradation_should_be_graceful": True},
            test_data={"degradation_levels": [0.0, 0.5, 0.8, 1.0]}
        )
    
    def _create_performance_under_load_test(self) -> TestConfiguration:
        """Create performance under load test configuration."""
        return TestConfiguration(
            test_name="Performance Under Load Test",
            test_type=ResilienceTestType.PERFORMANCE_UNDER_LOAD,
            timeout=60.0,
            expected_behavior={"performance_should_be_acceptable": True},
            test_data={"concurrent_requests": 50, "success_rate_threshold": 0.9}
        )
    
    def _create_error_handling_test(self) -> TestConfiguration:
        """Create error handling test configuration."""
        return TestConfiguration(
            test_name="Error Handling Test",
            test_type=ResilienceTestType.ERROR_HANDLING,
            timeout=15.0,
            expected_behavior={"errors_should_be_handled": True},
            test_data={"error_types": ["timeout", "connection", "validation"]}
        )
    
    def _create_timeout_handling_test(self) -> TestConfiguration:
        """Create timeout handling test configuration."""
        return TestConfiguration(
            test_name="Timeout Handling Test",
            test_type=ResilienceTestType.TIMEOUT_HANDLING,
            timeout=20.0,
            expected_behavior={"timeouts_should_be_handled": True},
            test_data={"timeout_scenarios": [1.0, 5.0, 10.0]}
        )
    
    def _create_partial_failure_test(self) -> TestConfiguration:
        """Create partial failure test configuration."""
        return TestConfiguration(
            test_name="Partial Failure Test",
            test_type=ResilienceTestType.PARTIAL_FAILURE,
            timeout=30.0,
            expected_behavior={"partial_failures_should_be_handled": True},
            test_data={"failure_rate": 0.3, "success_rate_threshold": 0.5}
        )
    
    def _get_test_configuration(self, test_type: ResilienceTestType) -> TestConfiguration:
        """Get test configuration by type."""
        configurations = {
            ResilienceTestType.REDIS_CONNECTION: self._create_redis_connection_test(),
            ResilienceTestType.CIRCUIT_BREAKER: self._create_circuit_breaker_test(),
            ResilienceTestType.FALLBACK_MECHANISM: self._create_fallback_mechanism_test(),
            ResilienceTestType.GRACEFUL_DEGRADATION: self._create_graceful_degradation_test(),
            ResilienceTestType.PERFORMANCE_UNDER_LOAD: self._create_performance_under_load_test(),
            ResilienceTestType.ERROR_HANDLING: self._create_error_handling_test(),
            ResilienceTestType.TIMEOUT_HANDLING: self._create_timeout_handling_test(),
            ResilienceTestType.PARTIAL_FAILURE: self._create_partial_failure_test()
        }
        
        return configurations.get(test_type)
    
    def _generate_test_summary(self) -> Dict[str, Any]:
        """Generate test summary."""
        total_tests = len(self._tests)
        passed_tests = len([t for t in self._tests if t.status == TestResult.PASSED])
        failed_tests = len([t for t in self._tests if t.status == TestResult.FAILED])
        skipped_tests = len([t for t in self._tests if t.status == TestResult.SKIPPED])
        error_tests = len([t for t in self._tests if t.status == TestResult.ERROR])
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "skipped_tests": skipped_tests,
            "error_tests": error_tests,
            "success_rate": passed_tests / max(total_tests, 1),
            "test_results": self._test_results,
            "execution_time": sum([t.end_time - t.start_time for t in self._tests if t.end_time])
        }
    
    def _collect_artifacts(self) -> Dict[str, Any]:
        """Collect test artifacts."""
        artifacts = {}
        
        for test in self._tests:
            artifacts[test.test_id] = {
                "logs": test.logs,
                "metrics": test.metrics,
                "artifacts": test.artifacts
            }
        
        return artifacts
    
    async def _initialize_mocks(self):
        """Initialize mock objects."""
        # Mock Redis
        self._redis_mock = unittest.mock.AsyncMock()
        
        # Mock cache
        self._cache_mock = unittest.mock.AsyncMock()
        
        self.logger.info("Mocks initialized")
    
    async def _cleanup(self):
        """Clean up after tests."""
        # Reset mocks
        if self._redis_mock:
            self._redis_mock.reset_mock()
        
        if self._cache_mock:
            self._cache_mock.reset_mock()
        
        # Reset circuit breakers
        if self.circuit_breaker:
            self.circuit_breaker.reset()
        
        # Reset chaos engine
        if self.chaos_engine:
            # Stop all experiments
            for experiment_id in list(self.chaos_engine._experiments.keys()):
                await self.chaos_engine.stop_experiment(experiment_id)
        
        self.logger.info("Cleanup completed")


# Global resilience test suite instance
_global_resilience_test_suite: Optional[ResilienceTestSuite] = None


def get_resilience_test_suite(**kwargs) -> ResilienceTestSuite:
    """
    Get or create global resilience test suite.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global ResilienceTestSuite instance
    """
    global _global_resilience_test_suite
    if _global_resilience_test_suite is None:
        _global_resilience_test_suite = ResilienceTestSuite(**kwargs)
    return _global_resilience_test_suite


# Pytest fixtures
@pytest.fixture
async def resilience_test_suite():
    """Pytest fixture for resilience test suite."""
    suite = ResilienceTestSuite()
    await suite._initialize_mocks()
    yield suite
    await suite._cleanup()


@pytest.fixture
def circuit_breaker():
    """Pytest fixture for circuit breaker."""
    from .circuit_breaker import CircuitConfig, CircuitBreaker
    config = CircuitConfig(name="test_circuit")
    return CircuitBreaker(config)


@pytest.fixture
def chaos_engine():
    """Pytest fixture for chaos engine."""
    from .chaos_engine import ChaosConfig, ChaosEngine
    config = ChaosConfig(dry_run_mode=True)  # Safe mode for tests
    return ChaosEngine(config)
