// Copyright (c) 2024 Market Intel Brain Team
// State Store Trait - Abstract Redis operations for agent state management
/// واجهة تخزين الحالة - تجريد عمليات Redis لإدارة حالة الوكيل

use async_trait::async_trait;
use thiserror::Error;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use chrono::{DateTime, Utc};
use crate::agent_keys::{
    AgentKeySchema, AgentState, AgentHistoryEntry, AgentMemoryEntry, 
    AgentConfiguration, AgentKeyError
};

/// State Store Trait
/// واجهة تخزين الحالة
#[async_trait]
pub trait StateStore: Send + Sync {
    /// Error type for state store operations
    /// نوع الخطأ لعمليات تخزين الحالة
    type Error: std::error::Error + Send + Sync + 'static;

    /// Save agent state
    /// حفظ حالة الوكيل
    async fn save_state(&self, agent_id: &str, state: &AgentState) -> Result<(), Self::Error>;

    /// Get agent state
    /// الحصول على حالة الوكيل
    async fn get_state(&self, agent_id: &str) -> Result<Option<AgentState>, Self::Error>;

    /// Update agent status
    /// تحديث حالة الوكيل
    async fn update_status(&self, agent_id: &str, status: crate::agent_keys::AgentStatus) -> Result<(), Self::Error>;

    /// Append entry to agent history
    /// إضافة إدخال إلى سجل الوكيل
    async fn append_history(&self, agent_id: &str, entry: &AgentHistoryEntry) -> Result<(), Self::Error>;

    /// Get agent history
    /// الحصول على سجل الوكيل
    async fn get_history(&self, agent_id: &str, limit: Option<usize>) -> Result<Vec<AgentHistoryEntry>, Self::Error>;

    /// Get agent history by time range
    /// الحصول على سجل الوكيل حسب النطاق الزمني
    async fn get_history_by_time_range(
        &self, 
        agent_id: &str, 
        start: DateTime<Utc>, 
        end: DateTime<Utc>
    ) -> Result<Vec<AgentHistoryEntry>, Self::Error>;

    /// Save agent memory entry
    /// حفظ إدخال ذاكرة الوكيل
    async fn save_memory(&self, agent_id: &str, memory: &AgentMemoryEntry) -> Result<(), Self::Error>;

    /// Get agent memory entries
    /// الحصول على إدخالات ذاكرة الوكيل
    async fn get_memory(&self, agent_id: &str, limit: Option<usize>) -> Result<Vec<AgentMemoryEntry>, Self::Error>;

    /// Search agent memory by content
    /// البحث في ذاكرة الوكيل حسب المحتوى
    async fn search_memory(&self, agent_id: &str, query: &str, limit: Option<usize>) -> Result<Vec<AgentMemoryEntry>, Self::Error>;

    /// Save agent configuration
    /// حفظ تكوين الوكيل
    async fn save_config(&self, agent_id: &str, config: &AgentConfiguration) -> Result<(), Self::Error>;

    /// Get agent configuration
    /// الحصول على تكوين الوكيل
    async fn get_config(&self, agent_id: &str) -> Result<Option<AgentConfiguration>, Self::Error>;

    /// Delete agent data
    /// حذف بيانات الوكيل
    async fn delete_agent(&self, agent_id: &str) -> Result<(), Self::Error>;

    /// List all agents
    /// قائمة جميع الوكلاء
    async fn list_agents(&self) -> Result<Vec<String>, Self::Error>;

    /// Get active agents
    /// الحصول على الوكلاء النشطين
    async fn get_active_agents(&self) -> Result<Vec<String>, Self::Error>;

    /// Check if agent exists
    /// التحقق من وجود الوكيل
    async fn agent_exists(&self, agent_id: &str) -> Result<bool, Self::Error>;

    /// Set agent lock
    /// تعيين قفل الوكيل
    async fn set_lock(&self, agent_id: &str, ttl_seconds: u64) -> Result<bool, Self::Error>;

