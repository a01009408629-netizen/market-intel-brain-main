// Copyright (c) 2024 Market Intel Brain Team
// Configuration Manager - Phase 21.5 Task C
// مدير التكوين - المهمة 21.5 ج

use std::sync::Arc;
use std::path::Path;
use tokio::sync::{RwLock, broadcast};
use tracing::{info, warn, error, debug};
use thiserror::Error;
use chrono::Utc;

use super::config_types::{
    AgentConfigurationFile, AgentConfig, ConfigError, ConfigResult, 
    GlobalConfig, ValidationLevel
};
use super::config_watcher::{ConfigWatcher, WatcherConfig, ConfigWatcherResult};
use super::events::{ConfigEvent, EventSource, ConfigUpdatePayload, AgentAdditionPayload};

/// Configuration manager error
/// خطأ مدير التكوين
#[derive(Error, Debug)]
pub enum ConfigManagerError {
    #[error("Configuration error: {0}")]
    ConfigError(#[from] ConfigError),
    
    #[error("Watcher error: {0}")]
    WatcherError(#[from] super::config_watcher::ConfigWatcherError),
    
    #[error("Agent not found: {0}")]
    AgentNotFound(String),
    
    #[error("Agent already exists: {0}")]
    AgentAlreadyExists(String),
    
    #[error("Invalid operation: {0}")]
    InvalidOperation(String),
    
    #[error("Configuration locked for updates")]
    ConfigurationLocked,
    
    #[error("Validation failed: {0}")]
    ValidationFailed(String),
    
    #[error("Broadcast error: {0}")]
    BroadcastError(String),
}

/// Result type for config manager operations
/// نوع النتيجة لعمليات مدير التكوين
pub type ConfigManagerResult<T> = Result<T, ConfigManagerError>;

/// Global configuration manager
/// مدير التكوين العالمي
pub struct ConfigManager {
    /// Thread-safe configuration storage
    /// تخزين التكوين الآمن للخيوط
    config: Arc<RwLock<AgentConfigurationFile>>,
    
    /// Configuration watcher
    /// مراقب التكوين
    watcher: Option<ConfigWatcher>,
    
    /// Event broadcaster
    /// بث الأحداث
    event_sender: broadcast::Sender<ConfigEvent>,
    
    /// Manager configuration
    /// تكوين المدير
    manager_config: ManagerConfig,
    
    /// Update lock
    /// قفل التحديث
    update_lock: Arc<RwLock<bool>>,
}

/// Manager configuration
/// تكوين المدير
#[derive(Debug, Clone)]
pub struct ManagerConfig {
    /// Enable hot reload
    /// تمكين إعادة التحميل السريع
    pub enable_hot_reload: bool,
    
    /// Enable configuration validation
    /// تمكين التحقق من التكوين
    pub enable_validation: bool,
    
    /// Validation level
    /// مستوى التحقق
    pub validation_level: ValidationLevel,
    
    /// Enable event broadcasting
    /// تمكين بث الأحداث
    pub enable_event_broadcasting: bool,
    
    /// Enable configuration backup
    /// تمكين النسخ الاحتياطي للتكوين
    pub enable_backup: bool,
    
    /// Maximum number of agents
    /// أقصى عدد من الوكلاء
    pub max_agents: usize,
    
    /// Enable configuration locking
    /// تمكين قفل التكوين
    pub enable_config_locking: bool,
    
    /// Auto-save on changes
    /// الحفظ التلقائي عند التغييرات
    pub auto_save_on_changes: bool,
}

impl Default for ManagerConfig {
    fn default() -> Self {
        Self {
            enable_hot_reload: true,
            enable_validation: true,
            validation_level: ValidationLevel::Strict,
            enable_event_broadcasting: true,
            enable_backup: true,
            max_agents: 1000,
            enable_config_locking: true,
            auto_save_on_changes: true,
        }
    }
}

impl ConfigManager {
    /// Create a new configuration manager
    /// إنشاء مدير تكوين جديد
    pub async fn new<P: AsRef<Path>>(
        config_file_path: P,
        manager_config: ManagerConfig,
    ) -> ConfigManagerResult<(Self, broadcast::Receiver<ConfigEvent>)> {
        let config_file_path = config_file_path.as_ref();
        
        // Load initial configuration
        let initial_config = AgentConfigurationFile::load_from_file(
            config_file_path.to_string_lossy().as_ref()
        )?;
        
        // Validate initial configuration
        if manager_config.enable_validation {
            let validation_result = initial_config.validate();
            if !validation_result.is_valid {
                return Err(ConfigManagerError::ValidationFailed(validation_result.summary));
            }
        }
        
        // Create broadcast channel
        let (event_sender, event_receiver) = broadcast::channel(1000);
        
        let config = Arc::new(RwLock::new(initial_config));
        let update_lock = Arc::new(RwLock::new(false));
        
        let mut manager = Self {
            config,
            watcher: None,
            event_sender,
            manager_config,
            update_lock,
        };
        
        // Initialize watcher if hot reload is enabled
        if manager_config.enable_hot_reload {
            manager.initialize_watcher(config_file_path).await?;
        }
        
        Ok((manager, event_receiver))
    }

    /// Initialize configuration watcher
    /// تهيئة مراقب التكوين
    async fn initialize_watcher<P: AsRef<Path>>(&mut self, config_file_path: P) -> ConfigManagerResult<()> {
        let watcher_config = WatcherConfig {
            enable_file_watching: true,
            polling_interval_seconds: 1,
            debounce_delay_ms: 500,
            max_file_size_bytes: 10 * 1024 * 1024,
            enable_backup: self.manager_config.enable_backup,
            backup_directory: None,
            enable_checksum_verification: true,
            backup_count: 5,
        };
        
        let (watcher, mut watcher_receiver) = ConfigWatcher::new(config_file_path, watcher_config)?;
        
        // Start watcher
        watcher.start().await?;
        
        // Forward watcher events to manager's event channel
        let manager_sender = self.event_sender.clone();
        tokio::spawn(async move {
            while let Ok(event) = watcher_receiver.recv().await {
                if let Err(e) = manager_sender.send(event) {
                    error!("Failed to forward watcher event: {}", e);
                    break;
                }
            }
        });
        
        self.watcher = Some(watcher);
        Ok(())
    }

    /// Get current configuration
    /// الحصول على التكوين الحالي
    pub async fn get_config(&self) -> AgentConfigurationFile {
        self.config.read().await.clone()
    }

    /// Get current configuration (read-only)
    /// الحصول على التكوين الحالي (للقراءة فقط)
    pub async fn read_config(&self) -> tokio::sync::RwLockReadGuard<'_, AgentConfigurationFile> {
        self.config.read().await
    }

    /// Get global configuration
    /// الحصول على التكوين العالمي
    pub async fn get_global_config(&self) -> GlobalConfig {
        self.config.read().await.global.clone()
    }

    /// Get agent configuration by name
    /// الحصول على تكوين الوكيل بالاسم
    pub async fn get_agent(&self, name: &str) -> Option<AgentConfig> {
        self.config.read().await.get_agent(name).cloned()
    }

    /// Get all agent configurations
    /// الحصول على جميع تكوينات الوكلاء
    pub async fn get_all_agents(&self) -> Vec<AgentConfig> {
        self.config.read().await.agents.clone()
    }

    /// Get enabled agents
    /// الحصول على الوكلاء المفعليين
    pub async fn get_enabled_agents(&self) -> Vec<AgentConfig> {
        self.config.read().await.get_enabled_agents().into_iter().cloned().collect()
    }

    /// Get active agents
    /// الحصول على الوكلاء النشطين
    pub async fn get_active_agents(&self) -> Vec<AgentConfig> {
        self.config.read().await.get_active_agents().into_iter().cloned().collect()
    }

    /// Add a new agent configuration
    /// إضافة تكوين وكيل جديد
    pub async fn add_agent(&self, mut agent: AgentConfig) -> ConfigManagerResult<()> {
        // Acquire update lock if enabled
        if self.manager_config.enable_config_locking {
            let mut lock = self.update_lock.write().await;
            if *lock {
                return Err(ConfigManagerError::ConfigurationLocked);
            }
            *lock = true;
            drop(lock);
        }
        
        // Check agent limit
        {
            let config = self.config.read().await;
            if config.agents.len() >= self.manager_config.max_agents {
                return Err(ConfigManagerError::InvalidOperation(
                    format!("Maximum number of agents ({}) reached", self.manager_config.max_agents)
                ));
            }
            
            // Check for duplicate names
            if config.agents.iter().any(|a| a.name == agent.name) {
                return Err(ConfigManagerError::AgentAlreadyExists(agent.name));
            }
        }
        
        // Validate agent configuration
        if self.manager_config.enable_validation {
            let validation_result = agent.validate(self.manager_config.validation_level.clone());
            if !validation_result.is_valid {
                return Err(ConfigManagerError::ValidationFailed(validation_result.summary));
            }
        }
        
        // Update metadata
        agent.update_metadata();
        
        // Add agent to configuration
        {
            let mut config = self.config.write().await;
            config.agents.push(agent.clone());
        }
        
        // Auto-save if enabled
        if self.manager_config.auto_save_on_changes {
            if let Err(e) = self.auto_save().await {
                warn!("Failed to auto-save configuration: {}", e);
            }
        }
        
        // Send event
        if self.manager_config.enable_event_broadcasting {
            let payload = AgentAdditionPayload {
                agent_config: agent.clone(),
                reason: "Manual addition".to_string(),
                addition_source: "config_manager".to_string(),
            };
            
            let event = ConfigEvent::agent_added(
                agent.name.clone(),
                payload,
                EventSource::ConfigManager,
            );
            
            if let Err(e) = self.event_sender.send(event) {
                error!("Failed to send agent added event: {}", e);
            }
        }
        
        // Release update lock
        if self.manager_config.enable_config_locking {
            let mut lock = self.update_lock.write().await;
            *lock = false;
        }
        
        info!("Agent '{}' added successfully", agent.name);
        Ok(())
    }

    /// Update an existing agent configuration
    /// تحديث تكوين وكيل موجود
    pub async fn update_agent(&self, mut agent: AgentConfig, reason: String) -> ConfigManagerResult<()> {
        // Acquire update lock if enabled
        if self.manager_config.enable_config_locking {
            let mut lock = self.update_lock.write().await;
            if *lock {
                return Err(ConfigManagerError::ConfigurationLocked);
            }
            *lock = true;
            drop(lock);
        }
        
        // Get previous configuration
        let previous_config = {
            let config = self.config.read().await;
            config.get_agent(&agent.name)
                .cloned()
                .ok_or_else(|| ConfigManagerError::AgentNotFound(agent.name.clone()))?
        };
        
        // Validate updated configuration
        if self.manager_config.enable_validation {
            let validation_result = agent.validate(self.manager_config.validation_level.clone());
            if !validation_result.is_valid {
                return Err(ConfigManagerError::ValidationFailed(validation_result.summary));
            }
        }
        
        // Update metadata
        agent.update_metadata();
        
        // Update agent in configuration
        {
            let mut config = self.config.write().await;
            if let Some(existing_agent) = config.get_agent_mut(&agent.name) {
                *existing_agent = agent.clone();
            } else {
                return Err(ConfigManagerError::AgentNotFound(agent.name));
            }
        }
        
        // Auto-save if enabled
        if self.manager_config.auto_save_on_changes {
            if let Err(e) = self.auto_save().await {
                warn!("Failed to auto-save configuration: {}", e);
            }
        }
        
        // Send event
        if self.manager_config.enable_event_broadcasting {
            let changed_fields = self.find_changed_fields(&previous_config, &agent);
            let payload = ConfigUpdatePayload {
                previous_config: Some(previous_config),
                new_config: agent.clone(),
                changed_fields,
                reason,
                update_source: "config_manager".to_string(),
            };
            
            let event = ConfigEvent::update_config(
                agent.name.clone(),
                payload,
                EventSource::ConfigManager,
            );
            
            if let Err(e) = self.event_sender.send(event) {
                error!("Failed to send config update event: {}", e);
            }
        }
        
        // Release update lock
        if self.manager_config.enable_config_locking {
            let mut lock = self.update_lock.write().await;
            *lock = false;
        }
        
        info!("Agent '{}' updated successfully", agent.name);
        Ok(())
    }

    /// Remove an agent configuration
    /// إزالة تكوين الوكيل
    pub async fn remove_agent(&self, name: &str, reason: String) -> ConfigManagerResult<()> {
        // Acquire update lock if enabled
        if self.manager_config.enable_config_locking {
            let mut lock = self.update_lock.write().await;
            if *lock {
                return Err(ConfigManagerError::ConfigurationLocked);
            }
            *lock = true;
            drop(lock);
        }
        
        // Get previous configuration
        let previous_config = {
            let config = self.config.read().await;
            config.get_agent(name).cloned()
        };
        
        // Remove agent from configuration
        {
            let mut config = self.config.write().await;
            if config.remove_agent(name).is_none() {
                return Err(ConfigManagerError::AgentNotFound(name.to_string()));
            }
        }
        
        // Auto-save if enabled
        if self.manager_config.auto_save_on_changes {
            if let Err(e) = self.auto_save().await {
                warn!("Failed to auto-save configuration: {}", e);
            }
        }
        
        // Send event
        if self.manager_config.enable_event_broadcasting {
            let payload = super::events::AgentRemovalPayload {
                agent_name: name.to_string(),
                previous_config,
                reason,
                removal_source: "config_manager".to_string(),
            };
            
            let event = ConfigEvent::agent_removed(
                name.to_string(),
                payload,
                EventSource::ConfigManager,
            );
            
            if let Err(e) = self.event_sender.send(event) {
                error!("Failed to send agent removed event: {}", e);
            }
        }
        
        // Release update lock
        if self.manager_config.enable_config_locking {
            let mut lock = self.update_lock.write().await;
            *lock = false;
        }
        
        info!("Agent '{}' removed successfully", name);
        Ok(())
    }

    /// Toggle agent enabled status
    /// تبديل حالة تفعيل الوكيل
    pub async fn toggle_agent(&self, name: &str, enabled: bool) -> ConfigManagerResult<()> {
        let mut agent = self.get_agent(name).await
            .ok_or_else(|| ConfigManagerError::AgentNotFound(name.to_string()))?;
        
        let previous_enabled = agent.enabled;
        agent.enabled = enabled;
        agent.update_metadata();
        
        // Update agent
        self.update_agent(
            agent,
            format!("Toggled enabled from {} to {}", previous_enabled, enabled)
        ).await?;
        
        // Send toggle event
        if self.manager_config.enable_event_broadcasting {
            let event = ConfigEvent::agent_toggled(
                name.to_string(),
                enabled,
                EventSource::ConfigManager,
            );
            
            if let Err(e) = self.event_sender.send(event) {
                error!("Failed to send agent toggled event: {}", e);
            }
        }
        
        info!("Agent '{}' {} successfully", name, if enabled { "enabled" } else { "disabled" });
        Ok(())
    }

    /// Update agent parameters
    /// تحديث معلمات الوكيل
    pub async fn update_agent_params(
        &self,
        name: &str,
        params: std::collections::HashMap<String, serde_json::Value>,
        reason: String,
    ) -> ConfigManagerResult<()> {
        let mut agent = self.get_agent(name).await
            .ok_or_else(|| ConfigManagerError::AgentNotFound(name.to_string()))?;
        
        let previous_params = agent.params.clone();
        agent.params = params;
        agent.update_metadata();
        
        // Update agent
        self.update_agent(agent, reason).await?;
        
        // Send parameter change event
        if self.manager_config.enable_event_broadcasting {
            let changed_params = self.find_changed_params(&previous_params, &self.get_agent(name).await.unwrap().params);
            let payload = super::events::ParameterChangePayload {
                agent_name: name.to_string(),
                changed_params,
                reason: "Parameter update".to_string(),
                change_source: "config_manager".to_string(),
            };
            
            let event = ConfigEvent::params_changed(
                name.to_string(),
                payload,
                EventSource::ConfigManager,
            );
            
            if let Err(e) = self.event_sender.send(event) {
                error!("Failed to send params changed event: {}", e);
            }
        }
        
        info!("Parameters for agent '{}' updated successfully", name);
        Ok(())
    }

    /// Update global configuration
    /// تحديث التكوين العالمي
    pub async fn update_global_config(&self, global_config: GlobalConfig) -> ConfigManagerResult<()> {
        // Acquire update lock if enabled
        if self.manager_config.enable_config_locking {
            let mut lock = self.update_lock.write().await;
            if *lock {
                return Err(ConfigManagerError::ConfigurationLocked);
            }
            *lock = true;
            drop(lock);
        }
        
        let previous_global = {
            let config = self.config.read().await;
            config.global.clone()
        };
        
        // Update global configuration
        {
            let mut config = self.config.write().await;
            config.global = global_config;
        }
        
        // Auto-save if enabled
        if self.manager_config.auto_save_on_changes {
            if let Err(e) = self.auto_save().await {
                warn!("Failed to auto-save configuration: {}", e);
            }
        }
        
        // Send event
        if self.manager_config.enable_event_broadcasting {
            let event = ConfigEvent::new(
                super::events::ConfigEventType::GlobalConfigChanged,
                EventSource::ConfigManager,
                "Global configuration updated".to_string(),
            );
            
            if let Err(e) = self.event_sender.send(event) {
                error!("Failed to send global config changed event: {}", e);
            }
        }
        
        // Release update lock
        if self.manager_config.enable_config_locking {
            let mut lock = self.update_lock.write().await;
            *lock = false;
        }
        
        info!("Global configuration updated successfully");
        Ok(())
    }

    /// Force reload configuration from file
    /// إعادة تحميل التكوين بالقوة من الملف
    pub async fn force_reload(&self) -> ConfigManagerResult<()> {
        if let Some(ref watcher) = self.watcher {
            watcher.force_reload().await?;
            info!("Configuration force reloaded successfully");
            Ok(())
        } else {
            Err(ConfigManagerError::InvalidOperation(
                "Hot reload is not enabled".to_string()
            ))
        }
    }

    /// Save configuration to file
    /// حفظ التكوين في الملف
    pub async fn save_to_file<P: AsRef<Path>>(&self, file_path: P) -> ConfigManagerResult<()> {
        let config = self.config.read().await;
        config.save_to_file(file_path.as_ref().to_string_lossy().as_ref())?;
        info!("Configuration saved to: {:?}", file_path.as_ref());
        Ok(())
    }

    /// Get configuration statistics
    /// الحصول على إحصائيات التكوين
    pub async fn get_statistics(&self) -> ConfigManagerStatistics {
        let config = self.config.read().await;
        let watcher_stats = if let Some(ref watcher) = self.watcher {
            Some(watcher.get_statistics().await)
        } else {
            None
        };
        
        ConfigManagerStatistics {
            total_agents: config.agents.len(),
            enabled_agents: config.get_enabled_agents().len(),
            active_agents: config.get_active_agents().len(),
            global_config: config.global.clone(),
            watcher_statistics: watcher_stats,
            hot_reload_enabled: self.manager_config.enable_hot_reload,
            validation_enabled: self.manager_config.enable_validation,
            event_broadcasting_enabled: self.manager_config.enable_event_broadcasting,
            max_agents: self.manager_config.max_agents,
            config_locked: *self.update_lock.read().await,
        }
    }

    /// Validate current configuration
    /// التحقق من التكوين الحالي
    pub async fn validate_current_config(&self) -> ConfigManagerResult<()> {
        let config = self.config.read().await;
        let validation_result = config.validate();
        
        if !validation_result.is_valid {
            return Err(ConfigManagerError::ValidationFailed(validation_result.summary));
        }
        
        info!("Current configuration validation passed");
        Ok(())
    }

    /// Auto-save configuration
    /// الحفظ التلقائي للتكوين
    async fn auto_save(&self) -> ConfigManagerResult<()> {
        // In a real implementation, this would save to the original file path
        // For now, we'll just log the operation
        debug!("Auto-saving configuration");
        Ok(())
    }

    /// Find changed fields between two agent configurations
    /// العثور على الحقول المتغيرة بين تكويني وكيل
    fn find_changed_fields(&self, previous: &AgentConfig, new: &AgentConfig) -> Vec<String> {
        let mut changed_fields = Vec::new();
        
        if previous.enabled != new.enabled {
            changed_fields.push("enabled".to_string());
        }
        
        if previous.interval_ms != new.interval_ms {
            changed_fields.push("interval_ms".to_string());
        }
        
        if previous.description != new.description {
            changed_fields.push("description".to_string());
        }
        
        if previous.version != new.version {
            changed_fields.push("version".to_string());
        }
        
        if previous.author != new.author {
            changed_fields.push("author".to_string());
        }
        
        if previous.params != new.params {
            changed_fields.push("params".to_string());
        }
        
        if previous.risk != new.risk {
            changed_fields.push("risk".to_string());
        }
        
        if previous.monitoring != new.monitoring {
            changed_fields.push("monitoring".to_string());
        }
        
        changed_fields
    }

    /// Find changed parameters between two parameter maps
    /// العثور على المعلمات المتغيرة بين خريطتي معلمتين
    fn find_changed_params(
        &self,
        previous: &std::collections::HashMap<String, serde_json::Value>,
        new: &std::collections::HashMap<String, serde_json::Value>,
    ) -> std::collections::HashMap<String, super::events::ParameterChange> {
        let mut changed_params = std::collections::HashMap::new();
        
        // Check for modified and new parameters
        for (key, new_value) in new {
            let change = super::events::ParameterChange {
                previous_value: previous.get(key).cloned(),
                new_value: new_value.clone(),
                param_type: self.get_param_type(new_value),
                timestamp: Utc::now(),
            };
            
            if previous.get(key) != Some(new_value) {
                changed_params.insert(key.clone(), change);
            }
        }
        
        // Check for removed parameters
        for key in previous.keys() {
            if !new.contains_key(key) {
                let change = super::events::ParameterChange {
                    previous_value: previous.get(key).cloned(),
                    new_value: serde_json::Value::Null,
                    param_type: "unknown".to_string(),
                    timestamp: Utc::now(),
                };
                
                changed_params.insert(key.clone(), change);
            }
        }
        
        changed_params
    }

    /// Get parameter type from JSON value
    /// الحصول على نوع المعلمة من قيمة JSON
    fn get_param_type(&self, value: &serde_json::Value) -> String {
        match value {
            serde_json::Value::Null => "null".to_string(),
            serde_json::Value::Bool(_) => "boolean".to_string(),
            serde_json::Value::Number(_) => "number".to_string(),
            serde_json::Value::String(_) => "string".to_string(),
            serde_json::Value::Array(_) => "array".to_string(),
            serde_json::Value::Object(_) => "object".to_string(),
        }
    }
}

/// Configuration manager statistics
/// إحصائيات مدير التكوين
#[derive(Debug, Clone)]
pub struct ConfigManagerStatistics {
    /// Total number of agents
    /// إجمالي عدد الوكلاء
    pub total_agents: usize,
    
