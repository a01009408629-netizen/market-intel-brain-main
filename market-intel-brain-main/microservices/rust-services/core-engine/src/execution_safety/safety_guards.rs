// Copyright (c) 2024 Market Intel Brain Team
// Safety Guards for Execution Modes - Phase 21.5 Task B
// حراسات السلامة لأنماط التنفيذ - المهمة 21.5 ب

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

/// Safety Guard Trait
/// واجهة حارس السلامة
pub trait SafetyGuard: Send + Sync {
    /// Guard name
    /// اسم الحارس
    fn name(&self) -> &str;
    
    /// Guard description
    /// وصف الحارس
    fn description(&self) -> &str;
    
    /// Check if the guard allows the operation
    /// التحقق مما إذا كان الحارس يسمح بالعملية
    fn check(&self, mode: ExecutionMode, operation: &Operation) -> GuardResult;
    
    /// Get the execution modes this guard applies to
    /// الحصول على أنماط التنفيذ التي ينطبق عليها هذا الحارس
    fn applies_to_modes(&self) -> Vec<ExecutionMode>;
    
    /// Get the risk level threshold for this guard
    /// الحصول على عتبة مستوى المخاطر لهذا الحارس
    fn risk_threshold(&self) -> RiskLevel;
}

/// Operation Type
/// نوع العملية
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum OperationType {
    /// Trade execution
    /// تنفيذ التداول
    Trade,
    
    /// Order placement
    /// وضع الأمر
    OrderPlacement,
    
    /// Position management
    /// إدارة المركز
    PositionManagement,
    
    /// Risk adjustment
    /// تعديل المخاطر
    RiskAdjustment,
    
    /// Configuration change
    /// تغيير التكوين
    ConfigurationChange,
    
    /// Data access
    /// الوصول إلى البيانات
    DataAccess,
    
    /// System operation
    /// عملية النظام
    SystemOperation,
    
    /// Custom operation
    /// عملية مخصصة
    Custom(String),
}

