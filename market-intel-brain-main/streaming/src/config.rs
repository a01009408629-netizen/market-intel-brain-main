//! Configuration management for Redpanda streaming
//! 
//! This module provides comprehensive configuration management for Redpanda clients,
//! producers, consumers, and stream processing components.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::Duration;
use crate::serde_types::{TopicConfig, ConsumerGroupConfig, ProducerConfig, StreamConfig};

/// Default Redpanda broker addresses
pub const DEFAULT_BROKERS: &[&str] = &["localhost:9092"];
/// Default topic prefix
pub const DEFAULT_TOPIC_PREFIX: &str = "market_intel";
/// Default client ID prefix
pub const DEFAULT_CLIENT_ID_PREFIX: &str = "market_intel_client";
/// Default consumer group prefix
pub const DEFAULT_GROUP_ID_PREFIX: &str = "market_intel_group";

/// Redpanda streaming configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedpandaConfig {
    /// Broker addresses
    pub brokers: Vec<String>,
    /// Security configuration
    pub security: SecurityConfig,
    /// Client configuration
    pub client: ClientConfig,
    /// Producer configuration
    pub producer: ProducerConfig,
    /// Consumer configuration
    pub consumer: ConsumerConfig,
    /// Topic configurations
    pub topics: HashMap<String, TopicConfig>,
    /// Stream configurations
    pub streams: HashMap<String, StreamConfig>,
    /// Global settings
    pub global: GlobalConfig,
}

/// Security configuration for Redpanda
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityConfig {
    /// Security protocol
    pub security_protocol: SecurityProtocol,
    /// SASL configuration
    pub sasl: Option<SaslConfig>,
    /// SSL/TLS configuration
    pub ssl: Option<SslConfig>,
    /// Additional security properties
    pub properties: HashMap<String, String>,
}

/// Security protocol types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SecurityProtocol {
    /// No security
    Plaintext,
    /// SSL/TLS encryption
    Ssl,
    /// SASL authentication
    SaslPlaintext,
    /// SASL over SSL/TLS
    SaslSsl,
}

/// SASL authentication configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SaslConfig {
    /// SASL mechanism
    pub mechanism: SaslMechanism,
    /// Username
    pub username: String,
    /// Password
    pub password: String,
    /// SASL service name
    pub service_name: Option<String>,
    /// Kerberos configuration
    pub kerberos: Option<KerberosConfig>,
}

/// SASL mechanisms
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SaslMechanism {
    /// Plain text authentication
    Plain,
    /// SCRAM-SHA-256
    ScramSha256,
    /// SCRAM-SHA-512
    ScramSha512,
    /// GSSAPI (Kerberos)
    Gssapi,
    /// OAuth Bearer
    OAuthBearer,
}

/// Kerberos configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KerberosConfig {
    /// Service principal name
    pub service_name: String,
    /// Keytab file path
    pub keytab_path: String,
    /// Realm
    pub realm: String,
    /// Minimum time before refresh
    pub min_time_before_renewal: Duration,
    /// SPNEGO configuration
    pub spnego: Option<SpnegoConfig>,
}

/// SPNEGO configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpnegoConfig {
    /// Keytab file path
    pub keytab_path: String,
    /// Principal
    pub principal: String,
}

/// SSL/TLS configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SslConfig {
    /// CA certificate file path
    pub ca_file: Option<String>,
    /// Certificate file path
    pub cert_file: Option<String>,
    /// Private key file path
    pub key_file: Option<String>,
    /// Private key password
    pub key_password: Option<String>,
    /// Verify hostname
    pub verify_hostname: bool,
    /// Certificate verification mode
    pub cert_verification_mode: CertVerificationMode,
    /// SSL protocols
    pub ssl_protocols: Vec<String>,
    /// Cipher suites
    pub cipher_suites: Vec<String>,
}

