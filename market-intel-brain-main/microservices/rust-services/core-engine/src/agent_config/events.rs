// Copyright (c) 2024 Market Intel Brain Team
// Agent Configuration Events - Phase 21.5 Task C
// أحداث تكوين الوكلاء - المهمة 21.5 ج

use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use uuid::Uuid;

use super::config_types::{AgentConfig, ConfigError};

/// Configuration event types
/// أنواع أحداث التكوين
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ConfigEventType {
    /// Configuration updated
    /// تحديث التكوين
    UpdateConfig,
    
    /// Agent added
    /// إضافة وكيل
    AgentAdded,
    
    /// Agent removed
    /// إزالة وكيل
    AgentRemoved,
    
    /// Agent enabled/disabled
    /// تفعيل/تعطيل الوكيل
    AgentToggled,
    
    /// Agent parameters changed
    /// تغيير معلمات الوكيل
    AgentParamsChanged,
    
    /// Risk configuration changed
    /// تغيير تكوين المخاطر
    RiskConfigChanged,
    
    /// Monitoring configuration changed
    /// تغيير تكوين المراقبة
    MonitoringConfigChanged,
    
    /// Global configuration changed
    /// تغيير التكوين العالمي
    GlobalConfigChanged,
    
    /// Configuration validation failed
    /// فشل التحقق من التكوين
    ValidationFailed,
    
    /// Configuration reload completed
    /// إكمال إعادة تحميل التكوين
    ReloadCompleted,
    
    /// Configuration reload failed
    /// فشل إعادة تحميل التكوين
    ReloadFailed,
    
    /// Hot reload enabled/disabled
    /// تفعيل/تعطيل إعادة التحميل السريع
    HotReloadToggled,
    
    /// Custom event
    /// حدث مخصص
    Custom(String),
}

