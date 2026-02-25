// Copyright (c) 2024 Market Intel Brain Team
// Data Processors Module
// وحدة معالجات البيانات

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataProcessor {
    pub id: String,
    pub name: String,
    pub processor_type: ProcessorType,
    pub enabled: bool,
    pub config: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ProcessorType {
    Filter,
    Transform,
    Aggregate,
    Enrich,
    Validate,
    Normalize,
}

impl DataProcessor {
    pub fn new(id: String, name: String, processor_type: ProcessorType) -> Self {
        Self {
            id,
            name,
            processor_type,
            enabled: true,
            config: HashMap::new(),
        }
    }
    
    pub fn with_config(mut self, config: HashMap<String, serde_json::Value>) -> Self {
        self.config = config;
        self
    }
}
