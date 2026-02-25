// Copyright (c) 2024 Market Intel Brain Team
// Agent Configuration Types - Phase 21.5 Task C
// أنواع تكوين الوكلاء - المهمة 21.5 ج

use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use thiserror::Error;
use uuid::Uuid;

/// Global agent configuration
/// التكوين العالمي للوكلاء
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GlobalConfig {
    /// Default interval for agents in milliseconds
    /// الفاصل الزمني الافتراضي للوكلاء بالمللي ثانية
    pub default_interval_ms: u64,
    
    /// Maximum number of concurrent agents
    /// الحد الأقصى لعدد الوكلاء المتزامنين
    pub max_concurrent_agents: usize,
    
    /// Global timeout for agent operations in seconds
    /// المهلة العالمية لعمليات الوكلاء بالثواني
    pub operation_timeout_seconds: u64,
    
    /// Enable hot-reload configuration
    /// تمكين إعادة التحميل السريع للتكوين
    pub enable_hot_reload: bool,
    
    /// Configuration validation level
    /// مستوى التحقق من التكوين
    pub validation_level: ValidationLevel,
}

impl Default for GlobalConfig {
    fn default() -> Self {
        Self {
            default_interval_ms: 1000,
            max_concurrent_agents: 100,
            operation_timeout_seconds: 30,
            enable_hot_reload: true,
            validation_level: ValidationLevel::Strict,
        }
    }
}

/// Validation level
/// مستوى التحقق
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ValidationLevel {
    /// No validation
    /// لا تحقق
    None,
    
    /// Basic validation
    /// تحقق أساسي
    Basic,
    
    /// Strict validation
    /// تحقق صارم
    Strict,
    
    /// Comprehensive validation
    /// تحقق شامل
    Comprehensive,
}

/// Agent configuration
/// تكوين الوكيل
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentConfig {
    /// Agent name
    /// اسم الوكيل
    pub name: String,
    
    /// Agent enabled status
    /// حالة تفعيل الوكيل
    pub enabled: bool,
    
    /// Agent execution interval in milliseconds
    /// فاصل تنفيذ الوكيل بالمللي ثانية
    pub interval_ms: u64,
    
    /// Agent description
    /// وصف الوكيل
    pub description: String,
    
    /// Agent version
    /// إصدار الوكيل
    pub version: String,
    
    /// Agent author
    /// مؤلف الوكيل
    pub author: String,
    
    /// Agent-specific parameters
    /// معلمات خاصة بالوكيل
    pub params: HashMap<String, serde_json::Value>,
    
    /// Risk management configuration
    /// تكوين إدارة المخاطر
    pub risk: RiskConfig,
    
    /// Monitoring configuration
    /// تكوين المراقبة
    pub monitoring: MonitoringConfig,
    
    /// Configuration metadata
    /// بيانات وصفية التكوين
    pub metadata: AgentMetadata,
}

/// Risk management configuration
/// تكوين إدارة المخاطر
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskConfig {
    /// Maximum drawdown allowed (0.0 to 1.0)
    /// أقصى انخفاض مسموح به (0.0 إلى 1.0)
    pub max_drawdown: f64,
    
    /// Maximum position value
    /// أقصى قيمة للمركز
    pub max_position_value: f64,
    
    /// Leverage limit
    /// حد الرافعة المالية
    pub leverage_limit: f64,
    
    /// Additional risk parameters
    /// معلمات المخاطر الإضافية
    pub additional_params: HashMap<String, serde_json::Value>,
}

impl Default for RiskConfig {
    fn default() -> Self {
        Self {
            max_drawdown: 0.05,
            max_position_value: 100000.0,
            leverage_limit: 2.0,
            additional_params: HashMap::new(),
        }
    }
}

/// Monitoring configuration
/// تكوين المراقبة
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MonitoringConfig {
    /// Enable metrics collection
    /// تمكين جمع المقاييس
    pub enable_metrics: bool,
    
    /// Log level
    /// مستوى السجل
    pub log_level: LogLevel,
    
    /// Enable performance tracking
    /// تمكين تتبع الأداء
    pub performance_tracking: bool,
    
    /// Additional monitoring parameters
    /// معلمات المراقبة الإضافية
    pub additional_params: HashMap<String, serde_json::Value>,
}

