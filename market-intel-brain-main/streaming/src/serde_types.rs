//! Serde serialization types for Redpanda streaming
//! 
//! This module provides serialization and deserialization support
//! for various message types using serde for JSON and binary formats.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use chrono::{DateTime, Utc};
use crate::config::DEFAULT_TOPIC_PREFIX;

/// Serializable market data message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SerializableMarketData {
    /// Unique symbol identifier
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
    /// Timestamp
    pub timestamp: DateTime<Utc>,
    /// Market data source
    pub source: String,
    /// Additional fields
    pub fields: HashMap<String, serde_json::Value>,
}

/// Serializable order message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SerializableOrder {
    /// Unique order ID
    pub order_id: String,
    /// Client order ID
    pub client_order_id: String,
    /// Symbol
    pub symbol: String,
    /// Order side
    pub side: String, // "BUY" or "SELL"
    /// Order type
    pub order_type: String, // "MARKET", "LIMIT", "STOP", etc.
    /// Quantity
    pub quantity: u64,
    /// Price (for limit orders)
    pub price: Option<f64>,
    /// Stop price (for stop orders)
    pub stop_price: Option<f64>,
    /// Order status
    pub status: String, // "NEW", "PARTIALLY_FILLED", "FILLED", "CANCELED", etc.
    /// Filled quantity
    pub filled_quantity: u64,
    /// Average fill price
    pub avg_fill_price: Option<f64>,
    /// Timestamp
    pub timestamp: DateTime<Utc>,
    /// Client ID
    pub client_id: String,
    /// Additional fields
    pub fields: HashMap<String, serde_json::Value>,
}

/// Serializable trade message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SerializableTrade {
    /// Unique trade ID
    pub trade_id: String,
    /// Order ID
    pub order_id: String,
    /// Symbol
    pub symbol: String,
    /// Trade side
    pub side: String, // "BUY" or "SELL"
    /// Quantity
    pub quantity: u64,
    /// Price
    pub price: f64,
    /// Trade timestamp
    pub timestamp: DateTime<Utc>,
    /// Venue/exchange
    pub venue: String,
    /// Fee
    pub fee: Option<f64>,
    /// Fee currency
    pub fee_currency: Option<String>,
    /// Additional fields
    pub fields: HashMap<String, serde_json::Value>,
}

/// Serializable event message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SerializableEvent {
    /// Unique event ID
    pub event_id: String,
    /// Event type
    pub event_type: String,
    /// Event source
    pub source: String,
    /// Event severity
    pub severity: String, // "INFO", "WARNING", "ERROR", "CRITICAL"
    /// Event title
    pub title: String,
    /// Event message
    pub message: String,
    /// Timestamp
    pub timestamp: DateTime<Utc>,
    /// Event data
    pub data: HashMap<String, serde_json::Value>,
    /// Correlation ID
    pub correlation_id: Option<String>,
    /// Causation ID
    pub causation_id: Option<String>,
}

/// Serializable control message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SerializableControlMessage {
    /// Control message type
    pub control_type: String,
    /// Target system/component
    pub target: String,
    /// Command
    pub command: String,
    /// Parameters
    pub parameters: HashMap<String, serde_json::Value>,
    /// Timestamp
    pub timestamp: DateTime<Utc>,
    /// Request ID
    pub request_id: String,
    /// Expected response type
    pub response_type: Option<String>,
}

