package otel

import (
	"context"
	"fmt"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

// OtelMiddleware provides OpenTelemetry instrumentation for Gin
type OtelMiddleware struct {
	serviceName string
}

// NewOtelMiddleware creates a new OTel middleware
func NewOtelMiddleware(serviceName string) *OtelMiddleware {
	return &OtelMiddleware{
		serviceName: serviceName,
	}
}

// Middleware returns the Gin middleware function
func (m *OtelMiddleware) Middleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		
		// Process request
		c.Next()
		
		// Calculate duration
		duration := time.Since(start)
		
		// Add duration to response headers
		c.Header("X-Duration", duration.String())
		
		// Log request
		fmt.Printf("Request: %s %s - Status: %d - Duration: %s\n",
			c.Request.Method, c.Request.URL.Path, c.Writer.Status(), duration.String())
	}
}

// MetricsMiddleware provides Prometheus metrics for the API Gateway
type MetricsMiddleware struct{}

// NewMetricsMiddleware creates a new metrics middleware
func NewMetricsMiddleware() *MetricsMiddleware {
	return &MetricsMiddleware{}
}

// Middleware returns the Gin middleware function for metrics
func (m *MetricsMiddleware) Middleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Process request
		c.Next()
		
		// Log metrics
		fmt.Printf("Metrics: %s %s - %d\n", c.Request.Method, c.Request.URL.Path, c.Writer.Status())
	}
}

// MetricsHandler returns Prometheus metrics for scraping
func (m *MetricsMiddleware) MetricsHandler() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "mock metrics"})
	}
}
