use std::env;
use std::time::Duration;
use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ConfigError {
    #[error("Missing env var: {0}")] MissingEnvVar(String),
    #[error("Invalid config: {0}")] InvalidConfig(String),
    #[error("Parse error: {0}")]    ParseError(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseConfig {
    pub url: String,
    pub max_connections: u32,
    pub min_connections: u32,
    pub connect_timeout: Duration,
    pub idle_timeout: Duration,
}

impl Default for DatabaseConfig {
    fn default() -> Self {
        Self {
            url: "postgres://localhost/market_intel".to_string(),
            max_connections: 10,
            min_connections: 1,
            connect_timeout: Duration::from_secs(10),
            idle_timeout: Duration::from_secs(600),
        }
    }
}

impl DatabaseConfig {
    pub fn from_env() -> Result<Self, ConfigError> {
        Ok(Self {
            url: env::var("DATABASE_URL")
                .unwrap_or_else(|_| "postgres://localhost/market_intel".to_string()),
            max_connections: env::var("DB_MAX_CONNECTIONS")
                .unwrap_or_else(|_| "10".to_string()).parse()
                .map_err(|e| ConfigError::ParseError(format!("DB_MAX_CONNECTIONS: {}", e)))?,
            min_connections: 1,
            connect_timeout: Duration::from_secs(10),
            idle_timeout: Duration::from_secs(600),
        })
    }
    pub fn validate(&self) -> Result<(), ConfigError> {
        if self.url.is_empty() {
            return Err(ConfigError::InvalidConfig("DATABASE_URL empty".into()));
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AnalyticsConfig {
    pub enabled: bool,
    pub kafka_bootstrap_servers: Vec<String>,
    pub topic: String,
    pub client_id: String,
    pub batch_size: usize,
    pub batch_timeout: Duration,
    pub compression_type: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoreEngineConfig {
    pub grpc_port: u16,
    pub database: DatabaseConfig,
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
            grpc_port: 50051,
            database: DatabaseConfig::default(),
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
    pub fn from_env() -> Result<Self, ConfigError> {
        Ok(Self {
            grpc_port: env::var("GRPC_PORT").unwrap_or_else(|_| "50051".to_string())
                .parse().map_err(|e| ConfigError::ParseError(format!("GRPC_PORT: {}", e)))?,
            database: DatabaseConfig::from_env()?,
            analytics_enabled: env::var("ANALYTICS_ENABLED")
                .unwrap_or_else(|_| "false".to_string()).parse()
                .map_err(|e| ConfigError::ParseError(format!("ANALYTICS_ENABLED: {}", e)))?,
            analytics_config: AnalyticsConfig {
                enabled: false,
                kafka_bootstrap_servers: env::var("KAFKA_BOOTSTRAP_SERVERS")
                    .unwrap_or_else(|_| "localhost:9092".to_string())
                    .split(',').map(|s| s.trim().to_string()).collect(),
                topic: env::var("ANALYTICS_TOPIC")
                    .unwrap_or_else(|_| "analytics-events".to_string()),
                client_id: env::var("ANALYTICS_CLIENT_ID")
                    .unwrap_or_else(|_| "core-engine".to_string()),
                batch_size: 100,
                batch_timeout: Duration::from_millis(100),
                compression_type: "gzip".to_string(),
            },
            vector_store_enabled: env::var("VECTOR_STORE_ENABLED")
                .unwrap_or_else(|_| "false".to_string()).parse()
                .map_err(|e| ConfigError::ParseError(format!("VECTOR_STORE_ENABLED: {}", e)))?,
            vector_store_config: VectorStoreConfigWrapper {
                enabled: false,
                qdrant_url: env::var("QDRANT_URL")
                    .unwrap_or_else(|_| "http://localhost:6333".to_string()),
                collection_name: env::var("QDRANT_COLLECTION_NAME")
                    .unwrap_or_else(|_| "market_data_vectors".to_string()),
                vector_size: 1536,
                similarity_threshold: 0.7,
                batch_size: 100,
                cache_enabled: true,
                cache_ttl: Duration::from_secs(300),
            },
            instance_id: env::var("INSTANCE_ID")
                .unwrap_or_else(|_| uuid::Uuid::new_v4().to_string()),
            log_level: env::var("LOG_LEVEL").unwrap_or_else(|_| "info".to_string()),
            environment: env::var("ENVIRONMENT").unwrap_or_else(|_| "development".to_string()),
        })
    }
}