"""
Cost Calculator

This module provides cost calculation functionality for API requests
with configurable cost weights and budget management.
"""

import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from decimal import Decimal, getcontext

from .exceptions import CostCalculationError, ConfigurationError


@dataclass
class CostConfig:
    """Configuration for cost calculation."""
    default_cost_per_request: float = 0.01  # $0.01 per request
    cost_weights: Dict[str, float] = None  # Provider-specific costs
    cost_per_unit: Dict[str, float] = None  # Per-unit costs (e.g., per record)
    enable_dynamic_pricing: bool = False
    currency: str = "USD"
    
    def __post_init__(self):
        """Initialize default values."""
        if self.cost_weights is None:
            self.cost_weights = {
                "default": self.default_cost_per_request,
                "finnhub": 0.01,
                "yahoo_finance": 0.005,
                "alpha_vantage": 0.02,
                "polygon": 0.015,
                "iex_cloud": 0.025
            }
        
        if self.cost_per_unit is None:
            self.cost_per_unit = {
                "record": 0.0001,  # $0.0001 per record
                "kb": 0.00001,     # $0.00001 per KB
                "api_call": 0.01    # $0.01 per API call
            }


@dataclass
class CostBreakdown:
    """Cost breakdown for a request."""
    total_cost: Decimal
    base_cost: Decimal
    weight_multiplier: Decimal
    volume_cost: Decimal
    currency: str
    calculation_details: Dict[str, Any]


