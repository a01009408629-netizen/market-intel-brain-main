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
	"github.com/market-intel/api-gateway/pkg/otel"
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

	// Initialize structured logging
	logger.Init()

	// Initialize OpenTelemetry
	if err := otel.InitOpenTelemetry(); err != nil {
		logger.Fatalf("Failed to initialize OpenTelemetry: %v", err)
	}
	defer func() {
		if err := otel.Shutdown(context.Background()); err != nil {
			logger.Errorf("Failed to shutdown OpenTelemetry: %v", err)
		}
	}()

	logger.Info("Starting Market Intel Brain API Gateway")

	// Load configuration
	config, err := config.Load(*configFile)
	if err != nil {
		logger.Fatalf("Failed to load configuration: %v", err)
	}

	logger.WithFields(map[string]interface{}{
		"version":    Version,
		"environment": config.Environment,
		"http_port":   config.HTTPPort,
		"grpc_port":   config.GRPCPort,
	}).Info("Starting Market Intel Brain API Gateway")

	// Create core engine client
	coreEngineClient, err := services.NewCoreEngineClient(config.CoreEngineURL)
	if err != nil {
		logger.Errorf("Failed to create Core Engine client: %v", err)
		// Continue without Core Engine connection for now
		coreEngineClient = nil
	} else {
		defer coreEngineClient.Close()
	}

	// Create HTTP server
	httpServer := server.NewHTTPServer(config, coreEngineClient)
	
	// Create gRPC server
	grpcServer := server.NewGRPCServer(config)

	// Start servers in goroutines
	go func() {
		logger.Infof("Starting HTTP server on port %d", config.HTTPPort)
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatalf("HTTP server failed to start: %v", err)
		}
	}()

	go func() {
		logger.Infof("Starting gRPC server on port %d", config.GRPCPort)
		if err := grpcServer.Start(); err != nil {
			logger.Errorf("gRPC server failed to start: %v", err)
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("Shutting down servers...")

	// Create a deadline for shutdown
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
