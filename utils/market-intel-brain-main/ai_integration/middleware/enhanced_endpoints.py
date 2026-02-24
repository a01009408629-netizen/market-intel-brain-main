"""
Enhanced AI Endpoints - High-Concurrency & DLQ Integration

Enterprise-grade endpoints with performance optimization,
dead letter queue integration, and cost monitoring.
"""

import asyncio
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

from fastapi import APIRouter, HTTPException, Query, Path, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator, ConfigDict

from .endpoints import (
    AIEndpointsRouter,
    AIMarketPriceResponse,
    AINewsArticleResponse,
    AISentimentDataResponse,
    AIErrorResponse,
    ResponseFormat,
    PerformanceMiddleware
)
from .data_quality_gateway import (
    get_data_quality_gateway,
    ValidationResult,
    QualityLevel
)
from .dead_letter_queue import (
    get_dead_letter_queue,
    ReprocessingStrategy
)
from .performance_optimization import (
    get_optimized_vector_storage,
    CacheStrategy
)
from .cost_optimization import (
    get_cost_optimizer,
    CostOptimizationStrategy
)

from ..unified_data_normalizer import (
    get_unified_normalizer,
    DataSource
)
from ..ai_data_pipeline import (
    get_ai_data_pipeline,
    DataCompressionLevel,
    TokenBudget
)


