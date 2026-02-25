//! Core Engine Main Entry Point
//! 
//! This is the main entry point for the Core Engine service.
//! It initializes the gRPC server and starts the LMAX Disruptor engine.

use std::net::SocketAddr;
use tonic::transport::Server;
use tracing::{info, error, warn};
use tracing_subscriber;

mod core_engine_service;
mod config;

use core_engine_service::CoreEngineServiceImpl;
use config::CoreEngineConfig;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .init();

    info!("Starting Market Intel Brain Core Engine v{}", env!("CARGO_PKG_VERSION"));

    // Load configuration
    let config = CoreEngineConfig::from_env()?;
    info!("Loaded configuration: {:?}", config);

    // Create core engine service
    let core_engine_service = CoreEngineServiceImpl::new(config.clone());

    // Create gRPC server
    let addr = SocketAddr::from(([0, 0, 0, 0], config.grpc_port));
    info!("Core Engine gRPC server listening on {}", addr);

    // Start server
    Server::builder()
        .add_service(
            market_intel::core_engine::core_engine_service_server::CoreEngineServiceServer::new(
                core_engine_service
            )
        )
        .serve(addr)
        .await
        .map_err(|e| {
            error!("Failed to start gRPC server: {}", e);
            e
        })?;

    Ok(())
}
