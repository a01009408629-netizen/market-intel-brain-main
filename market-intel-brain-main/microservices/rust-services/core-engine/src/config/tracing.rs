// Copyright (c) 2024 Market Intel Brain Team
// Tracing Configuration Module
// تكوين التتبع

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TracingConfig {
    pub enabled: bool,
    pub level: String,
    pub service_name: String,
    pub jaeger_endpoint: Option<String>,
    pub prometheus_endpoint: Option<String>,
    pub sampling_ratio: f64,
    pub extra_tags: HashMap<String, String>,
}

impl Default for TracingConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            level: "info".to_string(),
            service_name: "core-engine".to_string(),
            jaeger_endpoint: None,
            prometheus_endpoint: None,
            sampling_ratio: 1.0,
            extra_tags: HashMap::new(),
        }
    }
}
