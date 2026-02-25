//! Core types for Market Intel Brain platform

use chrono::{DateTime, Utc};
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use strum::{Display, EnumString};
use uuid::Uuid;

/// Unique identifier for any entity in system
pub type EntityId = Uuid;

/// Timestamp type
pub type Timestamp = DateTime<Utc>;

/// Price type with high precision
pub type Price = rust_decimal::Decimal;

/// Quantity type
pub type Quantity = rust_decimal::Decimal;

/// Symbol identifier
pub type Symbol = String;

/// Core message type for disruptor engine
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoreMessage {
    /// Unique message ID
    pub id: String,
    /// Message type
    pub message_type: MessageType,
    /// Message payload
    pub payload: MessagePayload,
    /// Source agent ID
    pub source: String,
    /// Destination agent ID (if applicable)
    pub destination: Option<String>,
    /// Message timestamp
    pub timestamp: DateTime<Utc>,
    /// Correlation ID for request/response tracking
    pub correlation_id: Option<String>,
    /// Causation ID for message causality tracking
    pub causation_id: Option<String>,
    /// Message priority
    pub priority: MessagePriority,
    /// Message version
    pub version: u32,
    /// Message metadata
    pub metadata: HashMap<String, String>,
    /// Processing flags
    pub flags: u32,
}

/// Message types for core engine
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum MessageType {
    /// Market data message
    MarketData = 1,
    /// Order message
    Order = 2,
    /// Trade message
    Trade = 3,
    /// Event message
    Event = 4,
    /// Control message
    Control = 5,
    /// Health check message
    HealthCheck = 6,
    /// Configuration message
    Configuration = 7,
    /// Security message
    Security = 8,
    /// Analytics message
    Analytics = 9,
    /// Storage message
    Storage = 10,
    /// Network message
    Network = 11,
    /// Risk management message
    RiskManagement = 12,
    /// Custom message type
    Custom(u32),
}

/// Message payload types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MessagePayload {
    /// Market data payload
    MarketData(MarketDataPayload),
    /// Order payload
    Order(OrderPayload),
    /// Trade payload
    Trade(TradePayload),
    /// Event payload
    Event(EventPayload),
    /// Control payload
    Control(ControlPayload),
    /// Health check payload
    HealthCheck(HealthCheckPayload),
    /// Configuration payload
    Configuration(ConfigurationPayload),
    /// Security payload
    Security(SecurityPayload),
    /// Analytics payload
    Analytics(AnalyticsPayload),
    /// Storage payload
    Storage(StoragePayload),
    /// Network payload
    Network(NetworkPayload),
    /// Risk management payload
    RiskManagement(RiskManagementPayload),
    /// Raw bytes payload
    Raw(Vec<u8>),
    /// JSON payload
    Json(serde_json::Value),
    /// Text payload
    Text(String),
}

/// Message priority levels
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum MessagePriority {
    /// Low priority
    Low = 1,
    /// Normal priority
    Normal = 2,
    /// High priority
    High = 3,
    /// Critical priority
    Critical = 4,
}

/// Processing result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessingResult {
    /// Result success flag
    pub success: bool,
    /// Result message
    pub message: String,
    /// Processing time in microseconds
    pub processing_time_us: u64,
    /// Result data
    pub data: Option<serde_json::Value>,
    /// Error details (if applicable)
    pub error: Option<String>,
}

/// Market data payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketDataPayload {
    /// Symbol identifier
    pub symbol: String,
    /// Last traded price
    pub last_price: f64,
    /// Bid price
    pub bid_price: f64,
    /// Ask price
    pub ask_price: f64,
    /// Bid size
    pub bid_size: u64,
    /// Ask size
    pub ask_size: u64,
    /// Volume
    pub volume: u64,
    /// Market data source
    pub source: String,
    /// Additional fields
    pub fields: HashMap<String, serde_json::Value>,
}

