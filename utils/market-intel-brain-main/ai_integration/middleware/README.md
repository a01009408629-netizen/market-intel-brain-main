# AI Integration Middleware Layer

Enterprise-grade middleware components providing AI-ready endpoints, strict data validation, and vector database abstraction.

## Overview

The middleware layer sits on top of the AI Integration Layer, providing:

1. **AI-Ready Endpoints** - REST/GraphQL APIs with zero token waste
2. **Data Quality Gateway** - Strict validation preventing dirty data
3. **Vector Cache Foundation** - Abstract layer for vector database readiness

## Directory Structure

```
ai_integration/middleware/
├── __init__.py                    # Package initialization
├── endpoints.py                   # AI-ready REST/GraphQL endpoints
├── data_quality_gateway.py         # Strict data validation layer
├── openapi_schema.py              # OpenAPI 3.0 specification
├── vector_cache/                  # Vector database abstraction
│   ├── __init__.py               # Vector cache package init
│   ├── interfaces.py              # Abstract interfaces
│   ├── factory.py                # Dependency injection container
│   └── mock_storage.py           # Reference implementation
└── README.md                     # This file
```

## Components

### 1. AI-Ready Endpoints (`endpoints.py`)

Enterprise-grade REST endpoints with strict performance requirements:

#### Key Features:
- **Zero Token Waste**: Ultra-optimized response formats with shortened field names
- **Performance Monitoring**: <200ms execution threshold with automatic warnings
- **Strict Validation**: Input validation with comprehensive error handling
- **Token Tracking**: Real-time token usage monitoring and cost estimation

#### Endpoints:
- `GET /api/v2/ai/normalized/market/{source}/{symbol}` - AI-ready market data
- `GET /api/v2/ai/normalized/news/{source}` - AI-ready news articles
- `GET /api/v2/ai/normalized/sentiment/{source}` - AI-ready sentiment data
- `GET /api/v2/ai/health` - Health check with performance metrics

#### Response Optimization:
```json
{
  "s": "BTCUSDT",           // symbol (shortened)
  "p": 15025.50,            // price (shortened)
  "c": 125.75,              // change (shortened)
  "cp": 0.84,               // change_percent (shortened)
  "v": 1542000000.0,        // volume (shortened)
  "ms": "open",              // market_status (shortened)
  "cur": "USDT",             // currency (shortened)
  "conf": 0.95,             // confidence (shortened)
  "ts": "2024-02-22T10:30:00Z"  // timestamp (shortened)
}
```

### 2. Data Quality Gateway (`data_quality_gateway.py`)

Strict schema validation layer ensuring AI engine never receives dirty data:

#### Validation Levels:
- **HIGH**: Excellent quality, ready for AI
- **MEDIUM**: Acceptable quality, minor issues
- **LOW**: Poor quality, use with caution
- **REJECTED**: Unusable quality, reject completely

#### Validation Features:
- **Field Validation**: Type checking, range validation, format validation
- **Consistency Checks**: Sentiment score vs label consistency
- **Quality Scoring**: Automatic quality assessment
- **Error Classification**: INFO, WARNING, ERROR, CRITICAL severity levels

#### Example Usage:
```python
from ai_integration.middleware import get_data_quality_gateway

gateway = get_data_quality_gateway()
result = await gateway.validate_market_price(ai_data)

if result.quality_level == QualityLevel.REJECTED:
    logger.error(f"Data rejected: {result.errors}")
elif result.quality_level == QualityLevel.LOW:
    logger.warning(f"Low quality data: {result.errors}")
```

### 3. Vector Cache Foundation (`vector_cache/`)

Abstract layer for vector database readiness with vendor flexibility:

#### Interfaces (`interfaces.py`):
- **IVectorStorage**: Abstract vector storage interface
- **IEmbeddingGenerator**: Abstract embedding generation interface
- **VectorStorageManager**: Enterprise-grade manager with DI

#### Factory Pattern (`factory.py`):
- **Vendor Flexibility**: Support for multiple vector databases
- **Cost Control**: Built-in cost estimation and comparison
- **Dependency Injection**: Clean architecture with factory pattern

