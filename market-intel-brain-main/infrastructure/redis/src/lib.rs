// Copyright (c) 2024 Market Intel Brain Team
// Redis Infrastructure - Agent State & Memory Management
/// بنية تحتية Redis - إدارة حالة وذاكرة الوكلاء

pub mod agent_keys;
pub mod state_store;
pub mod redis_manager;

pub use agent_keys::{
    AgentKeySchema, AgentState, AgentStatus, AgentHistoryEntry, AgentMemoryEntry,
    AgentConfiguration, AgentMetrics, AgentError, ErrorSeverity, MemoryType,
    AgentEventType, ResourceLimits
};

pub use state_store::{StateStore, RedisStateStore, StateStoreError, StateStoreResult};
pub use redis_manager::{RedisManager, RedisManagerConfig, RedisMetrics, AgentStateManager, AgentSummary};

use deadpool_redis::Pool;

/// Redis Infrastructure Manager
/// مدير بنية Redis التحتية
pub struct RedisInfrastructure {
    /// Redis manager
    /// مدير Redis
    redis_manager: std::sync::Arc<RedisManager>,
    
    /// Agent state manager
    /// مدير حالة الوكيل
    agent_state_manager: std::sync::Arc<AgentStateManager>,
}

impl RedisInfrastructure {
    /// Create new Redis infrastructure
    /// إنشاء بنية Redis التحتية جديدة
    pub async fn new(config: RedisManagerConfig) -> Result<Self, Box<dyn std::error::Error>> {
        let redis_manager = std::sync::Arc::new(RedisManager::new(config).await?);
        let agent_state_manager = std::sync::Arc::new(AgentStateManager::new(redis_manager.clone()).await);
        
        Ok(Self {
            redis_manager,
            agent_state_manager,
        })
    }

    /// Get Redis manager
    /// الحصول على مدير Redis
    pub fn redis_manager(&self) -> &std::sync::Arc<RedisManager> {
        &self.redis_manager
    }

    /// Get agent state manager
    /// الحصول على مدير حالة الوكيل
    pub fn agent_state_manager(&self) -> &std::sync::Arc<AgentStateManager> {
        &self.agent_state_manager
    }

    /// Get state store
    /// الحصول على تخزين الحالة
    pub fn state_store(&self) -> std::sync::Arc<RedisStateStore> {
        self.redis_manager.state_store()
    }

    /// Get connection pool
    /// الحصول على مجمع الاتصالات
    pub fn connection_pool(&self) -> Pool {
        self.redis_manager.pool.clone()
    }

    /// Close the infrastructure
    /// إغلاق البنية التحتية
    pub async fn close(&self) -> Result<(), Box<dyn std::error::Error>> {
        self.redis_manager.close().await?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_agent_key_schema() {
        let schema = AgentKeySchema::new("test-agent-123");
        assert_eq!(schema.state_key(), "agent:test-agent-123:state");
        assert_eq!(schema.history_key(), "agent:test-agent-123:history");
    }

    #[test]
    fn test_agent_state_creation() {
        let state = AgentState {
            agent_id: "test-agent".to_string(),
            status: AgentStatus::Processing,
            last_activity: chrono::Utc::now(),
            current_task: Some("task-123".to_string()),
            configuration: serde_json::json!({"key": "value"}),
            metrics: AgentMetrics::default(),
            error_state: None,
            metadata: std::collections::HashMap::new(),
        };
        
        assert_eq!(state.agent_id, "test-agent");
        assert_eq!(state.status, AgentStatus::Processing);
    }

    #[tokio::test]
    async fn test_redis_manager_config() {
        let config = RedisManagerConfig::default();
        assert_eq!(config.connection_url, "redis://localhost:6379");
        assert_eq!(config.max_pool_size, 20);
        assert_eq!(config.connection_timeout_seconds, 10);
    }
}
