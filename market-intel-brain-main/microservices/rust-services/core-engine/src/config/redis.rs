// Copyright (c) 2024 Market Intel Brain Team
// Redis Configuration Module
// تكوين Redis

use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedisConfig {
    pub url: String,
    pub max_connections: u32,
    pub min_idle_connections: u32,
    pub connection_timeout: Duration,
    pub command_timeout: Duration,
    pub idle_timeout: Option<Duration>,
    pub max_lifetime: Option<Duration>,
}

impl Default for RedisConfig {
    fn default() -> Self {
        Self {
            url: "redis://localhost:6379".to_string(),
            max_connections: 10,
            min_idle_connections: 1,
            connection_timeout: Duration::from_secs(5),
            command_timeout: Duration::from_secs(5),
            idle_timeout: Some(Duration::from_secs(300)),
            max_lifetime: Some(Duration::from_secs(1800)),
        }
    }
}
