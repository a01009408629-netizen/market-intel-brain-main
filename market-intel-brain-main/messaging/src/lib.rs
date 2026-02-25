//! Market Intel Brain - Ultra-Low Latency Messaging Layer
//! 
//! Aeron-based messaging system for high-frequency financial data
//! Provides microsecond-level latency between system components

pub mod aeron_client;
pub mod message_types;
pub mod publisher;
pub mod subscriber;
pub mod session;
pub mod codecs;
pub mod metrics;
pub mod config;

// Re-export commonly used items
pub use aeron_client::*;
pub use message_types::*;
pub use publisher::*;
pub use subscriber::*;
pub use session::*;
pub use codecs::*;
pub use metrics::*;
pub use config::*;

/// Library version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Default Aeron configuration
pub mod defaults {
    /// Default Aeron directory
    pub const AERON_DIR: &str = "/tmp/aeron";
    
    /// Default channel for market data
    pub const MARKET_DATA_CHANNEL: &str = "aeron:ipc?term-length=64k|init-term-id=0|term-id=0";
    
    /// Default channel for orders
    pub const ORDERS_CHANNEL: &str = "aeron:ipc?term-length=64k|init-term-id=1|term-id=1";
    
    /// Default channel for events
    pub const EVENTS_CHANNEL: &str = "aeron:ipc?term-length=64k|init-term-id=2|term-id=2";
    
    /// Default stream ID for market data
    pub const MARKET_DATA_STREAM_ID: i32 = 1001;
    
    /// Default stream ID for orders
    pub const ORDERS_STREAM_ID: i32 = 1002;
    
    /// Default stream ID for events
    pub const EVENTS_STREAM_ID: i32 = 1003;
    
    /// Default fragment size for batching
    pub const FRAGMENT_SIZE: i32 = 4096;
    
    /// Default linger timeout in nanoseconds
    pub const LINGER_TIMEOUT_NS: u64 = 5_000_000_000; // 5 seconds
    
    /// Default publication timeout in nanoseconds
    pub const PUBLICATION_TIMEOUT_NS: u64 = 10_000_000_000; // 10 seconds
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
        assert!(!defaults::AERON_DIR.is_empty());
        assert!(!defaults::MARKET_DATA_CHANNEL.is_empty());
        assert!(defaults::MARKET_DATA_STREAM_ID > 0);
    }
}
