// Copyright (c) 2024 Market Intel Brain Team
// Agent Redis Key Schema - Strict key management for agent state and memory
// مخطط مفاتيح Redis للوكلاء - إدارة صارمة لحالة الوكيل والذاكرة

use std::fmt;
use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Agent Redis Key Schema Helper
/// مساعد مخطط مفاتيح Redis للوكلاء
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AgentKeySchema {
    agent_id: String,
}

impl AgentKeySchema {
    /// Create a new agent key schema
    /// إنشاء مخطط مفاتيح وكيل جديد
    pub fn new(agent_id: impl Into<String>) -> Self {
        Self {
            agent_id: agent_id.into(),
        }
    }

    /// Get the agent ID
    /// الحصول على معرف الوكيل
    pub fn agent_id(&self) -> &str {
        &self.agent_id
    }

    /// Generate state key for agent
    /// إنشاء مفتاح الحالة للوكيل
    /// Pattern: `agent:{agent_id}:state`
    pub fn state_key(&self) -> String {
        format!("agent:{}:state", self.agent_id)
    }

    /// Generate history key for agent
    /// إنشاء مفتاح السجل للوكيل
    /// Pattern: `agent:{agent_id}:history`
    pub fn history_key(&self) -> String {
        format!("agent:{}:history", self.agent_id)
    }

    /// Generate memory key for agent
    /// إنشاء مفتاح الذاكرة للوكيل
    /// Pattern: `agent:{agent_id}:memory`
    pub fn memory_key(&self) -> String {
        format!("agent:{}:memory", self.agent_id)
    }

    /// Generate config key for agent
    /// إنشاء مفتاح التكوين للوكيل
    /// Pattern: `agent:{agent_id}:config`
    pub fn config_key(&self) -> String {
        format!("agent:{}:config", self.agent_id)
    }

    /// Generate metrics key for agent
    /// إنشاء مفتاح المقاييس للوكيل
    /// Pattern: `agent:{agent_id}:metrics`
    pub fn metrics_key(&self) -> String {
        format!("agent:{}:metrics", self.agent_id)
    }

    /// Generate lock key for agent
    /// إنشاء مفتاح القفل للوكيل
    /// Pattern: `agent:{agent_id}:lock`
    pub fn lock_key(&self) -> String {
        format!("agent:{}:lock", self.agent_id)
    }

    /// Generate session key for agent
    /// إنشاء مفتاح الجلسة للوكيل
    /// Pattern: `agent:{agent_id}:session:{session_id}`
    pub fn session_key(&self, session_id: impl Into<String>) -> String {
        format!("agent:{}:session:{}", self.agent_id, session_id.into())
    }

    /// Generate task key for agent
    /// إنشاء مفتاح المهمة للوكيل
    /// Pattern: `agent:{agent_id}:task:{task_id}`
    pub fn task_key(&self, task_id: impl Into<String>) -> String {
        format!("agent:{}:task:{}", self.agent_id, task_id.into())
    }

    /// Generate temporary key for agent
    /// إنشاء مفتاح مؤقت للوكيل
    /// Pattern: `agent:{agent_id}:temp:{key}`
    pub fn temp_key(&self, key: impl Into<String>) -> String {
        format!("agent:{}:temp:{}", self.agent_id, key.into())
    }

    /// Generate global agent list key
    /// إنشاء مفتاح قائمة الوكلاء العامة
    /// Pattern: `agents:all`
    pub fn agents_list_key() -> String {
        "agents:all".to_string()
    }

    /// Generate active agents key
    /// إنشاء مفتاح الوكلاء النشطين
    /// Pattern: `agents:active`
    pub fn active_agents_key() -> String {
        "agents:active".to_string()
    }

    /// Generate agent type index key
    /// إنشاء مفتاح فهرس نوع الوكيل
    /// Pattern: `agents:type:{agent_type}`
    pub fn agent_type_index_key(agent_type: impl Into<String>) -> String {
        format!("agents:type:{}", agent_type.into())
    }

