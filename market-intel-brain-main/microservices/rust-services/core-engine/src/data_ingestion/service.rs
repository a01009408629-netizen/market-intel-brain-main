// Copyright (c) 2024 Market Intel Brain Team
// Data Ingestion Service
// خدمة استيعاد البيانات

use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{info, warn, error};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum DataIngestionError {
    #[error("Source not found: {0}")]
    SourceNotFound(String),
    
    #[error("Processing failed: {0}")]
    ProcessingFailed(String),
    
    #[error("Configuration error: {0}")]
    ConfigurationError(String),
}

pub type DataIngestionResult<T> = Result<T, DataIngestionError>;

pub struct DataIngestionService {
    sources: Arc<RwLock<Vec<String>>>,
    processors: Arc<RwLock<Vec<String>>>,
}

impl DataIngestionService {
    pub fn new() -> DataIngestionResult<Self> {
        info!("Initializing Data Ingestion Service");
        
        Ok(Self {
            sources: Arc::new(RwLock::new(Vec::new())),
            processors: Arc::new(RwLock::new(Vec::new())),
        })
    }
    
    pub async fn add_source(&self, source: String) -> DataIngestionResult<()> {
        let mut sources = self.sources.write().await;
        sources.push(source);
        info!("Added data source: {}", source);
        Ok(())
    }
    
    pub async fn get_sources(&self) -> Vec<String> {
        self.sources.read().await.clone()
    }
    
    pub async fn add_processor(&self, processor: String) -> DataIngestionResult<()> {
        let mut processors = self.processors.write().await;
        processors.push(processor);
        info!("Added data processor: {}", processor);
        Ok(())
    }
    
    pub async fn get_processors(&self) -> Vec<String> {
        self.processors.read().await.clone()
    }
}

impl Default for DataIngestionService {
    fn default() -> Self {
        Self::new().unwrap()
    }
}
