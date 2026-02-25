use serde::{Deserialize, Serialize};
use std::env;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoreEngineConfig {
    pub grpc_port: u16,
    pub database_url: String,
    pub redis_url: String,
    pub redpanda_brokers: String,
    pub num_processors: usize,
    pub buffer_size: usize,
    pub log_level: String,
}

impl CoreEngineConfig {
    pub fn from_env() -> Result<Self, Box<dyn std::error::Error>> {
        Ok(Self {
            grpc_port: env::var("GRPC_PORT")
                .unwrap_or_else(|_| "50052".to_string())
                .parse()?,
            database_url: env::var("DATABASE_URL")
                .unwrap_or_else(|_| "postgres://postgres:postgres@localhost:5432/market_intel".to_string()),
            redis_url: env::var("REDIS_URL")
                .unwrap_or_else(|_| "redis://localhost:6379".to_string()),
            redpanda_brokers: env::var("REDPANDA_BROKERS")
                .unwrap_or_else(|_| "localhost:9092".to_string()),
            num_processors: env::var("NUM_PROCESSORS")
                .unwrap_or_else(|_| "4".to_string())
                .parse()?,
            buffer_size: env::var("BUFFER_SIZE")
                .unwrap_or_else(|_| "1048576".to_string())
                .parse()?,
            log_level: env::var("LOG_LEVEL")
                .unwrap_or_else(|_| "info".to_string()),
        })
    }
}
