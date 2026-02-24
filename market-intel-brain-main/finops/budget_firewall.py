"""
Budget Firewall

This module provides a comprehensive budget firewall system for API cost management
using token bucket algorithm and cost calculation for financial protection.
"""

import time
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from decimal import Decimal

from .token_bucket import TokenBucket, create_token_bucket
from .cost_calculator import CostCalculator, CostBreakdown
from .exceptions import (
    BudgetExceededException,
    InsufficientTokensError,
    ConfigurationError,
    BudgetFirewallError
)


@dataclass
class BudgetConfig:
    """Configuration for budget firewall."""
    redis_url: str = "redis://localhost:6379"
    default_budget: float = 100.0  # $100 default budget
    budget_period: int = 3600  # 1 hour in seconds
    token_capacity: int = 1000
    token_refill_rate: float = 1.0  # 1 token per second
    enable_hard_limit: bool = True
    enable_soft_warnings: bool = True
    soft_limit_threshold: float = 0.8  # 80% of budget
    enable_user_budgets: bool = False
    enable_provider_budgets: bool = True
    budget_reset_strategy: str = "periodic"  # "periodic" or "manual"
    enable_cost_tracking: bool = True
    enable_rate_limiting: bool = True


@dataclass
class BudgetStatus:
    """Current budget status."""
    user_id: str
    provider: Optional[str]
    current_budget: Decimal
    total_spent: Decimal
    remaining_budget: Decimal
    budget_utilization: float
    tokens_available: int
    reset_time: Optional[float]
    is_soft_limit_exceeded: bool
    is_hard_limit_exceeded: bool


