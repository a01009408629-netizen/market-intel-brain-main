//! Core traits for the Market Intel Brain platform

use async_trait::async_trait;
use std::sync::Arc;
use crate::types::*;

/// Generic data provider trait
#[async_trait]
pub trait DataProvider: Send + Sync {
    /// Error type for the provider
    type Error: std::error::Error + Send + Sync + 'static;

    /// Get market data for a symbol
    async fn get_market_data(
        &self,
        symbol: &Symbol,
        data_type: MarketDataType,
    ) -> Result<Vec<MarketData>, Self::Error>;

    /// Subscribe to real-time data updates
    async fn subscribe(
        &self,
        symbol: &Symbol,
        data_type: MarketDataType,
    ) -> Result<Box<dyn MarketDataStream>, Self::Error>;

    /// Check if the provider is healthy
    async fn health_check(&self) -> Result<bool, Self::Error>;
}

/// Market data stream trait
#[async_trait]
pub trait MarketDataStream: Send + Sync {
    /// Error type for the stream
    type Error: std::error::Error + Send + Sync + 'static;

    /// Get the next data item from the stream
    async fn next(&mut self) -> Result<Option<MarketData>, Self::Error>;

    /// Close the stream
    async fn close(&mut self) -> Result<(), Self::Error>;
}

/// Trading engine trait
#[async_trait]
pub trait TradingEngine: Send + Sync {
    /// Error type for the trading engine
    type Error: std::error::Error + Send + Sync + 'static;

    /// Submit a new order
    async fn submit_order(&self, order: Order) -> Result<Order, Self::Error>;

    /// Cancel an existing order
    async fn cancel_order(&self, order_id: EntityId) -> Result<Order, Self::Error>;

    /// Get order status
    async fn get_order(&self, order_id: EntityId) -> Result<Option<Order>, Self::Error>;

    /// Get all orders for an account
    async fn get_orders(&self, account_id: EntityId) -> Result<Vec<Order>, Self::Error>;

    /// Get positions for an account
    async fn get_positions(&self, account_id: EntityId) -> Result<Vec<Position>, Self::Error>;

    /// Get account information
    async fn get_account(&self, account_id: EntityId) -> Result<Option<Account>, Self::Error>;
}

/// Risk management trait
#[async_trait]
pub trait RiskManager: Send + Sync {
    /// Error type for risk management
    type Error: std::error::Error + Send + Sync + 'static;

    /// Evaluate risk for an order
    async fn evaluate_order_risk(&self, order: &Order) -> Result<RiskMetrics, Self::Error>;

    /// Evaluate risk for a position
    async fn evaluate_position_risk(&self, position: &Position) -> Result<RiskMetrics, Self::Error>;

    /// Evaluate risk for an account
    async fn evaluate_account_risk(&self, account: &Account) -> Result<RiskMetrics, Self::Error>;

    /// Check if an order passes risk checks
    async fn check_order_limits(&self, order: &Order) -> Result<bool, Self::Error>;

    /// Update risk limits
    async fn update_risk_limits(
        &self,
        entity_id: EntityId,
        limits: HashMap<String, Decimal>,
    ) -> Result<(), Self::Error>;
}

/// Analytics engine trait
#[async_trait]
pub trait AnalyticsEngine: Send + Sync {
    /// Error type for analytics
    type Error: std::error::Error + Send + Sync + 'static;

    /// Calculate technical indicators
    async fn calculate_indicators(
        &self,
        symbol: &Symbol,
        data: &[MarketData],
        indicators: &[String],
    ) -> Result<HashMap<String, Vec<Decimal>>, Self::Error>;

    /// Calculate portfolio metrics
    async fn calculate_portfolio_metrics(
        &self,
        positions: &[Position],
        market_data: &[MarketData],
    ) -> Result<HashMap<String, Decimal>, Self::Error>;

    /// Run backtest
    async fn run_backtest(
        &self,
        strategy: &str,
        data: &[MarketData],
        config: HashMap<String, serde_json::Value>,
    ) -> Result<HashMap<String, serde_json::Value>, Self::Error>;

    /// Generate market analysis
    async fn generate_market_analysis(
        &self,
        symbols: &[Symbol],
        timeframe: &str,
    ) -> Result<HashMap<String, serde_json::Value>, Self::Error>;
}

/// Storage trait
#[async_trait]
pub trait Storage: Send + Sync {
    /// Error type for storage
    type Error: std::error::Error + Send + Sync + 'static;

    /// Store market data
    async fn store_market_data(&self, data: &[MarketData]) -> Result<(), Self::Error>;

    /// Retrieve market data
    async fn get_market_data(
        &self,
        symbol: &Symbol,
        start: Timestamp,
        end: Timestamp,
        data_type: MarketDataType,
    ) -> Result<Vec<MarketData>, Self::Error>;

    /// Store order
    async fn store_order(&self, order: &Order) -> Result<(), Self::Error>;

    /// Retrieve order
    async fn get_order(&self, order_id: EntityId) -> Result<Option<Order>, Self::Error>;

    /// Store trade
    async fn store_trade(&self, trade: &Trade) -> Result<(), Self::Error>;

