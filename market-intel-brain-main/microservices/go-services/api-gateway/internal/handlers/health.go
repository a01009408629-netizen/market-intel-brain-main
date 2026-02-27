package handlers

import (
	"context"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/market-intel/api-gateway/internal/config"
	"github.com/market-intel/api-gateway/internal/services"
	"github.com/market-intel/api-gateway/pkg/logger"
)

type HealthHandler struct {
	config           *config.Config
	coreEngineClient services.CoreEngineInterface
}

func NewHealthHandler(config *config.Config, coreEngineClient services.CoreEngineInterface) *HealthHandler {
	return &HealthHandler{
		config:           config,
		coreEngineClient: coreEngineClient,
	}
}

type HealthResponse struct {
	Status    string                 `json:"status"`
	Timestamp time.Time              `json:"timestamp"`
	Services  map[string]interface{} `json:"services"`
}

func (h *HealthHandler) Health(c *gin.Context) {
	response := HealthResponse{
		Status:    "healthy",
		Timestamp: time.Now(),
		Services:  make(map[string]interface{}),
	}

	// Check API Gateway health
	response.Services["api_gateway"] = map[string]interface{}{
		"status":      "healthy",
		"version":     "0.1.0",
		"environment": h.config.Environment,
	}

	// Check Core Engine health
	if h.coreEngineClient != nil {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		err := h.coreEngineClient.HealthCheck(ctx, "api-gateway")
		if err != nil {
			logger.Errorf("Core Engine health check failed: %v", err)
			response.Services["core_engine"] = map[string]interface{}{
				"status": "unhealthy",
				"error":  err.Error(),
			}
			response.Status = "degraded"
		} else {
			response.Services["core_engine"] = map[string]interface{}{
				"status": "healthy",
			}
		}
	}

	// Determine overall HTTP status
	httpStatus := http.StatusOK
	if response.Status == "degraded" {
		httpStatus = http.StatusServiceUnavailable
	}

	c.JSON(httpStatus, response)
}

// Ping handles simple ping request
func (h *HealthHandler) Ping(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"message": "pong",
		"timestamp": time.Now(),
	})
}

// PingCoreEngine handles ping request to core engine
func (h *HealthHandler) PingCoreEngine(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	err := h.coreEngineClient.HealthCheck(ctx, "ping")
	if err != nil {
		logger.Errorf("Core Engine ping failed: %v", err)
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"message": "Core Engine ping failed",
			"error":   err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Core Engine is responsive",
		"timestamp": time.Now(),
	})
}
