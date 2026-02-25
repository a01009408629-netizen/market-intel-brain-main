// Copyright (c) 2024 Market Intel Brain Team
// Redis Manager - Efficient connection pool management for agent operations
/// مدير Redis - إدارة فعالة لمجمع الاتصالات لعمليات الوكلاء

use std::sync::Arc;
use std::time::Duration;
use deadpool_redis::{Config, Pool, Runtime};
use redis::Client;
use tokio::time::timeout;
use tracing::{info, warn, error, debug};
use crate::state_store::{StateStore, RedisStateStore, StateStoreError};
use crate::agent_keys::{AgentKeySchema, AgentState, AgentHistoryEntry, AgentMemoryEntry};

/// Redis Manager Configuration
/// تكوين مدير Redis
#[derive(Debug, Clone)]
pub struct RedisManagerConfig {
    /// Redis connection URL
    /// عنوان URL اتصال Redis
    pub connection_url: String,
    
    /// Maximum pool size
    /// الحد الأقصى لحجم المجمع
    pub max_pool_size: usize,
    
    /// Minimum pool size
    /// الحد الأدنى لحجم المجمع
    pub min_pool_size: Option<usize>,
    
    /// Connection timeout in seconds
    /// مهلة الاتصال بالثواني
    pub connection_timeout_seconds: u64,
    
    /// Command timeout in seconds
    /// مهلة الأمر بالثواني
    pub command_timeout_seconds: u64,
    
    /// Idle timeout in seconds
    /// مهلة الخمول بالثواني
    pub idle_timeout_seconds: Option<u64>,
    
    /// Maximum retries for failed operations
    /// أقصى عدد مرات إعادة المحاولة للعمليات الفاشلة
    pub max_retries: u32,
    
    /// Retry delay in milliseconds
    /// تأخير إعادة المحاولة بالمللي ثانية
    pub retry_delay_ms: u64,
    
    /// Enable connection health checks
    /// تمكين فحوصص صحة الاتصال
    pub enable_health_checks: bool,
    
    /// Health check interval in seconds
    /// فاصل فحص الصحة بالثواني
    pub health_check_interval_seconds: u64,
}

impl Default for RedisManagerConfig {
    fn default() -> Self {
        Self {
            connection_url: "redis://localhost:6379".to_string(),
            max_pool_size: 20,
            min_pool_size: Some(5),
            connection_timeout_seconds: 10,
            command_timeout_seconds: 5,
            idle_timeout_seconds: Some(300),
            max_retries: 3,
            retry_delay_ms: 1000,
            enable_health_checks: true,
            health_check_interval_seconds: 30,
        }
    }
}

/// Redis Manager
/// مدير Redis
pub struct RedisManager {
    /// Redis connection pool
    /// مجمع اتصالات Redis
    pool: Pool,
    
    /// Configuration
    /// التكوين
    config: RedisManagerConfig,
    
    /// State store instance
    /// مثيل تخزين الحالة
    state_store: Arc<RedisStateStore>,
    
    /// Metrics tracker
    /// متتبع المقاييس
    metrics: Arc<RedisMetrics>,
}

/// Redis Metrics
/// مقاييس Redis
#[derive(Debug, Default)]
pub struct RedisMetrics {
    /// Total operations
    /// إجمالي العمليات
    pub total_operations: std::sync::atomic::AtomicU64,
    
    /// Successful operations
    /// العمليات الناجحة
    pub successful_operations: std::sync::atomic::AtomicU64,
    
    /// Failed operations
    /// العمليات الفاشلة
    pub failed_operations: std::sync::atomic::AtomicU64,
    
    /// Connection errors
    /// أخطاء الاتصال
    pub connection_errors: std::sync::atomic::AtomicU64,
    
    /// Timeout errors
    /// أخطاء المهلة
    pub timeout_errors: std::sync::atomic::AtomicU64,
    
    /// Average response time in microseconds
    /// متوسط وقت الاستجابة بالميكروثانية
    pub avg_response_time_us: std::sync::atomic::AtomicU64,
    
    /// Pool size
    /// حجم المجمع
    pub pool_size: std::sync::atomic::AtomicUsize,
    
    /// Active connections
    /// الاتصالات النشطة
    pub active_connections: std::sync::atomic::AtomicUsize,
}

