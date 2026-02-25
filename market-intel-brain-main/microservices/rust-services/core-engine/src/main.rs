//! Core Engine Main Entry Point
//! 
//! This is the main entry point for the Core Engine service.
//! It initializes the gRPC server and starts the LMAX Disruptor engine.

use std::net::SocketAddr;
use tonic::transport::Server;
use tracing::{info, error, warn};
use tracing_subscriber;
use tokio::signal;

mod core_engine_service;
mod config;
mod data_ingestion;

use core_engine_service::CoreEngineServiceImpl;
use config::CoreEngineConfig;
use crate::otel;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize OpenTelemetry
    otel::init_telemetry("core-engine", env!("CARGO_PKG_VERSION"))?;
    
    // Set up graceful shutdown
    let (shutdown_tx, shutdown_rx) = tokio::sync::oneshot::channel::<()>();

    info!("Starting Market Intel Brain Core Engine v{}", env!("CARGO_PKG_VERSION"));

    // Load configuration
    let config = CoreEngineConfig::from_env()?;
    info!("Loaded configuration: {:?}", config);

    // Create core engine service
    let core_engine_service = CoreEngineServiceImpl::new(config.clone())?;

    // Start background data collection
    if let Err(e) = core_engine_service.data_ingestion.start_background_collection() {
        warn!("Failed to start background collection: {}", e);
    }

    // Create gRPC server
    let addr = SocketAddr::from(([0, 0, 0, 0], config.grpc_port));
    info!("Core Engine gRPC server listening on {}", addr);

    // Start server with graceful shutdown
    let server = Server::builder()
        .add_service(
            market_intel::core_engine::core_engine_service_server::CoreEngineServiceServer::new(
                core_engine_service
            )
        )
        .serve_with_shutdown(addr, async {
            shutdown_rx.await.ok();
            info!("Received shutdown signal");
        });

    // Wait for Ctrl+C signal
    tokio::select! {
        result = server => {
            if let Err(e) = result {
                error!("Failed to start gRPC server: {}", e);
                return Err(e.into());
            }
        }
        _ = signal::ctrl_c() => {
            info!("Received Ctrl+C signal");
        }
    }

    // Graceful shutdown
    info!("Shutting down Core Engine...");
    
    // Shutdown OpenTelemetry
    otel::shutdown_telemetry();

    info!("Core Engine shutdown complete");
    Ok(())
}
