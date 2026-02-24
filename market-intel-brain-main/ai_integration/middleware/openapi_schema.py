"""
OpenAPI Schema for AI Integration Endpoints

Enterprise-grade API schema for AI-ready endpoints with
strict validation and zero token waste.
"""

from typing import Dict, Any, List, Optional
import json


def get_ai_endpoints_openapi_schema() -> Dict[str, Any]:
    """
    Generate OpenAPI 3.0 schema for AI integration endpoints.
    
    Returns:
        Complete OpenAPI specification for AI endpoints.
    """
    schema = {
        "openapi": "3.0.3",
        "info": {
            "title": "Market Intel Brain - AI Integration API",
            "description": "Enterprise-grade AI-ready endpoints with strict validation and token optimization",
            "version": "2.0.0",
            "contact": {
                "name": "Market Intel Brain Team",
                "email": "ai-integration@marketintelbrain.com"
            },
            "license": {
                "name": "Enterprise License",
                "url": "https://marketintelbrain.com/license"
            }
        },
        "servers": [
            {
                "url": "https://api.marketintelbrain.com/v2",
                "description": "Production server"
            },
            {
                "url": "https://staging-api.marketintelbrain.com/v2",
                "description": "Staging server"
            },
            {
                "url": "http://localhost:8000/v2",
                "description": "Development server"
            }
        ],
        "paths": {
            "/ai/normalized/market/{source}/{symbol}": {
                "get": {
                    "tags": ["AI Integration"],
                    "summary": "Get AI-ready market price data",
                    "description": "Returns ultra-optimized market price data for AI consumption with zero token waste",
                    "operationId": "getAIMarketPrice",
                    "parameters": [
                        {
                            "name": "source",
                            "in": "path",
                            "required": True,
                            "schema": {
                                "type": "string",
                                "enum": ["binance", "yahoo_finance", "finnhub", "alpha_vantage", "marketstack", "fmp"],
                                "description": "Data source identifier"
                            },
                            "example": "binance"
                        },
                        {
                            "name": "symbol",
                            "in": "path",
                            "required": True,
                            "schema": {
                                "type": "string",
                                "pattern": "^[A-Z0-9]{1,20}$",
                                "description": "Trading symbol (uppercase alphanumeric)"
                            },
                            "example": "BTCUSDT"
                        },
                        {
                            "name": "format",
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "string",
                                "enum": ["json", "minimal", "compressed"],
                                "default": "json",
                                "description": "Response format optimization level"
                            },
                            "example": "json"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "AI-ready market price data",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/AIMarketPriceResponse"
                                    },
                                    "examples": {
                                        "success": {
                                            "summary": "Successful response",
                                            "value": {
                                                "s": "BTCUSDT",
                                                "p": 15025.50,
                                                "c": 125.75,
                                                "cp": 0.84,
                                                "v": 1542000000.0,
                                                "ms": "open",
                                                "cur": "USDT",
                                                "conf": 0.95,
                                                "ts": "2024-02-22T10:30:00Z"
                                            }
                                        }
                                    }
                                }
                            },
                            "headers": {
                                "X-Execution-Time": {
                                    "description": "Execution time in milliseconds",
                                    "schema": {
                                        "type": "string",
                                        "pattern": "^\\d+\\.\\d+$"
                                    }
                                },
                                "X-Token-Count": {
                                    "description": "Estimated token count",
                                    "schema": {
                                        "type": "integer",
                                        "minimum": 0
                                    }
                                },
                                "X-Performance-Warning": {
                                    "description": "Performance warning flag",
                                    "schema": {
                                        "type": "string",
                                        "enum": ["true", "false"]
                                    }
                                }
                            }
                        },
                        "400": {
                            "$ref": "#/components/responses/BadRequest"
                        },
                        "422": {
                            "$ref": "#/components/responses/ValidationError"
                        },
                        "500": {
                            "$ref": "#/components/responses/InternalServerError"
                        }
                    },
                    "x-performance-threshold": "200ms",
                    "x-token-optimization": "minimal"
                }
            },
            "/ai/normalized/news/{source}": {
                "get": {
                    "tags": ["AI Integration"],
                    "summary": "Get AI-ready news articles",
                    "description": "Returns ultra-optimized news articles for AI consumption with sentiment analysis",
                    "operationId": "getAINewsArticles",
                    "parameters": [
                        {
                            "name": "source",
                            "in": "path",
                            "required": True,
                            "schema": {
                                "type": "string",
                                "enum": ["yahoo_finance", "finnhub", "alpha_vantage", "news_catcher", "google_news"],
                                "description": "News data source identifier"
                            },
                            "example": "yahoo_finance"
                        },
                        {
                            "name": "symbol",
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "string",
                                "pattern": "^[A-Z0-9]{1,20}$",
                                "description": "Filter by trading symbol"
                            },
                            "example": "AAPL"
                        },
                        {
                            "name": "category",
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "string",
                                "description": "Filter by news category"
                            },
                            "example": "technology"
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 100,
                                "default": 10,
                                "description": "Maximum number of articles"
                            },
                            "example": 10
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "AI-ready news articles",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "$ref": "#/components/schemas/AINewsArticleResponse"
                                        }
                                    },
                                    "examples": {
                                        "success": {
                                            "summary": "Successful response",
                                            "value": [
                                                {
                                                    "t": "Apple Stock Reaches New Heights",
                                                    "s": "Apple shares surged to record levels following strong earnings report",
                                                    "ss": 0.75,
                                                    "sl": "positive",
                                                    "rs": 0.85,
                                                    "cat": "technology",
                                                    "conf": 0.90,
                                                    "ts": "2024-02-22T09:15:00Z"
                                                }
                                            ]
                                        }
                                    }
                                }
                            }
                        },
                        "400": {
                            "$ref": "#/components/responses/BadRequest"
                        },
                        "422": {
                            "$ref": "#/components/responses/ValidationError"
                        },
                        "500": {
                            "$ref": "#/components/responses/InternalServerError"
                        }
                    },
                    "x-performance-threshold": "200ms",
                    "x-token-optimization": "minimal"
                }
            },
            "/ai/normalized/sentiment/{source}": {
                "get": {
                    "tags": ["AI Integration"],
                    "summary": "Get AI-ready sentiment data",
                    "description": "Returns ultra-optimized sentiment analysis data for AI consumption",
                    "operationId": "getAISentimentData",
                    "parameters": [
                        {
                            "name": "source",
                            "in": "path",
                            "required": True,
                            "schema": {
                                "type": "string",
                                "enum": ["twitter", "reddit", "facebook", "instagram", "linkedin"],
                                "description": "Social media platform identifier"
                            },
                            "example": "twitter"
                        },
                        {
                            "name": "platform",
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "string",
                                "description": "Filter by platform (overrides path parameter)"
                            },
                            "example": "twitter"
                        },
                        {
                            "name": "topic",
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "string",
                                "description": "Filter by topic or keyword"
                            },
                            "example": "AAPL"
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 100,
                                "default": 10,
                                "description": "Maximum number of data points"
                            },
                            "example": 10
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "AI-ready sentiment data",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "$ref": "#/components/schemas/AISentimentDataResponse"
                                        }
                                    },
                                    "examples": {
                                        "success": {
                                            "summary": "Successful response",
                                            "value": [
                                                {
                                                    "plat": "twitter",
                                                    "top": "AAPL",
                                                    "os": 0.65,
                                                    "sl": "positive",
                                                    "conf": 0.80,
                                                    "es": 0.75,
                                                    "pc": 1250,
                                                    "ts": "2024-02-22T10:45:00Z"
                                                }
                                            ]
                                        }
                                    }
                                }
                            }
                        },
                        "400": {
                            "$ref": "#/components/responses/BadRequest"
                        },
                        "422": {
                            "$ref": "#/components/responses/ValidationError"
                        },
                        "500": {
                            "$ref": "#/components/responses/InternalServerError"
                        }
                    },
                    "x-performance-threshold": "200ms",
                    "x-token-optimization": "minimal"
                }
            },
            "/ai/health": {
                "get": {
                    "tags": ["AI Integration"],
                    "summary": "AI endpoints health check",
                    "description": "Health check for AI endpoints with performance metrics and data flow validation",
                    "operationId": "healthCheck",
                    "responses": {
                        "200": {
                            "description": "Health check results",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/HealthCheckResponse"
                                    },
                                    "examples": {
                                        "success": {
                                            "summary": "Healthy service",
                                            "value": {
                                                "status": "healthy",
                                                "timestamp": "2024-02-22T10:30:00Z",
                                                "data_flow_test": "passed",
                                                "performance": {
                                                    "total_requests": 1250,
                                                    "average_execution_time_ms": 145.5,
                                                    "warnings_triggered": 12,
                                                    "warning_rate": 0.96,
                                                    "total_tokens_processed": 45678
                                                },
                                                "token_usage": {
                                                    "current_session": {
                                                        "total_tokens": 45678,
                                                        "estimated_cost_usd": 0.0685
                                                    },
                                                    "daily_usage": {
                                                        "total_tokens": 123456,
                                                        "total_cost": 0.1852
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "503": {
                            "$ref": "#/components/responses/ServiceUnavailable"
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "AIMarketPriceResponse": {
                    "type": "object",
                    "required": ["s", "p", "ms", "cur", "conf", "ts"],
                    "properties": {
                        "s": {
                            "type": "string",
                            "description": "Trading symbol",
                            "example": "BTCUSDT"
                        },
                        "p": {
                            "type": "number",
                            "format": "float",
                            "description": "Current price",
                            "example": 15025.50
                        },
                        "c": {
                            "type": "number",
                            "format": "float",
                            "description": "Price change",
                            "example": 125.75
                        },
                        "cp": {
                            "type": "number",
                            "format": "float",
                            "description": "Percentage change",
                            "example": 0.84
                        },
                        "v": {
                            "type": "number",
                            "format": "float",
                            "description": "Trading volume",
                            "example": 1542000000.0
                        },
                        "ms": {
                            "type": "string",
                            "enum": ["open", "closed", "pre_market", "after_hours"],
                            "description": "Market status",
                            "example": "open"
                        },
                        "cur": {
                            "type": "string",
                            "pattern": "^[A-Z]{3}$",
                            "description": "Currency code",
                            "example": "USDT"
                        },
                        "conf": {
                            "type": "number",
                            "format": "float",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Data confidence level",
                            "example": 0.95
                        },
                        "ts": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Timestamp",
                            "example": "2024-02-22T10:30:00Z"
                        }
                    },
                    "description": "Ultra-optimized market price response for AI consumption",
                    "x-token-optimized": "true"
                },
                "AINewsArticleResponse": {
                    "type": "object",
                    "required": ["t", "ss", "sl", "rs", "cat", "conf", "ts"],
                    "properties": {
                        "t": {
                            "type": "string",
                            "minLength": 5,
                            "maxLength": 500,
                            "description": "Article title",
                            "example": "Apple Stock Reaches New Heights"
                        },
                        "s": {
                            "type": "string",
                            "maxLength": 1000,
                            "description": "Article summary",
                            "example": "Apple shares surged to record levels"
                        },
                        "ss": {
                            "type": "number",
                            "format": "float",
                            "minimum": -1,
                            "maximum": 1,
                            "description": "Sentiment score",
                            "example": 0.75
                        },
                        "sl": {
                            "type": "string",
                            "enum": ["positive", "negative", "neutral", "mixed"],
                            "description": "Sentiment label",
                            "example": "positive"
                        },
                        "rs": {
                            "type": "number",
                            "format": "float",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Relevance score",
                            "example": 0.85
                        },
                        "cat": {
                            "type": "string",
                            "maxLength": 50,
                            "description": "News category",
                            "example": "technology"
                        },
                        "conf": {
                            "type": "number",
                            "format": "float",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Data confidence level",
                            "example": 0.90
                        },
                        "ts": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Timestamp",
                            "example": "2024-02-22T09:15:00Z"
                        }
                    },
                    "description": "Ultra-optimized news article response for AI consumption",
                    "x-token-optimized": "true"
                },
                "AISentimentDataResponse": {
                    "type": "object",
                    "required": ["plat", "top", "os", "sl", "conf", "ts"],
                    "properties": {
                        "plat": {
                            "type": "string",
                            "maxLength": 50,
                            "description": "Social media platform",
                            "example": "twitter"
                        },
                        "top": {
                            "type": "string",
                            "maxLength": 100,
                            "description": "Topic or keyword",
                            "example": "AAPL"
                        },
                        "os": {
                            "type": "number",
                            "format": "float",
                            "minimum": -1,
                            "maximum": 1,
                            "description": "Overall sentiment",
                            "example": 0.65
                        },
                        "sl": {
                            "type": "string",
                            "enum": ["positive", "negative", "neutral", "mixed"],
                            "description": "Sentiment label",
                            "example": "positive"
                        },
                        "conf": {
                            "type": "number",
                            "format": "float",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Confidence level",
                            "example": 0.80
                        },
                        "es": {
                            "type": "number",
                            "format": "float",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Engagement score",
                            "example": 0.75
                        },
                        "pc": {
                            "type": "integer",
                            "minimum": 0,
                            "description": "Post count",
                            "example": 1250
                        },
                        "ts": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Timestamp",
                            "example": "2024-02-22T10:45:00Z"
                        }
                    },
                    "description": "Ultra-optimized sentiment data response for AI consumption",
                    "x-token-optimized": "true"
                },
                "HealthCheckResponse": {
                    "type": "object",
                    "required": ["status", "timestamp"],
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["healthy", "degraded", "unhealthy"],
                            "description": "Overall health status",
                            "example": "healthy"
                        },
                        "timestamp": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Health check timestamp",
                            "example": "2024-02-22T10:30:00Z"
                        },
                        "data_flow_test": {
                            "type": "string",
                            "enum": ["passed", "failed"],
                            "description": "Data flow test result",
                            "example": "passed"
                        },
                        "performance": {
                            "type": "object",
                            "properties": {
                                "total_requests": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "description": "Total requests processed"
                                },
                                "average_execution_time_ms": {
                                    "type": "number",
                                    "format": "float",
                                    "minimum": 0,
                                    "description": "Average execution time in milliseconds"
                                },
                                "warnings_triggered": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "description": "Number of performance warnings triggered"
                                },
                                "warning_rate": {
                                    "type": "number",
                                    "format": "float",
                                    "minimum": 0,
                                    "maximum": 100,
                                    "description": "Warning rate as percentage"
                                },
                                "total_tokens_processed": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "description": "Total tokens processed"
                                }
                            }
                        },
                        "token_usage": {
                            "type": "object",
                            "properties": {
                                "current_session": {
                                    "type": "object",
                                    "properties": {
                                        "total_tokens": {
                                            "type": "integer",
                                            "minimum": 0
                                        },
                                        "estimated_cost_usd": {
                                            "type": "number",
                                            "format": "float",
                                            "minimum": 0
                                        }
                                    }
                                },
                                "daily_usage": {
                                    "type": "object",
                                    "properties": {
                                        "total_tokens": {
                                            "type": "integer",
                                            "minimum": 0
                                        },
                                        "total_cost": {
                                            "type": "number",
                                            "format": "float",
                                            "minimum": 0
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "description": "Health check response with performance metrics"
                },
                "ErrorResponse": {
                    "type": "object",
                    "required": ["error", "message", "code", "ts"],
                    "properties": {
                        "error": {
                            "type": "string",
                            "description": "Error type",
                            "example": "ValidationError"
                        },
                        "message": {
                            "type": "string",
                            "description": "Error message",
                            "example": "Invalid symbol format"
                        },
                        "code": {
                            "type": "string",
                            "description": "Error code",
                            "example": "INVALID_SYMBOL"
                        },
                        "ts": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Error timestamp",
                            "example": "2024-02-22T10:30:00Z"
                        }
                    },
                    "description": "Standard error response format"
                }
            },
            "responses": {
                "BadRequest": {
                    "description": "Bad request - Invalid parameters",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ErrorResponse"
                            }
                        }
                    }
                },
                "ValidationError": {
                    "description": "Validation error - Data quality issues",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ErrorResponse"
                            }
                        }
                    }
                },
                "InternalServerError": {
                    "description": "Internal server error",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ErrorResponse"
                            }
                        }
                    }
                },
                "ServiceUnavailable": {
                    "description": "Service temporarily unavailable",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ErrorResponse"
                            }
                        }
                    }
                }
            },
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "JWT authentication token"
                },
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "API key authentication"
                }
            }
        },
        "security": [
            {
                "BearerAuth": []
            },
            {
                "ApiKeyAuth": []
            }
        ],
        "tags": [
            {
                "name": "AI Integration",
                "description": "AI-ready endpoints with token optimization and strict validation"
            }
        ],
        "x-performance-requirements": {
            "max_response_time_ms": 200,
            "max_token_waste": 0,
            "min_data_quality": "medium",
            "validation_strictness": "enterprise"
        },
        "x-token-optimization": {
            "field_shortening": "true",
            "metadata_stripping": "true",
            "response_compression": "minimal",
            "estimated_token_savings": "60-80%"
        }
    }
    
    return schema