    /// Release agent lock
    /// تحرير قفل الوكيل
    async fn release_lock(&self, agent_id: &str) -> Result<bool, Self::Error>;

    /// Get agent metrics
    /// الحصول على مقاييس الوكيل
    async fn get_metrics(&self, agent_id: &str) -> Result<Option<crate::agent_keys::AgentMetrics>, Self::Error>;

    /// Update agent metrics
    /// تحديث مقاييس الوكيل
    async fn update_metrics(&self, agent_id: &str, metrics: &crate::agent_keys::AgentMetrics) -> Result<(), Self::Error>;
}

/// State Store Error
/// خطأ تخزين الحالة
#[derive(Error, Debug)]
pub enum StateStoreError {
    #[error("Redis error: {0}")]
    RedisError(#[from] redis::RedisError),
    
    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),
    
    #[error("Agent key error: {0}")]
    AgentKeyError(#[from] AgentKeyError),
    
    #[error("Agent not found: {0}")]
    AgentNotFound(String),
    
    #[error("Invalid agent ID: {0}")]
    InvalidAgentId(String),
    
    #[error("Lock acquisition failed: {0}")]
    LockFailed(String),
    
    #[error("Configuration error: {0}")]
    ConfigurationError(String),
    
    #[error("Memory error: {0}")]
    MemoryError(String),
    
    #[error("History error: {0}")]
    HistoryError(String),
    
    #[error("Connection error: {0}")]
    ConnectionError(String),
    
    #[error("Timeout error: {0}")]
    TimeoutError(String),
    
    #[error("Unknown error: {0}")]
    Unknown(String),
}

/// Result type for state store operations
/// نوع النتيجة لعمليات تخزين الحالة
pub type StateStoreResult<T> = Result<T, StateStoreError>;

/// Redis State Store Implementation
/// تنفيذ تخزين الحالة باستخدام Redis
pub struct RedisStateStore {
    /// Redis connection pool
    /// مجمع اتصالات Redis
    pool: deadpool_redis::Pool,
    
    /// Key schema helper
    /// مساعد مخطط المفاتيح
    key_schema: AgentKeySchema,
}

impl RedisStateStore {
    /// Create new Redis state store
    /// إنشاء تخزين حالة Redis جديد
    pub fn new(pool: deadpool_redis::Pool) -> Self {
        Self {
            pool,
            key_schema: AgentKeySchema::new(""),
        }
    }

    /// Get Redis connection from pool
    /// الحصول على اتصال Redis من المجمع
    async fn get_connection(&self) -> StateStoreResult<deadpool_redis::Connection> {
        self.pool
            .get()
            .await
            .map_err(|e| StateStoreError::ConnectionError(e.to_string()))
    }

    /// Execute Redis command with error handling
    /// تنفيذ أمر Redis مع معالجة الأخطاء
    async fn execute_cmd<F, R>(&self, cmd: F) -> StateStoreResult<R>
    where
        F: FnOnce(&mut deadpool_redis::Connection) -> redis::RedisResult<R>,
    {
        let mut conn = self.get_connection().await?;
        cmd(&mut conn).map_err(|e| StateStoreError::RedisError(e))
    }

    /// Validate agent ID
    /// التحقق من صحة معرف الوكيل
    fn validate_agent_id(&self, agent_id: &str) -> StateStoreResult<()> {
        AgentKeySchema::validate_agent_id(agent_id)?;
        Ok(())
    }

    /// Serialize data to JSON
    /// تسلسل البيانات إلى JSON
    fn serialize_to_json<T: Serialize>(&self, data: &T) -> StateStoreResult<String> {
        serde_json::to_string(data).map_err(StateStoreError::SerializationError)
    }

    /// Deserialize data from JSON
    /// فك تسلسل البيانات من JSON
    fn deserialize_from_json<T: for<'de> Deserialize<'de>>(&self, json: &str) -> StateStoreResult<T> {
        serde_json::from_str(json).map_err(StateStoreError::SerializationError)
    }

