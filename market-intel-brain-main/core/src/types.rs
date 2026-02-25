//! Core types for the Market Intel Brain platform

use chrono::{DateTime, Utc};
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use strum::{Display, EnumString};
use uuid::Uuid;

/// Unique identifier for any entity in the system
pub type EntityId = Uuid;

/// Timestamp type
pub type Timestamp = DateTime<Utc>;

/// Price type with high precision
pub type Price = rust_decimal::Decimal;

/// Quantity type
pub type Quantity = rust_decimal::Decimal;

/// Symbol identifier
pub type Symbol = String;

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
