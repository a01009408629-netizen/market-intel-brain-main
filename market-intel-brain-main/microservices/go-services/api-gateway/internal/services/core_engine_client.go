package services

import (
	"context"
	"fmt"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	pb "github.com/market-intel/api-gateway/proto"
	"github.com/market-intel/api-gateway/pkg/logger"
)

type CoreEngineClient struct {
	conn   *grpc.ClientConn
	client pb.CoreEngineServiceClient
}

func NewCoreEngineClient(address string) (*CoreEngineClient, error) {
	// Create connection with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	conn, err := grpc.DialContext(ctx, address, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		logger.Errorf("Failed to connect to Core Engine: %v", err)
		return nil, fmt.Errorf("failed to connect to Core Engine: %w", err)
	}

	client := pb.NewCoreEngineServiceClient(conn)

	logger.Infof("Connected to Core Engine at %s", address)

	return &CoreEngineClient{
		conn:   conn,
		client: client,
	}, nil
}

func (c *CoreEngineClient) Close() error {
	if c.conn != nil {
		return c.conn.Close()
	}
	return nil
}

func (c *CoreEngineClient) HealthCheck(ctx context.Context, serviceName string) (*pb.HealthCheckResponse, error) {
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
	req := &pb.Empty{}

	resp, err := c.client.GetStatus(ctx, req)
	if err != nil {
		logger.Errorf("Core Engine get status failed: %v", err)
		return nil, fmt.Errorf("get status failed: %w", err)
	}

	logger.Infof("Core Engine status: %s", resp.Message)

	return resp, nil
}

// Data Ingestion Methods

func (c *CoreEngineClient) FetchMarketData(ctx context.Context, req *pb.FetchMarketDataRequest) (*pb.FetchMarketDataResponse, error) {
	resp, err := c.client.FetchMarketData(ctx, req)
	if err != nil {
		logger.Errorf("Failed to fetch market data: %v", err)
		return nil, fmt.Errorf("fetch market data failed: %w", err)
	}

	logger.Infof("Fetched market data: status=%s, items=%d", resp.Status.String(), len(resp.MarketData))

	return resp, nil
}

func (c *CoreEngineClient) FetchNewsData(ctx context.Context, req *pb.FetchNewsDataRequest) (*pb.FetchNewsDataResponse, error) {
	resp, err := c.client.FetchNewsData(ctx, req)
	if err != nil {
		logger.Errorf("Failed to fetch news data: %v", err)
		return nil, fmt.Errorf("fetch news data failed: %w", err)
	}

	logger.Infof("Fetched news data: status=%s, items=%d", resp.Status.String(), len(resp.NewsItems))

	return resp, nil
}

func (c *CoreEngineClient) GetMarketDataBuffer(ctx context.Context, req *pb.GetMarketDataBufferRequest) (*pb.GetMarketDataBufferResponse, error) {
	resp, err := c.client.GetMarketDataBuffer(ctx, req)
	if err != nil {
		logger.Errorf("Failed to get market data buffer: %v", err)
		return nil, fmt.Errorf("get market data buffer failed: %w", err)
	}

	logger.Infof("Got market data buffer: status=%s, items=%d", resp.Status.String(), len(resp.MarketData))

	return resp, nil
}

func (c *CoreEngineClient) GetNewsBuffer(ctx context.Context, req *pb.GetNewsBufferRequest) (*pb.GetNewsBufferResponse, error) {
	resp, err := c.client.GetNewsBuffer(ctx, req)
	if err != nil {
		logger.Errorf("Failed to get news buffer: %v", err)
		return nil, fmt.Errorf("get news buffer failed: %w", err)
	}

	logger.Infof("Got news buffer: status=%s, items=%d", resp.Status.String(), len(resp.NewsItems))

	return resp, nil
}

func (c *CoreEngineClient) GetIngestionStats(ctx context.Context, req *pb.Empty) (*pb.GetIngestionStatsResponse, error) {
	resp, err := c.client.GetIngestionStats(ctx, req)
	if err != nil {
		logger.Errorf("Failed to get ingestion stats: %v", err)
		return nil, fmt.Errorf("get ingestion stats failed: %w", err)
	}

	logger.Infof("Got ingestion stats: status=%s", resp.Status.String())

	return resp, nil
}

func (c *CoreEngineClient) ConnectDataSource(ctx context.Context, req *pb.ConnectDataSourceRequest) (*pb.ConnectDataSourceResponse, error) {
	resp, err := c.client.ConnectDataSource(ctx, req)
	if err != nil {
		logger.Errorf("Failed to connect to data source: %v", err)
		return nil, fmt.Errorf("connect data source failed: %w", err)
	}

	logger.Infof("Data source connection: source_id=%s, connected=%v, status=%s", 
		req.SourceId, resp.Connected, resp.Status.String())

	return resp, nil
}