    /// Set key with optional TTL
    /// تعيين المفتاح مع TTL اختياري
    async fn set_key_with_ttl(&self, key: &str, value: &str, ttl_seconds: Option<u64>) -> StateStoreResult<()> {
        self.execute_cmd(|conn| {
            if let Some(ttl) = ttl_seconds {
                conn.set_ex(key, value, ttl)
            } else {
                conn.set(key, value)
            }
        }).await
    }

    /// Get key value
    /// الحصول على قيمة المفتاح
    async fn get_key_value(&self, key: &str) -> StateStoreResult<Option<String>> {
        self.execute_cmd(|conn| conn.get(key)).await
    }

    /// Delete key
    /// حذف المفتاح
    async fn delete_key(&self, key: &str) -> StateStoreResult<bool> {
        self.execute_cmd(|conn| conn.del(key)).await
    }

    /// Check if key exists
    /// التحقق من وجود المفتاح
    async fn key_exists(&self, key: &str) -> StateStoreResult<bool> {
        self.execute_cmd(|conn| conn.exists(key)).await
    }

    /// Add to sorted set
    /// إضافة إلى مجموعة مرتبة
    async fn add_to_sorted_set(&self, key: &str, score: f64, member: &str) -> StateStoreResult<()> {
        self.execute_cmd(|conn| conn.zadd(key, score, member)).await
    }

    /// Get range from sorted set
    /// الحصول على نطاق من مجموعة مرتبة
    async fn get_sorted_set_range(&self, key: &str, start: isize, end: isize) -> StateStoreResult<Vec<String>> {
        self.execute_cmd(|conn| conn.zrange(key, start, end)).await
    }

    /// Get range from sorted set by score
    /// الحصول على نطاق من مجموعة مرتبة حسب النقاط
    async fn get_sorted_set_range_by_score(
        &self, 
        key: &str, 
        min: f64, 
        max: f64
    ) -> StateStoreResult<Vec<String>> {
        self.execute_cmd(|conn| conn.zrangebyscore(key, min, max)).await
    }

    /// Remove from sorted set
    /// إزالة من مجموعة مرتبة
    async fn remove_from_sorted_set(&self, key: &str, member: &str) -> StateStoreResult<bool> {
        self.execute_cmd(|conn| conn.zrem(key, member)).await
    }

    /// Add to set
    /// إضافة إلى مجموعة
    async fn add_to_set(&self, key: &str, member: &str) -> StateStoreResult<()> {
        self.execute_cmd(|conn| conn.sadd(key, member)).await
    }

    /// Get all set members
    /// الحصول على جميع أعضاء المجموعة
    async fn get_set_members(&self, key: &str) -> StateStoreResult<Vec<String>> {
        self.execute_cmd(|conn| conn.smembers(key)).await
    }

    /// Remove from set
    /// إزالة من مجموعة
    async fn remove_from_set(&self, key: &str, member: &str) -> StateStoreResult<bool> {
        self.execute_cmd(|conn| conn.srem(key, member)).await
    }

    /// Set lock with TTL
    /// تعيين قفل مع TTL
    async fn set_lock_with_ttl(&self, key: &str, value: &str, ttl_seconds: u64) -> StateStoreResult<bool> {
        self.execute_cmd(|conn| conn.set_nx(key, value, Some(ttl_seconds))).await
    }

    /// Release lock
    /// تحرير القفل
    async fn release_lock_value(&self, key: &str) -> StateStoreResult<bool> {
        self.delete_key(key).await
    }
}

#[async_trait]
impl StateStore for RedisStateStore {
    type Error = StateStoreError;

    async fn save_state(&self, agent_id: &str, state: &AgentState) -> StateStoreResult<()> {
        self.validate_agent_id(agent_id)?;
        
        let key_schema = AgentKeySchema::new(agent_id);
        let key = key_schema.state_key();
        let value = self.serialize_to_json(state)?;
        
        self.set_key_with_ttl(&key, &value, None).await
    }

