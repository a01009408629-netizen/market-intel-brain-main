package otel

import (
	"context"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/trace"
	"github.com/market-intel/api-gateway/pkg/otel"
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
	// Start time for request duration measurement
		start := time.Now()
		
	// Extract trace context from headers if present
	spanCtx := otel.TraceContextFromContext(c.Request.Context())
		ctx := otel.ContextWithSpan(spanCtx, "http-request")
		
	// Create span for the request
		spanName := fmt.Sprintf("%s %s %s", m.serviceName, c.Request.Method, c.Request.URL.Path)
		ctx, span := otel.Start(ctx, spanName)
		defer span.End()
		
	// Store span in context for later use
		c.Request = c.Request.WithContext(ctx)
		
	// Process request
		c.Next()
		
	// Calculate duration
		duration := time.Since(start)
		
	// Record request metrics
		otel.RecordRequest(span, c.Request.Method, c.Request.URL.Path, c.Writer.Status())
		
	// Add trace ID to response headers
		if traceID := otel.GetTraceID(c.Request.Context()); traceID != "" {
			c.Header("X-Trace-ID", traceID)
		}
		
	// Add duration to response headers
		c.Header("X-Duration", duration.String())
		
	// Log request with trace ID
		traceID := otel.GetTraceID(c.Request.Context())
		logrus.WithFields(logrus.Fields{
			"method":    c.Request.Method,
			"path":      c.Request.URL.Path,
			"status":    c.Writer.Status(),
			"trace_id":  traceID,
			"duration":  duration.String(),
		}).Info("Request completed")
	}
}

// MetricsMiddleware provides Prometheus metrics for the API Gateway
type MetricsMiddleware struct {
	registry *prometheus.Registry
}

// NewMetricsMiddleware creates a new metrics middleware
func NewMetricsMiddleware() *MetricsMiddleware {
	registry := prometheus.NewRegistry()
	
	// Create metrics
	registry.MustRegister(prometheus.NewCounter(
		"http_requests_total",
		"Total number of HTTP requests",
		[]string{"method", "path", "status"},
	))
	
	registry.MustRegister(prometheus.NewHistogram(
		"http_request_duration_seconds",
		"HTTP request duration in seconds",
		[]string{"method", "path", "status"},
		prometheus.ExponentialBuckets(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
	))
	
	registry.MustRegister(prometheus.NewCounter(
		"http_errors_total",
		"Total number of HTTP errors",
		[]string{"method", "path", "status"},
	))
	
	registry.MustRegister(prometheus.NewGauge(
		"http_connections_active",
		"Number of active HTTP connections",
	))
	
	return &MetricsMiddleware{
		registry: registry,
	}
}

// Middleware returns the Gin middleware function for metrics
func (m *MetricsMiddleware) Middleware() gin.HandlerFunc {
	return func(c *gin.Context) {
	// Start time for request duration measurement
		start := time.Now()
		
	// Process request
		c.Next()
		
	// Calculate duration
		duration := time.Since(start).Seconds()
		
	// Record metrics
		method := c.Request.Method
		path := c.Request.URL.Path
		status := strconv.Itoa(c.Writer.Status())
		
	// Increment request counter
		m.registry.MustRegister(
			prometheus.NewCounterVec(
				prometheus.CounterOpts{
					Name: "http_requests_total",
					Help: "Total number of HTTP requests",
				},
			),
		).WithLabelValues(
			prometheus.Labels{
				"method": method,
				"path":   path,
				"status": status,
			},
	).Inc()
		
	// Record request duration
		m.registry.MustRegister(
			prometheus.NewHistogramVec(
				prometheus.HistogramOpts{
					Name:    "http_request_duration_seconds",
					Help:    "HTTP request duration in seconds",
					Buckets: []float64{0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0},
				},
			),
		).WithLabelValues(
			prometheus.Labels{
				"method": method,
				"path":   path,
				"status": status,
			},
	).Observe(duration)
		
	// Record errors
		if c.Writer.Status() >= 400 {
			m.registry.MustRegister(
				prometheus.NewCounterVec(
					prometheus.CounterOpts{
						Name: "http_errors_total",
						Help: "Total number of HTTP errors",
					},
				),
			).WithLabelValues(
				prometheus.Labels{
					"method": method,
					"path":   path,
					"status": status,
				},
			).Inc()
		}
		
		// Update active connections gauge
		m.registry.MustRegister(
			prometheus.NewGauge(
				prometheus.GaugeOpts{
					Name: "http_connections_active",
					Help: "Number of active HTTP connections",
				},
			).Set(float64(c.Writer.Size()))
		)
	}
}

// MetricsHandler returns Prometheus metrics for scraping
func (m *MetricsMiddleware) MetricsHandler() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Enable Prometheus metrics endpoint
		promhttp.Handler()
	}
}
