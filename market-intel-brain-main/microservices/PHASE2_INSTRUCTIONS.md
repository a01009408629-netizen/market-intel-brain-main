# Phase 2: gRPC Generation and Foundation Wiring

## 🎯 Objective

Establish the base gRPC connection between the Rust Core Engine and Go API Gateway services. This phase focuses on infrastructure setup without business logic.

## ✅ What's Implemented

### 1. Rust Core Engine Service
- **build.rs**: Configured to compile protobuf files using `tonic-build`
- **gRPC Server**: Basic tokio gRPC server with HealthCheck implementation
- **Configuration**: Environment-based configuration management
- **Health Check**: Returns "Healthy" status with service information

### 2. Go API Gateway Service
- **gRPC Client**: Connection pool to Rust Core Engine service
- **HTTP Server**: Gin-based REST server with health endpoints
- **Health Endpoints**: 
  - `GET /health` - Overall system health
  - `GET /ping` - Simple ping test
  - `GET /ping/core-engine` - Ping Core Engine via gRPC

### 3. gRPC Communication
- **Proto Files**: Generated for both Rust and Go
- **Health Check**: Implemented in Rust, called from Go
- **Error Handling**: Proper error handling and logging

## 🚀 Quick Start

### Prerequisites

1. **Install Protocol Buffers Compiler**
   ```bash
   # macOS
   brew install protobuf
   
   # Ubuntu/Debian
   sudo apt-get install protobuf-compiler
   
   # Windows
   # Download from: https://github.com/protocolbuffers/protobuf/releases
   ```

2. **Install Go gRPC Plugins**
   ```bash
   go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
   go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
   ```

3. **Install Rust Dependencies**
   ```bash
   cd rust-services/core-engine
   cargo build
   ```

### Step 1: Generate Protobuf Code

```bash
cd microservices
chmod +x scripts/generate-proto.sh
./scripts/generate-proto.sh
```

### Step 2: Start Core Engine (Rust)

```bash
cd rust-services/core-engine
cargo run
```

Expected output:
```
INFO  Starting Market Intel Brain Core Engine v0.1.0
INFO  Loaded configuration: CoreEngineConfig { ... }
INFO  Core Engine gRPC server listening on 0.0.0.0:50052
```

### Step 3: Start API Gateway (Go)

```bash
cd go-services/api-gateway
go mod tidy
go run cmd/api-gateway/main.go
```

Expected output:
```
INFO Starting Market Intel Brain API Gateway v0.1.0
INFO Connected to Core Engine at localhost:50052
INFO Starting HTTP server on :8080
INFO Starting gRPC server on :8081
```

### Step 4: Test the Connection

```bash
# Test API Gateway health
curl http://localhost:8080/health

# Test simple ping
curl http://localhost:8080/ping

# Test Core Engine ping via gRPC
curl http://localhost:8080/ping/core-engine
```

Expected responses:

```json
// Health check
{
  "status": "healthy",
  "timestamp": "2024-02-25T13:30:00Z",
  "services": {
    "api_gateway": {
      "status": "healthy",
      "version": "0.1.0",
      "environment": "development"
    },
    "core_engine": {
      "status": "healthy",
      "version": "0.1.0",
      "details": {
        "service": "core-engine",
        "port": "50052",
        "processors": "4"
      }
    }
  }
}

// Ping
{
  "message": "pong",
  "service": "api-gateway",
  "timestamp": "2024-02-25T13:30:00Z"
}

// Core Engine ping
{
  "message": "Core Engine ping successful",
  "healthy": true,
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2024-02-25T13:30:00Z"
}
```

### Step 5: Automated Testing

```bash
cd microservices
chmod +x scripts/test-grpc-connection.sh
./scripts/test-grpc-connection.sh
```

## 📁 Project Structure

```
microservices/
├── rust-services/core-engine/
│   ├── build.rs                    # Protobuf compilation
│   ├── src/
│   │   ├── main.rs                 # Service entry point
│   │   ├── config.rs               # Configuration
│   │   ├── core_engine_service.rs  # gRPC service implementation
│   │   └── proto/mod.rs            # Generated proto modules
│   └── Cargo.toml                  # Dependencies
├── go-services/api-gateway/
│   ├── cmd/api-gateway/main.go     # Service entry point
│   ├── internal/
│   │   ├── config/config.go        # Configuration
│   │   ├── services/core_engine_client.go # gRPC client
│   │   ├── handlers/health.go      # HTTP handlers
│   │   └── server/                 # Server setup
│   ├── pkg/logger/logger.go        # Logging utilities
│   └── go.mod                      # Dependencies
└── scripts/
    ├── generate-proto.sh           # Protobuf generation
    └── test-grpc-connection.sh     # Connection testing
```

