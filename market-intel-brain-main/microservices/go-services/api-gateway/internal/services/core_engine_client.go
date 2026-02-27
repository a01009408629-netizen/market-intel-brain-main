package services

import (
	"context"
	"fmt"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/connectivity"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/keepalive"

	"github.com/market-intel/api-gateway/pkg/logger"
	"github.com/market-intel/api-gateway/pkg/otel"
	"github.com/market-intel/api-gateway/pkg/resilience"
	"github.com/market-intel/api-gateway/pkg/tls"
	pb "github.com/market-intel/api-gateway/pb"
)

// CoreEngineClient represents a client for Core Engine service
type CoreEngineClient struct {
	conn           *grpc.ClientConn
	circuitBreaker *resilience.CircuitBreakerWithRetry
}

// Ensure CoreEngineClient implements CoreEngineInterface
var _ CoreEngineInterface = (*CoreEngineClient)(nil)

func NewCoreEngineClient(address string) (*CoreEngineClient, error) {
	// Load TLS configuration
	tlsConfig, err := tls.NewTLSConfigFromEnv()
	if err != nil {
		return nil, fmt.Errorf("failed to load TLS configuration: %w", err)
	}

	// Create TLS client configuration
	tlsClientConfig, err := tlsConfig.CreateTLSClientConfig()
	if err != nil {
		return nil, fmt.Errorf("failed to create TLS client config: %w", err)
	}
	
	// Create gRPC credentials with TLS
	grpcCreds := credentials.NewTLS(tlsClientConfig)
	
	// Get certificate info for logging
	if tlsConfig.CertFile != "" {
		certInfo, err := tls.ParseCertificate(tlsConfig.CertFile)
		if err == nil {
			logger.Infof("Using client certificate: %s issued by %s", certInfo.Subject, certInfo.Issuer)
			logger.Infof("Certificate expires: %s", certInfo.NotAfter)
			if certInfo.IsExpired {
				return nil, fmt.Errorf("client certificate has expired")
			}
		}
	}
	
	// Create connection with timeout and TLS
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	
	conn, err := grpc.DialContext(ctx, address, 
		grpc.WithTransportCredentials(grpcCreds),
		grpc.WithBlock(),
		grpc.WithTimeout(5*time.Second),
		grpc.WithKeepaliveParams(keepalive.ClientParameters{
			Time:                10 * time.Second,
			Timeout:              3 * time.Second,
			PermitWithoutStream: true,
		}),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to core engine: %w", err)
	}
	
	logger.Infof("Connected to core engine at %s with mTLS", address)
	
	// Initialize circuit breaker with retry
	cbConfig := resilience.DefaultCircuitBreakerConfig()
	retryConfig := resilience.DefaultRetryConfig()
	circuitBreaker := resilience.NewCircuitBreakerWithRetry(cbConfig, retryConfig)
	
	return &CoreEngineClient{
		conn:           conn,
		circuitBreaker: circuitBreaker,
	}, nil
}

func (c *CoreEngineClient) Close() error {
	if c.conn != nil {
		return c.conn.Close()
	}
	return nil
}

// injectTraceContext injects OpenTelemetry trace context into gRPC metadata
func (c *CoreEngineClient) injectTraceContext(ctx context.Context) context.Context {
	// Extract trace ID from context
	traceID := otel.GetTraceID(ctx)
	if traceID != "" {
		// Create metadata with trace ID
		md := metadata.New(map[string]string{
			"trace_id": traceID,
		})
		return metadata.NewOutgoingContext(ctx, md)
	}
	return ctx
}

// HealthCheck performs a health check on the core engine
func (c *CoreEngineClient) HealthCheck(ctx context.Context, serviceName string) error {
	// Inject trace context
	ctx = c.injectTraceContext(ctx)
	
	// For now, just check if connection is alive
	if c.conn == nil {
		return fmt.Errorf("connection is nil")
	}
	
	// Get connection state
	if c.conn.GetState() != connectivity.Ready {
		return fmt.Errorf("connection is not ready")
	}
	
	logger.Infof("Core Engine health check passed for service: %s", serviceName)
	return nil
}

// GetStatus gets the status of the core engine
func (c *CoreEngineClient) GetStatus(ctx context.Context) error {
	// Inject trace context
	_ = c.injectTraceContext(ctx)
	
	// For now, just check if connection is alive
	if c.conn == nil {
		return fmt.Errorf("connection is nil")
	}
	
	logger.Infof("Core Engine status retrieved successfully")
	return nil
}