/// Generic envelope for all message types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessageEnvelope {
    /// Message type identifier
    pub message_type: String,
    /// Schema version
    pub schema_version: String,
    /// Message ID
    pub message_id: String,
    /// Correlation ID
    pub correlation_id: Option<String>,
    /// Causation ID
    pub causation_id: Option<String>,
    /// Source system
    pub source: String,
    /// Destination system (if applicable)
    pub destination: Option<String>,
    /// Timestamp
    pub timestamp: DateTime<Utc>,
    /// Message payload
    pub payload: serde_json::Value,
    /// Message metadata
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Batch message container
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BatchMessage {
    /// Batch ID
    pub batch_id: String,
    /// Messages in batch
    pub messages: Vec<MessageEnvelope>,
    /// Batch timestamp
    pub timestamp: DateTime<Utc>,
    /// Batch size
    pub batch_size: usize,
    /// Compression type used
    pub compression_type: Option<String>,
    /// Batch metadata
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Stream processing result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StreamResult {
    /// Result ID
    pub result_id: String,
    /// Stream ID
    pub stream_id: String,
    /// Processing status
    pub status: String, // "SUCCESS", "ERROR", "PARTIAL"
    /// Input message count
    pub input_count: usize,
    /// Output message count
    pub output_count: usize,
    /// Error count
    pub error_count: usize,
    /// Processing timestamp
    pub timestamp: DateTime<Utc>,
    /// Processing duration in milliseconds
    pub duration_ms: u64,
    /// Result data
    pub data: HashMap<String, serde_json::Value>,
    /// Errors (if any)
    pub errors: Vec<String>,
}

/// Topic configuration for serialization
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TopicConfig {
    /// Topic name
    pub topic_name: String,
    /// Number of partitions
    pub partitions: i32,
    /// Replication factor
    pub replication_factor: i32,
    /// Retention time in milliseconds
    pub retention_ms: Option<i64>,
    /// Maximum message size in bytes
    pub max_message_bytes: Option<i32>,
    /// Cleanup policy
    pub cleanup_policy: Option<String>, // "delete", "compact", "compact,delete"
    /// Compression type
    pub compression_type: Option<String>, // "none", "gzip", "snappy", "lz4", "zstd"
    /// Topic type
    pub topic_type: String, // "market_data", "orders", "trades", "events", "control"
    /// Schema registry information
    pub schema_info: Option<SchemaInfo>,
    /// Additional configuration
    pub config: HashMap<String, String>,
}

/// Schema registry information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SchemaInfo {
    /// Schema ID
    pub schema_id: String,
    /// Schema version
    pub version: String,
    /// Schema type (avro, json, protobuf)
    pub schema_type: String,
    /// Schema definition
    pub schema_definition: String,
    /// Compatibility level
    pub compatibility_level: String, // "NONE", "BACKWARD", "FORWARD", "FULL", "NONE"
}

/// Consumer group configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConsumerGroupConfig {
    /// Group ID
    pub group_id: String,
    /// Topics to consume
    pub topics: Vec<String>,
    /// Consumer instance ID
    pub instance_id: Option<String>,
    /// Auto offset reset policy
    pub auto_offset_reset: String, // "earliest", "latest", "none"
    /// Enable auto commit
    pub enable_auto_commit: bool,
    /// Auto commit interval in milliseconds
    pub auto_commit_interval_ms: i32,
    /// Session timeout in milliseconds
    pub session_timeout_ms: i32,
    /// Heartbeat interval in milliseconds
    pub heartbeat_interval_ms: i32,
    /// Max poll records
    pub max_poll_records: i32,
    /// Max poll interval in milliseconds
    pub max_poll_interval_ms: i32,
    /// Additional configuration
    pub config: HashMap<String, String>,
}

/// Producer configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProducerConfig {
    /// Producer ID
    pub producer_id: String,
    /// Default topic prefix
    pub topic_prefix: String,
    /// Transactional ID (for exactly-once semantics)
    pub transactional_id: Option<String>,
    /// Delivery timeout in milliseconds
    pub delivery_timeout_ms: i32,
    /// Request timeout in milliseconds
    pub request_timeout_ms: i32,
    /// Max in-flight requests
    pub max_in_flight_requests: i32,
    /// Enable idempotence
    pub enable_idempotence: bool,
    /// Compression type
    pub compression_type: String,
    /// Batch size in bytes
    pub batch_size: i32,
    /// Linger time in milliseconds
    pub linger_ms: i32,
    /// Additional configuration
    pub config: HashMap<String, String>,
}

/// Stream processing configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StreamConfig {
    /// Stream ID
    pub stream_id: String,
    /// Stream name
    pub stream_name: String,
    /// Input topics
    pub input_topics: Vec<String>,
    /// Output topics
    pub output_topics: Vec<String>,
    /// Processing function type
    pub processing_type: String, // "filter", "map", "reduce", "join", "window"
    /// Processing parameters
    pub processing_params: HashMap<String, serde_json::Value>,
    /// Window size (for windowed operations)
    pub window_size_ms: Option<u64>,
    /// Watermark strategy
    pub watermark_strategy: Option<String>,
    /// Checkpoint configuration
    pub checkpoint_config: Option<CheckpointConfig>,
    /// Additional configuration
    pub config: HashMap<String, serde_json::Value>,
}

/// Checkpoint configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CheckpointConfig {
    /// Checkpoint interval in milliseconds
    pub interval_ms: u64,
    /// Checkpoint storage location
    pub storage_location: String,
    /// Checkpoint retention policy
    pub retention_policy: String,
    /// Enable exactly-once processing
    pub exactly_once: bool,
}

