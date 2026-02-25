//! Message types for ultra-low latency messaging

use bytes::Buf;
use chrono::{DateTime, Utc};
use prost::{Message, Oneof};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

use crate::core::*;

/// Message header for all messages
#[derive(Debug, Clone, PartialEq, Message)]
pub struct MessageHeader {
    /// Message ID (UUID)
    #[prost(string, tag = "1")]
    pub message_id: String,
    
    /// Message type identifier
    #[prost(string, tag = "2")]
    pub message_type: String,
    
    /// Timestamp (nanoseconds since epoch)
    #[prost(uint64, tag = "3")]
    pub timestamp_ns: u64,
    
    /// Source identifier
    #[prost(string, tag = "4")]
    pub source: String,
    
    /// Correlation ID (for request/response)
    #[prost(string, optional, tag = "5")]
    pub correlation_id: Option<String>,
    
    /// Message version
    #[prost(uint32, tag = "6")]
    pub version: u32,
    
    /// Priority level
    #[prost(uint32, tag = "7")]
    pub priority: u32,
    
    /// Message flags
    #[prost(uint32, tag = "8")]
    pub flags: u32,
}

/// Market data message
#[derive(Debug, Clone, PartialEq, Message)]
pub struct MarketDataMessage {
    /// Message header
    #[prost(message, required, tag = "1")]
    pub header: MessageHeader,
    
    /// Symbol
    #[prost(string, required, tag = "2")]
    pub symbol: String,
    
    /// Exchange
    #[prost(string, required, tag = "3")]
    pub exchange: String,
    
    /// Data type
    #[prost(enumeration = "MarketDataType", required, tag = "4")]
    pub data_type: MarketDataType,
    
    /// Asset class
    #[prost(enumeration = "AssetClass", required, tag = "5")]
    pub asset_class: AssetClass,
    
    /// Price (scaled integer)
    #[prost(int64, tag = "6")]
    pub price: i64,
    
    /// Price scale (decimal places)
    #[prost(uint32, tag = "7")]
    pub price_scale: u32,
    
    /// Quantity (scaled integer)
    #[prost(int64, tag = "8")]
    pub quantity: i64,
    
    /// Quantity scale (decimal places)
    #[prost(uint32, tag = "9")]
    pub quantity_scale: u32,
    
    /// Bid price (scaled integer)
    #[prost(int64, optional, tag = "10")]
    pub bid_price: Option<i64>,
    
    /// Bid price scale
    #[prost(uint32, optional, tag = "11")]
    pub bid_price_scale: Option<u32>,
    
    /// Ask price (scaled integer)
    #[prost(int64, optional, tag = "12")]
    pub ask_price: Option<i64>,
    
    /// Ask price scale
    #[prost(uint32, optional, tag = "13")]
    pub ask_price_scale: Option<u32>,
    
    /// Bid quantity (scaled integer)
    #[prost(int64, optional, tag = "14")]
    pub bid_quantity: Option<i64>,
    
    /// Bid quantity scale
    #[prost(uint32, optional, tag = "15")]
    pub bid_quantity_scale: Option<u32>,
    
    /// Ask quantity (scaled integer)
    #[prost(int64, optional, tag = "16")]
    pub ask_quantity: Option<i64>,
    
    /// Ask quantity scale
    #[prost(uint32, optional, tag = "17")]
    pub ask_quantity_scale: Option<u32>,
    
    /// Sequence number
    #[prost(uint64, tag = "18")]
    pub sequence_number: u64,
    
    /// Additional metadata
    #[prost(map = "string, string", tag = "19")]
    pub metadata: HashMap<String, String>,
}

/// Order message
#[derive(Debug, Clone, PartialEq, Message)]
pub struct OrderMessage {
    /// Message header
    #[prost(message, required, tag = "1")]
    pub header: MessageHeader,
    
    /// Order ID
    #[prost(string, required, tag = "2")]
    pub order_id: String,
    
    /// Client order ID
    #[prost(string, optional, tag = "3")]
    pub client_order_id: Option<String>,
    
    /// Symbol
    #[prost(string, required, tag = "4")]
    pub symbol: String,
    
    /// Exchange
    #[prost(string, required, tag = "5")]
    pub exchange: String,
    
    /// Side
    #[prost(enumeration = "Side", required, tag = "6")]
    pub side: Side,
    
    /// Order type
    #[prost(enumeration = "OrderType", required, tag = "7")]
    pub order_type: OrderType,
    