impl RedisManager {
    /// Create new Redis manager
    /// إنشاء مدير Redis جديد
    pub async fn new(config: RedisManagerConfig) -> Result<Self, StateStoreError> {
        info!("Creating Redis manager with config: {:?}", config);
        
        // Create Redis pool configuration
        let mut pool_config = Config::from_url(&config.connection_url);
        pool_config.max_size = config.max_pool_size;
        pool_config.timeouts = Some(deadpool_redis::Timeouts {
            wait: Some(Duration::from_secs(config.connection_timeout_seconds)),
            create: Some(Duration::from_secs(config.connection_timeout_seconds)),
            recycle: Some(Duration::from_secs(config.idle_timeout_seconds.unwrap_or(300))),
        });
        
        // Create connection pool
        let pool = pool_config.create_pool().map_err(|e| {
            StateStoreError::ConnectionError(format!("Failed to create Redis pool: {}", e))
        })?;
        
        // Test connection
        Self::test_connection(&pool).await?;
        
        let state_store = Arc::new(RedisStateStore::new(pool.clone()));
        let metrics = Arc::new(RedisMetrics::default());
        
        let manager = Self {
            pool,
            config,
            state_store,
            metrics,
        };
        
        // Start health checks if enabled
        if config.enable_health_checks {
            manager.start_health_checks().await;
        }
        
        info!("Redis manager created successfully");
        Ok(manager)
    }

    /// Test Redis connection
    /// اختبار اتصال Redis
    async fn test_connection(pool: &Pool) -> Result<(), StateStoreError> {
        let mut conn = pool.get().await.map_err(|e| {
            StateStoreError::ConnectionError(format!("Failed to get connection: {}", e))
        })?;
        
        let _: String = conn.get("ping").await.map_err(|e| {
            StateStoreError::ConnectionError(format!("Redis ping failed: {}", e))
        })?;
        
        info!("Redis connection test successful");
        Ok(())
    }

