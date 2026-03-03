//! Configuration Module for Core Engine
//! 
//! This module provides configuration structures for the Core Engine service.

use std::env;
use std::time::Duration;
use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::database::DatabaseConfig;
use crate::tls::TlsConfig;

#[derive(Error, Debug)]
pub enum ConfigError {
    #[error("Environment variable {0} is not set")]
    MissingEnvVar(String),
    
    #[error("Invalid configuration: {0}")]
    InvalidConfig(String),
    
    #[error("Parse error: {0}")]
    ParseError(String),
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
            keep_alive: Duration::from_secs(60),
        }
    }
}

/// Analytics configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalyticsConfig {
    pub enabled: bool,
    pub kafka_bootstrap_servers: Vec<String>,
    pub topic: String,
    pub client_id: String,
    pub batch_size: usize,
    pub batch_timeout: Duration,
    pub compression_type: String,
}

impl Default for AnalyticsConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            kafka_bootstrap_servers: vec!["localhost:9092".to_string()],
            topic: "analytics-events".to_string(),
            client_id: "core-engine-analytics".to_string(),
            batch_size: 100,
            batch_timeout: Duration::from_millis(100),
            compression_type: "gzip".to_string(),
        }
    }
}

/// Vector store configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VectorStoreConfigWrapper {
    pub enabled: bool,
    pub qdrant_url: String,
    pub collection_name: String,
    pub vector_size: usize,
    pub similarity_threshold: f32,
    pub batch_size: usize,
    pub cache_enabled: bool,
    pub cache_ttl: Duration,
}

impl Default for VectorStoreConfigWrapper {
    fn default() -> Self {
        Self {
            enabled: false,
            qdrant_url: "http://localhost:6333".to_string(),
            collection_name: "market_data_vectors".to_string(),
            vector_size: 1536,
            similarity_threshold: 0.7,
            batch_size: 100,
            cache_enabled: true,
            cache_ttl: Duration::from_secs(300),
        }
    }
}

/// Main configuration structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoreEngineConfig {
    pub server: ServerConfig,
    pub database: DatabaseConfig,
    pub tls: TlsConfig,
    pub analytics_enabled: bool,
    pub analytics_config: AnalyticsConfig,
    pub vector_store_enabled: bool,
    pub vector_store_config: VectorStoreConfigWrapper,
    pub instance_id: String,
    pub log_level: String,
    pub environment: String,
}

impl Default for CoreEngineConfig {
    fn default() -> Self {
        Self {
            server: ServerConfig::default(),
            database: DatabaseConfig::default(),
            tls: TlsConfig::default(),
            analytics_enabled: false,
            analytics_config: AnalyticsConfig::default(),
            vector_store_enabled: false,
            vector_store_config: VectorStoreConfigWrapper::default(),
            instance_id: uuid::Uuid::new_v4().to_string(),
            log_level: "info".to_string(),
            environment: "development".to_string(),
        }
    }
}