    /// Parse agent ID from key
    /// استخراج معرف الوكيل من المفتاح
    pub fn parse_agent_id_from_key(key: &str) -> Option<String> {
        if key.starts_with("agent:") {
            let parts: Vec<&str> = key.split(':').collect();
            if parts.len() >= 2 {
                Some(parts[1].to_string())
            } else {
                None
            }
        } else {
            None
        }
    }

    /// Validate key format
    /// التحقق من صحة تنسيق المفتاح
    pub fn validate_key_format(&self, key: &str) -> bool {
        let expected_prefix = format!("agent:{}:", self.agent_id);
        key.starts_with(&expected_prefix)
    }
}

impl fmt::Display for AgentKeySchema {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "AgentKeySchema({})", self.agent_id)
    }
}

/// Agent State Data Structure
/// بنية بيانات حالة الوكيل
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentState {
    /// Agent identifier
    /// معرف الوكيل
    pub agent_id: String,
    
    /// Current status
    /// الحالة الحالية
    pub status: AgentStatus,
    
    /// Last activity timestamp
    /// وقت آخر نشاط
    pub last_activity: chrono::DateTime<chrono::Utc>,
    
    /// Current task or operation
    /// المهمة أو العملية الحالية
    pub current_task: Option<String>,
    
    /// Agent configuration
    /// تكوين الوكيل
    pub configuration: serde_json::Value,
    
    /// Performance metrics
    /// مقاييس الأداء
    pub metrics: AgentMetrics,
    
    /// Error state if any
    /// حالة الخطأ إن وجدت
    pub error_state: Option<AgentError>,
    
    /// Additional metadata
    /// بيانات وصفية إضافية
    pub metadata: std::collections::HashMap<String, serde_json::Value>,
}

/// Agent Status Enumeration
/// تعداد حالة الوكيل
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum AgentStatus {
    /// Agent is idle
    /// الوكيل في حالة خمول
    Idle,
    
    /// Agent is processing
    /// الوكيل يعالج
    Processing,
    
    /// Agent is waiting
    /// الوكيل ينتظر
    Waiting,
    
    /// Agent has an error
    /// الوكيل به خطأ
    Error,
    
    /// Agent is shutting down
    /// الوكيل في حالة إيقاف
    ShuttingDown,
    
    /// Agent is stopped
    /// الوكيل متوقف
    Stopped,
}

impl Default for AgentStatus {
    fn default() -> Self {
        Self::Idle
    }
}

/// Agent Metrics
/// مقاييس الوكيل
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentMetrics {
    /// Number of tasks completed
    /// عدد المهام المكتملة
    pub tasks_completed: u64,
    
    /// Number of tasks failed
    /// عدد المهام الفاشلة
    pub tasks_failed: u64,
    
    /// Average processing time in milliseconds
    /// متوسط وقت المعالجة بالمللي ثانية
    pub avg_processing_time_ms: f64,
    
    /// Memory usage in bytes
    /// استخدام الذاكرة بالبايت
    pub memory_usage_bytes: u64,
    
    /// CPU usage percentage
    /// نسبة استخدام المعالج
    pub cpu_usage_percent: f64,
    
    /// Network I/O in bytes
    /// إدخال/إخراج الشبكة بالبايت
    pub network_io_bytes: u64,
    
    /// Uptime in seconds
    /// وقت التشغيل بالثواني
    pub uptime_seconds: u64,
    
    /// Last heartbeat timestamp
    /// وقت آخر نبضة قلب
    pub last_heartbeat: chrono::DateTime<chrono::Utc>,
}

impl Default for AgentMetrics {
    fn default() -> Self {
        Self {
            tasks_completed: 0,
            tasks_failed: 0,
            avg_processing_time_ms: 0.0,
            memory_usage_bytes: 0,
            cpu_usage_percent: 0.0,
            network_io_bytes: 0,
            uptime_seconds: 0,
            last_heartbeat: chrono::Utc::now(),
        }
    }
}

