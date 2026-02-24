"""
Cost Optimization Layer - Vendor Flexibility & API Cost Reduction

Enterprise-grade cost optimization for vector databases and LLM APIs
with intelligent vendor selection and real-time cost monitoring.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import defaultdict

from .vector_cache.interfaces import (
    IVectorStorage,
    VectorStorageConfig,
    StorageType,
    DistanceMetric
)
from .vector_cache.factory import VectorStorageFactory
from ..ai_data_pipeline import AIModelType, TokenUsageTracker


class CostOptimizationStrategy(Enum):
    """Cost optimization strategies."""
    MINIMUM_COST = "minimum_cost"           # Always choose cheapest option
    BALANCED = "balanced"                   # Balance cost and performance
    PERFORMANCE = "performance"              # Prioritize performance over cost
    ADAPTIVE = "adaptive"                   # Adaptive based on usage patterns


class VendorPricingTier(Enum):
    """Vendor pricing tiers."""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


@dataclass
class VendorCostProfile:
    """Cost profile for a vendor."""
    
    # Basic information
    vendor_name: str
    storage_type: StorageType
    pricing_tier: VendorPricingTier
    
    # Storage costs (per 1K vectors per month)
    storage_cost_per_1k: float
    index_cost_per_1k: float
    transfer_cost_per_gb: float
    
    # Operation costs
    query_cost_per_1k: float
    insert_cost_per_1k: float
    update_cost_per_1k: float
    delete_cost_per_1k: float
    
    # Performance characteristics
    avg_query_time_ms: float
    max_qps: int  # Queries per second
    availability_sla: float  # 99.9, 99.99, etc.
    
    # Limits and quotas
    max_vectors: Optional[int] = None
    max_storage_gb: Optional[float] = None
    max_monthly_queries: Optional[int] = None
    
    # Additional features
    supports_hybrid_search: bool = False
    supports_metadata_filtering: bool = False
    supports_real_time_updates: bool = False
    
    # Contract terms
    contract_duration_months: int = 1
    cancellation_fee: float = 0.0
    
    # Timestamps
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def calculate_monthly_cost(
        self, 
        vector_count: int, 
        queries_per_month: int,
        inserts_per_month: int,
        updates_per_month: int,
        deletes_per_month: int
    ) -> float:
        """Calculate monthly cost for given usage."""
        # Storage costs
        storage_cost = (vector_count / 1000) * self.storage_cost_per_1k
        index_cost = (vector_count / 1000) * self.index_cost_per_1k
        
        # Operation costs
        query_cost = (queries_per_month / 1000) * self.query_cost_per_1k
        insert_cost = (inserts_per_month / 1000) * self.insert_cost_per_1k
        update_cost = (updates_per_month / 1000) * self.update_cost_per_1k
        delete_cost = (deletes_per_month / 1000) * self.delete_cost_per_1k
        
        total_cost = storage_cost + index_cost + query_cost + insert_cost + update_cost + delete_cost
        
        return total_cost
    
    def calculate_performance_score(self) -> float:
        """Calculate performance score (0-100)."""
        # Normalize performance metrics
        query_score = max(0, 100 - (self.avg_query_time_ms / 10))  # 10ms = 90 points
        qps_score = min(100, (self.max_qps / 1000) * 100)  # 1000 QPS = 100 points
        availability_score = self.availability_sla  # 99.9% = 99.9 points
        
        # Weighted average
        performance_score = (query_score * 0.4 + qps_score * 0.3 + availability_score * 0.3)
        
        return performance_score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "vendor_name": self.vendor_name,
            "storage_type": self.storage_type.value,
            "pricing_tier": self.pricing_tier.value,
            "storage_cost_per_1k": self.storage_cost_per_1k,
            "index_cost_per_1k": self.index_cost_per_1k,
            "transfer_cost_per_gb": self.transfer_cost_per_gb,
            "query_cost_per_1k": self.query_cost_per_1k,
            "insert_cost_per_1k": self.insert_cost_per_1k,
            "update_cost_per_1k": self.update_cost_per_1k,
            "delete_cost_per_1k": self.delete_cost_per_1k,
            "avg_query_time_ms": self.avg_query_time_ms,
            "max_qps": self.max_qps,
            "availability_sla": self.availability_sla,
            "max_vectors": self.max_vectors,
            "max_storage_gb": self.max_storage_gb,
            "max_monthly_queries": self.max_monthly_queries,
            "supports_hybrid_search": self.supports_hybrid_search,
            "supports_metadata_filtering": self.supports_metadata_filtering,
            "supports_real_time_updates": self.supports_real_time_updates,
            "contract_duration_months": self.contract_duration_months,
            "cancellation_fee": self.cancellation_fee,
            "performance_score": self.calculate_performance_score(),
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class LLMCostProfile:
    """Cost profile for LLM models."""
    
    model_type: AIModelType
    provider: str
    pricing_tier: VendorPricingTier
    
    # Token costs (per 1K tokens)
    input_cost_per_1k: float
    output_cost_per_1k: float
    
    # Performance characteristics
    avg_response_time_ms: float
    max_tokens_per_request: int
    context_window_size: int
    
    # Quality metrics
    quality_score: float  # 0-100 based on benchmarks
    
    # Limits and quotas
    max_requests_per_minute: Optional[int] = None
    max_tokens_per_month: Optional[int] = None
    
    # Additional features
    supports_function_calling: bool = False
    supports_streaming: bool = False
    supports_vision: bool = False
    
    def calculate_request_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a single request."""
        input_cost = (input_tokens / 1000) * self.input_cost_per_1k
        output_cost = (output_tokens / 1000) * self.output_cost_per_1k
        return input_cost + output_cost
    
    def calculate_monthly_cost(
        self, 
        requests_per_month: int,
        avg_input_tokens: int,
        avg_output_tokens: int
    ) -> float:
        """Calculate monthly cost for given usage."""
        total_input_tokens = requests_per_month * avg_input_tokens
        total_output_tokens = requests_per_month * avg_output_tokens
        
        return self.calculate_request_cost(total_input_tokens, total_output_tokens)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_type": self.model_type.value,
            "provider": self.provider,
            "pricing_tier": self.pricing_tier.value,
            "input_cost_per_1k": self.input_cost_per_1k,
            "output_cost_per_1k": self.output_cost_per_1k,
            "avg_response_time_ms": self.avg_response_time_ms,
            "max_tokens_per_request": self.max_tokens_per_request,
            "context_window_size": self.context_window_size,
            "quality_score": self.quality_score,
            "max_requests_per_minute": self.max_requests_per_minute,
            "max_tokens_per_month": self.max_tokens_per_month,
            "supports_function_calling": self.supports_function_calling,
            "supports_streaming": self.supports_streaming,
            "supports_vision": self.supports_vision
        }