/// Operation Context
/// سياق العملية
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Operation {
    /// Operation ID
    /// معرف العملية
    pub id: String,
    
    /// Operation type
    /// نوع العملية
    pub operation_type: OperationType,
    
    /// User requesting the operation
    /// المستخدم الذي يطلب العملية
    pub user: String,
    
    /// Operation timestamp
    /// وقت العملية
    pub timestamp: DateTime<Utc>,
    
    /// Operation parameters
    /// معلمات العملية
    pub parameters: HashMap<String, serde_json::Value>,
    
    /// Risk level of the operation
    /// مستوى مخاطر العملية
    pub risk_level: RiskLevel,
    
    /// Additional metadata
    /// بيانات وصفية إضافية
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Guard Result
/// نتيجة الحارس
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GuardResult {
    /// Guard name
    /// اسم الحارس
    pub guard_name: String,
    
    /// Operation allowed
    /// العملية مسموح بها
    pub allowed: bool,
    
    /// Reason for decision
    /// سبب القرار
    pub reason: String,
    
    /// Risk assessment
    /// تقييم المخاطر
    pub risk_assessment: RiskAssessment,
    
    /// Additional recommendations
    /// توصيات إضافية
    pub recommendations: Vec<String>,
    
    /// Execution time in microseconds
    /// وقت التنفيذ بالميكروثانية
    pub execution_time_us: u64,
}

/// Risk Assessment
/// تقييم المخاطر
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskAssessment {
    /// Overall risk score (0.0 to 1.0)
    /// درجة المخاطر الإجمالية (0.0 إلى 1.0)
    pub risk_score: f64,
    
    /// Risk factors identified
    /// عوامل المخاطر المحددة
    pub risk_factors: Vec<RiskFactor>,
    
    /// Mitigation suggestions
    /// اقتراحات التخفيف
    pub mitigation_suggestions: Vec<String>,
    
    /// Confidence level (0.0 to 1.0)
    /// مستوى الثقة (0.0 إلى 1.0)
    pub confidence_level: f64,
}

/// Risk Factor
/// عامل المخاطر
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskFactor {
    /// Factor name
    /// اسم العامل
    pub name: String,
    
    /// Factor description
    /// وصف العامل
    pub description: String,
    
    /// Factor impact (0.0 to 1.0)
    /// تأثير العامل (0.0 إلى 1.0)
    pub impact: f64,
    
    /// Factor category
    /// فئة العامل
    pub category: RiskCategory,
}

/// Risk Category
/// فئة المخاطر
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum RiskCategory {
    /// Financial risk
    /// المخاطر المالية
    Financial,
    
    /// Operational risk
    /// المخاطر التشغيلية
    Operational,
    
    /// Compliance risk
    /// مخاطر الامتثال
    Compliance,
    
    /// Technical risk
    /// المخاطر التقنية
    Technical,
    
    /// Security risk
    /// المخاطر الأمنية
    Security,
    
    /// Market risk
    /// مخاطر السوق
    Market,
}

/// Safety Guard Manager
/// مدير حراس السلامة
pub struct SafetyGuardManager {
    /// Registered guards
    /// الحراس المسجلون
    guards: Arc<RwLock<HashMap<String, Box<dyn SafetyGuard>>>>,
    
    /// Guard execution history
    /// سجل تنفيذ الحراس
    execution_history: Arc<RwLock<Vec<GuardExecutionRecord>>>,
    
    /// Configuration
    /// التكوين
    config: GuardManagerConfig,
}

/// Guard Manager Configuration
/// تكوين مدير الحراس
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GuardManagerConfig {
    /// Enable parallel guard execution
    /// تمكين التنفيذ المتوازي للحراس
    pub enable_parallel_execution: bool,
    
    /// Maximum concurrent guards
    /// أقصى عدد من الحراس المتزامنين
    pub max_concurrent_guards: usize,
    
    /// Guard execution timeout in milliseconds
    /// مهلة تنفيذ الحارس بالمللي ثانية
    pub guard_timeout_ms: u64,
    
    /// Enable guard caching
    /// تمكين تخزين الحراس مؤقتًا
    pub enable_guard_caching: bool,
    
    /// Cache TTL in seconds
    /// TTL التخزين المؤقت بالثواني
    pub cache_ttl_seconds: u64,
    
    /// Enable risk aggregation
    /// تمكين تجميع المخاطر
    pub enable_risk_aggregation: bool,
    
    /// Minimum confidence threshold
    /// عتبة الثقة الدنيا
    pub min_confidence_threshold: f64,
}

impl Default for GuardManagerConfig {
    fn default() -> Self {
        Self {
            enable_parallel_execution: true,
            max_concurrent_guards: 10,
            guard_timeout_ms: 5000,
            enable_guard_caching: true,
            cache_ttl_seconds: 300,
            enable_risk_aggregation: true,
            min_confidence_threshold: 0.7,
        }
    }
}

/// Guard Execution Record
/// سجل تنفيذ الحارس
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GuardExecutionRecord {
    /// Record ID
    /// معرف السجل
    pub id: String,
    
    /// Operation
    /// العملية
    pub operation: Operation,
    
    /// Execution mode
    /// نمط التنفيذ
    pub mode: ExecutionMode,
    
    /// Guard results
    /// نتائج الحراس
    pub guard_results: Vec<GuardResult>,
    
    /// Overall decision
    /// القرار الإجمالي
    pub overall_decision: GuardDecision,
    
    /// Execution timestamp
    /// وقت التنفيذ
    pub timestamp: DateTime<Utc>,
    
    /// Total execution time in milliseconds
    /// إجمالي وقت التنفيذ بالمللي ثانية
    pub total_execution_time_ms: u64,
}

/// Guard Decision
/// قرار الحارس
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum GuardDecision {
    /// Allow operation
    /// السماح بالعملية
    Allow,
    
    /// Deny operation
    /// رفض العملية
    Deny,
    
    /// Require additional approval
    /// تتطلب موافقة إضافية
    RequireApproval,
    
    /// Require manual review
    /// تتطلب مراجعة يدوية
    RequireManualReview,
}

/// Safety Guard Error
/// خطأ حارس السلامة
#[derive(Error, Debug)]
pub enum SafetyGuardError {
    #[error("Guard execution timeout: {0}")]
    GuardTimeout(String),
    
    #[error("Guard not found: {0}")]
    GuardNotFound(String),
    
    #[error("Invalid operation: {0}")]
    InvalidOperation(String),
    
    #[error("Risk assessment failed: {0}")]
    RiskAssessmentFailed(String),
    
    #[error("Configuration error: {0}")]
    ConfigurationError(String),
    
    #[error("Execution error: {0}")]
    ExecutionError(String),
}

/// Result type for safety guard operations
/// نوع النتيجة لعمليات حارس السلامة
pub type SafetyGuardResult<T> = Result<T, SafetyGuardError>;

impl SafetyGuardManager {
    /// Create new safety guard manager
    /// إنشاء مدير حراس سلامة جديد
    pub fn new(config: GuardManagerConfig) -> Self {
        Self {
            guards: Arc::new(RwLock::new(HashMap::new())),
            execution_history: Arc::new(RwLock::new(Vec::new())),
            config,
        }
    }

    /// Register a safety guard
    /// تسجيل حارس سلامة
    pub async fn register_guard(&self, guard: Box<dyn SafetyGuard>) -> SafetyGuardResult<()> {
        let name = guard.name().to_string();
        info!("Registering safety guard: {}", name);
        
        {
            let mut guards = self.guards.write().await;
            guards.insert(name, guard);
        }
        
        Ok(())
    }

    /// Unregister a safety guard
    /// إلغاء تسجيل حارس السلامة
    pub async fn unregister_guard(&self, name: &str) -> SafetyGuardResult<()> {
        info!("Unregistering safety guard: {}", name);
        
        {
            let mut guards = self.guards.write().await;
            guards.remove(name).ok_or_else(|| SafetyGuardError::GuardNotFound(name.to_string()))?;
        }
        
        Ok(())
    }

    /// Get all registered guards
    /// الحصول على جميع الحراس المسجلين
    pub async fn get_guards(&self) -> Vec<String> {
        let guards = self.guards.read().await;
        guards.keys().cloned().collect()
    }

    /// Check operation against all applicable guards
    /// التحقق من العملية مقابل جميع الحراس المطبقين
    pub async fn check_operation(&self, operation: Operation, mode: ExecutionMode) -> SafetyGuardResult<GuardExecutionRecord> {
        let start_time = std::time::Instant::now();
        
        info!("Checking operation {:?} against guards for mode: {:?}", operation.operation_type, mode);
        
        // Get applicable guards
        let applicable_guards = self.get_applicable_guards(mode).await?;
        
        if applicable_guards.is_empty() {
            warn!("No applicable guards found for mode: {:?}", mode);
            return Ok(self.create_empty_record(operation, mode, start_time.elapsed().as_millis() as u64));
        }
        
        // Execute guards
        let guard_results = if self.config.enable_parallel_execution {
            self.execute_guards_parallel(&applicable_guards, &operation, mode).await?
        } else {
            self.execute_guards_sequential(&applicable_guards, &operation, mode).await?
        };
        
        // Make overall decision
        let overall_decision = self.make_decision(&guard_results, &operation, mode).await?;
        
        // Create execution record
        let record = GuardExecutionRecord {
            id: uuid::Uuid::new_v4().to_string(),
            operation: operation.clone(),
            mode,
            guard_results,
            overall_decision,
            timestamp: Utc::now(),
            total_execution_time_ms: start_time.elapsed().as_millis() as u64,
        };
        
        // Store execution record
        self.store_execution_record(record.clone()).await;
        
        info!("Operation check completed: {:?}", overall_decision);
        Ok(record)
    }

    /// Get execution history
    /// الحصول على سجل التنفيذ
    pub async fn get_execution_history(&self, limit: Option<usize>) -> Vec<GuardExecutionRecord> {
        let history = self.execution_history.read().await;
        let limit = limit.unwrap_or(history.len());
        
        history.iter()
            .rev()
            .take(limit)
            .cloned()
            .collect()
    }

    /// Get guard statistics
    /// الحصول على إحصائيات الحراس
    pub async fn get_statistics(&self) -> GuardStatistics {
        let guards = self.guards.read().await;
        let history = self.execution_history.read().await;
        
        let mut guard_usage = HashMap::new();
        let mut decision_counts = HashMap::new();
        
        for record in history.iter() {
            // Count decisions
            *decision_counts.entry(record.overall_decision.clone()).or_insert(0) += 1;
            
            // Count guard usage
            for result in &record.guard_results {
                *guard_usage.entry(result.guard_name.clone()).or_insert(0) += 1;
            }
        }
        
        GuardStatistics {
            total_guards: guards.len(),
            total_executions: history.len(),
            guard_usage,
            decision_counts,
            parallel_execution_enabled: self.config.enable_parallel_execution,
            average_execution_time_ms: self.calculate_average_execution_time(&history),
        }
    }

    /// Get applicable guards for a mode
    /// الحصول على الحراس المطبقين لنمط
    async fn get_applicable_guards(&self, mode: ExecutionMode) -> SafetyGuardResult<Vec<Arc<Box<dyn SafetyGuard>>>> {
        let guards = self.guards.read().await;
        let mut applicable_guards = Vec::new();
        
        for guard in guards.values() {
            if guard.applies_to_modes().contains(&mode) {
                applicable_guards.push(Arc::new(guard.clone()));
            }
        }
        
        Ok(applicable_guards)
    }

    /// Execute guards in parallel
    /// تنفيذ الحراس بشكل متوازٍ
    async fn execute_guards_parallel(
        &self,
        guards: &[Arc<Box<dyn SafetyGuard>>],
        operation: &Operation,
        mode: ExecutionMode,
    ) -> SafetyGuardResult<Vec<GuardResult>> {
        let semaphore = Arc::new(tokio::sync::Semaphore::new(self.config.max_concurrent_guards));
        let mut tasks = Vec::new();
        
        for guard in guards {
            let semaphore = semaphore.clone();
            let operation = operation.clone();
            let mode = mode;
            
            let task = tokio::spawn(async move {
                let _permit = semaphore.acquire().await.unwrap();
                
                let start = std::time::Instant::now();
                let result = guard.check(mode, &operation);
                let execution_time = start.elapsed().as_micros() as u64;
                
                GuardResult {
                    guard_name: guard.name().to_string(),
                    allowed: result.allowed,
                    reason: result.reason,
                    risk_assessment: result.risk_assessment,
                    recommendations: result.recommendations,
                    execution_time_us: execution_time,
                }
            });
            
            tasks.push(task);
        }
        
        // Wait for all tasks to complete
        let mut results = Vec::new();
        for task in tasks {
            match task.await {
                Ok(result) => results.push(result),
                Err(e) => {
                    error!("Guard execution task failed: {}", e);
                    return Err(SafetyGuardError::ExecutionError(e.to_string()));
                }
            }
        }
        
        Ok(results)
    }

    /// Execute guards sequentially
    /// تنفيذ الحراس بشكل تسلسلي
    async fn execute_guards_sequential(
        &self,
        guards: &[Arc<Box<dyn SafetyGuard>>],
        operation: &Operation,
        mode: ExecutionMode,
    ) -> SafetyGuardResult<Vec<GuardResult>> {
        let mut results = Vec::new();
        
        for guard in guards {
            let start = std::time::Instant::now();
            let result = guard.check(mode, operation);
            let execution_time = start.elapsed().as_micros() as u64;
            
            let guard_result = GuardResult {
                guard_name: guard.name().to_string(),
                allowed: result.allowed,
                reason: result.reason,
                risk_assessment: result.risk_assessment,
                recommendations: result.recommendations,
                execution_time_us: execution_time,
            };
            
            results.push(guard_result);
            
            // Early termination if guard denies operation
            if !result.allowed {
                debug!("Guard {} denied operation, stopping further checks", guard.name());
                break;
            }
        }
        
        Ok(results)
    }

    /// Make overall decision based on guard results
    /// اتخاذ القرار الإجمالي بناءً على نتائج الحراس
    async fn make_decision(
        &self,
        guard_results: &[GuardResult],
        operation: &Operation,
        mode: ExecutionMode,
    ) -> SafetyGuardResult<GuardDecision> {
        // If any guard denies, deny the operation
        for result in guard_results {
            if !result.allowed {
                debug!("Operation denied by guard: {}", result.guard_name);
                return Ok(GuardDecision::Deny);
            }
        }
        
        // Aggregate risk assessment
        let aggregated_risk = if self.config.enable_risk_aggregation {
            self.aggregate_risk_assessment(guard_results).await?
        } else {
            RiskAssessment {
                risk_score: 0.0,
                risk_factors: vec![],
                mitigation_suggestions: vec![],
                confidence_level: 1.0,
            }
        };
        
        // Make decision based on risk and confidence
        if aggregated_risk.risk_score > 0.8 || aggregated_risk.confidence_level < self.config.min_confidence_threshold {
            Ok(GuardDecision::RequireManualReview)
        } else if aggregated_risk.risk_score > 0.6 {
            Ok(GuardDecision::RequireApproval)
        } else {
            Ok(GuardDecision::Allow)
        }
    }

    /// Aggregate risk assessment from multiple guards
    /// تجميع تقييم المخاطر من حراس متعددين
    async fn aggregate_risk_assessment(&self, guard_results: &[GuardResult]) -> SafetyGuardResult<RiskAssessment> {
        let mut total_risk_score = 0.0;
        let mut all_risk_factors = Vec::new();
        let mut all_suggestions = Vec::new();
        let mut confidence_sum = 0.0;
        
        for result in guard_results {
            total_risk_score += result.risk_assessment.risk_score;
            all_risk_factors.extend(result.risk_assessment.risk_factors.clone());
            all_suggestions.extend(result.risk_assessment.mitigation_suggestions.clone());
            confidence_sum += result.risk_assessment.confidence_level;
        }
        
        let avg_risk_score = if guard_results.is_empty() {
            0.0
        } else {
            total_risk_score / guard_results.len() as f64
        };
        
        let avg_confidence = if guard_results.is_empty() {
            1.0
        } else {
            confidence_sum / guard_results.len() as f64
        };
        
        Ok(RiskAssessment {
            risk_score: avg_risk_score,
            risk_factors: all_risk_factors,
            mitigation_suggestions: all_suggestions,
            confidence_level: avg_confidence,
        })
    }

    /// Store execution record
    /// تخزين سجل التنفيذ
    async fn store_execution_record(&self, record: GuardExecutionRecord) {
        let mut history = self.execution_history.write().await;
        history.push(record);
        
        // Trim history if needed (keep last 10000 records)
        if history.len() > 10000 {
            history.drain(0..history.len() - 10000);
        }
    }

    /// Create empty execution record
    /// إنشاء سجل تنفيذ فارغ
    fn create_empty_record(&self, operation: Operation, mode: ExecutionMode, execution_time_ms: u64) -> GuardExecutionRecord {
        GuardExecutionRecord {
            id: uuid::Uuid::new_v4().to_string(),
            operation,
            mode,
            guard_results: vec![],
            overall_decision: GuardDecision::Allow, // Default to allow when no guards
            timestamp: Utc::now(),
            total_execution_time_ms: execution_time_ms,
        }
    }

    /// Calculate average execution time
    /// حساب متوسط وقت التنفيذ
    fn calculate_average_execution_time(&self, history: &[GuardExecutionRecord]) -> f64 {
        if history.is_empty() {
            return 0.0;
        }
        
        let total_time: u64 = history.iter().map(|r| r.total_execution_time_ms).sum();
        total_time as f64 / history.len() as f64
    }
}

/// Guard Statistics
/// إحصائيات الحراس
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GuardStatistics {
    /// Total number of guards
    /// إجمالي عدد الحراس
    pub total_guards: usize,
    
    /// Total number of executions
    /// إجمالي عدد عمليات التنفيذ
    pub total_executions: usize,
    
    /// Guard usage counts
    /// عدد استخدامات الحراس
    pub guard_usage: HashMap<String, usize>,
    
    /// Decision counts
    /// عدد القرارات
    pub decision_counts: HashMap<GuardDecision, usize>,
    
    /// Parallel execution enabled
    /// التنفيذ المتوازي ممكن
    pub parallel_execution_enabled: bool,
    
    /// Average execution time in milliseconds
    /// متوسط وقت التنفيذ بالمللي ثانية
    pub average_execution_time_ms: f64,
}

// Default safety guard implementations

/// Live Trading Guard
/// حارس التداول المباشر
pub struct LiveTradingGuard {
    name: String,
    description: String,
}

impl LiveTradingGuard {
    pub fn new() -> Self {
        Self {
            name: "live_trading_guard".to_string(),
            description: "Ensures live trading operations meet safety requirements".to_string(),
        }
    }
}

impl SafetyGuard for LiveTradingGuard {
    fn name(&self) -> &str {
        &self.name
    }

    fn description(&self) -> &str {
        &self.description
    }

    fn check(&self, mode: ExecutionMode, operation: &Operation) -> GuardResult {
        let start = std::time::Instant::now();
        
        let allowed = match (mode, operation.operation_type) {
            (ExecutionMode::Live, OperationType::Trade) => {
                // Additional checks for live trading
                operation.risk_level.value() <= RiskLevel::Medium.value()
            }
            (ExecutionMode::Live, _) => true, // Other operations allowed in live mode
            (ExecutionMode::DryRun, _) => true, // All operations allowed in dry run
            (ExecutionMode::Backtest, _) => true, // All operations allowed in backtest
        };
        
        let reason = if allowed {
            "Operation allowed by live trading guard".to_string()
        } else {
            "Operation denied - risk level too high for live trading".to_string()
        };
        
        let risk_assessment = RiskAssessment {
            risk_score: operation.risk_level.value() as f64 / 3.0,
            risk_factors: vec![
                RiskFactor {
                    name: "operation_risk".to_string(),
                    description: "Risk associated with the operation type".to_string(),
                    impact: operation.risk_level.value() as f64 / 3.0,
                    category: RiskCategory::Financial,
                }
            ],
            mitigation_suggestions: if !allowed {
                vec!["Consider using DryRun mode first".to_string()]
            } else {
                vec![]
            },
            confidence_level: 0.8,
        };
        
        GuardResult {
            guard_name: self.name.clone(),
            allowed,
            reason,
            risk_assessment,
            recommendations: vec![],
            execution_time_us: start.elapsed().as_micros() as u64,
        }
    }

    fn applies_to_modes(&self) -> Vec<ExecutionMode> {
        vec![ExecutionMode::Live, ExecutionMode::DryRun, ExecutionMode::Backtest]
    }

    fn risk_threshold(&self) -> RiskLevel {
        RiskLevel::Medium
    }
}

/// Risk Level Guard
/// حارس مستوى المخاطر
pub struct RiskLevelGuard {
    name: String,
    description: String,
}

impl RiskLevelGuard {
    pub fn new() -> Self {
        Self {
            name: "risk_level_guard".to_string(),
            description: "Validates operation risk levels against mode thresholds".to_string(),
        }
    }
}

impl SafetyGuard for RiskLevelGuard {
    fn name(&self) -> &str {
        &self.name
    }

    fn description(&self) -> &str {
        &self.description
    }

    fn check(&self, mode: ExecutionMode, operation: &Operation) -> GuardResult {
        let start = std::time::Instant::now();
        
        let max_allowed_risk = match mode {
            ExecutionMode::Live => RiskLevel::Medium,
            ExecutionMode::DryRun => RiskLevel::High,
            ExecutionMode::Backtest => RiskLevel::High,
        };
        
        let allowed = operation.risk_level.value() <= max_allowed_risk.value();
        
        let reason = if allowed {
            format!("Risk level {:?} is within allowed threshold for mode {:?}", 
                    operation.risk_level, mode)
        } else {
            format!("Risk level {:?} exceeds allowed threshold {:?} for mode {:?}", 
                   operation.risk_level, max_allowed_risk, mode)
        };
        
        let risk_assessment = RiskAssessment {
            risk_score: operation.risk_level.value() as f64 / 3.0,
            risk_factors: vec![
                RiskFactor {
                    name: "operation_risk_level".to_string(),
                    description: "Inherent risk level of the operation".to_string(),
                    impact: operation.risk_level.value() as f64 / 3.0,
                    category: RiskCategory::Financial,
                }
            ],
            mitigation_suggestions: if !allowed {
                vec!["Consider reducing operation risk level".to_string()]
            } else {
                vec![]
            },
            confidence_level: 0.9,
        };
        
        GuardResult {
            guard_name: self.name.clone(),
            allowed,
            reason,
            risk_assessment,
            recommendations: vec![],
            execution_time_us: start.elapsed().as_micros() as u64,
        }
    }

    fn applies_to_modes(&self) -> Vec<ExecutionMode> {
        vec![ExecutionMode::Live, ExecutionMode::DryRun, ExecutionMode::Backtest]
    }

    fn risk_threshold(&self) -> RiskLevel {
        RiskLevel::None
    }
}

/// Configuration Guard
/// حارس التكوين
pub struct ConfigurationGuard {
    name: String,
    description: String,
}

impl ConfigurationGuard {
    pub fn new() -> Self {
        Self {
            name: "configuration_guard".to_string(),
            description: "Validates configuration changes against execution mode constraints".to_string(),
        }
    }
}

impl SafetyGuard for ConfigurationGuard {
    fn name(&self) -> &str {
        &self.name
    }

    fn description(&self) -> &str {
        &self.description
    }

    fn check(&self, mode: ExecutionMode, operation: &Operation) -> GuardResult {
        let start = std::time::Instant::now();
        
        let allowed = match (mode, operation.operation_type) {
            (ExecutionMode::Live, OperationType::ConfigurationChange) => {
                // Configuration changes in live mode require additional validation
                operation.parameters.get("validated").map_or(false, |v| v.as_bool().unwrap_or(false))
            }
            (ExecutionMode::DryRun, OperationType::ConfigurationChange) => true,
            (ExecutionMode::Backtest, OperationType::ConfigurationChange) => false, // No config changes in backtest
            (_, _) => true, // Other operations allowed
        };
        
        let reason = if allowed {
            "Configuration change allowed".to_string()
        } else {
            "Configuration change not allowed in current mode".to_string()
        };
        
        let risk_assessment = RiskAssessment {
            risk_score: if operation.operation_type == OperationType::ConfigurationChange { 0.3 } else { 0.1 },
            risk_factors: vec![
                RiskFactor {
                    name: "configuration_risk".to_string(),
                    description: "Risk associated with configuration changes".to_string(),
                    impact: if operation.operation_type == OperationType::ConfigurationChange { 0.3 } else { 0.1 },
                    category: RiskCategory::Operational,
                }
            ],
            mitigation_suggestions: if !allowed {
                vec!["Validate configuration changes in DryRun mode first".to_string()]
            } else {
                vec![]
            },
            confidence_level: 0.7,
        };
        
        GuardResult {
            guard_name: self.name.clone(),
            allowed,
            reason,
            risk_assessment,
            recommendations: vec![],
            execution_time_us: start.elapsed().as_micros() as u64,
        }
    }

    fn applies_to_modes(&self) -> Vec<ExecutionMode> {
        vec![ExecutionMode::Live, ExecutionMode::DryRun, ExecutionMode::Backtest]
    }

    fn risk_threshold(&self) -> RiskLevel {
        RiskLevel::Low
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_operation_creation() {
        let operation = Operation {
            id: "test-op".to_string(),
            operation_type: OperationType::Trade,
            user: "test-user".to_string(),
            timestamp: Utc::now(),
            parameters: HashMap::new(),
            risk_level: RiskLevel::Medium,
            metadata: HashMap::new(),
        };
        
        assert_eq!(operation.operation_type, OperationType::Trade);
        assert_eq!(operation.user, "test-user");
        assert_eq!(operation.risk_level, RiskLevel::Medium);
    }

    #[test]
    fn test_guard_result() {
        let result = GuardResult {
            guard_name: "test-guard".to_string(),
            allowed: true,
            reason: "Test passed".to_string(),
            risk_assessment: RiskAssessment {
                risk_score: 0.1,
                risk_factors: vec![],
                mitigation_suggestions: vec![],
                confidence_level: 0.9,
            },
            recommendations: vec![],
            execution_time_us: 100,
        };
        
        assert!(result.allowed);
        assert_eq!(result.guard_name, "test-guard");
        assert_eq!(result.execution_time_us, 100);
    }

    #[test]
    fn test_live_trading_guard() {
        let guard = LiveTradingGuard::new();
        assert_eq!(guard.name(), "live_trading_guard");
        assert!(guard.applies_to_modes().contains(&ExecutionMode::Live));
        assert_eq!(guard.risk_threshold(), RiskLevel::Medium);
    }

    #[tokio::test]
    async fn test_safety_guard_manager() {
        let config = GuardManagerConfig::default();
        let manager = SafetyGuardManager::new(config);
        
        // Register a guard
        let guard = LiveTradingGuard::new();
        manager.register_guard(Box::new(guard)).await.unwrap();
        
        // Check guards
        let guards = manager.get_guards().await;
        assert_eq!(guards.len(), 1);
        assert!(guards.contains(&"live_trading_guard".to_string()));
    }

    #[test]
    fn test_risk_category() {
        assert_eq!(format!("{:?}", RiskCategory::Financial), "Financial");
        assert_eq!(format!("{:?}", RiskCategory::Operational), "Operational");
        assert_eq!(format!("{:?}", RiskCategory::Compliance), "Compliance");
    }

    #[test]
    fn test_guard_decision() {
        assert_eq!(format!("{:?}", GuardDecision::Allow), "Allow");
        assert_eq!(format!("{:?}", GuardDecision::Deny), "Deny");
        assert_eq!(format!("{:?}", GuardDecision::RequireApproval), "RequireApproval");
        assert_eq!(format!("{:?}", GuardDecision::RequireManualReview), "RequireManualReview");
    }
}