/// Certificate verification modes
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CertVerificationMode {
    /// No verification
    None,
    /// Verify peer certificate
    Peer,
    /// Verify peer certificate if present
    PeerIfPresent,
    /// Require peer certificate
    RequirePeer,
}

/// Client configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClientConfig {
    /// Client ID
    pub client_id: String,
    /// Bootstrap servers
    pub bootstrap_servers: Vec<String>,
    /// Connection timeout
    pub connection_timeout: Duration,
    /// Request timeout
    pub request_timeout: Duration,
    /// Metadata request timeout
    pub metadata_request_timeout: Duration,
    /// Metadata refresh interval
    pub metadata_refresh_interval: Duration,
    /// Maximum connections per broker
    pub max_connections_per_broker: u32,
    /// Reconnect backoff time
    pub reconnect_backoff: Duration,
    /// Reconnect backoff max time
    pub reconnect_backoff_max: Duration,
    /// Retry backoff time
    pub retry_backoff: Duration,
    /// Additional client properties
    pub properties: HashMap<String, String>,
}

/// Global configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GlobalConfig {
    /// Enable debug logging
    pub debug: bool,
    /// Log level
    pub log_level: String,
    /// Metrics configuration
    pub metrics: MetricsConfig,
    /// Health check configuration
    pub health_check: HealthCheckConfig,
    /// Performance tuning
    pub performance: PerformanceConfig,
}

/// Metrics configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricsConfig {
    /// Enable metrics collection
    pub enabled: bool,
    /// Metrics port
    pub port: u16,
    /// Metrics path
    pub path: String,
    /// Metrics refresh interval
    pub refresh_interval: Duration,
    /// Export metrics to Prometheus
    pub prometheus: PrometheusConfig,
}

/// Prometheus configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PrometheusConfig {
    /// Enable Prometheus exporter
    pub enabled: bool,
    /// Exporter port
    pub port: u16,
    /// Exporter path
    pub path: String,
    /// Namespace for metrics
    pub namespace: String,
    /// Subsystem for metrics
    pub subsystem: String,
}

/// Health check configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthCheckConfig {
    /// Enable health checks
    pub enabled: bool,
    /// Health check port
    pub port: u16,
    /// Health check path
    pub path: String,
    /// Health check interval
    pub interval: Duration,
    /// Health check timeout
    pub timeout: Duration,
}

/// Performance configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceConfig {
    /// Number of IO threads
    pub io_threads: u32,
    /// Number of background threads
    pub background_threads: u32,
    /// Buffer memory size
    pub buffer_memory: usize,
    /// Batch buffer size
    pub batch_buffer_size: usize,
    /// Enable compression
    pub enable_compression: bool,
    /// Default compression type
    pub default_compression_type: CompressionType,
}

/// Compression types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CompressionType {
    /// No compression
    None,
    /// Gzip compression
    Gzip,
    /// Snappy compression
    Snappy,
    /// LZ4 compression
    Lz4,
    /// Zstd compression
    Zstd,
}

impl Default for RedpandaConfig {
    fn default() -> Self {
        Self {
            brokers: DEFAULT_BROKERS.iter().map(|s| s.to_string()).collect(),
            security: SecurityConfig::default(),
            client: ClientConfig::default(),
            producer: ProducerConfig::default(),
            consumer: ConsumerGroupConfig::default(),
            topics: HashMap::new(),
            streams: HashMap::new(),
            global: GlobalConfig::default(),
        }
    }
}

impl Default for SecurityConfig {
    fn default() -> Self {
        Self {
            security_protocol: SecurityProtocol::Plaintext,
            sasl: None,
            ssl: None,
            properties: HashMap::new(),
        }
    }
}

