// Copyright (c) 2024 Market Intel Brain Team
// Execution Mode Enum - Global execution safety modes
// تعداد أنماط التنفيذ - أنماط التنفيذ الآمنة العالمية

use std::fmt;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use chrono::{DateTime, Utc};

/// Global Execution Mode Enum
/// تعداد نمط التنفيذ العالمي
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ExecutionMode {
    /// Live mode - Real money/actions
    /// نمط مباشر - أموال/إجراءات حقيقية
    Live,
    
    /// DryRun mode - Simulate execution, log results
    /// نمط التشغيل الجاف - محاكاة التنفيذ، تسجيل النتائج
    DryRun,
    
    /// Backtest mode - Fast-forward purely on historical data
    /// نمط الاختبار الخلفي - التقدم السريع فقط على البيانات التاريخية
    Backtest,
}

impl ExecutionMode {
    /// Get the string representation of the execution mode
    /// الحصول على التمثيل النصي لنمط التنفيذ
    pub fn as_str(&self) -> &'static str {
        match self {
            ExecutionMode::Live => "live",
            ExecutionMode::DryRun => "dry_run",
            ExecutionMode::Backtest => "backtest",
        }
    }

    /// Get the display name of the execution mode
    /// الحصول على اسم العرض لنمط التنفيذ
    pub fn display_name(&self) -> &'static str {
        match self {
            ExecutionMode::Live => "Live Trading",
            ExecutionMode::DryRun => "Dry Run Simulation",
            ExecutionMode::Backtest => "Backtest Mode",
        }
    }

    /// Get the description of the execution mode
    /// الحصول على وصف نمط التنفيذ
    pub fn description(&self) -> &'static str {
        match self {
            ExecutionMode::Live => "Real money trading with actual market execution",
            ExecutionMode::DryRun => "Simulated execution with real-time data, no actual trades",
            ExecutionMode::Backtest => "Historical data analysis with fast-forward simulation",
        }
    }

    /// Check if the mode allows real execution
    /// التحقق مما إذا كان النمط يسمح بالتنفيذ الحقيقي
    pub fn allows_real_execution(&self) -> bool {
        matches!(self, ExecutionMode::Live)
    }

    /// Check if the mode allows real-time data
    /// التحقق مما إذا كان النمط يسمح بالبيانات في الوقت الفعلي
    pub fn allows_real_time_data(&self) -> bool {
        matches!(self, ExecutionMode::Live | ExecutionMode::DryRun)
    }

    /// Check if the mode uses historical data
    /// التحقق مما إذا كان النمط يستخدم البيانات التاريخية
    pub fn uses_historical_data(&self) -> bool {
        matches!(self, ExecutionMode::Backtest)
    }

    /// Check if the mode is safe for production
    /// التحقق مما إذا كان النمط آمنًا للإنتاج
    pub fn is_production_safe(&self) -> bool {
        !matches!(self, ExecutionMode::Live)
    }

    /// Check if the mode requires risk management
    /// التحقق مما إذا كان النمط يتطلب إدارة المخاطر
    pub fn requires_risk_management(&self) -> bool {
        matches!(self, ExecutionMode::Live)
    }

    /// Get the risk level of the execution mode
    /// الحصول على مستوى المخاطر لنمط التنفيذ
    pub fn risk_level(&self) -> RiskLevel {
        match self {
            ExecutionMode::Live => RiskLevel::High,
            ExecutionMode::DryRun => RiskLevel::Low,
            ExecutionMode::Backtest => RiskLevel::None,
        }
    }

    /// Get the required permissions for the execution mode
    /// الحصول على الأذونات المطلوبة لنمط التنفيذ
    pub fn required_permissions(&self) -> Vec<Permission> {
        match self {
            ExecutionMode::Live => vec![
                Permission::RealTrading,
                Permission::RiskManagement,
                Permission::Compliance,
                Permission::AuditLogging,
            ],
            ExecutionMode::DryRun => vec![
                Permission::Simulation,
                Permission::MarketData,
                Permission::AuditLogging,
            ],
            ExecutionMode::Backtest => vec![
                Permission::HistoricalData,
                Permission::Simulation,
                Permission::Analysis,
            ],
        }
    }

    /// Get the monitoring requirements for the execution mode
    /// الحصول على متطلبات المراقبة لنمط التنفيذ
    pub fn monitoring_requirements(&self) -> Vec<MonitoringRequirement> {
        match self {
            ExecutionMode::Live => vec![
                MonitoringRequirement::RealTimeMetrics,
                MonitoringRequirement::RiskMetrics,
                MonitoringRequirement::TradeExecution,
                MonitoringRequirement::ComplianceMonitoring,
                MonitoringRequirement::Alerting,
            ],
            ExecutionMode::DryRun => vec![
                MonitoringRequirement::SimulationMetrics,
                MonitoringRequirement::PerformanceMetrics,
                MonitoringRequirement::AuditLogging,
            ],
            ExecutionMode::Backtest => vec![
                MonitoringRequirement::BacktestMetrics,
                MonitoringRequirement::PerformanceAnalysis,
                MonitoringRequirement::ResultReporting,
            ],
        }
    }

    /// Get the data source requirements for the execution mode
    /// الحصول على متطلبات مصدر البيانات لنمط التنفيذ
    pub fn data_source_requirements(&self) -> Vec<DataSourceRequirement> {
        match self {
            ExecutionMode::Live => vec![
                DataSourceRequirement::RealTimeMarketData,
                DataSourceRequirement::OrderExecution,
                DataSourceRequirement::AccountData,
                DataSourceRequirement::RiskData,
            ],
            ExecutionMode::DryRun => vec![
                DataSourceRequirement::RealTimeMarketData,
                DataSourceRequirement::AccountData,
                DataSourceRequirement::RiskData,
            ],
            ExecutionMode::Backtest => vec![
                DataSourceRequirement::HistoricalMarketData,
                DataSourceRequirement::HistoricalTradeData,
                DataSourceRequirement::HistoricalAccountData,
            ],
        }
    }

    /// Validate if the execution mode is compatible with given requirements
    /// التحقق من توافق نمط التنفيذ مع المتطلبات المحددة
    pub fn validate_requirements(&self, requirements: &ExecutionRequirements) -> Result<(), ExecutionModeError> {
        // Check risk management requirements
        if self.requires_risk_management() && !requirements.has_risk_management {
            return Err(ExecutionModeError::RiskManagementRequired);
        }

        // Check data source requirements
        let required_sources = self.data_source_requirements();
        for source in &required_sources {
            if !requirements.available_data_sources.contains(source) {
                return Err(ExecutionModeError::MissingDataSource(source.clone()));
            }
        }

        // Check permission requirements
        let required_permissions = self.required_permissions();
        for permission in &required_permissions {
            if !requirements.available_permissions.contains(permission) {
                return Err(ExecutionModeError::MissingPermission(permission.clone()));
            }
        }

        // Check monitoring requirements
        let required_monitoring = self.monitoring_requirements();
        for monitoring in &required_monitoring {
            if !requirements.available_monitoring.contains(monitoring) {
                return Err(ExecutionModeError::MissingMonitoring(monitoring.clone()));
            }
        }

        Ok(())
    }

    /// Get the execution context for this mode
    /// الحصول على سياق التنفيذ لهذا النمط
    pub fn execution_context(&self) -> ExecutionContext {
        ExecutionContext {
            mode: *self,
            allows_real_execution: self.allows_real_execution(),
            allows_real_time_data: self.allows_real_time_data(),
            uses_historical_data: self.uses_historical_data(),
            risk_level: self.risk_level(),
            timestamp: Utc::now(),
        }
    }
}

