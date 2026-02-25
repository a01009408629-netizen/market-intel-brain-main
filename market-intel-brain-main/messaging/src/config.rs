//! Configuration management for Aeron messaging

use crate::core::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::Duration;

/// Aeron messaging configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AeronMessagingConfig {
    /// Aeron client configuration
    pub aeron: AeronConfig,
    /// Publisher configuration
    pub publisher: PublisherConfig,
    /// Subscriber configuration
    pub subscriber: SubscriberConfig,
    /// Codec configuration
    pub codec: CodecConfig,
    /// Channels configuration
    pub channels: HashMap<String, ChannelConfig>,
    /// Global settings
    pub global: GlobalConfig,
}

impl Default for AeronMessagingConfig {
    fn default() -> Self {
        let mut channels = HashMap::new();
        
        // Default channels
        channels.insert("market_data".to_string(), ChannelConfig {
            channel: defaults::MARKET_DATA_CHANNEL.to_string(),
            stream_id: defaults::MARKET_DATA_STREAM_ID,
            buffer_size: 64 * 1024, // 64KB
            linger_timeout_ns: defaults::LINGER_TIMEOUT_NS,
            reliable: true,
        });
        
        channels.insert("orders".to_string(), ChannelConfig {
            channel: defaults::ORDERS_CHANNEL.to_string(),
            stream_id: defaults::ORDERS_STREAM_ID,
            buffer_size: 32 * 1024, // 32KB
            linger_timeout_ns: defaults::LINGER_TIMEOUT_NS,
            reliable: true,
        });
        
        channels.insert("events".to_string(), ChannelConfig {
            channel: defaults::EVENTS_CHANNEL.to_string(),
            stream_id: defaults::EVENTS_STREAM_ID,
            buffer_size: 16 * 1024, // 16KB
            linger_timeout_ns: defaults::LINGER_TIMEOUT_NS,
            reliable: false, // Events can be fire-and-forget
        });
        
        Self {
            aeron: AeronConfig::default(),
            publisher: PublisherConfig::default(),
            subscriber: SubscriberConfig::default(),
            codec: CodecConfig::default(),
            channels,
            global: GlobalConfig::default(),
        }
    }
}

/// Channel configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChannelConfig {
    /// Aeron channel URI
    pub channel: String,
    /// Stream ID
    pub stream_id: i32,
    /// Buffer size in bytes
    pub buffer_size: usize,
    /// Linger timeout in nanoseconds
    pub linger_timeout_ns: u64,
    /// Reliable delivery
    pub reliable: bool,
}

/// Codec configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CodecConfig {
    /// Compression type
    pub compression_type: String,
    /// Encryption enabled
    pub encryption_enabled: bool,
    /// Encryption key (base64 encoded)
    pub encryption_key: Option<String>,
    /// Message validation enabled
    pub validation_enabled: bool,
    /// Schema registry URL
    pub schema_registry_url: Option<String>,
}

impl Default for CodecConfig {
    fn default() -> Self {
        Self {
            compression_type: "lz4".to_string(),
            encryption_enabled: false,
            encryption_key: None,
            validation_enabled: true,
            schema_registry_url: None,
        }
    }
}

/// Global configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GlobalConfig {
    /// Service name
    pub service_name: String,
    /// Service version
    pub service_version: String,
    /// Environment
    pub environment: String,
    /// Data center
    pub data_center: String,
    /// Metrics enabled
    pub metrics_enabled: bool,
    /// Tracing enabled
    pub tracing_enabled: bool,
    /// Health check enabled
    pub health_check_enabled: bool,
    /// Graceful shutdown timeout
    pub graceful_shutdown_timeout_ms: u64,
    /// Max concurrent connections
    pub max_connections: usize,
    /// Connection timeout
    pub connection_timeout_ms: u64,
}

impl Default for GlobalConfig {
    fn default() -> Self {
        Self {
            service_name: "market-intel-messaging".to_string(),
            service_version: "1.0.0".to_string(),
            environment: "development".to_string(),
            data_center: "local".to_string(),
            metrics_enabled: true,
            tracing_enabled: true,
            health_check_enabled: true,
            graceful_shutdown_timeout_ms: 30000, // 30 seconds
            max_connections: 1000,
            connection_timeout_ms: 5000, // 5 seconds
        }
    }
}

/// Configuration loader
pub struct ConfigLoader;