impl CoreEngineConfig {
    /// Load configuration from environment variables
    pub fn from_env() -> Result<Self, ConfigError> {
        let server = ServerConfig {
            host: env::var("SERVER_HOST").unwrap_or_else(|_| "0.0.0.0".to_string()),
            port: env::var("SERVER_PORT")
                .unwrap_or_else(|_| "8080".to_string())
                .parse()
                .map_err(|e| ConfigError::ParseError(format!("Invalid SERVER_PORT: {}", e)))?,
            grpc_port: env::var("GRPC_PORT")
                .unwrap_or_else(|_| "50051".to_string())
                .parse()
                .map_err(|e| ConfigError::ParseError(format!("Invalid GRPC_PORT: {}", e)))?,
            workers: env::var("WORKERS")
                .unwrap_or_else(|_| num_cpus::get().to_string())
                .parse()
                .map_err(|e| ConfigError::ParseError(format!("Invalid WORKERS: {}", e)))?,
            max_connections: env::var("MAX_CONNECTIONS")
                .unwrap_or_else(|_| "10000".to_string())
                .parse()
                .map_err(|e| ConfigError::ParseError(format!("Invalid MAX_CONNECTIONS: {}", e)))?,
            request_timeout: Duration::from_secs(
                env::var("REQUEST_TIMEOUT")
                    .unwrap_or_else(|_| "30".to_string())
                    .parse()
                    .map_err(|e| ConfigError::ParseError(format!("Invalid REQUEST_TIMEOUT: {}", e)))?
            ),
            keep_alive: Duration::from_secs(
                env::var("KEEP_ALIVE")
                    .unwrap_or_else(|_| "60".to_string())
                    .parse()
                    .map_err(|e| ConfigError::ParseError(format!("Invalid KEEP_ALIVE: {}", e)))?
            ),
        };

        let database = DatabaseConfig::from_env()
            .map_err(|e| ConfigError::InvalidConfig(format!("Database config error: {}", e)))?;

        let tls = TlsConfig::from_env();

        let analytics_enabled = env::var("ANALYTICS_ENABLED")
            .unwrap_or_else(|_| "false".to_string())
            .parse()
            .map_err(|e| ConfigError::ParseError(format!("Invalid ANALYTICS_ENABLED: {}", e)))?;

        let analytics_config = AnalyticsConfig {
            enabled: analytics_enabled,
            kafka_bootstrap_servers: env::var("KAFKA_BOOTSTRAP_SERVERS")
                .unwrap_or_else(|_| "localhost:9092".to_string())
                .split(',')
                .map(|s| s.trim().to_string())
                .collect(),
            topic: env::var("ANALYTICS_TOPIC")
                .unwrap_or_else(|_| "analytics-events".to_string()),
            client_id: env::var("ANALYTICS_CLIENT_ID")
                .unwrap_or_else(|_| "core-engine-analytics".to_string()),
            batch_size: env::var("ANALYTICS_BATCH_SIZE")
                .unwrap_or_else(|_| "100".to_string())
                .parse()
                .map_err(|e| ConfigError::ParseError(format!("Invalid ANALYTICS_BATCH_SIZE: {}", e)))?,
            batch_timeout: Duration::from_millis(
                env::var("ANALYTICS_BATCH_TIMEOUT")
                    .unwrap_or_else(|_| "100".to_string())
                    .parse()
                    .map_err(|e| ConfigError::ParseError(format!("Invalid ANALYTICS_BATCH_TIMEOUT: {}", e)))?
            ),
            compression_type: env::var("ANALYTICS_COMPRESSION_TYPE")
                .unwrap_or_else(|_| "gzip".to_string()),
        };

        let vector_store_enabled = env::var("VECTOR_STORE_ENABLED")
            .unwrap_or_else(|_| "false".to_string())
            .parse()
            .map_err(|e| ConfigError::ParseError(format!("Invalid VECTOR_STORE_ENABLED: {}", e)))?;

        let vector_store_config = VectorStoreConfigWrapper {
            enabled: vector_store_enabled,
            qdrant_url: env::var("QDRANT_URL")
                .unwrap_or_else(|_| "http://localhost:6333".to_string()),
            collection_name: env::var("QDRANT_COLLECTION_NAME")
                .unwrap_or_else(|_| "market_data_vectors".to_string()),
            vector_size: env::var("QDRANT_VECTOR_SIZE")
                .unwrap_or_else(|_| "1536".to_string())
                .parse()
                .map_err(|e| ConfigError::ParseError(format!("Invalid QDRANT_VECTOR_SIZE: {}", e)))?,
            similarity_threshold: env::var("QDRANT_SIMILARITY_THRESHOLD")
                .unwrap_or_else(|_| "0.7".to_string())
                .parse()
                .map_err(|e| ConfigError::ParseError(format!("Invalid QDRANT_SIMILARITY_THRESHOLD: {}", e)))?,
            batch_size: env::var("QDRANT_BATCH_SIZE")
                .unwrap_or_else(|_| "100".to_string())
                .parse()
                .map_err(|e| ConfigError::ParseError(format!("Invalid QDRANT_BATCH_SIZE: {}", e)))?,
            cache_enabled: env::var("QDRANT_CACHE_ENABLED")
                .unwrap_or_else(|_| "true".to_string())
                .parse()
                .map_err(|e| ConfigError::ParseError(format!("Invalid QDRANT_CACHE_ENABLED: {}", e)))?,
            cache_ttl: Duration::from_secs(
                env::var("QDRANT_CACHE_TTL")
                    .unwrap_or_else(|_| "300".to_string())
                    .parse()
                    .map_err(|e| ConfigError::ParseError(format!("Invalid QDRANT_CACHE_TTL: {}", e)))?
            ),
        };

        Ok(Self {
            server,
            database,
            tls,
            analytics_enabled,
            analytics_config,
            vector_store_enabled,
            vector_store_config,
            instance_id: env::var("INSTANCE_ID")
                .unwrap_or_else(|_| uuid::Uuid::new_v4().to_string()),
            log_level: env::var("LOG_LEVEL")
                .unwrap_or_else(|_| "info".to_string()),
            environment: env::var("ENVIRONMENT")
                .unwrap_or_else(|_| "development".to_string()),
        })
    }