// FetchMarketData fetches market data from the core engine
func (c *CoreEngineClient) FetchMarketData(ctx context.Context, req *pb.FetchMarketDataRequest) (*pb.FetchMarketDataResponse, error) {
	logger.Infof("Fetching market data from core engine")
	
	// For now, return a mock response
	// This will be replaced with actual gRPC call when protobuf is properly generated
	response := &pb.FetchMarketDataResponse{
		Success: true,
		Message: "Market data fetched successfully (mock)",
		MarketData: []pb.MarketData{
			{
				Symbol:    "AAPL",
				Price:     150.25,
				Timestamp: time.Now().Unix(),
				Volume:    1000000,
			},
		},
	}
	
	return response, nil
}

// FetchNewsData fetches news data from the core engine
func (c *CoreEngineClient) FetchNewsData(ctx context.Context, req *pb.FetchNewsDataRequest) (*pb.FetchNewsDataResponse, error) {
	logger.Infof("Fetching news data from core engine")
	
	// For now, return a mock response
	// This will be replaced with actual gRPC call when protobuf is properly generated
	response := &pb.FetchNewsDataResponse{
		Success: true,
		Message: "News data fetched successfully (mock)",
		NewsData: []pb.NewsData{
			{
				ID:        "1",
				Title:     "Market Update",
				Content:   "Stock markets are showing positive trends",
				Source:    "Reuters",
				Timestamp: time.Now().Unix(),
			},
		},
	}
	
	return response, nil
}

// ConnectDataSource connects a data source to the core engine
func (c *CoreEngineClient) ConnectDataSource(ctx context.Context, req *pb.ConnectDataSourceRequest) (*pb.ConnectDataSourceResponse, error) {
	logger.Infof("Connecting data source to core engine")
	
	// For now, return a mock response
	// This will be replaced with actual gRPC call when protobuf is properly generated
	response := &pb.ConnectDataSourceResponse{
		Success: true,
		Message: "Data source connected successfully (mock)",
	}
	
	return response, nil
}

// GetMarketDataBuffer gets market data buffer from the core engine
func (c *CoreEngineClient) GetMarketDataBuffer(ctx context.Context, req *pb.GetMarketDataBufferRequest) (*pb.GetMarketDataBufferResponse, error) {
	logger.Infof("Getting market data buffer from core engine")
	
	// For now, return a mock response
	// This will be replaced with actual gRPC call when protobuf is properly generated
	response := &pb.GetMarketDataBufferResponse{
		Success: true,
		Message: "Market data buffer retrieved successfully (mock)",
		MarketData: []pb.MarketData{
			{
				Symbol:    "AAPL",
				Price:     150.25,
				Timestamp: time.Now().Unix(),
				Volume:    1000000,
			},
		},
	}
	
	return response, nil
}

// GetNewsBuffer gets news buffer from the core engine
func (c *CoreEngineClient) GetNewsBuffer(ctx context.Context, req *pb.GetNewsBufferRequest) (*pb.GetNewsBufferResponse, error) {
	logger.Infof("Getting news buffer from core engine")
	
	// For now, return a mock response
	// This will be replaced with actual gRPC call when protobuf is properly generated
	response := &pb.GetNewsBufferResponse{
		Success: true,
		Message: "News buffer retrieved successfully (mock)",
		NewsData: []pb.NewsData{
			{
				ID:        "1",
				Title:     "Market Update",
				Content:   "Stock markets are showing positive trends",
				Source:    "Reuters",
				Timestamp: time.Now().Unix(),
			},
		},
	}
	
	return response, nil
}

// GetIngestionStats gets ingestion stats from the core engine
func (c *CoreEngineClient) GetIngestionStats(ctx context.Context, req *pb.GetIngestionStatsRequest) (*pb.GetIngestionStatsResponse, error) {
	logger.Infof("Getting ingestion stats from core engine")
	
	// For now, return a mock response
	// This will be replaced with actual gRPC call when protobuf is properly generated
	response := &pb.GetIngestionStatsResponse{
		Success: true,
		Message: "Ingestion stats retrieved successfully (mock)",
		Stats: map[string]interface{}{
			"total_processed": 1000,
			"success_rate":   0.95,
			"last_processed": time.Now().Unix(),
		},
	}
	
	return response, nil
}

// ExecuteWithCircuitBreaker executes a function with circuit breaker protection
func (c *CoreEngineClient) ExecuteWithCircuitBreaker(ctx context.Context, operation func() error) error {
	logger.Infof("Executing operation with circuit breaker protection")
	
	err := c.circuitBreaker.Execute(ctx, func() error {
		// Inject trace context
		ctx := c.injectTraceContext(ctx)
		
		// Add timeout to context
		ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
		defer cancel()

		// Execute the operation
		return operation()
	})

	if err != nil {
		logger.Errorf("Circuit breaker error: %v", err)
		return err
	}

	logger.Infof("Operation executed successfully")
	return nil
}
