package services

import (
	"context"
	"fmt"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/metadata"

	"github.com/market-intel/api-gateway/pkg/logger"
	"github.com/market-intel/api-gateway/pkg/otel"
	"github.com/market-intel/api-gateway/pkg/resilience"
	"github.com/market-intel/api-gateway/pkg/tls"
)

type CoreEngineClient struct {
	conn           *grpc.ClientConn
	circuitBreaker *resilience.CircuitBreakerWithRetry
}

func NewCoreEngineClient(address string) (*CoreEngineClient, error) {
	// Load TLS configuration
	tlsConfig, err := tls.NewTLSConfigFromEnv()()
	
	// Validate TLS configuration
	if err := tlsConfig.Validate(); err != nil {
		return nil, logger.Errorf("TLS configuration validation failed: %w", err)
	}
	
	// Create gRPC credentials with TLS
	grpcCreds, err := tlsConfig.CreateGRPCCredentials()
	if err != nil {
		return nil, logger.Errorf("failed to create gRPC credentials: %w", err)
	}
	
	// Get certificate info for logging
	if certInfo, err := tlsConfig.GetCertificateInfo(); err == nil {
		logger.Infof("Using client certificate: %s issued by %s", certInfo.Subject, certInfo.Issuer)
		logger.Infof("Certificate expires: %s", certInfo.NotAfter)
		if certInfo.IsExpired() {
			return nil, logger.Errorf("client certificate has expired")
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
		return nil, logger.Errorf("failed to connect to core engine: %w", err)
	}

	client := pb.NewCoreEngineServiceClient(conn)
	
	logger.Infof("Connected to core engine at %s with mTLS", address)
	
	// Initialize circuit breaker with retry
	cbConfig := resilience.DefaultCircuitBreakerConfig()
	retryConfig := resilience.DefaultRetryConfig()
	circuitBreaker := resilience.NewCircuitBreakerWithRetry(cbConfig, retryConfig)
	
	return &CoreEngineClient{
		conn:           conn,
		client:         client,
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

func (c *CoreEngineClient) HealthCheck(ctx context.Context, serviceName string) (*pb.HealthCheckResponse, error) {
	// Inject trace context
	ctx = c.injectTraceContext(ctx)
	
	req := &pb.HealthCheckRequest{
		ServiceName: serviceName,
		Metadata:    map[string]string{
			"client": "api-gateway",
		},
	}

	resp, err := c.client.HealthCheck(ctx, req)
	if err != nil {
		logger.Errorf("Core Engine health check failed: %v", err)
		return nil, fmt.Errorf("health check failed: %w", err)
	}

	logger.Infof("Core Engine health check: healthy=%v, status=%s", resp.Healthy, resp.Status)

	return resp, nil
}

func (c *CoreEngineClient) GetStatus(ctx context.Context) (*pb.EngineStatusResponse, error) {
	// Inject trace context
	ctx = c.injectTraceContext(ctx)
	
	req := &pb.Empty{}

	resp, err := c.client.GetStatus(ctx, req)
	if err != nil {
		logger.Errorf("Core Engine get status failed: %v", err)
		return nil, fmt.Errorf("get status failed: %w", err)
	}

	logger.Infof("Core Engine status: %s", resp.Message)

	return resp, nil
}

// FetchMarketData fetches market data from the core engine with circuit breaker protection
func (c *CoreEngineClient) FetchMarketData(ctx context.Context, req *pb.FetchMarketDataRequest) (*pb.FetchMarketDataResponse, error) {
	logger.Infof("Fetching market data from core engine with circuit breaker protection")
	
	var response *pb.FetchMarketDataResponse
	err := c.circuitBreaker.Execute(ctx, func() error {
		// Inject trace context
		ctx = c.injectTraceContext(ctx)
		
		// Add timeout to context
		ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
		defer cancel()
		
		// Make gRPC call
		resp, err := c.client.FetchMarketData(ctx, req)
		if err != nil {
			return logger.Errorf("failed to fetch market data: %w", err)
		}
		
		response = resp
		return nil
	})
	
	if err != nil {
		logger.Errorf("Circuit breaker error for market data fetch: %v", err)
		return nil, err
	}
	
	logger.Infof("Market data fetched successfully")
	return response, nil
}

// FetchNewsData fetches news data from the core engine with circuit breaker protection
func (c *CoreEngineClient) FetchNewsData(ctx context.Context, req *pb.FetchNewsDataRequest) (*pb.FetchNewsDataResponse, error) {
	logger.Infof("Fetching news data from core engine with circuit breaker protection")
	
	var response *pb.FetchNewsDataResponse
	err := c.circuitBreaker.Execute(ctx, func() error {
		// Inject trace context
		ctx = c.injectTraceContext(ctx)
		
		// Add timeout to context
		ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
		defer cancel()
		
		// Make gRPC call
		resp, err := c.client.FetchNewsData(ctx, req)
		if err != nil {
			return logger.Errorf("failed to fetch news data: %w", err)
		}
		
		response = resp
		return nil
	})
	
	if err != nil {
		logger.Errorf("Circuit breaker error for news data fetch: %v", err)
		return nil, err
	}
	
	logger.Infof("News data fetched successfully")
	return response, nil
}

// GetMarketDataBuffer gets market data buffer from the core engine with circuit breaker protection
func (c *CoreEngineClient) GetMarketDataBuffer(ctx context.Context, req *pb.GetMarketDataBufferRequest) (*pb.GetMarketDataBufferResponse, error) {
	logger.Infof("Getting market data buffer from core engine with circuit breaker protection")
	
	var response *pb.GetMarketDataBufferResponse
	err := c.circuitBreaker.Execute(ctx, func() error {
		// Inject trace context
		ctx = c.injectTraceContext(ctx)
		
		// Add timeout to context
		ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
		defer cancel()
		
		// Make gRPC call
		resp, err := c.client.GetMarketDataBuffer(ctx, req)
		if err != nil {
			return logger.Errorf("failed to get market data buffer: %w", err)
		}
		
		response = resp
		return nil
	})
	
	if err != nil {
		logger.Errorf("Circuit breaker error for market data buffer: %v", err)
		return nil, err
	}
	
	logger.Infof("Market data buffer retrieved successfully")
	return response, nil
}

// GetNewsBuffer gets news buffer from the core engine with circuit breaker protection
func (c *CoreEngineClient) GetNewsBuffer(ctx context.Context, req *pb.GetNewsBufferRequest) (*pb.GetNewsBufferResponse, error) {
	logger.Infof("Getting news buffer from core engine with circuit breaker protection")
	
	var response *pb.GetNewsBufferResponse
	err := c.circuitBreaker.Execute(ctx, func() error {
		// Inject trace context
		ctx = c.injectTraceContext(ctx)
		
		// Add timeout to context
		ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
		defer cancel()
		
		// Make gRPC call
		resp, err := c.client.GetNewsBuffer(ctx, req)
		if err != nil {
			return logger.Errorf("failed to get news buffer: %w", err)
		}
		
		response = resp
		return nil
	})
	
	if err != nil {
		logger.Errorf("Circuit breaker error for news buffer: %v", err)
		return nil, err
	}
	
	logger.Infof("News buffer retrieved successfully")
	return response, nil
}

// GetIngestionStats gets ingestion stats from the core engine with circuit breaker protection
func (c *CoreEngineClient) GetIngestionStats(ctx context.Context, req *pb.GetIngestionStatsRequest) (*pb.GetIngestionStatsResponse, error) {
	logger.Infof("Getting ingestion stats from core engine with circuit breaker protection")
	
	var response *pb.GetIngestionStatsResponse
	err := c.circuitBreaker.Execute(ctx, func() error {
		// Inject trace context
		ctx = c.injectTraceContext(ctx)
		
		// Add timeout to context
		ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
		defer cancel()
		
		// Make gRPC call
		resp, err := c.client.GetIngestionStats(ctx, req)
		if err != nil {
			return logger.Errorf("failed to get ingestion stats: %w", err)
		}
		
		response = resp
		return nil
	})
	
	if err != nil {
		logger.Errorf("Circuit breaker error for ingestion stats: %v", err)
		return nil, err
	}
	
	logger.Infof("Ingestion stats retrieved successfully")
	return response, nil
}

// ConnectDataSource connects a data source to the core engine with circuit breaker protection
func (c *CoreEngineClient) ConnectDataSource(ctx context.Context, req *pb.ConnectDataSourceRequest) (*pb.ConnectDataSourceResponse, error) {
	logger.Infof("Connecting data source to core engine with circuit breaker protection")
	
	var response *pb.ConnectDataSourceResponse
	err := c.circuitBreaker.Execute(ctx, func() error {
		// Inject trace context
		ctx = c.injectTraceContext(ctx)
		
		// Add timeout to context
		ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
		defer cancel()
		
		// Make gRPC call
		resp, err := c.client.ConnectDataSource(ctx, req)
		if err != nil {
			return logger.Errorf("failed to connect data source: %w", err)
		}
		
		response = resp
		return nil
	})
	
	if err != nil {
		logger.Errorf("Circuit breaker error for data source connection: %v", err)
		return nil, err
	}
	
	logger.Infof("Data source connected successfully")
	return response, nil
}
"github.com/market-intel/api-gateway/pb