    async fn get_state(&self, agent_id: &str) -> StateStoreResult<Option<AgentState>> {
        self.validate_agent_id(agent_id)?;
        
        let key_schema = AgentKeySchema::new(agent_id);
        let key = key_schema.state_key();
        
        match self.get_key_value(&key).await? {
            Some(json) => {
                let state = self.deserialize_from_json(&json)?;
                Ok(Some(state))
            }
            None => Ok(None),
        }
    }

    async fn update_status(&self, agent_id: &str, status: crate::agent_keys::AgentStatus) -> StateStoreResult<()> {
        self.validate_agent_id(agent_id)?;
        
        let mut state = self.get_state(agent_id).await?;
        if let Some(ref mut s) = state {
            s.status = status.clone();
            s.last_activity = Utc::now();
            self.save_state(agent_id, s).await
        } else {
            Err(StateStoreError::AgentNotFound(agent_id.to_string()))
        }
    }

    async fn append_history(&self, agent_id: &str, entry: &AgentHistoryEntry) -> StateStoreResult<()> {
        self.validate_agent_id(agent_id)?;
        
        let key_schema = AgentKeySchema::new(agent_id);
        let key = key_schema.history_key();
        let value = self.serialize_to_json(entry)?;
        
        // Use timestamp as score for sorted set
        let score = entry.timestamp.timestamp() as f64;
        self.add_to_sorted_set(&key, score, &value).await
    }

    async fn get_history(&self, agent_id: &str, limit: Option<usize>) -> StateStoreResult<Vec<AgentHistoryEntry>> {
        self.validate_agent_id(agent_id)?;
        
        let key_schema = AgentKeySchema::new(agent_id);
        let key = key_schema.history_key();
        
        let end = limit.unwrap_or(100) as isize - 1;
        let json_entries = self.get_sorted_set_range(&key, -end, -1).await?;
        
        let mut entries = Vec::new();
        for json_entry in json_entries {
            let entry = self.deserialize_from_json(&json_entry)?;
            entries.push(entry);
        }
        
        // Reverse to get chronological order (newest first)
        entries.reverse();
        Ok(entries)
    }