class CostCalculator:
    """
    Cost calculator for API requests and operations.
    
    This class provides flexible cost calculation with support for
    provider-specific weights, volume-based costs, and dynamic pricing.
    """
    
    def __init__(
        self,
        config: Optional[CostConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize cost calculator.
        
        Args:
            config: Cost calculation configuration
            logger: Logger instance
        """
        self.config = config or CostConfig()
        self.logger = logger or logging.getLogger("CostCalculator")
        
        # Set decimal context for financial calculations
        getcontext().prec = 6  # 6 decimal places for financial accuracy
        
        self.logger.info(f"CostCalculator initialized (currency={self.config.currency})")
    
    def calculate_request_cost(
        self,
        provider: str,
        operation: str,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None,
        custom_cost: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CostBreakdown:
        """
        Calculate cost for a single request.
        
        Args:
            provider: Provider name
            operation: Operation type
            request_size: Size of request in bytes
            response_size: Size of response in bytes
            custom_cost: Custom cost override
            metadata: Additional metadata for cost calculation
            
        Returns:
            CostBreakdown with detailed cost information
        """
        try:
            # Use custom cost if provided
            if custom_cost is not None:
                base_cost = Decimal(str(custom_cost))
                weight_multiplier = Decimal('1.0')
                volume_cost = Decimal('0.0')
            else:
                # Get base cost for provider
                base_cost = Decimal(str(self._get_base_cost(provider)))
                
                # Apply weight multiplier
                weight_multiplier = Decimal(str(self._get_weight_multiplier(provider, operation)))
                
                # Calculate volume-based costs
                volume_cost = self._calculate_volume_cost(
                    provider, operation, request_size, response_size, metadata
                )
            
            # Calculate total cost
            total_cost = (base_cost * weight_multiplier) + volume_cost
            
            # Create breakdown
            breakdown = CostBreakdown(
                total_cost=total_cost,
                base_cost=base_cost,
                weight_multiplier=weight_multiplier,
                volume_cost=volume_cost,
                currency=self.config.currency,
                calculation_details={
                    "provider": provider,
                    "operation": operation,
                    "base_cost": float(base_cost),
                    "weight_multiplier": float(weight_multiplier),
                    "volume_cost": float(volume_cost),
                    "request_size": request_size,
                    "response_size": response_size,
                    "metadata": metadata or {}
                }
            )
            
            self.logger.debug(
                f"Calculated cost for {provider}.{operation}: "
                f"${total_cost:.6f} {self.config.currency}"
            )
            
            return breakdown
            
        except Exception as e:
            self.logger.error(f"Error calculating cost: {e}")
            raise CostCalculationError(f"Failed to calculate cost: {e}", operation)
    
    def calculate_batch_cost(
        self,
        requests: List[Dict[str, Any]]
    ) -> CostBreakdown:
        """
        Calculate cost for multiple requests.
        
        Args:
            requests: List of request dictionaries
            
        Returns:
            CostBreakdown with total cost for all requests
        """
        try:
            total_base_cost = Decimal('0')
            total_volume_cost = Decimal('0')
            
            calculation_details = {
                "requests": [],
                "providers": {},
                "operations": {},
                "total_requests": len(requests)
            }
            
            for i, request in enumerate(requests):
                provider = request.get('provider', 'unknown')
                operation = request.get('operation', 'unknown')
                
                # Calculate individual request cost
                request_breakdown = self.calculate_request_cost(
                    provider=provider,
                    operation=operation,
                    request_size=request.get('request_size'),
                    response_size=request.get('response_size'),
                    custom_cost=request.get('custom_cost'),
                    metadata=request.get('metadata')
                )
                
                # Accumulate costs
                total_base_cost += request_breakdown.base_cost
                total_volume_cost += request_breakdown.volume_cost
                
                # Track provider and operation stats
                if provider not in calculation_details["providers"]:
                    calculation_details["providers"][provider] = {
                        "count": 0,
                        "total_cost": Decimal('0')
                    }
                
                if operation not in calculation_details["operations"]:
                    calculation_details["operations"][operation] = {
                        "count": 0,
                        "total_cost": Decimal('0')
                    }
                
                calculation_details["providers"][provider]["count"] += 1
                calculation_details["providers"][provider]["total_cost"] += request_breakdown.total_cost
                
                calculation_details["operations"][operation]["count"] += 1
                calculation_details["operations"][operation]["total_cost"] += request_breakdown.total_cost
                
                calculation_details["requests"].append({
                    "index": i,
                    "provider": provider,
                    "operation": operation,
                    "cost": float(request_breakdown.total_cost),
                    "breakdown": request_breakdown.calculation_details
                })
            
            # Calculate total cost
            total_cost = total_base_cost + total_volume_cost
            
            return CostBreakdown(
                total_cost=total_cost,
                base_cost=total_base_cost,
                weight_multiplier=Decimal('1.0'),
                volume_cost=total_volume_cost,
                currency=self.config.currency,
                calculation_details=calculation_details
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating batch cost: {e}")
            raise CostCalculationError(f"Failed to calculate batch cost: {e}")
    
    def _get_base_cost(self, provider: str) -> float:
        """
        Get base cost for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            Base cost per request
        """
        return self.config.cost_weights.get(provider, self.config.cost_weights["default"])
    
    def _get_weight_multiplier(self, provider: str, operation: str) -> float:
        """
        Get weight multiplier for provider/operation combination.
        
        Args:
            provider: Provider name
            operation: Operation type
            
        Returns:
            Weight multiplier
        """
        # Default weight multiplier
        base_multiplier = 1.0
        
        # Operation-specific multipliers
        operation_multipliers = {
            "fetch": 1.0,
            "sync": 1.2,
            "bulk": 0.8,
            "real_time": 1.5,
            "historical": 0.7
        }
        
        # Provider-specific multipliers
        provider_multipliers = {
            "finnhub": {
                "real_time": 1.3,
                "historical": 0.6
            },
            "alpha_vantage": {
                "real_time": 1.4,
                "bulk": 0.7
            }
        }
        
        # Apply operation multiplier
        operation_multiplier = operation_multipliers.get(operation, 1.0)
        
        # Apply provider-specific multiplier if available
        if provider in provider_multipliers:
            provider_multiplier = provider_multipliers[provider].get(operation, 1.0)
            return base_multiplier * operation_multiplier * provider_multiplier
        
        return base_multiplier * operation_multiplier
    
    def _calculate_volume_cost(
        self,
        provider: str,
        operation: str,
        request_size: Optional[int],
        response_size: Optional[int],
        metadata: Optional[Dict[str, Any]]
    ) -> Decimal:
        """
        Calculate volume-based cost component.
        
        Args:
            provider: Provider name
            operation: Operation type
            request_size: Request size in bytes
            response_size: Response size in bytes
            metadata: Additional metadata
            
        Returns:
            Volume cost component
        """
        volume_cost = Decimal('0')
        
        # Calculate cost based on data volume
        if request_size is not None:
            kb_size = request_size / 1024
            cost_per_kb = self.config.cost_per_unit.get("kb", 0.00001)
            volume_cost += Decimal(str(kb_size * cost_per_kb))
        
        if response_size is not None:
            kb_size = response_size / 1024
            cost_per_kb = self.config.cost_per_unit.get("kb", 0.00001)
            volume_cost += Decimal(str(kb_size * cost_per_kb))
        
        # Calculate cost based on record count
        if metadata and "record_count" in metadata:
            record_count = metadata["record_count"]
            cost_per_record = self.config.cost_per_unit.get("record", 0.0001)
            volume_cost += Decimal(str(record_count * cost_per_record))
        
        return volume_cost
    
    def estimate_monthly_cost(
        self,
        provider: str,
        operation: str,
        requests_per_day: int,
        avg_request_size: Optional[int] = None,
        avg_response_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Estimate monthly cost for a provider/operation combination.
        
        Args:
            provider: Provider name
            operation: Operation type
            requests_per_day: Average requests per day
            avg_request_size: Average request size in bytes
            avg_response_size: Average response size in bytes
            
        Returns:
            Monthly cost estimation
        """
        try:
            # Calculate cost per request
            cost_breakdown = self.calculate_request_cost(
                provider=provider,
                operation=operation,
                request_size=avg_request_size,
                response_size=avg_response_size
            )
            
            # Calculate monthly estimates
            days_per_month = 30
            requests_per_month = requests_per_day * days_per_month
            monthly_cost = cost_breakdown.total_cost * requests_per_month
            
            return {
                "provider": provider,
                "operation": operation,
                "requests_per_day": requests_per_day,
                "requests_per_month": requests_per_month,
                "cost_per_request": float(cost_breakdown.total_cost),
                "daily_cost": float(cost_breakdown.total_cost * requests_per_day),
                "monthly_cost": float(monthly_cost),
                "currency": self.config.currency,
                "breakdown": cost_breakdown.calculation_details
            }
            
        except Exception as e:
            self.logger.error(f"Error estimating monthly cost: {e}")
            raise CostCalculationError(f"Failed to estimate monthly cost: {e}")
    
    def get_provider_costs(self) -> Dict[str, float]:
        """
        Get cost configuration for all providers.
        
        Returns:
            Dictionary of provider costs
        """
        return self.config.cost_weights.copy()
    
    def update_provider_cost(self, provider: str, cost: float):
        """
        Update cost for a specific provider.
        
        Args:
            provider: Provider name
            cost: New cost per request
        """
        if cost < 0:
            raise ConfigurationError("cost", cost, "Cost cannot be negative")
        
        self.config.cost_weights[provider] = cost
        self.logger.info(f"Updated cost for {provider}: ${cost:.6f}")
    
    def update_cost_per_unit(self, unit: str, cost: float):
        """
        Update cost per unit.
        
        Args:
            unit: Unit type (e.g., "record", "kb")
            cost: Cost per unit
        """
        if cost < 0:
            raise ConfigurationError("cost", cost, "Cost cannot be negative")
        
        self.config.cost_per_unit[unit] = cost
        self.logger.info(f"Updated cost per {unit}: ${cost:.6f}")
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """
        Get summary of cost configuration.
        
        Returns:
            Cost configuration summary
        """
        return {
            "currency": self.config.currency,
            "default_cost_per_request": self.config.default_cost_per_request,
            "provider_costs": self.config.cost_weights,
            "cost_per_unit": self.config.cost_per_unit,
            "enable_dynamic_pricing": self.config.enable_dynamic_pricing,
            "total_providers": len(self.config.cost_weights)
        }
    
    def validate_cost_configuration(self) -> List[str]:
        """
        Validate cost configuration.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check for negative costs
        for provider, cost in self.config.cost_weights.items():
            if cost < 0:
                errors.append(f"Negative cost for provider {provider}: {cost}")
        
        # Check for negative unit costs
        for unit, cost in self.config.cost_per_unit.items():
            if cost < 0:
                errors.append(f"Negative cost per {unit}: {cost}")
        
        # Check for missing default cost
        if "default" not in self.config.cost_weights:
            errors.append("Missing default cost configuration")
        
        return errors


# Global cost calculator instance
_global_calculator: Optional[CostCalculator] = None


def get_calculator(**kwargs) -> CostCalculator:
    """
    Get or create the global cost calculator.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global CostCalculator instance
    """
    global _global_calculator
    if _global_calculator is None:
        _global_calculator = CostCalculator(**kwargs)
    return _global_calculator


# Utility functions
def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Format amount as currency.
    
    Args:
        amount: Amount to format
        currency: Currency code
        
    Returns:
        Formatted currency string
    """
    return f"{currency} {amount:.6f}"


def calculate_roi(
    investment_cost: float,
    return_value: float,
    period_days: int
) -> Dict[str, float]:
    """
    Calculate Return on Investment (ROI).
    
    Args:
        investment_cost: Total investment cost
        return_value: Total return value
        period_days: Investment period in days
        
    Returns:
        ROI metrics
    """
    if investment_cost <= 0:
        return {"roi": 0.0, "annualized_roi": 0.0}
    
    roi = (return_value - investment_cost) / investment_cost
    annualized_roi = roi * (365 / period_days)
    
    return {
        "roi": roi,
        "annualized_roi": annualized_roi
    }
