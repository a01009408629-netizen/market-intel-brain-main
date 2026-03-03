use std::net::SocketAddr;
use tonic::transport::{Certificate, Identity, Server, ServerTlsConfig};
use tracing::{error, info, warn};

use core_engine::analytics;
use core_engine::config::CoreEngineConfig;
use core_engine::core_engine_service::CoreEngineServiceImpl;
use core_engine::otel;
use core_engine::tls::TlsConfig;
use core_engine::vector_store;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    otel::init_telemetry("core-engine", env!("CARGO_PKG_VERSION"))?;
    analytics::init();
    vector_store::init();

    info!("Starting Core Engine v{}", env!("CARGO_PKG_VERSION"));

    let config = CoreEngineConfig::from_env()
        .map_err(|e| format!("Failed to load config: {}", e))?;

    let tls_config = TlsConfig::from_env();
    if let Err(e) = tls_config.validate() {
        error!("TLS validation failed: {}", e);
        return Err(e);
    }

    let server_tls_config = tls_config
        .create_server_tls_config()
        .map_err(|e| format!("Failed to create TLS config: {}", e))?;

    let svc = CoreEngineServiceImpl::new(config.clone()).await?;
    let addr = SocketAddr::from(([0, 0, 0, 0], config.grpc_port));
    info!("gRPC listening on {}", addr);

    let mut builder = Server::builder();
    if let Some(tls) = server_tls_config {
        info!("mTLS enabled");
        builder.tls_config(tls)?
            .add_service(svc.into_service())
            .serve_with_shutdown(addr, shutdown_signal()).await?;
    } else {
        warn!("No TLS - NOT FOR PRODUCTION");
        builder.add_service(svc.into_service())
            .serve_with_shutdown(addr, shutdown_signal()).await?;
    }

    otel::shutdown_telemetry();
    analytics::cleanup();
    vector_store::cleanup();
    Ok(())
}

async fn shutdown_signal() {
    #[cfg(unix)] {
        use tokio::signal::unix::{signal, SignalKind};
        let mut sigterm = signal(SignalKind::terminate()).unwrap();
        let mut sigint  = signal(SignalKind::interrupt()).unwrap();
        tokio::select! {
            _ = sigterm.recv() => info!("SIGTERM"),
            _ = sigint.recv()  => info!("SIGINT"),
        }
    }
    #[cfg(not(unix))] {
        let _ = tokio::signal::ctrl_c().await;
    }
}