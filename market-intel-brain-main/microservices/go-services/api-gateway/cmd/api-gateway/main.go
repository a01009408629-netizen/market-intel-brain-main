package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/market-intel/api-gateway/internal/config"
	"github.com/market-intel/api-gateway/internal/server"
	"github.com/market-intel/api-gateway/internal/services"
	"github.com/market-intel/api-gateway/pkg/logger"
)

var (
	configFile = flag.String("config", "", "Path to configuration file")
	version    = flag.Bool("version", false, "Show version information")
)

const Version = "0.1.0"

func main() {
	flag.Parse()

	if *version {
		fmt.Printf("Market Intel Brain API Gateway v%s\n", Version)
		os.Exit(0)
	}

	// Initialize logger
	logger.Init()

	// Load configuration
	cfg, err := config.Load(*configFile)
	if err != nil {
		logger.Fatalf("Failed to load configuration: %v", err)
	}

	logger.WithFields(map[string]interface{}{
		"version":    Version,
		"environment": cfg.Environment,
		"http_port":   cfg.HTTPPort,
		"grpc_port":   cfg.GRPCPort,
	}).Info("Starting Market Intel Brain API Gateway")

	// Create Core Engine client
	coreEngineClient, err := services.NewCoreEngineClient(cfg.CoreEngineURL)
	if err != nil {
		logger.Errorf("Failed to create Core Engine client: %v", err)
		// Continue without Core Engine connection for now
		coreEngineClient = nil
	} else {
		defer coreEngineClient.Close()
	}

	// Create HTTP server
	httpServer := server.NewHTTPServer(cfg, coreEngineClient)
	
	// Create gRPC server
	grpcServer := server.NewGRPCServer(cfg)

	// Start servers in goroutines
	go func() {
		logger.Infof("Starting HTTP server on port %d", cfg.HTTPPort)
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatalf("HTTP server failed to start: %v", err)
		}
	}()

	go func() {
		logger.Infof("Starting gRPC server on port %d", cfg.GRPCPort)
		if err := grpcServer.Start(); err != nil {
			logger.Errorf("gRPC server failed to start: %v", err)
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("Shutting down servers...")

	// Graceful shutdown with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Shutdown HTTP server
	if err := httpServer.Shutdown(); err != nil {
		logger.Errorf("HTTP server shutdown error: %v", err)
	}

	// Shutdown gRPC server
	grpcServer.Stop()

	logger.Info("Servers stopped successfully")
}
