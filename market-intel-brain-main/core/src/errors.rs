//! Error types for the Market Intel Brain platform

use thiserror::Error;
use crate::types::*;

/// Core error type for the Market Intel Brain platform
#[derive(Error, Debug)]
pub enum MarketIntelError {
    /// Configuration error
    #[error("Configuration error: {message}")]
    Configuration { message: String },

    /// Data provider error
    #[error("Data provider error: {provider} - {message}")]
    DataProvider { provider: String, message: String },

    /// Trading engine error
    #[error("Trading engine error: {message}")]
    TradingEngine { message: String },

    /// Risk management error
    #[error("Risk management error: {message}")]
    RiskManagement { message: String },

    /// Analytics error
    #[error("Analytics error: {message}")]
    Analytics { message: String },

    /// Storage error
    #[error("Storage error: {message}")]
    Storage { message: String },

    /// Network error
    #[error("Network error: {message}")]
    Network { message: String },

    /// Authentication error
    #[error("Authentication error: {message}")]
    Authentication { message: String },

    /// Authorization error
    #[error("Authorization error: {message}")]
    Authorization { message: String },

    /// Validation error
    #[error("Validation error: {field} - {message}")]
    Validation { field: String, message: String },

    /// Not found error
    #[error("Resource not found: {resource} with ID {id}")]
    NotFound { resource: String, id: String },

    /// Conflict error
    #[error("Conflict: {message}")]
    Conflict { message: String },

    /// Rate limit error
    #[error("Rate limit exceeded: {limit} requests per {period}")]
    RateLimit { limit: u32, period: String },

    /// Timeout error
    #[error("Operation timed out after {timeout_ms}ms")]
    Timeout { timeout_ms: u64 },

    /// Internal error
    #[error("Internal error: {message}")]
    Internal { message: String },

    /// External service error
    #[error("External service error: {service} - {message}")]
    ExternalService { service: String, message: String },

    /// Serialization error
    #[error("Serialization error: {message}")]
    Serialization { message: String },

    /// Deserialization error
    #[error("Deserialization error: {message}")]
    Deserialization { message: String },

    /// Database error
    #[error("Database error: {message}")]
    Database { message: String },

    /// Cache error
    #[error("Cache error: {message}")]
    Cache { message: String },

    /// Event bus error
    #[error("Event bus error: {message}")]
    EventBus { message: String },

    /// Metrics error
    #[error("Metrics error: {message}")]
    Metrics { message: String },

    /// Logging error
    #[error("Logging error: {message}")]
    Logging { message: String },

    /// Custom error
    #[error("{message}")]
    Custom { message: String },
}

impl MarketIntelError {
    /// Create a configuration error
    pub fn configuration(message: impl Into<String>) -> Self {
        Self::Configuration {
            message: message.into(),
        }
    }

    /// Create a data provider error
    pub fn data_provider(provider: impl Into<String>, message: impl Into<String>) -> Self {
        Self::DataProvider {
            provider: provider.into(),
            message: message.into(),
        }
    }

    /// Create a trading engine error
    pub fn trading_engine(message: impl Into<String>) -> Self {
        Self::TradingEngine {
            message: message.into(),
        }
    }

    /// Create a risk management error
    pub fn risk_management(message: impl Into<String>) -> Self {
        Self::RiskManagement {
            message: message.into(),
        }
    }

    /// Create an analytics error
    pub fn analytics(message: impl Into<String>) -> Self {
        Self::Analytics {
            message: message.into(),
        }
    }

    /// Create a storage error
    pub fn storage(message: impl Into<String>) -> Self {
        Self::Storage {
            message: message.into(),
        }
    }

    /// Create a network error
    pub fn network(message: impl Into<String>) -> Self {
        Self::Network {
            message: message.into(),
        }
    }

    /// Create an authentication error
    pub fn authentication(message: impl Into<String>) -> Self {
        Self::Authentication {
            message: message.into(),
        }
    }

    /// Create an authorization error
    pub fn authorization(message: impl Into<String>) -> Self {
        Self::Authorization {
            message: message.into(),
        }
    }

    /// Create a validation error
    pub fn validation(field: impl Into<String>, message: impl Into<String>) -> Self {
        Self::Validation {
            field: field.into(),
            message: message.into(),
        }
    }

