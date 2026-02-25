//! Configuration management for Core Engine
//! 
//! This module provides configuration structures and management
//! for the Core Engine and its components.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::Duration;

/// Core Engine configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoreEngineConfig {
    /// Number of processor threads
    pub num_processors: usize,
    /// Ring buffer size (must be power of 2)
    pub buffer_size: usize,
    /// Enable performance profiling
    pub enable_profiling: bool,
    /// Enable health monitoring
    pub enable_health_monitoring: bool,
    /// Health check interval
    pub health_check_interval: Duration,
    /// Performance monitoring interval
    pub performance_interval: Duration,
    /// Thread affinity settings
    pub thread_affinity: Option<ThreadAffinityConfig>,
    /// Memory configuration
    pub memory: MemoryConfig,
    /// Network configuration
    pub network: NetworkConfig,
    /// Security configuration
    pub security: SecurityConfig,
    /// Logging configuration
    pub logging: LoggingConfig,
    /// Metrics configuration
    pub metrics: MetricsConfig,
}

/// Thread affinity configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThreadAffinityConfig {
    /// Enable thread affinity
    pub enabled: bool,
    /// CPU cores to bind threads to
    pub cpu_cores: Vec<usize>,
    /// Affinity strategy
    pub strategy: AffinityStrategy,
}

/// Thread affinity strategies
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AffinityStrategy {
    /// Round-robin assignment
    RoundRobin,
    /// Sequential assignment
    Sequential,
    /// Manual assignment
    Manual,
    /// Automatic assignment
    Automatic,
}

/// Memory configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryConfig {
    /// Pre-allocated buffer size in MB
    pub preallocated_buffers_mb: usize,
    /// Enable memory pooling
    pub enable_pooling: bool,
    /// Pool size
    pub pool_size: usize,
    /// Memory alignment
    pub alignment: usize,
    /// Enable huge pages
    pub enable_huge_pages: bool,
    /// Garbage collection settings
    pub gc: GcConfig,
}

/// Garbage collection configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GcConfig {
    /// Enable GC
    pub enabled: bool,
    /// GC threshold in MB
    pub threshold_mb: usize,
    /// GC interval
    pub interval: Duration,
    /// GC strategy
    pub strategy: GcStrategy,
}

/// Garbage collection strategies
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum GcStrategy {
    /// Mark and sweep
    MarkAndSweep,
    /// Generational
    Generational,
    /// Reference counting
    ReferenceCounting,
    /// Concurrent
    Concurrent,
}

/// Network configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NetworkConfig {
    /// Enable network features
    pub enabled: bool,
    /// Bind address
    pub bind_address: String,
    /// Port range
    pub port_range: PortRange,
    /// Connection timeout
    pub connection_timeout: Duration,
    /// Keep-alive interval
    pub keepalive_interval: Duration,
    /// Buffer sizes
    pub buffer_sizes: BufferSizes,
    /// Protocol settings
    pub protocols: ProtocolConfig,
}

/// Port range configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PortRange {
    /// Start port
    pub start: u16,
    /// End port
    pub end: u16,
}

/// Buffer sizes configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BufferSizes {
    /// Send buffer size in bytes
    pub send_buffer: usize,
    /// Receive buffer size in bytes
    pub receive_buffer: usize,
    /// Socket buffer size in bytes
    pub socket_buffer: usize,
}

/// Protocol configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProtocolConfig {
    /// Enable TCP
    pub tcp_enabled: bool,
    /// Enable UDP
    pub udp_enabled: bool,
    /// Enable WebSocket
    pub websocket_enabled: bool,
    /// Enable gRPC
    pub grpc_enabled: bool,
    /// Enable Aeron
    pub aeron_enabled: bool,
    /// Enable Redpanda
    pub redpanda_enabled: bool,
}

/// Security configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityConfig {
    /// Enable security features
    pub enabled: bool,
    /// Authentication settings
    pub authentication: AuthenticationConfig,
    /// Authorization settings
    pub authorization: AuthorizationConfig,
    /// Encryption settings
    pub encryption: EncryptionConfig,
    /// Audit settings
    pub audit: AuditConfig,
}

/// Authentication configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthenticationConfig {
    /// Enable authentication
    pub enabled: bool,
    /// Authentication methods
    pub methods: Vec<AuthMethod>,
    /// Token expiration time
    pub token_expiration: Duration,
    /// Session timeout
    pub session_timeout: Duration,
}

