// Copyright (c) 2024 Market Intel Brain Team
// Metrics Configuration Module
// تكوين المقاييس

use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricsConfig {
    pub enabled: bool,
    pub prometheus_port: u16,
    pub prometheus_path: String,
    pub collection_interval: Duration,
    pub enable_histograms: bool,
    pub enable_counters: bool,
    pub enable_gauges: bool,
}

impl Default for MetricsConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            prometheus_port: 9090,
            prometheus_path: "/metrics".to_string(),
            collection_interval: Duration::from_secs(15),
            enable_histograms: true,
            enable_counters: true,
            enable_gauges: true,
        }
    }
}
