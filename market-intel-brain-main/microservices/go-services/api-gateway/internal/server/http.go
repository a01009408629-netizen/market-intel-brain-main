package server

import (
	"context"
	"net/http"
	"net/http/pprof"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/market-intel/api-gateway/internal/config"
	"github.com/market-intel/api-gateway/internal/handlers"
	"github.com/market-intel/api-gateway/internal/services"
	"github.com/market-intel/api-gateway/pkg/logger"
	"github.com/market-intel/api-gateway/pkg/otel"
)

type HTTPServer struct {
	config            *config.Config
	coreEngineClient  *services.CoreEngineClient
	server            *http.Server
	otelMiddleware    *otel.OtelMiddleware
	metricsMiddleware *otel.MetricsMiddleware
}

func NewHTTPServer(config *config.Config, coreEngineClient *services.CoreEngineClient) *HTTPServer {
	return &HTTPServer{
		config:            config,
		coreEngineClient:  coreEngineClient,
		otelMiddleware:    otel.NewOtelMiddleware("api-gateway"),
		metricsMiddleware: otel.NewMetricsMiddleware(),
	}
}

func (s *HTTPServer) SetupRoutes() *gin.Engine {
	// Set Gin mode
	if s.config.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	router := gin.New()

	// Add OpenTelemetry middleware first (to trace all requests)
	router.Use(s.otelMiddleware.Middleware())

	// Add metrics middleware
	router.Use(s.metricsMiddleware.Middleware())

	// Add logging middleware
	router.Use(gin.Logger())
	router.Use(gin.Recovery())

	// Add CORS middleware
	router.Use(func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Origin, Content-Type, Accept, Authorization")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	})

	// Create handlers
	healthHandler := handlers.NewHealthHandler(s.config, s.coreEngineClient)
	dataIngestionHandler := handlers.NewDataIngestionHandler(s.config, s.coreEngineClient)

	// Setup routes
	v1 := router.Group("/api/v1")
	{
		// Health endpoints
		v1.GET("/health", healthHandler.Health)
		v1.GET("/ping", healthHandler.Ping)
		v1.GET("/ping/core-engine", healthHandler.PingCoreEngine)

		// Data ingestion endpoints
		v1.POST("/market-data/fetch", dataIngestionHandler.FetchMarketData)
		v1.POST("/news/fetch", dataIngestionHandler.FetchNewsData)
		v1.GET("/market-data/buffer", dataIngestionHandler.GetMarketDataBuffer)
		v1.GET("/news/buffer", dataIngestionHandler.GetNewsBuffer)
		v1.GET("/ingestion/stats", dataIngestionHandler.GetIngestionStats)
		v1.POST("/data-sources/connect", dataIngestionHandler.ConnectDataSource)

		// WebSocket endpoints
		v1.GET("/ws/market-data", dataIngestionHandler.WebSocketMarketData)

		// Metrics endpoint (Prometheus)
		v1.GET("/metrics", s.metricsMiddleware.MetricsHandler())
	}

	// Root endpoints
	router.GET("/health", healthHandler.Health)
	router.GET("/ping", healthHandler.Ping)
	router.GET("/ping/core-engine", healthHandler.PingCoreEngine)

	// Profiling endpoints (only in non-production environments)
	if s.config.Environment != "production" {
		router.GET("/debug/pprof/", gin.WrapF(pprof.Index))
		router.GET("/debug/pprof/cmdline", gin.WrapF(pprof.Cmdline))
		router.GET("/debug/pprof/profile", gin.WrapF(pprof.Profile))
		router.GET("/debug/pprof/symbol", gin.WrapF(pprof.Symbol))
		router.GET("/debug/pprof/trace", gin.WrapF(pprof.Trace))
		router.GET("/debug/pprof/goroutine", gin.WrapF(pprof.Handler("goroutine").ServeHTTP))
		router.GET("/debug/pprof/heap", gin.WrapF(pprof.Handler("heap").ServeHTTP))
		router.GET("/debug/pprof/threadcreate", gin.WrapF(pprof.Handler("threadcreate").ServeHTTP))
		router.GET("/debug/pprof/block", gin.WrapF(pprof.Handler("block").ServeHTTP))
	}

	return router
}

func (s *HTTPServer) Start(addr string) error {
	s.server = &http.Server{
		Addr:    addr,
		Handler:  s.SetupRoutes(),
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	logger.Infof("Starting HTTP server on %s", addr)
	return s.server.ListenAndServe()
}

func (s *HTTPServer) Shutdown(ctx context.Context) error {
	logger.Infof("Shutting down HTTP server...")
	return s.server.Shutdown(ctx)
}

func (s *HTTPServer) GetServer() *http.Server {
	return s.server
}