impl fmt::Display for ExecutionMode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

impl Default for ExecutionMode {
    fn default() -> Self {
        ExecutionMode::DryRun // Safe default
    }
}

/// Risk Level Enum
/// تعداد مستوى المخاطر
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum RiskLevel {
    /// No risk - Historical analysis only
    /// لا مخاطر - تحليل تاريخي فقط
    None,
    
    /// Low risk - Simulation without real money
    /// مخاطر منخفضة - محاكاة بدون أموال حقيقية
    Low,
    
    /// Medium risk - Limited real exposure
    /// مخاطر متوسطة - تعرض حقيقي محدود
    Medium,
    
    /// High risk - Full real trading exposure
    /// مخاطر عالية - تعرض تداول حقيقي كامل
    High,
}

impl RiskLevel {
    /// Get the numeric value of the risk level
    /// الحصول على القيمة الرقمية لمستوى المخاطر
    pub fn value(&self) -> u8 {
        match self {
            RiskLevel::None => 0,
            RiskLevel::Low => 1,
            RiskLevel::Medium => 2,
            RiskLevel::High => 3,
        }
    }

    /// Get the color representation for UI
    /// الحصول على التمثيل اللوني لواجهة المستخدم
    pub fn color(&self) -> &'static str {
        match self {
            RiskLevel::None => "green",
            RiskLevel::Low => "blue",
            RiskLevel::Medium => "orange",
            RiskLevel::High => "red",
        }
    }

    /// Get the description of the risk level
    /// الحصول على وصف مستوى المخاطر
    pub fn description(&self) -> &'static str {
        match self {
            RiskLevel::None => "No financial risk - historical analysis only",
            RiskLevel::Low => "Low financial risk - simulation without real money",
            RiskLevel::Medium => "Medium financial risk - limited real exposure",
            RiskLevel::High => "High financial risk - full real trading exposure",
        }
    }
}

