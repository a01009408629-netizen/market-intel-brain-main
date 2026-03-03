//! TLS / mTLS configuration helpers
//!
//! Reads certificate paths from environment variables and builds a
//! `tonic::transport::ServerTlsConfig` when TLS is enabled.

use std::path::PathBuf;
use tonic::transport::{Certificate, Identity, ServerTlsConfig};

/// TLS configuration loaded from environment variables.
pub struct TlsConfig {
    /// Path to the PEM-encoded server certificate
    pub cert_path: Option<PathBuf>,
    /// Path to the PEM-encoded server private key
    pub key_path: Option<PathBuf>,
    /// Path to the PEM-encoded CA certificate used for client verification (mTLS)
    pub ca_cert_path: Option<PathBuf>,
    /// Whether TLS is enabled at all
    pub tls_enabled: bool,
}

impl TlsConfig {
    /// Load TLS configuration from environment variables.
    ///
    /// | Variable              | Description                        |
    /// |-----------------------|------------------------------------|
    /// | `TLS_ENABLED`         | `"true"` to enable TLS             |
    /// | `TLS_CERT_PATH`       | Path to server certificate PEM     |
    /// | `TLS_KEY_PATH`        | Path to server private key PEM     |
    /// | `TLS_CA_CERT_PATH`    | Path to CA cert PEM (mTLS)        |
    pub fn from_env() -> Self {
        let tls_enabled = std::env::var("TLS_ENABLED")
            .map(|v| v.to_lowercase() == "true")
            .unwrap_or(false);

        Self {
            tls_enabled,
            cert_path: std::env::var("TLS_CERT_PATH").ok().map(PathBuf::from),
            key_path: std::env::var("TLS_KEY_PATH").ok().map(PathBuf::from),
            ca_cert_path: std::env::var("TLS_CA_CERT_PATH").ok().map(PathBuf::from),
        }
    }

    /// Validate that required files exist when TLS is enabled.
    pub fn validate(&self) -> Result<(), Box<dyn std::error::Error>> {
        if !self.tls_enabled {
            return Ok(());
        }

        let cert = self.cert_path.as_ref().ok_or("TLS_CERT_PATH is not set")?;
        let key = self.key_path.as_ref().ok_or("TLS_KEY_PATH is not set")?;

        if !cert.exists() {
            return Err(format!("TLS cert not found: {}", cert.display()).into());
        }
        if !key.exists() {
            return Err(format!("TLS key not found: {}", key.display()).into());
        }
        if let Some(ca) = &self.ca_cert_path {
            if !ca.exists() {
                return Err(format!("CA cert not found: {}", ca.display()).into());
            }
        }

        Ok(())
    }

    /// Build a `ServerTlsConfig` when TLS is enabled, or return `None`.
    ///
    /// Returns `Some(ServerTlsConfig)` with mTLS when `TLS_CA_CERT_PATH` is set,
    /// plain TLS otherwise.  Returns `None` when `TLS_ENABLED` is false.
    pub fn create_server_tls_config(
        &self,
    ) -> Result<Option<ServerTlsConfig>, Box<dyn std::error::Error>> {
        if !self.tls_enabled {
            return Ok(None);
        }

        let cert_pem =
            std::fs::read(self.cert_path.as_ref().ok_or("TLS_CERT_PATH is not set")?)?;
        let key_pem =
            std::fs::read(self.key_path.as_ref().ok_or("TLS_KEY_PATH is not set")?)?;

        let identity = Identity::from_pem(cert_pem, key_pem);
        let mut tls = ServerTlsConfig::new().identity(identity);

        // Enable mTLS when a CA cert is provided
        if let Some(ca_path) = &self.ca_cert_path {
            let ca_pem = std::fs::read(ca_path)?;
            let ca_cert = Certificate::from_pem(ca_pem);
            tls = tls.client_ca_root(ca_cert);
            tracing::info!("mTLS enabled (client certificate verification active)");
        }

        Ok(Some(tls))
    }
}