/// Configuration event
/// حدث التكوين
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigEvent {
    /// Event ID
    /// معرف الحدث
    pub id: String,
    
    /// Event type
    /// نوع الحدث
    pub event_type: ConfigEventType,
    
    /// Event timestamp
    /// وقت الحدث
    pub timestamp: DateTime<Utc>,
    
    /// Source of the event
    /// مصدر الحدث
    pub source: EventSource,
    
    /// Agent name (if applicable)
    /// اسم الوكيل (إذا كان ينطبق)
    pub agent_name: Option<String>,
    
    /// Event data
    /// بيانات الحدث
    pub data: HashMap<String, serde_json::Value>,
    
    /// Event severity
    /// شدة الحدث
    pub severity: EventSeverity,
    
    /// Event message
    /// رسالة الحدث
    pub message: String,
    
    /// Additional metadata
    /// بيانات وصفية إضافية
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Event source
/// مصدر الحدث
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum EventSource {
    /// File watcher
    /// مراقب الملفات
    FileWatcher,
    
    /// Configuration manager
    /// مدير التكوين
    ConfigManager,
    
    /// API request
    /// طلب API
    ApiRequest,
    
    /// Manual operation
    /// عملية يدوية
    Manual,
    
    /// System operation
    /// عملية نظام
    System,
    
    /// External source
    /// مصدر خارجي
    External(String),
}

/// Event severity
/// شدة الحدث
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum EventSeverity {
    /// Trace severity
    /// شدة التتبع
    Trace,
    
    /// Debug severity
    /// شدة التصحيح
    Debug,
    
    /// Info severity
    /// شدة المعلومات
    Info,
    
    /// Warn severity
    /// شدة التحذير
    Warn,
    
    /// Error severity
    /// شدة الخطأ
    Error,
    
    /// Critical severity
    /// شدة حرجة
    Critical,
}

/// Configuration update payload
/// حمولة تحديث التكوين
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigUpdatePayload {
    /// Previous configuration
    /// التكوين السابق
    pub previous_config: Option<AgentConfig>,
    
    /// New configuration
    /// التكوين الجديد
    pub new_config: AgentConfig,
    
    /// Changed fields
    /// الحقول المتغيرة
    pub changed_fields: Vec<String>,
    
    /// Update reason
    /// سبب التحديث
    pub reason: String,
    
    /// Update source
    /// مصدر التحديث
    pub update_source: String,
}

/// Agent addition payload
/// حمولة إضافة الوكيل
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentAdditionPayload {
    /// Added agent configuration
    /// تكوين الوكيل المضاف
    pub agent_config: AgentConfig,
    
    /// Addition reason
    /// سبب الإضافة
    pub reason: String,
    
    /// Addition source
    /// مصدر الإضافة
    pub addition_source: String,
}

/// Agent removal payload
/// حمولة إزالة الوكيل
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentRemovalPayload {
    /// Removed agent name
    /// اسم الوكيل المزال
    pub agent_name: String,
    
    /// Previous configuration (if available)
    /// التكوين السابق (إذا كان متاحًا)
    pub previous_config: Option<AgentConfig>,
    
    /// Removal reason
    /// سبب الإزالة
    pub reason: String,
    
    /// Removal source
    /// مصدر الإزالة
    pub removal_source: String,
}

/// Parameter change payload
/// حمولة تغيير المعلمة
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParameterChangePayload {
    /// Agent name
    /// اسم الوكيل
    pub agent_name: String,
    
    /// Changed parameters
    /// المعلمات المتغيرة
    pub changed_params: HashMap<String, ParameterChange>,
    
    /// Change reason
    /// سبب التغيير
    pub reason: String,
    
    /// Change source
    /// مصدر التغيير
    pub change_source: String,
}

/// Parameter change details
/// تفاصيل تغيير المعلمة
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParameterChange {
    /// Previous value
    /// القيمة السابقة
    pub previous_value: Option<serde_json::Value>,
    
    /// New value
    /// القيمة الجديدة
    pub new_value: serde_json::Value,
    
    /// Parameter type
    /// نوع المعلمة
    pub param_type: String,
    
    /// Change timestamp
    /// وقت التغيير
    pub timestamp: DateTime<Utc>,
}

/// Validation failure payload
/// حمولة فشل التحقق
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationFailurePayload {
    /// Configuration that failed validation
    /// التكوين الذي فشل في التحقق
    pub config: AgentConfig,
    
    /// Validation errors
    /// أخطاء التحقق
    pub errors: Vec<String>,
    
    /// Validation warnings
    /// تحذيرات التحقق
    pub warnings: Vec<String>,
    
    /// Validation level
    /// مستوى التحقق
    pub validation_level: String,
}

/// Reload completion payload
/// حمولة إكمال إعادة التحميل
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReloadCompletionPayload {
    /// Reload success
    /// نجح إعادة التحميل
    pub success: bool,
    
    /// Number of agents loaded
    /// عدد الوكلاء المحملين
    pub agents_loaded: usize,
    
    /// Number of agents failed to load
    /// عدد الوكلاء الذين فشلوا في التحميل
    pub agents_failed: usize,
    
    /// Reload duration in milliseconds
    /// مدة إعادة التحميل بالمللي ثانية
    pub reload_duration_ms: u64,
    
    /// File path
    /// مسار الملف
    pub file_path: String,
    
    /// File checksum
    /// المجموع الاختباري للملف
    pub file_checksum: String,
}

impl ConfigEvent {
    /// Create a new configuration event
    /// إنشاء حدث تكوين جديد
    pub fn new(
        event_type: ConfigEventType,
        source: EventSource,
        message: String,
    ) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            event_type,
            timestamp: Utc::now(),
            source,
            agent_name: None,
            data: HashMap::new(),
            severity: EventSeverity::Info,
            message,
            metadata: HashMap::new(),
        }
    }

    /// Create an update config event
    /// إنشاء حدث تحديث التكوين
    pub fn update_config(
        agent_name: String,
        payload: ConfigUpdatePayload,
        source: EventSource,
    ) -> Self {
        let mut event = Self::new(
            ConfigEventType::UpdateConfig,
            source,
            format!("Configuration updated for agent: {}", agent_name),
        );
        
        event.agent_name = Some(agent_name.clone());
        event.data.insert("payload".to_string(), serde_json::to_value(payload).unwrap());
        event.severity = EventSeverity::Info;
        
        event
    }

    /// Create an agent added event
    /// إنشاء حدث إضافة وكيل
    pub fn agent_added(
        agent_name: String,
        payload: AgentAdditionPayload,
        source: EventSource,
    ) -> Self {
        let mut event = Self::new(
            ConfigEventType::AgentAdded,
            source,
            format!("Agent added: {}", agent_name),
        );
        
        event.agent_name = Some(agent_name.clone());
        event.data.insert("payload".to_string(), serde_json::to_value(payload).unwrap());
        event.severity = EventSeverity::Info;
        
        event
    }

    /// Create an agent removed event
    /// إنشاء حدث إزالة وكيل
    pub fn agent_removed(
        agent_name: String,
        payload: AgentRemovalPayload,
        source: EventSource,
    ) -> Self {
        let mut event = Self::new(
            ConfigEventType::AgentRemoved,
            source,
            format!("Agent removed: {}", agent_name),
        );
        
        event.agent_name = Some(agent_name.clone());
        event.data.insert("payload".to_string(), serde_json::to_value(payload).unwrap());
        event.severity = EventSeverity::Warn;
        
        event
    }

    /// Create an agent toggled event
    /// إنشاء حدث تبديل الوكيل
    pub fn agent_toggled(
        agent_name: String,
        enabled: bool,
        source: EventSource,
    ) -> Self {
        let mut event = Self::new(
            ConfigEventType::AgentToggled,
            source,
            format!("Agent {} {}", agent_name, if enabled { "enabled" } else { "disabled" }),
        );
        
        event.agent_name = Some(agent_name.clone());
        event.data.insert("enabled".to_string(), serde_json::Value::Bool(enabled));
        event.severity = EventSeverity::Info;
        
        event
    }

    /// Create a parameter change event
    /// إنشاء حدث تغيير المعلمة
    pub fn params_changed(
        agent_name: String,
        payload: ParameterChangePayload,
        source: EventSource,
    ) -> Self {
        let mut event = Self::new(
            ConfigEventType::AgentParamsChanged,
            source,
            format!("Parameters changed for agent: {}", agent_name),
        );
        
        event.agent_name = Some(agent_name.clone());
        event.data.insert("payload".to_string(), serde_json::to_value(payload).unwrap());
        event.severity = EventSeverity::Info;
        
        event
    }

    /// Create a validation failed event
    /// إنشاء حدث فشل التحقق
    pub fn validation_failed(
        agent_name: String,
        payload: ValidationFailurePayload,
        source: EventSource,
    ) -> Self {
        let mut event = Self::new(
            ConfigEventType::ValidationFailed,
            source,
            format!("Validation failed for agent: {}", agent_name),
        );
        
        event.agent_name = Some(agent_name.clone());
        event.data.insert("payload".to_string(), serde_json::to_value(payload).unwrap());
        event.severity = EventSeverity::Error;
        
        event
    }

    /// Create a reload completed event
    /// إنشاء حدث إكمال إعادة التحميل
    pub fn reload_completed(
        payload: ReloadCompletionPayload,
        source: EventSource,
    ) -> Self {
        let mut event = Self::new(
            ConfigEventType::ReloadCompleted,
            source,
            "Configuration reload completed".to_string(),
        );
        
        event.data.insert("payload".to_string(), serde_json::to_value(payload).unwrap());
        event.severity = if payload.success {
            EventSeverity::Info
        } else {
            EventSeverity::Error
        };
        
        event
    }

    /// Create a reload failed event
    /// إنشاء حدث فشل إعادة التحميل
    pub fn reload_failed(
        error: ConfigError,
        file_path: String,
        source: EventSource,
    ) -> Self {
        let mut event = Self::new(
            ConfigEventType::ReloadFailed,
            source,
            format!("Configuration reload failed: {}", error),
        );
        
        event.data.insert("error".to_string(), serde_json::Value::String(error.to_string()));
        event.data.insert("file_path".to_string(), serde_json::Value::String(file_path));
        event.severity = EventSeverity::Error;
        
        event
    }

    /// Create a hot reload toggled event
    /// إنشاء حدث تبديل إعادة التحميل السريع
    pub fn hot_reload_toggled(
        enabled: bool,
        source: EventSource,
    ) -> Self {
        let mut event = Self::new(
            ConfigEventType::HotReloadToggled,
            source,
            format!("Hot reload {}", if enabled { "enabled" } else { "disabled" }),
        );
        
        event.data.insert("enabled".to_string(), serde_json::Value::Bool(enabled));
        event.severity = EventSeverity::Info;
        
        event
    }

    /// Add metadata to the event
    /// إضافة بيانات وصفية للحدث
    pub fn with_metadata(mut self, key: String, value: serde_json::Value) -> Self {
        self.metadata.insert(key, value);
        self
    }

    /// Set event severity
    /// تعيين شدة الحدث
    pub fn with_severity(mut self, severity: EventSeverity) -> Self {
        self.severity = severity;
        self
    }

    /// Add data to the event
    /// إضافة بيانات للحدث
    pub fn with_data(mut self, key: String, value: serde_json::Value) -> Self {
        self.data.insert(key, value);
        self
    }

    /// Get payload as typed value
    /// الحصول على الحمولة كقيمة موحدة
    pub fn get_payload<T>(&self) -> Option<T>
    where
        T: for<'de> Deserialize<'de>,
    {
        self.data.get("payload").and_then(|value| {
            serde_json::from_value(value.clone()).ok()
        })
    }

    /// Check if event is for a specific agent
    /// التحقق مما إذا كان الحدث لوكيل معين
    pub fn is_for_agent(&self, agent_name: &str) -> bool {
        self.agent_name.as_ref().map_or(false, |name| name == agent_name)
    }

    /// Check if event is of a specific type
    /// التحقق مما إذا كان الحدث من نوع معين
    pub fn is_type(&self, event_type: &ConfigEventType) -> bool {
        &self.event_type == event_type
    }

    /// Check if event has a specific severity or higher
    /// التحقق مما إذا كان الحدث لديه شدة معينة أو أعلى
    pub fn is_severity_or_higher(&self, min_severity: EventSeverity) -> bool {
        self.severity >= min_severity
    }

    /// Get event age in seconds
    /// الحصول على عمر الحدث بالثواني
    pub fn age_seconds(&self) -> i64 {
        let now = Utc::now();
        (now - self.timestamp).num_seconds()
    }

    /// Check if event is recent (within last N seconds)
    /// التحقق مما إذا كان الحدث حديثًا (خلال آخر N ثانية)
    pub fn is_recent(&self, seconds: i64) -> bool {
        self.age_seconds() <= seconds
    }
}