class BudgetFirewall:
    """
    Budget firewall for API cost management.
    
    This class provides comprehensive budget control using token buckets
    for rate limiting and cost calculation for financial protection.
    """
    
    def __init__(
        self,
        config: Optional[BudgetConfig] = None,
        cost_calculator: Optional[CostCalculator] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize budget firewall.
        
        Args:
            config: Budget firewall configuration
            cost_calculator: Cost calculator instance
            logger: Logger instance
        """
        self.config = config or BudgetConfig()
        self.logger = logger or logging.getLogger("BudgetFirewall")
        
        # Initialize cost calculator
        self.cost_calculator = cost_calculator or CostCalculator()
        
        # Redis client
        self._redis_client = None
        
        # Token buckets for rate limiting
        self._token_buckets: Dict[str, TokenBucket] = {}
        
        # Budget tracking
        self._user_budgets: Dict[str, Decimal] = {}
        self._provider_budgets: Dict[str, Decimal] = {}
        self._spending_tracking: Dict[str, Decimal] = {}
        
        # Statistics
        self._stats = {
            'requests_checked': 0,
            'requests_allowed': 0,
            'requests_blocked': 0,
            'budget_exceeded_events': 0,
            'tokens_consumed': 0,
            'start_time': time.time()
        }
        
        self.logger.info("BudgetFirewall initialized")
    
    async def _get_redis_client(self):
        """Get or create Redis client."""
        if self._redis_client is None:
            try:
                import redis.asyncio as redis
                self._redis_client = redis.from_url(self.config.redis_url)
                await self._redis_client.ping()
                self.logger.info(f"Connected to Redis: {self.config.redis_url}")
            except Exception as e:
                self.logger.error(f"Failed to connect to Redis: {e}")
                raise BudgetFirewallError(f"Redis connection failed: {e}")
        
        return self._redis_client
    
    async def start(self):
        """Start the budget firewall."""
        try:
            # Initialize Redis connection
            await self._get_redis_client()
            
            # Load initial budgets
            await self._load_budgets()
            
            self.logger.info("BudgetFirewall started")
            
        except Exception as e:
            self.logger.error(f"Failed to start budget firewall: {e}")
            raise BudgetFirewallError(f"Startup failed: {e}")
    
    async def stop(self):
        """Stop the budget firewall."""
        try:
            if self._redis_client:
                await self._redis_client.close()
                self._redis_client = None
            
            self.logger.info("BudgetFirewall stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping budget firewall: {e}")
    
    async def check_request(
        self,
        provider: str,
        user_id: str,
        operation: str = "default",
        request_size: Optional[int] = None,
        response_size: Optional[int] = None,
        custom_cost: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if a request is allowed based on budget and rate limits.
        
        Args:
            provider: Provider name
            user_id: User identifier
            operation: Operation type
            request_size: Request size in bytes
            response_size: Response size in bytes
            custom_cost: Custom cost override
            metadata: Additional metadata
            
        Returns:
            True if request is allowed, False otherwise
            
        Raises:
            BudgetExceededException: If budget is exceeded
            InsufficientTokensError: If rate limit is exceeded
        """
        self._stats['requests_checked'] += 1
        
        try:
            # Calculate request cost
            cost_breakdown = self.cost_calculator.calculate_request_cost(
                provider=provider,
                operation=operation,
                request_size=request_size,
                response_size=response_size,
                custom_cost=custom_cost,
                metadata=metadata
            )
            
            request_cost = float(cost_breakdown.total_cost)
            
            # Check budget limits
            await self._check_budget_limits(provider, user_id, request_cost)
            
            # Check rate limits
            if self.config.enable_rate_limiting:
                await self._check_rate_limits(provider, user_id)
            
            # Record spending
            await self._record_spending(provider, user_id, request_cost)
            
            # Consume tokens
            if self.config.enable_rate_limiting:
                await self._consume_tokens(provider, user_id)
            
            self._stats['requests_allowed'] += 1
            
            self.logger.debug(
                f"Request allowed: {provider}.{operation} for {user_id} "
                f"(cost: ${request_cost:.6f})"
            )
            
            return True
            
        except (BudgetExceededException, InsufficientTokensError):
            self._stats['requests_blocked'] += 1
            raise
        except Exception as e:
            self._stats['requests_blocked'] += 1
            self.logger.error(f"Error checking request: {e}")
            raise BudgetFirewallError(f"Request check failed: {e}")
    
    async def _check_budget_limits(
        self,
        provider: str,
        user_id: str,
        request_cost: float
    ):
        """
        Check budget limits for the request.
        
        Args:
            provider: Provider name
            user_id: User identifier
            request_cost: Cost of the request
            
        Raises:
            BudgetExceededException: If budget is exceeded
        """
        # Get current budgets
        user_budget = await self._get_user_budget(user_id)
        provider_budget = await self._get_provider_budget(provider)
        
        # Get current spending
        current_spending = await self._get_current_spending(provider, user_id)
        
        # Calculate remaining budgets
        remaining_user_budget = user_budget - current_spending
        remaining_provider_budget = provider_budget - current_spending
        
        # Check hard limits
        if self.config.enable_hard_limit:
            if remaining_user_budget < request_cost:
                reset_time = await self._get_budget_reset_time(user_id)
                raise BudgetExceededException(
                    provider=provider,
                    user_id=user_id,
                    requested_cost=request_cost,
                    available_budget=float(remaining_user_budget),
                    reset_time=reset_time
                )
            
            if remaining_provider_budget < request_cost:
                reset_time = await self._get_provider_reset_time(provider)
                raise BudgetExceededException(
                    provider=provider,
                    user_id=user_id,
                    requested_cost=request_cost,
                    available_budget=float(remaining_provider_budget),
                    reset_time=reset_time
                )
        
        # Check soft limits (warnings)
        if self.config.enable_soft_warnings:
            soft_threshold = user_budget * self.config.soft_limit_threshold
            
            if remaining_user_budget < soft_threshold:
                await self._emit_soft_limit_warning(
                    provider, user_id, remaining_user_budget, soft_threshold
                )
    
    async def _check_rate_limits(self, provider: str, user_id: str):
        """
        Check rate limits using token bucket.
        
        Args:
            provider: Provider name
            user_id: User identifier
            
        Raises:
            InsufficientTokensError: If rate limit is exceeded
        """
        bucket_key = f"rate_limit:{provider}:{user_id}"
        
        # Get or create token bucket
        if bucket_key not in self._token_buckets:
            redis_client = await self._get_redis_client()
            bucket = create_token_bucket(
                redis_client=redis_client,
                bucket_type="redis",
                bucket_key=bucket_key,
                capacity=self.config.token_capacity,
                refill_rate=self.config.token_refill_rate,
                logger=self.logger
            )
            self._token_buckets[bucket_key] = bucket
        
        # Try to consume a token
        bucket = self._token_buckets[bucket_key]
        if not await bucket.consume(1):
            available_tokens = await bucket.get_available_tokens()
            raise InsufficientTokensError(
                provider=provider,
                user_id=user_id,
                tokens_requested=1,
                tokens_available=available_tokens,
                refill_rate=self.config.token_refill_rate
            )
    
    async def _record_spending(self, provider: str, user_id: str, cost: float):
        """
        Record spending for budget tracking.
        
        Args:
            provider: Provider name
            user_id: User identifier
            cost: Cost amount
        """
        spending_key = f"spending:{provider}:{user_id}"
        current_time = time.time()
        
        try:
            redis_client = await self._get_redis_client()
            
            # Add to spending total
            await redis_client.hincrbyfloat(spending_key, "total", cost)
            await redis_client.hset(spending_key, "last_updated", current_time)
            
            # Set expiration
            await redis_client.expire(spending_key, self.config.budget_period * 2)
            
            self._stats['tokens_consumed'] += 1
            
        except Exception as e:
            self.logger.error(f"Error recording spending: {e}")
    
    async def _consume_tokens(self, provider: str, user_id: str):
        """Consume tokens for rate limiting."""
        bucket_key = f"rate_limit:{provider}:{user_id}"
        if bucket_key in self._token_buckets:
            await self._token_buckets[bucket_key].consume(1)
    
    async def _get_user_budget(self, user_id: str) -> Decimal:
        """Get budget for a user."""
        if self.config.enable_user_budgets:
            budget_key = f"budget:user:{user_id}"
            redis_client = await self._get_redis_client()
            
            budget_str = await redis_client.hget(budget_key, "amount")
            if budget_str:
                return Decimal(budget_str)
        
        return Decimal(str(self.config.default_budget))
    
    async def _get_provider_budget(self, provider: str) -> Decimal:
        """Get budget for a provider."""
        if self.config.enable_provider_budgets:
            budget_key = f"budget:provider:{provider}"
            redis_client = await self._get_redis_client()
            
            budget_str = await redis_client.hget(budget_key, "amount")
            if budget_str:
                return Decimal(budget_str)
        
        return Decimal(str(self.config.default_budget))
    
    async def _get_current_spending(self, provider: str, user_id: str) -> Decimal:
        """Get current spending for provider/user combination."""
        spending_key = f"spending:{provider}:{user_id}"
        redis_client = await self._get_redis_client()
        
        spending_str = await redis_client.hget(spending_key, "total")
        if spending_str:
            return Decimal(spending_str)
        
        return Decimal('0')
    
    async def _get_budget_reset_time(self, user_id: str) -> Optional[float]:
        """Get budget reset time for a user."""
        if self.config.budget_reset_strategy == "periodic":
            # Calculate next reset time based on period
            current_time = time.time()
            period_start = int(current_time // self.config.budget_period) * self.config.budget_period
            next_reset = period_start + self.config.budget_period
            return next_reset
        
        return None
    
    async def _get_provider_reset_time(self, provider: str) -> Optional[float]:
        """Get budget reset time for a provider."""
        if self.config.budget_reset_strategy == "periodic":
            current_time = time.time()
            period_start = int(current_time // self.config.budget_period) * self.config.budget_period
            next_reset = period_start + self.config.budget_period
            return next_reset
        
        return None
    
    async def _emit_soft_limit_warning(
        self,
        provider: str,
        user_id: str,
        remaining_budget: Decimal,
        soft_threshold: Decimal
    ):
        """Emit soft limit warning."""
        self.logger.warning(
            f"Soft budget limit exceeded for {provider}:{user_id}: "
            f"remaining ${remaining_budget:.6f} (threshold: ${soft_threshold:.6f})"
        )
        
        # Could integrate with alerting system here
        # await alert_system.send_warning(...)
    
    async def _load_budgets(self):
        """Load initial budgets from Redis."""
        try:
            redis_client = await self._get_redis_client()
            
            # Load user budgets if enabled
            if self.config.enable_user_budgets:
                user_budget_keys = await redis_client.keys("budget:user:*")
                for key in user_budget_keys:
                    user_id = key.split(":")[-1]
                    budget_str = await redis_client.hget(key, "amount")
                    if budget_str:
                        self._user_budgets[user_id] = Decimal(budget_str)
            
            # Load provider budgets if enabled
            if self.config.enable_provider_budgets:
                provider_budget_keys = await redis_client.keys("budget:provider:*")
                for key in provider_budget_keys:
                    provider = key.split(":")[-1]
                    budget_str = await redis_client.hget(key, "amount")
                    if budget_str:
                        self._provider_budgets[provider] = Decimal(budget_str)
            
            self.logger.info(
                f"Loaded {len(self._user_budgets)} user budgets and "
                f"{len(self._provider_budgets)} provider budgets"
            )
            
        except Exception as e:
            self.logger.error(f"Error loading budgets: {e}")
    
    async def set_user_budget(self, user_id: str, budget: float):
        """
        Set budget for a specific user.
        
        Args:
            user_id: User identifier
            budget: Budget amount
        """
        if not self.config.enable_user_budgets:
            raise ConfigurationError("enable_user_budgets", False, "User budgets not enabled")
        
        try:
            redis_client = await self._get_redis_client()
            budget_key = f"budget:user:{user_id}"
            
            await redis_client.hset(budget_key, "amount", str(budget))
            await redis_client.hset(budget_key, "updated_at", time.time())
            
            self._user_budgets[user_id] = Decimal(str(budget))
            
            self.logger.info(f"Set user budget for {user_id}: ${budget:.6f}")
            
        except Exception as e:
            self.logger.error(f"Error setting user budget: {e}")
            raise BudgetFirewallError(f"Failed to set user budget: {e}")
    
    async def set_provider_budget(self, provider: str, budget: float):
        """
        Set budget for a specific provider.
        
        Args:
            provider: Provider name
            budget: Budget amount
        """
        if not self.config.enable_provider_budgets:
            raise ConfigurationError("enable_provider_budgets", False, "Provider budgets not enabled")
        
        try:
            redis_client = await self._get_redis_client()
            budget_key = f"budget:provider:{provider}"
            
            await redis_client.hset(budget_key, "amount", str(budget))
            await redis_client.hset(budget_key, "updated_at", time.time())
            
            self._provider_budgets[provider] = Decimal(str(budget))
            
            self.logger.info(f"Set provider budget for {provider}: ${budget:.6f}")
            
        except Exception as e:
            self.logger.error(f"Error setting provider budget: {e}")
            raise BudgetFirewallError(f"Failed to set provider budget: {e}")
    
    async def get_budget_status(
        self,
        provider: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> BudgetStatus:
        """
        Get current budget status.
        
        Args:
            provider: Filter by provider
            user_id: Filter by user
            
        Returns:
            BudgetStatus with current status
        """
        try:
            if user_id:
                # Get status for specific user
                user_budget = await self._get_user_budget(user_id)
                current_spending = Decimal('0')
                
                # Sum spending across all providers for this user
                if provider:
                    current_spending = await self._get_current_spending(provider, user_id)
                else:
                    # Sum across all providers
                    redis_client = await self._get_redis_client()
                    spending_keys = await redis_client.keys(f"spending:*:{user_id}")
                    for key in spending_keys:
                        spending_str = await redis_client.hget(key, "total")
                        if spending_str:
                            current_spending += Decimal(spending_str)
                
                remaining_budget = user_budget - current_spending
                utilization = float(current_spending / user_budget) if user_budget > 0 else 0
                
                reset_time = await self._get_budget_reset_time(user_id)
                
                return BudgetStatus(
                    user_id=user_id,
                    provider=provider,
                    current_budget=user_budget,
                    total_spent=current_spending,
                    remaining_budget=remaining_budget,
                    budget_utilization=utilization,
                    tokens_available=0,  # Not applicable for budget status
                    reset_time=reset_time,
                    is_soft_limit_exceeded=utilization > self.config.soft_limit_threshold,
                    is_hard_limit_exceeded=remaining_budget < 0
                )
            
            elif provider:
                # Get status for specific provider
                provider_budget = await self._get_provider_budget(provider)
                current_spending = Decimal('0')
                
                # Sum spending across all users for this provider
                redis_client = await self._get_redis_client()
                spending_keys = await redis_client.keys(f"spending:{provider}:*")
                for key in spending_keys:
                    spending_str = await redis_client.hget(key, "total")
                    if spending_str:
                        current_spending += Decimal(spending_str)
                
                remaining_budget = provider_budget - current_spending
                utilization = float(current_spending / provider_budget) if provider_budget > 0 else 0
                
                reset_time = await self._get_provider_reset_time(provider)
                
                return BudgetStatus(
                    user_id="all",
                    provider=provider,
                    current_budget=provider_budget,
                    total_spent=current_spending,
                    remaining_budget=remaining_budget,
                    budget_utilization=utilization,
                    tokens_available=0,
                    reset_time=reset_time,
                    is_soft_limit_exceeded=utilization > self.config.soft_limit_threshold,
                    is_hard_limit_exceeded=remaining_budget < 0
                )
            
            else:
                # Get overall status
                raise BudgetFirewallError("Must specify either provider or user_id")
                
        except Exception as e:
            self.logger.error(f"Error getting budget status: {e}")
            raise BudgetFirewallError(f"Failed to get budget status: {e}")
    
    async def reset_user_budget(self, user_id: str):
        """
        Reset budget and spending for a user.
        
        Args:
            user_id: User identifier
        """
        try:
            redis_client = await self._get_redis_client()
            
            # Reset spending
            spending_keys = await redis_client.keys(f"spending:*:{user_id}")
            for key in spending_keys:
                await redis_client.delete(key)
            
            self.logger.info(f"Reset budget and spending for user: {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error resetting user budget: {e}")
            raise BudgetFirewallError(f"Failed to reset user budget: {e}")
    
    async def reset_provider_budget(self, provider: str):
        """
        Reset budget and spending for a provider.
        
        Args:
            provider: Provider identifier
        """
        try:
            redis_client = await self._get_redis_client()
            
            # Reset spending
            spending_keys = await redis_client.keys(f"spending:{provider}:*")
            for key in spending_keys:
                await redis_client.delete(key)
            
            self.logger.info(f"Reset budget and spending for provider: {provider}")
            
        except Exception as e:
            self.logger.error(f"Error resetting provider budget: {e}")
            raise BudgetFirewallError(f"Failed to reset provider budget: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get budget firewall statistics.
        
        Returns:
            Statistics dictionary
        """
        uptime = time.time() - self._stats['start_time']
        
        return {
            'uptime': uptime,
            'requests_checked': self._stats['requests_checked'],
            'requests_allowed': self._stats['requests_allowed'],
            'requests_blocked': self._stats['requests_blocked'],
            'budget_exceeded_events': self._stats['budget_exceeded_events'],
            'tokens_consumed': self._stats['tokens_consumed'],
            'allowance_rate': (
                self._stats['requests_allowed'] / max(self._stats['requests_checked'], 1)
            ),
            'block_rate': (
                self._stats['requests_blocked'] / max(self._stats['requests_checked'], 1)
            ),
            'config': {
                'default_budget': self.config.default_budget,
                'budget_period': self.config.budget_period,
                'token_capacity': self.config.token_capacity,
                'token_refill_rate': self.config.token_refill_rate,
                'enable_hard_limit': self.config.enable_hard_limit,
                'soft_limit_threshold': self.config.soft_limit_threshold
            }
        }
    
    def get_config(self) -> BudgetConfig:
        """Get current configuration."""
        return self.config


# Global budget firewall instance
_global_firewall: Optional[BudgetFirewall] = None


def get_firewall(**kwargs) -> BudgetFirewall:
    """
    Get or create the global budget firewall.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global BudgetFirewall instance
    """
    global _global_firewall
    if _global_firewall is None:
        _global_firewall = BudgetFirewall(**kwargs)
    return _global_firewall
