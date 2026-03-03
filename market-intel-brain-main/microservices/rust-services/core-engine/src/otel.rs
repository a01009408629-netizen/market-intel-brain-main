use opentelemetry::global;
use opentelemetry_sdk::propagation::TraceContextPropagator;
use opentelemetry_sdk::trace::{RandomIdGenerator, Sampler};
use opentelemetry_sdk::{trace as sdktrace, Resource};
use opentelemetry::KeyValue;
use tracing::info;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter, fmt};
use tracing_opentelemetry;
use opentelemetry_jaeger;

pub fn init_telemetry(service_name: &str, service_version: &str) -> anyhow::Result<()> {
    let jaeger_endpoint = std::env::var("JAEGER_ENDPOINT")
        .unwrap_or_else(|_| "http://localhost:14268/api/traces".to_string());

    let tracer = opentelemetry_jaeger::new_collector_pipeline()
        .with_endpoint(jaeger_endpoint)
        .with_service_name(service_name)
        .with_trace_config(
            sdktrace::config()
                .with_sampler(Sampler::AlwaysOn)
                .with_id_generator(RandomIdGenerator::default())
                .with_resource(Resource::new(vec![
                    KeyValue::new("service.name", service_name.to_string()),
                    KeyValue::new("service.version", service_version.to_string()),
                    KeyValue::new("environment",
                        std::env::var("ENVIRONMENT")
                            .unwrap_or_else(|_| "development".to_string())),
                ]))
        )
        .install_batch(opentelemetry_sdk::runtime::Tokio)?;

    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info".into()),
        )
        .with(tracing_subscriber::fmt::layer().json())
        .with(tracing_opentelemetry::layer().with_tracer(tracer))
        .init();

    global::set_text_map_propagator(TraceContextPropagator::new());

    info!("OpenTelemetry initialized");
    Ok(())
}

pub fn shutdown_telemetry() {
    global::shutdown_tracer_provider();
    tracing::info!("OpenTelemetry shutdown");
}