/// Agent Error Information
/// معلومات خطأ الوكيل
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentError {
    /// Error code
    /// رمز الخطأ
    pub code: String,
    
    /// Error message
    /// رسالة الخطأ
    pub message: String,
    
    /// Error timestamp
    /// وقت الخطأ
    pub timestamp: chrono::DateTime<chrono::Utc>,
    
    /// Error severity
    /// شدة الخطأ
    pub severity: ErrorSeverity,
    
    /// Error context
    /// سياق الخطأ
    pub context: std::collections::HashMap<String, serde_json::Value>,
    
    /// Stack trace if available
    /// تتبع المكدس إن وجد
    pub stack_trace: Option<String>,
}

/// Error Severity Enumeration
/// تعداد شدة الخطأ
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum ErrorSeverity {
    /// Low severity error
    /// خطأ منخفض الشدة
    Low,
    
    /// Medium severity error
    /// خطأ متوسط الشدة
    Medium,
    
    /// High severity error
    /// خطأ عالي الشدة
    High,
    
    /// Critical error
    /// خطأ حرج
    Critical,
}

/// Agent History Entry
/// إدخال سجل الوكيل
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentHistoryEntry {
    /// Entry ID
    /// معرف الإدخال
    pub id: String,
    
    /// Timestamp
    /// وقت الإدخال
    pub timestamp: chrono::DateTime<chrono::Utc>,
    
    /// Event type
    /// نوع الحدث
    pub event_type: AgentEventType,
    
    /// Event data
    /// بيانات الحدث
    pub data: serde_json::Value,
    
    /// Agent status at the time of event
    /// حالة الوكيل وقت الحدث
    pub agent_status: AgentStatus,
    
    /// Execution time in milliseconds
    /// وقت التنفيذ بالمللي ثانية
    pub execution_time_ms: Option<f64>,
    
    /// Additional metadata
    /// بيانات وصفية إضافية
    pub metadata: std::collections::HashMap<String, serde_json::Value>,
}

/// Agent Event Type Enumeration
/// تعداد نوع حدث الوكيل
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum AgentEventType {
    /// Agent started
    /// بدء الوكيل
    Started,
    
    /// Agent stopped
    /// إيقاف الوكيل
    Stopped,
    
    /// Task started
    /// بدء المهمة
    TaskStarted,
    
    /// Task completed
    /// إكمال المهمة
    TaskCompleted,
    
    /// Task failed
    /// فشل المهمة
    TaskFailed,
    
    /// Configuration changed
    /// تغيير التكوين
    ConfigurationChanged,
    
    /// Error occurred
    /// حدث خطأ
    ErrorOccurred,
    
    /// Heartbeat
    /// نبضة القلب
    Heartbeat,
    
    /// Custom event
    /// حدث مخصص
    Custom(String),
}

/// Agent Memory Entry
/// إدخال ذاكرة الوكيل
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentMemoryEntry {
    /// Entry ID
    /// معرف الإدخال
    pub id: String,
    
    /// Memory type
    /// نوع الذاكرة
    pub memory_type: MemoryType,
    
    /// Content
    /// المحتوى
    pub content: String,
    
    /// Vector embedding for similarity search
    /// تضمين المتجه للبحث عن التشابه
    pub embedding: Option<Vec<f32>>,
    
    /// Timestamp
    /// وقت الإدخال
    pub timestamp: chrono::DateTime<chrono::Utc>,
    
    /// Importance score (0.0 to 1.0)
    /// درجة الأهمية (0.0 إلى 1.0)
    pub importance_score: f64,
    
    /// Access count
    /// عدد الوصول
    pub access_count: u64,
    
    /// Last access timestamp
    /// وقت آخر وصول
    pub last_accessed: chrono::DateTime<chrono::Utc>,
    
    /// Tags
    /// العلامات
    pub tags: Vec<String>,
    
    /// Additional metadata
    /// بيانات وصفية إضافية
    pub metadata: std::collections::HashMap<String, serde_json::Value>,
}

