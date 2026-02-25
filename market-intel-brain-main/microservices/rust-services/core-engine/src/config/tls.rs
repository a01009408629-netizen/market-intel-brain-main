// Copyright (c) 2024 Market Intel Brain Team
// TLS Configuration Module
// تكوين TLS

use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use thiserror::Error;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TlsConfig {
    pub enabled: bool,
    pub cert_path: Option<PathBuf>,
    pub key_path: Option<PathBuf>,
    pub ca_path: Option<PathBuf>,
    pub verify_client: bool,
    pub server_name: Option<String>,
}

#[derive(Error, Debug)]
pub enum TlsError {
    #[error("Certificate file not found: {0}")]
    CertNotFound(String),
    
    #[error("Key file not found: {0}")]
    KeyNotFound(String),
    
    #[error("CA file not found: {0}")]
    CaNotFound(String),
    
    #[error("Invalid TLS configuration: {0}")]
    InvalidConfig(String),
}

impl TlsConfig {
    pub fn validate(&self) -> Result<(), TlsError> {
        if self.enabled {
            if let Some(ref cert_path) = self.cert_path {
                if !cert_path.exists() {
                    return Err(TlsError::CertNotFound(cert_path.to_string_lossy().to_string()));
                }
            }
            
            if let Some(ref key_path) = self.key_path {
                if !key_path.exists() {
                    return Err(TlsError::KeyNotFound(key_path.to_string_lossy().to_string()));
                }
            }
            
            if let Some(ref ca_path) = self.ca_path {
                if !ca_path.exists() {
                    return Err(TlsError::CaNotFound(ca_path.to_string_lossy().to_string()));
                }
            }
        }
        
        Ok(())
    }
    
    pub fn create_server_tls_config(&self) -> Option<tonic::transport::ServerTlsConfig> {
        if !self.enabled {
            return None;
        }
        
        // In a real implementation, this would create the actual TLS config
        // For now, return None as placeholder
        None
    }
}

impl Default for TlsConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            cert_path: None,
            key_path: None,
            ca_path: None,
            verify_client: true,
            server_name: None,
        }
    }
}
