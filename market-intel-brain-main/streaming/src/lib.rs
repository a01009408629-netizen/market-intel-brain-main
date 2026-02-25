//! Market Intel Brain - Redpanda Streaming Layer
//! 
//! High-performance streaming system using Redpanda as Kafka alternative
//! Optimized for real-time financial data processing

pub mod redpanda_client;
pub mod producer;
pub mod consumer;
pub mod streams;
pub mod serde_types;
pub mod config;
pub mod metrics;
pub mod admin;

// Re-export commonly used items
pub use redpanda_client::*;
pub use producer::*;
pub use consumer::*;
pub use streams::*;
pub use serde_types::*;
pub use config::*;
pub use metrics::*;
pub use admin::*;

/// Library version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Default configuration constants
pub mod defaults {
    /// Default Redpanda bootstrap servers
    pub const BOOTSTRAP_SERVERS: &str = "localhost:9092";
    
    /// Default client ID prefix
    pub const CLIENT_ID_PREFIX: &str = "market-intel";
    
    /// Default group ID prefix
    pub const GROUP_ID_PREFIX: &str = "market-intel-group";
    
    /// Default session timeout in milliseconds
    pub const SESSION_TIMEOUT_MS: u64 = 30000;
    
    /// Default heartbeat interval in milliseconds
    pub const HEARTBEAT_INTERVAL_MS: u64 = 3000;
    
    /// Default max poll records
    pub const MAX_POLL_RECORDS: i32 = 1000;
    
    /// Default fetch max bytes
    pub const FETCH_MAX_BYTES: i32 = 1048576; // 1MB
    
    /// Default compression type
    pub const COMPRESSION_TYPE: &str = "lz4";
    
    /// Default acks
    pub const DEFAULT_ACKS: &str = "all";
    
    /// Default replication factor
    pub const REPLICATION_FACTOR: i32 = 3;
    
    /// Default partition count
    pub const PARTITION_COUNT: i32 = 3;
    
    /// Default retention in hours
    pub const RETENTION_HOURS: i32 = 24;
    
    /// Default segment size in MB
    pub const SEGMENT_SIZE_MB: i32 = 1024; // 1GB
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_version() {
        assert!(!VERSION.is_empty());
    }

    #[test]
    fn test_defaults() {
        assert!(!defaults::BOOTSTRAP_SERVERS.is_empty());
        assert!(!defaults::CLIENT_ID_PREFIX.is_empty());
        assert!(defaults::SESSION_TIMEOUT_MS > 0);
        assert!(defaults::MAX_POLL_RECORDS > 0);
    }
}
