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

	pb "github.com/a01009408629-netizen/market-intel-brain-main/microservices/go-services/api-gateway/pb"
	"github.com/a01009408629-netizen/market-intel-brain-main/microservices/go-services/api-gateway/pkg/logger"
	"github.com/a01009408629-netizen/market-intel-brain-main/microservices/go-services/api-gateway/pkg/otel"
	"github.com/a01009408629-netizen/market-intel-brain-main/microservices/go-services/api-gateway/pkg/resilience"
	"github.com/a01009408629-netizen/market-intel-brain-main/microservices/go-services/api-gateway/pkg/tls"
)

// CoreEngineInterface defines all methods the client implements
type CoreEngineInterface interface {
	ProcessMarketData(ctx context.Context, data []byte) ([]byte, error)
	GetAnalytics(ctx context.Context, query string) ([]byte, error)
	HealthCheck(ctx context.Context, serviceName string) error
	Close() error
	GetStatus(ctx context.Context) error
	FetchMarketData(ctx context.Context, req *pb.FetchMarketDataRequest) (*pb.FetchMarketDataResponse, error)
	FetchNewsData(ctx context.Context, req *pb.FetchNewsDataRequest) (*pb.FetchNewsDataResponse, error)
	ConnectDataSource(ctx context.Context, req *pb.ConnectDataSourceRequest) (*pb.ConnectDataSourceResponse, error)
	GetMarketDataBuffer(ctx context.Context, req *pb.GetMarketDataBufferRequest) (*pb.GetMarketDataBufferResponse, error)
	GetNewsBuffer(ctx context.Context, req *pb.GetNewsBufferRequest) (*pb.GetNewsBufferResponse, error)
	GetIngestionStats(ctx context.Context, req *pb.GetIngestionStatsRequest) (*pb.GetIngestionStatsResponse, error)
	ExecuteWithCircuitBreaker(ctx context.Context, operation func() error) error
}

// CoreEngineClient represents a client for Core Engine service
type CoreEngineClient struct {
	conn           *grpc.ClientConn
	circuitBreaker resilience.CircuitBreakerWithRetry
}

// compile-time check
var _ CoreEngineInterface = (*CoreEngineClient)(nil)

func NewCoreEngineClient(address string) (*CoreEngineClient, error) {
	tlsConfig, err := tls.NewTLSConfigFromEnv()
	if err != nil {
		return nil, fmt.Errorf("failed to load TLS configuration: %w", err)
	}

	tlsClientConfig, err := tlsConfig.CreateTLSClientConfig()
	if err != nil {
		return nil, fmt.Errorf("failed to create TLS client config: %w", err)
	}

	grpcCreds := credentials.NewTLS(tlsClientConfig)

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

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	conn, err := grpc.DialContext(ctx, address,
		grpc.WithTransportCredentials(grpcCreds),
		grpc.WithBlock(),
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

func (c *CoreEngineClient) injectTraceContext(ctx context.Context) context.Context {
	traceID := otel.GetTraceID(ctx)
	if traceID != "" {
		md := metadata.New(map[string]string{
			"trace_id": traceID,
		})
		return metadata.NewOutgoingContext(ctx, md)
	}
	return ctx
}

func (c *CoreEngineClient) HealthCheck(ctx context.Context, serviceName string) error {
	ctx = c.injectTraceContext(ctx)
	if c.conn == nil {
		return fmt.Errorf("connection is nil")
	}
	if c.conn.GetState() != connectivity.Ready {
		return fmt.Errorf("connection is not ready")
	}
	logger.Infof("Core Engine health check passed for service: %s", serviceName)
	return nil
}

func (c *CoreEngineClient) GetStatus(ctx context.Context) error {
	_ = c.injectTraceContext(ctx)
	if c.conn == nil {
		return fmt.Errorf("connection is nil")
	}
	logger.Infof("Core Engine status retrieved successfully")
	return nil
}

func (c *CoreEngineClient) FetchMarketData(ctx context.Context, req *pb.FetchMarketDataRequest) (*pb.FetchMarketDataResponse, error) {
	logger.Infof("Fetching market data from core engine")
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

func (c *CoreEngineClient) FetchNewsData(ctx context.Context, req *pb.FetchNewsDataRequest) (*pb.FetchNewsDataResponse, error) {
	logger.Infof("Fetching news data from core engine")
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

func (c *CoreEngineClient) ConnectDataSource(ctx context.Context, req *pb.ConnectDataSourceRequest) (*pb.ConnectDataSourceResponse, error) {
	logger.Infof("Connecting data source to core engine")
	response := &pb.ConnectDataSourceResponse{
		Success: true,
		Message: "Data source connected successfully (mock)",
	}
	return response, nil
}

func (c *CoreEngineClient) GetMarketDataBuffer(ctx context.Context, req *pb.GetMarketDataBufferRequest) (*pb.GetMarketDataBufferResponse, error) {
	logger.Infof("Getting market data buffer from core engine")
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

func (c *CoreEngineClient) GetNewsBuffer(ctx context.Context, req *pb.GetNewsBufferRequest) (*pb.GetNewsBufferResponse, error) {
	logger.Infof("Getting news buffer from core engine")
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

func (c *CoreEngineClient) GetIngestionStats(ctx context.Context, req *pb.GetIngestionStatsRequest) (*pb.GetIngestionStatsResponse, error) {
	logger.Infof("Getting ingestion stats from core engine")
	response := &pb.GetIngestionStatsResponse{
		Success: true,
		Message: "Ingestion stats retrieved successfully (mock)",
	}
	return response, nil
}

func (c *CoreEngineClient) ExecuteWithCircuitBreaker(ctx context.Context, operation func() error) error {
	logger.Infof("Executing operation with circuit breaker protection")
	err := c.circuitBreaker.Execute(ctx, func() error {
		ctx := c.injectTraceContext(ctx)
		ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
		defer cancel()
		return operation()
	})
	if err != nil {
		logger.Errorf("Circuit breaker error: %v", err)
		return err
	}
	logger.Infof("Operation executed successfully")
	return nil
}

func (c *CoreEngineClient) ProcessMarketData(ctx context.Context, data []byte) ([]byte, error) {
	logger.Infof("Processing market data in core engine")
	ctx = c.injectTraceContext(ctx)
	response := []byte(`{"status":"success","message":"Market data processed successfully (mock)"}`)
	return response, nil
}

func (c *CoreEngineClient) GetAnalytics(ctx context.Context, query string) ([]byte, error) {
	logger.Infof("Retrieving analytics from core engine with query: %s", query)
	ctx = c.injectTraceContext(ctx)
	response := []byte(`{"analytics":{"result":"mock_data"},"status":"success"}`)
	return response, nil
}