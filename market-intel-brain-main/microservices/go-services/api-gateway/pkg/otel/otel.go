package otel

import (
	"context"

	"log"
)

// InitOpenTelemetry initializes OpenTelemetry with minimal setup
func InitOpenTelemetry() error {
	log.Println("OpenTelemetry initialized (minimal setup)")
	return nil
}

// Shutdown gracefully shuts down OpenTelemetry
func Shutdown(ctx context.Context) error {
	log.Println("OpenTelemetry shutdown")
	return nil
}

// GetTraceID extracts trace ID from context
func GetTraceID(ctx context.Context) string {
	return "mock-trace-id"
}

// CreateSpan creates a new span with the given name
func CreateSpan(ctx context.Context, name string, operation string) (context.Context, interface{}) {
	return ctx, "mock-span"
}

// RecordError records an error in the current span
func RecordError(ctx context.Context, span interface{}, err error) {
	log.Printf("Error recorded: %v", err)
}

// RecordRequest records a request in the current span
func RecordRequest(ctx context.Context, span interface{}, method, path string, statusCode int) {
	log.Printf("Request recorded: %s %s - %d", method, path, statusCode)
}
