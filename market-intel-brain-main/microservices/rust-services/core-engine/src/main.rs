//! Core Engine Main Entry Point
//! 
//! This is the main entry point for the Core Engine service.
//! It initializes the gRPC server with TLS/mTLS support and starts the LMAX Disruptor engine.

use std::net::SocketAddr;
use std::sync::Arc;
use tonic::transport::{Server, ServerTlsConfig};
use tonic::transport::Identity;
use tonic::transport::Certificate;
use tracing::{info, error, warn};
use tracing_subscriber;
use tokio::signal;
use tower::ServiceBuilder;

use market_intel_core_engine::core_engine_service::CoreEngineServiceImpl;
use market_intel_core_engine::config::CoreEngineConfig;
use market_intel_core_engine::otel;
use market_intel_core_engine::tls::TlsConfig;
use market_intel_core_engine::analytics;
use market_intel_core_engine::vector_store;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize OpenTelemetry
    otel::init_telemetry("core-engine", env!("CARGO_PKG_VERSION"))?;
    
    // Initialize Analytics
    analytics::init();
    
    // Initialize Vector Store
    vector_store::init();
    
    // Set up graceful shutdown
    let (shutdown_tx, shutdown_rx) = tokio::sync::oneshot::channel::<()>();

    info!("Starting Market Intel Brain Core Engine v{}", env!("CARGO_PKG_VERSION"));

    // Load configuration
    let config = CoreEngineConfig::from_env()
        .map_err(|e| format!("Failed to load configuration: {}", e))?;
    
    // Initialize TLS configuration
    let tls_config = TlsConfig::from_env();
    
    // Validate TLS configuration
    if let Err(e) = tls_config.validate() {
        error!("TLS configuration validation failed: {}", e);
        return Err(e);
    }
    
    // Create TLS server configuration
    let server_tls_config = tls_config.create_server_tls_config()
        .map_err(|e| format!("Failed to create TLS configuration: {}", e))?;
    
    // Create gRPC service
    let core_engine_service = CoreEngineServiceImpl::new(config.clone());
    let core_engine_service = market_intel_core_engine::proto::core_engine::core_engine_service_server::CoreEngineServiceServer::new(core_engine_service);

    // Create server address
    let addr = SocketAddr::from(([0, 0, 0, 0], config.grpc_port));
    
    info!("Starting gRPC server on {} with TLS", addr);
    
    // Create server with TLS
    let server = Server::builder()
        .add_service(core_engine_service)
        .add_optional_service(
            Some(tonic_health::server::health_server::HealthServer::default()),
        );
    
    // Start server with or without TLS based on configuration
    let server_handle = if let Some(tls_config) = server_tls_config {
        info!("Starting gRPC server with mTLS enabled");
        server
            .tls_config(tls_config)
            .serve_with_shutdown(addr, shutdown_signal())
    } else {
        warn!("Starting gRPC server without TLS - NOT RECOMMENDED FOR PRODUCTION");
        server
            .serve_with_shutdown(addr, shutdown_signal())
    };
    
    // Wait for server to complete
    match server_handle.await {
        Ok(_) => {
            info!("gRPC server shutdown completed successfully");
        }
        Err(e) => {
            error!("gRPC server error: {}", e);
            return Err(e.into());
        }
    }
    
    // Shutdown OpenTelemetry
    otel::shutdown_telemetry();
    
    // Cleanup Analytics
    analytics::cleanup();
    
    // Cleanup Vector Store
    vector_store::cleanup();
    
    info!("Core Engine service shutdown complete");
    Ok(())
}

/// Signal handler for graceful shutdown
async fn shutdown_signal() {
    #[cfg(unix)]
    {
        use tokio::signal::unix::{signal, SignalKind};
        
        let mut sigterm = signal(SignalKind::terminate()).unwrap();
        let mut sigint = signal(SignalKind::interrupt()).unwrap();
        
        tokio::select! {
            _ = sigterm.recv() => info!("Received SIGTERM signal"),
            _ = sigint.recv() => info!("Received SIGINT signal"),
        }
    }
    
    #[cfg(not(unix))]
    {
        use tokio::signal;
        
        let ctrl_c = signal::ctrl_c();
        match ctrl_c.await {
            Ok(()) => info!("Received Ctrl-C signal"),
            Err(err) => error!("Failed to listen for Ctrl-C: {}", err),
        }
    }
}