/// Authentication methods
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AuthMethod {
    /// Username/password
    Password,
    /// JWT token
    Jwt,
    /// OAuth2
    OAuth2,
    /// API key
    ApiKey,
    /// Certificate-based
    Certificate,
    /// Kerberos
    Kerberos,
}

/// Authorization configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthorizationConfig {
    /// Enable authorization
    pub enabled: bool,
    /// Authorization model
    pub model: AuthzModel,
    /// Role-based access control
    pub rbac: RbacConfig,
    /// Attribute-based access control
    pub abac: AbacConfig,
}

/// Authorization models
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AuthzModel {
    /// Role-based access control
    Rbac,
    /// Attribute-based access control
    Abac,
    /// Discretionary access control
    Dac,
    /// Mandatory access control
    Mac,
    /// Hybrid model
    Hybrid,
}

/// Role-based access control configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RbacConfig {
    /// Enable RBAC
    pub enabled: bool,
    /// Role definitions
    pub roles: HashMap<String, RoleDefinition>,
    /// Permission mappings
    pub permissions: HashMap<String, Vec<String>>,
}

/// Role definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoleDefinition {
    /// Role name
    pub name: String,
    /// Role description
    pub description: String,
    /// Role permissions
    pub permissions: Vec<String>,
    /// Role hierarchy
    pub inherits: Vec<String>,
}

/// Attribute-based access control configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AbacConfig {
    /// Enable ABAC
    pub enabled: bool,
    /// Policy definitions
    pub policies: Vec<PolicyDefinition>,
    /// Attribute sources
    pub attributes: HashMap<String, AttributeSource>,
}

/// Policy definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyDefinition {
    /// Policy name
    pub name: String,
    /// Policy rules
    pub rules: Vec<PolicyRule>,
    /// Policy effect
    pub effect: PolicyEffect,
}

/// Policy rule
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyRule {
    /// Rule condition
    pub condition: String,
    /// Rule action
    pub action: String,
    /// Rule priority
    pub priority: u32,
}

/// Policy effects
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PolicyEffect {
    /// Allow access
    Allow,
    /// Deny access
    Deny,
    /// Conditional access
    Conditional,
}

/// Attribute source
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AttributeSource {
    /// User attribute
    User(String),
    /// Resource attribute
    Resource(String),
    /// Environment attribute
    Environment(String),
    /// Action attribute
    Action(String),
}

/// Encryption configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EncryptionConfig {
    /// Enable encryption
    pub enabled: bool,
    /// Encryption algorithm
    pub algorithm: EncryptionAlgorithm,
    /// Key management
    pub key_management: KeyManagementConfig,
    /// Encryption scope
    pub scope: EncryptionScope,
}

/// Encryption algorithms
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EncryptionAlgorithm {
    /// AES-256-GCM
    Aes256Gcm,
    /// ChaCha20-Poly1305
    ChaCha20Poly1305,
    /// RSA-4096
    Rsa4096,
    /// ECDSA
    Ecdsa,
}

/// Key management configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KeyManagementConfig {
    /// Key store type
    pub store_type: KeyStoreType,
    /// Key store path
    pub store_path: String,
    /// Key rotation interval
    pub rotation_interval: Duration,
    /// Key derivation settings
    pub derivation: KeyDerivationConfig,
}

/// Key store types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum KeyStoreType {
    /// File-based store
    File,
    /// Hardware security module
    Hsm,
    /// Cloud KMS
    CloudKms,
    /// Database store
    Database,
}

/// Key derivation configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KeyDerivationConfig {
    /// Derivation algorithm
    pub algorithm: DerivationAlgorithm,
    /// Salt
    pub salt: String,
    /// Iterations
    pub iterations: u32,
}

/// Key derivation algorithms
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DerivationAlgorithm {
    /// PBKDF2
    Pbkdf2,
    /// Argon2
    Argon2,
    /// Scrypt
    Scrypt,
    /// Bcrypt
    Bcrypt,
}

/// Encryption scope
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EncryptionScope {
    /// Encrypt data at rest
    pub data_at_rest: bool,
    /// Encrypt data in transit
    pub data_in_transit: bool,
    /// Encrypt memory
    pub memory: bool,
    /// Encrypt logs
    pub logs: bool,
}

/// Audit configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditConfig {
    /// Enable auditing
    pub enabled: bool,
    /// Audit log path
    pub log_path: String,
    /// Audit events
    pub events: Vec<AuditEvent>,
    /// Retention period
    pub retention_period: Duration,
    /// Compression settings
    pub compression: bool,
}