impl Default for ClientConfig {
    fn default() -> Self {
        Self {
            client_id: format!("{}_{}", DEFAULT_CLIENT_ID_PREFIX, uuid::Uuid::new_v4()),
            bootstrap_servers: DEFAULT_BROKERS.iter().map(|s| s.to_string()).collect(),
            connection_timeout: Duration::from_secs(30),
            request_timeout: Duration::from_secs(30),
            metadata_request_timeout: Duration::from_secs(5),
            metadata_refresh_interval: Duration::from_secs(300),
            max_connections_per_broker: 5,
            reconnect_backoff: Duration::from_millis(50),
            reconnect_backoff_max: Duration::from_secs(30),
            retry_backoff: Duration::from_millis(100),
            properties: HashMap::new(),
        }
    }
}

impl Default for GlobalConfig {
    fn default() -> Self {
        Self {
            debug: false,
            log_level: "info".to_string(),
            metrics: MetricsConfig::default(),
            health_check: HealthCheckConfig::default(),
            performance: PerformanceConfig::default(),
        }
    }
}

impl Default for MetricsConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            port: 9090,
            path: "/metrics".to_string(),
            refresh_interval: Duration::from_secs(15),
            prometheus: PrometheusConfig::default(),
        }
    }
}

impl Default for PrometheusConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            port: 9090,
            path: "/metrics".to_string(),
            namespace: "market_intel".to_string(),
            subsystem: "redpanda".to_string(),
        }
    }
}

impl Default for HealthCheckConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            port: 8080,
            path: "/health".to_string(),
            interval: Duration::from_secs(30),
            timeout: Duration::from_secs(5),
        }
    }
}

impl Default for PerformanceConfig {
    fn default() -> Self {
        Self {
            io_threads: num_cpus::get() as u32,
            background_threads: (num_cpus::get() / 2) as u32,
            buffer_memory: 64 * 1024 * 1024, // 64MB
            batch_buffer_size: 16 * 1024,     // 16KB
            enable_compression: true,
            default_compression_type: CompressionType::Lz4,
        }
    }
}

/// Configuration loader
pub struct ConfigLoader;

impl ConfigLoader {
    /// Load configuration from file
    pub fn load_from_file<P: AsRef<std::path::Path>>(path: P) -> Result<RedpandaConfig, Box<dyn std::error::Error>> {
        let content = std::fs::read_to_string(path)?;
        let config: RedpandaConfig = toml::from_str(&content)?;
        Ok(config)
    }

    /// Save configuration to file
    pub fn save_to_file<P: AsRef<std::path::Path>>(
        config: &RedpandaConfig,
        path: P,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let content = toml::to_string_pretty(config)?;
        std::fs::write(path, content)?;
        Ok(())
    }