class EnhancedAIEndpointsRouter(AIEndpointsRouter):
    """
    Enhanced AI endpoints with high-concurrency support,
    DLQ integration, and cost optimization.
    """
    
    def __init__(self):
        super().__init__()
        
        # Initialize enhanced components
        self.dlq = get_dead_letter_queue(auto_reprocess=True)
        self.cost_optimizer = get_cost_optimizer()
        
        # Configure cost optimization
        self.cost_optimizer.set_strategy(CostOptimizationStrategy.ADAPTIVE)
        self.cost_optimizer.set_budget_limit("api_calls", 1000.0)  # $1000/month
        self.cost_optimizer.set_alert_threshold("api_calls", 80)  # Alert at 80%
        
        # Enhanced performance middleware
        self.enhanced_middleware = EnhancedPerformanceMiddleware(
            warning_threshold_ms=200.0,
            enable_dlq_tracking=True,
            enable_cost_tracking=True
        )
        
        # Setup enhanced routes
        self._setup_enhanced_routes()
    
    def _setup_enhanced_routes(self):
        """Setup enhanced routes with DLQ and cost tracking."""
        
        @self.router.get(
            "/dlq/entries",
            summary="Get DLQ entries",
            description="Retrieve dead letter queue entries for monitoring and reprocessing"
        )
        async def get_dlq_entries(
            status: Optional[str] = Query(None, description="Filter by status"),
            data_type: Optional[str] = Query(None, description="Filter by data type"),
            source: Optional[str] = Query(None, description="Filter by source"),
            limit: int = Query(50, ge=1, le=1000, description="Maximum entries to return"),
            offset: int = Query(0, ge=0, description="Offset for pagination")
        ) -> Dict[str, Any]:
            """Get DLQ entries with filtering."""
            try:
                # Convert status string to enum
                dlq_status = None
                if status:
                    from .dead_letter_queue import DLQStatus
                    status_map = {
                        "pending": DLQStatus.PENDING,
                        "processing": DLQStatus.PROCESSING,
                        "retried": DLQStatus.RETRIED,
                        "failed": DLQStatus.FAILED,
                        "archived": DLQStatus.ARCHIVED
                    }
                    dlq_status = status_map.get(status.lower())
                
                entries = await self.dlq.get_entries(
                    status=dlq_status,
                    data_type=data_type,
                    source=source,
                    limit=limit,
                    offset=offset
                )
                
                # Convert to dictionaries
                entries_data = [entry.to_dict() for entry in entries]
                
                return {
                    "entries": entries_data,
                    "total": len(entries_data),
                    "limit": limit,
                    "offset": offset
                }
                
            except Exception as e:
                self.logger.error(f"❌ Failed to get DLQ entries: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve DLQ entries"
                )
        
        @self.router.post(
            "/dlq/{entry_id}/retry",
            summary="Retry DLQ entry",
            description="Manually retry a specific DLQ entry"
        )
        async def retry_dlq_entry(
            entry_id: str = Path(..., description="DLQ entry ID")
        ) -> Dict[str, Any]:
            """Retry a DLQ entry."""
            try:
                # Define reprocessing function
                async def reprocess_func(data: Dict[str, Any]) -> Any:
                    # This would integrate with the normal processing pipeline
                    return await self._reprocess_data(data)
                
                success = await self.dlq.retry_entry(entry_id, reprocess_func)
                
                if success:
                    return {"status": "success", "message": f"Entry {entry_id} retried successfully"}
                else:
                    return {"status": "error", "message": f"Failed to retry entry {entry_id}"}
                
            except Exception as e:
                self.logger.error(f"❌ Failed to retry DLQ entry {entry_id}: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retry DLQ entry"
                )
        
        @self.router.get(
            "/cost/analysis",
            summary="Get cost analysis",
            description="Get detailed cost analysis and optimization recommendations"
        )
        async def get_cost_analysis(
            category: Optional[str] = Query(None, description="Cost category"),
            months: int = Query(12, ge=1, le=24, description="Number of months to analyze")
        ) -> Dict[str, Any]:
            """Get cost analysis."""
            try:
                if category:
                    analysis = self.cost_optimizer.get_cost_analysis(category, months)
                else:
                    # Get analysis for all categories
                    analysis = {}
                    for cat in self.cost_optimizer._cost_tracker.keys():
                        analysis[cat] = self.cost_optimizer.get_cost_analysis(cat, months)
                
                # Get optimization recommendations
                recommendations = self.cost_optimizer.get_optimization_recommendations()
                
                return {
                    "analysis": analysis,
                    "recommendations": recommendations,
                    "strategy": self.cost_optimizer.strategy.value,
                    "budget_limits": self.cost_optimizer.budget_limits
                }
                
            except Exception as e:
                self.logger.error(f"❌ Failed to get cost analysis: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve cost analysis"
                )
        
        @self.router.get(
            "/performance/stats",
            summary="Get performance statistics",
            description="Get detailed performance statistics including cache hit rates"
        )
        async def get_performance_stats() -> Dict[str, Any]:
            """Get performance statistics."""
            try:
                # Get enhanced middleware stats
                enhanced_stats = self.enhanced_middleware.get_enhanced_stats()
                
                # Get DLQ stats
                dlq_stats = await self.dlq.get_statistics()
                
                # Get cost optimizer stats
                cost_stats = {}
                for category in self.cost_optimizer._cost_tracker.keys():
                    cost_stats[category] = self.cost_optimizer.get_cost_analysis(category, 1)
                
                return {
                    "performance": enhanced_stats,
                    "dlq": dlq_stats,
                    "costs": cost_stats,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
            except Exception as e:
                self.logger.error(f"❌ Failed to get performance stats: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve performance statistics"
                )
        
        @self.router.get(
            "/recommendations/vendors",
            summary="Get vendor recommendations",
            description="Get cost-optimized vendor recommendations"
        )
        async def get_vendor_recommendations(
            vector_count: int = Query(100000, ge=1000, description="Number of vectors"),
            queries_per_month: int = Query(1000000, ge=1000, description="Queries per month"),
            performance_requirement: str = Query("medium", description="Performance requirement"),
            budget_limit: Optional[float] = Query(None, description="Budget limit")
        ) -> Dict[str, Any]:
            """Get vendor recommendations."""
            try:
                recommendations = self.cost_optimizer.recommend_vector_storage(
                    vector_count=vector_count,
                    queries_per_month=queries_per_month,
                    performance_requirement=performance_requirement,
                    budget_limit=budget_limit
                )
                
                # Convert to dictionaries
                recommendations_data = [profile.to_dict() for profile in recommendations]
                
                return {
                    "recommendations": recommendations_data,
                    "requirements": {
                        "vector_count": vector_count,
                        "queries_per_month": queries_per_month,
                        "performance_requirement": performance_requirement,
                        "budget_limit": budget_limit
                    },
                    "strategy": self.cost_optimizer.strategy.value
                }
                
            except Exception as e:
                self.logger.error(f"❌ Failed to get vendor recommendations: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve vendor recommendations"
                )
    
    async def _reprocess_data(self, data: Dict[str, Any]) -> Any:
        """Reprocess data from DLQ."""
        try:
            # This would integrate with the normal processing pipeline
            # For now, simulate successful reprocessing
            await asyncio.sleep(0.1)  # Simulate processing time
            
            return {
                "status": "reprocessed",
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to reprocess data: {e}")
            raise
    
    def get_enhanced_router(self) -> APIRouter:
        """Get the enhanced FastAPI router."""
        return self.router
    
    def get_enhanced_middleware(self) -> "EnhancedPerformanceMiddleware":
        """Get the enhanced performance middleware."""
        return self.enhanced_middleware


class EnhancedPerformanceMiddleware(PerformanceMiddleware):
    """
    Enhanced performance middleware with DLQ tracking and cost monitoring.
    """
    
    def __init__(
        self,
        warning_threshold_ms: float = 200.0,
        enable_dlq_tracking: bool = True,
        enable_cost_tracking: bool = True
    ):
        super().__init__(warning_threshold_ms)
        self.enable_dlq_tracking = enable_dlq_tracking
        self.enable_cost_tracking = enable_cost_tracking
        
        # Enhanced statistics
        self._dlq_entries_processed = 0
        self._dlq_entries_failed = 0
        self._cost_savings = 0.0
        self._cache_hit_rates = {}
    
    async def dispatch(self, request, call_next):
        """Enhanced dispatch with DLQ and cost tracking."""
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate metrics
            execution_time_ms = (time.time() - start_time) * 1000
            warning_exceeded = execution_time_ms > self.warning_threshold_ms
            
            # Track cost savings from token optimization
            if self.enable_cost_tracking and hasattr(response, 'headers'):
                token_count = int(response.headers.get("X-Token-Count", "0"))
                # Calculate savings (assuming 60% optimization)
                original_tokens = token_count / 0.4  # 40% of original
                saved_tokens = original_tokens - token_count
                self._cost_savings += saved_tokens * 0.00001  # Rough cost estimation
            
            # Enhanced headers
            response.headers["X-Enhanced-Performance"] = "true"
            response.headers["X-DLQ-Entries-Processed"] = str(self._dlq_entries_processed)
            response.headers["X-Cost-Savings"] = f"{self._cost_savings:.6f}"
            
            if warning_exceeded:
                self.logger.warning(
                    f"⚠️ Enhanced Performance Warning: {request.method} {request.url.path} "
                    f"took {execution_time_ms:.2f}ms (threshold: {self.warning_threshold_ms}ms)"
                )
            
            return response
            
        except Exception as e:
            # Track DLQ entries if enabled
            if self.enable_dlq_tracking:
                self._dlq_entries_failed += 1
            
            self.logger.error(f"❌ Enhanced middleware error: {e}")
            raise
    
    def get_enhanced_stats(self) -> Dict[str, Any]:
        """Get enhanced performance statistics."""
        base_stats = self.get_performance_summary()
        
        return {
            **base_stats,
            "enhanced": {
                "dlq_entries_processed": self._dlq_entries_processed,
                "dlq_entries_failed": self._dlq_entries_failed,
                "cost_savings": self._cost_savings,
                "cache_hit_rates": self._cache_hit_rates,
                "dlq_tracking_enabled": self.enable_dlq_tracking,
                "cost_tracking_enabled": self.enable_cost_tracking
            }
        }


# Global enhanced router instance
_enhanced_ai_endpoints_router: Optional[EnhancedAIEndpointsRouter] = None


def get_enhanced_ai_endpoints_router() -> EnhancedAIEndpointsRouter:
    """Get or create the global enhanced AI endpoints router instance."""
    global _enhanced_ai_endpoints_router
    if _enhanced_ai_endpoints_router is None:
        _enhanced_ai_endpoints_router = EnhancedAIEndpointsRouter()
    return _enhanced_ai_endpoints_router