/// Event filter
/// مرشح الأحداث
#[derive(Debug, Clone)]
pub struct EventFilter {
    /// Event types to include
    /// أنواع الأحداث لتضمينها
    pub event_types: Option<Vec<ConfigEventType>>,
    
    /// Agent names to include
    /// أسماء الوكلاء لتضمينها
    pub agent_names: Option<Vec<String>>,
    
    /// Event sources to include
    /// مصادر الأحداث لتضمينها
    pub sources: Option<Vec<EventSource>>,
    
    /// Minimum severity
    /// الحد الأدنى للشدة
    pub min_severity: Option<EventSeverity>,
    
    /// Maximum age in seconds
    /// أقصى عمر بالثواني
    pub max_age_seconds: Option<i64>,
}

impl EventFilter {
    /// Create a new event filter
    /// إنشاء مرشح أحداث جديد
    pub fn new() -> Self {
        Self {
            event_types: None,
            agent_names: None,
            sources: None,
            min_severity: None,
            max_age_seconds: None,
        }
    }

    /// Filter by event types
    /// تصفية حسب أنواع الأحداث
    pub fn with_event_types(mut self, types: Vec<ConfigEventType>) -> Self {
        self.event_types = Some(types);
        self
    }

    /// Filter by agent names
    /// تصفية حسب أسماء الوكلاء
    pub fn with_agent_names(mut self, names: Vec<String>) -> Self {
        self.agent_names = Some(names);
        self
    }

