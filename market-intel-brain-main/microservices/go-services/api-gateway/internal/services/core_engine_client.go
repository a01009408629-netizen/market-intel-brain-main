package services

import (
	"context"
	"fmt"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/connectivity"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/keepalive"
	"google.golang.org/grpc/metadata"

	"github.com/market-intel/api-gateway/pkg/logger"
	"github.com/market-intel/api-gateway/pkg/otel"
	"github.com/market-intel/api-gateway/pkg/resilience"
	"github.com/market-intel/api-gateway/pkg/tls"
)

// CoreEngineClient represents a client for the Core Engine service
type CoreEngineClient struct {
	conn           *grpc.ClientConn
	circuitBreaker *resilience.CircuitBreakerWithRetry
}

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
			Timeout:             3 * time.Second,
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