/// Audit events
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AuditEvent {
    /// Authentication events
    Authentication,
    /// Authorization events
    Authorization,
    /// Data access events
    DataAccess,
    /// Configuration changes
    ConfigurationChange,
    /// System events
    System,
    /// Security events
    Security,
    /// Performance events
    Performance,
}

/// Logging configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoggingConfig {
    /// Enable logging
    pub enabled: bool,
    /// Log level
    pub level: LogLevel,
    /// Log format
    pub format: LogFormat,
    /// Output destinations
    pub outputs: Vec<LogOutput>,
    /// Rotation settings
    pub rotation: LogRotationConfig,
}

/// Log levels
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LogLevel {
    /// Trace level
    Trace,
    /// Debug level
    Debug,
    /// Info level
    Info,
    /// Warning level
    Warning,
    /// Error level
    Error,
    /// Fatal level
    Fatal,
}

/// Log formats
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LogFormat {
    /// JSON format
    Json,
    /// Plain text format
    Text,
    /// Structured format
    Structured,
    /// Custom format
    Custom(String),
}

/// Log output destinations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LogOutput {
    /// Console output
    Console,
    /// File output
    File { path: String },
    /// Syslog output
    Syslog,
    /// Remote syslog
    RemoteSyslog { host: String, port: u16 },
    /// Database output
    Database { connection_string: String },
}

/// Log rotation configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogRotationConfig {
    /// Enable rotation
    pub enabled: bool,
    /// Rotation trigger
    pub trigger: RotationTrigger,
    /// Max file size in MB
    pub max_file_size_mb: usize,
    /// Max files to keep
    pub max_files: usize,
    /// Compression format
    pub compression: CompressionFormat,
}

/// Rotation triggers
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RotationTrigger {
    /// Size-based rotation
    Size,
    /// Time-based rotation
    Time,
    /// Hybrid rotation
    Hybrid,
}

/// Compression formats
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CompressionFormat {
    /// No compression
    None,
    /// Gzip compression
    Gzip,
    /// Zstd compression
    Zstd,
    /// LZ4 compression
    Lz4,
}

/// Metrics configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricsConfig {
    /// Enable metrics collection
    pub enabled: bool,
    /// Metrics collection interval
    pub interval: Duration,
    /// Metrics exporters
    pub exporters: Vec<MetricsExporter>,
    /// Custom metrics
    pub custom_metrics: HashMap<String, CustomMetric>,
}

/// Metrics exporters
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MetricsExporter {
    /// Prometheus exporter
    Prometheus { port: u16, path: String },
    /// InfluxDB exporter
    InfluxDB { url: String, database: String },
    /// StatsD exporter
    StatsD { host: String, port: u16 },
    /// OpenTelemetry exporter
    OpenTelemetry { endpoint: String },
    /// Custom exporter
    Custom { name: String, config: HashMap<String, String> },
}

/// Custom metric definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CustomMetric {
    /// Metric name
    pub name: String,
    /// Metric type
    pub metric_type: MetricType,
    /// Metric description
    pub description: String,
    /// Metric units
    pub unit: String,
    /// Metric labels
    pub labels: HashMap<String, String>,
}

/// Metric types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MetricType {
    /// Counter metric
    Counter,
    /// Gauge metric
    Gauge,
    /// Histogram metric
    Histogram,
    /// Summary metric
    Summary,
}

impl Default for CoreEngineConfig {
    fn default() -> Self {
        Self {
            num_processors: num_cpus::get(),
            buffer_size: 1024 * 1024, // 1M entries
            enable_profiling: true,
            enable_health_monitoring: true,
            health_check_interval: Duration::from_secs(30),
            performance_interval: Duration::from_secs(5),
            thread_affinity: None,
            memory: MemoryConfig::default(),
            network: NetworkConfig::default(),
            security: SecurityConfig::default(),
            logging: LoggingConfig::default(),
            metrics: MetricsConfig::default(),
        }
    }
}

impl Default for ThreadAffinityConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            cpu_cores: Vec::new(),
            strategy: AffinityStrategy::Automatic,
        }
    }
}

impl Default for MemoryConfig {
    fn default() -> Self {
        Self {
            preallocated_buffers_mb: 512,
            enable_pooling: true,
            pool_size: 1000,
            alignment: 64,
            enable_huge_pages: false,
            gc: GcConfig::default(),
        }
    }
}