    /// Filter by event sources
    /// تصفية حسب مصادر الأحداث
    pub fn with_sources(mut self, sources: Vec<EventSource>) -> Self {
        self.sources = Some(sources);
        self
    }

    /// Filter by minimum severity
    /// تصفية حسب الحد الأدنى للشدة
    pub fn with_min_severity(mut self, severity: EventSeverity) -> Self {
        self.min_severity = Some(severity);
        self
    }

    /// Filter by maximum age
    /// تصفية حسب أقصى عمر
    pub fn with_max_age(mut self, seconds: i64) -> Self {
        self.max_age_seconds = Some(seconds);
        self
    }

    /// Check if event matches the filter
    /// التحقق مما إذا كان الحدث يطابق المرشح
    pub fn matches(&self, event: &ConfigEvent) -> bool {
        // Check event types
        if let Some(ref types) = self.event_types {
            if !types.contains(&event.event_type) {
                return false;
            }
        }

        // Check agent names
        if let Some(ref names) = self.agent_names {
            if let Some(ref agent_name) = event.agent_name {
                if !names.contains(agent_name) {
                    return false;
                }
            } else {
                return false;
            }
        }

        // Check sources
        if let Some(ref sources) = self.sources {
            if !sources.contains(&event.source) {
                return false;
            }
        }

        // Check severity
        if let Some(ref min_severity) = self.min_severity {
            if event.severity < *min_severity {
                return false;
            }
        }

        // Check age
        if let Some(max_age) = self.max_age_seconds {
            if event.age_seconds() > max_age {
                return false;
            }
        }

        true
    }
}