    /// Start health checks
    /// بدء فحوصص الصحة
    async fn start_health_checks(&self) {
        let pool = self.pool.clone();
        let config = self.config.clone();
        let metrics = self.metrics.clone();
        
        tokio::spawn(async move {
            let mut interval = tokio::time::interval(
                Duration::from_secs(config.health_check_interval_seconds)
            );
            
            loop {
                interval.tick().await;
                
                match Self::test_connection(&pool).await {
                    Ok(_) => {
                        debug!("Redis health check passed");
                    }
                    Err(e) => {
                        warn!("Redis health check failed: {}", e);
                        metrics.connection_errors.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                }
                
                // Update pool metrics
                let status = pool.status();
                metrics.pool_size.store(status.size, std::sync::atomic::Ordering::Relaxed);
                metrics.active_connections.store(
                    status.available + status.waiting, 
                    std::sync::atomic::Ordering::Relaxed
                );
            }
        });
    }

    /// Get state store instance
    /// الحصول على مثيل تخزين الحالة
    pub fn state_store(&self) -> Arc<RedisStateStore> {
        self.state_store.clone()
    }

    /// Get metrics
    /// الحصول على المقاييس
    pub fn get_metrics(&self) -> &RedisMetrics {
        &self.metrics
    }

    /// Execute operation with retry logic
    /// تنفيذ العملية مع منطق إعادة المحاولة
    async fn execute_with_retry<F, R, E>(&self, operation: F) -> Result<R, E>
    where
        F: Fn() -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<R, E>> + Send>>,
        E: std::fmt::Display,
    {
        let mut last_error = None;
        
        for attempt in 0..=self.config.max_retries {
            let start_time = std::time::Instant::now();
            
            let result = if self.config.command_timeout_seconds > 0 {
                timeout(
                    Duration::from_secs(self.config.command_timeout_seconds),
                    operation()
                )
                .await
                .map_err(|_| {
                    self.metrics.timeout_errors.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    StateStoreError::TimeoutError("Command timeout".to_string())
                })?
            } else {
                operation().await
            };
            
            let elapsed = start_time.elapsed();
            let elapsed_us = elapsed.as_micros() as u64;
            
            // Update metrics
            self.metrics.total_operations.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            
            match result {
                Ok(value) => {
                    self.metrics.successful_operations.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    
                    // Update average response time
                    let current_avg = self.metrics.avg_response_time_us.load(std::sync::atomic::Ordering::Relaxed);
                    let new_avg = (current_avg + elapsed_us) / 2;
                    self.metrics.avg_response_time_us.store(new_avg, std::sync::atomic::Ordering::Relaxed);
                    
                    return Ok(value);
                }
                Err(e) => {
                    self.metrics.failed_operations.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    last_error = Some(e);
                    
                    if attempt < self.config.max_retries {
                        warn!("Operation failed (attempt {}), retrying in {}ms: {}", 
                              attempt + 1, self.config.retry_delay_ms, e);
                        tokio::time::sleep(Duration::from_millis(self.config.retry_delay_ms)).await;
                    }
                }
            }
        }
        
        Err(last_error.unwrap())
    }

    /// Save agent state with retry
    /// حفظ حالة الوكيل مع إعادة المحاولة
    pub async fn save_state(&self, agent_id: &str, state: &AgentState) -> Result<(), StateStoreError> {
        let state_store = self.state_store.clone();
        let agent_id = agent_id.to_string();
        let state = state.clone();
        
        self.execute_with_retry(|| {
            Box::pin(async move {
                state_store.save_state(&agent_id, &state).await
            })
        }).await
    }

    /// Get agent state with retry
    /// الحصول على حالة الوكيل مع إعادة المحاولة
    pub async fn get_state(&self, agent_id: &str) -> Result<Option<AgentState>, StateStoreError> {
        let state_store = self.state_store.clone();
        let agent_id = agent_id.to_string();
        
        self.execute_with_retry(|| {
            Box::pin(async move {
                state_store.get_state(&agent_id).await
            })
        }).await
    }

    /// Append to agent history with retry
    /// إضافة إلى سجل الوكيل مع إعادة المحاولة
    pub async fn append_history(&self, agent_id: &str, entry: &AgentHistoryEntry) -> Result<(), StateStoreError> {
        let state_store = self.state_store.clone();
        let agent_id = agent_id.to_string();
        let entry = entry.clone();
        
        self.execute_with_retry(|| {
            Box::pin(async move {
                state_store.append_history(&agent_id, &entry).await
            })
        }).await
    }

    /// Save agent memory with retry
    /// حفظ ذاكرة الوكيل مع إعادة المحاولة
    pub async fn save_memory(&self, agent_id: &str, memory: &AgentMemoryEntry) -> Result<(), StateStoreError> {
        let state_store = self.state_store.clone();
        let agent_id = agent_id.to_string();
        let memory = memory.clone();
        
        self.execute_with_retry(|| {
            Box::pin(async move {
                state_store.save_memory(&agent_id, &memory).await
            })
        }).await
    }

    /// Batch save agent states
    /// حفظ حالات الوكلاء بشكل مجمع
    pub async fn batch_save_states(&self, states: Vec<(String, AgentState)>) -> Result<Vec<String>, StateStoreError> {
        let mut successful_saves = Vec::new();
        let mut failed_saves = Vec::new();
        
        // Process in parallel with limited concurrency
        let semaphore = Arc::new(tokio::sync::Semaphore::new(10)); // Limit to 10 concurrent operations
        let mut tasks = Vec::new();
        
        for (agent_id, state) in states {
            let semaphore = semaphore.clone();
            let manager = self.clone();
            
            let task = tokio::spawn(async move {
                let _permit = semaphore.acquire().await.unwrap();
                
                match manager.save_state(&agent_id, &state).await {
                    Ok(_) => Some(agent_id),
                    Err(e) => {
                        error!("Failed to save state for agent {}: {}", agent_id, e);
                        None
                    }
                }
            });
            
            tasks.push(task);
        }
        
        // Wait for all tasks to complete
        for task in tasks {
            match task.await {
                Ok(Some(agent_id)) => successful_saves.push(agent_id),
                Ok(None) => {}
                Err(e) => {
                    error!("Task failed: {}", e);
                    failed_saves.push("unknown".to_string());
                }
            }
        }
        
        if failed_saves.is_empty() {
            Ok(successful_saves)
        } else {
            Err(StateStoreError::Unknown(format!("Failed to save {} states", failed_saves.len())))
        }
    }

    /// Batch append to history
    /// إضافة مجمع إلى السجل
    pub async fn batch_append_history(&self, entries: Vec<(String, AgentHistoryEntry)>) -> Result<Vec<String>, StateStoreError> {
        let mut successful_appends = Vec::new();
        let mut failed_appends = Vec::new();
        
        let semaphore = Arc::new(tokio::sync::Semaphore::new(10));
        let mut tasks = Vec::new();
        
        for (agent_id, entry) in entries {
            let semaphore = semaphore.clone();
            let manager = self.clone();
            
            let task = tokio::spawn(async move {
                let _permit = semaphore.acquire().await.unwrap();
                
                match manager.append_history(&agent_id, &entry).await {
                    Ok(_) => Some(agent_id),
                    Err(e) => {
                        error!("Failed to append history for agent {}: {}", agent_id, e);
                        None
                    }
                }
            });
            
            tasks.push(task);
        }
        
        for task in tasks {
            match task.await {
                Ok(Some(agent_id)) => successful_appends.push(agent_id),
                Ok(None) => {}
                Err(e) => {
                    error!("Task failed: {}", e);
                    failed_appends.push("unknown".to_string());
                }
            }
        }
        
        if failed_appends.is_empty() {
            Ok(successful_appends)
        } else {
            Err(StateStoreError::Unknown(format!("Failed to append {} history entries", failed_appends.len())))
        }
    }

    /// Get connection pool status
    /// الحصول على حالة مجمع الاتصالات
    pub fn get_pool_status(&self) -> deadpool_redis::Status {
        self.pool.status()
    }

    /// Close the Redis manager
    /// إغلاق مدير Redis
    pub async fn close(&self) -> Result<(), StateStoreError> {
        info!("Closing Redis manager");
        
        // Close the connection pool
        self.pool.close().await;
        
        info!("Redis manager closed successfully");
        Ok(())
    }
}

impl Clone for RedisManager {
    fn clone(&self) -> Self {
        Self {
            pool: self.pool.clone(),
            config: self.config.clone(),
            state_store: self.state_store.clone(),
            metrics: self.metrics.clone(),
        }
    }
}

/// Agent State Manager
/// مدير حالة الوكيل
pub struct AgentStateManager {
    /// Redis manager
    /// مدير Redis
    redis_manager: Arc<RedisManager>,
}

impl AgentStateManager {
    /// Create new agent state manager
    /// إنشاء مدير حالة الوكيل جديد
    pub async fn new(redis_manager: Arc<RedisManager>) -> Self {
        Self { redis_manager }
    }