class CostOptimizer:
    """
    Enterprise-grade cost optimizer for vector databases and LLM APIs.
    
    Provides intelligent vendor selection, real-time cost monitoring,
    and automatic cost optimization recommendations.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("CostOptimizer")
        
        # Vendor cost profiles
        self._vendor_profiles: Dict[StorageType, List[VendorCostProfile]] = {}
        self._llm_profiles: Dict[AIModelType, List[LLMCostProfile]] = {}
        
        # Usage tracking
        self._usage_tracker: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._cost_tracker: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Optimization settings
        self.strategy = CostOptimizationStrategy.ADAPTIVE
        self.budget_limits: Dict[str, float] = {}
        self.alert_thresholds: Dict[str, float] = {}
        
        # Initialize default profiles
        self._initialize_default_profiles()
        
        self.logger.info("CostOptimizer initialized with adaptive strategy")
    
    def set_strategy(self, strategy: CostOptimizationStrategy):
        """Set cost optimization strategy."""
        self.strategy = strategy
        self.logger.info(f"Cost optimization strategy set to: {strategy.value}")
    
    def set_budget_limit(self, category: str, limit: float):
        """Set budget limit for a category."""
        self.budget_limits[category] = limit
        self.logger.info(f"Budget limit set: {category} = ${limit:.2f}")
    
    def set_alert_threshold(self, category: str, threshold: float):
        """Set alert threshold for a category."""
        self.alert_thresholds[category] = threshold
        self.logger.info(f"Alert threshold set: {category} = {threshold}%")
    
    def add_vendor_profile(self, profile: VendorCostProfile):
        """Add or update vendor cost profile."""
        if profile.storage_type not in self._vendor_profiles:
            self._vendor_profiles[profile.storage_type] = []
        
        # Remove existing profile for same vendor and tier
        self._vendor_profiles[profile.storage_type] = [
            p for p in self._vendor_profiles[profile.storage_type]
            if not (p.vendor_name == profile.vendor_name and p.pricing_tier == profile.pricing_tier)
        ]
        
        self._vendor_profiles[profile.storage_type].append(profile)
        
        self.logger.info(f"Added vendor profile: {profile.vendor_name} ({profile.storage_type.value})")
    
    def add_llm_profile(self, profile: LLMCostProfile):
        """Add or update LLM cost profile."""
        if profile.model_type not in self._llm_profiles:
            self._llm_profiles[profile.model_type] = []
        
        # Remove existing profile for same provider and tier
        self._llm_profiles[profile.model_type] = [
            p for p in self._llm_profiles[profile.model_type]
            if not (p.provider == profile.provider and p.pricing_tier == profile.pricing_tier)
        ]
        
        self._llm_profiles[profile.model_type].append(profile)
        
        self.logger.info(f"Added LLM profile: {profile.provider} ({profile.model_type.value})")
    
    def recommend_vector_storage(
        self,
        vector_count: int,
        queries_per_month: int,
        inserts_per_month: int,
        performance_requirement: str = "medium",
        budget_limit: Optional[float] = None
    ) -> List[VendorCostProfile]:
        """Recommend vector storage options based on requirements."""
        recommendations = []
        
        for storage_type, profiles in self._vendor_profiles.items():
            for profile in profiles:
                # Calculate monthly cost
                monthly_cost = profile.calculate_monthly_cost(
                    vector_count, queries_per_month, inserts_per_month, 0, 0
                )
                
                # Check budget limit
                if budget_limit and monthly_cost > budget_limit:
                    continue
                
                # Check limits
                if profile.max_vectors and vector_count > profile.max_vectors:
                    continue
                
                if profile.max_monthly_queries and queries_per_month > profile.max_monthly_queries:
                    continue
                
                # Calculate score based on strategy
                score = self._calculate_storage_score(profile, monthly_cost, performance_requirement)
                
                recommendations.append((profile, score, monthly_cost))
        
        # Sort by score (descending)
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        # Return top recommendations
        return [profile for profile, _, _ in recommendations[:5]]
    
    def recommend_llm_model(
        self,
        requests_per_month: int,
        avg_input_tokens: int,
        avg_output_tokens: int,
        quality_requirement: str = "medium",
        budget_limit: Optional[float] = None
    ) -> List[LLMCostProfile]:
        """Recommend LLM models based on requirements."""
        recommendations = []
        
        for model_type, profiles in self._llm_profiles.items():
            for profile in profiles:
                # Calculate monthly cost
                monthly_cost = profile.calculate_monthly_cost(
                    requests_per_month, avg_input_tokens, avg_output_tokens
                )
                
                # Check budget limit
                if budget_limit and monthly_cost > budget_limit:
                    continue
                
                # Check limits
                if profile.max_tokens_per_month:
                    monthly_tokens = requests_per_month * (avg_input_tokens + avg_output_tokens)
                    if monthly_tokens > profile.max_tokens_per_month:
                        continue
                
                # Calculate score based on strategy
                score = self._calculate_llm_score(profile, monthly_cost, quality_requirement)
                
                recommendations.append((profile, score, monthly_cost))
        
        # Sort by score (descending)
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        # Return top recommendations
        return [profile for profile, _, _ in recommendations[:5]]
    
    def track_usage(self, category: str, metric: str, value: float):
        """Track usage metric."""
        timestamp = datetime.now(timezone.utc)
        
        if "history" not in self._usage_tracker[category]:
            self._usage_tracker[category]["history"] = []
        
        self._usage_tracker[category]["history"].append({
            "timestamp": timestamp.isoformat(),
            "metric": metric,
            "value": value
        })
        
        # Keep only last 1000 entries
        if len(self._usage_tracker[category]["history"]) > 1000:
            self._usage_tracker[category]["history"] = self._usage_tracker[category]["history"][-1000:]
    
    def track_cost(self, category: str, cost: float, description: str = ""):
        """Track cost."""
        timestamp = datetime.now(timezone.utc)
        
        if "costs" not in self._cost_tracker[category]:
            self._cost_tracker[category]["costs"] = []
        
        self._cost_tracker[category]["costs"].append({
            "timestamp": timestamp.isoformat(),
            "cost": cost,
            "description": description
        })
        
        # Update monthly total
        current_month = timestamp.strftime("%Y-%m")
        if "monthly_totals" not in self._cost_tracker[category]:
            self._cost_tracker[category]["monthly_totals"] = {}
        
        if current_month not in self._cost_tracker[category]["monthly_totals"]:
            self._cost_tracker[category]["monthly_totals"][current_month] = 0.0
        
        self._cost_tracker[category]["monthly_totals"][current_month] += cost
        
        # Check budget limits and alerts
        self._check_budget_alerts(category, cost)
    
    def get_cost_analysis(self, category: str, months: int = 12) -> Dict[str, Any]:
        """Get cost analysis for a category."""
        if category not in self._cost_tracker:
            return {"error": "No cost data available"}
        
        cost_data = self._cost_tracker[category]
        monthly_totals = cost_data.get("monthly_totals", {})
        
        # Calculate statistics
        recent_months = sorted(monthly_totals.keys())[-months:]
        total_cost = sum(monthly_totals[month] for month in recent_months)
        avg_monthly_cost = total_cost / len(recent_months) if recent_months else 0
        
        # Find trends
        if len(recent_months) >= 2:
            last_month = monthly_totals[recent_months[-1]]
            prev_month = monthly_totals[recent_months[-2]]
            month_over_month_change = ((last_month - prev_month) / prev_month) * 100 if prev_month > 0 else 0
        else:
            month_over_month_change = 0
        
        return {
            "category": category,
            "total_cost": total_cost,
            "average_monthly_cost": avg_monthly_cost,
            "month_over_month_change": month_over_month_change,
            "budget_limit": self.budget_limits.get(category),
            "budget_utilization": (avg_monthly_cost / self.budget_limits[category] * 100) if category in self.budget_limits else None,
            "monthly_breakdown": {month: monthly_totals[month] for month in recent_months},
            "recent_costs": cost_data.get("costs", [])[-100:]  # Last 100 costs
        }
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get cost optimization recommendations."""
        recommendations = []
        
        # Analyze each category
        for category in self._cost_tracker:
            analysis = self.get_cost_analysis(category)
            
            # Budget optimization
            if analysis.get("budget_utilization", 0) > 90:
                recommendations.append({
                    "type": "budget_optimization",
                    "category": category,
                    "priority": "high",
                    "message": f"Budget utilization for {category} is {analysis['budget_utilization']:.1f}%",
                    "suggestion": "Consider upgrading to higher tier or optimizing usage"
                })
            
            # Cost trend analysis
            if analysis.get("month_over_month_change", 0) > 20:
                recommendations.append({
                    "type": "cost_trend",
                    "category": category,
                    "priority": "medium",
                    "message": f"Costs for {category} increased by {analysis['month_over_month_change']:.1f}% month-over-month",
                    "suggestion": "Review usage patterns and consider optimization"
                })
        
        return recommendations
    
    def _calculate_storage_score(
        self, 
        profile: VendorCostProfile, 
        monthly_cost: float, 
        performance_requirement: str
    ) -> float:
        """Calculate score for vector storage profile."""
        if self.strategy == CostOptimizationStrategy.MINIMUM_COST:
            # Inverse cost (lower cost = higher score)
            return 1.0 / (monthly_cost + 0.01)
        
        elif self.strategy == CostOptimizationStrategy.PERFORMANCE:
            # Performance score only
            return profile.calculate_performance_score()
        
        elif self.strategy == CostOptimizationStrategy.BALANCED:
            # Balance cost and performance (50/50)
            performance_score = profile.calculate_performance_score()
            cost_score = 1.0 / (monthly_cost + 0.01)
            return (performance_score * 0.5 + cost_score * 0.5)
        
        elif self.strategy == CostOptimizationStrategy.ADAPTIVE:
            # Adaptive based on performance requirement
            performance_score = profile.calculate_performance_score()
            cost_score = 1.0 / (monthly_cost + 0.01)
            
            if performance_requirement == "high":
                return (performance_score * 0.7 + cost_score * 0.3)
            elif performance_requirement == "low":
                return (performance_score * 0.3 + cost_score * 0.7)
            else:  # medium
                return (performance_score * 0.5 + cost_score * 0.5)
        
        return 0.0
    
    def _calculate_llm_score(
        self, 
        profile: LLMCostProfile, 
        monthly_cost: float, 
        quality_requirement: str
    ) -> float:
        """Calculate score for LLM profile."""
        if self.strategy == CostOptimizationStrategy.MINIMUM_COST:
            return 1.0 / (monthly_cost + 0.01)
        
        elif self.strategy == CostOptimizationStrategy.PERFORMANCE:
            return profile.quality_score
        
        elif self.strategy == CostOptimizationStrategy.BALANCED:
            quality_score = profile.quality_score
            cost_score = 1.0 / (monthly_cost + 0.01)
            return (quality_score * 0.5 + cost_score * 0.5)
        
        elif self.strategy == CostOptimizationStrategy.ADAPTIVE:
            quality_score = profile.quality_score
            cost_score = 1.0 / (monthly_cost + 0.01)
            
            if quality_requirement == "high":
                return (quality_score * 0.7 + cost_score * 0.3)
            elif quality_requirement == "low":
                return (quality_score * 0.3 + cost_score * 0.7)
            else:  # medium
                return (quality_score * 0.5 + cost_score * 0.5)
        
        return 0.0
    
    def _check_budget_alerts(self, category: str, cost: float):
        """Check budget alerts and log if needed."""
        if category in self.budget_limits:
            current_month = datetime.now(timezone.utc).strftime("%Y-%m")
            monthly_total = self._cost_tracker[category]["monthly_totals"].get(current_month, 0.0)
            
            budget_limit = self.budget_limits[category]
            utilization = (monthly_total / budget_limit) * 100
            
            # Check alert threshold
            alert_threshold = self.alert_thresholds.get(category, 80)
            
            if utilization >= alert_threshold:
                self.logger.warning(
                    f"⚠️ Budget Alert: {category} utilization at {utilization:.1f}% "
                    f"(${monthly_total:.2f} of ${budget_limit:.2f})"
                )
    
    def _initialize_default_profiles(self):
        """Initialize default vendor and LLM profiles."""
        
        # Vector Storage Profiles
        # Mock Storage (Free)
        self.add_vendor_profile(VendorCostProfile(
            vendor_name="Mock Storage",
            storage_type=StorageType.MOCK,
            pricing_tier=VendorPricingTier.FREE,
            storage_cost_per_1k=0.0,
            index_cost_per_1k=0.0,
            transfer_cost_per_gb=0.0,
            query_cost_per_1k=0.0,
            insert_cost_per_1k=0.0,
            update_cost_per_1k=0.0,
            delete_cost_per_1k=0.0,
            avg_query_time_ms=50,
            max_qps=100,
            availability_sla=99.0,
            supports_hybrid_search=False,
            supports_metadata_filtering=True,
            supports_real_time_updates=True
        ))
        
        # Redis (Low Cost)
        self.add_vendor_profile(VendorCostProfile(
            vendor_name="Redis",
            storage_type=StorageType.REDIS,
            pricing_tier=VendorPricingTier.BASIC,
            storage_cost_per_1k=0.001,
            index_cost_per_1k=0.0005,
            transfer_cost_per_gb=0.05,
            query_cost_per_1k=0.0001,
            insert_cost_per_1k=0.0002,
            update_cost_per_1k=0.0002,
            delete_cost_per_1k=0.0001,
            avg_query_time_ms=25,
            max_qps=1000,
            availability_sla=99.9,
            supports_hybrid_search=False,
            supports_metadata_filtering=True,
            supports_real_time_updates=True
        ))
        
        # Pinecone (Medium Cost)
        self.add_vendor_profile(VendorCostProfile(
            vendor_name="Pinecone",
            storage_type=StorageType.PINECONE,
            pricing_tier=VendorPricingTier.PROFESSIONAL,
            storage_cost_per_1k=0.70,
            index_cost_per_1k=0.35,
            transfer_cost_per_gb=0.10,
            query_cost_per_1k=0.005,
            insert_cost_per_1k=0.01,
            update_cost_per_1k=0.01,
            delete_cost_per_1k=0.005,
            avg_query_time_ms=15,
            max_qps=5000,
            availability_sla=99.9,
            supports_hybrid_search=True,
            supports_metadata_filtering=True,
            supports_real_time_updates=True
        ))
        
        # LLM Profiles
        # GPT-3.5-Turbo
        self.add_llm_profile(LLMCostProfile(
            model_type=AIModelType.GPT_3_5_TURBO,
            provider="OpenAI",
            pricing_tier=VendorPricingTier.PROFESSIONAL,
            input_cost_per_1k=0.0015,
            output_cost_per_1k=0.002,
            avg_response_time_ms=200,
            max_tokens_per_request=4096,
            context_window_size=4096,
            quality_score=85,
            max_requests_per_minute=3500,
            supports_function_calling=True,
            supports_streaming=True,
            supports_vision=False
        ))
        
        # GPT-4
        self.add_llm_profile(LLMCostProfile(
            model_type=AIModelType.GPT_4,
            provider="OpenAI",
            pricing_tier=VendorPricingTier.PROFESSIONAL,
            input_cost_per_1k=0.03,
            output_cost_per_1k=0.06,
            avg_response_time_ms=500,
            max_tokens_per_request=8192,
            context_window_size=8192,
            quality_score=95,
            max_requests_per_minute=500,
            supports_function_calling=True,
            supports_streaming=True,
            supports_vision=True
        ))
        
        # Claude
        self.add_llm_profile(LLMCostProfile(
            model_type=AIModelType.CLAUDE,
            provider="Anthropic",
            pricing_tier=VendorPricingTier.PROFESSIONAL,
            input_cost_per_1k=0.008,
            output_cost_per_1k=0.024,
            avg_response_time_ms=300,
            max_tokens_per_request=4096,
            context_window_size=4096,
            quality_score=92,
            max_requests_per_minute=1000,
            supports_function_calling=True,
            supports_streaming=True,
            supports_vision=False
        ))


# Global cost optimizer instance
_cost_optimizer: Optional[CostOptimizer] = None


def get_cost_optimizer() -> CostOptimizer:
    """Get or create global cost optimizer instance."""
    global _cost_optimizer
    if _cost_optimizer is None:
        _cost_optimizer = CostOptimizer()
    return _cost_optimizer
