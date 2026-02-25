// Copyright (c) 2024 Market Intel Brain Team
// Execution Mode Monitoring and Logging - Phase 21.5 Task B
// مراقبة وتسجيل نمط التنفيذ - المهمة 21.5 ب

use std::sync::Arc;
use std::collections::HashMap;
use tokio::sync::RwLock;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use tracing::{info, warn, error, debug};
use thiserror::Error;

use super::execution_mode::{
    ExecutionMode, ExecutionModeResult, ExecutionModeError, ExecutionContext, RiskLevel
};
use super::safety_manager::{ExecutionModeEvent, SafetyManagerStatistics};
use super::safety_guards::{GuardExecutionRecord, GuardStatistics};

/// Execution Mode Monitor
/// مراقب نمط التنفيذ
pub struct ExecutionModeMonitor {
    /// Monitoring configuration
    /// تكوين المراقبة
    config: MonitorConfig,
    
    /// Event history
    /// سجل الأحداث
    event_history: Arc<RwLock<Vec<ExecutionModeEvent>>>,
    
    /// Metrics collector
    /// جامع المقاييس
    metrics: Arc<RwLock<ExecutionModeMetrics>>,
    
    /// Alert manager
    /// مدير التنبيهات
    alert_manager: Arc<AlertManager>,
}

/// Monitor Configuration
/// تكوين المراقبة
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MonitorConfig {
    /// Enable event logging
    /// تمكين تسجيل الأحداث
    pub enable_event_logging: bool,
    
    /// Enable metrics collection
    /// تمكين جمع المقاييس
    pub enable_metrics_collection: bool,
    
    /// Enable alerting
    /// تمكين التنبيهات
    pub enable_alerting: bool,
    
    /// Maximum event history size
    /// الحد الأقصى لحجم سجل الأحداث
    pub max_event_history: usize,
    
    /// Metrics retention period in hours
    /// فترة احتفاظ المقاييس بالساعات
    pub metrics_retention_hours: u64,
    
    /// Alert thresholds
    /// عتبات التنبيه
    pub alert_thresholds: AlertThresholds,
    
    /// Enable performance monitoring
    /// تمكين مراقبة الأداء
    pub enable_performance_monitoring: bool,
    
    /// Enable security monitoring
    /// تمكين مراقبة الأمان
    pub enable_security_monitoring: bool,
}

/// Alert Thresholds
/// عتبات التنبيه
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertThresholds {
    /// Maximum failed transitions per hour
    /// أقصى عدد الانتقالات الفاشلة بالساعة
    pub max_failed_transitions_per_hour: u32,
    
    /// Maximum emergency stops per hour
    /// أقصى عدد التوقفات الطارئة بالساعة
    pub max_emergency_stops_per_hour: u32,
    
    /// Maximum risk level threshold
    /// عتبة مستوى المخاطر الأقصى
    pub max_risk_level: RiskLevel,
    
    /// Minimum confidence threshold
    /// عتبة الثقة الدنيا
    pub min_confidence_threshold: f64,
    
    /// Maximum response time threshold in milliseconds
    /// عتبة وقت الاستجابة الأقصى بالمللي ثانية
    pub max_response_time_ms: u64,
    
    /// Maximum error rate threshold (0.0 to 1.0)
    /// عتبة معدل الخطأ الأقصى (0.0 إلى 1.0)
    pub max_error_rate: f64,
}

impl Default for AlertThresholds {
    fn default() -> Self {
        Self {
            max_failed_transitions_per_hour: 5,
            max_emergency_stops_per_hour: 2,
            max_risk_level: RiskLevel::High,
            min_confidence_threshold: 0.7,
            max_response_time_ms: 1000,
            max_error_rate: 0.05, // 5%
        }
    }
}

impl Default for MonitorConfig {
    fn default() -> Self {
        Self {
            enable_event_logging: true,
            enable_metrics_collection: true,
            enable_alerting: true,
            max_event_history: 10000,
            metrics_retention_hours: 24,
            alert_thresholds: AlertThresholds::default(),
            enable_performance_monitoring: true,
            enable_security_monitoring: true,
        }
    }
}

