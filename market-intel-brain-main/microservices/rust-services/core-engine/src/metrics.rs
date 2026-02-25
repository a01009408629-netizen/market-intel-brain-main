//! Metrics collection for the Core Engine

use opentelemetry::metrics::Counter;
use opentelemetry::metrics::Histogram;
use opentelemetry::Context;
use std::sync::OnceLock;

/// Global metrics storage
static METRICS: OnceLock<(Counter<u64>, Counter<u64>, Histogram<f64>)> = OnceLock::new();

/// Set the global metrics
pub fn set_metrics(
    request_counter: Counter<u64>,
    error_counter: Counter<u64>,
    request_duration: Histogram<f64>,
) {
    METRICS.set((request_counter, error_counter, request_duration))
        .expect("Metrics already initialized");
}

/// Get the global metrics
pub fn get_metrics() -> Option<(Counter<u64>, Counter<u64>, Histogram<f64>)> {
    METRICS.get().cloned()
}

/// Record a request
pub fn record_request(duration: std::time::Duration) {
    if let Some((request_counter, _, request_duration)) = get_metrics() {
        request_counter.add(&Context::current(), 1);
        request_duration.record(&Context::current(), duration.as_secs_f64());
    }
}

/// Record an error
pub fn record_error() {
    if let Some(_, error_counter, _) = get_metrics() {
        error_counter.add(&Context::current(), 1);
    }
}

/// Prometheus metrics exporter
pub mod prometheus {
    use prometheus::{Encoder, TextEncoder, Counter, Histogram, Registry, Opts, HistogramOpts};
    use std::sync::OnceLock;

    static REGISTRY: OnceLock<Registry> = OnceLock::new();

    pub fn get_registry() -> &'static Registry {
        REGISTRY.get_or_init(|| {
            let registry = Registry::new();
            
            // Register custom metrics
            let request_counter = Counter::with_opts(
                Opts::new("grpc_requests_total", "Total number of gRPC requests")
                    .namespace("market_intel")
                    .subsystem("core_engine")
            );
            
            let request_duration = Histogram::with_opts(
                HistogramOpts::new("grpc_request_duration_seconds", "gRPC request duration in seconds")
                    .namespace("market_intel")
                    .subsystem("core_engine")
                    .buckets(vec![0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0])
            );
            
            let error_counter = Counter::with_opts(
                Opts::new("grpc_errors_total", "Total number of gRPC errors")
                    .namespace("market_intel")
                    .subsystem("core_engine")
            );
            
            registry.register(Box::new(request_counter)).unwrap();
            registry.register(Box::new(request_duration)).unwrap();
            registry.register(Box::new(error_counter)).unwrap();
            
            registry
        })
    }

    /// Export metrics in Prometheus format
    pub fn export_metrics() -> String {
        let registry = get_registry();
        let encoder = TextEncoder::new();
        let metric_families = registry.gather();
        encoder.encode_to_string(&metric_families).unwrap()
    }

    /// Increment request counter
    pub fn increment_request_counter(method: &str, status: &str) {
        let registry = get_registry();
        let counter = registry.get_metric::<Counter>("grpc_requests_total").unwrap();
        counter.inc();
    }

    /// Record request duration
    pub fn record_request_duration(method: &str, status: &str, duration: f64) {
        let registry = get_registry();
        let histogram = registry.get_metric::<Histogram>("grpc_request_duration_seconds").unwrap();
        histogram.observe(duration);
    }

    /// Increment error counter
    pub fn increment_error_counter(method: &str, error_type: &str) {
        let registry = get_registry();
        let counter = registry.get_metric::<Counter>("grpc_errors_total").unwrap();
        counter.inc();
    }
}
