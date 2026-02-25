package server

import (
	"net"

	"github.com/market-intel/api-gateway/internal/config"
	"github.com/market-intel/api-gateway/pkg/logger"
)

type GRPCServer struct {
	config *config.Config
}

func NewGRPCServer(config *config.Config) *GRPCServer {
	return &GRPCServer{
		config: config,
	}
}

func (s *GRPCServer) Start() error {
	// TODO: Implement gRPC server for API Gateway
	// This will be used for inter-service communication
	logger.Infof("gRPC server not yet implemented for API Gateway")
	return nil
}

func (s *GRPCServer) Stop() error {
	// TODO: Implement gRPC server shutdown
	return nil
}

func (s *GRPCServer) Listen() (net.Listener, error) {
	return net.Listen("tcp", s.config.GetGRPCPort())
}
