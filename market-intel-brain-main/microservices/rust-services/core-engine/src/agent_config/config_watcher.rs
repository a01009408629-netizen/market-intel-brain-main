// Copyright (c) 2024 Market Intel Brain Team
// Configuration Watcher - Phase 21.5 Task C
// مراقب التكوين - المهمة 21.5 ج

use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{RwLock, broadcast, mpsc};
use tokio::time::sleep;
use tracing::{info, warn, error, debug};
use notify::{Watcher, RecursiveMode, RecommendedWatcher, Event, EventKind, Config as NotifyConfig};
use notify::event::ModifyKind;
use thiserror::Error;
use chrono::Utc;

use super::config_types::{AgentConfigurationFile, ConfigError, ConfigResult};
use super::events::{ConfigEvent, EventSource, ReloadCompletionPayload, ReloadFailedPayload};

/// Configuration watcher error
/// خطأ مراقب التكوين
#[derive(Error, Debug)]
pub enum ConfigWatcherError {
    #[error("File not found: {0}")]
    FileNotFound(String),
    
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
    
    #[error("Notify error: {0}")]
    NotifyError(#[from] notify::Error),
    
    #[error("Configuration error: {0}")]
    ConfigError(#[from] ConfigError),
    
    #[error("Channel error: {0}")]
    ChannelError(String),
    
    #[error("Watcher already running")]
    WatcherAlreadyRunning,
    
    #[error("Watcher not running")]
    WatcherNotRunning,
    
    #[error("Invalid file path: {0}")]
    InvalidFilePath(String),
}

/// Result type for config watcher operations
/// نوع النتيجة لعمليات مراقب التكوين
pub type ConfigWatcherResult<T> = Result<T, ConfigWatcherError>;

/// Configuration watcher
/// مراقب التكوين
pub struct ConfigWatcher {
    /// File path to watch
    /// مسار الملف للمراقبة
    file_path: PathBuf,
    
    /// Current configuration
    /// التكوين الحالي
    current_config: Arc<RwLock<AgentConfigurationFile>>,
    
    /// Event broadcaster
    /// بث الأحداث
    event_sender: broadcast::Sender<ConfigEvent>,
    
    /// Watcher handle
    /// مقبض المراقب
    watcher_handle: Arc<RwLock<Option<tokio::task::JoinHandle<()>>>>,
    
    /// Configuration
    /// التكوين
    config: WatcherConfig,
    
    /// Statistics
    /// الإحصائيات
    statistics: Arc<RwLock<WatcherStatistics>>,
}

/// Watcher configuration
/// تكوين المراقب
#[derive(Debug, Clone)]
pub struct WatcherConfig {
    /// Enable file watching
    /// تمكين مراقبة الملفات
    pub enable_file_watching: bool,
    
    /// Polling interval in seconds (fallback if file watching fails)
    /// فاصل الاستطلاع بالثواني (الاحتياطي إذا فشلت مراقبة الملفات)
    pub polling_interval_seconds: u64,
    
    /// Debounce delay in milliseconds
    /// تأخير الت debounce بالمللي ثانية
    pub debounce_delay_ms: u64,
    
    /// Maximum file size in bytes
    /// أقصى حجم للملف بالبايت
    pub max_file_size_bytes: usize,
    
    /// Enable backup on change
    /// تمكين النسخ الاحتياطي عند التغيير
    pub enable_backup: bool,
    
    /// Backup directory
    /// دليل النسخ الاحتياطي
    pub backup_directory: Option<PathBuf>,
    
    /// Enable checksum verification
    /// تمكين التحقق من المجموع الاختباري
    pub enable_checksum_verification: bool,
    
    /// Number of backup files to keep
    /// عدد ملفات النسخ الاحتياطي للاحتفاظ بها
    pub backup_count: usize,
}

impl Default for WatcherConfig {
    fn default() -> Self {
        Self {
            enable_file_watching: true,
            polling_interval_seconds: 1,
            debounce_delay_ms: 500,
            max_file_size_bytes: 10 * 1024 * 1024, // 10MB
            enable_backup: true,
            backup_directory: None,
            enable_checksum_verification: true,
            backup_count: 5,
        }
    }
}

/// Watcher statistics
/// إحصائيات المراقب
#[derive(Debug, Clone, Default)]
pub struct WatcherStatistics {
    /// Total file changes detected
    /// إجمالي تغييرات الملفات المكتشفة
    pub total_changes_detected: u64,
    
    /// Successful reloads
    /// عمليات إعادة التحميل الناجحة
    pub successful_reloads: u64,
    
    /// Failed reloads
    /// عمليات إعادة التحميل الفاشلة
    pub failed_reloads: u64,
    
    /// Last reload timestamp
    /// وقت آخر إعادة تحميل
    pub last_reload_timestamp: Option<chrono::DateTime<Utc>>,
    
    /// Average reload time in milliseconds
    /// متوسط وقت إعادة التحميل بالمللي ثانية
    pub avg_reload_time_ms: f64,
    
    /// Current file checksum
    /// المجموع الاختباري الحالي للملف
    pub current_file_checksum: Option<String>,
    
    /// Watcher start timestamp
    /// وقت بدء المراقب
    pub watcher_start_timestamp: Option<chrono::DateTime<Utc>>,
    
    /// Total bytes processed
    /// إجمالي البايتات المعالجة
    pub total_bytes_processed: u64,
}

impl ConfigWatcher {
    /// Create a new configuration watcher
    /// إنشاء مراقب تكوين جديد
    pub fn new<P: AsRef<Path>>(
        file_path: P,
        config: WatcherConfig,
    ) -> ConfigWatcherResult<(Self, broadcast::Receiver<ConfigEvent>)> {
        let file_path = file_path.as_ref().to_path_buf();
        
        // Validate file path
        if !file_path.exists() {
            return Err(ConfigWatcherError::FileNotFound(
                file_path.to_string_lossy().to_string()
            ));
        }
        
        if !file_path.is_file() {
            return Err(ConfigWatcherError::InvalidFilePath(
                file_path.to_string_lossy().to_string()
            ));
        }
        
        // Create broadcast channel
        let (event_sender, event_receiver) = broadcast::channel(1000);
        
        // Load initial configuration
        let initial_config = AgentConfigurationFile::load_from_file(
            file_path.to_string_lossy().as_ref()
        )?;
        
        let current_config = Arc::new(RwLock::new(initial_config));
        
        let watcher = Self {
            file_path,
            current_config,
            event_sender,
            watcher_handle: Arc::new(RwLock::new(None)),
            config,
            statistics: Arc::new(RwLock::new(WatcherStatistics::default())),
        };
        
        Ok((watcher, event_receiver))
    }

    /// Start watching for configuration changes
    /// بدء مراقبة تغييرات التكوين
    pub async fn start(&self) -> ConfigWatcherResult<()> {
        // Check if watcher is already running
        {
            let handle = self.watcher_handle.read().await;
            if handle.is_some() {
                return Err(ConfigWatcherError::WatcherAlreadyRunning);
            }
        }

        info!("Starting configuration watcher for: {:?}", self.file_path);
        
        // Update statistics
        {
            let mut stats = self.statistics.write().await;
            stats.watcher_start_timestamp = Some(Utc::now());
        }
        
        // Load initial configuration and calculate checksum
        self.load_initial_config().await?;
        
        // Start watching
        if self.config.enable_file_watching {
            self.start_file_watcher().await?;
        } else {
            self.start_polling_watcher().await?;
        }
        
        info!("Configuration watcher started successfully");
        Ok(())
    }

    /// Stop watching for configuration changes
    /// إيقاف مراقبة تغييرات التكوين
    pub async fn stop(&self) -> ConfigWatcherResult<()> {
        info!("Stopping configuration watcher");
        
        // Abort the watcher task
        {
            let mut handle = self.watcher_handle.write().await;
            if let Some(task) = handle.take() {
                task.abort();
            }
        }
        
        info!("Configuration watcher stopped");
        Ok(())
    }

    /// Get current configuration
    /// الحصول على التكوين الحالي
    pub async fn get_config(&self) -> AgentConfigurationFile {
        self.current_config.read().await.clone()
    }

    /// Get current configuration (read-only)
    /// الحصول على التكوين الحالي (للقراءة فقط)
    pub async fn read_config(&self) -> std::sync::RwLockReadGuard<'_, AgentConfigurationFile> {
        self.current_config.read().await
    }

    /// Force reload configuration
    /// إعادة تحميل التكوين بالقوة
    pub async fn force_reload(&self) -> ConfigWatcherResult<()> {
        info!("Force reloading configuration");
        self.reload_config().await
    }

    /// Get watcher statistics
    /// الحصول على إحصائيات المراقب
    pub async fn get_statistics(&self) -> WatcherStatistics {
        self.statistics.read().await.clone()
    }

    /// Check if watcher is running
    /// التحقق مما إذا كان المراقب يعمل
    pub async fn is_running(&self) -> bool {
        let handle = self.watcher_handle.read().await;
        handle.is_some()
    }

    /// Get file path
    /// الحصول على مسار الملف
    pub fn file_path(&self) -> &Path {
        &self.file_path
    }

    /// Load initial configuration
    /// تحميل التكوين الأولي
    async fn load_initial_config(&self) -> ConfigWatcherResult<()> {
        let config = AgentConfigurationFile::load_from_file(
            self.file_path.to_string_lossy().as_ref()
        )?;
        
        // Validate configuration
        let validation_result = config.validate();
        if !validation_result.is_valid {
            warn!("Initial configuration validation failed: {}", validation_result.summary);
        }
        
        // Update current configuration
        {
            let mut current_config = self.current_config.write().await;
            *current_config = config;
        }
        
        // Calculate and store checksum
        if self.config.enable_checksum_verification {
            let checksum = self.calculate_file_checksum().await?;
            {
                let mut stats = self.statistics.write().await;
                stats.current_file_checksum = Some(checksum);
            }
        }
        
        info!("Initial configuration loaded successfully");
        Ok(())
    }

    /// Start file watcher using notify crate
    /// بدء مراقب الملفات باستخدام صندوق notify
    async fn start_file_watcher(&self) -> ConfigWatcherResult<()> {
        use std::sync::mpsc as std_mpsc;
        
        let (tx, rx) = std_mpsc::channel::<Event>();
        let file_path = self.file_path.clone();
        let debounce_delay = Duration::from_millis(self.config.debounce_delay_ms);
        
        // Create notify watcher
        let mut watcher = RecommendedWatcher::new(
            move |res: Result<Event, notify::Error>| {
                match res {
                    Ok(event) => {
                        if let Err(e) = tx.send(event) {
                            error!("Failed to send file system event: {}", e);
                        }
                    }
                    Err(e) => {
                        error!("File system watcher error: {}", e);
                    }
                }
            },
            NotifyConfig::default(),
        )?;
        
        // Watch the file
        watcher.watch(&file_path, RecursiveMode::NonRecursive)?;
        
        // Clone necessary data for the task
        let current_config = self.current_config.clone();
        let event_sender = self.event_sender.clone();
        let statistics = self.statistics.clone();
        let config = self.config.clone();
        let file_path_clone = file_path.clone();
        
        // Spawn watcher task
        let task = tokio::spawn(async move {
            let mut last_change_time = None;
            
            while let Ok(event) = rx.recv() {
                debug!("File system event received: {:?}", event);
                
                // Filter for relevant events
                if !self.is_relevant_event(&event) {
                    continue;
                }
                
                let now = std::time::Instant::now();
                
                // Debounce rapid changes
                if let Some(last_time) = last_change_time {
                    if now.duration_since(last_time) < debounce_delay {
                        debug!("Debouncing rapid file changes");
                        continue;
                    }
                }
                
                last_change_time = Some(now);
                
                // Reload configuration
                if let Err(e) = Self::reload_config_internal(
                    &file_path_clone,
                    &current_config,
                    &event_sender,
                    &statistics,
                    &config,
                ).await {
                    error!("Failed to reload configuration: {}", e);
                }
            }
        });
        
        // Store the task handle
        {
            let mut handle = self.watcher_handle.write().await;
            *handle = Some(task);
        }
        
        Ok(())
    }

    /// Start polling watcher (fallback)
    /// بدء المراقب بالاستطلاع (الاحتياطي)
    async fn start_polling_watcher(&self) -> ConfigWatcherResult<()> {
        let file_path = self.file_path.clone();
        let current_config = self.current_config.clone();
        let event_sender = self.event_sender.clone();
        let statistics = self.statistics.clone();
        let config = self.config.clone();
        let polling_interval = Duration::from_secs(config.polling_interval_seconds);
        
        // Spawn polling task
        let task = tokio::spawn(async move {
            let mut last_checksum = None;
            
            loop {
                // Calculate current checksum
                match Self::calculate_file_checksum_internal(&file_path).await {
                    Ok(current_checksum) => {
                        if let Some(ref last) = last_checksum {
                            if current_checksum != *last {
                                debug!("File change detected by polling");
                                
                                if let Err(e) = Self::reload_config_internal(
                                    &file_path,
                                    &current_config,
                                    &event_sender,
                                    &statistics,
                                    &config,
                                ).await {
                                    error!("Failed to reload configuration: {}", e);
                                }
                            }
                        }
                        last_checksum = Some(current_checksum);
                    }
                    Err(e) => {
                        error!("Failed to calculate file checksum: {}", e);
                    }
                }
                
                sleep(polling_interval).await;
            }
        });
        
        // Store the task handle
        {
            let mut handle = self.watcher_handle.write().await;
            *handle = Some(task);
        }
        
        Ok(())
    }

    /// Check if event is relevant for configuration changes
    /// التحقق مما إذا كان الحدث ذا صلة لتغييرات التكوين
    fn is_relevant_event(&self, event: &Event) -> bool {
        match event.kind {
            EventKind::Create(_) => true,
            EventKind::Modify(kind) => {
                matches!(kind, ModifyKind::Data(_) | ModifyKind::Name(_))
            }
            EventKind::Remove(_) => true,
            _ => false,
        }
    }

    /// Reload configuration
    /// إعادة تحميل التكوين
    async fn reload_config(&self) -> ConfigWatcherResult<()> {
        Self::reload_config_internal(
            &self.file_path,
            &self.current_config,
            &self.event_sender,
            &self.statistics,
            &self.config,
        ).await
    }

    /// Internal reload configuration method
    /// طريقة إعادة تحميل التكوين الداخلية
    async fn reload_config_internal(
        file_path: &Path,
        current_config: &Arc<RwLock<AgentConfigurationFile>>,
        event_sender: &broadcast::Sender<ConfigEvent>,
        statistics: &Arc<RwLock<WatcherStatistics>>,
        config: &WatcherConfig,
    ) -> ConfigWatcherResult<()> {
        let start_time = std::time::Instant::now();
        let file_path_str = file_path.to_string_lossy().to_string();
        
        info!("Reloading configuration from: {}", file_path_str);
        
        // Update statistics
        {
            let mut stats = statistics.write().await;
            stats.total_changes_detected += 1;
        }
        
        // Check file size
        let metadata = std::fs::metadata(file_path)?;
        if metadata.len() > config.max_file_size_bytes as u64 {
            return Err(ConfigWatcherError::ConfigError(
                ConfigError::InvalidConfiguration(
                    format!("File size {} exceeds maximum {}", 
                           metadata.len(), config.max_file_size_bytes)
                )
            ));
        }
        
        // Create backup if enabled
        if config.enable_backup {
            if let Err(e) = Self::create_backup(file_path, config).await {
                warn!("Failed to create backup: {}", e);
            }
        }
        
        // Load new configuration
        let new_config = match AgentConfigurationFile::load_from_file(&file_path_str) {
            Ok(config) => config,
            Err(e) => {
                // Send reload failed event
                let event = ConfigEvent::reload_failed(
                    e.clone(),
                    file_path_str.clone(),
                    EventSource::FileWatcher,
                );
                
                if let Err(send_err) = event_sender.send(event) {
                    error!("Failed to send reload failed event: {}", send_err);
                }
                
                // Update statistics
                {
                    let mut stats = statistics.write().await;
                    stats.failed_reloads += 1;
                }
                
                return Err(ConfigWatcherError::ConfigError(e));
            }
        };
        
        // Validate new configuration
        let validation_result = new_config.validate();
        if !validation_result.is_valid {
            warn!("Configuration validation failed: {}", validation_result.summary);
            
            // Send validation failed event
            for agent in &new_config.agents {
                let event = ConfigEvent::validation_failed(
                    agent.name.clone(),
                    super::events::ValidationFailurePayload {
                        config: agent.clone(),
                        errors: validation_result.errors.iter().map(|e| e.message.clone()).collect(),
                        warnings: validation_result.warnings.iter().map(|w| w.message.clone()).collect(),
                        validation_level: "strict".to_string(),
                    },
                    EventSource::FileWatcher,
                );
                
                if let Err(send_err) = event_sender.send(event) {
                    error!("Failed to send validation failed event: {}", send_err);
                }
            }
        }
        
        // Compare with current configuration
        let previous_config = {
            let config_guard = current_config.read().await;
            config_guard.clone()
        };
        
        // Update current configuration
        {
            let mut config_guard = current_config.write().await;
            *config_guard = new_config.clone();
        }
        
        // Calculate checksum
        let checksum = if config.enable_checksum_verification {
            Some(Self::calculate_file_checksum_internal(file_path).await?)
        } else {
            None
        };
        
        // Update statistics
        let reload_duration = start_time.elapsed().as_millis() as u64;
        {
            let mut stats = statistics.write().await;
            stats.successful_reloads += 1;
            stats.last_reload_timestamp = Some(Utc::now());
            stats.current_file_checksum = checksum.clone();
            
            // Update average reload time
            let total_reloads = stats.successful_reloads + stats.failed_reloads;
            if total_reloads > 0 {
                stats.avg_reload_time_ms = 
                    (stats.avg_reload_time_ms * (total_reloads - 1) as f64 + reload_duration as f64) 
                    / total_reloads as f64;
            }
            
            stats.total_bytes_processed += metadata.len();
        }
        
        // Send reload completed event
        let payload = ReloadCompletionPayload {
            success: true,
            agents_loaded: new_config.agents.len(),
            agents_failed: 0,
            reload_duration_ms: reload_duration,
            file_path: file_path_str.clone(),
            file_checksum: checksum.unwrap_or_default(),
        };
        
        let event = ConfigEvent::reload_completed(payload, EventSource::FileWatcher);
        if let Err(send_err) = event_sender.send(event) {
            error!("Failed to send reload completed event: {}", send_err);
        }
        
        // Send configuration update events for changed agents
        Self::send_config_update_events(&previous_config, &new_config, event_sender).await?;
        
        info!("Configuration reloaded successfully in {}ms", reload_duration);
        Ok(())
    }

    /// Send configuration update events
    /// إرسال أحداث تحديث التكوين
    async fn send_config_update_events(
        previous_config: &AgentConfigurationFile,
        new_config: &AgentConfigurationFile,
        event_sender: &broadcast::Sender<ConfigEvent>,
    ) -> ConfigWatcherResult<()> {
        // Create maps of previous agents for easy lookup
        let previous_agents: std::collections::HashMap<String, &super::config_types::AgentConfig> = 
            previous_config.agents.iter().map(|agent| (agent.name.clone(), agent)).collect();
        
        // Check for added agents
        for new_agent in &new_config.agents {
            if !previous_agents.contains_key(&new_agent.name) {
                let payload = super::events::AgentAdditionPayload {
                    agent_config: new_agent.clone(),
                    reason: "Configuration reload".to_string(),
                    addition_source: "file_watcher".to_string(),
                };
                
                let event = ConfigEvent::agent_added(
                    new_agent.name.clone(),
                    payload,
                    EventSource::FileWatcher,
                );
                
                if let Err(send_err) = event_sender.send(event) {
                    error!("Failed to send agent added event: {}", send_err);
                }
            }
        }
        
        // Check for removed agents
        for (agent_name, previous_agent) in &previous_agents {
            if !new_config.agents.iter().any(|agent| agent.name == *agent_name) {
                let payload = super::events::AgentRemovalPayload {
                    agent_name: agent_name.clone(),
                    previous_config: Some(previous_agent.clone()),
                    reason: "Configuration reload".to_string(),
                    removal_source: "file_watcher".to_string(),
                };
                
                let event = ConfigEvent::agent_removed(
                    agent_name.clone(),
                    payload,
                    EventSource::FileWatcher,
                );
                
                if let Err(send_err) = event_sender.send(event) {
                    error!("Failed to send agent removed event: {}", send_err);
                }
            }
        }
        
        // Check for updated agents
        for new_agent in &new_config.agents {
            if let Some(previous_agent) = previous_agents.get(&new_agent.name) {
                if previous_agent != new_agent {
                    let payload = super::events::ConfigUpdatePayload {
                        previous_config: Some(previous_agent.clone()),
                        new_config: new_agent.clone(),
                        changed_fields: Self::find_changed_fields(previous_agent, new_agent),
                        reason: "Configuration reload".to_string(),
                        update_source: "file_watcher".to_string(),
                    };
                    
                    let event = ConfigEvent::update_config(
                        new_agent.name.clone(),
                        payload,
                        EventSource::FileWatcher,
                    );
                    
                    if let Err(send_err) = event_sender.send(event) {
                        error!("Failed to send config update event: {}", send_err);
                    }
                }
            }
        }
        
        Ok(())
    }

    /// Find changed fields between two agent configurations
    /// العثور على الحقول المتغيرة بين تكويني وكيل
    fn find_changed_fields(
        previous: &super::config_types::AgentConfig,
        new: &super::config_types::AgentConfig,
    ) -> Vec<String> {
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
        
        // Compare parameters
        if previous.params != new.params {
            changed_fields.push("params".to_string());
        }
        
        // Compare risk configuration
        if previous.risk != new.risk {
            changed_fields.push("risk".to_string());
        }
        
        // Compare monitoring configuration
        if previous.monitoring != new.monitoring {
            changed_fields.push("monitoring".to_string());
        }
        
        changed_fields
    }

    /// Create backup of configuration file
    /// إنشاء نسخة احتياطية من ملف التكوين
    async fn create_backup(file_path: &Path, config: &WatcherConfig) -> ConfigWatcherResult<()> {
        let backup_dir = if let Some(ref dir) = config.backup_directory {
            dir.clone()
        } else {
            file_path.parent().unwrap_or(Path::new(".")).join("backups")
        };
        
        // Create backup directory if it doesn't exist
        std::fs::create_dir_all(&backup_dir)?;
        
        // Generate backup filename with timestamp
        let timestamp = Utc::now().format("%Y%m%d_%H%M%S");
        let file_name = file_path.file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("config");
        let backup_file_name = format!("{}_{}.toml", file_name, timestamp);
        let backup_path = backup_dir.join(backup_file_name);
        
        // Copy file
        std::fs::copy(file_path, &backup_path)?;
        
        // Clean up old backups
        Self::cleanup_old_backups(&backup_dir, file_name, config.backup_count).await?;
        
        info!("Configuration backup created: {:?}", backup_path);
        Ok(())
    }

    /// Clean up old backup files
    /// تنظيف ملفات النسخ الاحتياطي القديمة
    async fn cleanup_old_backups(
        backup_dir: &Path,
        file_prefix: &str,
        keep_count: usize,
    ) -> ConfigWatcherResult<()> {
        let mut backup_files = Vec::new();
        
        // List backup files
        for entry in std::fs::read_dir(backup_dir)? {
            let entry = entry?;
            let path = entry.path();
            
            if let Some(file_name) = path.file_name().and_then(|n| n.to_str()) {
                if file_name.starts_with(file_prefix) && file_name.ends_with(".toml") {
                    if let Ok(metadata) = entry.metadata() {
                        if let Ok(modified) = metadata.modified() {
                            backup_files.push((path, modified));
                        }
                    }
                }
            }
        }
        
        // Sort by modification time (newest first)
        backup_files.sort_by(|a, b| b.1.cmp(&a.1));
        
        // Remove old backups
        for (path, _) in backup_files.iter().skip(keep_count) {
            if let Err(e) = std::fs::remove_file(path) {
                warn!("Failed to remove old backup file {:?}: {}", path, e);
            }
        }
        
        Ok(())
    }

    /// Calculate file checksum
    /// حساب المجموع الاختباري للملف
    async fn calculate_file_checksum(&self) -> ConfigWatcherResult<String> {
        Self::calculate_file_checksum_internal(&self.file_path).await
    }

    /// Internal checksum calculation
    /// حساب المجموع الاختباري الداخلي
    async fn calculate_file_checksum_internal(file_path: &Path) -> ConfigWatcherResult<String> {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        use std::io::Read;
        
        let mut file = std::fs::File::open(file_path)?;
        let mut hasher = DefaultHasher::new();
        let mut buffer = [0; 8192];
        
        loop {
            let bytes_read = file.read(&mut buffer)?;
            if bytes_read == 0 {
                break;
            }
            hasher.write(&buffer[..bytes_read]);
        }
        
        Ok(format!("{:x}", hasher.finish()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;
    use std::io::Write;
    use tokio::time::timeout;

    #[tokio::test]
    async fn test_config_watcher_creation() {
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
        
        // Create watcher
        let config = WatcherConfig::default();
        let (watcher, _receiver) = ConfigWatcher::new(temp_file.path(), config).unwrap();
        
        // Test initial state
        assert!(!watcher.is_running().await);
        assert_eq!(watcher.file_path(), temp_file.path());
        
        // Get initial config
        let initial_config = watcher.get_config().await;
        assert_eq!(initial_config.agents.len(), 1);
        assert_eq!(initial_config.agents[0].name, "TestAgent");
    }

    #[tokio::test]
    async fn test_config_watcher_start_stop() {
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
        
        // Create watcher with polling (to avoid notify issues in tests)
        let mut config = WatcherConfig::default();
        config.enable_file_watching = false;
        config.polling_interval_seconds = 1;
        
        let (watcher, _receiver) = ConfigWatcher::new(temp_file.path(), config).unwrap();
        
        // Start watcher
        watcher.start().await.unwrap();
        assert!(watcher.is_running().await);
        
        // Stop watcher
        watcher.stop().await.unwrap();
        assert!(!watcher.is_running().await);
    }

    #[tokio::test]
    async fn test_config_reload() {
        // Create a temporary config file
        let mut temp_file = NamedTempFile::new().unwrap();
        let initial_config = r#"
[global]
default_interval_ms = 1000

[[agents]]
name = "TestAgent"
enabled = true
interval_ms = 500
"#;
        temp_file.write_all(initial_config.as_bytes()).unwrap();
        
        let config = WatcherConfig::default();
        let (watcher, mut receiver) = ConfigWatcher::new(temp_file.path(), config).unwrap();
        
        // Start watcher
        watcher.start().await.unwrap();
        
        // Modify the file
        let modified_config = r#"
[global]
default_interval_ms = 1000

[[agents]]
name = "TestAgent"
enabled = true
interval_ms = 1000

[[agents]]
name = "NewAgent"
enabled = false
interval_ms = 2000
"#;
        temp_file.write_all(modified_config.as_bytes()).unwrap();
        
        // Wait for reload event
        let event = timeout(Duration::from_secs(5), receiver.recv()).await.unwrap().unwrap();
        assert!(matches!(event.event_type, super::events::ConfigEventType::ReloadCompleted));
        
        // Check updated config
        let updated_config = watcher.get_config().await;
        assert_eq!(updated_config.agents.len(), 2);
        assert!(updated_config.agents.iter().any(|a| a.name == "NewAgent"));
        
        watcher.stop().await.unwrap();
    }

    #[tokio::test]
    async fn test_watcher_statistics() {
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
        
        let config = WatcherConfig::default();
        let (watcher, _receiver) = ConfigWatcher::new(temp_file.path(), config).unwrap();
        
        // Get initial statistics
        let stats = watcher.get_statistics().await;
        assert_eq!(stats.total_changes_detected, 0);
        assert_eq!(stats.successful_reloads, 0);
        assert_eq!(stats.failed_reloads, 0);
        
        // Force reload
        watcher.force_reload().await.unwrap();
        
        // Check updated statistics
        let stats = watcher.get_statistics().await;
        assert_eq!(stats.successful_reloads, 1);
        assert!(stats.last_reload_timestamp.is_some());
    }

    #[test]
    fn test_watcher_config() {
        let config = WatcherConfig::default();
        assert!(config.enable_file_watching);
        assert_eq!(config.polling_interval_seconds, 1);
        assert_eq!(config.debounce_delay_ms, 500);
        assert_eq!(config.max_file_size_bytes, 10 * 1024 * 1024);
        assert!(config.enable_backup);
        assert!(config.enable_checksum_verification);
        assert_eq!(config.backup_count, 5);
    }

    #[test]
    fn test_watcher_statistics_default() {
        let stats = WatcherStatistics::default();
        assert_eq!(stats.total_changes_detected, 0);
        assert_eq!(stats.successful_reloads, 0);
        assert_eq!(stats.failed_reloads, 0);
        assert!(stats.last_reload_timestamp.is_none());
        assert_eq!(stats.avg_reload_time_ms, 0.0);
        assert!(stats.current_file_checksum.is_none());
        assert!(stats.watcher_start_timestamp.is_none());
        assert_eq!(stats.total_bytes_processed, 0);
    }
}
