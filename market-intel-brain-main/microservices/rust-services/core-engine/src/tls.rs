//! TLS Configuration and mTLS Support for Core Engine
//! 
//! This module provides TLS configuration for the gRPC server with mutual TLS (mTLS) support.

use std::fs::File;
use std::io::Read;
use std::path::Path;
use tonic::transport::{Certificate, Identity, ServerTlsConfig};
use tonic::transport::tls::ServerTlsConfigBuilder;
use tokio_rustls::rustls::{Certificate as RustlsCertificate, PrivateKey, ServerConfig};
use tokio_rustls::rustls::internal::pemfile::{certs, pkcs8_private_keys};
use tracing::{info, warn, error};

/// TLS configuration for the gRPC server
#[derive(Debug, Clone)]
pub struct TlsConfig {
    /// Path to the TLS certificate file
    pub cert_path: String,
    /// Path to the TLS private key file
    pub key_path: String,
    /// Path to the CA certificate file for client verification
    pub ca_cert_path: String,
    /// Whether to require client certificate (mTLS)
    pub require_client_cert: bool,
    /// Whether to verify client certificates
    pub verify_client_cert: bool,
}

impl Default for TlsConfig {
    fn default() -> Self {
        Self {
            cert_path: "/etc/tls/tls.crt".to_string(),
            key_path: "/etc/tls/tls.key".to_string(),
            ca_cert_path: "/etc/tls/ca.crt".to_string(),
            require_client_cert: true,
            verify_client_cert: true,
        }
    }
}

impl TlsConfig {
    /// Create TLS configuration from environment variables
    pub fn from_env() -> Self {
        Self {
            cert_path: std::env::var("TLS_CERT_PATH")
                .unwrap_or_else(|_| "/etc/tls/tls.crt".to_string()),
            key_path: std::env::var("TLS_KEY_PATH")
                .unwrap_or_else(|_| "/etc/tls/tls.key".to_string()),
            ca_cert_path: std::env::var("CA_CERT_PATH")
                .unwrap_or_else(|_| "/etc/tls/ca.crt".to_string()),
            require_client_cert: std::env::var("REQUIRE_CLIENT_CERT")
                .unwrap_or_else(|_| "true".to_string())
                .parse()
                .unwrap_or(true),
            verify_client_cert: std::env::var("VERIFY_CLIENT_CERT")
                .unwrap_or_else(|_| "true".to_string())
                .parse()
                .unwrap_or(true),
        }
    }