    /// Initialize agent
    /// تهيئة الوكيل
    pub async fn initialize_agent(&self, agent_id: &str, initial_state: AgentState) -> Result<(), StateStoreError> {
        info!("Initializing agent: {}", agent_id);
        
        // Save initial state
        self.redis_manager.save_state(agent_id, &initial_state).await?;
        
        // Add to agents list
        let key_schema = AgentKeySchema::new(agent_id);
        let state_store = self.redis_manager.state_store();
        
        // Add to global agents list
        state_store.add_to_set(&AgentKeySchema::agents_list_key(), agent_id).await?;
        
        // Add to active agents list
        state_store.add_to_set(&AgentKeySchema::active_agents_key(), agent_id).await?;
        
        // Create initial history entry
        let history_entry = AgentHistoryEntry {
            id: format!("init-{}", chrono::Utc::now().timestamp()),
            timestamp: chrono::Utc::now(),
            event_type: crate::agent_keys::AgentEventType::Started,
            data: serde_json::json!({"agent_id": agent_id}),
            agent_status: initial_state.status.clone(),
            execution_time_ms: None,
            metadata: std::collections::HashMap::new(),
        };
        
        self.redis_manager.append_history(agent_id, &history_entry).await?;
        
        info!("Agent {} initialized successfully", agent_id);
        Ok(())
    }