    /// Quantity (scaled integer)
    #[prost(int64, required, tag = "8")]
    pub quantity: i64,
    
    /// Quantity scale
    #[prost(uint32, required, tag = "9")]
    pub quantity_scale: u32,
    
    /// Price (scaled integer)
    #[prost(int64, optional, tag = "10")]
    pub price: Option<i64>,
    
    /// Price scale
    #[prost(uint32, optional, tag = "11")]
    pub price_scale: Option<u32>,
    
    /// Stop price (scaled integer)
    #[prost(int64, optional, tag = "12")]
    pub stop_price: Option<i64>,
    
    /// Stop price scale
    #[prost(uint32, optional, tag = "13")]
    pub stop_price_scale: Option<u32>,
    
    /// Time in force
    #[prost(string, optional, tag = "14")]
    pub time_in_force: Option<String>,
    
    /// Order status
    #[prost(enumeration = "OrderStatus", required, tag = "15")]
    pub status: OrderStatus,
    
    /// Created timestamp (nanoseconds)
    #[prost(uint64, required, tag = "16")]
    pub created_at_ns: u64,
    
    /// Updated timestamp (nanoseconds)
    #[prost(uint64, required, tag = "17")]
    pub updated_at_ns: u64,
    
    /// Filled quantity (scaled integer)
    #[prost(int64, required, tag = "18")]
    pub filled_quantity: i64,
    
    /// Filled quantity scale
    #[prost(uint32, required, tag = "19")]
    pub filled_quantity_scale: u32,
    
    /// Average fill price (scaled integer)
    #[prost(int64, optional, tag = "20")]
    pub avg_fill_price: Option<i64>,
    
    /// Average fill price scale
    #[prost(uint32, optional, tag = "21")]
    pub avg_fill_price_scale: Option<u32>,
    
    /// Additional metadata
    #[prost(map = "string, string", tag = "22")]
    pub metadata: HashMap<String, String>,
}

/// Trade message
#[derive(Debug, Clone, PartialEq, Message)]
pub struct TradeMessage {
    /// Message header
    #[prost(message, required, tag = "1")]
    pub header: MessageHeader,
    
    /// Trade ID
    #[prost(string, required, tag = "2")]
    pub trade_id: String,
    
    /// Order ID
    #[prost(string, required, tag = "3")]
    pub order_id: String,
    
    /// Symbol
    #[prost(string, required, tag = "4")]
    pub symbol: String,
    
    /// Exchange
    #[prost(string, required, tag = "5")]
    pub exchange: String,
    
    /// Side
    #[prost(enumeration = "Side", required, tag = "6")]
    pub side: Side,
    
    /// Quantity (scaled integer)
    #[prost(int64, required, tag = "7")]
    pub quantity: i64,
    
    /// Quantity scale
    #[prost(uint32, required, tag = "8")]
    pub quantity_scale: u32,
    
    /// Price (scaled integer)
    #[prost(int64, required, tag = "9")]
    pub price: i64,
    
    /// Price scale
    #[prost(uint32, required, tag = "10")]
    pub price_scale: u32,
    
    /// Trade timestamp (nanoseconds)
    #[prost(uint64, required, tag = "11")]
    pub timestamp_ns: u64,
    
    /// Exchange trade ID
    #[prost(string, optional, tag = "12")]
    pub exchange_trade_id: Option<String>,
    
    /// Fees (scaled integer)
    #[prost(int64, optional, tag = "13")]
    pub fees: Option<i64>,
    
    /// Fees scale
    #[prost(uint32, optional, tag = "14")]
    pub fees_scale: Option<u32>,
    
    /// Additional metadata
    #[prost(map = "string, string", tag = "15")]
    pub metadata: HashMap<String, String>,
}

/// Event message
#[derive(Debug, Clone, PartialEq, Message)]
pub struct EventMessage {
    /// Message header
    #[prost(message, required, tag = "1")]
    pub header: MessageHeader,
    
    /// Event data (JSON serialized)
    #[prost(string, required, tag = "2")]
    pub event_data: String,
    
    /// Event version
    #[prost(uint32, required, tag = "3")]
    pub event_version: u32,
    
    /// Event schema
    #[prost(string, required, tag = "4")]
    pub event_schema: String,
    
    /// Additional metadata
    #[prost(map = "string, string", tag = "5")]
    pub metadata: HashMap<String, String>,
}