impl ConfigLoader {
    /// Load configuration from file
    pub fn load_from_file(path: &str) -> Result<AeronMessagingConfig> {
        let content = std::fs::read_to_string(path)
            .map_err(|e| MarketIntelError::configuration(format!("Failed to read config file: {}", e)))?;
        
        let config: AeronMessagingConfig = toml::from_str(&content)
            .map_err(|e| MarketIntelError::configuration(format!("Failed to parse config: {}", e)))?;
        
        // Validate configuration
        Self::validate_config(&config)?;
        
        Ok(config)
    }
    
    /// Load configuration from environment variables
    pub fn load_from_env() -> Result<AeronMessagingConfig> {
        let mut config = AeronMessagingConfig::default();
        
        // Override with environment variables
        if let Ok(aeron_dir) = std::env::var("AERON_DIR") {
            config.aeron.aeron_dir = aeron_dir;
        }
        
        if let Ok(service_name) = std::env::var("SERVICE_NAME") {
            config.global.service_name = service_name;
        }
        
        if let Ok(environment) = std::env::var("ENVIRONMENT") {
            config.global.environment = environment;
        }
        
        if let Ok(compression_type) = std::env::var("COMPRESSION_TYPE") {
            config.codec.compression_type = compression_type;
        }
        
        if let Ok(encryption_key) = std::env::var("ENCRYPTION_KEY") {
            config.codec.encryption_key = Some(encryption_key);
            config.codec.encryption_enabled = true;
        }
        
        // Validate configuration
        Self::validate_config(&config)?;
        
        Ok(config)
    }
    
    /// Load configuration with precedence (env > file > defaults)
    pub fn load_with_precedence(config_file: Option<&str>) -> Result<AeronMessagingConfig> {
        let mut config = if let Some(file) = config_file {
            Self::load_from_file(file)?
        } else {
            AeronMessagingConfig::default()
        };
        
        // Override with environment variables
        let env_config = Self::load_from_env()?;
        Self::merge_configs(&mut config, env_config);
        
        // Validate final configuration
        Self::validate_config(&config)?;
        
        Ok(config)
    }
    
    /// Merge configurations (env takes precedence)
    fn merge_configs(base: &mut AeronMessagingConfig, overlay: AeronMessagingConfig) {
        // Merge global config
        if overlay.global.service_name != GlobalConfig::default().service_name {
            base.global.service_name = overlay.global.service_name;
        }
        if overlay.global.environment != GlobalConfig::default().environment {
            base.global.environment = overlay.global.environment;
        }
        if overlay.global.data_center != GlobalConfig::default().data_center {
            base.global.data_center = overlay.global.data_center;
        }
        
        // Merge Aeron config
        if overlay.aeron.aeron_dir != AeronConfig::default().aeron_dir {
            base.aeron.aeron_dir = overlay.aeron.aeron_dir;
        }
        if overlay.aeron.embedded_media_driver != AeronConfig::default().embedded_media_driver {
            base.aeron.embedded_media_driver = overlay.aeron.embedded_media_driver;
        }
        
        // Merge codec config
        if overlay.codec.compression_type != CodecConfig::default().compression_type {
            base.codec.compression_type = overlay.codec.compression_type;
        }
        if overlay.codec.encryption_enabled != CodecConfig::default().encryption_enabled {
            base.codec.encryption_enabled = overlay.codec.encryption_enabled;
        }
        if overlay.codec.encryption_key.is_some() {
            base.codec.encryption_key = overlay.codec.encryption_key;
        }
        
        // Merge channels
        for (name, channel_config) in overlay.channels {
            base.channels.insert(name, channel_config);
        }
    }
    
    /// Validate configuration
    fn validate_config(config: &AeronMessagingConfig) -> Result<()> {
        // Validate Aeron directory
        if config.aeron.aeron_dir.is_empty() {
            return Err(MarketIntelError::configuration("Aeron directory cannot be empty"));
        }
        
        // Validate channels
        for (name, channel) in &config.channels {
            if channel.channel.is_empty() {
                return Err(MarketIntelError::configuration(format!("Channel {} has empty channel URI", name)));
            }
            
            if channel.stream_id <= 0 {
                return Err(MarketIntelError::configuration(format!("Channel {} has invalid stream ID", name)));
            }
            
            if channel.buffer_size == 0 {
                return Err(MarketIntelError::configuration(format!("Channel {} has invalid buffer size", name)));
            }
        }
        
        // Validate compression type
        match config.codec.compression_type.as_str() {
            "none" | "lz4" | "zstd" | "gzip" => {},
            _ => return Err(MarketIntelError::configuration(format!("Invalid compression type: {}", config.codec.compression_type))),
        }
        
        // Validate encryption key if enabled
        if config.codec.encryption_enabled && config.codec.encryption_key.is_none() {
            return Err(MarketIntelError::configuration("Encryption enabled but no key provided"));
        }
        
        // Validate global settings
        if config.global.service_name.is_empty() {
            return Err(MarketIntelError::configuration("Service name cannot be empty"));
        }
        
        if config.global.max_connections == 0 {
            return Err(MarketIntelError::configuration("Max connections must be greater than 0"));
        }
        
        Ok(())
    }
    
