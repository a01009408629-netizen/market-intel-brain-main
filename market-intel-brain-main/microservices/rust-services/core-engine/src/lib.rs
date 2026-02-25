//! Core Engine Library
//! 
//! This library provides the Core Engine implementation with LMAX Disruptor
//! and gRPC service integration.

pub mod config;
pub mod core_engine_service;
pub mod data_ingestion;
pub mod proto;

// Re-export commonly used items
pub use config::*;
pub use core_engine_service::*;
pub use data_ingestion::*;

/// Core Engine version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