/// Control message
#[derive(Debug, Clone, PartialEq, Message)]
pub struct ControlMessage {
    /// Message header
    #[prost(message, required, tag = "1")]
    pub header: MessageHeader,
    
    /// Control command
    #[prost(enumeration = "ControlCommand", required, tag = "2")]
    pub command: ControlCommand,
    
    /// Command parameters
    #[prost(map = "string, string", tag = "3")]
    pub parameters: HashMap<String, String>,
    
    /// Target component
    #[prost(string, optional, tag = "4")]
    pub target: Option<String>,
    
    /// Request ID (for command-response)
    #[prost(string, optional, tag = "5")]
    pub request_id: Option<String>,
}

/// Unified message wrapper
#[derive(Debug, Clone, PartialEq, Message)]
pub struct UnifiedMessage {
    /// Message header
    #[prost(message, required, tag = "1")]
    pub header: MessageHeader,
    
    /// Message payload
    #[prost(oneof = "MessagePayload", tags = "2, 3, 4, 5, 6")]
    pub payload: Option<MessagePayload>,
}

/// Message payload types
#[derive(Debug, Clone, PartialEq, Oneof)]
pub enum MessagePayload {
    /// Market data
    #[prost(message, tag = "2")]
    MarketData(MarketDataMessage),
    
    /// Order
    #[prost(message, tag = "3")]
    Order(OrderMessage),
    
    /// Trade
    #[prost(message, tag = "4")]
    Trade(TradeMessage),
    
    /// Event
    #[prost(message, tag = "5")]
    Event(EventMessage),
    
    /// Control
    #[prost(message, tag = "6")]
    Control(ControlMessage),
}

/// Market data types
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Enumeration)]
pub enum MarketDataType {
    /// Trade data
    Trade = 0,
    /// Quote data
    Quote = 1,
    /// Order book data
    OrderBook = 2,
    /// Bar/candlestick data
    Bar = 3,
    /// Tick data
    Tick = 4,
}

/// Asset classes
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Enumeration)]
pub enum AssetClass {
    /// Equities
    Equity = 0,
    /// Foreign Exchange
    Forex = 1,
    /// Cryptocurrencies
    Crypto = 2,
    /// Commodities
    Commodity = 3,
    /// Fixed Income
    FixedIncome = 4,
    /// Derivatives
    Derivative = 5,
}

/// Order sides
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Enumeration)]
pub enum Side {
    /// Buy
    Buy = 0,
    /// Sell
    Sell = 1,
}

/// Order types
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Enumeration)]
pub enum OrderType {
    /// Market order
    Market = 0,
    /// Limit order
    Limit = 1,
    /// Stop loss order
    StopLoss = 2,
    /// Stop limit order
    StopLimit = 3,
    /// Iceberg order
    Iceberg = 4,
}

/// Order statuses
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Enumeration)]
pub enum OrderStatus {
    /// New order
    New = 0,
    /// Partially filled
    PartiallyFilled = 1,
    /// Fully filled
    Filled = 2,
    /// Cancelled
    Cancelled = 3,
    /// Rejected
    Rejected = 4,
    /// Expired
    Expired = 5,
}

/// Control commands
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Enumeration)]
pub enum ControlCommand {
    /// Start component
    Start = 0,
    /// Stop component
    Stop = 1,
    /// Restart component
    Restart = 2,
    /// Configure component
    Configure = 3,
    /// Health check
    HealthCheck = 4,
    /// Reset state
    Reset = 5,
    /// Shutdown system
    Shutdown = 6,
}

/// Message priority levels
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum MessagePriority {
    /// Critical (highest priority)
    Critical = 0,
    /// High priority
    High = 1,
    /// Normal priority
    Normal = 2,
    /// Low priority
    Low = 3,
    /// Background (lowest priority)
    Background = 4,
}

impl MessagePriority {
    /// Convert to u32
    pub fn as_u32(self) -> u32 {
        self as u32
    }
    
    /// Convert from u32
    pub fn from_u32(value: u32) -> Self {
        match value {
            0 => MessagePriority::Critical,
            1 => MessagePriority::High,
            2 => MessagePriority::Normal,
            3 => MessagePriority::Low,
            4 => MessagePriority::Background,
            _ => MessagePriority::Normal,
        }
    }
}

/// Message flags
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct MessageFlags {
    pub flags: u32,
}

impl MessageFlags {
    /// Create new flags
    pub fn new() -> Self {
        Self { flags: 0 }
    }
    