    /// Load configuration from environment variables
    pub fn load_from_env() -> RedpandaConfig {
        let mut config = RedpandaConfig::default();

        // Load brokers
        if let Ok(brokers) = std::env::var("REDPANDA_BROKERS") {
            config.brokers = brokers.split(',').map(|s| s.trim().to_string()).collect();
        }

        // Load security protocol
        if let Ok(security_protocol) = std::env::var("REDPANDA_SECURITY_PROTOCOL") {
            config.security.security_protocol = match security_protocol.as_str() {
                "PLAINTEXT" => SecurityProtocol::Plaintext,
                "SSL" => SecurityProtocol::Ssl,
                "SASL_PLAINTEXT" => SecurityProtocol::SaslPlaintext,
                "SASL_SSL" => SecurityProtocol::SaslSsl,
                _ => SecurityProtocol::Plaintext,
            };
        }

        // Load SASL configuration
        if let Ok(username) = std::env::var("REDPANDA_SASL_USERNAME") {
            let password = std::env::var("REDPANDA_SASL_PASSWORD")
                .unwrap_or_else(|_| String::new());
            let mechanism = std::env::var("REDPANDA_SASL_MECHANISM")
                .unwrap_or_else(|_| "PLAIN".to_string());

            config.security.sasl = Some(SaslConfig {
                mechanism: match mechanism.as_str() {
                    "PLAIN" => SaslMechanism::Plain,
                    "SCRAM-SHA-256" => SaslMechanism::ScramSha256,
                    "SCRAM-SHA-512" => SaslMechanism::ScramSha512,
                    "GSSAPI" => SaslMechanism::Gssapi,
                    "OAUTHBEARER" => SaslMechanism::OAuthBearer,
                    _ => SaslMechanism::Plain,
                },
                username,
                password,
                service_name: std::env::var("REDPANDA_SASL_SERVICE_NAME").ok(),
                kerberos: None,
            });
        }

        // Load SSL configuration
        if let Ok(ca_file) = std::env::var("REDPANDA_SSL_CA_FILE") {
            config.security.ssl = Some(SslConfig {
                ca_file: Some(ca_file),
                cert_file: std::env::var("REDPANDA_SSL_CERT_FILE").ok(),
                key_file: std::env::var("REDPANDA_SSL_KEY_FILE").ok(),
                key_password: std::env::var("REDPANDA_SSL_KEY_PASSWORD").ok(),
                verify_hostname: std::env::var("REDPANDA_SSL_VERIFY_HOSTNAME")
                    .unwrap_or_else(|_| "true".to_string())
                    .parse()
                    .unwrap_or(true),
                cert_verification_mode: CertVerificationMode::Peer,
                ssl_protocols: vec!["TLSv1.2".to_string(), "TLSv1.3".to_string()],
                cipher_suites: Vec::new(),
            });
        }

        // Load client configuration
        if let Ok(client_id) = std::env::var("REDPANDA_CLIENT_ID") {
            config.client.client_id = client_id;
        }

        config
    }

    /// Merge configurations
    pub fn merge(base: &RedpandaConfig, override_config: &RedpandaConfig) -> RedpandaConfig {
        let mut merged = base.clone();
        
        // Merge brokers
        if !override_config.brokers.is_empty() {
            merged.brokers = override_config.brokers.clone();
        }

        // Merge security configuration
        if !matches!(override_config.security.security_protocol, SecurityProtocol::Plaintext) {
            merged.security = override_config.security.clone();
        }

        // Merge client configuration
        if override_config.client.client_id != base.client.client_id {
            merged.client = override_config.client.clone();
        }

        // Merge topics
        for (name, topic_config) in &override_config.topics {
            merged.topics.insert(name.clone(), topic_config.clone());
        }

        // Merge streams
        for (name, stream_config) in &override_config.streams {
            merged.streams.insert(name.clone(), stream_config.clone());
        }

        merged
    }
}

/// Configuration builder
pub struct ConfigBuilder {
    config: RedpandaConfig,
}

impl ConfigBuilder {
    /// Create a new configuration builder
    pub fn new() -> Self {
        Self {
            config: RedpandaConfig::default(),
        }
    }

    /// Set brokers
    pub fn brokers(mut self, brokers: Vec<String>) -> Self {
        self.config.brokers = brokers;
        self
    }

    /// Set security protocol
    pub fn security_protocol(mut self, protocol: SecurityProtocol) -> Self {
        self.config.security.security_protocol = protocol;
        self
    }

    /// Set SASL configuration
    pub fn sasl_config(mut self, sasl: SaslConfig) -> Self {
        self.config.security.sasl = Some(sasl);
        self
    }

    /// Set SSL configuration
    pub fn ssl_config(mut self, ssl: SslConfig) -> Self {
        self.config.security.ssl = Some(ssl);
        self
    }

    /// Set client ID
    pub fn client_id(mut self, client_id: String) -> Self {
        self.config.client.client_id = client_id;
        self
    }

    /// Add topic configuration
    pub fn add_topic(mut self, name: String, config: TopicConfig) -> Self {
        self.config.topics.insert(name, config);
        self
    }

    /// Add stream configuration
    pub fn add_stream(mut self, name: String, config: StreamConfig) -> Self {
        self.config.streams.insert(name, config);
        self
    }