    /// Create a not found error
    pub fn not_found(resource: impl Into<String>, id: impl Into<String>) -> Self {
        Self::NotFound {
            resource: resource.into(),
            id: id.into(),
        }
    }

    /// Create a conflict error
    pub fn conflict(message: impl Into<String>) -> Self {
        Self::Conflict {
            message: message.into(),
        }
    }

    /// Create a rate limit error
    pub fn rate_limit(limit: u32, period: impl Into<String>) -> Self {
        Self::RateLimit {
            limit,
            period: period.into(),
        }
    }

    /// Create a timeout error
    pub fn timeout(timeout_ms: u64) -> Self {
        Self::Timeout { timeout_ms }
    }

    /// Create an internal error
    pub fn internal(message: impl Into<String>) -> Self {
        Self::Internal {
            message: message.into(),
        }
    }

    /// Create an external service error
    pub fn external_service(service: impl Into<String>, message: impl Into<String>) -> Self {
        Self::ExternalService {
            service: service.into(),
            message: message.into(),
        }
    }

    /// Create a serialization error
    pub fn serialization(message: impl Into<String>) -> Self {
        Self::Serialization {
            message: message.into(),
        }
    }

    /// Create a deserialization error
    pub fn deserialization(message: impl Into<String>) -> Self {
        Self::Deserialization {
            message: message.into(),
        }
    }

    /// Create a database error
    pub fn database(message: impl Into<String>) -> Self {
        Self::Database {
            message: message.into(),
        }
    }

    /// Create a cache error
    pub fn cache(message: impl Into<String>) -> Self {
        Self::Cache {
            message: message.into(),
        }
    }

    /// Create an event bus error
    pub fn event_bus(message: impl Into<String>) -> Self {
        Self::EventBus {
            message: message.into(),
        }
    }

    /// Create a metrics error
    pub fn metrics(message: impl Into<String>) -> Self {
        Self::Metrics {
            message: message.into(),
        }
    }

    /// Create a logging error
    pub fn logging(message: impl Into<String>) -> Self {
        Self::Logging {
            message: message.into(),
        }
    }

    /// Create a custom error
    pub fn custom(message: impl Into<String>) -> Self {
        Self::Custom {
            message: message.into(),
        }
    }

    /// Get error code
    pub fn code(&self) -> &'static str {
        match self {
            Self::Configuration { .. } => "CONFIG_ERROR",
            Self::DataProvider { .. } => "DATA_PROVIDER_ERROR",
            Self::TradingEngine { .. } => "TRADING_ENGINE_ERROR",
            Self::RiskManagement { .. } => "RISK_MANAGEMENT_ERROR",
            Self::Analytics { .. } => "ANALYTICS_ERROR",
            Self::Storage { .. } => "STORAGE_ERROR",
            Self::Network { .. } => "NETWORK_ERROR",
            Self::Authentication { .. } => "AUTHENTICATION_ERROR",
            Self::Authorization { .. } => "AUTHORIZATION_ERROR",
            Self::Validation { .. } => "VALIDATION_ERROR",
            Self::NotFound { .. } => "NOT_FOUND",
            Self::Conflict { .. } => "CONFLICT",
            Self::RateLimit { .. } => "RATE_LIMIT",
            Self::Timeout { .. } => "TIMEOUT",
            Self::Internal { .. } => "INTERNAL_ERROR",
            Self::ExternalService { .. } => "EXTERNAL_SERVICE_ERROR",
            Self::Serialization { .. } => "SERIALIZATION_ERROR",
            Self::Deserialization { .. } => "DESERIALIZATION_ERROR",
            Self::Database { .. } => "DATABASE_ERROR",
            Self::Cache { .. } => "CACHE_ERROR",
            Self::EventBus { .. } => "EVENT_BUS_ERROR",
            Self::Metrics { .. } => "METRICS_ERROR",
            Self::Logging { .. } => "LOGGING_ERROR",
            Self::Custom { .. } => "CUSTOM_ERROR",
        }
    }

    /// Check if error is retryable
    pub fn is_retryable(&self) -> bool {
        matches!(
            self,
            Self::Network { .. }
                | Self::Timeout { .. }
                | Self::ExternalService { .. }
                | Self::Database { .. }
                | Self::Cache { .. }
                | Self::EventBus { .. }
        )
    }

    /// Check if error is client error (4xx)
    pub fn is_client_error(&self) -> bool {
        matches!(
            self,
            Self::Validation { .. }
                | Self::NotFound { .. }
                | Self::Conflict { .. }
                | Self::Authentication { .. }
                | Self::Authorization { .. }
                | Self::RateLimit { .. }
        )
    }

    /// Check if error is server error (5xx)
    pub fn is_server_error(&self) -> bool {
        !self.is_client_error()
    }
}