/// Permission Enum
/// تعداد الأذونات
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Permission {
    /// Real trading permission
    /// إذن التداول الحقيقي
    RealTrading,
    
    /// Simulation permission
    /// إذن المحاكاة
    Simulation,
    
    /// Risk management permission
    /// إذن إدارة المخاطر
    RiskManagement,
    
    /// Compliance permission
    /// إذن الامتثال
    Compliance,
    
    /// Audit logging permission
    /// إذن تسجيل المراجعة
    AuditLogging,
    
    /// Market data permission
    /// إذن بيانات السوق
    MarketData,
    
    /// Historical data permission
    /// إذن البيانات التاريخية
    HistoricalData,
    
    /// Order execution permission
    /// إذن تنفيذ الأوامر
    OrderExecution,
    
    /// Account data permission
    /// إذن بيانات الحساب
    AccountData,
    
    /// Risk data permission
    /// إذن بيانات المخاطر
    RiskData,
    
    /// Analysis permission
    /// إذن التحليل
    Analysis,
}

impl Permission {
    /// Get the string representation of the permission
    /// الحصول على التمثيل النصي للإذن
    pub fn as_str(&self) -> &'static str {
        match self {
            Permission::RealTrading => "real_trading",
            Permission::Simulation => "simulation",
            Permission::RiskManagement => "risk_management",
            Permission::Compliance => "compliance",
            Permission::AuditLogging => "audit_logging",
            Permission::MarketData => "market_data",
            Permission::HistoricalData => "historical_data",
            Permission::OrderExecution => "order_execution",
            Permission::AccountData => "account_data",
            Permission::RiskData => "risk_data",
            Permission::Analysis => "analysis",
        }
    }

    /// Get the description of the permission
    /// الحصول على وصف الإذن
    pub fn description(&self) -> &'static str {
        match self {
            Permission::RealTrading => "Permission to execute real trades with actual money",
            Permission::Simulation => "Permission to run simulations without real money",
            Permission::RiskManagement => "Permission to access and manage risk controls",
            Permission::Compliance => "Permission to access compliance features",
            Permission::AuditLogging => "Permission to access audit logs",
            Permission::MarketData => "Permission to access real-time market data",
            Permission::HistoricalData => "Permission to access historical market data",
            Permission::OrderExecution => "Permission to execute orders",
            Permission::AccountData => "Permission to access account information",
            Permission::RiskData => "Permission to access risk metrics",
            Permission::Analysis => "Permission to perform analysis",
        }
    }
}

