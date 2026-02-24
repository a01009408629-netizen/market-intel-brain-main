"""
AI Integration Middleware Layer

Enterprise-grade middleware components for AI-ready endpoints,
data quality validation, vector database abstraction, and cost optimization.
"""

from .endpoints import (
    AIEndpointsRouter,
    get_ai_endpoints_router
)

from .data_quality_gateway import (
    DataQualityGateway,
    ValidationResult,
    QualityLevel,
    get_data_quality_gateway
)

from .vector_cache import (
    IVectorStorage,
    VectorStorageConfig,
    EmbeddingMetadata,
    SimilaritySearchResult,
    VectorStorageFactory,
    get_vector_storage
)

from .performance_optimization import (
    HotVectorCache,
    OptimizedVectorStorage,
    CacheStrategy,
    get_optimized_vector_storage
)

from .dead_letter_queue import (
    DeadLetterQueue,
    DLQEntry,
    DLQStatus,
    ReprocessingStrategy,
    get_dead_letter_queue
)

from .cost_optimization import (
    CostOptimizer,
    VendorCostProfile,
    LLMCostProfile,
    CostOptimizationStrategy,
    get_cost_optimizer
)

__all__ = [
    # AI Endpoints
    "AIEndpointsRouter",
    "get_ai_endpoints_router",
    
    # Data Quality Gateway
    "DataQualityGateway",
    "ValidationResult",
    "QualityLevel",
    "get_data_quality_gateway",
    
    # Vector Cache
    "IVectorStorage",
    "VectorStorageConfig",
    "EmbeddingMetadata",
    "SimilaritySearchResult",
    "VectorStorageFactory",
    "get_vector_storage",
    
    # Performance Optimization
    "HotVectorCache",
    "OptimizedVectorStorage",
    "CacheStrategy",
    "get_optimized_vector_storage",
    
    # Dead Letter Queue
    "DeadLetterQueue",
    "DLQEntry",
    "DLQStatus",
    "ReprocessingStrategy",
    "get_dead_letter_queue",
    
    # Cost Optimization
    "CostOptimizer",
    "VendorCostProfile",
    "LLMCostProfile",
    "CostOptimizationStrategy",
    "get_cost_optimizer"
]