## 🔧 Configuration

### Environment Variables

**Core Engine (Rust):**
```bash
export GRPC_PORT=50052
export DATABASE_URL=postgres://postgres:postgres@localhost:5432/market_intel
export REDIS_URL=redis://localhost:6379
export REDPANDA_BROKERS=localhost:9092
export NUM_PROCESSORS=4
export BUFFER_SIZE=1048576
export LOG_LEVEL=info
```

**API Gateway (Go):**
```bash
export HTTP_PORT=8080
export GRPC_PORT=8081
export DATABASE_URL=postgres://postgres:postgres@localhost:5432/market_intel
export REDIS_URL=redis://localhost:6379
export REDPANDA_BROKERS=localhost:9092
export CORE_ENGINE_URL=localhost:50052
export AUTH_SERVICE_URL=localhost:50051
export LOG_LEVEL=info
export ENVIRONMENT=development
```

## 🧪 Testing

### Manual Testing

1. **Start both services** (see Quick Start)
2. **Test endpoints** with curl or Postman
3. **Check logs** for gRPC communication

### Automated Testing

```bash
# Run connection tests
./scripts/test-grpc-connection.sh

# Expected output:
# [INFO] Core Engine is running on port 50052
# [INFO] API Gateway is running on port 8080
# [INFO] ✅ Core Engine gRPC health check successful!
# [INFO] ✅ API Gateway health check successful!
# [INFO] ✅ API Gateway ping endpoint working!
# [INFO] ✅ API Gateway → Core Engine ping successful!
# [INFO] 🎉 All services are running and connected!
```

## 🐛 Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Check what's using the port
   lsof -i :50052  # Core Engine
   lsof -i :8080   # API Gateway
   
   # Kill the process
   kill -9 <PID>
   ```

2. **gRPC connection failed**
   ```bash
   # Check if Core Engine is running
   curl http://localhost:50052/health  # Won't work, gRPC only
   
   # Use grpcurl if available
   grpcurl -plaintext localhost:50052 list
   ```

3. **Protobuf generation failed**
   ```bash
   # Clean and regenerate
   rm -rf go-services/api-gateway/proto/*
   rm -rf rust-services/core-engine/src/proto/*
   ./scripts/generate-proto.sh
   ```

4. **Go module issues**
   ```bash
   cd go-services/api-gateway
   go mod tidy
   go mod download
   ```

5. **Rust build issues**
   ```bash
   cd rust-services/core-engine
   cargo clean
   cargo build
   ```

### Debug Mode

**Core Engine:**
```bash
RUST_LOG=debug cargo run
```

**API Gateway:**
```bash
LOG_LEVEL=debug go run cmd/api-gateway/main.go
```

## 📊 Performance Targets

- **gRPC Latency**: <1ms (local)
- **HTTP Response Time**: <10ms
- **Connection Setup**: <100ms
- **Health Check**: <50ms

## 🎯 Success Criteria

- [x] ✅ Rust Core Engine starts and listens on gRPC port
- [x] ✅ Go API Gateway starts and connects to Core Engine
- [x] ✅ Health check endpoint returns "Healthy" status
- [x] ✅ API Gateway can ping Core Engine via gRPC
- [x] ✅ Proper error handling and logging
- [x] ✅ Configuration management working
- [x] ✅ Protobuf generation working

## 🔄 Next Steps

Once Phase 2 is confirmed working, we can proceed to:

1. **Phase 3**: Implement actual business logic migration
2. **Add authentication** and authorization
3. **Implement message processing** in Core Engine
4. **Add market data endpoints** to API Gateway
5. **Set up monitoring** and metrics

## 📞 Support

If you encounter issues:

1. Check the logs for both services
2. Run the automated test script
3. Verify all prerequisites are installed
4. Check that ports are not blocked by firewall

---

**Phase 2 Status**: ✅ **COMPLETE** - Ready for testing and validation!
