use std::net::SocketAddr;
use tonic::transport::Server;
use tracing::{info, warn};
use core_engine::analytics;
use core_engine::config::CoreEngineConfig;
use core_engine::core_engine_service::CoreEngineServiceImpl;
use core_engine::otel;
use core_engine::vector_store;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    otel::init_telemetry("core-engine", env!("CARGO_PKG_VERSION"))?;
    analytics::init();
    vector_store::init();
    info!("Starting Core Engine v{}", env!("CARGO_PKG_VERSION"));
    let config = CoreEngineConfig::from_env()
        .map_err(|e| -> Box<dyn std::error::Error> { format!("Failed to load config: {}", e).into() })?;
    let svc = CoreEngineServiceImpl::new(config.clone()).await?;
    let addr = SocketAddr::from(([0, 0, 0, 0], config.server.grpc_port));
    info!("gRPC listening on {}", addr);
    warn!("TLS disabled - NOT FOR PRODUCTION");
    Server::builder()
        .add_service(svc.into_service())
        .serve_with_shutdown(addr, shutdown_signal())
        .await?;
    otel::shutdown_telemetry();
    analytics::cleanup();
    vector_store::cleanup();
    Ok(())
}

async fn shutdown_signal() {
    #[cfg(unix)] {
        use tokio::signal::unix::{signal, SignalKind};
        let mut sigterm = signal(SignalKind::terminate()).unwrap();
        let mut sigint = signal(SignalKind::interrupt()).unwrap();
        tokio::select! {
            _ = sigterm.recv() => info!("SIGTERM"),
            _ = sigint.recv()  => info!("SIGINT"),
        }
    }
    #[cfg(not(unix))] {
        let _ = tokio::signal::ctrl_c().await;
    }
}