/// Order payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderPayload {
    /// Unique order ID
    pub order_id: String,
    /// Client order ID
    pub client_order_id: String,
    /// Symbol
    pub symbol: String,
    /// Order side
    pub side: String,
    /// Order type
    pub order_type: String,
    /// Quantity
    pub quantity: u64,
    /// Price (for limit orders)
    pub price: Option<f64>,
    /// Order status
    pub status: String,
    /// Client ID
    pub client_id: String,
}

/// Trade payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradePayload {
    /// Unique trade ID
    pub trade_id: String,
    /// Order ID
    pub order_id: String,
    /// Symbol
    pub symbol: String,
    /// Trade side
    pub side: String,
    /// Quantity
    pub quantity: u64,
    /// Price
    pub price: f64,
    /// Trade timestamp
    pub timestamp: DateTime<Utc>,
    /// Venue/exchange
    pub venue: String,
}

/// Event payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventPayload {
    /// Unique event ID
    pub event_id: String,
    /// Event type
    pub event_type: String,
    /// Event source
    pub source: String,
    /// Event severity
    pub severity: String,
    /// Event title
    pub title: String,
    /// Event message
    pub message: String,
    /// Event data
    pub data: HashMap<String, serde_json::Value>,
}

/// Control payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ControlPayload {
    /// Control command
    pub command: String,
    /// Target system/component
    pub target: String,
    /// Command parameters
    pub parameters: HashMap<String, serde_json::Value>,
    /// Request ID
    pub request_id: String,
}

/// Health check payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthCheckPayload {
    /// Component name
    pub component: String,
    /// Health status
    pub status: String,
    /// Status message
    pub message: String,
    /// Check timestamp
    pub timestamp: DateTime<Utc>,
}

/// Configuration payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigurationPayload {
    /// Configuration key
    pub key: String,
    /// Configuration value
    pub value: serde_json::Value,
    /// Configuration scope
    pub scope: String,
}

/// Security payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityPayload {
    /// Security event type
    pub event_type: String,
    /// User ID (if applicable)
    pub user_id: Option<String>,
    /// Resource being accessed
    pub resource: String,
    /// Action performed
    pub action: String,
    /// Result of the action
    pub result: String,
}

/// Analytics payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalyticsPayload {
    /// Analytics query or operation
    pub operation: String,
    /// Query parameters
    pub parameters: HashMap<String, serde_json::Value>,
    /// Result data
    pub result: Option<serde_json::Value>,
    /// Processing time in milliseconds
    pub processing_time_ms: u64,
}

/// Storage payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StoragePayload {
    /// Storage operation
    pub operation: String,
    /// Storage key or path
    pub key: String,
    /// Data being stored or retrieved
    pub data: Option<Vec<u8>>,
    /// Storage metadata
    pub metadata: HashMap<String, String>,
}

/// Network payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NetworkPayload {
    /// Network operation
    pub operation: String,
    /// Target endpoint
    pub endpoint: String,
    /// Request/response data
    pub data: Option<Vec<u8>>,
    /// Network protocol
    pub protocol: String,
}

/// Risk management payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskManagementPayload {
    /// Risk check type
    pub check_type: String,
    /// Entity being checked (order, position, etc.)
    pub entity: String,
    /// Risk parameters
    pub parameters: HashMap<String, serde_json::Value>,
    /// Risk result
    pub result: String,
}