impl Default for MonitoringConfig {
    fn default() -> Self {
        Self {
            enable_metrics: true,
            log_level: LogLevel::Info,
            performance_tracking: true,
            additional_params: HashMap::new(),
        }
    }
}

/// Log level
/// مستوى السجل
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum LogLevel {
    /// Trace level
    /// مستوى التتبع
    Trace,
    
    /// Debug level
    /// مستوى التصحيح
    Debug,
    
    /// Info level
    /// مستوى المعلومات
    Info,
    
    /// Warn level
    /// مستوى التحذير
    Warn,
    
    /// Error level
    /// مستوى الخطأ
    Error,
}

/// Agent metadata
/// بيانات وصفية الوكيل
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentMetadata {
    /// Configuration creation timestamp
    /// وقت إنشاء التكوين
    pub created_at: DateTime<Utc>,
    
    /// Configuration last modified timestamp
    /// وقت آخر تعديل للتكوين
    pub modified_at: DateTime<Utc>,
    
    /// Configuration version
    /// إصدار التكوين
    pub config_version: String,
    
    /// Configuration checksum
    /// المجموع الاختباري للتكوين
    pub checksum: String,
    
    /// Tags
    /// العلامات
    pub tags: Vec<String>,
    
    /// Additional metadata
    /// بيانات وصفية إضافية
    pub additional_metadata: HashMap<String, serde_json::Value>,
}

impl Default for AgentMetadata {
    fn default() -> Self {
        let now = Utc::now();
        Self {
            created_at: now,
            modified_at: now,
            config_version: "1.0.0".to_string(),
            checksum: String::new(),
            tags: Vec::new(),
            additional_metadata: HashMap::new(),
        }
    }
}

/// Complete agent configuration file structure
/// هيكل ملف تكوين الوكلاء الكامل
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentConfigurationFile {
    /// Global configuration
    /// التكوين العالمي
    pub global: GlobalConfig,
    
    /// Agent configurations
    /// تكوينات الوكلاء
    pub agents: Vec<AgentConfig>,
}

impl Default for AgentConfigurationFile {
    fn default() -> Self {
        Self {
            global: GlobalConfig::default(),
            agents: Vec::new(),
        }
    }
}

/// Configuration validation result
/// نتيجة التحقق من التكوين
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigValidationResult {
    /// Validation passed
    /// التحقق نجح
    pub is_valid: bool,
    
    /// Validation errors
    /// أخطاء التحقق
    pub errors: Vec<ValidationError>,
    
    /// Validation warnings
    /// تحذيرات التحقق
    pub warnings: Vec<ValidationWarning>,
    
    /// Validation summary
    /// ملخص التحقق
    pub summary: String,
}

/// Validation error
/// خطأ التحقق
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationError {
    /// Error code
    /// رمز الخطأ
    pub code: String,
    
    /// Error message
    /// رسالة الخطأ
    pub message: String,
    
    /// Field path
    /// مسار الحقل
    pub field_path: String,
    
    /// Error severity
    /// شدة الخطأ
    pub severity: ErrorSeverity,
}

/// Validation warning
/// تحذير التحقق
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationWarning {
    /// Warning code
    /// رمز التحذير
    pub code: String,
    
    /// Warning message
    /// رسالة التحذير
    pub message: String,
    
    /// Field path
    /// مسار الحقل
    pub field_path: String,
    
    /// Recommendation
    /// توصية
    pub recommendation: String,
}

/// Error severity
/// شدة الخطأ
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ErrorSeverity {
    /// Low severity
    /// شدة منخفضة
    Low,
    
    /// Medium severity
    /// شدة متوسطة
    Medium,
    
    /// High severity
    /// شدة عالية
    High,
    
    /// Critical severity
    /// شدة حرجة
    Critical,
}

/// Configuration error
/// خطأ التكوين
#[derive(Error, Debug)]
pub enum ConfigError {
    #[error("File not found: {0}")]
    FileNotFound(String),
    
    #[error("Parse error: {0}")]
    ParseError(String),
    
    #[error("Validation error: {0}")]
    ValidationError(String),
    
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
    