/// Execution Mode Metrics
/// مقاييس نمط التنفيذ
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionModeMetrics {
    /// Total transitions
    /// إجمالي الانتقالات
    pub total_transitions: u64,
    
    /// Successful transitions
    /// الانتقالات الناجحة
    pub successful_transitions: u64,
    
    /// Failed transitions
    /// الانتقالات الفاشلة
    pub failed_transitions: u64,
    
    /// Emergency stops
    /// التوقفات الطارئة
    pub emergency_stops: u64,
    
    /// Mode distribution
    /// توزيع الأنماط
    pub mode_distribution: HashMap<ExecutionMode, u64>,
    
    /// Average response time in milliseconds
    /// متوسط وقت الاستجابة بالمللي ثانية
    pub avg_response_time_ms: f64,
    
    /// Error rate (0.0 to 1.0)
    /// معدل الخطأ (0.0 إلى 1.0)
    pub error_rate: f64,
    
    /// Risk level distribution
    /// توزيع مستوى المخاطر
    pub risk_level_distribution: HashMap<RiskLevel, u64>,
    
    /// Performance metrics
    /// مقاييس الأداء
    pub performance_metrics: PerformanceMetrics,
    
    /// Security metrics
    /// مقاييس الأمان
    pub security_metrics: SecurityMetrics,
    
    /// Last updated timestamp
    /// وقت آخر تحديث
    pub last_updated: DateTime<Utc>,
}

/// Performance Metrics
/// مقاييس الأداء
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceMetrics {
    /// Average guard execution time in microseconds
    /// متوسط وقت تنفيذ الحارس بالميكروثانية
    pub avg_guard_execution_time_us: f64,
    
    /// Average mode validation time in microseconds
    /// متوسط وقت التحقق من النمط بالميكروثانية
    pub avg_validation_time_us: f64,
    
    /// Peak concurrent operations
    /// ذروة العمليات المتزامنة
    pub peak_concurrent_operations: u32,
    
    /// Memory usage in bytes
    /// استخدام الذاكرة بالبايت
    pub memory_usage_bytes: u64,
    
    /// CPU usage percentage
    /// نسبة استخدام المعالج
    pub cpu_usage_percent: f64,
    
    /// Network I/O in bytes
    /// إدخال/إخراج الشبكة بالبايت
    pub network_io_bytes: u64,
}

/// Security Metrics
/// مقاييس الأمان
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityMetrics {
    /// Authentication failures
    /// فشل المصادقة
    pub authentication_failures: u64,
    
    /// Authorization failures
    /// فشل التفويض
    pub authorization_failures: u64,
    
    /// MFA challenges
    /// تحديات المصادقة متعددة العوامل
    pub mfa_challenges: u64,
    
    /// Suspicious operations
    /// العمليات المشبوهة
    pub suspicious_operations: u64,
    
    /// Blocked operations
    /// العمليات المحظورة
    pub blocked_operations: u64,
    
    /// Security violations
    /// انتهاكات الأمان
    pub security_violations: u64,
    
    /// Audit log entries
    /// إدخالات سجل المراجعة
    pub audit_log_entries: u64,
}

/// Alert Manager
/// مدير التنبيهات
pub struct AlertManager {
    /// Alert configuration
    /// تكوين التنبيهات
    config: AlertConfig,
    
    /// Active alerts
    /// التنبيهات النشطة
    active_alerts: Arc<RwLock<Vec<Alert>>>,
    
    /// Alert history
    /// سجل التنبيهات
    alert_history: Arc<RwLock<Vec<Alert>>>,
}

/// Alert Configuration
/// تكوين التنبيهات
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertConfig {
    /// Enable email alerts
    /// تمكين التنبيهات البريد الإلكتروني
    pub enable_email_alerts: bool,
    
    /// Enable SMS alerts
    /// تمكين تنبيهات الرسائل النصية
    pub enable_sms_alerts: bool,
    
    /// Enable webhook alerts
    /// تمكين تنبيهات webhook
    pub enable_webhook_alerts: bool,
    
    /// Email recipients
    /// مستلمو البريد الإلكتروني
    pub email_recipients: Vec<String>,
    
    /// SMS recipients
    /// مستلمو الرسائل النصية
    pub sms_recipients: Vec<String>,
    
    /// Webhook URLs
    /// عناوين webhook
    pub webhook_urls: Vec<String>,
    
    /// Alert cooldown period in minutes
    /// فترة تبريد التنبيه بالدقائق
    pub alert_cooldown_minutes: u64,
}