impl Default for GcConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            threshold_mb: 100,
            interval: Duration::from_secs(60),
            strategy: GcStrategy::Generational,
        }
    }
}

impl Default for NetworkConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            bind_address: "0.0.0.0".to_string(),
            port_range: PortRange { start: 8080, end: 8090 },
            connection_timeout: Duration::from_secs(30),
            keepalive_interval: Duration::from_secs(60),
            buffer_sizes: BufferSizes::default(),
            protocols: ProtocolConfig::default(),
        }
    }
}

impl Default for PortRange {
    fn default() -> Self {
        Self { start: 8080, end: 8090 }
    }
}

impl Default for BufferSizes {
    fn default() -> Self {
        Self {
            send_buffer: 64 * 1024,      // 64KB
            receive_buffer: 64 * 1024,   // 64KB
            socket_buffer: 128 * 1024,   // 128KB
        }
    }
}

impl Default for ProtocolConfig {
    fn default() -> Self {
        Self {
            tcp_enabled: true,
            udp_enabled: false,
            websocket_enabled: true,
            grpc_enabled: true,
            aeron_enabled: true,
            redpanda_enabled: true,
        }
    }
}

impl Default for SecurityConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            authentication: AuthenticationConfig::default(),
            authorization: AuthorizationConfig::default(),
            encryption: EncryptionConfig::default(),
            audit: AuditConfig::default(),
        }
    }
}

impl Default for AuthenticationConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            methods: vec![AuthMethod::Jwt, AuthMethod::ApiKey],
            token_expiration: Duration::from_secs(3600),
            session_timeout: Duration::from_secs(1800),
        }
    }
}

impl Default for AuthorizationConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            model: AuthzModel::Hybrid,
            rbac: RbacConfig::default(),
            abac: AbacConfig::default(),
        }
    }
}

impl Default for RbacConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            roles: HashMap::new(),
            permissions: HashMap::new(),
        }
    }
}

impl Default for AbacConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            policies: Vec::new(),
            attributes: HashMap::new(),
        }
    }
}

impl Default for EncryptionConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            algorithm: EncryptionAlgorithm::Aes256Gcm,
            key_management: KeyManagementConfig::default(),
            scope: EncryptionScope::default(),
        }
    }
}

impl Default for KeyManagementConfig {
    fn default() -> Self {
        Self {
            store_type: KeyStoreType::File,
            store_path: "./keys".to_string(),
            rotation_interval: Duration::from_secs(86400), // 24 hours
            derivation: KeyDerivationConfig::default(),
        }
    }
}

impl Default for KeyDerivationConfig {
    fn default() -> Self {
        Self {
            algorithm: DerivationAlgorithm::Argon2,
            salt: "default_salt".to_string(),
            iterations: 100000,
        }
    }
}

impl Default for EncryptionScope {
    fn default() -> Self {
        Self {
            data_at_rest: true,
            data_in_transit: true,
            memory: false,
            logs: false,
        }
    }
}

impl Default for AuditConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            log_path: "./audit.log".to_string(),
            events: vec![
                AuditEvent::Authentication,
                AuditEvent::Authorization,
                AuditEvent::DataAccess,
                AuditEvent::Security,
            ],
            retention_period: Duration::from_secs(86400 * 30), // 30 days
            compression: true,
        }
    }
}

impl Default for LoggingConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            level: LogLevel::Info,
            format: LogFormat::Json,
            outputs: vec![LogOutput::Console],
            rotation: LogRotationConfig::default(),
        }
    }
}

impl Default for LogRotationConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            trigger: RotationTrigger::Hybrid,
            max_file_size_mb: 100,
            max_files: 10,
            compression: CompressionFormat::Gzip,
        }
    }
}

impl Default for MetricsConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            interval: Duration::from_secs(15),
            exporters: vec![
                MetricsExporter::Prometheus {
                    port: 9090,
                    path: "/metrics".to_string(),
                },
            ],
            custom_metrics: HashMap::new(),
        }
    }
}

/// Configuration loader
pub struct ConfigLoader;

impl ConfigLoader {
    /// Load configuration from file
    pub fn load_from_file<P: AsRef<std::path::Path>>(path: P) -> Result<CoreEngineConfig, Box<dyn std::error::Error>> {
        let content = std::fs::read_to_string(path)?;
        let config: CoreEngineConfig = toml::from_str(&content)?;
        Ok(config)
    }
    