/// Memory Type Enumeration
/// تعداد نوع الذاكرة
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum MemoryType {
    /// Short-term memory
    /// الذاكرة قصيرة المدى
    ShortTerm,
    
    /// Long-term memory
    /// الذاكرة طويلة المدى
    LongTerm,
    
    /// Working memory
    /// الذاكرة العاملة
    Working,
    
    /// Episodic memory
    /// الذاكرة الحلقاتية
    Episodic,
    
    /// Semantic memory
    /// الذاكرة الدلالية
    Semantic,
    
    /// Procedural memory
    /// الذاكرة الإجرائية
    Procedural,
}

/// Agent Configuration
/// تكوين الوكيل
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentConfiguration {
    /// Agent type
    /// نوع الوكيل
    pub agent_type: String,
    
    /// Agent version
    /// نسخة الوكيل
    pub version: String,
    
    /// Maximum concurrent tasks
    /// الحد الأقصى للمهام المتزامنة
    pub max_concurrent_tasks: u32,
    
    /// Task timeout in seconds
    /// مهلة المهمة بالثواني
    pub task_timeout_seconds: u64,
    
    /// Memory retention period in days
    /// فترة الاحتفاظ بالذاكرة بالأيام
    pub memory_retention_days: u32,
    
    /// Heartbeat interval in seconds
    /// فاصل نبضة القلب بالثواني
    pub heartbeat_interval_seconds: u64,
    
    /// Auto-restart configuration
    /// تكوين إعادة التشغيل التلقائي
    pub auto_restart: bool,
    
    /// Resource limits
    /// حدود الموارد
    pub resource_limits: ResourceLimits,
    
    /// Custom settings
    /// إعدادات مخصصة
    pub custom_settings: std::collections::HashMap<String, serde_json::Value>,
}

/// Resource Limits
/// حدود الموارد
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceLimits {
    /// Maximum memory in MB
    /// أقصى ذاكرة بالميجابايت
    pub max_memory_mb: u64,
    
    /// Maximum CPU percentage
    /// أقصى نسبة معالج
    pub max_cpu_percent: f64,
    
    /// Maximum network bandwidth in MB/s
    /// أقصى عرض نطاق شبكة بالميجابايت/ثانية
    pub max_network_bandwidth_mbps: f64,
    
    /// Maximum disk space in MB
    /// أقصى مساحة قرص بالميجابايت
    pub max_disk_space_mb: u64,
}

impl Default for ResourceLimits {
    fn default() -> Self {
        Self {
            max_memory_mb: 1024,
            max_cpu_percent: 80.0,
            max_network_bandwidth_mbps: 100.0,
            max_disk_space_mb: 10240,
        }
    }
}

/// Redis Key Schema Error
/// خطأ مخطط مفاتيح Redis
#[derive(Error, Debug)]
pub enum AgentKeyError {
    #[error("Invalid agent ID: {0}")]
    InvalidAgentId(String),
    
    #[error("Invalid key format: {0}")]
    InvalidKeyFormat(String),
    
    #[error("Agent ID not found in key: {0}")]
    AgentIdNotFound(String),
    
    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),
    
    #[error("Chrono error: {0}")]
    ChronoError(#[from] chrono::ParseError),
}

impl AgentKeySchema {
    /// Validate agent ID format
    /// التحقق من تنسيق معرف الوكيل
    pub fn validate_agent_id(agent_id: &str) -> Result<(), AgentKeyError> {
        if agent_id.is_empty() {
            return Err(AgentKeyError::InvalidAgentId("Agent ID cannot be empty".to_string()));
        }
        
        if agent_id.len() > 255 {
            return Err(AgentKeyError::InvalidAgentId("Agent ID too long (max 255 characters)".to_string()));
        }
        
        // Check for valid characters (alphanumeric, underscore, hyphen)
        if !agent_id.chars().all(|c| c.is_alphanumeric() || c == '_' || c == '-') {
            return Err(AgentKeyError::InvalidAgentId("Agent ID contains invalid characters".to_string()));
        }
        
        Ok(())
    }
    