    /// Enable debug mode
    pub fn debug(mut self, debug: bool) -> Self {
        self.config.global.debug = debug;
        self
    }

    /// Set log level
    pub fn log_level(mut self, level: String) -> Self {
        self.config.global.log_level = level;
        self
    }

    /// Build the configuration
    pub fn build(self) -> RedpandaConfig {
        self.config
    }
}

impl Default for ConfigBuilder {
    fn default() -> Self {
        Self::new()
    }
}

/// Configuration utilities
pub struct ConfigUtils;

impl ConfigUtils {
    /// Validate configuration
    pub fn validate(config: &RedpandaConfig) -> Result<(), String> {
        // Validate brokers
        if config.brokers.is_empty() {
            return Err("At least one broker must be specified".to_string());
        }

        // Validate security configuration
        match &config.security.security_protocol {
            SecurityProtocol::SaslPlaintext | SecurityProtocol::SaslSsl => {
                if config.security.sasl.is_none() {
                    return Err("SASL configuration is required for SASL security protocol".to_string());
                }
            }
            SecurityProtocol::Ssl | SecurityProtocol::SaslSsl => {
                if config.security.ssl.is_none() {
                    return Err("SSL configuration is required for SSL security protocol".to_string());
                }
            }
            _ => {}
        }

        // Validate client configuration
        if config.client.client_id.is_empty() {
            return Err("Client ID cannot be empty".to_string());
        }

        // Validate topic configurations
        for (name, topic_config) in &config.topics {
            if topic_config.topic_name.is_empty() {
                return Err(format!("Topic name cannot be empty for topic '{}'", name));
            }
            if topic_config.partitions <= 0 {
                return Err(format!("Partitions must be positive for topic '{}'", name));
            }
            if topic_config.replication_factor <= 0 {
                return Err(format!("Replication factor must be positive for topic '{}'", name));
            }
        }

        Ok(())
    }

    /// Get Kafka client configuration
    pub fn get_kafka_config(config: &RedpandaConfig) -> HashMap<String, String> {
        let mut kafka_config = HashMap::new();

        // Bootstrap servers
        kafka_config.insert("bootstrap.servers".to_string(), config.brokers.join(","));

        // Client ID
        kafka_config.insert("client.id".to_string(), config.client.client_id.clone());

        // Security configuration
        match config.security.security_protocol {
            SecurityProtocol::Plaintext => {
                kafka_config.insert("security.protocol".to_string(), "plaintext".to_string());
            }
            SecurityProtocol::Ssl => {
                kafka_config.insert("security.protocol".to_string(), "ssl".to_string());
            }
            SecurityProtocol::SaslPlaintext => {
                kafka_config.insert("security.protocol".to_string(), "sasl_plaintext".to_string());
            }
            SecurityProtocol::SaslSsl => {
                kafka_config.insert("security.protocol".to_string(), "sasl_ssl".to_string());
            }
        }

        // SASL configuration
        if let Some(sasl) = &config.security.sasl {
            let mechanism = match sasl.mechanism {
                SaslMechanism::Plain => "PLAIN",
                SaslMechanism::ScramSha256 => "SCRAM-SHA-256",
                SaslMechanism::ScramSha512 => "SCRAM-SHA-512",
                SaslMechanism::Gssapi => "GSSAPI",
                SaslMechanism::OAuthBearer => "OAUTHBEARER",
            };
            kafka_config.insert("sasl.mechanism".to_string(), mechanism.to_string());
            kafka_config.insert("sasl.username".to_string(), sasl.username.clone());
            kafka_config.insert("sasl.password".to_string(), sasl.password.clone());

            if let Some(service_name) = &sasl.service_name {
                kafka_config.insert("sasl.service.name".to_string(), service_name.clone());
            }
        }

        // SSL configuration
        if let Some(ssl) = &config.security.ssl {
            if let Some(ca_file) = &ssl.ca_file {
                kafka_config.insert("ssl.ca.location".to_string(), ca_file.clone());
            }
            if let Some(cert_file) = &ssl.cert_file {
                kafka_config.insert("ssl.certificate.location".to_string(), cert_file.clone());
            }
            if let Some(key_file) = &ssl.key_file {
                kafka_config.insert("ssl.key.location".to_string(), key_file.clone());
            }
            if let Some(key_password) = &ssl.key_password {
                kafka_config.insert("ssl.key.password".to_string(), key_password.clone());
            }
            kafka_config.insert("ssl.verify.hostname".to_string(), ssl.verify_hostname.to_string());
        }

        // Performance configuration
        kafka_config.insert("socket.timeout.ms".to_string(), config.client.request_timeout.as_millis().to_string());
        kafka_config.insert("request.timeout.ms".to_string(), config.client.request_timeout.as_millis().to_string());
        kafka_config.insert("metadata.request.timeout.ms".to_string(), config.client.metadata_request_timeout.as_millis().to_string());

        // Add custom properties
        for (key, value) in &config.client.properties {
            kafka_config.insert(key.clone(), value.clone());
        }

        kafka_config
    }