    #[error("Serialization error: {0}")]
    SerializationError(#[from] toml::de::Error),
    
    #[error("Invalid configuration: {0}")]
    InvalidConfiguration(String),
    
    #[error("Duplicate agent name: {0}")]
    DuplicateAgentName(String),
    
    #[error("Invalid agent parameter: {agent}.{param} - {reason}")]
    InvalidParameter { agent: String, param: String, reason: String },
    
    #[error("Risk configuration error: {0}")]
    RiskConfigError(String),
    
    #[error("Monitoring configuration error: {0}")]
    MonitoringConfigError(String),
}

/// Result type for configuration operations
/// نوع النتيجة لعمليات التكوين
pub type ConfigResult<T> = Result<T, ConfigError>;

impl AgentConfig {
    /// Create a new agent configuration
    /// إنشاء تكوين وكيل جديد
    pub fn new(name: String) -> Self {
        let now = Utc::now();
        Self {
            name,
            enabled: false,
            interval_ms: 1000,
            description: String::new(),
            version: "1.0.0".to_string(),
            author: "Market Intel Brain Team".to_string(),
            params: HashMap::new(),
            risk: RiskConfig::default(),
            monitoring: MonitoringConfig::default(),
            metadata: AgentMetadata::default(),
        }
    }

    /// Validate the agent configuration
    /// التحقق من تكوين الوكيل
    pub fn validate(&self, validation_level: ValidationLevel) -> ConfigValidationResult {
        let mut errors = Vec::new();
        let mut warnings = Vec::new();

        // Basic validation
        if self.name.is_empty() {
            errors.push(ValidationError {
                code: "EMPTY_NAME".to_string(),
                message: "Agent name cannot be empty".to_string(),
                field_path: "name".to_string(),
                severity: ErrorSeverity::High,
            });
        }

        if self.interval_ms == 0 {
            errors.push(ValidationError {
                code: "INVALID_INTERVAL".to_string(),
                message: "Interval must be greater than 0".to_string(),
                field_path: "interval_ms".to_string(),
                severity: ErrorSeverity::High,
            });
        }

        if self.interval_ms < 10 {
            warnings.push(ValidationWarning {
                code: "VERY_LOW_INTERVAL".to_string(),
                message: "Very low interval may cause performance issues".to_string(),
                field_path: "interval_ms".to_string(),
                recommendation: "Consider increasing interval to at least 10ms".to_string(),
            });
        }

        // Risk configuration validation
        if self.risk.max_drawdown < 0.0 || self.risk.max_drawdown > 1.0 {
            errors.push(ValidationError {
                code: "INVALID_DRAWDOWN".to_string(),
                message: "Max drawdown must be between 0.0 and 1.0".to_string(),
                field_path: "risk.max_drawdown".to_string(),
                severity: ErrorSeverity::High,
            });
        }

        if self.risk.max_position_value <= 0.0 {
            errors.push(ValidationError {
                code: "INVALID_POSITION_VALUE".to_string(),
                message: "Max position value must be greater than 0".to_string(),
                field_path: "risk.max_position_value".to_string(),
                severity: ErrorSeverity::High,
            });
        }

        if self.risk.leverage_limit <= 0.0 {
            errors.push(ValidationError {
                code: "INVALID_LEVERAGE".to_string(),
                message: "Leverage limit must be greater than 0".to_string(),
                field_path: "risk.leverage_limit".to_string(),
                severity: ErrorSeverity::High,
            });
        }

        // Strict validation
        if validation_level == ValidationLevel::Strict || validation_level == ValidationLevel::Comprehensive {
            if self.description.is_empty() {
                warnings.push(ValidationWarning {
                    code: "EMPTY_DESCRIPTION".to_string(),
                    message: "Agent description is empty".to_string(),
                    field_path: "description".to_string(),
                    recommendation: "Add a meaningful description for better documentation".to_string(),
                });
            }

            if self.version.is_empty() {
                errors.push(ValidationError {
                    code: "EMPTY_VERSION".to_string(),
                    message: "Agent version cannot be empty".to_string(),
                    field_path: "version".to_string(),
                    severity: ErrorSeverity::Medium,
                });
            }

            if self.author.is_empty() {
                warnings.push(ValidationWarning {
                    code: "EMPTY_AUTHOR".to_string(),
                    message: "Agent author is empty".to_string(),
                    field_path: "author".to_string(),
                    recommendation: "Specify the author for better traceability".to_string(),
                });
            }
        }

        // Comprehensive validation
        if validation_level == ValidationLevel::Comprehensive {
            // Validate parameter types
            for (key, value) in &self.params {
                if key.is_empty() {
                    warnings.push(ValidationWarning {
                        code: "EMPTY_PARAM_KEY".to_string(),
                        message: "Parameter key is empty".to_string(),
                        field_path: format!("params.{}", key),
                        recommendation: "Remove empty parameter keys".to_string(),
                    });
                }

                if value.is_null() {
                    warnings.push(ValidationWarning {
                        code: "NULL_PARAM_VALUE".to_string(),
                        message: format!("Parameter '{}' has null value", key),
                        field_path: format!("params.{}", key),
                        recommendation: "Provide a valid value for the parameter".to_string(),
                    });
                }
            }

            // Check for common parameter names
            let common_params = vec!["threshold", "timeout", "retries", "max_size"];
            for common_param in common_params {
                if !self.params.contains_key(common_param) {
                    warnings.push(ValidationWarning {
                        code: "MISSING_COMMON_PARAM".to_string(),
                        message: format!("Missing common parameter: {}", common_param),
                        field_path: "params".to_string(),
                        recommendation: format!("Consider adding '{}' parameter if applicable", common_param),
                    });
                }
            }
        }

        let is_valid = errors.is_empty();
        let summary = if is_valid {
            "Configuration validation passed".to_string()
        } else {
            format!("Configuration validation failed with {} error(s)", errors.len())
        };

        ConfigValidationResult {
            is_valid,
            errors,
            warnings,
            summary,
        }
    }