    async fn get_history_by_time_range(
        &self, 
        agent_id: &str, 
        start: DateTime<Utc>, 
        end: DateTime<Utc>
    ) -> StateStoreResult<Vec<AgentHistoryEntry>> {
        self.validate_agent_id(agent_id)?;
        
        let key_schema = AgentKeySchema::new(agent_id);
        let key = key_schema.history_key();
        
        let min_score = start.timestamp() as f64;
        let max_score = end.timestamp() as f64;
        
        let json_entries = self.get_sorted_set_range_by_score(&key, min_score, max_score).await?;
        
        let mut entries = Vec::new();
        for json_entry in json_entries {
            let entry = self.deserialize_from_json(&json_entry)?;
            entries.push(entry);
        }
        
        // Sort by timestamp
        entries.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));
        Ok(entries)
    }

    async fn save_memory(&self, agent_id: &str, memory: &AgentMemoryEntry) -> StateStoreResult<()> {
        self.validate_agent_id(agent_id)?;
        
        let key_schema = AgentKeySchema::new(agent_id);
        let key = key_schema.memory_key();
        let value = self.serialize_to_json(memory)?;
        
        // Use timestamp + importance as score for sorting
        let score = memory.timestamp.timestamp() as f64 + memory.importance_score;
        self.add_to_sorted_set(&key, score, &value).await
    }

    async fn get_memory(&self, agent_id: &str, limit: Option<usize>) -> StateStoreResult<Vec<AgentMemoryEntry>> {
        self.validate_agent_id(agent_id)?;
        
        let key_schema = AgentKeySchema::new(agent_id);
        let key = key_schema.memory_key();
        
        let end = limit.unwrap_or(100) as isize - 1;
        let json_entries = self.get_sorted_set_range(&key, -end, -1).await?;
        
        let mut memories = Vec::new();
        for json_entry in json_entries {
            let memory = self.deserialize_from_json(&json_entry)?;
            memories.push(memory);
        }
        
        // Reverse to get most recent first
        memories.reverse();
        Ok(memories)
    }

    async fn search_memory(&self, agent_id: &str, query: &str, limit: Option<usize>) -> StateStoreResult<Vec<AgentMemoryEntry>> {
        // Get all memories and filter by content (simplified implementation)
        let memories = self.get_memory(agent_id, limit).await?;
        
        let query_lower = query.to_lowercase();
        let filtered_memories: Vec<AgentMemoryEntry> = memories
            .into_iter()
            .filter(|memory| {
                memory.content.to_lowercase().contains(&query_lower) ||
                memory.tags.iter().any(|tag| tag.to_lowercase().contains(&query_lower))
            })
            .collect();
        
        Ok(filtered_memories)
    }

    async fn save_config(&self, agent_id: &str, config: &AgentConfiguration) -> StateStoreResult<()> {
        self.validate_agent_id(agent_id)?;
        
        let key_schema = AgentKeySchema::new(agent_id);
        let key = key_schema.config_key();
        let value = self.serialize_to_json(config)?;
        
        self.set_key_with_ttl(&key, &value, None).await
    }

    async fn get_config(&self, agent_id: &str) -> StateStoreResult<Option<AgentConfiguration>> {
        self.validate_agent_id(agent_id)?;
        
        let key_schema = AgentKeySchema::new(agent_id);
        let key = key_schema.config_key();
        
        match self.get_key_value(&key).await? {
            Some(json) => {
                let config = self.deserialize_from_json(&json)?;
                Ok(Some(config))
            }
            None => Ok(None),
        }
    }

    async fn delete_agent(&self, agent_id: &str) -> StateStoreResult<()> {
        self.validate_agent_id(agent_id)?;
        
        let key_schema = AgentKeySchema::new(agent_id);
        
        // Delete all agent-related keys
        let keys_to_delete = vec![
            key_schema.state_key(),
            key_schema.history_key(),
            key_schema.memory_key(),
            key_schema.config_key(),
            key_schema.metrics_key(),
            key_schema.lock_key(),
        ];
        
        for key in keys_to_delete {
            self.delete_key(&key).await?;
        }
        
        // Remove from agent lists
        self.remove_from_set(&AgentKeySchema::agents_list_key(), agent_id).await?;
        self.remove_from_set(&AgentKeySchema::active_agents_key(), agent_id).await?;
        
        Ok(())
    }

    async fn list_agents(&self) -> StateStoreResult<Vec<String>> {
        self.get_set_members(&AgentKeySchema::agents_list_key()).await
    }

    async fn get_active_agents(&self) -> StateStoreResult<Vec<String>> {
        self.get_set_members(&AgentKeySchema::active_agents_key()).await
    }

    async fn agent_exists(&self, agent_id: &str) -> StateStoreResult<bool> {
        self.validate_agent_id(agent_id)?;
        
        let key_schema = AgentKeySchema::new(agent_id);
        let key = key_schema.state_key();
        
        self.key_exists(&key).await
    }

    async fn set_lock(&self, agent_id: &str, ttl_seconds: u64) -> StateStoreResult<bool> {
        self.validate_agent_id(agent_id)?;
        
        let key_schema = AgentKeySchema::new(agent_id);
        let key = key_schema.lock_key();
        let value = format!("locked:{}", Utc::now().timestamp());
        
        self.set_lock_with_ttl(&key, &value, ttl_seconds).await
    }

    async fn release_lock(&self, agent_id: &str) -> StateStoreResult<bool> {
        self.validate_agent_id(agent_id)?;
        
        let key_schema = AgentKeySchema::new(agent_id);
        let key = key_schema.lock_key();
        
        self.release_lock_value(&key).await
    }

    async fn get_metrics(&self, agent_id: &str) -> StateStoreResult<Option<crate::agent_keys::AgentMetrics>> {
        self.validate_agent_id(agent_id)?;
        
        let key_schema = AgentKeySchema::new(agent_id);
        let key = key_schema.metrics_key();
        
        match self.get_key_value(&key).await? {
            Some(json) => {
                let metrics = self.deserialize_from_json(&json)?;
                Ok(Some(metrics))
            }
            None => Ok(None),
        }
    }

    async fn update_metrics(&self, agent_id: &str, metrics: &crate::agent_keys::AgentMetrics) -> StateStoreResult<()> {
        self.validate_agent_id(agent_id)?;
        
        let key_schema = AgentKeySchema::new(agent_id);
        let key = key_schema.metrics_key();
        let value = self.serialize_to_json(metrics)?;
        
        self.set_key_with_ttl(&key, &value, None).await
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::agent_keys::{AgentStatus, AgentEventType, MemoryType};

    #[test]
    fn test_state_store_error() {
        let error = StateStoreError::AgentNotFound("test-agent".to_string());
        assert_eq!(error.to_string(), "Agent not found: test-agent");
    }

    #[test]
    fn test_agent_key_validation() {
        let store = RedisStateStore::new(deadpool_redis::Pool::default());
        
        assert!(store.validate_agent_id("valid-agent-123").is_ok());
        assert!(store.validate_agent_id("").is_err());
        assert!(store.validate_agent_id("agent@invalid").is_err());
    }

    #[test]
    fn test_serialization() {
        let store = RedisStateStore::new(deadpool_redis::Pool::default());
        
        let state = AgentState {
            agent_id: "test-agent".to_string(),
            status: AgentStatus::Processing,
            last_activity: Utc::now(),
            current_task: Some("task-123".to_string()),
            configuration: serde_json::json!({"key": "value"}),
            metrics: crate::agent_keys::AgentMetrics::default(),
            error_state: None,
            metadata: std::collections::HashMap::new(),
        };
        
        let json = store.serialize_to_json(&state).unwrap();
        let deserialized: AgentState = store.deserialize_from_json(&json).unwrap();
        
        assert_eq!(state.agent_id, deserialized.agent_id);
        assert_eq!(state.status, deserialized.status);
    }

    #[test]
    fn test_history_entry_serialization() {
        let store = RedisStateStore::new(deadpool_redis::Pool::default());
        
        let entry = AgentHistoryEntry {
            id: "entry-123".to_string(),
            timestamp: Utc::now(),
            event_type: AgentEventType::TaskStarted,
            data: serde_json::json!({"task_id": "task-456"}),
            agent_status: AgentStatus::Processing,
            execution_time_ms: Some(150.5),
            metadata: std::collections::HashMap::new(),
        };
        
        let json = store.serialize_to_json(&entry).unwrap();
        let deserialized: AgentHistoryEntry = store.deserialize_from_json(&json).unwrap();
        
        assert_eq!(entry.id, deserialized.id);
        assert_eq!(entry.event_type, deserialized.event_type);
    }

    #[test]
    fn test_memory_entry_serialization() {
        let store = RedisStateStore::new(deadpool_redis::Pool::default());
        
        let memory = AgentMemoryEntry {
            id: "memory-123".to_string(),
            memory_type: MemoryType::LongTerm,
            content: "Test memory content".to_string(),
            embedding: Some(vec![0.1, 0.2, 0.3]),
            timestamp: Utc::now(),
            importance_score: 0.8,
            access_count: 5,
            last_accessed: Utc::now(),
            tags: vec!["test".to_string(), "memory".to_string()],
            metadata: std::collections::HashMap::new(),
        };
        
        let json = store.serialize_to_json(&memory).unwrap();
        let deserialized: AgentMemoryEntry = store.deserialize_from_json(&json).unwrap();
        
        assert_eq!(memory.id, deserialized.id);
        assert_eq!(memory.memory_type, deserialized.memory_type);
    }
}