impl Default for AlertConfig {
    fn default() -> Self {
        Self {
            enable_email_alerts: false,
            enable_sms_alerts: false,
            enable_webhook_alerts: false,
            email_recipients: vec![],
            sms_recipients: vec![],
            webhook_urls: vec![],
            alert_cooldown_minutes: 15,
        }
    }
}

/// Alert
/// تنبيه
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Alert {
    /// Alert ID
    /// معرف التنبيه
    pub id: String,
    
    /// Alert type
    /// نوع التنبيه
    pub alert_type: AlertType,
    
    /// Alert severity
    /// شدة التنبيه
    pub severity: AlertSeverity,
    
    /// Alert message
    /// رسالة التنبيه
    pub message: String,
    
    /// Alert timestamp
    /// وقت التنبيه
    pub timestamp: DateTime<Utc>,
    
    /// Source
    /// المصدر
    pub source: String,
    
    /// Alert data
    /// بيانات التنبيه
    pub data: HashMap<String, serde_json::Value>,
    
    /// Acknowledged
    /// تم الاعتراف به
    pub acknowledged: bool,
    
    /// Resolved
    /// تم حله
    pub resolved: bool,
}

/// Alert Type
/// نوع التنبيه
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum AlertType {
    /// Mode transition failure
    /// فشل انتقال النمط
    ModeTransitionFailure,
    
    /// Emergency stop triggered
    /// تشغيل التوقف الطارئ
    EmergencyStopTriggered,
    
    /// High risk operation
    /// عملية عالية المخاطر
    HighRiskOperation,
    
    /// Performance degradation
    /// تدهور الأداء
    PerformanceDegradation,
    
    /// Security violation
    /// انتهاك أمني
    SecurityViolation,
    
    /// Configuration error
    /// خطأ في التكوين
    ConfigurationError,
    
    /// System error
    /// خطأ في النظام
    SystemError,
    
    /// Custom alert
    /// تنبيه مخصص
    Custom(String),
}