#### Supported Storage Types:
- **MOCK**: Free reference implementation
- **REDIS**: Low-cost self-hosted option
- **PINECONE**: Managed high-performance option
- **CHROMA**: Open-source option
- **WEAVIATE**: Managed semantic search
- **QDRANT**: High-performance with self-hosting
- **MILVUS**: Open-source enterprise option

#### Example Usage:
```python
from ai_integration.middleware.vector_cache import get_vector_storage, StorageType

# Get mock storage for testing
storage = get_vector_storage()

# Create with specific configuration
from ai_integration.middleware.vector_cache import VectorStorageConfig, StorageType
config = VectorStorageConfig(
    storage_type=StorageType.REDIS,
    dimension=1536,
    host="localhost",
    port=6379
)
storage = get_vector_storage(config)

# Perform similarity search
from ai_integration.middleware.vector_cache import SearchQuery
query = SearchQuery(
    query_vector=[0.1, 0.2, 0.3, ...],
    top_k=10,
    threshold=0.7
)
results = await storage.similarity_search(query)
```

## Performance Requirements

### Endpoint Performance:
- **Max Response Time**: 200ms
- **Warning Threshold**: 200ms (logged as warning)
- **Token Optimization**: 60-80% reduction
- **Data Quality**: Minimum MEDIUM quality

### Validation Performance:
- **Market Price Validation**: <5ms
- **News Article Validation**: <8ms
- **Sentiment Data Validation**: <6ms
- **Batch Validation**: <50ms for 100 items

### Vector Storage Performance:
- **Insertion**: <10ms per embedding
- **Search**: <50ms for top-10 results
- **Batch Operations**: <1s for 1000 embeddings

## API Schema

The complete OpenAPI 3.0 specification is available in `openapi_schema.py`:

### Key Schema Features:
- **Strict Validation**: All parameters validated
- **Token Optimization**: Response schemas optimized for minimal tokens
- **Error Handling**: Comprehensive error responses
- **Security**: JWT and API key authentication
- **Documentation**: Complete API documentation

### Schema Statistics:
- **API Version**: 2.0.0
- **Endpoints**: 4 main endpoints
- **Schemas**: 5 response schemas
- **Security Schemes**: 2 (JWT, API Key)
- **Tags**: 1 (AI Integration)

## Integration Examples

### FastAPI Integration:
```python
from fastapi import FastAPI
from ai_integration.middleware import get_ai_endpoints_router

app = FastAPI(title="Market Intel Brain AI API")
ai_router = get_ai_endpoints_router()

# Add AI endpoints
app.include_router(ai_router.get_router())

# Add performance middleware
app.add_middleware(ai_router.performance_middleware)
```

### Data Quality Integration:
```python
from ai_integration.middleware import get_data_quality_gateway

gateway = get_data_quality_gateway()

# Validate before AI processing
async def process_ai_data(data):
    validation = await gateway.validate_market_price(data)
    
    if validation.is_valid:
        # Process with AI
        return await ai_model.process(data)
    else:
        # Handle validation errors
        raise ValidationError(validation.errors)
```

### Vector Storage Integration:
```python
from ai_integration.middleware.vector_cache import (
    get_vector_storage_di, 
    VectorStorageConfig,
    StorageType
)

# Configure dependency injection
di = get_vector_storage_di()
di.set_default_config(VectorStorageConfig(
    storage_type=StorageType.MOCK,
    dimension=1536
))

# Use in services
storage = await di.get_storage()
await storage.insert_embedding(vector, metadata)
```

## Configuration

### Environment Variables:
```bash
# Performance settings
AI_ENDPOINT_TIMEOUT_MS=200
AI_PERFORMANCE_WARNINGS=true

# Quality settings
AI_MIN_QUALITY_LEVEL=medium
AI_STRICT_VALIDATION=true

# Vector storage settings
AI_VECTOR_STORAGE_TYPE=mock
AI_VECTOR_DIMENSION=1536
AI_VECTOR_METRIC=cosine
```

### Programmatic Configuration:
```python
from ai_integration.middleware import get_ai_endpoints_router
from ai_integration.middleware.data_quality_gateway import get_data_quality_gateway
from ai_integration.middleware.vector_cache import get_vector_storage

# Configure endpoints
router = get_ai_endpoints_router()
router.performance_middleware.warning_threshold_ms = 150

# Configure quality gateway
gateway = get_data_quality_gateway()
gateway.reset_stats()

# Configure vector storage
storage = get_vector_storage()
```