    /// Retrieve trades
    async fn get_trades(
        &self,
        order_id: Option<EntityId>,
        symbol: Option<&Symbol>,
        start: Option<Timestamp>,
        end: Option<Timestamp>,
    ) -> Result<Vec<Trade>, Self::Error>;

    /// Store position
    async fn store_position(&self, position: &Position) -> Result<(), Self::Error>;

    /// Retrieve positions
    async fn get_positions(&self, account_id: EntityId) -> Result<Vec<Position>, Self::Error>;

    /// Store account
    async fn store_account(&self, account: &Account) -> Result<(), Self::Error>;

    /// Retrieve account
    async fn get_account(&self, account_id: EntityId) -> Result<Option<Account>, Self::Error>;
}

/// Configuration trait
pub trait Configuration: Send + Sync {
    /// Get configuration value
    fn get<T>(&self, key: &str) -> Result<T, Box<dyn std::error::Error>>
    where
        T: serde::de::DeserializeOwned;

    /// Set configuration value
    fn set<T>(&mut self, key: &str, value: T) -> Result<(), Box<dyn std::error::Error>>
    where
        T: serde::Serialize;

    /// Check if configuration key exists
    fn contains_key(&self, key: &str) -> bool;

    /// Get all configuration keys
    fn keys(&self) -> Vec<String>;
}

/// Event bus trait
#[async_trait]
pub trait EventBus: Send + Sync {
    /// Error type for event bus
    type Error: std::error::Error + Send + Sync + 'static;

    /// Publish an event
    async fn publish<T>(&self, event: T) -> Result<(), Self::Error>
    where
        T: serde::Serialize + Send + Sync;

    /// Subscribe to events
    async fn subscribe<T, F>(&self, handler: F) -> Result<(), Self::Error>
    where
        T: serde::de::DeserializeOwned + Send + Sync + 'static,
        F: Fn(T) -> Box<dyn std::future::Future<Output = ()> + Send> + Send + Sync + 'static;

    /// Unsubscribe from events
    async fn unsubscribe<T>(&self) -> Result<(), Self::Error>
    where
        T: serde::de::DeserializeOwned + Send + Sync + 'static;
}

/// Cache trait
#[async_trait]
pub trait Cache: Send + Sync {
    /// Error type for cache
    type Error: std::error::Error + Send + Sync + 'static;

    /// Get value from cache
    async fn get<T>(&self, key: &str) -> Result<Option<T>, Self::Error>
    where
        T: serde::de::DeserializeOwned;

    /// Set value in cache
    async fn set<T>(&self, key: &str, value: T, ttl: Option<u64>) -> Result<(), Self::Error>
    where
        T: serde::Serialize;

    /// Delete value from cache
    async fn delete(&self, key: &str) -> Result<bool, Self::Error>;

    /// Clear all cache
    async fn clear(&self) -> Result<(), Self::Error>;

    /// Check if key exists
    async fn exists(&self, key: &str) -> Result<bool, Self::Error>;
}

/// Logger trait
pub trait Logger: Send + Sync {
    /// Log debug message
    fn debug(&self, message: &str);

    /// Log info message
    fn info(&self, message: &str);

    /// Log warning message
    fn warn(&self, message: &str);

    /// Log error message
    fn error(&self, message: &str);

    /// Log with custom level
    fn log(&self, level: &str, message: &str);
}

/// Metrics trait
pub trait Metrics: Send + Sync {
    /// Increment a counter
    fn increment_counter(&self, name: &str, labels: Option<HashMap<String, String>>);

    /// Set a gauge value
    fn set_gauge(&self, name: &str, value: f64, labels: Option<HashMap<String, String>>);

    /// Record a histogram value
    fn record_histogram(&self, name: &str, value: f64, labels: Option<HashMap<String, String>>);

    /// Record a timer duration
    fn record_timer(&self, name: &str, duration: std::time::Duration, labels: Option<HashMap<String, String>>);
}

/// Service registry trait
pub trait ServiceRegistry: Send + Sync {
    /// Register a service
    fn register<T>(&mut self, name: &str, service: Arc<T>)
    where
        T: Send + Sync + 'static;

    /// Get a service
    fn get<T>(&self, name: &str) -> Result<Arc<T>, Box<dyn std::error::Error>>
    where
        T: Send + Sync + 'static;

    /// Check if service exists
    fn contains(&self, name: &str) -> bool;

    /// List all registered services
    fn list_services(&self) -> Vec<String>;
}

/// Health check trait
#[async_trait]
pub trait HealthCheck: Send + Sync {
    /// Error type for health check
    type Error: std::error::Error + Send + Sync + 'static;

    /// Check health of the component
    async fn check_health(&self) -> Result<HealthStatus, Self::Error>;

    /// Get component name
    fn name(&self) -> &str;

    /// Get component version
    fn version(&self) -> &str;
}

/// Health status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthStatus {
    /// Component name
    pub name: String,
    /// Component version
    pub version: String,
    /// Health status
    pub status: ComponentHealth,
    /// Last check timestamp
    pub timestamp: Timestamp,
    /// Additional details
    pub details: HashMap<String, serde_json::Value>,
}

/// Component health status
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum ComponentHealth {
    /// Component is healthy
    Healthy,
    /// Component is degraded but functioning
    Degraded,
    /// Component is unhealthy
    Unhealthy,
}