    /// Validate configuration
    pub fn validate(&self) -> Result<(), ConfigError> {
        if self.server.port == 0 {
            return Err(ConfigError::InvalidConfig("Server port cannot be 0".to_string()));
        }
        
        if self.server.grpc_port == 0 {
            return Err(ConfigError::InvalidConfig("gRPC port cannot be 0".to_string()));
        }
        
        if self.server.workers == 0 {
            return Err(ConfigError::InvalidConfig("Workers cannot be 0".to_string()));
        }

        self.database.validate()
            .map_err(|e| ConfigError::InvalidConfig(format!("Database validation failed: {}", e)))?;

        if self.analytics_enabled {
            if self.analytics_config.kafka_bootstrap_servers.is_empty() {
                return Err(ConfigError::InvalidConfig("Kafka bootstrap servers cannot be empty when analytics is enabled".to_string()));
            }
        }

        if self.vector_store_enabled {
            if self.vector_store_config.qdrant_url.is_empty() {
                return Err(ConfigError::InvalidConfig("Qdrant URL cannot be empty when vector store is enabled".to_string()));
            }
        }

        tracing::info!("Configuration validated successfully");
        Ok(())
    }
}

/// Parse optional environment variable
pub fn parse_optional_env_var<T>(key: &str) -> Result<Option<T>, ConfigError>
where
    T: std::str::FromStr,
    T::Err: std::fmt::Display,
{
    match env::var(key) {
        Ok(value) => {
            let parsed = value.parse()
                .map_err(|e| ConfigError::ParseError(format!("Failed to parse {}: {}", key, e)))?;
            Ok(Some(parsed))
        }
        Err(env::VarError::NotPresent) => Ok(None),
        Err(e) => Err(ConfigError::ParseError(format!("Failed to read {}: {}", key, e))),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = CoreEngineConfig::default();
        assert_eq!(config.server.host, "0.0.0.0");
        assert_eq!(config.server.port, 8080);
        assert_eq!(config.server.grpc_port, 50051);
        assert!(!config.analytics_enabled);
        assert!(!config.vector_store_enabled);
        assert_eq!(config.log_level, "info");
        assert_eq!(config.environment, "development");
    }

    #[test]
    fn test_config_validation() {
        let mut config = CoreEngineConfig::default();
        
        // Valid config should pass
        assert!(config.validate().is_ok());
        
        // Invalid port should fail
        config.server.port = 0;
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_parse_optional_env_var() {
        std::env::set_var("TEST_OPTIONAL", "42");
        assert_eq!(parse_optional_env_var::<u32>("TEST_OPTIONAL").unwrap(), Some(42));
        
        std::env::set_var("TEST_OPTIONAL", "");
        assert_eq!(parse_optional_env_var::<u32>("TEST_OPTIONAL").unwrap(), None);
        
        std::env::remove_var("TEST_OPTIONAL");
        assert_eq!(parse_optional_env_var::<u32>("TEST_OPTIONAL").unwrap(), None);
    }
}