impl CoreMessage {
    /// Create new core message
    pub fn new(
        message_type: MessageType,
        payload: MessagePayload,
        source: String,
    ) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            message_type,
            payload,
            source,
            destination: None,
            timestamp: Utc::now(),
            correlation_id: None,
            causation_id: None,
            priority: MessagePriority::Normal,
            version: 1,
            metadata: HashMap::new(),
            flags: 0,
        }
    }
    
    /// Set destination
    pub fn with_destination(mut self, destination: String) -> Self {
        self.destination = Some(destination);
        self
    }
    
    /// Set correlation ID
    pub fn with_correlation_id(mut self, correlation_id: String) -> Self {
        self.correlation_id = Some(correlation_id);
        self
    }
    
    /// Set causation ID
    pub fn with_causation_id(mut self, causation_id: String) -> Self {
        self.causation_id = Some(causation_id);
        self
    }
    
    /// Set priority
    pub fn with_priority(mut self, priority: MessagePriority) -> Self {
        self.priority = priority;
        self
    }
    
    /// Add metadata
    pub fn with_metadata(mut self, key: String, value: String) -> Self {
        self.metadata.insert(key, value);
        self
    }
    
    /// Set flag
    pub fn with_flag(mut self, flag: u32) -> Self {
        self.flags |= flag;
        self
    }
    
    /// Check if flag is set
    pub fn has_flag(&self, flag: u32) -> bool {
        (self.flags & flag) != 0
    }
    
    /// Get message size in bytes
    pub fn size(&self) -> usize {
        // Approximate size calculation
        std::mem::size_of::<Self>() + 
        self.id.len() + 
        self.source.len() + 
        self.destination.as_ref().map(|d| d.len()).unwrap_or(0) +
        self.correlation_id.as_ref().map(|c| c.len()).unwrap_or(0) +
        self.causation_id.as_ref().map(|c| c.len()).unwrap_or(0) +
        self.metadata.iter().map(|(k, v)| k.len() + v.len()).sum::<usize>()
    }
    
    /// Validate message
    pub fn validate(&self) -> Result<(), String> {
        if self.id.is_empty() {
            return Err("Message ID cannot be empty".to_string());
        }
        
        if self.source.is_empty() {
            return Err("Message source cannot be empty".to_string());
        }
        
        // Validate payload based on message type
        match (&self.message_type, &self.payload) {
            (MessageType::MarketData, MessagePayload::MarketData(_)) => Ok(()),
            (MessageType::Order, MessagePayload::Order(_)) => Ok(()),
            (MessageType::Trade, MessagePayload::Trade(_)) => Ok(()),
            (MessageType::Event, MessagePayload::Event(_)) => Ok(()),
            (MessageType::Control, MessagePayload::Control(_)) => Ok(()),
            (MessageType::HealthCheck, MessagePayload::HealthCheck(_)) => Ok(()),
            (MessageType::Configuration, MessagePayload::Configuration(_)) => Ok(()),
            (MessageType::Security, MessagePayload::Security(_)) => Ok(()),
            (MessageType::Analytics, MessagePayload::Analytics(_)) => Ok(()),
            (MessageType::Storage, MessagePayload::Storage(_)) => Ok(()),
            (MessageType::Network, MessagePayload::Network(_)) => Ok(()),
            (MessageType::RiskManagement, MessagePayload::RiskManagement(_)) => Ok(()),
            _ => Err("Message type and payload mismatch".to_string()),
        }
    }
}

impl Default for MessagePriority {
    fn default() -> Self {
        MessagePriority::Normal
    }
}

/// Market data types
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Display, EnumString)]
pub enum MarketDataType {
    /// Trade data (last price, volume)
    #[strum(serialize = "trade")]
    Trade,
    /// Quote data (bid/ask)
    #[strum(serialize = "quote")]
    Quote,
    /// Order book data
    #[strum(serialize = "orderbook")]
    OrderBook,
    /// Bar/candlestick data
    #[strum(serialize = "bar")]
    Bar,
    /// Tick data
    #[strum(serialize = "tick")]
    Tick,
}

/// Asset classes
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Display, EnumString)]
pub enum AssetClass {
    /// Equities/Stocks
    #[strum(serialize = "equity")]
    Equity,
    /// Foreign Exchange
    #[strum(serialize = "fx")]
    Forex,
    /// Cryptocurrencies
    #[strum(serialize = "crypto")]
    Crypto,
    /// Commodities
    #[strum(serialize = "commodity")]
    Commodity,
    /// Fixed Income/Bonds
    #[strum(serialize = "fixed_income")]
    FixedIncome,
    /// Derivatives/Options
    #[strum(serialize = "derivative")]
    Derivative,
}

