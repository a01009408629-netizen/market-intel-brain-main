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
	coreEngineClient *services.CoreEngineClient
}

func NewHealthHandler(config *config.Config, coreEngineClient *services.CoreEngineClient) *HealthHandler {
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

		coreEngineHealth, err := h.coreEngineClient.HealthCheck(ctx, "api-gateway")
		if err != nil {
			logger.Errorf("Core Engine health check failed: %v", err)
			response.Services["core_engine"] = map[string]interface{}{
				"status": "unhealthy",
				"error":  err.Error(),
			}
			response.Status = "degraded"
		} else {
			response.Services["core_engine"] = map[string]interface{}{
				"status":  "healthy",
				"version": coreEngineHealth.Version,
				"details": coreEngineHealth.Details,
			}
		}
	} else {
		response.Services["core_engine"] = map[string]interface{}{
			"status": "not_connected",
		}
		response.Status = "degraded"
	}

	// Set HTTP status based on overall health
	httpStatus := http.StatusOK
	if response.Status == "degraded" {
		httpStatus = http.StatusServiceUnavailable
	}

	c.JSON(httpStatus, response)
}

func (h *HealthHandler) Ping(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"message":   "pong",
		"service":   "api-gateway",
		"timestamp": time.Now(),
	})
}

func (h *HealthHandler) PingCoreEngine(c *gin.Context) {
	if h.coreEngineClient == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error": "Core Engine client not initialized",
		})
		return
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
	defer cancel()

	health, err := h.coreEngineClient.HealthCheck(ctx, "api-gateway")
	if err != nil {
		logger.Errorf("Failed to ping Core Engine: %v", err)
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error":   "Failed to ping Core Engine",
			"details": err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message":   "Core Engine ping successful",
		"healthy":   health.Healthy,
		"status":    health.Status,
		"version":   health.Version,
		"timestamp": time.Now(),
	})
}