    /// Number of enabled agents
    /// عدد الوكلاء المفعليين
    pub enabled_agents: usize,
    
    /// Number of active agents
    /// عدد الوكلاء النشطين
    pub active_agents: usize,
    
    /// Global configuration
    /// التكوين العالمي
    pub global_config: GlobalConfig,
    
    /// Watcher statistics
    /// إحصائيات المراقب
    pub watcher_statistics: Option<super::config_watcher::WatcherStatistics>,
    
    /// Hot reload enabled
    /// إعادة التحميل السريع ممكنة
    pub hot_reload_enabled: bool,
    
    /// Validation enabled
    /// التحقق ممكن
    pub validation_enabled: bool,
    
    /// Event broadcasting enabled
    /// بث الأحداث ممكن
    pub event_broadcasting_enabled: bool,
    
    /// Maximum agents
    /// أقصى عدد من الوكلاء
    pub max_agents: usize,
    
    /// Configuration locked
    /// التكوين مقفول
    pub config_locked: bool,
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;
    use std::io::Write;

    #[tokio::test]
    async fn test_config_manager_creation() {
        // Create a temporary config file
        let mut temp_file = NamedTempFile::new().unwrap();
        let config_content = r#"
[global]
default_interval_ms = 1000
max_concurrent_agents = 10

[[agents]]
name = "TestAgent"
enabled = true
interval_ms = 500
description = "Test agent"
version = "1.0.0"
author = "Test Author"

[agents.params]
threshold = 2.5
"#;
        temp_file.write_all(config_content.as_bytes()).unwrap();
        
        // Create config manager
        let manager_config = ManagerConfig::default();
        let (manager, _receiver) = ConfigManager::new(temp_file.path(), manager_config).await.unwrap();
        
        // Test initial state
        let stats = manager.get_statistics().await;
        assert_eq!(stats.total_agents, 1);
        assert_eq!(stats.enabled_agents, 1);
        assert_eq!(stats.active_agents, 1);
        
        // Get agent
        let agent = manager.get_agent("TestAgent").await;
        assert!(agent.is_some());
        assert_eq!(agent.unwrap().name, "TestAgent");
    }