    /// Save configuration to file
    pub fn save_to_file(config: &AeronMessagingConfig, path: &str) -> Result<()> {
        let content = toml::to_string_pretty(config)
            .map_err(|e| MarketIntelError::configuration(format!("Failed to serialize config: {}", e)))?;
        
        std::fs::write(path, content)
            .map_err(|e| MarketIntelError::configuration(format!("Failed to write config file: {}", e)))?;
        
        Ok(())
    }
}

/// Configuration builder
pub struct ConfigBuilder {
    config: AeronMessagingConfig,
}

impl ConfigBuilder {
    /// Create new builder
    pub fn new() -> Self {
        Self {
            config: AeronMessagingConfig::default(),
        }
    }
    
    /// Set Aeron directory
    pub fn aeron_dir(mut self, dir: &str) -> Self {
        self.config.aeron.aeron_dir = dir.to_string();
        self
    }
    
    /// Set service name
    pub fn service_name(mut self, name: &str) -> Self {
        self.config.global.service_name = name.to_string();
        self
    }
    
    /// Set environment
    pub fn environment(mut self, env: &str) -> Self {
        self.config.global.environment = env.to_string();
        self
    }
    
    /// Set compression type
    pub fn compression_type(mut self, compression: &str) -> Self {
        self.config.codec.compression_type = compression.to_string();
        self
    }
    
    /// Set encryption key
    pub fn encryption_key(mut self, key: &str) -> Self {
        self.config.codec.encryption_key = Some(key.to_string());
        self.config.codec.encryption_enabled = true;
        self
    }
    
    /// Add channel
    pub fn add_channel(mut self, name: &str, channel: ChannelConfig) -> Self {
        self.config.channels.insert(name.to_string(), channel);
        self
    }
    
