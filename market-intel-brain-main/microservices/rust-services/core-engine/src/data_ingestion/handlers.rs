// Copyright (c) 2024 Market Intel Brain Team
// Data Handlers Module
// وحدة معالجات البيانات

use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataMessage {
    pub id: String,
    pub source: String,
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub data: serde_json::Value,
    pub metadata: HashMap<String, String>,
}

#[async_trait]
pub trait DataHandler: Send + Sync {
    async fn handle(&self, message: DataMessage) -> Result<(), HandlerError>;
    fn name(&self) -> &str;
}

#[derive(Debug, thiserror::Error)]
pub enum HandlerError {
    #[error("Processing error: {0}")]
    ProcessingError(String),
    
    #[error("Validation error: {0}")]
    ValidationError(String),
    
    #[error("Serialization error: {0}")]
    SerializationError(String),
}

pub struct DefaultDataHandler {
    name: String,
}

impl DefaultDataHandler {
    pub fn new(name: String) -> Self {
        Self { name }
    }
}

#[async_trait]
impl DataHandler for DefaultDataHandler {
    async fn handle(&self, message: DataMessage) -> Result<(), HandlerError> {
        tracing::info!("Handling message from source: {}", message.source);
        // Default implementation - just log the message
        Ok(())
    }
    
    fn name(&self) -> &str {
        &self.name
    }
}