    /// Calculate configuration checksum
    /// حساب المجموع الاختباري للتكوين
    pub fn calculate_checksum(&self) -> String {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut hasher = DefaultHasher::new();
        self.name.hash(&mut hasher);
        self.enabled.hash(&mut hasher);
        self.interval_ms.hash(&mut hasher);
        self.description.hash(&mut hasher);
        self.version.hash(&mut hasher);
        
        // Hash parameters
        let mut param_keys: Vec<_> = self.params.keys().collect();
        param_keys.sort();
        for key in param_keys {
            key.hash(&mut hasher);
            if let Some(value) = self.params.get(key) {
                value.to_string().hash(&mut hasher);
            }
        }
        
        format!("{:x}", hasher.finish())
    }

    /// Update metadata
    /// تحديث البيانات الوصفية
    pub fn update_metadata(&mut self) {
        let now = Utc::now();
        self.metadata.modified_at = now;
        self.metadata.checksum = self.calculate_checksum();
    }

    /// Get parameter as typed value
    /// الحصول على المعلمة كقيمة موحدة
    pub fn get_param<T>(&self, key: &str) -> Option<T>
    where
        T: for<'de> Deserialize<'de>,
    {
        self.params.get(key).and_then(|value| {
            serde_json::from_value(value.clone()).ok()
        })
    }

    /// Set parameter
    /// تعيين المعلمة
    pub fn set_param<T>(&mut self, key: String, value: T) -> ConfigResult<()>
    where
        T: Serialize,
    {
        let json_value = serde_json::to_value(value)
            .map_err(|e| ConfigError::SerializationError(toml::de::Error::custom(e.to_string())))?;
        
        self.params.insert(key, json_value);
        self.update_metadata();
        Ok(())
    }

    /// Remove parameter
    /// إزالة المعلمة
    pub fn remove_param(&mut self, key: &str) -> Option<serde_json::Value> {
        let removed = self.params.remove(key);
        if removed.is_some() {
            self.update_metadata();
        }
        removed
    }

    /// Check if agent is enabled and configured
    /// التحقق مما إذا كان الوكيل مفعلاً ومكونًا
    pub fn is_active(&self) -> bool {
        self.enabled && !self.name.is_empty() && self.interval_ms > 0
    }