/// Result type alias for convenience
pub type Result<T> = std::result::Result<T, MarketIntelError>;

/// Convert from sqlx::Error to MarketIntelError
impl From<sqlx::Error> for MarketIntelError {
    fn from(err: sqlx::Error) -> Self {
        match err {
            sqlx::Error::Database(db_err) => {
                Self::database(format!("Database error: {}", db_err.message()))
            }
            sqlx::Error::PoolTimedOut => Self::timeout(30000),
            sqlx::Error::PoolClosed => Self::internal("Database pool is closed"),
            sqlx::Error::WorkerCrashed => Self::internal("Database worker crashed"),
            _ => Self::database(format!("Database error: {}", err)),
        }
    }
}

/// Convert from redis::RedisError to MarketIntelError
impl From<redis::RedisError> for MarketIntelError {
    fn from(err: redis::RedisError) -> Self {
        match err.kind() {
            redis::ErrorKind::IoError => Self::network(format!("Redis IO error: {}", err)),
            redis::ErrorKind::TypeError => Self::serialization(format!("Redis type error: {}", err)),
            redis::ErrorKind::ResponseError => Self::cache(format!("Redis response error: {}", err)),
            _ => Self::cache(format!("Redis error: {}", err)),
        }
    }
}

/// Convert from reqwest::Error to MarketIntelError
impl From<reqwest::Error> for MarketIntelError {
    fn from(err: reqwest::Error) -> Self {
        if err.is_timeout() {
            Self::timeout(30000)
        } else if err.is_connect() {
            Self::network(format!("Connection error: {}", err))
        } else if err.is_request() {
            Self::validation("request", format!("Request error: {}", err))
        } else {
            Self::network(format!("HTTP error: {}", err))
        }
    }
}

/// Convert from serde_json::Error to MarketIntelError
impl From<serde_json::Error> for MarketIntelError {
    fn from(err: serde_json::Error) -> Self {
        Self::serialization(format!("JSON serialization error: {}", err))
    }
}

/// Convert from bincode::Error to MarketIntelError
impl From<bincode::Error> for MarketIntelError {
    fn from(err: bincode::Error) -> Self {
        Self::serialization(format!("Bincode serialization error: {}", err))
    }
}

/// Convert from tokio::io::Error to MarketIntelError
impl From<tokio::io::Error> for MarketIntelError {
    fn from(err: tokio::io::Error) -> Self {
        if err.kind() == std::io::ErrorKind::TimedOut {
            Self::timeout(30000)
        } else {
            Self::network(format!("IO error: {}", err))
        }
    }
}

/// Convert from uuid::Error to MarketIntelError
impl From<uuid::Error> for MarketIntelError {
    fn from(err: uuid::Error) -> Self {
        Self::validation("uuid", format!("UUID error: {}", err))
    }
}

/// Convert from rust_decimal::Error to MarketIntelError
impl From<rust_decimal::Error> for MarketIntelError {
    fn from(err: rust_decimal::Error) -> Self {
        Self::validation("decimal", format!("Decimal error: {}", err))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_codes() {
        let err = MarketIntelError::configuration("test");
        assert_eq!(err.code(), "CONFIG_ERROR");
    }

    #[test]
    fn test_retryable_errors() {
        assert!(MarketIntelError::network("test").is_retryable());
        assert!(MarketIntelError::timeout(1000).is_retryable());
        assert!(!MarketIntelError::validation("test", "test").is_retryable());
    }

    #[test]
    fn test_client_server_errors() {
        assert!(MarketIntelError::validation("test", "test").is_client_error());
        assert!(MarketIntelError::not_found("test", "test").is_client_error());
        assert!(!MarketIntelError::network("test").is_client_error());
        assert!(MarketIntelError::network("test").is_server_error());
    }
}
