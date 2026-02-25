// Copyright (c) 2024 Market Intel Brain Team
// Analytics Configuration Module
// تكوين التحليلات

use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalyticsConfig {
    pub enabled: bool,
    pub endpoint: String,
    pub api_key: Option<String>,
    pub batch_size: usize,
    pub flush_interval: Duration,
    pub enable_real_time: bool,
    pub enable_historical: bool,
}

impl Default for AnalyticsConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            endpoint: "http://localhost:8080/analytics".to_string(),
            api_key: None,
            batch_size: 100,
            flush_interval: Duration::from_secs(30),
            enable_real_time: true,
            enable_historical: true,
        }
    }
}