    /// Save configuration to file
    pub fn save_to_file<P: AsRef<std::path::Path>>(
        config: &CoreEngineConfig,
        path: P,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let content = toml::to_string_pretty(config)?;
        std::fs::write(path, content)?;
        Ok(())
    }
    
    /// Load configuration from environment variables
    pub fn load_from_env() -> CoreEngineConfig {
        let mut config = CoreEngineConfig::default();
        
        // Load basic settings
        if let Ok(processors) = std::env::var("CORE_NUM_PROCESSORS") {
            if let Ok(num) = processors.parse() {
                config.num_processors = num;
            }
        }
        
        if let Ok(buffer_size) = std::env::var("CORE_BUFFER_SIZE") {
            if let Ok(size) = buffer_size.parse() {
                config.buffer_size = size;
            }
        }
        
        if let Ok(profiling) = std::env::var("CORE_ENABLE_PROFILING") {
            config.enable_profiling = profiling.parse().unwrap_or(true);
        }
        
        // Load network settings
        if let Ok(bind_address) = std::env::var("CORE_BIND_ADDRESS") {
            config.network.bind_address = bind_address;
        }
        
        if let Ok(port_start) = std::env::var("CORE_PORT_START") {
            if let Ok(start) = port_start.parse() {
                config.network.port_range.start = start;
            }
        }
        
        if let Ok(port_end) = std::env::var("CORE_PORT_END") {
            if let Ok(end) = port_end.parse() {
                config.network.port_range.end = end;
            }
        }
        
        // Load security settings
        if let Ok(security_enabled) = std::env::var("CORE_SECURITY_ENABLED") {
            config.security.enabled = security_enabled.parse().unwrap_or(true);
        }
        
        config
    }
    
    /// Merge configurations
    pub fn merge(base: &CoreEngineConfig, override_config: &CoreEngineConfig) -> CoreEngineConfig {
        let mut merged = base.clone();
        
        // Override basic settings
        if override_config.num_processors != base.num_processors {
            merged.num_processors = override_config.num_processors;
        }
        
        if override_config.buffer_size != base.buffer_size {
            merged.buffer_size = override_config.buffer_size;
        }
        
        if override_config.enable_profiling != base.enable_profiling {
            merged.enable_profiling = override_config.enable_profiling;
        }
        
        // Override network settings
        if override_config.network.bind_address != base.network.bind_address {
            merged.network.bind_address = override_config.network.bind_address.clone();
        }
        
        if override_config.network.port_range != base.network.port_range {
            merged.network.port_range = override_config.network.port_range.clone();
        }
        
        // Override security settings
        if override_config.security.enabled != base.security.enabled {
            merged.security.enabled = override_config.security.enabled;
        }
        
        merged
    }
}

/// Configuration validator
pub struct ConfigValidator;

impl ConfigValidator {
    /// Validate core engine configuration
    pub fn validate(config: &CoreEngineConfig) -> Result<(), String> {
        // Validate processor count
        if config.num_processors == 0 {
            return Err("Number of processors must be greater than 0".to_string());
        }
        
        if config.num_processors > num_cpus::get() * 2 {
            return Err("Number of processors exceeds system capacity".to_string());
        }
        
        // Validate buffer size
        if !config.buffer_size.is_power_of_two() {
            return Err("Buffer size must be a power of 2".to_string());
        }
        
        if config.buffer_size < 1024 {
            return Err("Buffer size must be at least 1024".to_string());
        }
        
        // Validate thread affinity
        if let Some(ref affinity) = config.thread_affinity {
            if affinity.enabled && affinity.cpu_cores.is_empty() {
                return Err("Thread affinity enabled but no CPU cores specified".to_string());
            }
            
            for &core in &affinity.cpu_cores {
                if core >= num_cpus::get() {
                    return Err(format!("CPU core {} exceeds system capacity", core));
                }
            }
        }
        
        // Validate network configuration
        if config.network.enabled {
            if config.network.port_range.start >= config.network.port_range.end {
                return Err("Invalid port range".to_string());
            }
            
            if config.network.port_range.start < 1024 {
                return Err("Port range should not include privileged ports".to_string());
            }
        }
        
        // Validate security configuration
        if config.security.enabled {
            if config.security.authentication.enabled && config.security.authentication.methods.is_empty() {
                return Err("Authentication enabled but no methods specified".to_string());
            }
            
            if config.security.encryption.enabled {
                match config.security.encryption.key_management.store_type {
                    KeyStoreType::File => {
                        if config.security.encryption.key_management.store_path.is_empty() {
                            return Err("File key store path not specified".to_string());
                        }
                    }
                    _ => {}
                }
            }
        }
        
        Ok(())
    }
    
