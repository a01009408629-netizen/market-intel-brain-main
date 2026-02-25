# Market Intel Brain - Microservices Project Structure

## Complete Project Tree

```
microservices/
├── README.md                                    # Architecture overview and development phases
├── docker-compose.yml                           # Complete orchestration with all services
├── PROJECT_STRUCTURE.md                         # This file - detailed project structure
│
├── proto/                                       # gRPC protobuf definitions
│   ├── common.proto                            # Common types and messages
│   ├── core_engine.proto                        # Core Engine service definitions
│   ├── api_gateway.proto                        # API Gateway service definitions
│   └── auth_service.proto                       # Auth Service service definitions
│
├── rust-services/                               # Rust microservices (Core Business Logic)
│   └── core-engine/                            # LMAX Disruptor-based processing engine
│       ├── Cargo.toml                          # Rust dependencies and build config
│       ├── Dockerfile                          # Multi-stage Docker build
│       ├── src/
│       │   ├── main.rs                         # Service entry point
│       │   ├── lib.rs                          # Library exports
│       │   ├── config.rs                       # Configuration management
│       │   ├── core_engine_service.rs          # gRPC service implementation
│       │   ├── core_engine.rs                  # Core engine logic
│       │   └── proto/                          # Generated gRPC code
│       └── config/                             # Configuration files
│           ├── default.toml                    # Default configuration
│           └── production.toml                 # Production configuration
│
├── go-services/                                 # Go microservices (API & External Integration)
│   └── api-gateway/                            # REST API, WebSocket, and routing
│       ├── go.mod                              # Go module dependencies
│       ├── Dockerfile                          # Multi-stage Docker build
│       ├── cmd/
│       │   └── api-gateway/
│       │       └── main.go                     # Service entry point
│       ├── internal/
│       │   ├── config/                          # Configuration management
│       │   │   ├── config.go                   # Configuration struct and loading
│       │   │   └── env.go                      # Environment variable handling
│       │   ├── server/                          # Server implementations
│       │   │   ├── http.go                     # HTTP server setup
│       │   │   ├── grpc.go                     # gRPC server setup
│       │   │   └── websocket.go                # WebSocket handlers
│       │   ├── handlers/                        # HTTP handlers
│       │   │   ├── auth.go                     # Authentication handlers
│       │   │   ├── market_data.go               # Market data handlers
│       │   │   ├── orders.go                   # Order management handlers
│       │   │   ├── portfolio.go                # Portfolio handlers
│       │   │   ├── analytics.go                 # Analytics handlers
│       │   │   └── notifications.go             # Notification handlers
│       │   ├── middleware/                      # HTTP middleware
│       │   │   ├── auth.go                     # Authentication middleware
│       │   │   ├── cors.go                     # CORS middleware
│       │   │   ├── logging.go                  # Logging middleware
│       │   │   ├── ratelimit.go                # Rate limiting middleware
│       │   │   └── metrics.go                  # Metrics middleware
│       │   ├── services/                        # Business logic services
│       │   │   ├── auth_service.go              # Authentication service client
│       │   │   ├── core_engine_client.go        # Core engine gRPC client
│       │   │   ├── market_data_service.go       # Market data service
│       │   │   └── notification_service.go     # Notification service
│       │   └── models/                          # Data models
│       │       ├── user.go                     # User models
│       │       ├── order.go                    # Order models
│       │       ├── market_data.go              # Market data models
│       │       └── response.go                 # Response models
│       ├── pkg/                                 # Public packages
│       │   ├── logger/                          # Logging utilities
│       │   │   └── logger.go                   # Logger setup
│       │   ├── metrics/                         # Metrics collection
│       │   │   └── prometheus.go               # Prometheus metrics
│       │   └── utils/                          # Utility functions
│       │       ├── validation.go               # Input validation
│       │       └── helpers.go                  # Helper functions
│       └── config/                             # Configuration files
│           ├── default.yaml                    # Default configuration
│           └── production.yaml                 # Production configuration
│
├── deployments/                                 # Deployment configurations
│   ├── docker/                                 # Docker configurations
│   │   ├── postgres/
│   │   │   └── init.sql                        # Database initialization
│   │   ├── redis/
│   │   │   └── redis.conf                      # Redis configuration
│   │   └── redpanda/
│   │       └── redpanda.yaml                   # Redpanda configuration
│   ├── kubernetes/                             # Kubernetes manifests
│   │   ├── namespace.yaml                     # Namespace definition
│   │   ├── configmaps/                        # ConfigMaps
│   │   ├── secrets/                           # Secrets
│   │   ├── deployments/                        # Service deployments
│   │   ├── services/                          # Service definitions
│   │   ├── ingress/                           # Ingress configurations
│   │   └── monitoring/                        # Monitoring stack
│   └── terraform/                             # Terraform infrastructure
│       ├── main.tf                            # Main Terraform configuration
│       ├── variables.tf                        # Variable definitions
│       ├── outputs.tf                         # Output definitions
│       └── modules/                           # Reusable modules
│
├── monitoring/                                 # Observability and monitoring
│   ├── prometheus/
│   │   ├── prometheus.yml                      # Prometheus configuration
│   │   ├── rules/                             # Alerting rules
│   │   │   ├── alerts.yml                      # Alert rules
│   │   │   └── recording.yml                  # Recording rules
│   │   └── targets/                           # Service targets
│   ├── grafana/
│   │   ├── dashboards/                        # Grafana dashboards
│   │   │   ├── overview.json                  # System overview
│   │   │   ├── core-engine.json               # Core engine metrics
│   │   │   ├── api-gateway.json               # API gateway metrics
│   │   │   └── auth-service.json              # Auth service metrics
│   │   ├── datasources/                       # Data source configurations
│   │   │   └── prometheus.yml                 # Prometheus data source
│   │   └── provisioning/                      # Auto-provisioning
│   │       ├── dashboards.yml                 # Dashboard provisioning
│   │       └── datasources.yml                # Datasource provisioning
│   ├── jaeger/                                # Distributed tracing
│   │   ├── jaeger.yml                         # Jaeger configuration
│   │   └── sampling.yml                       # Sampling configuration
│   └── alertmanager/
│       ├── alertmanager.yml                   # Alertmanager configuration
│       └── templates/                         # Alert templates
│
├── docs/                                       # Documentation
│   ├── architecture/                          # Architecture documentation
│   │   ├── overview.md                       # System overview
│   │   ├── microservices.md                   # Microservices design
│   │   ├── data-flow.md                       # Data flow diagrams
│   │   └── security.md                        # Security architecture
│   ├── api/                                   # API documentation
│   │   ├── rest-api.md                        # REST API reference
│   │   ├── grpc-api.md                        # gRPC API reference
│   │   └── websocket-api.md                   # WebSocket API reference
│   ├── deployment/                            # Deployment guides
│   │   ├── docker.md                         # Docker deployment
│   │   ├── kubernetes.md                     # Kubernetes deployment
│   │   └── production.md                     # Production deployment
│   └── development/                           # Development guides
│       ├── setup.md                          # Development setup
│       ├── testing.md                        # Testing strategies
│       └── debugging.md                       # Debugging guide
│
└── scripts/                                   # Utility scripts
    ├── build.sh                              # Build all services
    ├── deploy.sh                             # Deploy services
    ├── test.sh                               # Run tests
    ├── generate-proto.sh                    # Generate protobuf code
    ├── health-check.sh                      # Health check script
    └── cleanup.sh                           # Cleanup resources
```