/// Exchange identifiers
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Display, EnumString)]
pub enum Exchange {
    /// New York Stock Exchange
    #[strum(serialize = "NYSE")]
    NYSE,
    /// NASDAQ
    #[strum(serialize = "NASDAQ")]
    NASDAQ,
    /// London Stock Exchange
    #[strum(serialize = "LSE")]
    LSE,
    /// Tokyo Stock Exchange
    #[strum(serialize = "TSE")]
    TSE,
    /// Binance
    #[strum(serialize = "BINANCE")]
    Binance,
    /// Coinbase
    #[strum(serialize = "COINBASE")]
    Coinbase,
    /// Forex market
    #[strum(serialize = "FOREX")]
    Forex,
    /// Custom/Other exchange
    #[strum(serialize = "OTHER")]
    Other(String),
}

/// Side of an order or trade
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Display, EnumString)]
pub enum Side {
    /// Buy side
    #[strum(serialize = "buy")]
    Buy,
    /// Sell side
    #[strum(serialize = "sell")]
    Sell,
}

/// Order types
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Display, EnumString)]
pub enum OrderType {
    /// Market order
    #[strum(serialize = "market")]
    Market,
    /// Limit order
    #[strum(serialize = "limit")]
    Limit,
    /// Stop loss order
    #[strum(serialize = "stop_loss")]
    StopLoss,
    /// Stop limit order
    #[strum(serialize = "stop_limit")]
    StopLimit,
    /// Iceberg order
    #[strum(serialize = "iceberg")]
    Iceberg,
}

/// Order status
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Display, EnumString)]
pub enum OrderStatus {
    /// New order
    #[strum(serialize = "new")]
    New,
    /// Partially filled
    #[strum(serialize = "partially_filled")]
    PartiallyFilled,
    /// Fully filled
    #[strum(serialize = "filled")]
    Filled,
    /// Cancelled
    #[strum(serialize = "cancelled")]
    Cancelled,
    /// Rejected
    #[strum(serialize = "rejected")]
    Rejected,
    /// Expired
    #[strum(serialize = "expired")]
    Expired,
}

/// Risk levels
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Display, EnumString)]
pub enum RiskLevel {
    /// Low risk
    #[strum(serialize = "low")]
    Low,
    /// Medium risk
    #[strum(serialize = "medium")]
    Medium,
    /// High risk
    #[strum(serialize = "high")]
    High,
    /// Critical risk
    #[strum(serialize = "critical")]
    Critical,
}

