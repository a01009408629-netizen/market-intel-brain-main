//! OpenTelemetry configuration and utilities for the Core Engine

use opentelemetry::global;
use opentelemetry::propagation::Extractor;
use opentelemetry::sdk::propagation::TraceContextPropagator;
use opentelemetry::sdk::trace::{self, RandomIdGenerator, Sampler};
use opentelemetry::sdk::{trace as sdktrace, Resource};
use opentelemetry::KeyValue;
use opentelemetry::trace::{Span, Tracer};
use opentelemetry::{Context, propagation::TextMapCompositePropagator};
use opentelemetry_jaeger::Propagator as JaegerPropagator;
use opentelemetry_semantic_conventions as semcov;
use tonic::metadata::MetadataMap;
use tracing::info;
use tracing_opentelemetry::OpenTelemetrySpanExt;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

/// Initialize OpenTelemetry with Jaeger and Prometheus exporters
pub fn init_telemetry(service_name: &str, service_version: &str) -> anyhow::Result<()> {
    // Set up Jaeger exporter for tracing
    let jaeger_endpoint = std::env::var("JAEGER_ENDPOINT")
        .unwrap_or_else(|_| "http://localhost:14268/api/traces".to_string());

    let jaeger_exporter = opentelemetry_jaeger::new_agent_pipeline()
        .with_endpoint(jaeger_endpoint)
        .with_service_name(service_name)
        .with_trace_config(
            sdktrace::config()
                .with_sampler(Sampler::AlwaysOn)
                .with_id_generator(RandomIdGenerator::default())
                .with_resource(Resource::new(vec![
                    KeyValue::new(semcov::SERVICE_NAME, service_name),
                    KeyValue::new(semcov::SERVICE_VERSION, service_version),
                    KeyValue::new("environment", std::env::var("ENVIRONMENT").unwrap_or_else(|_| "development".to_string())),
                    KeyValue::new("instance_id", std::env::var("INSTANCE_ID").unwrap_or_else(|_| "unknown".to_string())),
                ]))
        )
        .install_batch(opentelemetry::runtime::Tokio)?;

    // Set up Prometheus exporter for metrics
    let prometheus_exporter = opentelemetry_prometheus::exporter()
        .with_registry(prometheus::Registry::new())
        .build()?;

    // Create a meter for metrics
    let meter = opentelemetry::global::meter(service_name);

    // Create metrics
    let request_counter = meter
        .u64_counter("requests_total")
        .with_description("Total number of requests")
        .init();

    let error_counter = meter
        .u64_counter("errors_total")
        .with_description("Total number of errors")
        .init();

    let request_duration = meter
        .f64_histogram("request_duration_seconds")
        .with_description("Request duration in seconds")
        .with_unit("s")
        .init();

    // Store metrics globally for later use
    crate::metrics::set_metrics(request_counter, error_counter, request_duration);

    // Set up tracing subscriber with OpenTelemetry layer
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "market_intel_core_engine=debug,tower_http=debug,axum::rejection=trace".into()),
        )
        .with(tracing_subscriber::fmt::layer().json())
        .with(tracing_opentelemetry::layer().with_tracer(jaeger_exporter))
        .init();

    // Set global propagator
    global::set_text_map_propagator(TextMapCompositePropagator::new(vec![
        Box::new(JaegerPropagator::new()),
        Box::new(TraceContextPropagator::new()),
    ]));

    info!("OpenTelemetry initialized successfully");
    Ok(())
}

/// Extract trace ID from gRPC metadata
pub fn extract_trace_id(metadata: &MetadataMap) -> Option<String> {
    let extractor = GrpcMetadataExtractor { metadata };
    let context = global::get_text_map_propagator(|propagator| {
        propagator.extract(&extractor)
    });

    let span_context = context.span().span_context();
    if span_context.is_valid() {
        Some(span_context.trace_id().to_string())
    } else {
        None
    }
}

/// Extractor for gRPC metadata
struct GrpcMetadataExtractor<'a> {
    metadata: &'a MetadataMap,
}

impl<'a> Extractor for GrpcMetadataExtractor<'a> {
    fn get(&self, key: &str) -> Option<&str> {
        self.metadata.get(key).map(|value| value.to_str().unwrap_or(""))
    }

    fn keys(&self) -> Vec<&str> {
        self.metadata
            .keys()
            .map(|key| key.to_str().unwrap_or(""))
            .collect()
    }
}

/// Create a span with the given name and operation
pub fn create_span(
    name: &str,
    operation: &str,
    trace_id: Option<String>,
) -> Span {
    let mut span = tracing::info_span!(
        name,
        operation = operation,
        service = "core-engine",
    );

    if let Some(trace_id) = trace_id {
        span.record("trace_id", &trace_id);
    }

    span
}

/// Record an error in the current span
pub fn record_error(span: &Span, error: &anyhow::Error) {
    span.record("error", true);
    span.record("error.message", &error.to_string());
    
    // Increment error counter
    if let Some((_, _, error_counter)) = crate::metrics::get_metrics() {
        error_counter.add(&Context::current(), 1);
    }
}

/// Record a request in the current span
pub fn record_request(
    span: &Span,
    method: &str,
    status: &str,
    duration: std::time::Duration,
) {
    span.record("grpc.method", method);
    span.record("grpc.status", status);
    span.record("duration_ms", duration.as_millis());

    // Increment request counter
    if let Some((request_counter, _, _)) = crate::metrics::get_metrics() {
        request_counter.add(&Context::current(), 1);
    }

    // Record duration
    if let Some((_, _, request_duration)) = crate::metrics::get_metrics() {
        request_duration.record(&Context::current(), duration.as_secs_f64());
    }
}

/// Shutdown OpenTelemetry gracefully
pub fn shutdown_telemetry() {
    global::shutdown_tracer_provider();
    info!("OpenTelemetry shutdown completed");
}

#[cfg(test)]
mod tests {
    use super::*;
    use tonic::metadata::MetadataValue;

    #[test]
    fn test_extract_trace_id() {
        let mut metadata = MetadataMap::new();
        metadata.insert("trace_id", MetadataValue::from_static("1234567890abcdef1234567890abcdef"));

        let trace_id = extract_trace_id(&metadata);
        assert_eq!(trace_id, Some("1234567890abcdef1234567890abcdef".to_string()));
    }

    #[test]
    fn test_extract_trace_id_missing() {
        let metadata = MetadataMap::new();

        let trace_id = extract_trace_id(&metadata);
        assert_eq!(trace_id, None);
    }
}