## Service Responsibilities

### Rust Services (Core Business Logic)

#### 1. Core Engine (`rust-services/core-engine/`)
- **Primary Function**: LMAX Disruptor-based ultra-low latency processing
- **Responsibilities**:
  - High-performance message processing
  - Agent management and orchestration
  - Real-time event processing
  - Performance monitoring and profiling
  - Memory management and optimization
- **gRPC Port**: 50052
- **Performance Target**: <1 microsecond latency, 10M+ messages/second

#### 2. Data Processor (`rust-services/data-processor/`) - Phase 2
- **Primary Function**: High-performance data processing and analytics
- **Responsibilities**:
  - Market data normalization
  - Technical indicators calculation
  - Data aggregation and transformation
  - Real-time analytics processing

#### 3. AI Inference (`rust-services/ai-inference/`) - Phase 2
- **Primary Function**: ML model inference and predictions
- **Responsibilities**:
  - Sentiment analysis
  - Predictive modeling
  - Pattern recognition
  - Model serving and optimization

#### 4. Risk Engine (`rust-services/risk-engine/`) - Phase 2
- **Primary Function**: Real-time risk calculations and monitoring
- **Responsibilities**:
  - Portfolio risk analysis
  - Position monitoring
  - Limit checking
  - Risk alert generation

#### 5. Trading Engine (`rust-services/trading-engine/`) - Phase 2
- **Primary Function**: Order execution and portfolio management
- **Responsibilities**:
  - Order management
  - Trade execution
  - Position tracking
  - Portfolio optimization

### Go Services (API & External Integration)