impl Default for EventFilter {
    fn default() -> Self {
        Self::new()
    }
}

/// Event statistics
/// إحصائيات الأحداث
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventStatistics {
    /// Total events
    /// إجمالي الأحداث
    pub total_events: u64,
    
    /// Events by type
    /// الأحداث حسب النوع
    pub events_by_type: HashMap<ConfigEventType, u64>,
    
    /// Events by severity
    /// الأحداث حسب الشدة
    pub events_by_severity: HashMap<EventSeverity, u64>,
    
    /// Events by source
    /// الأحداث حسب المصدر
    pub events_by_source: HashMap<EventSource, u64>,
    
    /// Events by agent
    /// الأحداث حسب الوكيل
    pub events_by_agent: HashMap<String, u64>,
    
    /// Average events per minute
    /// متوسط الأحداث في الدقيقة
    pub avg_events_per_minute: f64,
    
    /// Peak events per minute
    /// ذروة الأحداث في الدقيقة
    pub peak_events_per_minute: u64,
    
    /// Last event timestamp
    /// وقت آخر حدث
    pub last_event_timestamp: Option<DateTime<Utc>>,
}

impl EventStatistics {
    /// Create new event statistics
    /// إنشاء إحصائيات أحداث جديدة
    pub fn new() -> Self {
        Self {
            total_events: 0,
            events_by_type: HashMap::new(),
            events_by_severity: HashMap::new(),
            events_by_source: HashMap::new(),
            events_by_agent: HashMap::new(),
            avg_events_per_minute: 0.0,
            peak_events_per_minute: 0,
            last_event_timestamp: None,
        }
    }

