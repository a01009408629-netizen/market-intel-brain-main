"""
Financial Operations (FinOps) - Budget Firewall

This module provides a budget firewall system for API cost management
using Redis token bucket algorithm for rate limiting and cost control.
"""

from .budget_firewall import BudgetFirewall, get_firewall
from .token_bucket import TokenBucket, RedisTokenBucket
from .cost_calculator import CostCalculator, get_calculator
from .exceptions import (
    BudgetExceededException,
    InsufficientTokensError,
    ConfigurationError,
    BudgetFirewallError
)

__all__ = [
    # Core classes
    'BudgetFirewall',
    'TokenBucket',
    'RedisTokenBucket',
    'CostCalculator',
    
    # Convenience functions
    'get_firewall',
    'get_calculator',
    
    # Exceptions
    'BudgetExceededException',
    'InsufficientTokensError',
    'ConfigurationError',
    'BudgetFirewallError'
]

# Global instances
_global_firewall = None
_global_calculator = None


def get_global_firewall(**kwargs) -> BudgetFirewall:
    """Get or create the global budget firewall."""
    global _global_firewall
    if _global_firewall is None:
        _global_firewall = BudgetFirewall(**kwargs)
    return _global_firewall


def get_global_calculator(**kwargs) -> CostCalculator:
    """Get or create the global cost calculator."""
    global _global_calculator
    if _global_calculator is None:
        _global_calculator = CostCalculator(**kwargs)
    return _global_calculator
