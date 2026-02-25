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

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
	"github.com/spf13/viper"

	"github.com/market-intel/api-gateway/internal/config"
	"github.com/market-intel/api-gateway/internal/server"
	"github.com/market-intel/api-gateway/pkg/logger"
)

var (
	configFile = flag.String("config", "", "Path to configuration file")
	version    = flag.Bool("version", false, "Show version information")
)

func main() {
	flag.Parse()

	if *version {
		fmt.Printf("Market Intel Brain API Gateway v%s\n", config.Version)
		os.Exit(0)
	}

	// Initialize logger
	logger.Init()

	// Load configuration
	cfg, err := config.Load(*configFile)
	if err != nil {
		logrus.WithError(err).Fatal("Failed to load configuration")
	}

	logrus.WithFields(logrus.Fields{
		"version":    config.Version,
		"environment": cfg.Environment,
		"http_port":   cfg.HTTPPort,
		"grpc_port":   cfg.GRPCPort,
	}).Info("Starting Market Intel Brain API Gateway")

	// Create HTTP server
	httpServer := server.NewHTTPServer(cfg)
	
	// Create gRPC server
	grpcServer := server.NewGRPCServer(cfg)

	// Start servers in goroutines
	go func() {
		logrus.Infof("Starting HTTP server on port %d", cfg.HTTPPort)
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logrus.WithError(err).Fatal("HTTP server failed to start")
		}
	}()

	go func() {
		logrus.Infof("Starting gRPC server on port %d", cfg.GRPCPort)
		if err := grpcServer.Start(); err != nil {
			logrus.WithError(err).Fatal("gRPC server failed to start")
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logrus.Info("Shutting down servers...")

	// Graceful shutdown with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Shutdown HTTP server
	if err := httpServer.Shutdown(ctx); err != nil {
		logrus.WithError(err).Error("HTTP server shutdown error")
	}

	// Shutdown gRPC server
	grpcServer.Stop()

	logrus.Info("Servers stopped successfully")
}