    /// Update statistics with an event
    /// تحديث الإحصائيات بحدث
    pub fn update(&mut self, event: &ConfigEvent) {
        self.total_events += 1;
        
        // Update by type
        *self.events_by_type.entry(event.event_type.clone()).or_insert(0) += 1;
        
        // Update by severity
        *self.events_by_severity.entry(event.severity.clone()).or_insert(0) += 1;
        
        // Update by source
        *self.events_by_source.entry(event.source.clone()).or_insert(0) += 1;
        
        // Update by agent
        if let Some(ref agent_name) = event.agent_name {
            *self.events_by_agent.entry(agent_name.clone()).or_insert(0) += 1;
        }
        
        // Update last event timestamp
        if self.last_event_timestamp.is_none() || event.timestamp > self.last_event_timestamp.unwrap() {
            self.last_event_timestamp = Some(event.timestamp);
        }
    }

    /// Calculate events per minute
    /// حساب الأحداث في الدقيقة
    pub fn calculate_events_per_minute(&self, time_window_minutes: u64) -> f64 {
        if let Some(last_timestamp) = self.last_event_timestamp {
            let window_start = last_timestamp - chrono::Duration::minutes(time_window_minutes as i64);
            // In a real implementation, we would filter events by timestamp
            // For now, return a simple calculation
            self.total_events as f64 / time_window_minutes as f64
        } else {
            0.0
        }
    }
}

impl Default for EventStatistics {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_event_creation() {
        let event = ConfigEvent::new(
            ConfigEventType::UpdateConfig,
            EventSource::FileWatcher,
            "Test event".to_string(),
        );
        
        assert_eq!(event.event_type, ConfigEventType::UpdateConfig);
        assert_eq!(event.source, EventSource::FileWatcher);
        assert_eq!(event.message, "Test event");
        assert_eq!(event.severity, EventSeverity::Info);
    }

    #[test]
    fn test_agent_specific_events() {
        let agent_name = "TestAgent".to_string();
        let event = ConfigEvent::agent_toggled(
            agent_name.clone(),
            true,
            EventSource::ApiRequest,
        );
        
        assert!(event.is_for_agent(&agent_name));
        assert!(event.is_type(&ConfigEventType::AgentToggled));
        assert_eq!(event.agent_name, Some(agent_name));
    }

    #[test]
    fn test_event_filter() {
        let filter = EventFilter::new()
            .with_event_types(vec![ConfigEventType::UpdateConfig, ConfigEventType::AgentAdded])
            .with_min_severity(EventSeverity::Warn);
        
        let event = ConfigEvent::new(
            ConfigEventType::UpdateConfig,
            EventSource::FileWatcher,
            "Test event".to_string(),
        ).with_severity(EventSeverity::Error);
        
        assert!(filter.matches(&event));
        
        let low_severity_event = ConfigEvent::new(
            ConfigEventType::AgentRemoved,
            EventSource::FileWatcher,
            "Test event".to_string(),
        ).with_severity(EventSeverity::Info);
        
        assert!(!filter.matches(&low_severity_event));
    }

    #[test]
    fn test_event_statistics() {
        let mut stats = EventStatistics::new();
        
        let event = ConfigEvent::new(
            ConfigEventType::UpdateConfig,
            EventSource::FileWatcher,
            "Test event".to_string(),
        );
        
        stats.update(&event);
        
        assert_eq!(stats.total_events, 1);
        assert_eq!(stats.events_by_type.get(&ConfigEventType::UpdateConfig), Some(&1));
        assert_eq!(stats.events_by_source.get(&EventSource::FileWatcher), Some(&1));
    }

    #[test]
    fn test_event_age() {
        let event = ConfigEvent::new(
            ConfigEventType::UpdateConfig,
            EventSource::FileWatcher,
            "Test event".to_string(),
        );
        
        // Event should be recent (age should be < 1 second)
        assert!(event.is_recent(1));
        assert!(event.age_seconds() < 1);
    }

    #[test]
    fn test_event_severity_ordering() {
        assert!(EventSeverity::Trace < EventSeverity::Debug);
        assert!(EventSeverity::Debug < EventSeverity::Info);
        assert!(EventSeverity::Info < EventSeverity::Warn);
        assert!(EventSeverity::Warn < EventSeverity::Error);
        assert!(EventSeverity::Error < EventSeverity::Critical);
    }
}
