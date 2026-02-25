# Developer Guide

This guide provides detailed instructions for developers working on the Market Intel Brain project.

## Table of Contents

1. [Adding a New gRPC Endpoint](#adding-a-new-grpc-endpoint)
2. [Running Local Chaos Testing](#running-local-chaos-testing)
3. [Error Handling Strategy](#error-handling-strategy)
4. [Development Workflow](#development-workflow)
5. [Testing Guidelines](#testing-guidelines)
6. [Debugging Tips](#debugging-tips)

## Adding a New gRPC Endpoint

This section provides a step-by-step guide for adding a new gRPC endpoint to the system.

### Prerequisites

- Familiarity with Protocol Buffers (.proto files)
- Understanding of gRPC concepts
- Access to the development environment

### Step 1: Define the gRPC Service in Proto File

1. **Locate the appropriate proto file** in `microservices/proto/`:
   - `core_engine.proto` for core engine services
   - `api_gateway.proto` for gateway services
   - `analytics.proto` for analytics services
   - `auth_service.proto` for authentication services

2. **Add your service definition**:
```protobuf
service YourNewService {
  rpc YourMethod(YourRequest) returns (YourResponse);
  rpc AnotherMethod(AnotherRequest) returns (stream AnotherResponse);
}
```

3. **Define message types**:
```protobuf
message YourRequest {
  string field1 = 1;
  int32 field2 = 2;
  optional string optional_field = 3;
}

message YourResponse {
  bool success = 1;
  string message = 2;
  repeated Item items = 3;
}
```

### Step 2: Generate gRPC Code

1. **Run the code generation script**:
```bash
cd microservices
make generate-proto
```

2. **Verify generated files**:
   - Go: `microservices/go-services/*/pb/`
   - Rust: `microservices/rust-services/*/src/generated/`

### Step 3: Implement the Service in Rust

1. **Create the service implementation** in `microservices/rust-services/core-engine/src/`:

```rust
use tonic::{Request, Response, Status, Streaming};
use crate::generated::your_service::*;
use crate::generated::common::*;

pub struct YourNewServiceImpl {
    // Add any required dependencies
    config: Arc<Config>,
    metrics: Arc<Metrics>,
}

impl YourNewServiceImpl {
    pub fn new(config: Arc<Config>, metrics: Arc<Metrics>) -> Self {
        Self { config, metrics }
    }
}

#[tonic::async_trait]
impl your_new_service_server::YourNewService for YourNewServiceImpl {
    async fn your_method(
        &self,
        request: Request<YourRequest>,
    ) -> Result<Response<YourResponse>, Status> {
        let req = request.into_inner();
        
        // Validate input
        if req.field1.is_empty() {
            return Err(Status::invalid_argument("field1 cannot be empty"));
        }
        
        // Process the request
        let result = self.process_request(&req).await?;
        
        // Return response
        Ok(Response::new(YourResponse {
            success: true,
            message: "Operation completed successfully".to_string(),
            items: result,
        }))
    }
    
    async fn another_method(
        &self,
        request: Request<AnotherRequest>,
    ) -> Result<Response<Streaming<AnotherResponse>>, Status> {
        // Implement streaming response
        let (tx, rx) = mpsc::channel(128);
        
        // Spawn background task for streaming
        let config = self.config.clone();
        tokio::spawn(async move {
            // Generate stream data
            for item in generate_stream_data(&config).await {
                if tx.send(Ok(item)).await.is_err() {
                    break; // Client disconnected
                }
            }
        });
        
        Ok(Response::new(rx))
    }
}

impl YourNewServiceImpl {
    async fn process_request(&self, req: &YourRequest) -> Result<Vec<Item>, Box<dyn Error>> {
        // Implement your business logic here
        let mut items = Vec::new();
        
        // Example: Process data
        for i in 0..req.field2 {
            items.push(Item {
                id: i as i64,
                name: format!("Item {}", i),
                value: req.field1.clone(),
            });
        }
        
        Ok(items)
    }
}
```

2. **Register the service** in `main.rs`:

```rust
// Add to the service setup
let your_service = YourNewServiceImpl::new(config.clone(), metrics.clone());

Server::builder()
    .add_service(
        CoreEngineServiceServer::with_interceptor(core_engine_service, auth_interceptor)
    )
    .add_service(
        YourNewServiceServer::with_interceptor(your_service, auth_interceptor)
    )
    .serve_with_shutdown(addr, shutdown_signal)
    .await?;
```

### Step 4: Implement Client in Go Gateway

1. **Create the client wrapper** in `microservices/go-services/api-gateway/internal/services/`:

```go
package services

import (
    "context"
    "time"
    
    "github.com/market-intel/api-gateway/pb"
    "google.golang.org/grpc"
    "google.golang.org/grpc/codes"
    "google.golang.org/grpc/status"
)

type YourNewServiceClient struct {
    client pb.YourNewServiceClient
    conn   *grpc.ClientConn
}

func NewYourNewServiceClient(conn *grpc.ClientConn) *YourNewServiceClient {
    return &YourNewServiceClient{
        client: pb.NewYourNewServiceClient(conn),
        conn:   conn,
    }
}

func (c *YourNewServiceClient) YourMethod(ctx context.Context, req *pb.YourRequest) (*pb.YourResponse, error) {
    // Add timeout
    ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
    defer cancel()
    
    // Call the service
    resp, err := c.client.YourMethod(ctx, req)
    if err != nil {
        // Handle gRPC errors
        st, ok := status.FromError(err)
        if ok {
            switch st.Code() {
            case codes.InvalidArgument:
                return nil, fmt.Errorf("invalid argument: %s", st.Message())
            case codes.DeadlineExceeded:
                return nil, fmt.Errorf("request timeout")
            default:
                return nil, fmt.Errorf("gRPC error: %s", st.Message())
            }
        }
        return nil, fmt.Errorf("failed to call YourMethod: %w", err)
    }
    
    return resp, nil
}
```

2. **Register the client** in the service manager:

```go
// In service_manager.go
type ServiceManager struct {
    // Existing clients...
    yourNewService *services.YourNewServiceClient
}

func NewServiceManager(config *config.Config) (*ServiceManager, error) {
    // Existing setup...
    
    // Add new service client
    yourNewService := services.NewYourNewServiceClient(conn)
    
    return &ServiceManager{
        // Existing clients...
        yourNewService: yourNewService,
    }, nil
}
```

### Step 5: Add HTTP Endpoint

1. **Create the HTTP handler** in `microservices/go-services/api-gateway/internal/handlers/`:

```go
package handlers

import (
    "net/http"
    "strconv"
    
    "github.com/gin-gonic/gin"
    "github.com/market-intel/api-gateway/pb"
)

type YourHandler struct {
    service *services.YourNewServiceClient
}

func NewYourHandler(service *services.YourNewServiceClient) *YourHandler {
    return &YourHandler{service: service}
}

func (h *YourHandler) YourMethod(c *gin.Context) {
    // Parse request
    var req pb.YourRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    
    // Call gRPC service
    resp, err := h.service.YourMethod(c.Request.Context(), &req)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    // Return response
    c.JSON(http.StatusOK, resp)
}
```

2. **Register the route** in the router:

```go
// In routes.go
func SetupRoutes(r *gin.Engine, sm *services.ServiceManager) {
    // Existing routes...
    
    // Add new routes
    yourHandler := handlers.NewYourHandler(sm.YourNewServiceClient)
    
    api := r.Group("/api/v1")
    {
        // Existing routes...
        api.POST("/your-endpoint", yourHandler.YourMethod)
        api.GET("/your-endpoint/:id", yourHandler.GetByID)
    }
}
```

### Step 6: Add Tests

1. **Unit tests for Rust service**:

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use tokio_test;
    
    #[tokio::test]
    async fn test_your_method_success() {
        let config = Arc::new(Config::default());
        let metrics = Arc::new(Metrics::new());
        let service = YourNewServiceImpl::new(config, metrics);
        
        let request = YourRequest {
            field1: "test".to_string(),
            field2: 5,
            ..Default::default()
        };
        
        let result = service.your_method(Request::from(request)).await;
        assert!(result.is_ok());
        
        let response = result.unwrap().into_inner();
        assert!(response.success);
        assert_eq!(response.items.len(), 5);
    }
    
    #[tokio::test]
    async fn test_your_method_invalid_input() {
        let config = Arc::new(Config::default());
        let metrics = Arc::new(Metrics::new());
        let service = YourNewServiceImpl::new(config, metrics);
        
        let request = YourRequest {
            field1: "".to_string(), // Invalid: empty string
            field2: 5,
            ..Default::default()
        };
        
        let result = service.your_method(Request::from(request)).await;
        assert!(result.is_err());
        
        let status = result.unwrap_err();
        assert_eq!(status.code(), tonic::Code::InvalidArgument);
    }
}
```

2. **Integration tests for Go client**:

```go
package services_test

import (
    "context"
    "testing"
    "time"
    
    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/require"
    "github.com/market-intel/api-gateway/pb"
)

func TestYourNewServiceClient_YourMethod(t *testing.T) {
    // Setup test server
    server := setupTestServer(t)
    defer server.Stop()
    
    // Create client
    conn := setupTestConnection(t, server.Addr())
    defer conn.Close()
    
    client := services.NewYourNewServiceClient(conn)
    
    // Test successful call
    req := &pb.YourRequest{
        Field1: "test",
        Field2: 3,
    }
    
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()
    
    resp, err := client.YourMethod(ctx, req)
    require.NoError(t, err)
    assert.True(t, resp.Success)
    assert.Len(t, resp.Items, 3)
}
```

### Step 7: Update Documentation

1. **Update API documentation** in `docs/api/`
2. **Add examples** to `docs/examples/`
3. **Update OpenAPI spec** if applicable

## Running Local Chaos Testing

This section explains how to run the local chaos testing suite to verify system resilience.

### Prerequisites

- Docker and Docker Compose installed
- Kubernetes cluster (minikube, kind, or k3s)
- kubectl configured
- Chaos Mesh or Litmus Chaos installed (optional)

### Quick Start

1. **Run the basic chaos test**:
```bash
cd chaos-testing
./chaos-engine.sh --test=latency --duration=60s
```

2. **Run all chaos experiments**:
```bash
cd chaos-testing
./chaos-engine.sh --all
```

### Available Chaos Experiments

#### 1. Network Latency Injection

```bash
# Add 100ms latency to all traffic
./chaos-engine.sh --test=latency --latency=100ms --duration=300s

# Add latency to specific service
./chaos-engine.sh --test=latency --service=rust-engine --latency=200ms
```

#### 2. Packet Loss Injection

```bash
# Add 10% packet loss
./chaos-engine.sh --test=packet-loss --loss=10% --duration=300s

# Add packet loss to specific service
./chaos-engine.sh --test=packet-loss --service=go-gateway --loss=5%
```

#### 3. Pod Deletion

```bash
# Randomly delete pods
./chaos-engine.sh --test=pod-delete --count=2 --interval=60s

# Delete specific service pods
./chaos-engine.sh --test=pod-delete --service=analytics --count=1
```

#### 4. CPU Stress

```bash
# Add CPU stress to pods
./chaos-engine.sh --test=cpu-stress --cores=2 --duration=300s

# Stress specific service
./chaos-engine.sh --test=cpu-stress --service=rust-engine --cores=1
```

#### 5. Memory Stress

```bash
# Add memory stress
./chaos-engine.sh --test=memory-stress --memory=512Mi --duration=300s

# Stress specific service
./chaos-engine.sh --test=memory-stress --service=go-gateway --memory=256Mi
```

### Advanced Chaos Testing

#### Using Chaos Mesh

1. **Install Chaos Mesh**:
```bash
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm repo update
helm install chaos-mesh chaos-mesh/chaos-mesh --namespace chaos-testing --create-namespace
```

2. **Run Chaos Mesh experiments**:
```bash
# Apply a chaos experiment
kubectl apply -f chaos-testing/chaos-mesh/network-delay.yaml

# Monitor the experiment
kubectl get chaos -n chaos-testing

# Delete the experiment
kubectl delete chaos network-delay -n chaos-testing
```

#### Using Litmus Chaos

1. **Install Litmus Chaos**:
```bash
kubectl apply -f https://hub.litmuschaos.io/api/get?path=1.13.0/litmus-operator-generic.yaml
```

2. **Run Litmus experiments**:
```bash
# Create chaos experiment
kubectl apply -f chaos-testing/litmus/pod-delete.yaml

# Check results
kubectl get chaosexperiments -n litmus
kubectl get chaosresults -n litmus
```

### Monitoring Chaos Tests

1. **View real-time metrics**:
```bash
# Watch service health
watch kubectl get pods -n market-intel-brain

# Check service logs
kubectl logs -f deployment/go-gateway -n market-intel-brain
kubectl logs -f deployment/rust-engine -n market-intel-brain
```

2. **Monitor with Prometheus**:
```bash
# Access Prometheus dashboard
kubectl port-forward svc/prometheus-service 9090:9090 -n market-intel-brain-observability

# Check error rates
curl -s "http://localhost:9090/api/v1/query?query=sum(rate(http_requests_total{code=~\"5..\"}[5m]))"
```

3. **Check distributed traces**:
```bash
# Access Jaeger dashboard
kubectl port-forward svc/jaeger-service 16686:16686 -n market-intel-brain-observability
```

### Custom Chaos Experiments

1. **Create a custom experiment**:
```bash
# Create new chaos script
cat > chaos-testing/custom/my-experiment.sh << 'EOF'
#!/bin/bash

# Custom chaos experiment
echo "Starting custom chaos experiment..."

# Add your chaos logic here
kubectl patch deployment go-gateway -n market-intel-brain -p '{"spec":{"template":{"spec":{"containers":[{"name":"go-gateway","env":[{"name":"CHAOS_MODE","value":"true"}]}]}}}}'

# Wait for specified duration
sleep $DURATION

# Restore normal operation
kubectl patch deployment go-gateway -n market-intel-brain -p '{"spec":{"template":{"spec":{"containers":[{"name":"go-gateway","env":[{"name":"CHAOS_MODE","value":"false"}]}]}}}}'

echo "Custom chaos experiment completed"
EOF

chmod +x chaos-testing/custom/my-experiment.sh
```

2. **Run the custom experiment**:
```bash
./chaos-testing/custom/my-experiment.sh --duration=120s
```

### Best Practices

1. **Start small**: Begin with simple experiments and gradually increase complexity
2. **Monitor continuously**: Always watch system behavior during chaos tests
3. **Document results**: Keep track of what works and what doesn't
4. **Test in staging**: Run chaos tests in a staging environment before production
5. **Have rollback plans**: Know how to quickly restore services if things go wrong

## Error Handling Strategy

This section explains the error handling patterns used throughout the system, focusing on Rust's Result/Option patterns and Go's error handling.

### Rust Error Handling

#### Result Type Usage

The Rust services extensively use the `Result<T, E>` type for error handling:

```rust
use std::error::Error;
use std::fmt;

// Custom error type
#[derive(Debug)]
pub enum ServiceError {
    DatabaseError(String),
    ValidationError(String),
    NetworkError(String),
    ConfigurationError(String),
}

impl fmt::Display for ServiceError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            ServiceError::DatabaseError(msg) => write!(f, "Database error: {}", msg),
            ServiceError::ValidationError(msg) => write!(f, "Validation error: {}", msg),
            ServiceError::NetworkError(msg) => write!(f, "Network error: {}", msg),
            ServiceError::ConfigurationError(msg) => write!(f, "Configuration error: {}", msg),
        }
    }
}

impl Error for ServiceError {}

// Function returning Result
async fn process_data(input: &str) -> Result<ProcessedData, ServiceError> {
    if input.is_empty() {
        return Err(ServiceError::ValidationError("Input cannot be empty".to_string()));
    }
    
    // Process the data
    let result = database_query(input).await
        .map_err(|e| ServiceError::DatabaseError(e.to_string()))?;
    
    Ok(result)
}
```

#### Option Type Usage

The `Option<T>` type is used for values that may or may not exist:

```rust
// Function returning Option
fn find_user(id: u64) -> Option<User> {
    // Search for user
    if id == 0 {
        None
    } else {
        Some(User { id, name: "John Doe".to_string() })
    }
}

// Using Option with pattern matching
match find_user(user_id) {
    Some(user) => println!("Found user: {}", user.name),
    None => println!("User not found"),
}

// Using Option combinators
let user_name = find_user(user_id)
    .map(|user| user.name)
    .unwrap_or_else(|| "Unknown".to_string());
```

#### Error Propagation

Using the `?` operator for error propagation:

```rust
async fn complex_operation(input: &str) -> Result<FinalResult, ServiceError> {
    // Each step can fail and will propagate the error
    let validated = validate_input(input)?;
    let processed = process_data(&validated).await?;
    let saved = save_to_database(&processed).await?;
    
    Ok(FinalResult { data: saved })
}
```

#### gRPC Error Handling

Converting service errors to gRPC status codes:

```rust
use tonic::{Status, Code};

impl From<ServiceError> for Status {
    fn from(err: ServiceError) -> Self {
        match err {
            ServiceError::ValidationError(msg) => Status::new(Code::InvalidArgument, msg),
            ServiceError::DatabaseError(msg) => Status::new(Code::Internal, msg),
            ServiceError::NetworkError(msg) => Status::new(Code::Unavailable, msg),
            ServiceError::ConfigurationError(msg) => Status::new(Code::FailedPrecondition, msg),
        }
    }
}

// In gRPC service implementation
async fn handle_request(&self, request: Request<Input>) -> Result<Response<Output>, Status> {
    let result = complex_operation(&request.get_ref().data).await?;
    Ok(Response::new(Output { result }))
}
```

### Go Error Handling

#### Error Creation and Wrapping

```go
package errors

import (
    "fmt"
    "errors"
)

// Custom error types
type ServiceError struct {
    Code    string
    Message string
    Cause   error
}

func (e *ServiceError) Error() string {
    if e.Cause != nil {
        return fmt.Sprintf("%s: %s (caused by: %v)", e.Code, e.Message, e.Cause)
    }
    return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

func (e *ServiceError) Unwrap() error {
    return e.Cause
}

// Error constructors
func NewValidationError(msg string) *ServiceError {
    return &ServiceError{
        Code:    "VALIDATION_ERROR",
        Message: msg,
    }
}

func NewDatabaseError(msg string, cause error) *ServiceError {
    return &ServiceError{
        Code:    "DATABASE_ERROR",
        Message: msg,
        Cause:   cause,
    }
}

// Error checking functions
func IsValidationError(err error) bool {
    var serviceErr *ServiceError
    if errors.As(err, &serviceErr) {
        return serviceErr.Code == "VALIDATION_ERROR"
    }
    return false
}
```

#### Error Handling in Services

```go
package services

import (
    "context"
    "fmt"
)

func (s *YourService) ProcessData(ctx context.Context, input string) (*Result, error) {
    // Input validation
    if input == "" {
        return nil, errors.NewValidationError("input cannot be empty")
    }
    
    // Database operation with error wrapping
    result, err := s.database.Query(ctx, input)
    if err != nil {
        return nil, errors.NewDatabaseError("failed to query database", err)
    }
    
    // Process the result
    processed, err := s.processResult(result)
    if err != nil {
        return nil, fmt.Errorf("failed to process result: %w", err)
    }
    
    return processed, nil
}
```

#### gRPC Error Handling

```go
package handlers

import (
    "google.golang.org/grpc/codes"
    "google.golang.org/grpc/status"
    "github.com/market-intel/api-gateway/errors"
)

func (h *Handler) HandleRequest(ctx context.Context, req *pb.Request) (*pb.Response, error) {
    result, err := h.service.ProcessData(ctx, req.Input)
    if err != nil {
        // Convert service errors to gRPC status
        if errors.IsValidationError(err) {
            return nil, status.Error(codes.InvalidArgument, err.Error())
        }
        if errors.IsDatabaseError(err) {
            return nil, status.Error(codes.Internal, err.Error())
        }
        
        // Default error handling
        return nil, status.Error(codes.Internal, "internal server error")
    }
    
    return &pb.Response{Result: result}, nil
}
```

### Error Handling Patterns

#### 1. Circuit Breaker Pattern

```rust
use tokio::sync::RwLock;
use std::sync::Arc;
use std::time::{Duration, Instant};

#[derive(Debug)]
pub enum CircuitState {
    Closed,
    Open,
    HalfOpen,
}

pub struct CircuitBreaker {
    state: Arc<RwLock<CircuitState>>,
    failure_count: Arc<RwLock<u32>>,
    last_failure_time: Arc<RwLock<Option<Instant>>>,
    threshold: u32,
    timeout: Duration,
}

impl CircuitBreaker {
    pub async fn call<F, T>(&self, f: F) -> Result<T, ServiceError>
    where
        F: FnOnce() -> Result<T, ServiceError>,
    {
        // Check circuit state
        {
            let state = self.state.read().await;
            match *state {
                CircuitState::Open => {
                    let last_failure = self.last_failure_time.read().await;
                    if let Some(last) = *last_failure {
                        if last.elapsed() > self.timeout {
                            drop(state);
                            *self.state.write().await = CircuitState::HalfOpen;
                        } else {
                            return Err(ServiceError::NetworkError("Circuit breaker is open".to_string()));
                        }
                    }
                }
                _ => {}
            }
        }
        
        // Execute the function
        match f() {
            Ok(result) => {
                // Reset on success
                *self.failure_count.write().await = 0;
                *self.state.write().await = CircuitState::Closed;
                Ok(result)
            }
            Err(err) => {
                // Increment failure count
                let mut count = self.failure_count.write().await;
                *count += 1;
                *self.last_failure_time.write().await = Some(Instant::now());
                
                // Open circuit if threshold exceeded
                if *count >= self.threshold {
                    *self.state.write().await = CircuitState::Open;
                }
                
                Err(err)
            }
        }
    }
}
```

#### 2. Retry Pattern

```go
package retry

import (
    "context"
    "time"
    "math/rand"
)

type RetryConfig struct {
    MaxAttempts int
    InitialDelay time.Duration
    MaxDelay     time.Duration
    Multiplier   float64
}

func RetryWithBackoff(ctx context.Context, config RetryConfig, fn func() error) error {
    var lastErr error
    delay := config.InitialDelay
    
    for attempt := 1; attempt <= config.MaxAttempts; attempt++ {
        err := fn()
        if err == nil {
            return nil
        }
        
        lastErr = err
        
        // Don't wait after the last attempt
        if attempt == config.MaxAttempts {
            break
        }
        
        // Calculate next delay with jitter
        jitter := time.Duration(rand.Float64() * float64(delay))
        select {
        case <-time.After(delay + jitter):
        case <-ctx.Done():
            return ctx.Err()
        }
        
        // Exponential backoff
        delay = time.Duration(float64(delay) * config.Multiplier)
        if delay > config.MaxDelay {
            delay = config.MaxDelay
        }
    }
    
    return lastErr
}
```

#### 3. Timeout Pattern

```rust
use tokio::time::{timeout, Duration};

async fn with_timeout<F, T>(duration: Duration, future: F) -> Result<T, ServiceError>
where
    F: std::future::Future<Output = Result<T, ServiceError>>,
{
    match timeout(duration, future).await {
        Ok(result) => result,
        Err(_) => Err(ServiceError::NetworkError("Operation timed out".to_string())),
    }
}
```

### Error Monitoring and Alerting

#### Structured Error Logging

```rust
use tracing::{error, warn, info};
use serde_json::json;

async fn handle_error(err: &ServiceError, context: &str) {
    error!(
        error = %err,
        context = context,
        timestamp = %chrono::Utc::now(),
        "Service error occurred"
    );
    
    // Send to monitoring system
    if let Err(e) = send_error_to_monitoring(err, context).await {
        warn!("Failed to send error to monitoring: {}", e);
    }
}
```

#### Error Metrics

```go
package metrics

import (
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promauto"
)

var (
    errorCounter = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "service_errors_total",
            Help: "Total number of service errors",
        },
        []string{"service", "error_type"},
    )
    
    errorLatency = promauto.NewHistogramVec(
        prometheus.HistogramOpts{
            Name: "error_handling_duration_seconds",
            Help: "Time spent handling errors",
        },
        []string{"service", "error_type"},
    )
)

func RecordError(service, errorType string) {
    errorCounter.WithLabelValues(service, errorType).Inc()
}

func RecordErrorLatency(service, errorType string, duration time.Duration) {
    errorLatency.WithLabelValues(service, errorType).Observe(duration.Seconds())
}
```

## Development Workflow

### 1. Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/a01009408629-netizen/market-intel-brain.git
cd market-intel-brain

# Install Rust toolchain
rustup toolchain install stable
rustup default stable

# Install Go
go version  # Ensure Go 1.21+ is installed

# Install Docker
docker --version

# Setup Kubernetes
minikube start
```

### 2. Local Development

```bash
# Build all services
make build

# Run tests
make test

# Start local services
make run-local

# Run with hot reload
make run-dev
```

### 3. Code Quality

```bash
# Format code
make format

# Lint code
make lint

# Run security checks
make security-scan
```

## Testing Guidelines

### 1. Unit Tests

- Write tests for all public functions
- Use table-driven tests for multiple scenarios
- Mock external dependencies

### 2. Integration Tests

- Test service interactions
- Use test containers for database testing
- Test error scenarios

### 3. End-to-End Tests

- Test complete user workflows
- Use real Kubernetes cluster
- Test performance characteristics

## Debugging Tips

### 1. Rust Debugging

```bash
# Use RUST_LOG for detailed logging
RUST_LOG=debug cargo run

# Use gdb for debugging
rust-gdb target/debug/my-service

# Use memory profiling
valgrind --tool=memcheck target/debug/my-service
```

### 2. Go Debugging

```bash
# Use delve for debugging
dlv debug ./cmd/my-service

# Use pprof for profiling
go tool pprof http://localhost:6060/debug/pprof/profile
```

### 3. Kubernetes Debugging

```bash
# Check pod status
kubectl get pods -n market-intel-brain

# View pod logs
kubectl logs -f deployment/rust-engine -n market-intel-brain

# Debug running pods
kubectl exec -it deployment/rust-engine -n market-intel-brain -- /bin/bash

# Check events
kubectl get events -n market-intel-brain --sort-by='.lastTimestamp'
```

---

For more information, refer to the [Architecture Documentation](ARCHITECTURE.md) and the project's [GitHub repository](https://github.com/a01009408629-netizen/market-intel-brain).