/// Alert Severity
/// شدة التنبيه
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum AlertSeverity {
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

/// Execution Mode Monitor Error
/// خطأ مراقب نمط التنفيذ
#[derive(Error, Debug)]
pub enum MonitorError {
    #[error("Configuration error: {0}")]
    ConfigurationError(String),
    
    #[error("Alert sending failed: {0}")]
    AlertSendingFailed(String),
    
    #[error("Metrics collection failed: {0}")]
    MetricsCollectionFailed(String),
    
    #[error("Event logging failed: {0}")]
    EventLoggingFailed(String),
    
    #[error("Data processing error: {0}")]
    DataProcessingError(String),
    
    #[error("Storage error: {0}")]
    StorageError(String),
}

/// Result type for monitor operations
/// نوع النتيجة لعمليات المراقب
pub type MonitorResult<T> = Result<T, MonitorError>;

impl ExecutionModeMonitor {
    /// Create new execution mode monitor
    /// إنشاء مراقب نمط تنفيذ جديد
    pub fn new(config: MonitorConfig) -> Self {
        Self {
            config,
            event_history: Arc::new(RwLock::new(Vec::new())),
            metrics: Arc::new(RwLock::new(ExecutionModeMetrics::default())),
            alert_manager: Arc::new(AlertManager::new(AlertConfig::default())),
        }
    }

    /// Record execution mode event
    /// تسجيل حدث نمط التنفيذ
    pub async fn record_event(&self, event: ExecutionModeEvent) -> MonitorResult<()> {
        if self.config.enable_event_logging {
            info!("Recording execution mode event: {:?}", event.event_type);
            
            // Add to event history
            {
                let mut history = self.event_history.write().await;
                history.push(event.clone());
                
                // Trim history if needed
                if history.len() > self.config.max_event_history {
                    history.drain(0..history.len() - self.config.max_event_history);
                }
            }
            
            // Update metrics
            if self.config.enable_metrics_collection {
                self.update_metrics_for_event(&event).await?;
            }
            
            // Check for alerts
            if self.config.enable_alerting {
                self.check_alert_conditions(&event).await?;
            }
        }
        
        Ok(())
    }

    /// Record guard execution
    /// تسجيل تنفيذ الحارس
    pub async fn record_guard_execution(&self, record: GuardExecutionRecord) -> MonitorResult<()> {
        info!("Recording guard execution for mode: {:?}", record.mode);
        
        // Update metrics
        if self.config.enable_metrics_collection {
            self.update_metrics_for_guard_execution(&record).await?;
        }
        
        // Check for alerts
        if self.config.enable_alerting {
            self.check_guard_execution_alerts(&record).await?;
        }
        
        Ok(())
    }

    /// Update safety manager statistics
    /// تحديث إحصائيات مدير السلامة
    pub async fn update_safety_manager_stats(&self, stats: SafetyManagerStatistics) -> MonitorResult<()> {
        if self.config.enable_metrics_collection {
            let mut metrics = self.metrics.write().await;
            
            // Update mode distribution
            metrics.mode_distribution.insert(stats.current_mode, 1);
            
            // Update last updated timestamp
            metrics.last_updated = Utc::now();
        }
        
        Ok(())
    }

    /// Update guard statistics
    /// تحديث إحصائيات الحراس
    pub async fn update_guard_stats(&self, stats: GuardStatistics) -> MonitorResult<()> {
        if self.config.enable_metrics_collection {
            let mut metrics = self.metrics.write().await;
            
            // Update performance metrics
            metrics.performance_metrics.avg_guard_execution_time_us = stats.average_execution_time_ms * 1000.0;
            
            // Update last updated timestamp
            metrics.last_updated = Utc::now();
        }
        
        Ok(())
    }

    /// Get current metrics
    /// الحصول على المقاييس الحالية
    pub async fn get_metrics(&self) -> ExecutionModeMetrics {
        self.metrics.read().await.clone()
    }

    /// Get event history
    /// الحصول على سجل الأحداث
    pub async fn get_event_history(&self, limit: Option<usize>) -> Vec<ExecutionModeEvent> {
        let history = self.event_history.read().await;
        let limit = limit.unwrap_or(history.len());
        
        history.iter()
            .rev()
            .take(limit)
            .cloned()
            .collect()
    }

    /// Get active alerts
    /// الحصول على التنبيهات النشطة
    pub async fn get_active_alerts(&self) -> Vec<Alert> {
        let alerts = self.alert_manager.active_alerts.read().await;
        alerts.iter().filter(|a| !a.resolved).cloned().collect()
    }

    /// Get alert history
    /// الحصول على سجل التنبيهات
    pub async fn get_alert_history(&self, limit: Option<usize>) -> Vec<Alert> {
        let history = self.alert_manager.alert_history.read().await;
        let limit = limit.unwrap_or(history.len());
        
        history.iter()
            .rev()
            .take(limit)
            .cloned()
            .collect()
    }

    /// Acknowledge alert
    /// الاعتراف بالتنبيه
    pub async fn acknowledge_alert(&self, alert_id: &str) -> MonitorResult<()> {
        let mut alerts = self.alert_manager.active_alerts.write().await;
        
        if let Some(alert) = alerts.iter_mut().find(|a| a.id == alert_id) {
            alert.acknowledged = true;
            info!("Alert acknowledged: {}", alert_id);
            Ok(())
        } else {
            Err(MonitorError::ConfigurationError(format!("Alert not found: {}", alert_id)))
        }
    }

    /// Resolve alert
    /// حل التنبيه
    pub async fn resolve_alert(&self, alert_id: &str) -> MonitorResult<()> {
        let mut active_alerts = self.alert_manager.active_alerts.write().await;
        let mut alert_history = self.alert_manager.alert_history.write().await;
        
        // Find and remove from active alerts
        if let Some(pos) = active_alerts.iter().position(|a| a.id == alert_id) {
            let mut alert = active_alerts.remove(pos);
            alert.resolved = true;
            alert_history.push(alert.clone());
            
            info!("Alert resolved: {}", alert_id);
            Ok(())
        } else {
            Err(MonitorError::ConfigurationError(format!("Alert not found: {}", alert_id)))
        }
    }

    /// Update metrics for event
    /// تحديث المقاييس للحدث
    async fn update_metrics_for_event(&self, event: &ExecutionModeEvent) -> MonitorResult<()> {
        let mut metrics = self.metrics.write().await;
        
        metrics.total_transitions += 1;
        
        match event.event_type {
            super::execution_mode::ExecutionModeEventType::ModeChanged => {
                metrics.successful_transitions += 1;
            }
            super::execution_mode::ExecutionModeEventType::EmergencyStopTriggered => {
                metrics.emergency_stops += 1;
            }
            super::execution_mode::ExecutionModeEventType::SafetyCheckFailed |
            super::execution_mode::ExecutionModeEventType::ValidationFailed => {
                metrics.failed_transitions += 1;
            }
            _ => {}
        }
        
        // Update mode distribution
        *metrics.mode_distribution.entry(event.mode).or_insert(0) += 1;
        
        // Calculate error rate
        if metrics.total_transitions > 0 {
            metrics.error_rate = metrics.failed_transitions as f64 / metrics.total_transitions as f64;
        }
        
        // Update last updated timestamp
        metrics.last_updated = Utc::now();
        
        Ok(())
    }

    /// Update metrics for guard execution
    /// تحديث المقاييس لتنفيذ الحارس
    async fn update_metrics_for_guard_execution(&self, record: &GuardExecutionRecord) -> MonitorResult<()> {
        let mut metrics = self.metrics.write().await;
        
        // Update performance metrics
        if !record.guard_results.is_empty() {
            let total_time_us: u64 = record.guard_results.iter().map(|r| r.execution_time_us).sum();
            let avg_time_us = total_time_us as f64 / record.guard_results.len() as f64;
            metrics.performance_metrics.avg_guard_execution_time_us = avg_time_us;
        }
        
        // Update risk level distribution
        for result in &record.guard_results {
            let risk_level = result.risk_assessment.risk_score;
            let risk_category = if risk_level < 0.33 {
                RiskLevel::Low
            } else if risk_level < 0.66 {
                RiskLevel::Medium
            } else {
                RiskLevel::High
            };
            *metrics.risk_level_distribution.entry(risk_category).or_insert(0) += 1;
        }
        
        // Update last updated timestamp
        metrics.last_updated = Utc::now();
        
        Ok(())
    }

    /// Check alert conditions for event
    /// التحقق من شروط التنبيه للحدث
    async fn check_alert_conditions(&self, event: &ExecutionModeEvent) -> MonitorResult<()> {
        let thresholds = &self.config.alert_thresholds;
        
        // Check for emergency stops
        if matches!(event.event_type, super::execution_mode::ExecutionModeEventType::EmergencyStopTriggered) {
            self.create_alert(
                AlertType::EmergencyStopTriggered,
                AlertSeverity::Critical,
                format!("Emergency stop triggered: {:?}", event.mode),
                "execution_safety".to_string(),
                event.data.clone(),
            ).await?;
        }
        
        // Check for failed transitions
        if matches!(event.event_type, super::execution_mode::ExecutionModeEventType::SafetyCheckFailed) {
            self.create_alert(
                AlertType::ModeTransitionFailure,
                AlertSeverity::High,
                "Safety check failed during mode transition".to_string(),
                "execution_safety".to_string(),
                event.data.clone(),
            ).await?;
        }
        
        // Check for high risk operations
        if event.mode == ExecutionMode::Live && 
           matches!(event.event_type, super::execution_mode::ExecutionModeEventType::ModeChanged) {
            self.create_alert(
                AlertType::HighRiskOperation,
                AlertSeverity::Medium,
                "High risk operation: Live mode activated".to_string(),
                "execution_safety".to_string(),
                event.data.clone(),
            ).await?;
        }
        
        Ok(())
    }

    /// Check alert conditions for guard execution
    /// التحقق من شروط التنبيه لتنفيذ الحارس
    async fn check_guard_execution_alerts(&self, record: &GuardExecutionRecord) -> MonitorResult<()> {
        let thresholds = &self.config.alert_thresholds;
        
        // Check for denied operations
        if matches!(record.overall_decision, super::safety_guards::GuardDecision::Deny) {
            self.create_alert(
                AlertType::SecurityViolation,
                AlertSeverity::High,
                "Operation denied by safety guards".to_string(),
                "safety_guards".to_string(),
                HashMap::new(),
            ).await?;
        }
        
        // Check for slow execution
        if record.total_execution_time_ms > thresholds.max_response_time_ms {
            self.create_alert(
                AlertType::PerformanceDegradation,
                AlertSeverity::Medium,
                format!("Slow guard execution: {}ms", record.total_execution_time_ms),
                "performance".to_string(),
                HashMap::new(),
            ).await?;
        }
        
        Ok(())
    }

    /// Create and send alert
    /// إنشاء وإرسال تنبيه
    async fn create_alert(
        &self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: String,
        source: String,
        data: HashMap<String, serde_json::Value>,
    ) -> MonitorResult<()> {
        let alert = Alert {
            id: uuid::Uuid::new_v4().to_string(),
            alert_type,
            severity,
            message,
            timestamp: Utc::now(),
            source,
            data,
            acknowledged: false,
            resolved: false,
        };
        
        // Add to active alerts
        {
            let mut active_alerts = self.alert_manager.active_alerts.write().await;
            active_alerts.push(alert.clone());
        }
        
        // Add to history
        {
            let mut alert_history = self.alert_manager.alert_history.write().await;
            alert_history.push(alert.clone());
            
            // Trim history if needed
            if alert_history.len() > 1000 {
                alert_history.drain(0..alert_history.len() - 1000);
            }
        }
        
        // Send alert notifications
        self.send_alert_notifications(&alert).await?;
        
        warn!("Alert created: {} - {}", alert.alert_type, alert.message);
        Ok(())
    }

    /// Send alert notifications
    /// إرسال إشعارات التنبيه
    async fn send_alert_notifications(&self, alert: &Alert) -> MonitorResult<()> {
        let config = &self.alert_manager.config;
        
        // Send email alerts
        if config.enable_email_alerts && !config.email_recipients.is_empty() {
            // In a real implementation, this would send actual emails
            debug!("Sending email alert to {} recipients", config.email_recipients.len());
        }
        
        // Send SMS alerts
        if config.enable_sms_alerts && !config.sms_recipients.is_empty() {
            // In a real implementation, this would send actual SMS
            debug!("Sending SMS alert to {} recipients", config.sms_recipients.len());
        }
        
        // Send webhook alerts
        if config.enable_webhook_alerts && !config.webhook_urls.is_empty() {
            // In a real implementation, this would send actual webhooks
            debug!("Sending webhook alert to {} URLs", config.webhook_urls.len());
        }
        
        Ok(())
    }

    /// Clean up old metrics
    /// تنظيف المقاييس القديمة
    pub async fn cleanup_old_metrics(&self) -> MonitorResult<()> {
        let cutoff_time = Utc::now() - chrono::Duration::hours(self.config.metrics_retention_hours as i64);
        
        // Clean up old events
        {
            let mut events = self.event_history.write().await;
            events.retain(|e| e.timestamp > cutoff_time);
        }
        
        // Clean up old alerts
        {
            let mut alerts = self.alert_manager.alert_history.write().await;
            alerts.retain(|a| a.timestamp > cutoff_time);
        }
        
        info!("Cleaned up metrics older than {} hours", self.config.metrics_retention_hours);
        Ok(())
    }

    /// Generate monitoring report
    /// إنشاء تقرير المراقبة
    pub async fn generate_report(&self) -> MonitoringReport {
        let metrics = self.metrics.read().await;
        let active_alerts = self.get_active_alerts().await;
        let recent_events = self.get_event_history(Some(100)).await;
        
        MonitoringReport {
            generated_at: Utc::now(),
            metrics: metrics.clone(),
            active_alerts_count: active_alerts.len(),
            critical_alerts_count: active_alerts.iter().filter(|a| matches!(a.severity, AlertSeverity::Critical)).count(),
            recent_events_count: recent_events.len(),
            system_health: self.calculate_system_health(&metrics),
            recommendations: self.generate_recommendations(&metrics, &active_alerts),
        }
    }

    /// Calculate system health
    /// حساب صحة النظام
    fn calculate_system_health(&self, metrics: &ExecutionModeMetrics) -> SystemHealth {
        let health_score = 1.0 - (metrics.error_rate * 0.5) - (metrics.emergency_stops as f64 * 0.3);
        
        let health_status = if health_score >= 0.9 {
            SystemHealthStatus::Excellent
        } else if health_score >= 0.7 {
            SystemHealthStatus::Good
        } else if health_score >= 0.5 {
            SystemHealthStatus::Fair
        } else {
            SystemHealthStatus::Poor
        };
        
        SystemHealth {
            status: health_status,
            score: health_score,
            issues: self.identify_health_issues(metrics),
        }
    }

    /// Identify health issues
    /// تحديد مشاكل الصحة
    fn identify_health_issues(&self, metrics: &ExecutionModeMetrics) -> Vec<String> {
        let mut issues = Vec::new();
        
        if metrics.error_rate > 0.05 {
            issues.push("High error rate detected".to_string());
        }
        
        if metrics.emergency_stops > 0 {
            issues.push("Emergency stops triggered".to_string());
        }
        
        if metrics.avg_response_time_ms > 1000.0 {
            issues.push("High response time detected".to_string());
        }
        
        if metrics.failed_transitions > metrics.successful_transitions {
            issues.push("More failed than successful transitions".to_string());
        }
        
        issues
    }

    /// Generate recommendations
    /// إنشاء توصيات
    fn generate_recommendations(&self, metrics: &ExecutionModeMetrics, alerts: &[Alert]) -> Vec<String> {
        let mut recommendations = Vec::new();
        
        if metrics.error_rate > 0.05 {
            recommendations.push("Review and fix failed transitions".to_string());
        }
        
        if alerts.iter().any(|a| matches!(a.severity, AlertSeverity::Critical)) {
            recommendations.push("Address critical alerts immediately".to_string());
        }
        
        if metrics.avg_response_time_ms > 500.0 {
            recommendations.push("Optimize system performance".to_string());
        }
        
        if metrics.emergency_stops > 0 {
            recommendations.push("Review emergency stop triggers".to_string());
        }
        
        recommendations
    }
}

impl Default for ExecutionModeMetrics {
    fn default() -> Self {
        Self {
            total_transitions: 0,
            successful_transitions: 0,
            failed_transitions: 0,
            emergency_stops: 0,
            mode_distribution: HashMap::new(),
            avg_response_time_ms: 0.0,
            error_rate: 0.0,
            risk_level_distribution: HashMap::new(),
            performance_metrics: PerformanceMetrics::default(),
            security_metrics: SecurityMetrics::default(),
            last_updated: Utc::now(),
        }
    }
}

impl Default for PerformanceMetrics {
    fn default() -> Self {
        Self {
            avg_guard_execution_time_us: 0.0,
            avg_validation_time_us: 0.0,
            peak_concurrent_operations: 0,
            memory_usage_bytes: 0,
            cpu_usage_percent: 0.0,
            network_io_bytes: 0,
        }
    }
}

impl Default for SecurityMetrics {
    fn default() -> Self {
        Self {
            authentication_failures: 0,
            authorization_failures: 0,
            mfa_challenges: 0,
            suspicious_operations: 0,
            blocked_operations: 0,
            security_violations: 0,
            audit_log_entries: 0,
        }
    }
}

impl AlertManager {
    /// Create new alert manager
    /// إنشاء مدير تنبيهات جديد
    pub fn new(config: AlertConfig) -> Self {
        Self {
            config,
            active_alerts: Arc::new(RwLock::new(Vec::new())),
            alert_history: Arc::new(RwLock::new(Vec::new())),
        }
    }
}

/// Monitoring Report
/// تقرير المراقبة
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MonitoringReport {
    /// Report generation timestamp
    /// وقت إنشاء التقرير
    pub generated_at: DateTime<Utc>,
    
    /// Current metrics
    /// المقاييس الحالية
    pub metrics: ExecutionModeMetrics,
    
    /// Number of active alerts
    /// عدد التنبيهات النشطة
    pub active_alerts_count: usize,
    
    /// Number of critical alerts
    /// عدد التنبيهات الحرجة
    pub critical_alerts_count: usize,
    
    /// Number of recent events
    /// عدد الأحداث الأخيرة
    pub recent_events_count: usize,
    
    /// System health
    /// صحة النظام
    pub system_health: SystemHealth,
    
    /// Recommendations
    /// التوصيات
    pub recommendations: Vec<String>,
}

/// System Health
/// صحة النظام
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemHealth {
    /// Health status
    /// حالة الصحة
    pub status: SystemHealthStatus,
    
    /// Health score (0.0 to 1.0)
    /// درجة الصحة (0.0 إلى 1.0)
    pub score: f64,
    
    /// Identified issues
    /// المشاكل المحددة
    pub issues: Vec<String>,
}

/// System Health Status
/// حالة صحة النظام
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum SystemHealthStatus {
    /// Excellent health
    /// صحة ممتازة
    Excellent,
    
    /// Good health
    /// صحة جيدة
    Good,
    
    /// Fair health
    /// صحة مقبولة
    Fair,
    
    /// Poor health
    /// صحة سيئة
    Poor,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_execution_mode_metrics() {
        let metrics = ExecutionModeMetrics::default();
        assert_eq!(metrics.total_transitions, 0);
        assert_eq!(metrics.successful_transitions, 0);
        assert_eq!(metrics.error_rate, 0.0);
    }

    #[test]
    fn test_alert_creation() {
        let alert = Alert {
            id: "test-alert".to_string(),
            alert_type: AlertType::ModeTransitionFailure,
            severity: AlertSeverity::High,
            message: "Test alert".to_string(),
            timestamp: Utc::now(),
            source: "test".to_string(),
            data: HashMap::new(),
            acknowledged: false,
            resolved: false,
        };
        
        assert_eq!(alert.alert_type, AlertType::ModeTransitionFailure);
        assert_eq!(alert.severity, AlertSeverity::High);
        assert!(!alert.acknowledged);
        assert!(!alert.resolved);
    }

    #[test]
    fn test_alert_severity_ordering() {
        assert!(AlertSeverity::Low < AlertSeverity::Medium);
        assert!(AlertSeverity::Medium < AlertSeverity::High);
        assert!(AlertSeverity::High < AlertSeverity::Critical);
    }

    #[test]
    fn test_system_health_status() {
        assert_eq!(format!("{:?}", SystemHealthStatus::Excellent), "Excellent");
        assert_eq!(format!("{:?}", SystemHealthStatus::Good), "Good");
        assert_eq!(format!("{:?}", SystemHealthStatus::Fair), "Fair");
        assert_eq!(format!("{:?}", SystemHealthStatus::Poor), "Poor");
    }

    #[tokio::test]
    async fn test_execution_mode_monitor() {
        let config = MonitorConfig::default();
        let monitor = ExecutionModeMonitor::new(config);
        
        // Test metrics
        let metrics = monitor.get_metrics().await;
        assert_eq!(metrics.total_transitions, 0);
        
        // Test event history
        let history = monitor.get_event_history(Some(10)).await;
        assert_eq!(history.len(), 0);
        
        // Test alerts
        let alerts = monitor.get_active_alerts().await;
        assert_eq!(alerts.len(), 0);
    }

    #[test]
    fn test_monitor_config() {
        let config = MonitorConfig::default();
        assert!(config.enable_event_logging);
        assert!(config.enable_metrics_collection);
        assert!(config.enable_alerting);
        assert_eq!(config.max_event_history, 10000);
    }

    #[test]
    fn test_alert_thresholds() {
        let thresholds = AlertThresholds::default();
        assert_eq!(thresholds.max_failed_transitions_per_hour, 5);
        assert_eq!(thresholds.max_emergency_stops_per_hour, 2);
        assert_eq!(thresholds.max_risk_level, RiskLevel::High);
    }
}