#### 1. API Gateway (`go-services/api-gateway/`)
- **Primary Function**: REST API, WebSocket, and external integrations
- **Responsibilities**:
  - HTTP/REST API endpoints
  - WebSocket connections
  - Request routing and load balancing
  - Authentication and authorization
  - Rate limiting and throttling
  - Request/response transformation
- **HTTP Port**: 8080
- **gRPC Port**: 8081

#### 2. Auth Service (`go-services/auth-service/`) - Phase 2
- **Primary Function**: Authentication, authorization, and user management
- **Responsibilities**:
  - User authentication
  - JWT token management
  - Role-based access control
  - API key management
  - Session management
  - Multi-factor authentication
- **gRPC Port**: 50051

#### 3. Data Ingestion (`go-services/data-ingestion/`) - Phase 2
- **Primary Function**: External data source connectors
- **Responsibilities**:
  - External API integrations
  - Data source normalization
  - Data validation and filtering
  - Real-time data streaming
  - Error handling and retry logic

#### 4. Notification Service (`go-services/notification-service/`) - Phase 2
- **Primary Function**: Alerts and notifications
- **Responsibilities**:
  - Email notifications
  - SMS notifications
  - Webhook delivery
  - Push notifications
  - Alert aggregation and deduplication

#### 5. Config Service (`go-services/config-service/`) - Phase 2
- **Primary Function**: Configuration management
- **Responsibilities**:
  - Centralized configuration
  - Dynamic configuration updates
  - Environment-specific configs
  - Configuration validation
  - Audit logging

## Communication Patterns

### 1. gRPC Inter-Service Communication
- **Core Engine ↔ API Gateway**: Market data, orders, trades
- **API Gateway ↔ Auth Service**: Authentication, authorization
- **All Services ↔ Config Service**: Configuration management
- **Core Engine ↔ Risk Engine**: Risk calculations
- **Core Engine ↔ Trading Engine**: Order execution

### 2. Event Streaming (Redpanda)
- **Market Data Events**: Real-time market data updates
- **Order Events**: Order lifecycle events
- **Trade Events**: Trade confirmations
- **Risk Events**: Risk alerts and notifications
- **System Events**: Health checks and monitoring

### 3. Database Access
- **PostgreSQL**: Primary data storage
  - User accounts and profiles
  - Order and trade history
  - Portfolio and position data
  - Configuration data
- **Redis**: Caching and session storage
  - Session data
  - API rate limiting
  - Market data cache
  - Temporary data

## Development Workflow

### Phase 1: Architecture & Scaffolding ✅
- [x] Project structure creation
- [x] Docker compose setup
- [x] gRPC contract definitions
- [x] Basic service scaffolding
- [x] Infrastructure configuration

### Phase 2: Core Migration (Next)
- [ ] Implement Core Engine service
- [ ] Implement API Gateway service
- [ ] Set up gRPC communication
- [ ] Implement basic authentication
- [ ] Add monitoring and logging

### Phase 3: Service Expansion
- [ ] Migrate remaining services
- [ ] Implement advanced features
- [ ] Add comprehensive testing
- [ ] Performance optimization

### Phase 4: Integration & Production
- [ ] End-to-end testing
- [ ] Security hardening
- [ ] Documentation completion
- [ ] Production deployment

## Technology Stack

### Rust Services
- **Runtime**: Tokio async runtime
- **gRPC**: Tonic + Prost
- **Database**: SQLx (PostgreSQL) + Redis
- **Message Queue**: rdkafka (Redpanda)
- **Logging**: Tracing + Tracing Subscriber
- **Metrics**: Prometheus client

### Go Services
- **Web Framework**: Gin (HTTP) + gRPC
- **Authentication**: JWT + OAuth2
- **Database**: pgx (PostgreSQL) + Redis
- **Message Queue**: kafka-go (Redpanda)
- **Logging**: Logrus
- **Metrics**: Prometheus client

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Orchestration**: Kubernetes
- **Monitoring**: Prometheus + Grafana + Jaeger
- **CI/CD**: GitHub Actions
- **Infrastructure as Code**: Terraform

## Performance Targets

### Latency Requirements
- **Core Engine Processing**: <1 microsecond (P99)
- **API Gateway Response**: <10 milliseconds (P99)
- **Database Queries**: <5 milliseconds (P99)
- **Message Queue Latency**: <100 microseconds (P99)

### Throughput Requirements
- **Core Engine**: 10M+ messages/second
- **API Gateway**: 100K+ requests/second
- **Database**: 50K+ queries/second
- **Message Queue**: 100M+ messages/second

### Availability Requirements
- **Uptime**: 99.99% (4.32 minutes/month downtime)
- **Recovery Time**: <30 seconds
- **Data Loss**: Zero data loss
- **Consistency**: Strong consistency for critical data
