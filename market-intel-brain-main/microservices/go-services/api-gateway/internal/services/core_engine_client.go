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