    /// Create with validation
    /// إنشاء مع التحقق
    pub fn with_validation(agent_id: impl Into<String>) -> Result<Self, AgentKeyError> {
        let agent_id = agent_id.into();
        Self::validate_agent_id(&agent_id)?;
        Ok(Self { agent_id })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Utc;

    #[test]
    fn test_agent_key_schema() {
        let schema = AgentKeySchema::new("test-agent-123");
        
        assert_eq!(schema.state_key(), "agent:test-agent-123:state");
        assert_eq!(schema.history_key(), "agent:test-agent-123:history");
        assert_eq!(schema.memory_key(), "agent:test-agent-123:memory");
        assert_eq!(schema.config_key(), "agent:test-agent-123:config");
        assert_eq!(schema.metrics_key(), "agent:test-agent-123:metrics");
        assert_eq!(schema.lock_key(), "agent:test-agent-123:lock");
        assert_eq!(schema.session_key("session-1"), "agent:test-agent-123:session:session-1");
        assert_eq!(schema.task_key("task-1"), "agent:test-agent-123:task:task-1");
        assert_eq!(schema.temp_key("temp-key"), "agent:test-agent-123:temp:temp-key");
    }

    #[test]
    fn test_parse_agent_id_from_key() {
        assert_eq!(
            AgentKeySchema::parse_agent_id_from_key("agent:test-123:state"),
            Some("test-123".to_string())
        );
        assert_eq!(
            AgentKeySchema::parse_agent_id_from_key("agent:test-456:history"),
            Some("test-456".to_string())
        );
        assert_eq!(
            AgentKeySchema::parse_agent_id_from_key("other:key"),
            None
        );
    }

    #[test]
    fn test_validate_agent_id() {
        assert!(AgentKeySchema::validate_agent_id("valid-agent-123").is_ok());
        assert!(AgentKeySchema::validate_agent_id("agent_456").is_ok());
        
        assert!(AgentKeySchema::validate_agent_id("").is_err());
        assert!(AgentKeySchema::validate_agent_id("agent@invalid").is_err());
        
        let long_id = "a".repeat(256);
        assert!(AgentKeySchema::validate_agent_id(&long_id).is_err());
    }

    #[test]
    fn test_agent_state_serialization() {
        let state = AgentState {
            agent_id: "test-agent".to_string(),
            status: AgentStatus::Processing,
            last_activity: Utc::now(),
            current_task: Some("task-123".to_string()),
            configuration: serde_json::json!({"key": "value"}),
            metrics: AgentMetrics::default(),
            error_state: None,
            metadata: std::collections::HashMap::new(),
        };
        
        let serialized = serde_json::to_string(&state).unwrap();
        let deserialized: AgentState = serde_json::from_str(&serialized).unwrap();
        
        assert_eq!(state.agent_id, deserialized.agent_id);
        assert_eq!(state.status, deserialized.status);
    }

    #[test]
    fn test_agent_history_entry() {
        let entry = AgentHistoryEntry {
            id: "entry-123".to_string(),
            timestamp: Utc::now(),
            event_type: AgentEventType::TaskStarted,
            data: serde_json::json!({"task_id": "task-456"}),
            agent_status: AgentStatus::Processing,
            execution_time_ms: Some(150.5),
            metadata: std::collections::HashMap::new(),
        };
        
        let serialized = serde_json::to_string(&entry).unwrap();
        let deserialized: AgentHistoryEntry = serde_json::from_str(&serialized).unwrap();
        
        assert_eq!(entry.id, deserialized.id);
        assert_eq!(entry.event_type, deserialized.event_type);
    }

    #[test]
    fn test_global_keys() {
        assert_eq!(AgentKeySchema::agents_list_key(), "agents:all");
        assert_eq!(AgentKeySchema::active_agents_key(), "agents:active");
        assert_eq!(AgentKeySchema::agent_type_index_key("analytics"), "agents:type:analytics");
        assert_eq!(AgentKeySchema::agent_type_index_key("trading"), "agents:type:trading");
    }
}