    #[tokio::test]
    async fn test_add_agent() {
        // Create a temporary config file
        let mut temp_file = NamedTempFile::new().unwrap();
        let config_content = r#"
[global]
default_interval_ms = 1000

[[agents]]
name = "ExistingAgent"
enabled = true
interval_ms = 500
"#;
        temp_file.write_all(config_content.as_bytes()).unwrap();
        
        // Create config manager
        let manager_config = ManagerConfig::default();
        let (manager, _receiver) = ConfigManager::new(temp_file.path(), manager_config).await.unwrap();
        
        // Add new agent
        let new_agent = AgentConfig::new("NewAgent".to_string());
        manager.add_agent(new_agent).await.unwrap();
        
        // Verify agent was added
        let stats = manager.get_statistics().await;
        assert_eq!(stats.total_agents, 2);
        
        let agent = manager.get_agent("NewAgent").await;
        assert!(agent.is_some());
    }

    #[tokio::test]
    async fn test_update_agent() {
        // Create a temporary config file
        let mut temp_file = NamedTempFile::new().unwrap();
        let config_content = r#"
[global]
default_interval_ms = 1000

[[agents]]
name = "TestAgent"
enabled = true
interval_ms = 500
description = "Original description"
"#;
        temp_file.write_all(config_content.as_bytes()).unwrap();
        
        // Create config manager
        let manager_config = ManagerConfig::default();
        let (manager, _receiver) = ConfigManager::new(temp_file.path(), manager_config).await.unwrap();
        
        // Update agent
        let mut agent = manager.get_agent("TestAgent").await.unwrap();
        agent.description = "Updated description".to_string();
        manager.update_agent(agent, "Test update".to_string()).await.unwrap();
        
        // Verify agent was updated
        let updated_agent = manager.get_agent("TestAgent").await.unwrap();
        assert_eq!(updated_agent.description, "Updated description");
    }