    /// Get effective interval (falls back to global default if invalid)
    /// الحصول على الفاصل الزمني الفعال (يعود إلى الافتراضي العالمي إذا كان غير صالح)
    pub fn effective_interval(&self, global_default: u64) -> u64 {
        if self.interval_ms == 0 {
            global_default
        } else {
            self.interval_ms
        }
    }
}

impl AgentConfigurationFile {
    /// Load configuration from file
    /// تحميل التكوين من الملف
    pub fn load_from_file(file_path: &str) -> ConfigResult<Self> {
        let content = std::fs::read_to_string(file_path)
            .map_err(|e| ConfigError::FileNotFound(format!("Cannot read file {}: {}", file_path, e)))?;
        
        let config: AgentConfigurationFile = toml::from_str(&content)
            .map_err(|e| ConfigError::ParseError(format!("Cannot parse TOML: {}", e)))?;
        
        Ok(config)
    }

    /// Save configuration to file
    /// حفظ التكوين في الملف
    pub fn save_to_file(&self, file_path: &str) -> ConfigResult<()> {
        let content = toml::to_string_pretty(self)
            .map_err(|e| ConfigError::SerializationError(toml::de::Error::custom(e.to_string())))?;
        
        std::fs::write(file_path, content)
            .map_err(ConfigError::IoError)?;
        
        Ok(())
    }

    /// Validate the entire configuration
    /// التحقق من التكوين بأكمله
    pub fn validate(&self) -> ConfigValidationResult {
        let mut all_errors = Vec::new();
        let mut all_warnings = Vec::new();

        // Validate global configuration
        if self.global.max_concurrent_agents == 0 {
            all_errors.push(ValidationError {
                code: "INVALID_MAX_AGENTS".to_string(),
                message: "Max concurrent agents must be greater than 0".to_string(),
                field_path: "global.max_concurrent_agents".to_string(),
                severity: ErrorSeverity::High,
            });
        }

        if self.global.operation_timeout_seconds == 0 {
            all_errors.push(ValidationError {
                code: "INVALID_TIMEOUT".to_string(),
                message: "Operation timeout must be greater than 0".to_string(),
                field_path: "global.operation_timeout_seconds".to_string(),
                severity: ErrorSeverity::High,
            });
        }

        // Check for duplicate agent names
        let mut agent_names = std::collections::HashSet::new();
        for agent in &self.agents {
            if !agent_names.insert(&agent.name) {
                all_errors.push(ValidationError {
                    code: "DUPLICATE_AGENT_NAME".to_string(),
                    message: format!("Duplicate agent name: {}", agent.name),
                    field_path: format!("agents.{}", agent.name),
                    severity: ErrorSeverity::High,
                });
            }
        }

        // Validate each agent
        for agent in &self.agents {
            let validation_result = agent.validate(self.global.validation_level.clone());
            all_errors.extend(validation_result.errors);
            all_warnings.extend(validation_result.warnings);
        }

        let is_valid = all_errors.is_empty();
        let summary = if is_valid {
            format!("Configuration validation passed for {} agent(s)", self.agents.len())
        } else {
            format!("Configuration validation failed with {} error(s) and {} warning(s)", 
                    all_errors.len(), all_warnings.len())
        };

        ConfigValidationResult {
            is_valid,
            errors: all_errors,
            warnings: all_warnings,
            summary,
        }
    }

    /// Get agent by name
    /// الحصول على الوكيل بالاسم
    pub fn get_agent(&self, name: &str) -> Option<&AgentConfig> {
        self.agents.iter().find(|agent| agent.name == name)
    }

    /// Get agent by name (mutable)
    /// الحصول على الوكيل بالاسم (قابل للتعديل)
    pub fn get_agent_mut(&mut self, name: &str) -> Option<&mut AgentConfig> {
        self.agents.iter_mut().find(|agent| agent.name == name)
    }

    /// Add agent configuration
    /// إضافة تكوين الوكيل
    pub fn add_agent(&mut self, agent: AgentConfig) -> ConfigResult<()> {
        // Check for duplicate names
        if self.agents.iter().any(|a| a.name == agent.name) {
            return Err(ConfigError::DuplicateAgentName(agent.name));
        }

        self.agents.push(agent);
        Ok(())
    }

