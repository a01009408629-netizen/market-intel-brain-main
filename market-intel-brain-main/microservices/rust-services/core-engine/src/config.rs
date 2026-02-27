// Copyright (c) 2024 Market Intel Brain Team
// Configuration module for Core Engine
// This module provides strongly typed configuration with validation

use std::env;
use std::net::SocketAddr;
use std::path::PathBuf;
use std::str::FromStr;
use std::time::Duration;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use tracing::{info, warn, error};

pub mod database;
pub mod redis;
pub mod kafka;
pub mod tls;
pub mod tracing;
pub mod metrics;
pub mod analytics;
pub mod vector_store;

#[derive(Error, Debug)]
pub enum ConfigError {
    #[error("Environment variable {0} is not set")]
    MissingEnvVar(String),
    
    #[error("Environment variable {0} has invalid value: {1}")]
    InvalidEnvVar(String, String),
    
    #[error("Configuration validation failed: {0}")]
    ValidationError(String),
    
    #[error("Failed to parse configuration: {0}")]
    ParseError(#[from] toml::de::Error),
    
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

/// Main configuration structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoreEngineConfig {
    pub server: ServerConfig,
    pub database: database::DatabaseConfig,
    pub redis: redis::RedisConfig,
    pub kafka: kafka::KafkaConfig,
    pub tls: tls::TlsConfig,
    pub tracing: tracing::TracingConfig,
    pub metrics: metrics::MetricsConfig,
    pub analytics: analytics::AnalyticsConfig,
    pub vector_store: vector_store::VectorStoreConfig,
}

/// Server configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    pub host: String,
    pub port: u16,
    pub grpc_port: u16,
    pub workers: usize,
    pub max_connections: usize,
    pub request_timeout: Duration,
    pub shutdown_timeout: Duration,
    pub keep_alive: Duration,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            host: "0.0.0.0".to_string(),
            port: 8080,
            grpc_port: 50051,
            workers: num_cpus::get(),
            max_connections: 10000,
            request_timeout: Duration::from_secs(30),
            shutdown_timeout: Duration::from_secs(30),
            keep_alive: Duration::from_secs(75),
        }
    }
}

impl ServerConfig {
    pub fn from_env() -> Result<Self, ConfigError> {
        let host = env::var("SERVER_HOST").unwrap_or_else(|_| "0.0.0.0".to_string());
        let port = parse_env_var("SERVER_PORT", "8080")?;
        let grpc_port = parse_env_var("SERVER_GRPC_PORT", "50051")?;
        let workers = parse_env_var("SERVER_WORKERS", &num_cpus::get().to_string())?;
        let max_connections = parse_env_var("SERVER_MAX_CONNECTIONS", "10000")?;
        let request_timeout = parse_duration_env("SERVER_REQUEST_TIMEOUT", "30s")?;
        let shutdown_timeout = parse_duration_env("SERVER_SHUTDOWN_TIMEOUT", "30s")?;
        let keep_alive = parse_duration_env("SERVER_KEEP_ALIVE", "75s")?;

        let config = Self {
            host,
            port,
            grpc_port,
            workers,
            max_connections,
            request_timeout,
            shutdown_timeout,
            keep_alive,
        };

        config.validate()?;
        Ok(config)
    }

    pub fn validate(&self) -> Result<(), ConfigError> {
        if self.port == 0 {
            return Err(ConfigError::ValidationError("Server port cannot be 0".to_string()));
        }
        
        if self.grpc_port == 0 {
            return Err(ConfigError::ValidationError("gRPC port cannot be 0".to_string()));
        }
        
        if self.workers == 0 {
            return Err(ConfigError::ValidationError("Worker count cannot be 0".to_string()));
        }
        
        if self.max_connections == 0 {
            return Err(ConfigError::ValidationError("Max connections cannot be 0".to_string()));
        }
        
        if self.request_timeout.is_zero() {
            return Err(ConfigError::ValidationError("Request timeout cannot be zero".to_string()));
        }
        
        if self.shutdown_timeout.is_zero() {
            return Err(ConfigError::ValidationError("Shutdown timeout cannot be zero".to_string()));
        }
        
        if self.keep_alive.is_zero() {
            return Err(ConfigError::ValidationError("Keep-alive timeout cannot be zero".to_string()));
        }

        Ok(())
    }

    pub fn grpc_address(&self) -> SocketAddr {
        format!("{}:{}", self.host, self.grpc_port)
            .parse()
            .expect("Invalid socket address")
    }