/// Market data structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketData {
    /// Unique identifier
    pub id: EntityId,
    /// Symbol
    pub symbol: Symbol,
    /// Exchange
    pub exchange: Exchange,
    /// Data type
    pub data_type: MarketDataType,
    /// Asset class
    pub asset_class: AssetClass,
    /// Timestamp
    pub timestamp: Timestamp,
    /// Price (if applicable)
    pub price: Option<Price>,
    /// Quantity (if applicable)
    pub quantity: Option<Quantity>,
    /// Bid price (for quotes)
    pub bid_price: Option<Price>,
    /// Ask price (for quotes)
    pub ask_price: Option<Price>,
    /// Bid quantity (for quotes)
    pub bid_quantity: Option<Quantity>,
    /// Ask quantity (for quotes)
    pub ask_quantity: Option<Quantity>,
    /// Additional metadata
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Order structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Order {
    /// Unique identifier
    pub id: EntityId,
    /// Client order ID
    pub client_order_id: Option<String>,
    /// Symbol
    pub symbol: Symbol,
    /// Exchange
    pub exchange: Exchange,
    /// Side
    pub side: Side,
    /// Order type
    pub order_type: OrderType,
    /// Quantity
    pub quantity: Quantity,
    /// Price (for limit orders)
    pub price: Option<Price>,
    /// Stop price (for stop orders)
    pub stop_price: Option<Price>,
    /// Time in force
    pub time_in_force: Option<String>,
    /// Status
    pub status: OrderStatus,
    /// Created timestamp
    pub created_at: Timestamp,
    /// Updated timestamp
    pub updated_at: Timestamp,
    /// Filled quantity
    pub filled_quantity: Quantity,
    /// Average fill price
    pub avg_fill_price: Option<Price>,
    /// Additional metadata
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Trade structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Trade {
    /// Unique identifier
    pub id: EntityId,
    /// Order ID
    pub order_id: EntityId,
    /// Symbol
    pub symbol: Symbol,
    /// Exchange
    pub exchange: Exchange,
    /// Side
    pub side: Side,
    /// Quantity
    pub quantity: Quantity,
    /// Price
    pub price: Price,
    /// Trade timestamp
    pub timestamp: Timestamp,
    /// Trade ID from exchange
    pub exchange_trade_id: Option<String>,
    /// Fees
    pub fees: Option<Decimal>,
    /// Additional metadata
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Position structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    /// Unique identifier
    pub id: EntityId,
    /// Symbol
    pub symbol: Symbol,
    /// Exchange
    pub exchange: Exchange,
    /// Side
    pub side: Side,
    /// Quantity
    pub quantity: Quantity,
    /// Average price
    pub avg_price: Price,
    /// Market value
    pub market_value: Option<Decimal>,
    /// Unrealized PnL
    pub unrealized_pnl: Option<Decimal>,
    /// Realized PnL
    pub realized_pnl: Decimal,
    /// Last updated
    pub updated_at: Timestamp,
    /// Additional metadata
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Account structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Account {
    /// Unique identifier
    pub id: EntityId,
    /// Account name
    pub name: String,
    /// Account type
    pub account_type: String,
    /// Base currency
    pub base_currency: String,
    /// Total balance
    pub total_balance: Decimal,
    /// Available balance
    pub available_balance: Decimal,
    /// Margin used
    pub margin_used: Option<Decimal>,
    /// Margin available
    pub margin_available: Option<Decimal>,
    /// Total PnL
    pub total_pnl: Decimal,
    /// Positions
    pub positions: Vec<Position>,
    /// Created timestamp
    pub created_at: Timestamp,
    /// Updated timestamp
    pub updated_at: Timestamp,
    /// Additional metadata
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Risk metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskMetrics {
    /// Unique identifier
    pub id: EntityId,
    /// Entity ID (account, position, etc.)
    pub entity_id: EntityId,
    /// Risk level
    pub risk_level: RiskLevel,
    /// Value at Risk (VaR)
    pub var_1d: Option<Decimal>,
    /// Expected shortfall
    pub expected_shortfall: Option<Decimal>,
    /// Maximum drawdown
    pub max_drawdown: Option<Decimal>,
    /// Sharpe ratio
    pub sharpe_ratio: Option<Decimal>,
    /// Beta
    pub beta: Option<Decimal>,
    /// Volatility
    pub volatility: Option<Decimal>,
    /// Exposure limits
    pub exposure_limits: HashMap<String, Decimal>,
    /// Current exposure
    pub current_exposure: HashMap<String, Decimal>,
    /// Calculated timestamp
    pub calculated_at: Timestamp,
    /// Additional metadata
    pub metadata: HashMap<String, serde_json::Value>,
}

/// API response wrapper
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiResponse<T> {
    /// Success flag
    pub success: bool,
    /// Response data
    pub data: Option<T>,
    /// Error message
    pub error: Option<String>,
    /// Response timestamp
    pub timestamp: Timestamp,
    /// Request ID
    pub request_id: Option<String>,
}

impl<T> ApiResponse<T> {
    /// Create a successful response
    pub fn success(data: T) -> Self {
        Self {
            success: true,
            data: Some(data),
            error: None,
            timestamp: Utc::now(),
            request_id: None,
        }
    }

    /// Create an error response
    pub fn error(error: String) -> Self {
        Self {
            success: false,
            data: None,
            error: Some(error),
            timestamp: Utc::now(),
            request_id: None,
        }
    }

    /// Set request ID
    pub fn with_request_id(mut self, request_id: String) -> Self {
        self.request_id = Some(request_id);
        self
    }
}
