# MAIFA Source Adapter Layer Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        API[API Gateway]
        WEB[Web Interface]
        SCHED[Scheduler]
    end
    
    subgraph "Source Adapter Layer"
        REG[Adapter Registry]
        CB[Circuit Breaker]
        RETRY[Retry Engine]
        BASE[Base Adapter]
        
        subgraph "Concrete Adapters"
            FIN[Finnhub Adapter]
            YAHOO[Yahoo Finance Adapter]
            ALPHA[Alpha Vantage Adapter]
            MARKET[MarketStack Adapter]
        end
    end
    
    subgraph "Infrastructure Layer"
        REDIS[(Redis)]
        HTTP[HTTP Client Pool]
        METRICS[Metrics Collection]
        LOGS[Structured Logging]
    end
    
    subgraph "External Services"
        FINHUB[Finnhub API]
        YAPI[Yahoo Finance API]
            AAPI[Alpha Vantage API]
            MAPI[MarketStack API]
    end
    
    API --> REG
    WEB --> REG
    SCHED --> REG
    
    REG --> FIN
    REG --> YAHOO
    REG --> ALPHA
    REG --> MARKET
    
    FIN --> BASE
    YAHOO --> BASE
    ALPHA --> BASE
    MARKET --> BASE
    
    BASE --> CB
    BASE --> RETRY
    BASE --> HTTP
    
    CB --> REDIS
    RETRY --> REDIS
    BASE --> METRICS
    BASE --> LOGS
    
    FIN --> FINHUB
    YAHOO --> YAPI
    ALPHA --> AAPI
    MARKET --> MAPI
```

## Component Overview

### **Core Interfaces & Contracts**
- **Error Contract**: Unified exception hierarchy with transient/non-transient classification
- **Circuit Breaker**: Redis-based distributed circuit breaker for multi-node environments
- **Retry Engine**: Exponential backoff with jitter and exception filtering

### **Base Layer & Validation**
- **Base Adapter**: Abstract class with HTTP client pooling and fingerprint-safe headers
- **Request Schemas**: Pydantic V2 models for strict type validation
- **Response Schemas**: Unified normalization models for consistent data format

### **Concrete Implementation & Orchestration**
- **Finnhub Adapter**: Canonical implementation demonstrating all patterns
- **Adapter Registry**: Factory pattern for dynamic, lazy-loading of adapters

### **Key Features**
- **Zero-Crash Design**: All exceptions wrapped and handled gracefully
- **Fingerprint Safety**: Dynamic User-Agent rotation and header management
- **Connection Pooling**: HTTPX client with optimized connection reuse
- **Distributed Resilience**: Redis-backed circuit breaker and retry logic
- **Strict Typing**: Python 3.12+ with comprehensive type hints
- **Observability**: Structured logging and metrics collection
- **Dependency Injection**: Testable design with mock support