    /// Remove agent configuration
    /// إزالة تكوين الوكيل
    pub fn remove_agent(&mut self, name: &str) -> Option<AgentConfig> {
        let pos = self.agents.iter().position(|agent| agent.name == name)?;
        Some(self.agents.remove(pos))
    }

    /// Get active agents
    /// الحصول على الوكلاء النشطين
    pub fn get_active_agents(&self) -> Vec<&AgentConfig> {
        self.agents.iter().filter(|agent| agent.is_active()).collect()
    }

    /// Get enabled agents
    /// الحصول على الوكلاء المفعليين
    pub fn get_enabled_agents(&self) -> Vec<&AgentConfig> {
        self.agents.iter().filter(|agent| agent.enabled).collect()
    }

    /// Get agent count
    /// الحصول على عدد الوكلاء
    pub fn agent_count(&self) -> usize {
        self.agents.len()
    }

    /// Get active agent count
    /// الحصول على عدد الوكلاء النشطين
    pub fn active_agent_count(&self) -> usize {
        self.agents.iter().filter(|agent| agent.is_active()).count()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_agent_config_creation() {
        let agent = AgentConfig::new("TestAgent".to_string());
        assert_eq!(agent.name, "TestAgent");
        assert!(!agent.enabled);
        assert_eq!(agent.interval_ms, 1000);
    }

    #[test]
    fn test_agent_validation() {
        let mut agent = AgentConfig::new("TestAgent".to_string());
        agent.interval_ms = 0; // Invalid
        
        let result = agent.validate(ValidationLevel::Basic);
        assert!(!result.is_valid);
        assert!(!result.errors.is_empty());
    }

    #[test]
    fn test_config_checksum() {
        let agent = AgentConfig::new("TestAgent".to_string());
        let checksum1 = agent.calculate_checksum();
        let checksum2 = agent.calculate_checksum();
        assert_eq!(checksum1, checksum2);
    }

    #[test]
    fn test_parameter_operations() {
        let mut agent = AgentConfig::new("TestAgent".to_string());
        
        // Set parameter
        agent.set_param("threshold".to_string(), 2.5).unwrap();
        assert!(agent.params.contains_key("threshold"));
        
        // Get parameter
        let threshold: f64 = agent.get_param("threshold").unwrap();
        assert_eq!(threshold, 2.5);
        
        // Remove parameter
        let removed = agent.remove_param("threshold");
        assert!(removed.is_some());
        assert!(!agent.params.contains_key("threshold"));
    }

    #[test]
    fn test_agent_activity() {
        let mut agent = AgentConfig::new("TestAgent".to_string());
        assert!(!agent.is_active());
        
        agent.enabled = true;
        assert!(agent.is_active());
        
        agent.interval_ms = 0;
        assert!(!agent.is_active());
    }

    #[test]
    fn test_effective_interval() {
        let mut agent = AgentConfig::new("TestAgent".to_string());
        agent.interval_ms = 500;
        
        assert_eq!(agent.effective_interval(1000), 500);
        
        agent.interval_ms = 0;
        assert_eq!(agent.effective_interval(1000), 1000);
    }

    #[test]
    fn test_config_file_operations() {
        let mut config = AgentConfigurationFile::default();
        
        let agent = AgentConfig::new("TestAgent".to_string());
        config.add_agent(agent).unwrap();
        
        assert_eq!(config.agent_count(), 1);
        assert_eq!(config.active_agent_count(), 0);
        
        let retrieved = config.get_agent("TestAgent");
        assert!(retrieved.is_some());
        assert_eq!(retrieved.unwrap().name, "TestAgent");
    }

    #[test]
    fn test_validation_levels() {
        let agent = AgentConfig::new("TestAgent".to_string());
        
        let basic_result = agent.validate(ValidationLevel::Basic);
        let strict_result = agent.validate(ValidationLevel::Strict);
        let comprehensive_result = agent.validate(ValidationLevel::Comprehensive);
        
        // Comprehensive should have more warnings than strict
        assert!(comprehensive_result.warnings.len() >= strict_result.warnings.len());
        assert!(strict_result.warnings.len() >= basic_result.warnings.len());
    }
}