    pub fn http_address(&self) -> SocketAddr {
        format!("{}:{}", self.host, self.port)
            .parse()
            .expect("Invalid socket address")
    }
}

impl CoreEngineConfig {
    /// Load configuration from environment variables
    pub fn from_env() -> Result<Self, ConfigError> {
        info!("Loading configuration from environment variables");
        
        let server = ServerConfig::from_env()?;
        let database = database::DatabaseConfig::from_env()?;
        let redis = redis::RedisConfig::from_env()?;
        let kafka = kafka::KafkaConfig::from_env()?;
        let tls = tls::TlsConfig::from_env()?;
        let tracing = tracing::TracingConfig::from_env()?;
        let metrics = metrics::MetricsConfig::from_env()?;
        let analytics = analytics::AnalyticsConfig::from_env()?;
        let vector_store = vector_store::VectorStoreConfig::from_env()?;

        let config = Self {
            server,
            database,
            redis,
            kafka,
            tls,
            tracing,
            metrics,
            analytics,
            vector_store,
        };

        config.validate()?;
        info!("Configuration loaded and validated successfully");
        Ok(config)
    }

    /// Load configuration from file
    pub fn from_file(path: &str) -> Result<Self, ConfigError> {
        info!("Loading configuration from file: {}", path);
        
        let content = std::fs::read_to_string(path)?;
        let config: Self = toml::from_str(&content)?;
        
        config.validate()?;
        info!("Configuration loaded and validated successfully");
        Ok(config)
    }

    /// Validate entire configuration
    pub fn validate(&self) -> Result<(), ConfigError> {
        self.server.validate()?;
        self.database.validate()?;
        self.redis.validate()?;
        self.kafka.validate()?;
        self.tls.validate()?;
        self.tracing.validate()?;
        self.metrics.validate()?;
        self.analytics.validate()?;
        self.vector_store.validate()?;
        
        // Cross-component validation
        if self.server.grpc_port == self.server.port {
            warn!("HTTP and gRPC ports are the same, this may cause conflicts");
        }
        
        Ok(())
    }

    /// Get configuration summary for logging
    pub fn summary(&self) -> String {
        format!(
            "CoreEngineConfig {{ server: {}:{}, grpc: {}:{}, database: {}, redis: {}, kafka: {}, tls: {} }}",
            self.server.host,
            self.server.port,
            self.server.host,
            self.server.grpc_port,
            self.database.host,
            self.redis.host,
            self.kafka.bootstrap_servers,
            self.tls.enabled
        )
    }
}

/// Helper function to parse environment variable with default
fn parse_env_var<T>(key: &str, default: &str) -> Result<T, ConfigError>
where
    T: FromStr,
    <T as FromStr>::Err: std::fmt::Display,
{
    match env::var(key) {
        Ok(value) => value
            .parse()
            .map_err(|e| ConfigError::InvalidEnvVar(key.to_string(), e.to_string())),
        Err(_) => default
            .parse()
            .map_err(|e| ConfigError::InvalidEnvVar(key.to_string(), e.to_string())),
    }
}

/// Helper function to parse duration from environment variable
fn parse_duration_env(key: &str, default: &str) -> Result<Duration, ConfigError> {
    let value = env::var(key).unwrap_or_else(|_| default.to_string());
    
    // Parse duration string (e.g., "30s", "5m", "1h")
    let duration = if let Some(seconds) = value.strip_suffix('s') {
        seconds.parse::<u64>()
            .map(Duration::from_secs)
            .map_err(|e| ConfigError::InvalidEnvVar(key.to_string(), e.to_string()))?
    } else if let Some(minutes) = value.strip_suffix('m') {
        minutes.parse::<u64>()
            .map(Duration::from_secs)
            .map(|s| Duration::from_secs(s * 60))
            .map_err(|e| ConfigError::InvalidEnvVar(key.to_string(), e.to_string()))?
    } else if let Some(hours) = value.strip_suffix('h') {
        hours.parse::<u64>()
            .map(Duration::from_secs)
            .map(|s| Duration::from_secs(s * 3600))
            .map_err(|e| ConfigError::InvalidEnvVar(key.to_string(), e.to_string()))?
    } else {
        // Assume seconds if no suffix
        value.parse::<u64>()
            .map(Duration::from_secs)
            .map_err(|e| ConfigError::InvalidEnvVar(key.to_string(), e.to_string()))?
    };
    
    Ok(duration)
}

