"""
Chaos Engineering Suite

This module provides chaos engineering capabilities for testing system resilience
with circuit breaker patterns, fault injection, and graceful degradation.
"""

from .circuit_breaker import CircuitBreaker, get_circuit_breaker
from .chaos_engine import ChaosEngine, get_chaos_engine
from .resilience_tests import ResilienceTestSuite, get_resilience_test_suite
from .exceptions import ChaosError, ConfigurationError

__all__ = [
    # Core classes
    'CircuitBreaker',
    'ChaosEngine',
    'ResilienceTestSuite',
    
    # Convenience functions
    'get_circuit_breaker',
    'get_chaos_engine',
    'get_resilience_test_suite',
    
    # Exceptions
    'ChaosError',
    'ConfigurationError'
]

# Global instances
_global_circuit_breaker = None
_global_chaos_engine = None
_global_resilience_test_suite = None


def get_global_circuit_breaker(**kwargs) -> CircuitBreaker:
    """Get or create global circuit breaker."""
    global _global_circuit_breaker
    if _global_circuit_breaker is None:
        _global_circuit_breaker = CircuitBreaker(**kwargs)
    return _global_circuit_breaker


def get_global_chaos_engine(**kwargs) -> ChaosEngine:
    """Get or create global chaos engine."""
    global _global_chaos_engine
    if _global_chaos_engine is None:
        _global_chaos_engine = ChaosEngine(**kwargs)
    return _global_chaos_engine


def get_global_resilience_test_suite(**kwargs) -> ResilienceTestSuite:
    """Get or create global resilience test suite."""
    global _global_resilience_test_suite
    if _global_resilience_test_suite is None:
        _global_resilience_test_suite = ResilienceTestSuite(**kwargs)
    return _global_resilience_test_suite
