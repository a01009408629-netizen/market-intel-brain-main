//! Tracing configuration module

/// Tracing configuration for the Core Engine service
#[derive(Debug, Clone)]
pub struct TracingConfig {
    /// Service name for tracing
    pub service_name: String,
    /// Log level
    pub log_level: String,
    /// Whether to enable JSON logging
    pub json_logging: bool,
}

impl Default for TracingConfig {
    fn default() -> Self {
        Self {
            service_name: String::from("core-engine"),
            log_level: std::env::var("LOG_LEVEL").unwrap_or_else(|_| String::from("info")),
            json_logging: std::env::var("JSON_LOGGING")
                .map(|v| v == "true")
                .unwrap_or(false),
        }
    }
}

impl TracingConfig {
    /// Create a new TracingConfig from environment variables
    pub fn from_env() -> Self {
        Self::default()
    }
}