    /// Update agent status
    /// تحديث حالة الوكيل
    pub async fn update_agent_status(&self, agent_id: &str, status: crate::agent_keys::AgentStatus) -> Result<(), StateStoreError> {
        let state_store = self.redis_manager.state_store();
        
        // Update status in state
        state_store.update_status(agent_id, status.clone()).await?;
        
        // Create history entry
        let history_entry = AgentHistoryEntry {
            id: format!("status-{}", chrono::Utc::now().timestamp()),
            timestamp: chrono::Utc::now(),
            event_type: crate::agent_keys::AgentEventType::Custom("status_change".to_string()),
            data: serde_json::json!({"new_status": format!("{:?}", status)}),
            agent_status: status.clone(),
            execution_time_ms: None,
            metadata: std::collections::HashMap::new(),
        };
        
        self.redis_manager.append_history(agent_id, &history_entry).await?;
        
        // Update active agents list based on status
        match status {
            crate::agent_keys::AgentStatus::Stopped | crate::agent_keys::AgentStatus::Error => {
                state_store.remove_from_set(&AgentKeySchema::active_agents_key(), agent_id).await?;
            }
            _ => {
                state_store.add_to_set(&AgentKeySchema::active_agents_key(), agent_id).await?;
            }
        }
        
        Ok(())
    }

    /// Get agent summary
    /// الحصول على ملخص الوكيل
    pub async fn get_agent_summary(&self, agent_id: &str) -> Result<AgentSummary, StateStoreError> {
        let state = self.redis_manager.get_state(agent_id).await?
            .ok_or_else(|| StateStoreError::AgentNotFound(agent_id.to_string()))?;
        
        let history = self.redis_manager.state_store().get_history(agent_id, Some(10)).await?;
        let metrics = self.redis_manager.state_store().get_metrics(agent_id).await?;
        
        Ok(AgentSummary {
            agent_id: agent_id.to_string(),
            status: state.status,
            last_activity: state.last_activity,
            current_task: state.current_task,
            recent_history: history,
            metrics,
            error_state: state.error_state,
        })
    }
}

/// Agent Summary
/// ملخص الوكيل
#[derive(Debug, Clone)]
pub struct AgentSummary {
    /// Agent ID
    /// معرف الوكيل
    pub agent_id: String,
    
    /// Current status
    /// الحالة الحالية
    pub status: crate::agent_keys::AgentStatus,
    
    /// Last activity
    /// آخر نشاط
    pub last_activity: chrono::DateTime<chrono::Utc>,
    
    /// Current task
    /// المهمة الحالية
    pub current_task: Option<String>,
    
    /// Recent history
    /// السجل الحديث
    pub recent_history: Vec<AgentHistoryEntry>,
    
    /// Metrics
    /// المقاييس
    pub metrics: Option<crate::agent_keys::AgentMetrics>,
    
    /// Error state
    /// حالة الخطأ
    pub error_state: Option<crate::agent_keys::AgentError>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::agent_keys::{AgentStatus, AgentEventType};

    #[test]
    fn test_redis_manager_config_default() {
        let config = RedisManagerConfig::default();
        assert_eq!(config.connection_url, "redis://localhost:6379");
        assert_eq!(config.max_pool_size, 20);
        assert_eq!(config.connection_timeout_seconds, 10);
        assert_eq!(config.command_timeout_seconds, 5);
    }

    #[test]
    fn test_redis_metrics() {
        let metrics = RedisMetrics::default();
        assert_eq!(metrics.total_operations.load(std::sync::atomic::Ordering::Relaxed), 0);
        assert_eq!(metrics.successful_operations.load(std::sync::atomic::Ordering::Relaxed), 0);
        assert_eq!(metrics.failed_operations.load(std::sync::atomic::Ordering::Relaxed), 0);
    }

    #[tokio::test]
    async fn test_agent_summary_creation() {
        let state = AgentState {
            agent_id: "test-agent".to_string(),
            status: AgentStatus::Processing,
            last_activity: chrono::Utc::now(),
            current_task: Some("task-123".to_string()),
            configuration: serde_json::json!({"key": "value"}),
            metrics: crate::agent_keys::AgentMetrics::default(),
            error_state: None,
            metadata: std::collections::HashMap::new(),
        };
        
        let summary = AgentSummary {
            agent_id: "test-agent".to_string(),
            status: state.status,
            last_activity: state.last_activity,
            current_task: state.current_task,
            recent_history: vec![],
            metrics: Some(state.metrics),
            error_state: state.error_state,
        };
        
        assert_eq!(summary.agent_id, "test-agent");
        assert_eq!(summary.status, AgentStatus::Processing);
    }
}
