// Copyright (c) 2024 Market Intel Brain Team
// Vector Database Infrastructure - Agent Memory Management
/// بنية تحتية لقاعدة بيانات المتجهات - إدارة ذاكرة الوكلاء

pub mod agent_memory;

pub use agent_memory::{
    AgentMemoryVectorDB, AgentMemoryConfig, AgentMemoryError, AgentMemoryResult,
    MemoryStatistics, HnswConfig, AgentStateManager
};

use qdrant_client::prelude::*;

/// Vector Database Manager
/// مدير قاعدة بيانات المتجهات
pub struct VectorDBManager {
    /// Qdrant client
    /// عميل Qdrant
    client: QdrantClient,
    
    /// Agent memory vector DB
    /// قاعدة بيانات متجهات ذاكرة الوكيل
    agent_memory: Option<agent_memory::AgentMemoryVectorDB>,
}

impl VectorDBManager {
    /// Create new vector DB manager
    /// إنشاء مدير قاعدة بيانات متجهات جديد
    pub async fn new(connection_url: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let client = QdrantClient::from_url(connection_url)?;
        
        Ok(Self {
            client,
            agent_memory: None,
        })
    }

    /// Initialize agent memory vector DB
    /// تهيئة قاعدة بيانات متجهات ذاكرة الوكيل
    pub async fn init_agent_memory(&mut self, config: agent_memory::AgentMemoryConfig) -> Result<(), Box<dyn std::error::Error>> {
        let agent_memory_db = agent_memory::AgentMemoryVectorDB::new(self.client.clone(), config).await?;
        self.agent_memory = Some(agent_memory_db);
        Ok(())
    }

    /// Get agent memory vector DB
    /// الحصول على قاعدة بيانات متجهات ذاكرة الوكيل
    pub fn agent_memory(&self) -> Option<&agent_memory::AgentMemoryVectorDB> {
        self.agent_memory.as_ref()
    }

    /// Get Qdrant client
    /// الحصول على عميل Qdrant
    pub fn client(&self) -> &QdrantClient {
        &self.client
    }

    /// Close the vector DB manager
    /// إغلاق مدير قاعدة بيانات المتجهات
    pub async fn close(&self) -> Result<(), Box<dyn std::error::Error>> {
        // Qdrant client doesn't need explicit closing in most cases
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vector_db_manager_creation() {
        // This test would require a running Qdrant instance
        // let manager = VectorDBManager::new("http://localhost:6333").await.unwrap();
        // assert!(manager.agent_memory().is_none());
    }
}
