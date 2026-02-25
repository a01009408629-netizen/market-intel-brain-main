package otel

import (
	"context"
	"fmt"
	"os"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/exporters/jaeger"
	"go.opentelemetry.io/otel/exporters/prometheus"
	"go.opentelemetry.io/otel/metric"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk"
	"go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/resource"
	"go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/semconv/v1.13.1/semconv"
)

const (
	serviceName    = "api-gateway"
	serviceVersion = "1.0.0"
	environment    = "development"
)

// InitOpenTelemetry initializes OpenTelemetry with appropriate exporters
func InitOpenTelemetry() error {
	// Set up Jaeger exporter for tracing
	jaegerEndpoint := os.Getenv("JAEGER_ENDPOINT")
	if jaegerEndpoint == "" {
		jaegerEndpoint = "http://localhost:14268/api/traces"
	}

	jaegerExp, err := jaeger.New(jaeger.WithCollectorEndpoint(jaegerEndpoint))
	if err != nil {
		return fmt.Errorf("failed to create Jaeger exporter: %w", err)
	}

	// Set up Prometheus exporter for metrics
	prometheusExp, err := prometheus.New()
	if err != nil {
		return fmt.Errorf("failed to create Prometheus exporter: %w", err)
	}

	// Create resource
	res, err := resource.New(
		resource.WithAttributes(
			semconv.ServiceVersionKey.String(serviceVersion),
			semconv.ServiceNameKey.String(serviceName),
			attribute.String("environment", environment),
			attribute.String("instance.id", os.Getenv("INSTANCE_ID")),
		),
	)
	if err != nil {
		return fmt.Errorf("failed to create resource: %w", err)
	}

	// Create trace provider
	traceProvider := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(otel.NewBatchSpanProcessor(jaegerExp)),
		sdktrace.WithResource(res),
	)

	// Create meter provider
	meterProvider := sdkmetric.NewMeterProvider(
		sdkmetric.WithReader(prometheusExp),
		sdkmetric.WithResource(res),
	)

	// Create OTel provider
	otel.SetTracerProvider(traceProvider)
	otel.SetMeterProvider(meterProvider)

	// Register trace propagator
	otel.SetTextMapPropagator(propagation.TraceContext{})
	otel.SetTextMapPropagator(propagation.Baggage{})

	// Create metrics
	meter := otel.Meter("market_intel_api_gateway")
	
	// Create counters
	requestCounter := meter.Int64Counter(
		"requests_total",
		"Total number of requests",
	)
	
	errorCounter := meter.Int64Counter(
		"errors_total",
		"Total number of errors",
	)
	
	// Create histogram
	requestDuration := meter.Float64Histogram(
		"request_duration_seconds",
		"Request duration in seconds",
		metric.WithUnit("s"),
		metric.WithExplicitBucketBoundaries([]float64{0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0}),
	)

	// Store metrics for later use
	RequestCounter = requestCounter
	ErrorCounter = errorCounter
	RequestDuration = requestDuration

	return nil
}

// Global metrics
var (
	RequestCounter    otel.Int64Counter
	ErrorCounter      otel.Int64Counter
	RequestDuration    otel.Float64Histogram
)

// GetTraceID extracts trace ID from context
func GetTraceID(ctx context.Context) string {
	spanCtx := trace.SpanContextFromContext(ctx)
	if !spanCtx.IsValid() {
		return ""
	}
	return spanCtx.TraceID().String()
}

// InjectTraceID injects trace ID into gRPC metadata
func InjectTraceID(ctx context.Context, metadata map[string]string) {
	if traceID := GetTraceID(ctx); traceID != "" {
		metadata["trace_id"] = traceID
	}
}

// CreateSpan creates a new span with the given name
func CreateSpan(ctx context.Context, name string, operation string) (context.Context, trace.Span) {
	tracer := otel.Tracer(serviceName)
	
	ctx, span := tracer.Start(
		ctx,
		name,
		trace.WithAttributes(
			attribute.String("operation", operation),
			attribute.String("service", serviceName),
			attribute.String("version", serviceVersion),
		),
	)
	
	return ctx, span
}

// RecordError records an error in the current span
func RecordError(ctx context.Context, span trace.Span, err error) {
	span.SetStatus(codes.Error, err.Error())
	span.RecordError(err)
	ErrorCounter.Add(ctx, 1)
}

// Shutdown gracefully shuts down OpenTelemetry
func Shutdown(ctx context.Context) error {
	// Shutdown trace provider
	if tp := otel.GetTracerProvider(); tp != nil {
		if err := tp.(interface{ Shutdown(context.Context) error }).Shutdown(ctx); err != nil {
			return fmt.Errorf("failed to shutdown tracer provider: %w", err)
		}
	}
	
	// Shutdown meter provider
	if mp := otel.GetMeterProvider(); mp != nil {
		if err := mp.(interface{ Shutdown(context.Context) error }).Shutdown(ctx); err != nil {
			return fmt.Errorf("failed to shutdown meter provider: %w", err)
		}
	}
	
	return nil
}

// RecordRequest records a request in the current span
func RecordRequest(ctx context.Context, span trace.Span, method, path string, statusCode int) {
	span.SetAttributes(
		attribute.String("http.method", method),
		attribute.String("http.path", path),
		attribute.Int("http.status_code", statusCode),
	)
	
	// Record status code as metric
	RequestCounter.Add(ctx, 1)
	
	// Record request duration
	duration := float64(time.Since(span.StartTime().UnixNano()) / 1e9)
	RequestDuration.Record(ctx, duration)
	
	// Set span status based on status code
	if statusCode >= 400 {
		span.SetStatus(codes.Error, fmt.Sprintf("HTTP %d", statusCode))
	} else {
		span.SetStatus(codes.Ok, "OK")
	}
}