    /// Set flag
    pub fn set(&mut self, flag: u32) {
        self.flags |= flag;
    }
    
    /// Check if flag is set
    pub fn is_set(&self, flag: u32) -> bool {
        (self.flags & flag) != 0
    }
    
    /// Clear flag
    pub fn clear(&mut self, flag: u32) {
        self.flags &= !flag;
    }
}

/// Message flag constants
pub mod message_flags {
    /// Message is a replay
    pub const REPLAY: u32 = 0x01;
    /// Message is compressed
    pub const COMPRESSED: u32 = 0x02;
    /// Message is encrypted
    pub const ENCRYPTED: u32 = 0x04;
    /// Message is batched
    pub const BATCHED: u32 = 0x08;
    /// Message requires acknowledgment
    pub const REQUIRES_ACK: u32 = 0x10;
    /// Message is a heartbeat
    pub const HEARTBEAT: u32 = 0x20;
}

/// Utility functions for message handling
pub mod utils {
    use super::*;
    use chrono::TimeZone;
    
    /// Generate message ID
    pub fn generate_message_id() -> String {
        Uuid::new_v4().to_string()
    }
    
    /// Get current timestamp in nanoseconds
    pub fn current_timestamp_ns() -> u64 {
        Utc::now().timestamp_nanos_opt().unwrap_or(0) as u64
    }
    
    /// Convert timestamp to DateTime
    pub fn timestamp_to_datetime(timestamp_ns: u64) -> DateTime<Utc> {
        let timestamp_s = timestamp_ns as i64 / 1_000_000_000;
        let timestamp_ns_rem = timestamp_ns as i64 % 1_000_000_000;
        Utc.timestamp_opt(timestamp_s, timestamp_ns_rem as u32 * 1_000_000_000)
            .single()
            .unwrap_or_else(Utc::now)
    }
    
    /// Convert DateTime to timestamp
    pub fn datetime_to_timestamp(dt: DateTime<Utc>) -> u64 {
        dt.timestamp_nanos_opt().unwrap_or(0) as u64
    }
    
    /// Scale decimal to integer
    pub fn scale_decimal(value: f64, scale: u32) -> i64 {
        let multiplier = 10_f64.powi(scale as i32);
        (value * multiplier).round() as i64
    }
    
    /// Unscale integer to decimal
    pub fn unscale_decimal(value: i64, scale: u32) -> f64 {
        let divisor = 10_f64.powi(scale as i32);
        value as f64 / divisor
    }
    
    /// Create message header
    pub fn create_header(
        message_type: &str,
        source: &str,
        priority: MessagePriority,
    ) -> MessageHeader {
        MessageHeader {
            message_id: generate_message_id(),
            message_type: message_type.to_string(),
            timestamp_ns: current_timestamp_ns(),
            source: source.to_string(),
            correlation_id: None,
            version: 1,
            priority: priority.as_u32(),
            flags: 0,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use super::utils::*;
    
    #[test]
    fn test_message_id_generation() {
        let id1 = generate_message_id();
        let id2 = generate_message_id();
        assert_ne!(id1, id2);
        assert_eq!(id1.len(), 36); // UUID length
    }
    
    #[test]
    fn test_timestamp_conversion() {
        let now = Utc::now();
        let timestamp_ns = datetime_to_timestamp(now);
        let converted = timestamp_to_datetime(timestamp_ns);
        
        // Allow small difference due to rounding
        let diff = (now - converted).num_milliseconds().abs();
        assert!(diff < 1000);
    }
    
    #[test]
    fn test_decimal_scaling() {
        let value = 123.456;
        let scale = 3;
        let scaled = scale_decimal(value, scale);
        let unscaled = unscale_decimal(scaled, scale);
        
        assert!((value - unscaled).abs() < 0.001);
    }
    
    #[test]
    fn test_message_flags() {
        let mut flags = MessageFlags::new();
        assert!(!flags.is_set(message_flags::REPLAY));
        
        flags.set(message_flags::REPLAY);
        assert!(flags.is_set(message_flags::REPLAY));
        
        flags.clear(message_flags::REPLAY);
        assert!(!flags.is_set(message_flags::REPLAY));
    }
    
    #[test]
    fn test_message_priority() {
        let priority = MessagePriority::High;
        assert_eq!(priority.as_u32(), 1);
        assert_eq!(MessagePriority::from_u32(1), MessagePriority::High);
        assert_eq!(MessagePriority::from_u32(99), MessagePriority::Normal);
    }
}
