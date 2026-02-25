// Copyright (c) 2024 Market Intel Brain Team
// Vector Store Configuration Module
// تكوين تخزين المتجهات

use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VectorStoreConfig {
    pub enabled: bool,
    pub endpoint: String,
    pub api_key: Option<String>,
    pub collection_name: String,
    pub dimension: usize,
    pub distance_metric: String,
    pub batch_size: usize,
    pub timeout: Duration,
}

impl Default for VectorStoreConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            endpoint: "http://localhost:6333".to_string(),
            api_key: None,
            collection_name: "market_intel".to_string(),
            dimension: 768,
            distance_metric: "cosine".to_string(),
            batch_size: 100,
            timeout: Duration::from_secs(30),
        }
    }
}