/// Monitoring Requirement Enum
/// تعداد متطلبات المراقبة
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum MonitoringRequirement {
    /// Real-time metrics monitoring
    /// مراقبة المقاييس في الوقت الفعلي
    RealTimeMetrics,
    
    /// Risk metrics monitoring
    /// مراقبة مقاييس المخاطر
    RiskMetrics,
    
    /// Trade execution monitoring
    /// مراقبة تنفيذ التداول
    TradeExecution,
    
    /// Compliance monitoring
    /// مراقبة الامتثال
    ComplianceMonitoring,
    
    /// Alerting system
    /// نظام التنبيه
    Alerting,
    
    /// Simulation metrics
    /// مقاييس المحاكاة
    SimulationMetrics,
    
    /// Performance metrics
    /// مقاييس الأداء
    PerformanceMetrics,
    
    /// Audit logging
    /// تسجيل المراجعة
    AuditLogging,
    
    /// Backtest metrics
    /// مقاييس الاختبار الخلفي
    BacktestMetrics,
    
    /// Performance analysis
    /// تحليل الأداء
    PerformanceAnalysis,
    
    /// Result reporting
    /// تقارير النتائج
    ResultReporting,
}

impl MonitoringRequirement {
    /// Get the string representation of the monitoring requirement
    /// الحصول على التمثيل النصي لمتطلب المراقبة
    pub fn as_str(&self) -> &'static str {
        match self {
            MonitoringRequirement::RealTimeMetrics => "real_time_metrics",
            MonitoringRequirement::RiskMetrics => "risk_metrics",
            MonitoringRequirement::TradeExecution => "trade_execution",
            MonitoringRequirement::ComplianceMonitoring => "compliance_monitoring",
            MonitoringRequirement::Alerting => "alerting",
            MonitoringRequirement::SimulationMetrics => "simulation_metrics",
            MonitoringRequirement::PerformanceMetrics => "performance_metrics",
            MonitoringRequirement::AuditLogging => "audit_logging",
            MonitoringRequirement::BacktestMetrics => "backtest_metrics",
            MonitoringRequirement::PerformanceAnalysis => "performance_analysis",
            MonitoringRequirement::ResultReporting => "result_reporting",
        }
    }
}

/// Data Source Requirement Enum
/// تعداد متطلبات مصدر البيانات
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum DataSourceRequirement {
    /// Real-time market data
    /// بيانات السوق في الوقت الفعلي
    RealTimeMarketData,
    
    /// Order execution data
    /// بيانات تنفيذ الأوامر
    OrderExecution,
    
    /// Account data
    /// بيانات الحساب
    AccountData,
    
    /// Risk data
    /// بيانات المخاطر
    RiskData,
    
    /// Historical market data
    /// بيانات السوق التاريخية
    HistoricalMarketData,
    
    /// Historical trade data
    /// بيانات التداول التاريخية
    HistoricalTradeData,
    
    /// Historical account data
    /// بيانات الحساب التاريخية
    HistoricalAccountData,
}

impl DataSourceRequirement {
    /// Get the string representation of the data source requirement
    /// الحصول على التمثيل النصي لمتطلب مصدر البيانات
    pub fn as_str(&self) -> &'static str {
        match self {
            DataSourceRequirement::RealTimeMarketData => "real_time_market_data",
            DataSourceRequirement::OrderExecution => "order_execution",
            DataSourceRequirement::AccountData => "account_data",
            DataSourceRequirement::RiskData => "risk_data",
            DataSourceRequirement::HistoricalMarketData => "historical_market_data",
            DataSourceRequirement::HistoricalTradeData => "historical_trade_data",
            DataSourceRequirement::HistoricalAccountData => "historical_account_data",
        }
    }
}

/// Execution Requirements Struct
/// هيكل متطلبات التنفيذ
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionRequirements {
    /// Available permissions
    /// الأذونات المتاحة
    pub available_permissions: Vec<Permission>,
    
    /// Available data sources
    /// مصادر البيانات المتاحة
    pub available_data_sources: Vec<DataSourceRequirement>,
    
    /// Available monitoring
    /// المراقبة المتاحة
    pub available_monitoring: Vec<MonitoringRequirement>,
    
    /// Has risk management
    /// لديه إدارة مخاطر
    pub has_risk_management: bool,
    
    /// Maximum risk level allowed
    /// أقصى مستوى مخاطر مسموح
    pub max_risk_level: RiskLevel,
    
    /// Environment type
    /// نوع البيئة
    pub environment: Environment,
}

