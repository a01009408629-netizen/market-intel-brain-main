"""
Budget Firewall Exceptions

Custom exceptions for the budget firewall system.
"""


class BudgetFirewallError(Exception):
    """Base exception for all budget firewall errors."""
    
    def __init__(self, message: str, provider: str = None, user_id: str = None):
        super().__init__(message)
        self.provider = provider
        self.user_id = user_id
        self.message = message


class BudgetExceededException(BudgetFirewallError):
    """Raised when budget limit is exceeded."""
    
    def __init__(
        self,
        provider: str,
        user_id: str,
        requested_cost: float,
        available_budget: float,
        reset_time: float = None
    ):
        message = (
            f"Budget exceeded for provider '{provider}' and user '{user_id}': "
            f"requested {requested_cost:.6f}, available {available_budget:.6f}"
        )
        super().__init__(message, provider, user_id)
        self.requested_cost = requested_cost
        self.available_budget = available_budget
        self.reset_time = reset_time


class InsufficientTokensError(BudgetFirewallError):
    """Raised when insufficient tokens are available."""
    
    def __init__(
        self,
        provider: str,
        user_id: str,
        tokens_requested: int,
        tokens_available: int,
        refill_rate: float
    ):
        message = (
            f"Insufficient tokens for provider '{provider}' and user '{user_id}': "
            f"requested {tokens_requested}, available {tokens_available}, "
            f"refill rate {refill_rate:.2f}/s"
        )
        super().__init__(message, provider, user_id)
        self.tokens_requested = tokens_requested
        self.tokens_available = tokens_available
        self.refill_rate = refill_rate


class ConfigurationError(BudgetFirewallError):
    """Raised when budget firewall configuration is invalid."""
    
    def __init__(self, parameter: str, value: any, reason: str = None):
        message = f"Invalid configuration for '{parameter}': {value}"
        if reason:
            message += f" ({reason})"
        super().__init__(message)
        self.parameter = parameter
        self.value = value
        self.reason = reason


class RedisConnectionError(BudgetFirewallError):
    """Raised when Redis connection fails."""
    
    def __init__(self, message: str, redis_url: str = None):
        super().__init__(message)
        self.redis_url = redis_url
        self.message = message


class TokenBucketError(BudgetFirewallError):
    """Raised when token bucket operations fail."""
    
    def __init__(self, message: str, bucket_key: str = None):
        super().__init__(message)
        self.bucket_key = bucket_key
        self.message = message


class CostCalculationError(BudgetFirewallError):
    """Raised when cost calculation fails."""
    
    def __init__(self, message: str, operation: str = None):
        super().__init__(message)
        self.operation = operation
        self.message = message


class RateLimitError(BudgetFirewallError):
    """Raised when rate limit is exceeded."""
    
    def __init__(
        self,
        provider: str,
        user_id: str,
        current_rate: float,
        limit_rate: float,
        retry_after: float
    ):
        message = (
            f"Rate limit exceeded for provider '{provider}' and user '{user_id}': "
            f"current {current_rate:.2f}/s, limit {limit_rate:.2f}/s, "
            f"retry after {retry_after:.1f}s"
        )
        super().__init__(message, provider, user_id)
        self.current_rate = current_rate
        self.limit_rate = limit_rate
        self.retry_after = retry_after


class BudgetResetError(BudgetFirewallError):
    """Raised when budget reset operation fails."""
    
    def __init__(self, message: str, provider: str = None, user_id: str = None):
        super().__init__(message, provider, user_id)
        self.message = message