impl MessageEnvelope {
    /// Create a new message envelope
    pub fn new(
        message_type: String,
        message_id: String,
        payload: serde_json::Value,
        source: String,
    ) -> Self {
        Self {
            message_type,
            schema_version: "1.0".to_string(),
            message_id,
            correlation_id: None,
            causation_id: None,
            source,
            destination: None,
            timestamp: Utc::now(),
            payload,
            metadata: HashMap::new(),
        }
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

    /// Set destination
    pub fn with_destination(mut self, destination: String) -> Self {
        self.destination = Some(destination);
        self
    }

    /// Add metadata
    pub fn with_metadata(mut self, key: String, value: serde_json::Value) -> Self {
        self.metadata.insert(key, value);
        self
    }

    /// Get topic name based on message type and prefix
    pub fn topic_name(&self, prefix: Option<&str>) -> String {
        let prefix = prefix.unwrap_or(DEFAULT_TOPIC_PREFIX);
        match self.message_type.as_str() {
            "market_data" => format!("{}.market_data", prefix),
            "order" => format!("{}.orders", prefix),
            "trade" => format!("{}.trades", prefix),
            "event" => format!("{}.events", prefix),
            "control" => format!("{}.control", prefix),
            _ => format!("{}.unknown", prefix),
        }
    }
}

impl BatchMessage {
    /// Create a new batch message
    pub fn new(messages: Vec<MessageEnvelope>) -> Self {
        let batch_size = messages.len();
        Self {
            batch_id: uuid::Uuid::new_v4().to_string(),
            messages,
            timestamp: Utc::now(),
            batch_size,
            compression_type: None,
            metadata: HashMap::new(),
        }
    }

    /// Add metadata
    pub fn with_metadata(mut self, key: String, value: serde_json::Value) -> Self {
        self.metadata.insert(key, value);
        self
    }
}

impl Default for TopicConfig {
    fn default() -> Self {
        Self {
            topic_name: String::new(),
            partitions: 1,
            replication_factor: 1,
            retention_ms: None,
            max_message_bytes: Some(1048576), // 1MB
            cleanup_policy: Some("delete".to_string()),
            compression_type: Some("lz4".to_string()),
            topic_type: "unknown".to_string(),
            schema_info: None,
            config: HashMap::new(),
        }
    }
}

impl Default for ConsumerGroupConfig {
    fn default() -> Self {
        Self {
            group_id: String::new(),
            topics: Vec::new(),
            instance_id: None,
            auto_offset_reset: "latest".to_string(),
            enable_auto_commit: true,
            auto_commit_interval_ms: 5000,
            session_timeout_ms: 30000,
            heartbeat_interval_ms: 3000,
            max_poll_records: 500,
            max_poll_interval_ms: 300000,
            config: HashMap::new(),
        }
    }
}

impl Default for ProducerConfig {
    fn default() -> Self {
        Self {
            producer_id: uuid::Uuid::new_v4().to_string(),
            topic_prefix: DEFAULT_TOPIC_PREFIX.to_string(),
            transactional_id: None,
            delivery_timeout_ms: 120000,
            request_timeout_ms: 30000,
            max_in_flight_requests: 5,
            enable_idempotence: true,
            compression_type: "lz4".to_string(),
            batch_size: 16384,
            linger_ms: 5,
            config: HashMap::new(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json;

    #[test]
    fn test_message_envelope_serialization() {
        let envelope = MessageEnvelope::new(
            "market_data".to_string(),
            "msg-123".to_string(),
            serde_json::json!({"symbol": "AAPL", "price": 150.0}),
            "test-source".to_string(),
        );

        let json = serde_json::to_string(&envelope).unwrap();
        let deserialized: MessageEnvelope = serde_json::from_str(&json).unwrap();

        assert_eq!(deserialized.message_type, "market_data");
        assert_eq!(deserialized.message_id, "msg-123");
        assert_eq!(deserialized.source, "test-source");
    }

    #[test]
    fn test_batch_message_serialization() {
        let envelope1 = MessageEnvelope::new(
            "order".to_string(),
            "order-1".to_string(),
            serde_json::json!({"symbol": "AAPL", "quantity": 100}),
            "trading-system".to_string(),
        );

        let envelope2 = MessageEnvelope::new(
            "order".to_string(),
            "order-2".to_string(),
            serde_json::json!({"symbol": "GOOGL", "quantity": 50}),
            "trading-system".to_string(),
        );

        let batch = BatchMessage::new(vec![envelope1, envelope2]);

        assert_eq!(batch.batch_size, 2);
        assert_eq!(batch.messages.len(), 2);
    }

    #[test]
    fn test_topic_name_generation() {
        let envelope = MessageEnvelope::new(
            "market_data".to_string(),
            "msg-123".to_string(),
            serde_json::json!({"symbol": "AAPL"}),
            "test-source".to_string(),
        );

        assert_eq!(envelope.topic_name(None), "default.market_data");
        assert_eq!(envelope.topic_name(Some("trading")), "trading.market_data");
    }
}
