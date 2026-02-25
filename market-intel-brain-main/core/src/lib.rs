//! Market Intel Brain - Core Engine
//! 
//! This crate provides the central processing engine with LMAX Disruptor architecture
//! for ultra-low latency, lock-free message processing.

pub mod disruptor;
pub mod core_engine;
pub mod types;
pub mod config;
pub mod traits;
pub mod errors;
pub mod utils;
pub mod events;

// Re-export commonly used items
pub use types::*;
pub use config::*;
pub use core_engine::*;
pub use disruptor::*;
pub use traits::*;
pub use errors::*;
pub use utils::*;
pub use events::*;

/// Core engine version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Default configuration
pub const DEFAULT_CONFIG: &str = include_str!("../config/default.toml");

/// Default configuration constants
pub mod constants {
    /// Default port for the API server
    pub const DEFAULT_API_PORT: u16 = 8080;
    
    /// Default Redis connection pool size
    pub const DEFAULT_REDIS_POOL_SIZE: u32 = 10;
    
    /// Default database connection pool size
    pub const DEFAULT_DB_POOL_SIZE: u32 = 20;
    
    /// Default request timeout in seconds
    pub const DEFAULT_REQUEST_TIMEOUT: u64 = 30;
    
    /// Default rate limit requests per minute
    pub const DEFAULT_RATE_LIMIT_RPM: u32 = 1000;
    
    /// Maximum batch size for data processing
    pub const MAX_BATCH_SIZE: usize = 10_000;
    
    /// Default cache TTL in seconds
    pub const DEFAULT_CACHE_TTL: u64 = 300;
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_version() {
        assert!(!VERSION.is_empty());
    }
}
