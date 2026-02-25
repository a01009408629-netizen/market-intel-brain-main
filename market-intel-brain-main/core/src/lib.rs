//! Market Intel Brain - Core Library
//! 
//! This crate contains the core types, traits, and utilities that form the foundation
//! of the Market Intel Brain enterprise financial intelligence platform.

pub mod types;
pub mod traits;
pub mod errors;
pub mod utils;
pub mod events;

// Re-export commonly used items
pub use types::*;
pub use traits::*;
pub use errors::*;
pub use utils::*;
pub use events::*;

/// Core version information
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

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