    /// Build configuration
    pub fn build(self) -> Result<AeronMessagingConfig> {
        ConfigLoader::validate_config(&self.config)?;
        Ok(self.config)
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
    /// Convert duration to nanoseconds
    pub fn duration_to_nanos(duration: Duration) -> u64 {
        duration.as_nanos() as u64
    }
    
    /// Convert nanoseconds to duration
    pub fn nanos_to_duration(nanos: u64) -> Duration {
        Duration::from_nanos(nanos)
    }
    
    /// Format bytes in human readable format
    pub fn format_bytes(bytes: u64) -> String {
        const UNITS: &[&str] = &["B", "KB", "MB", "GB", "TB"];
        const THRESHOLD: f64 = 1024.0;
        
        if bytes == 0 {
            return "0 B".to_string();
        }
        
        let bytes_f = bytes as f64;
        let unit_index = (bytes_f.log10() / THRESHOLD.log10()).floor() as usize;
        let unit_index = unit_index.min(UNITS.len() - 1);
        
        let size = bytes_f / THRESHOLD.powi(unit_index as i32);
        
        if unit_index == 0 {
            format!("{} {}", bytes, UNITS[unit_index])
        } else {
            format!("{:.2} {}", size, UNITS[unit_index])
        }
    }
    
    /// Format nanoseconds in human readable format
    pub fn format_nanos(nanos: u64) -> String {
        if nanos < 1_000 {
            format!("{} ns", nanos)
        } else if nanos < 1_000_000 {
            format!("{:.2} μs", nanos as f64 / 1_000.0)
        } else if nanos < 1_000_000_000 {
            format!("{:.2} ms", nanos as f64 / 1_000_000.0)
        } else {
            format!("{:.2} s", nanos as f64 / 1_000_000_000.0)
        }
    }
    
    /// Validate channel URI
    pub fn validate_channel_uri(uri: &str) -> Result<()> {
        if !uri.starts_with("aeron:") {
            return Err(MarketIntelError::configuration("Channel URI must start with 'aeron:'"));
        }
        
        // Basic validation for IPC channel
        if uri.starts_with("aeron:ipc") {
            return Ok(());
        }
        
        // Basic validation for UDP channel
        if uri.starts_with("aeron:udp") {
            if !uri.contains("endpoint=") {
                return Err(MarketIntelError::configuration("UDP channel must specify endpoint"));
            }
            return Ok(());
        }
        
        Err(MarketIntelError::configuration("Unsupported channel type"))
    }
    
    /// Generate default channel configuration
    pub fn default_channel_config(stream_id: i32, reliable: bool) -> ChannelConfig {
        ChannelConfig {
            channel: format!("aeron:ipc?term-length=64k|init-term-id=0|term-id={}", stream_id),
            stream_id,
            buffer_size: 64 * 1024, // 64KB
            linger_timeout_ns: defaults::LINGER_TIMEOUT_NS,
            reliable,
        }
    }
    
    /// Create high-performance channel configuration
    pub fn high_performance_channel_config(stream_id: i32) -> ChannelConfig {
        ChannelConfig {
            channel: format!("aeron:ipc?term-length=128k|init-term-id=0|term-id={}|sparse=true", stream_id),
            stream_id,
            buffer_size: 128 * 1024, // 128KB
            linger_timeout_ns: 1_000_000_000, // 1 second
            reliable: true,
        }
    }
    
    /// Create low-latency channel configuration
    pub fn low_latency_channel_config(stream_id: i32) -> ChannelConfig {
        ChannelConfig {
            channel: format!("aeron:ipc?term-length=32k|init-term-id=0|term-id={}|linger=0", stream_id),
            stream_id,
            buffer_size: 32 * 1024, // 32KB
            linger_timeout_ns: 100_000_000, // 100ms
            reliable: true,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_default_config() {
        let config = AeronMessagingConfig::default();
        assert_eq!(config.global.service_name, "market-intel-messaging");
        assert_eq!(config.channels.len(), 3);
        assert!(config.channels.contains_key("market_data"));
        assert!(config.channels.contains_key("orders"));
        assert!(config.channels.contains_key("events"));
    }
    
    #[test]
    fn test_config_builder() {
        let config = ConfigBuilder::new()
            .service_name("test-service")
            .environment("test")
            .compression_type("lz4")
            .build()
            .unwrap();
        
        assert_eq!(config.global.service_name, "test-service");
        assert_eq!(config.global.environment, "test");
        assert_eq!(config.codec.compression_type, "lz4");
    }
    
    #[test]
    fn test_config_validation() {
        let mut config = AeronMessagingConfig::default();
        
        // Test invalid Aeron directory
        config.aeron.aeron_dir = "".to_string();
        assert!(ConfigLoader::validate_config(&config).is_err());
        
        // Test invalid stream ID
        config.aeron.aeron_dir = "/tmp/aeron".to_string();
        let channel = config.channels.get_mut("market_data").unwrap();
        channel.stream_id = -1;
        assert!(ConfigLoader::validate_config(&config).is_err());
        
        // Test invalid compression type
        channel.stream_id = defaults::MARKET_DATA_STREAM_ID;
        config.codec.compression_type = "invalid".to_string();
        assert!(ConfigLoader::validate_config(&config).is_err());
    }
    
    #[test]
    fn test_config_utils() {
        assert_eq!(ConfigUtils::format_bytes(1024), "1 KB");
        assert_eq!(ConfigUtils::format_bytes(1_048_576), "1 MB");
        assert_eq!(ConfigUtils::format_nanos(1_000), "1 μs");
        assert_eq!(ConfigUtils::format_nanos(1_000_000), "1 ms");
        assert_eq!(ConfigUtils::format_nanos(1_000_000_000), "1 s");
    }
    
    #[test]
    fn test_channel_validation() {
        assert!(ConfigUtils::validate_channel_uri("aeron:ipc").is_ok());
        assert!(ConfigUtils::validate_channel_uri("aeron:udp?endpoint=224.0.0.1:40456").is_ok());
        assert!(ConfigUtils::validate_channel_uri("invalid:uri").is_err());
        assert!(ConfigUtils::validate_channel_uri("aeron:udp").is_err());
    }
    
    #[test]
    fn test_default_channel_configs() {
        let config = ConfigUtils::default_channel_config(1001, true);
        assert_eq!(config.stream_id, 1001);
        assert!(config.reliable);
        assert_eq!(config.buffer_size, 64 * 1024);
        
        let high_perf = ConfigUtils::high_performance_channel_config(2001);
        assert_eq!(high_perf.stream_id, 2001);
        assert_eq!(high_perf.buffer_size, 128 * 1024);
        
        let low_latency = ConfigUtils::low_latency_channel_config(3001);
        assert_eq!(low_latency.stream_id, 3001);
        assert_eq!(low_latency.buffer_size, 32 * 1024);
        assert_eq!(low_latency.linger_timeout_ns, 100_000_000);
    }
}
