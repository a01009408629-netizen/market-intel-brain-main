package otel

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/trace"
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

		// Create span for the request
		spanName := fmt.Sprintf("%s %s %s", m.serviceName, c.Request.Method, c.Request.URL.Path)
		ctx, span := otel.Tracer(m.serviceName).Start(c.Request.Context(), spanName)
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
		log.Printf("Request: %s %s - Status: %d - TraceID: %s - Duration: %s\n",
			c.Request.Method, c.Request.URL.Path, c.Writer.Status(), traceID, duration.String())
	}
}

// MetricsMiddleware provides Prometheus metrics for the API Gateway
type MetricsMiddleware struct {
	registry *prometheus.Registry

	// Metrics
	requestCounter   *prometheus.CounterVec
	durationHistogram *prometheus.HistogramVec
	errorCounter     *prometheus.CounterVec
	activeGauge     *prometheus.Gauge
}

// NewMetricsMiddleware creates a new metrics middleware
func NewMetricsMiddleware() *MetricsMiddleware {
	registry := prometheus.NewRegistry()

	// Create metrics
	requestCounter := prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_requests_total",
			Help: "Total number of HTTP requests",
		},
		[]string{"method", "path", "status"},
	)

	durationHistogram := prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "http_request_duration_seconds",
			Help:    "HTTP request duration in seconds",
			Buckets: prometheus.ExponentialBuckets(0.001, 2, 10),
		},
		[]string{"method", "path", "status"},
	)

	errorCounter := prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_errors_total",
			Help: "Total number of HTTP errors",
		},
		[]string{"method", "path", "status"},
	)

	activeGauge := prometheus.NewGauge(
		prometheus.GaugeOpts{
			Name: "http_connections_active",
			Help: "Number of active HTTP connections",
		},
	)

	// Register metrics
	registry.MustRegister(requestCounter)
	registry.MustRegister(durationHistogram)
	registry.MustRegister(errorCounter)
	registry.MustRegister(activeGauge)

	return &MetricsMiddleware{
		registry:          registry,
		requestCounter:    requestCounter,
		durationHistogram: durationHistogram,
		errorCounter:      errorCounter,
		activeGauge:       activeGauge,
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
		m.requestCounter.WithLabelValues(method, path, status).Inc()

		// Record request duration
		m.durationHistogram.WithLabelValues(method, path, status).Observe(duration)

		// Record errors
		if c.Writer.Status() >= 400 {
			m.errorCounter.WithLabelValues(method, path, status).Inc()
		}

		// Update active connections gauge
		m.activeGauge.Set(float64(c.Writer.Size()))
	}
}

// MetricsHandler returns Prometheus metrics for scraping
func (m *MetricsMiddleware) MetricsHandler() gin.HandlerFunc {
	return promhttp.HandlerFor(m.registry, promhttp.HandlerOpts{})
}