impl Default for ExecutionRequirements {
    fn default() -> Self {
        Self {
            available_permissions: vec![
                Permission::Simulation,
                Permission::MarketData,
                Permission::AuditLogging,
                Permission::Analysis,
            ],
            available_data_sources: vec![
                DataSourceRequirement::RealTimeMarketData,
                DataSourceRequirement::AccountData,
            ],
            available_monitoring: vec![
                MonitoringRequirement::SimulationMetrics,
                MonitoringRequirement::PerformanceMetrics,
                MonitoringRequirement::AuditLogging,
            ],
            has_risk_management: false,
            max_risk_level: RiskLevel::Low,
            environment: Environment::Development,
        }
    }
}

/// Environment Enum
/// تعداد البيئة
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Environment {
    /// Development environment
    /// بيئة التطوير
    Development,
    
    /// Testing environment
    /// بيئة الاختبار
    Testing,
    
    /// Staging environment
    /// بيئة التجهيز
    Staging,
    
    /// Production environment
    /// بيئة الإنتاج
    Production,
}

impl Environment {
    /// Get the string representation of the environment
    /// الحصول على التمثيل النصي للبيئة
    pub fn as_str(&self) -> &'static str {
        match self {
            Environment::Development => "development",
            Environment::Testing => "testing",
            Environment::Staging => "staging",
            Environment::Production => "production",
        }
    }

    /// Check if the environment allows live trading
    /// التحقق مما إذا كانت البيئة تسمح بالتداول المباشر
    pub fn allows_live_trading(&self) -> bool {
        matches!(self, Environment::Production)
    }

    /// Get the maximum allowed risk level for the environment
    /// الحصول على أقصى مستوى مخاطر مسموح للبيئة
    pub fn max_allowed_risk_level(&self) -> RiskLevel {
        match self {
            Environment::Development => RiskLevel::None,
            Environment::Testing => RiskLevel::Low,
            Environment::Staging => RiskLevel::Medium,
            Environment::Production => RiskLevel::High,
        }
    }
}

/// Execution Context Struct
/// هيكل سياق التنفيذ
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionContext {
    /// Execution mode
    /// نمط التنفيذ
    pub mode: ExecutionMode,
    
    /// Allows real execution
    /// يسمح بالتنفيذ الحقيقي
    pub allows_real_execution: bool,
    
    /// Allows real-time data
    /// يسمح بالبيانات في الوقت الفعلي
    pub allows_real_time_data: bool,
    
    /// Uses historical data
    /// يستخدم البيانات التاريخية
    pub uses_historical_data: bool,
    
    /// Risk level
    /// مستوى المخاطر
    pub risk_level: RiskLevel,
    
    /// Timestamp when context was created
    /// وقت إنشاء السياق
    pub timestamp: DateTime<Utc>,
}

/// Execution Mode Error
/// خطأ نمط التنفيذ
#[derive(Error, Debug)]
pub enum ExecutionModeError {
    #[error("Risk management is required for this execution mode")]
    RiskManagementRequired,
    
    #[error("Missing data source: {0:?}")]
    MissingDataSource(DataSourceRequirement),
    
    #[error("Missing permission: {0:?}")]
    MissingPermission(Permission),
    
    #[error("Missing monitoring requirement: {0:?}")]
    MissingMonitoring(MonitoringRequirement),
    
    #[error("Invalid execution mode for environment: {mode:?} in {environment:?}")]
    InvalidModeForEnvironment { mode: ExecutionMode, environment: Environment },
    
    #[error("Risk level {risk_level:?} exceeds maximum allowed {max_risk_level:?}")]
    RiskLevelExceeded { risk_level: RiskLevel, max_risk_level: RiskLevel },
    
    #[error("Execution mode transition not allowed: {from:?} to {to:?}")]
    InvalidTransition { from: ExecutionMode, to: ExecutionMode },
    
    #[error("Configuration error: {0}")]
    ConfigurationError(String),
}