    /// Get recommended configuration for system
    pub fn get_recommended() -> CoreEngineConfig {
        let cpu_count = num_cpus::get();
        let memory_gb = Self::get_system_memory_gb();
        
        CoreEngineConfig {
            num_processors: cpu_count,
            buffer_size: Self::calculate_optimal_buffer_size(cpu_count, memory_gb),
            enable_profiling: true,
            enable_health_monitoring: true,
            health_check_interval: Duration::from_secs(30),
            performance_interval: Duration::from_secs(5),
            thread_affinity: Some(ThreadAffinityConfig {
                enabled: true,
                cpu_cores: (0..cpu_count).collect(),
                strategy: AffinityStrategy::Automatic,
            }),
            memory: MemoryConfig {
                preallocated_buffers_mb: (memory_gb / 4) * 1024, // 25% of memory
                enable_pooling: true,
                pool_size: cpu_count * 100,
                alignment: 64,
                enable_huge_pages: memory_gb >= 16,
                gc: GcConfig::default(),
            },
            network: NetworkConfig::default(),
            security: SecurityConfig::default(),
            logging: LoggingConfig::default(),
            metrics: MetricsConfig::default(),
        }
    }
    
    /// Get system memory in GB
    fn get_system_memory_gb() -> usize {
        // Simplified memory detection
        // In practice, you'd use system-specific APIs
        16 // Default to 16GB
    }
    
    /// Calculate optimal buffer size
    fn calculate_optimal_buffer_size(cpu_count: usize, memory_gb: usize) -> usize {
        let base_size = 1024 * 1024; // 1M entries
        
        // Scale based on CPU count and memory
        let cpu_factor = (cpu_count as f64).log2() as usize;
        let memory_factor = (memory_gb as f64 / 16.0).ceil() as usize;
        
        base_size * cpu_factor.max(1) * memory_factor.max(1)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_default_config() {
        let config = CoreEngineConfig::default();
        assert!(config.num_processors > 0);
        assert!(config.buffer_size.is_power_of_two());
        assert!(config.enable_profiling);
        assert!(config.enable_health_monitoring);
    }
    
    #[test]
    fn test_config_validation() {
        let mut config = CoreEngineConfig::default();
        
        // Valid config should pass
        assert!(ConfigValidator::validate(&config).is_ok());
        
        // Invalid processor count should fail
        config.num_processors = 0;
        assert!(ConfigValidator::validate(&config).is_err());
        
        // Invalid buffer size should fail
        config.num_processors = 4;
        config.buffer_size = 1000; // Not power of 2
        assert!(ConfigValidator::validate(&config).is_err());
    }
    
    #[test]
    fn test_config_from_env() {
        std::env::set_var("CORE_NUM_PROCESSORS", "8");
        std::env::set_var("CORE_BUFFER_SIZE", "2097152");
        std::env::set_var("CORE_ENABLE_PROFILING", "false");
        
        let config = ConfigLoader::load_from_env();
        assert_eq!(config.num_processors, 8);
        assert_eq!(config.buffer_size, 2097152);
        assert!(!config.enable_profiling);
        
        std::env::remove_var("CORE_NUM_PROCESSORS");
        std::env::remove_var("CORE_BUFFER_SIZE");
        std::env::remove_var("CORE_ENABLE_PROFILING");
    }
    
    #[test]
    fn test_config_merge() {
        let base = CoreEngineConfig::default();
        let mut override_config = CoreEngineConfig::default();
        override_config.num_processors = 16;
        override_config.enable_profiling = false;
        
        let merged = ConfigLoader::merge(&base, &override_config);
        assert_eq!(merged.num_processors, 16);
        assert!(!merged.enable_profiling);
        assert_eq!(merged.buffer_size, base.buffer_size); // Should remain unchanged
    }
    
    #[test]
    fn test_recommended_config() {
        let config = ConfigValidator::get_recommended();
        assert!(config.num_processors > 0);
        assert!(config.buffer_size.is_power_of_two());
        assert!(config.thread_affinity.is_some());
        assert!(config.thread_affinity.as_ref().unwrap().enabled);
    }
}
