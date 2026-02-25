// Copyright (c) 2024 Market Intel Brain Team
// Data Sources Module
// وحدة مصادر البيانات

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataSource {
    pub id: String,
    pub name: String,
    pub source_type: SourceType,
    pub endpoint: String,
    pub enabled: bool,
    pub config: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum SourceType {
    WebSocket,
    REST,
    FIX,
    Kafka,
    Redis,
    Database,
}

impl DataSource {
    pub fn new(id: String, name: String, source_type: SourceType, endpoint: String) -> Self {
        Self {
            id,
            name,
            source_type,
            endpoint,
            enabled: true,
            config: HashMap::new(),
        }
    }
    
    pub fn with_config(mut self, config: HashMap<String, serde_json::Value>) -> Self {
        self.config = config;
        self
    }
}