/// Helper function to parse boolean from environment variable
fn parse_bool_env(key: &str, default: bool) -> Result<bool, ConfigError> {
    match env::var(key) {
        Ok(value) => {
            match value.to_lowercase().as_str() {
                "true" | "1" | "yes" | "on" => Ok(true),
                "false" | "0" | "no" | "off" => Ok(false),
                _ => Err(ConfigError::InvalidEnvVar(
                    key.to_string(),
                    "Expected 'true', 'false', '1', '0', 'yes', 'no', 'on', or 'off'".to_string(),
                )),
            }
        }
        Err(_) => Ok(default),
    }
}

/// Helper function to parse optional environment variable
fn parse_optional_env_var<T>(key: &str) -> Result<Option<T>, ConfigError>
where
    T: FromStr,
    <T as FromStr>::Err: std::fmt::Display,
{
    match env::var(key) {
        Ok(value) => {
            if value.is_empty() {
                Ok(None)
            } else {
                value
                    .parse()
                    .map(Some)
                    .map_err(|e| ConfigError::InvalidEnvVar(key.to_string(), e.to_string()))
            }
        }
        Err(_) => Ok(None),
    }
}

/// Helper function to parse optional path from environment variable
fn parse_optional_path_env(key: &str) -> Result<Option<PathBuf>, ConfigError> {
    match env::var(key) {
        Ok(value) => {
            if value.is_empty() {
                Ok(None)
            } else {
                Ok(Some(PathBuf::from(value)))
            }
        }
        Err(_) => Ok(None),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;

    #[test]
    fn test_server_config_from_env() {
        // Test with default values
        env::set_var("SERVER_HOST", "127.0.0.1");
        env::set_var("SERVER_PORT", "8080");
        env::set_var("SERVER_GRPC_PORT", "50051");
        
        let config = ServerConfig::from_env().unwrap();
        assert_eq!(config.host, "127.0.0.1");
        assert_eq!(config.port, 8080);
        assert_eq!(config.grpc_port, 50051);
        
        // Clean up
        env::remove_var("SERVER_HOST");
        env::remove_var("SERVER_PORT");
        env::remove_var("SERVER_GRPC_PORT");
    }

    #[test]
    fn test_server_config_validation() {
        let mut config = ServerConfig::default();
        
        // Test valid config
        assert!(config.validate().is_ok());
        
        // Test invalid port
        config.port = 0;
        assert!(config.validate().is_err());
        
        config.port = 8080;
        config.grpc_port = 0;
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_parse_duration_env() {
        env::set_var("TEST_DURATION", "30s");
        let duration = parse_duration_env("TEST_DURATION", "10s").unwrap();
        assert_eq!(duration, Duration::from_secs(30));
        
        env::set_var("TEST_DURATION", "5m");
        let duration = parse_duration_env("TEST_DURATION", "10s").unwrap();
        assert_eq!(duration, Duration::from_secs(300));
        
        env::set_var("TEST_DURATION", "1h");
        let duration = parse_duration_env("TEST_DURATION", "10s").unwrap();
        assert_eq!(duration, Duration::from_secs(3600));
        
        env::remove_var("TEST_DURATION");
    }

    #[test]
    fn test_parse_bool_env() {
        env::set_var("TEST_BOOL", "true");
        assert!(parse_bool_env("TEST_BOOL", false).unwrap());
        
        env::set_var("TEST_BOOL", "false");
        assert!(!parse_bool_env("TEST_BOOL", true).unwrap());
        
        env::set_var("TEST_BOOL", "1");
        assert!(parse_bool_env("TEST_BOOL", false).unwrap());
        
        env::set_var("TEST_BOOL", "0");
        assert!(!parse_bool_env("TEST_BOOL", true).unwrap());
        
        env::remove_var("TEST_BOOL");
        assert!(!parse_bool_env("TEST_BOOL", false).unwrap());
    }

    #[test]
    fn test_parse_optional_env_var() {
        env::set_var("TEST_OPTIONAL", "42");
        assert_eq!(parse_optional_env_var::<u32>("TEST_OPTIONAL").unwrap(), Some(42));
        
        env::set_var("TEST_OPTIONAL", "");
        assert_eq!(parse_optional_env_var::<u32>("TEST_OPTIONAL").unwrap(), None);
        
        env::remove_var("TEST_OPTIONAL");
        assert_eq!(parse_optional_env_var::<u32>("TEST_OPTIONAL").unwrap(), None);
    }
}