/// Result type for execution mode operations
/// نوع النتيجة لعمليات نمط التنفيذ
pub type ExecutionModeResult<T> = Result<T, ExecutionModeError>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_execution_mode_properties() {
        assert_eq!(ExecutionMode::Live.as_str(), "live");
        assert_eq!(ExecutionMode::DryRun.as_str(), "dry_run");
        assert_eq!(ExecutionMode::Backtest.as_str(), "backtest");

        assert!(ExecutionMode::Live.allows_real_execution());
        assert!(!ExecutionMode::DryRun.allows_real_execution());
        assert!(!ExecutionMode::Backtest.allows_real_execution());

        assert!(ExecutionMode::Live.allows_real_time_data());
        assert!(ExecutionMode::DryRun.allows_real_time_data());
        assert!(!ExecutionMode::Backtest.allows_real_time_data());

        assert!(!ExecutionMode::Live.uses_historical_data());
        assert!(!ExecutionMode::DryRun.uses_historical_data());
        assert!(ExecutionMode::Backtest.uses_historical_data());
    }

    #[test]
    fn test_risk_levels() {
        assert_eq!(ExecutionMode::Live.risk_level(), RiskLevel::High);
        assert_eq!(ExecutionMode::DryRun.risk_level(), RiskLevel::Low);
        assert_eq!(ExecutionMode::Backtest.risk_level(), RiskLevel::None);

        assert_eq!(RiskLevel::None.value(), 0);
        assert_eq!(RiskLevel::Low.value(), 1);
        assert_eq!(RiskLevel::Medium.value(), 2);
        assert_eq!(RiskLevel::High.value(), 3);
    }

    #[test]
    fn test_permissions() {
        let live_permissions = ExecutionMode::Live.required_permissions();
        assert!(live_permissions.contains(&Permission::RealTrading));
        assert!(live_permissions.contains(&Permission::RiskManagement));

        let dry_run_permissions = ExecutionMode::DryRun.required_permissions();
        assert!(dry_run_permissions.contains(&Permission::Simulation));
        assert!(!dry_run_permissions.contains(&Permission::RealTrading));

        let backtest_permissions = ExecutionMode::Backtest.required_permissions();
        assert!(backtest_permissions.contains(&Permission::HistoricalData));
        assert!(!backtest_permissions.contains(&Permission::RealTrading));
    }

    #[test]
    fn test_environment_restrictions() {
        assert!(!Environment::Development.allows_live_trading());
        assert!(!Environment::Testing.allows_live_trading());
        assert!(!Environment::Staging.allows_live_trading());
        assert!(Environment::Production.allows_live_trading());

        assert_eq!(Environment::Development.max_allowed_risk_level(), RiskLevel::None);
        assert_eq!(Environment::Testing.max_allowed_risk_level(), RiskLevel::Low);
        assert_eq!(Environment::Staging.max_allowed_risk_level(), RiskLevel::Medium);
        assert_eq!(Environment::Production.max_allowed_risk_level(), RiskLevel::High);
    }

    #[test]
    fn test_execution_context() {
        let context = ExecutionMode::Live.execution_context();
        assert_eq!(context.mode, ExecutionMode::Live);
        assert!(context.allows_real_execution);
        assert!(context.allows_real_time_data);
        assert!(!context.uses_historical_data);
        assert_eq!(context.risk_level, RiskLevel::High);
    }

    #[test]
    fn test_validation() {
        let requirements = ExecutionRequirements::default();
        
        // Should succeed for DryRun with default requirements
        assert!(ExecutionMode::DryRun.validate_requirements(&requirements).is_ok());
        
        // Should fail for Live with default requirements (missing permissions)
        assert!(ExecutionMode::Live.validate_requirements(&requirements).is_err());
    }

    #[test]
    fn test_display() {
        assert_eq!(format!("{}", ExecutionMode::Live), "live");
        assert_eq!(format!("{}", ExecutionMode::DryRun), "dry_run");
        assert_eq!(format!("{}", ExecutionMode::Backtest), "backtest");
    }

    #[test]
    fn test_default() {
        assert_eq!(ExecutionMode::default(), ExecutionMode::DryRun);
        assert_eq!(ExecutionMode::default().risk_level(), RiskLevel::Low);
    }
}
