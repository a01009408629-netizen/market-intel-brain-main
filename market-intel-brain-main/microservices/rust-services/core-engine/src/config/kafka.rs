// Copyright (c) 2024 Market Intel Brain Team
// Kafka Configuration Module
// تكوين Kafka

use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KafkaConfig {
    pub bootstrap_servers: String,
    pub group_id: String,
    pub client_id: String,
    pub session_timeout: Duration,
    pub auto_offset_reset: String,
    pub enable_auto_commit: bool,
    pub auto_commit_interval: Duration,
    pub max_poll_records: i32,
    pub fetch_max_bytes: i32,
}

impl Default for KafkaConfig {
    fn default() -> Self {
        Self {
            bootstrap_servers: "localhost:9092".to_string(),
            group_id: "market-intel-brain".to_string(),
            client_id: "core-engine".to_string(),
            session_timeout: Duration::from_secs(30),
            auto_offset_reset: "latest".to_string(),
            enable_auto_commit: true,
            auto_commit_interval: Duration::from_secs(5),
            max_poll_records: 100,
            fetch_max_bytes: 1048576, // 1MB
        }
    }
}