    #[tokio::test]
    async fn test_remove_agent() {
        // Create a temporary config file
        let mut temp_file = NamedTempFile::new().unwrap();
        let config_content = r#"
[global]
default_interval_ms = 1000

[[agents]]
name = "TestAgent"
enabled = true
interval_ms = 500
"#;
        temp_file.write_all(config_content.as_bytes()).unwrap();
        
        // Create config manager
        let manager_config = ManagerConfig::default();
        let (manager, _receiver) = ConfigManager::new(temp_file.path(), manager_config).await.unwrap();
        
        // Remove agent
        manager.remove_agent("TestAgent", "Test removal".to_string()).await.unwrap();
        
        // Verify agent was removed
        let stats = manager.get_statistics().await;
        assert_eq!(stats.total_agents, 0);
        
        let agent = manager.get_agent("TestAgent").await;
        assert!(agent.is_none());
    }

    #[tokio::test]
    async fn test_toggle_agent() {
        // Create a temporary config file
        let mut temp_file = NamedTempFile::new().unwrap();
        let config_content = r#"
[global]
default_interval_ms = 1000

[[agents]]
name = "TestAgent"
enabled = true
interval_ms = 500
"#;
        temp_file.write_all(config_content.as_bytes()).unwrap();
        
        // Create config manager
        let manager_config = ManagerConfig::default();
        let (manager, _receiver) = ConfigManager::new(temp_file.path(), manager_config).await.unwrap();
        
        // Toggle agent
        manager.toggle_agent("TestAgent", false).await.unwrap();
        
        // Verify agent was toggled
        let agent = manager.get_agent("TestAgent").await.unwrap();
        assert!(!agent.enabled);
        
        // Toggle back
        manager.toggle_agent("TestAgent", true).await.unwrap();
        
        let agent = manager.get_agent("TestAgent").await.unwrap();
        assert!(agent.enabled);
    }

