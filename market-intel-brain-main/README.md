# 🧠 Market Intel Brain

Enterprise-grade market intelligence platform built with Rust and Go microservices architecture.

## 🏗️ Architecture

### Core Components

- **🦀 Rust Core Engine** - High-performance data processing and analytics
- **🐹 Go API Gateway** - Scalable HTTP/gRPC gateway and routing
- **📋 Protobuf Contracts** - Type-safe service communication
- **🐳 Docker Containers** - Multi-architecture containerized deployment
- **📊 Observability Stack** - Comprehensive monitoring and logging

### Microservices Structure

```
microservices/
├── go-services/
│   └── api-gateway/          # HTTP/gRPC API Gateway
├── rust-services/
│   └── core-engine/          # Data Processing Engine
├── proto/                   # Protobuf Definitions
├── scripts/                 # Utility Scripts
├── docker-compose.yml         # Services Orchestration
└── docker-compose-observability.yml  # Monitoring Stack
```

### Technology Stack

| Component | Technology | Purpose |
|------------|-------------|----------|
| **Core Engine** | 🦀 Rust | High-performance data processing |
| **API Gateway** | 🐹 Go | Scalable HTTP/gRPC services |
| **Communication** | 📋 Protobuf | Type-safe inter-service communication |
| **Containerization** | 🐳 Docker | Multi-architecture deployment |
| **Orchestration** | 🐙 Docker Compose | Local development and testing |
| **Observability** | 📊 Prometheus + Grafana | Monitoring and visualization |
| **Logging** | 📝 ELK Stack | Centralized logging |
| **Tracing** | 🔍 Jaeger | Distributed tracing |

## 🚀 Getting Started

### Prerequisites

- **Docker & Docker Compose** - For container orchestration
- **Go 1.21+** - For API Gateway development
- **Rust 1.75+** - For Core Engine development
- **Buf** - For Protobuf management
- **Make** - For build automation

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/a01009408629-netizen/market-intel-brain.git
   cd market-intel-brain
   ```

2. **Start all services**
   ```bash
   # Start observability stack
   make start-observability
   
   # Start application services
   make start-services
   ```
   
   Or using Docker Compose directly:
   ```bash
   # Start observability stack
   docker-compose -f docker-compose-observability.yml up -d
   
   # Start application services
   docker-compose -f docker-compose.yml up -d --build
   ```

3. **Verify services are running**
   ```bash
   # Check API Gateway
   curl http://localhost:8080/api/v1/health
   
   # Check Core Engine (gRPC)
   grpcurl -plaintext localhost:50052 list
   ```

### Development Setup

1. **Install dependencies**
   ```bash
   # Go dependencies
   cd microservices/go-services/api-gateway
   go mod download
   
   # Rust dependencies
   cd microservices/rust-services/core-engine
   cargo build
   ```

2. **Run tests**
   ```bash
   # Go tests
   cd microservices/go-services/api-gateway
   go test -v ./...
   
   # Rust tests
   cd microservices/rust-services/core-engine
   cargo test
   ```

3. **Generate Protobuf files**
   ```bash
   cd microservices/proto
   buf generate
   ```

### Available Make Commands

```bash
make help           # Show all available commands
make start-services  # Start application services
make stop-services   # Stop application services
make start-observability  # Start monitoring stack
make stop-observability   # Stop monitoring stack
make test           # Run all tests
make lint           # Run linting
make build          # Build all services
make clean          # Clean build artifacts
```

## 🛠 Tech Stack

### Backend Technologies

- **🦀 Rust 1.75+** - Core engine and data processing
  - Tokio for async runtime
  - Tonic for gRPC services
  - Serde for serialization
  - Tracing for observability

- **🐹 Go 1.21+** - API gateway and HTTP services
  - Gin for HTTP framework
  - gRPC for service communication
  - OpenTelemetry for observability
  - Prometheus for metrics

### Infrastructure

- **🐳 Docker** - Containerization and deployment
- **📋 Protobuf** - Service contract definitions
- **🔍 Buf** - Protobuf linting and validation
- **📊 Prometheus** - Metrics collection
- **📈 Grafana** - Metrics visualization
- **📝 Elasticsearch** - Log storage
- **🔍 Jaeger** - Distributed tracing

### Development Tools

- **🔧 golangci-lint** - Go linting and quality
- **🦀 Clippy** - Rust linting and quality
- **🔒 Gosec** - Go security scanning
- **🔒 cargo-audit** - Rust security scanning
- **🔍 Trivy** - Container vulnerability scanning

## 📊 Service Endpoints

### API Gateway (Go)
- **Health Check:** `GET http://localhost:8080/api/v1/health`
- **Metrics:** `GET http://localhost:8080/metrics`
- **API Documentation:** `GET http://localhost:8080/docs`

