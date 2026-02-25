//! Core Engine Library
//! 
//! This library provides the Core Engine implementation with LMAX Disruptor
//! and gRPC service integration.

pub mod config;
pub mod core_engine_service;
pub mod data_ingestion;
pub mod proto;
pub mod otel;
pub mod metrics;
pub mod analytics;
pub mod vector_store;
pub mod execution_safety;

// Re-export commonly used items
pub use config::*;
pub use core_engine_service::*;
pub use data_ingestion::*;
pub use otel::*;
pub use metrics::*;
pub use analytics::*;
pub use vector_store::*;
pub use execution_safety::*;

/// Core Engine version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