## Monitoring and Observability

### Performance Monitoring:
```python
# Get endpoint metrics
router = get_ai_endpoints_router()
metrics = router.get_performance_metrics()

# Get performance summary
summary = router.performance_middleware.get_performance_summary()
print(f"Average time: {summary['average_execution_time_ms']:.2f}ms")
print(f"Warning rate: {summary['warning_rate']:.1f}%")
```

### Quality Monitoring:
```python
# Get validation statistics
gateway = get_data_quality_gateway()
stats = gateway.get_validation_stats()

print(f"Total validations: {stats['total_validations']}")
print(f"Success rate: {stats['successful_validations'] / stats['total_validations'] * 100:.1f}%")
print(f"Average validation time: {stats['average_validation_time_ms']:.2f}ms")
```

### Vector Storage Monitoring:
```python
# Get storage statistics
storage = get_vector_storage()
stats = await storage.get_stats()

print(f"Total embeddings: {stats.total_embeddings}")
print(f"Average query time: {stats.avg_query_time_ms:.2f}ms")
print(f"Storage size: {stats.storage_size_bytes / 1024 / 1024:.2f}MB")
```

## Testing

### Unit Tests:
```bash
# Run all middleware tests
python -m pytest tests/middleware/ -v

# Run specific component tests
python -m pytest tests/middleware/test_endpoints.py -v
python -m pytest tests/middleware/test_data_quality_gateway.py -v
python -m pytest tests/middleware/test_vector_cache.py -v
```

### Integration Tests:
```bash
# Run API integration tests
python -m pytest tests/integration/test_ai_endpoints.py -v

# Run performance tests
python -m pytest tests/performance/test_endpoint_performance.py -v
```

### Schema Validation:
```bash
# Validate OpenAPI schema
python -m ai_integration.middleware.openapi_schema
```

## Best Practices

### Endpoint Design:
1. **Zero Token Waste**: Use shortened field names
2. **Strict Validation**: Validate all inputs
3. **Performance Monitoring**: Track execution times
4. **Error Handling**: Provide clear error messages

### Data Quality:
1. **Strict Validation**: Never pass dirty data to AI
2. **Quality Scoring**: Assess data quality automatically
3. **Consistency Checks**: Validate data relationships
4. **Error Classification**: Use appropriate severity levels

### Vector Storage:
1. **Vendor Flexibility**: Use abstract interfaces
2. **Cost Control**: Monitor and compare costs
3. **Performance**: Optimize for query speed
4. **Scalability**: Design for large datasets

## Troubleshooting

### Common Issues:

**Performance Issues:**
- Check endpoint execution times
- Monitor token usage
- Validate data quality processing time

**Validation Failures:**
- Review validation error messages
- Check data format requirements
- Verify field constraints

**Vector Storage Issues:**
- Validate configuration parameters
- Check connection status
- Monitor storage statistics

### Debug Tools:

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Get detailed metrics
router = get_ai_endpoints_router()
for metric in router.get_performance_metrics():
    print(f"{metric.endpoint}: {metric.execution_time_ms:.2f}ms")

# Validate configuration
from ai_integration.middleware.vector_cache import get_vector_storage_factory
factory = get_vector_storage_factory()
print("Supported types:", factory.get_supported_types())
```

## Future Enhancements

Planned improvements include:

1. **GraphQL Support**: Add GraphQL endpoints for flexible queries
2. **Advanced Caching**: Implement multi-level caching strategies
3. **Real-time Monitoring**: Add live performance dashboards
4. **Auto-scaling**: Implement dynamic scaling based on load
5. **Advanced Vector Operations**: Add hybrid search and filtering
6. **Cost Optimization**: Implement automatic vendor selection

## Support

For issues, questions, or contributions:

1. Check the test suite for usage examples
2. Review the OpenAPI schema for endpoint details
3. Monitor performance metrics for optimization opportunities
4. Use the mock storage for testing and development

The middleware layer provides a robust foundation for AI-powered applications with enterprise-grade reliability, performance, and cost efficiency.
