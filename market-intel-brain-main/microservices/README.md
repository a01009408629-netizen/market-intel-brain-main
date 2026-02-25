# Market Intel Brain - Microservices Architecture

## Architecture Overview

This is the new microservices architecture that refactors the monolithic Python application into separate services using Rust and Go.

### Service Distribution

#### Rust Services (Core Business Logic)
- **core-engine** - LMAX Disruptor-based processing engine
- **data-processor** - High-performance data processing and analytics
- **ai-inference** - ML model inference and predictions
- **risk-engine** - Real-time risk calculations and monitoring
- **trading-engine** - Order execution and portfolio management

#### Go Services (API & External Integration)
- **api-gateway** - REST API, WebSocket, and routing
- **auth-service** - Authentication and authorization
- **data-ingestion** - External data source connectors
- **notification-service** - Alerts and notifications
- **config-service** - Configuration management

### Communication
- **gRPC** - Inter-service communication
- **Redpanda** - Event streaming and messaging
- **PostgreSQL** - Primary data storage
- **Redis** - Caching and session storage

## Project Structure

```
microservices/
├── rust-services/          # Rust microservices
│   ├── core-engine/
│   ├── data-processor/
│   ├── ai-inference/
│   ├── risk-engine/
│   └── trading-engine/
├── go-services/            # Go microservices
│   ├── api-gateway/
│   ├── auth-service/
│   ├── data-ingestion/
│   ├── notification-service/
│   └── config-service/
├── proto/                  # gRPC protobuf definitions
├── deployments/            # Docker and Kubernetes configs
├── monitoring/             # Observability and monitoring
└── docs/                  # Architecture documentation
```

## Development Phases

### Phase 1: Architecture & Scaffolding ✅
- [x] Project structure creation
- [x] Docker compose setup
- [x] gRPC contract definitions
- [x] Basic service scaffolding

### Phase 2: Core Migration (Planned)
- [ ] Migrate core engine to Rust
- [ ] Migrate data processing to Rust
- [ ] Set up gRPC communication
- [ ] Implement basic API gateway

### Phase 3: Service Expansion (Planned)
- [ ] Migrate AI/ML services
- [ ] Migrate risk engine
- [ ] Migrate trading engine
- [ ] Implement auth service

### Phase 4: Integration & Testing (Planned)
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Security hardening
- [ ] Documentation completion