### Core Engine (Rust)
- **gRPC Port:** `50052`
- **Health Check:** gRPC health service
- **Metrics:** `GET http://localhost:9000/metrics`

### Observability Stack
- **Prometheus:** `http://localhost:9090`
- **Grafana:** `http://localhost:3000` (admin/admin)
- **Jaeger:** `http://localhost:16686`
- **Elasticsearch:** `http://localhost:9200`
- **Kibana:** `http://localhost:5601`

## 🧪 Testing

### Unit Tests
```bash
# Go tests
make test-go

# Rust tests
make test-rust

# All tests
make test
```

### Integration Tests
```bash
# Run full integration test suite
make test-integration

# Run E2E validation
make test-e2e
```

### Performance Tests
```bash
# Run benchmarks
make benchmark

# Load testing
make load-test
```

## 📈 Monitoring & Observability

### Metrics
- **Application Metrics:** Prometheus endpoints on all services
- **Infrastructure Metrics:** Docker and system metrics
- **Business Metrics:** Custom business KPIs

### Logging
- **Structured Logging:** JSON format across all services
- **Centralized Logs:** Elasticsearch + Kibana
- **Log Levels:** Configurable log levels per service

### Tracing
- **Distributed Tracing:** Jaeger integration
- **Request Tracing:** End-to-end request flow
- **Performance Analysis:** Latency and bottleneck detection

## 🔒 Security

### Security Scanning
- **SAST:** Static code analysis (Gosec, Clippy)
- **Dependency Scanning:** Vulnerability detection (cargo-audit, Trivy)
- **Container Security:** Image vulnerability scanning

### Best Practices
- **Secrets Management:** Environment variables only
- **Network Security:** Service-to-service encryption
- **Input Validation:** Comprehensive input sanitization
- **Authentication:** JWT-based authentication

## 🚀 Deployment

### Development
```bash
# Start development environment
make dev

# Stop development environment
make stop-dev
```

### Production
```bash
# Build production images
make build-prod

# Deploy to production
make deploy-prod
```

### Environment Variables
See `.env.example` for all available configuration options.

## 📚 Documentation

- **[Architecture Guide](./ARCHITECTURE.md)** - Detailed system architecture
- **[API Documentation](./docs/api/)** - REST and gRPC API docs
- **[Development Guide](./docs/development/)** - Development setup and guidelines
- **[Deployment Guide](./docs/deployment/)** - Production deployment instructions

## 🤝 Contributing

Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests.

### Branch Strategy (GitFlow)

- **`main`** - Production-ready code
- **`develop`** - Integration branch for features
- **`feature/*`** - Feature branches
- **`hotfix/*`** - Hotfix branches
- **`release/*`** - Release preparation branches

### Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Maintenance tasks

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Rust Community** - Excellent async and gRPC libraries
- **Go Community** - Robust HTTP and gRPC tools
- **OpenTelemetry** - Comprehensive observability framework
- **Buf** - Modern Protobuf tooling