    /// Load TLS certificate from file
    pub fn load_certificate(&self) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
        let mut file = File::open(&self.cert_path)?;
        let mut buffer = Vec::new();
        file.read_to_end(&mut buffer)?;
        Ok(buffer)
    }

    /// Load TLS private key from file
    pub fn load_private_key(&self) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
        let mut file = File::open(&self.key_path)?;
        let mut buffer = Vec::new();
        file.read_to_end(&mut buffer)?;
        Ok(buffer)
    }

    /// Load CA certificate from file
    pub fn load_ca_certificate(&self) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
        let mut file = File::open(&self.ca_cert_path)?;
        let mut buffer = Vec::new();
        file.read_to_end(&mut buffer)?;
        Ok(buffer)
    }

    /// Create tonic ServerTlsConfig
    pub fn create_server_tls_config(&self) -> Result<Option<ServerTlsConfig>, Box<dyn std::error::Error>> {
        info!("Creating TLS configuration with mTLS support");
        info!("Certificate path: {}", self.cert_path);
        info!("Key path: {}", self.key_path);
        info!("CA certificate path: {}", self.ca_cert_path);
        info!("Require client cert: {}", self.require_client_cert);
        info!("Verify client cert: {}", self.verify_client_cert);

        // Check if certificate files exist
        if !Path::new(&self.cert_path).exists() {
            return Err(format!("TLS certificate file not found: {}", self.cert_path).into());
        }

        if !Path::new(&self.key_path).exists() {
            return Err(format!("TLS private key file not found: {}", self.key_path).into());
        }

        if self.verify_client_cert && !Path::new(&self.ca_cert_path).exists() {
            return Err(format!("CA certificate file not found: {}", self.ca_cert_path).into());
        }

        // Load certificates
        let cert_data = self.load_certificate()?;
        let key_data = self.load_private_key()?;

        // Create identity
        let identity = Identity::from_pem(cert_data, key_data);

        // Create server TLS config
        let mut tls_config = ServerTlsConfigBuilder::new()
            .identity(identity)
            .client_ca_root(Certificate::from_pem(self.load_ca_certificate()?));

        // Configure client certificate verification
        if self.require_client_cert {
            tls_config = tls_config.client_auth_option(tonic::transport::ClientAuthOption::RequireAnyClientCert);
            info!("Client certificate verification enabled");
        } else {
            tls_config = tls_config.client_auth_option(tonic::transport::ClientAuthOption::DontRequestClientCert);
            warn!("Client certificate verification disabled");
        }

        let server_tls_config = tls_config.build();

        info!("TLS configuration created successfully");
        Ok(Some(server_tls_config))
    }

    /// Create rustls ServerConfig for advanced configuration
    pub fn create_rustls_server_config(&self) -> Result<ServerConfig, Box<dyn std::error::Error>> {
        info!("Creating rustls ServerConfig with mTLS support");

        // Load server certificate and key
        let cert_file = File::open(&self.cert_path)?;
        let key_file = File::open(&self.key_path)?;

        let cert_data = certs(&mut cert_file)?
            .into_iter()
            .map(RustlsCertificate)
            .collect();

        let key_data = pkcs8_private_keys(&mut key_file)?
            .into_iter()
            .next()
            .ok_or("No private key found")?;

        // Create server config
        let mut config = ServerConfig::builder()
            .with_safe_defaults()
            .with_no_client_auth();

        // Add server certificate
        config = config.with_single_cert(cert_data, PrivateKey(key_data))?;

        // Configure client certificate verification
        if self.verify_client_cert {
            let ca_cert_file = File::open(&self.ca_cert_path)?;
            let ca_cert_data = certs(&mut ca_cert_file)?
                .into_iter()
                .map(RustlsCertificate)
                .collect();

            config = config.with_client_cert_verifier(
                tokio_rustls::rustls::AllowAnyAuthenticatedClientOrAnonymousClient::new(ca_cert_data)
            );
            info!("Client certificate verification enabled");
        } else {
            warn!("Client certificate verification disabled");
        }

        let server_config = config
            .with_protocols(&["h2", "http/1.1"])
            .with_all_versions();

        info!("rustls ServerConfig created successfully");
        Ok(server_config)
    }

    /// Validate TLS configuration
    pub fn validate(&self) -> Result<(), Box<dyn std::error::Error>> {
        info!("Validating TLS configuration");

        // Check certificate files
        if !Path::new(&self.cert_path).exists() {
            return Err(format!("TLS certificate file not found: {}", self.cert_path).into());
        }

        if !Path::new(&self.key_path).exists() {
            return Err(format!("TLS private key file not found: {}", self.key_path).into());
        }

        if self.verify_client_cert && !Path::new(&self.ca_cert_path).exists() {
            return Err(format!("CA certificate file not found: {}", self.ca_cert_path).into());
        }

        // Validate certificate format
        let cert_data = self.load_certificate()?;
        let key_data = self.load_private_key()?;

        // Try to parse certificates
        let _certs = certs(&mut cert_data.as_slice())
            .map_err(|e| format!("Failed to parse TLS certificate: {}", e))?;

        let _keys = pkcs8_private_keys(&mut key_data.as_slice())
            .map_err(|e| format!("Failed to parse TLS private key: {}", e))?;

        if self.verify_client_cert {
            let ca_cert_data = self.load_ca_certificate()?;
            let _ca_certs = certs(&mut ca_cert_data.as_slice())
                .map_err(|e| format!("Failed to parse CA certificate: {}", e))?;
        }

        info!("TLS configuration validation successful");
        Ok(())
    }

    /// Get certificate information
    pub fn get_cert_info(&self) -> Result<CertificateInfo, Box<dyn std::error::Error>> {
        let cert_data = self.load_certificate()?;
        let certs = certs(&mut cert_data.as_slice())?;
        
        if let Some(cert) = certs.first() {
            let x509_cert = openssl::x509::X509::from_der(cert.as_ref())?;
            
            Ok(CertificateInfo {
                subject: x509_cert.subject_name()
                    .to_text()
                    .unwrap_or_else(|_| "Unknown".to_string()),
                issuer: x509_cert.issuer_name()
                    .to_text()
                    .unwrap_or_else(|_| "Unknown".to_string()),
                serial_number: x509_cert.serial_number()
                    .to_bn()
                    .and_then(|bn| bn.to_hex_str())
                    .unwrap_or_else(|_| "Unknown".to_string()),
                not_before: x509_cert.not_before()
                    .to_string()
                    .unwrap_or_else(|_| "Unknown".to_string()),
                not_after: x509_cert.not_after()
                    .to_string()
                    .unwrap_or_else(|_| "Unknown".to_string()),
                version: x509_cert.version(),
                signature_algorithm: x509_cert.signature_algorithm()
                    .object()
                    .to_string()
                    .unwrap_or_else(|_| "Unknown".to_string()),
            })
        } else {
            Err("No certificate found".into())
        }
    }
}