    /// Format configuration for display
    pub fn format_config(config: &RedpandaConfig) -> String {
        format!(
            "Redpanda Configuration:\n\
             Brokers: {}\n\
             Security Protocol: {:?}\n\
             Client ID: {}\n\
             Topics: {}\n\
             Streams: {}\n\
             Debug: {}",
            config.brokers.join(","),
            config.security.security_protocol,
            config.client.client_id,
            config.topics.len(),
            config.streams.len(),
            config.global.debug
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = RedpandaConfig::default();
        assert_eq!(config.brokers, vec!["localhost:9092"]);
        assert!(matches!(config.security.security_protocol, SecurityProtocol::Plaintext));
        assert!(config.client.client_id.starts_with("market_intel_client"));
    }

    #[test]
    fn test_config_builder() {
        let config = ConfigBuilder::new()
            .brokers(vec!["broker1:9092".to_string(), "broker2:9092".to_string()])
            .client_id("test_client".to_string())
            .debug(true)
            .build();

        assert_eq!(config.brokers, vec!["broker1:9092", "broker2:9092"]);
        assert_eq!(config.client.client_id, "test_client");
        assert!(config.global.debug);
    }

    #[test]
    fn test_config_validation() {
        let mut config = RedpandaConfig::default();
        assert!(ConfigUtils::validate(&config).is_ok());

        config.brokers.clear();
        assert!(ConfigUtils::validate(&config).is_err());

        config.brokers = vec!["localhost:9092".to_string()];
        config.security.security_protocol = SecurityProtocol::SaslPlaintext;
        assert!(ConfigUtils::validate(&config).is_err());
    }

    #[test]
    fn test_kafka_config_generation() {
        let config = RedpandaConfig::default();
        let kafka_config = ConfigUtils::get_kafka_config(&config);

        assert_eq!(kafka_config.get("bootstrap.servers"), Some(&"localhost:9092".to_string()));
        assert_eq!(kafka_config.get("security.protocol"), Some(&"plaintext".to_string()));
        assert!(kafka_config.contains_key("client.id"));
    }

    #[test]
    fn test_env_loading() {
        std::env::set_var("REDPANDA_BROKERS", "broker1:9092,broker2:9092");
        std::env::set_var("REDPANDA_CLIENT_ID", "env_test_client");
        
        let config = ConfigLoader::load_from_env();
        assert_eq!(config.brokers, vec!["broker1:9092", "broker2:9092"]);
        assert_eq!(config.client.client_id, "env_test_client");
        
        std::env::remove_var("REDPANDA_BROKERS");
        std::env::remove_var("REDPANDA_CLIENT_ID");
    }
}