    #[tokio::test]
    async fn test_update_agent_params() {
        // Create a temporary config file
        let mut temp_file = NamedTempFile::new().unwrap();
        let config_content = r#"
[global]
default_interval_ms = 1000

[[agents]]
name = "TestAgent"
enabled = true
interval_ms = 500

[agents.params]
threshold = 2.5
"#;
        temp_file.write_all(config_content.as_bytes()).unwrap();
        
        // Create config manager
        let manager_config = ManagerConfig::default();
        let (manager, _receiver) = ConfigManager::new(temp_file.path(), manager_config).await.unwrap();
        
        // Update parameters
        let mut new_params = std::collections::HashMap::new();
        new_params.insert("threshold".to_string(), serde_json::Value::Number(3.0.into()));
        new_params.insert("new_param".to_string(), serde_json::Value::String("test".to_string()));
        
        manager.update_agent_params("TestAgent", new_params, "Test param update".to_string()).await.unwrap();
        
        // Verify parameters were updated
        let agent = manager.get_agent("TestAgent").await.unwrap();
        assert_eq!(agent.params.get("threshold"), Some(&serde_json::Value::Number(3.0.into())));
        assert_eq!(agent.params.get("new_param"), Some(&serde_json::Value::String("test".to_string())));
    }

    #[test]
    fn test_manager_config() {
        let config = ManagerConfig::default();
        assert!(config.enable_hot_reload);
        assert!(config.enable_validation);
        assert_eq!(config.validation_level, ValidationLevel::Strict);
        assert!(config.enable_event_broadcasting);
        assert!(config.enable_backup);
        assert_eq!(config.max_agents, 1000);
        assert!(config.enable_config_locking);
        assert!(config.auto_save_on_changes);
    }
}