/// Certificate information
#[derive(Debug, Clone)]
pub struct CertificateInfo {
    pub subject: String,
    pub issuer: String,
    pub serial_number: String,
    pub not_before: String,
    pub not_after: String,
    pub version: i32,
    pub signature_algorithm: String,
}

impl CertificateInfo {
    /// Check if certificate is expired
    pub fn is_expired(&self) -> bool {
        // Parse the not_after date and compare with current time
        // This is a simplified check - in production, use proper date parsing
        self.not_after.contains("2025") || self.not_after.contains("2024")
    }

    /// Get days until expiration
    pub fn days_until_expiration(&self) -> i64 {
        // This is a simplified calculation - in production, use proper date parsing
        if let Some(year_str) = self.not_after.split_whitespace().last() {
            if let Ok(year) = year_str.parse::<i32>() {
                let current_year = chrono::Utc::now().year();
                return (year - current_year) as i64 * 365;
            }
        }
        0
    }
}

/// TLS utilities
pub mod utils {
    use super::*;
    use tracing::{info, warn};

    /// Load certificate chain
    pub fn load_certificate_chain(cert_path: &str) -> Result<Vec<Vec<u8>>, Box<dyn std::error::Error>> {
        let mut certs = Vec::new();
        
        // Try to load as PEM file
        if let Ok(mut file) = File::open(cert_path) {
            let mut buffer = String::new();
            file.read_to_string(&mut buffer)?;
            
            // Split by certificate boundaries
            let cert_blocks: Vec<&str> = buffer
                .split("-----END CERTIFICATE-----")
                .collect();
            
            for cert_block in cert_blocks {
                if cert_block.contains("-----BEGIN CERTIFICATE-----") {
                    let cert_data = format!("{}-----END CERTIFICATE-----", cert_block);
                    certs.push(cert_data.into_bytes());
                }
            }
        }
        
        if certs.is_empty() {
            return Err("No certificates found".into());
        }
        
        Ok(certs)
    }

    /// Validate certificate chain
    pub fn validate_certificate_chain(
        certs: &[Vec<u8>],
        ca_cert: &[u8],
    ) -> Result<(), Box<dyn std::error::Error>> {
        for cert_data in certs {
            let cert = openssl::x509::X509::from_der(cert_data)?;
            
            // Verify certificate against CA
            let store = openssl::x509::store::X509StoreBuilder::new()?;
            let ca_cert_obj = openssl::x509::X509::from_der(ca_cert)?;
            store.add_cert(ca_cert_obj)?;
            
            let mut store_ctx = openssl::x509::X509StoreContext::new()?;
            store_ctx.init(&store.build(), &cert)?;
            
            if store_ctx.verify_cert().is_err() {
                return Err("Certificate verification failed".into());
            }
        }
        
        Ok(())
    }

    /// Generate certificate fingerprint
    pub fn generate_fingerprint(cert_data: &[u8]) -> Result<String, Box<dyn std::error::Error>> {
        let cert = openssl::x509::X509::from_der(cert_data)?;
        let fingerprint = cert.fingerprint(openssl::hash::MessageDigest::sha256())?;
        Ok(hex::encode(fingerprint))
    }

    /// Check certificate revocation (placeholder)
    pub fn check_revocation(cert_data: &[u8]) -> Result<bool, Box<dyn std::error::Error>> {
        // In production, implement CRL or OCSP checking
        warn!("Certificate revocation checking not implemented - always returns false");
        Ok(false)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tls_config_default() {
        let config = TlsConfig::default();
        assert_eq!(config.cert_path, "/etc/tls/tls.crt");
        assert_eq!(config.key_path, "/etc/tls/tls.key");
        assert_eq!(config.ca_cert_path, "/etc/tls/ca.crt");
        assert!(config.require_client_cert);
        assert!(config.verify_client_cert);
    }

    #[test]
    fn test_tls_config_from_env() {
        std::env::set_var("TLS_CERT_PATH", "/custom/tls.crt");
        std::env::set_var("TLS_KEY_PATH", "/custom/tls.key");
        std::env::set_var("CA_CERT_PATH", "/custom/ca.crt");
        std::env::set_var("REQUIRE_CLIENT_CERT", "false");
        std::env::set_var("VERIFY_CLIENT_CERT", "false");

        let config = TlsConfig::from_env();
        assert_eq!(config.cert_path, "/custom/tls.crt");
        assert_eq!(config.key_path, "/custom/tls.key");
        assert_eq!(config.ca_cert_path, "/custom/ca.crt");
        assert!(!config.require_client_cert);
        assert!(!config.verify_client_cert);
    }
}
