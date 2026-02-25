package server

import (
	"net/http"
	"net/http/pprof"
	"runtime"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/market-intel/api-gateway/internal/config"
	"github.com/market-intel/api-gateway/internal/handlers"
	"github.com/market-intel/api-gateway/internal/services"
	"github.com/market-intel/api-gateway/pkg/logger"
	"github.com/market-intel/api-gateway/pkg/otel"
)

type HTTPServer struct {
	config           *config.Config
	coreEngineClient *services.CoreEngineClient
	server           *http.Server
	otelMiddleware    *otel.OtelMiddleware
	metricsMiddleware *otel.MetricsMiddleware
}

func NewHTTPServer(config *config.Config, coreEngineClient *services.CoreEngineClient) *HTTPServer {
	return &HTTPServer{
		config:           config,
		coreEngineClient: coreEngineClient,
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
		router.GET("/debug/pprof/", gin.WrapF(http.HandlerFunc(pprof.Index)))
		router.GET("/debug/pprof/cmdline", gin.WrapF(http.HandlerFunc(pprof.Cmdline)))
		router.GET("/debug/pprof/profile", gin.WrapF(http.HandlerFunc(pprof.Profile)))
		router.GET("/debug/pprof/symbol", gin.WrapF(http.HandlerFunc(pprof.Symbol)))
		router.GET("/debug/pprof/trace", gin.WrapF(http.HandlerFunc(pprof.Trace)))
		router.GET("/debug/pprof/heap", gin.WrapF(http.HandlerFunc(pprof.Heap)))
		router.GET("/debug/pprof/goroutine", gin.WrapF(http.HandlerFunc(pprof.Goroutine)))
		router.GET("/debug/pprof/threadcreate", gin.WrapF(http.HandlerFunc(pprof.ThreadCreate)))
		router.GET("/debug/pprof/block", gin.WrapF(http.HandlerFunc(pprof.Block)))
		router.GET("/debug/pprof/mutex", gin.WrapF(http.HandlerFunc(pprof.Mutex)))
		
		// Additional profiling endpoints
		router.GET("/debug/pprof/allocs", gin.WrapF(http.HandlerFunc(pprof.Allocs)))
		router.GET("/debug/pprof/lookups", gin.WrapF(http.HandlerFunc(pprof.Lookups)))
		router.GET("/debug/pprof/schedtrace", gin.WrapF(http.HandlerFunc(pprof.SchedTrace)))
		router.GET("/debug/pprof/syscall", gin.WrapF(http.HandlerFunc(pprof.Syscall)))
	}

	// Legacy compatibility endpoints (redirect to v1)
	router.GET("/api/market-data/fetch", func(c *gin.Context) {
		c.Redirect(301, "/api/v1/market-data/fetch")
	})
	router.GET("/api/news/fetch", func(c *gin.Context) {
		c.Redirect(301, "/api/v1/news/fetch")
	})
	router.GET("/api/market-data/buffer", func(c *gin.Context) {
		c.Redirect(301, "/api/v1/market-data/buffer")
	})
	router.GET("/api/news/buffer", func(c *gin.Context) {
		c.Redirect(301, "/api/v1/news/buffer")
	})

	return router
}

func (s *HTTPServer) ListenAndServe() error {
	router := s.SetupRoutes()

	// Create a custom server with profiling support
	s.server = &http.Server{
		Addr:    s.config.GetHTTPPort(),
		Handler: router,
		// Configure timeouts for production
		ReadTimeout:       30 * time.Second,
		WriteTimeout:      30 * time.Second,
		ReadHeaderTimeout: 10 * time.Second,
		IdleTimeout:       60 * time.Second,
		MaxHeaderBytes:    1 << 20, // 1MB
	}

	logger.Infof("Starting HTTP server on %s", s.config.GetHTTPPort())
	logger.Infof("Profiling endpoints available at: http://localhost%s/debug/pprof/", s.config.GetHTTPPort())
	logger.Infof("GOMAXPROCS set to: %d", runtime.GOMAXPROCS(0))

	return s.server.ListenAndServe()
}

func (s *HTTPServer) Shutdown() error {
	if s.server != nil {
		return s.server.Close()
	}
	return nil
}
