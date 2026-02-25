package server

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/market-intel/api-gateway/internal/config"
	"github.com/market-intel/api-gateway/internal/handlers"
	"github.com/market-intel/api-gateway/internal/services"
	"github.com/market-intel/api-gateway/pkg/logger"
)

type HTTPServer struct {
	config           *config.Config
	coreEngineClient *services.CoreEngineClient
	server           *http.Server
}

func NewHTTPServer(config *config.Config, coreEngineClient *services.CoreEngineClient) *HTTPServer {
	return &HTTPServer{
		config:           config,
		coreEngineClient: coreEngineClient,
	}
}

func (s *HTTPServer) SetupRoutes() *gin.Engine {
	// Set Gin mode
	if s.config.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	router := gin.New()

	// Add middleware
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
	}

	// Root endpoints
	router.GET("/health", healthHandler.Health)
	router.GET("/ping", healthHandler.Ping)
	router.GET("/ping/core-engine", healthHandler.PingCoreEngine)

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

	s.server = &http.Server{
		Addr:    s.config.GetHTTPPort(),
		Handler: router,
	}

	logger.Infof("Starting HTTP server on %s", s.config.GetHTTPPort())
	return s.server.ListenAndServe()
}

func (s *HTTPServer) Shutdown() error {
	if s.server != nil {
		return s.server.Close()
	}
	return nil
}