def get_openapi_json() -> str:
    """Get OpenAPI schema as JSON string."""
    return json.dumps(get_ai_endpoints_openapi_schema(), indent=2)


def get_openapi_yaml() -> str:
    """Get OpenAPI schema as YAML string."""
    try:
        import yaml
        return yaml.dump(get_ai_endpoints_openapi_schema(), default_flow_style=False)
    except ImportError:
        return "# Install PyYAML to get YAML format: pip install PyYAML\n\n" + get_openapi_json()


# Example usage and validation
if __name__ == "__main__":
    # Generate and validate schema
    schema = get_ai_endpoints_openapi_schema()
    
    # Basic validation
    assert "openapi" in schema
    assert "paths" in schema
    assert "components" in schema
    
    # Check required endpoints
    required_paths = [
        "/ai/normalized/market/{source}/{symbol}",
        "/ai/normalized/news/{source}",
        "/ai/normalized/sentiment/{source}",
        "/ai/health"
    ]
    
    for path in required_paths:
        assert path in schema["paths"], f"Missing required path: {path}"
    
    # Check token optimization
    for path, path_spec in schema["paths"].items():
        for method, method_spec in path_spec.items():
            if method in ["get", "post", "put", "delete"]:
                assert "x-token-optimization" in method_spec, f"Missing token optimization for {method} {path}"
                assert "x-performance-threshold" in method_spec, f"Missing performance threshold for {method} {path}"
    
    print("✅ OpenAPI schema validation passed")
    print(f"📊 Generated schema with {len(schema['paths'])} endpoints")
    print(f"🔒 Security schemes: {list(schema['components']['securitySchemes'].keys())}")
    print(f"🏷️  Tags: {[tag['name'] for tag in schema['tags']]}")
