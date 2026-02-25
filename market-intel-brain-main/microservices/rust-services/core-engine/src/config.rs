use serde::{Deserialize, Serialize};
use std::env;

use crate::analytics::{AnalyticsConfig, PublisherConfig};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoreEngineConfig {
    pub grpc_port: u16,
    pub database_url: String,
    pub redis_url: String,
    pub redpanda_brokers: String,
    pub num_processors: usize,
    pub buffer_size: usize,
    pub log_level: String,
    pub instance_id: String,
    pub analytics_enabled: bool,
    pub analytics_config: AnalyticsConfig,
}

impl CoreEngineConfig {
    pub fn from_env() -> Result<Self, Box<dyn std::error::Error>> {
        let redpanda_brokers = env::var("REDPANDA_BROKERS")
            .unwrap_or_else(|_| "localhost:9092".to_string());
        
        Ok(Self {
            grpc_port: env::var("GRPC_PORT")
                .unwrap_or_else(|_| "50052".to_string())
                .parse()?,
            database_url: env::var("DATABASE_URL")
                .unwrap_or_else(|_| "postgres://postgres:postgres@localhost:5432/market_intel".to_string()),
            redis_url: env::var("REDIS_URL")
                .unwrap_or_else(|_| "redis://localhost:6379".to_string()),
            redpanda_brokers: redpanda_brokers.clone(),
            num_processors: env::var("NUM_PROCESSORS")
                .unwrap_or_else(|_| "4".to_string())
                .parse()?,
            buffer_size: env::var("BUFFER_SIZE")
                .unwrap_or_else(|_| "1048576".to_string())
                .parse()?,
            log_level: env::var("LOG_LEVEL")
                .unwrap_or_else(|_| "info".to_string()),
            instance_id: env::var("INSTANCE_ID")
                .unwrap_or_else(|_| {
                    format!("core-engine-{}", std::process::id())
                }),
            analytics_enabled: env::var("ANALYTICS_ENABLED")
                .unwrap_or_else(|_| "true".to_string())
                .parse()
                .unwrap_or(true),
            analytics_config: AnalyticsConfig {
                enabled: env::var("ANALYTICS_ENABLED")
                    .unwrap_or_else(|_| "true".to_string())
                    .parse()
                    .unwrap_or(true),
                publisher: PublisherConfig {
                    bootstrap_servers: redpanda_brokers.split(',').map(|s| s.to_string()).collect(),
                    topic: env::var("ANALYTICS_TOPIC")
                        .unwrap_or_else(|_| "market-intel-analytics".to_string()),
                    client_id: env::var("ANALYTICS_CLIENT_ID")
                        .unwrap_or_else(|_| "core-engine".to_string()),
                    ..Default::default()
                },
                ..Default::default()
            },
        })
    }
}
