//! Event system for the Market Intel Brain platform

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

use crate::types::*;

/// Unique event identifier
pub type EventId = Uuid;

/// Event type identifier
pub type EventType = String;

/// Base event trait
pub trait Event: Send + Sync {
    /// Get event ID
    fn id(&self) -> EventId;
    
    /// Get event type
    fn event_type(&self) -> &str;
    
    /// Get event timestamp
    fn timestamp(&self) -> DateTime<Utc>;
    
    /// Get event version
    fn version(&self) -> &str;
    
    /// Get event source
    fn source(&self) -> &str;
    
    /// Get event correlation ID (if any)
    fn correlation_id(&self) -> Option<EventId>;
    
    /// Serialize event to JSON
    fn to_json(&self) -> Result<String, serde_json::Error>;
    
    /// Get event metadata
    fn metadata(&self) -> &HashMap<String, serde_json::Value>;
}

/// Market data event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketDataEvent {
    /// Event ID
    pub id: EventId,
    /// Event type
    pub event_type: EventType,
    /// Event timestamp
    pub timestamp: DateTime<Utc>,
    /// Event version
    pub version: String,
    /// Event source
    pub source: String,
    /// Correlation ID
    pub correlation_id: Option<EventId>,
    /// Event metadata
    pub metadata: HashMap<String, serde_json::Value>,
    /// Market data
    pub data: MarketData,
}

impl Event for MarketDataEvent {
    fn id(&self) -> EventId {
        self.id
    }
    
    fn event_type(&self) -> &str {
        &self.event_type
    }
    
    fn timestamp(&self) -> DateTime<Utc> {
        self.timestamp
    }
    
    fn version(&self) -> &str {
        &self.version
    }
    
    fn source(&self) -> &str {
        &self.source
    }
    
    fn correlation_id(&self) -> Option<EventId> {
        self.correlation_id
    }
    
    fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string(self)
    }
    
    fn metadata(&self) -> &HashMap<String, serde_json::Value> {
        &self.metadata
    }
}

/// Order event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderEvent {
    /// Event ID
    pub id: EventId,
    /// Event type
    pub event_type: EventType,
    /// Event timestamp
    pub timestamp: DateTime<Utc>,
    /// Event version
    pub version: String,
    /// Event source
    pub source: String,
    /// Correlation ID
    pub correlation_id: Option<EventId>,
    /// Event metadata
    pub metadata: HashMap<String, serde_json::Value>,
    /// Order data
    pub order: Order,
    /// Previous status (for status changes)
    pub previous_status: Option<OrderStatus>,
}

impl Event for OrderEvent {
    fn id(&self) -> EventId {
        self.id
    }
    
    fn event_type(&self) -> &str {
        &self.event_type
    }
    
    fn timestamp(&self) -> DateTime<Utc> {
        self.timestamp
    }
    
    fn version(&self) -> &str {
        &self.version
    }
    
    fn source(&self) -> &str {
        &self.source
    }
    
    fn correlation_id(&self) -> Option<EventId> {
        self.correlation_id
    }
    
    fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string(self)
    }
    
    fn metadata(&self) -> &HashMap<String, serde_json::Value> {
        &self.metadata
    }
}

/// Trade event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradeEvent {
    /// Event ID
    pub id: EventId,
    /// Event type
    pub event_type: EventType,
    /// Event timestamp
    pub timestamp: DateTime<Utc>,
    /// Event version
    pub version: String,
    /// Event source
    pub source: String,
    /// Correlation ID
    pub correlation_id: Option<EventId>,
    /// Event metadata
    pub metadata: HashMap<String, serde_json::Value>,
    /// Trade data
    pub trade: Trade,
}

impl Event for TradeEvent {
    fn id(&self) -> EventId {
        self.id
    }
    
    fn event_type(&self) -> &str {
        &self.event_type
    }
    
    fn timestamp(&self) -> DateTime<Utc> {
        self.timestamp
    }
    
    fn version(&self) -> &str {
        &self.version
    }
    
    fn source(&self) -> &str {
        &self.source
    }
    
    fn correlation_id(&self) -> Option<EventId> {
        self.correlation_id
    }
    
    fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string(self)
    }
    
    fn metadata(&self) -> &HashMap<String, serde_json::Value> {
        &self.metadata
    }
}

/// Position event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PositionEvent {
    /// Event ID
    pub id: EventId,
    /// Event type
    pub event_type: EventType,
    /// Event timestamp
    pub timestamp: DateTime<Utc>,
    /// Event version
    pub version: String,
    /// Event source
    pub source: String,
    /// Correlation ID
    pub correlation_id: Option<EventId>,
    /// Event metadata
    pub metadata: HashMap<String, serde_json::Value>,
    /// Position data
    pub position: Position,
    /// Previous quantity (for position changes)
    pub previous_quantity: Option<Quantity>,
}

impl Event for PositionEvent {
    fn id(&self) -> EventId {
        self.id
    }
    
    fn event_type(&self) -> &str {
        &self.event_type
    }
    
    fn timestamp(&self) -> DateTime<Utc> {
        self.timestamp
    }
    
    fn version(&self) -> &str {
        &self.version
    }
    
    fn source(&self) -> &str {
        &self.source
    }
    
    fn correlation_id(&self) -> Option<EventId> {
        self.correlation_id
    }
    
    fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string(self)
    }
    
    fn metadata(&self) -> &HashMap<String, serde_json::Value> {
        &self.metadata
    }
}

/// Risk event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskEvent {
    /// Event ID
    pub id: EventId,
    /// Event type
    pub event_type: EventType,
    /// Event timestamp
    pub timestamp: DateTime<Utc>,
    /// Event version
    pub version: String,
    /// Event source
    pub source: String,
    /// Correlation ID
    pub correlation_id: Option<EventId>,
    /// Event metadata
    pub metadata: HashMap<String, serde_json::Value>,
    /// Risk metrics
    pub risk_metrics: RiskMetrics,
    /// Risk alert level
    pub alert_level: RiskLevel,
}

impl Event for RiskEvent {
    fn id(&self) -> EventId {
        self.id
    }
    
    fn event_type(&self) -> &str {
        &self.event_type
    }
    
    fn timestamp(&self) -> DateTime<Utc> {
        self.timestamp
    }
    
    fn version(&self) -> &str {
        &self.version
    }
    
    fn source(&self) -> &str {
        &self.source
    }
    
    fn correlation_id(&self) -> Option<EventId> {
        self.correlation_id
    }
    
    fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string(self)
    }
    
    fn metadata(&self) -> &HashMap<String, serde_json::Value> {
        &self.metadata
    }
}

/// System event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemEvent {
    /// Event ID
    pub id: EventId,
    /// Event type
    pub event_type: EventType,
    /// Event timestamp
    pub timestamp: DateTime<Utc>,
    /// Event version
    pub version: String,
    /// Event source
    pub source: String,
    /// Correlation ID
    pub correlation_id: Option<EventId>,
    /// Event metadata
    pub metadata: HashMap<String, serde_json::Value>,
    /// System component
    pub component: String,
    /// System level
    pub level: SystemLevel,
    /// Message
    pub message: String,
    /// Additional data
    pub data: HashMap<String, serde_json::Value>,
}

impl Event for SystemEvent {
    fn id(&self) -> EventId {
        self.id
    }
    
    fn event_type(&self) -> &str {
        &self.event_type
    }
    
    fn timestamp(&self) -> DateTime<Utc> {
        self.timestamp
    }
    
    fn version(&self) -> &str {
        &self.version
    }
    
    fn source(&self) -> &str {
        &self.source
    }
    
    fn correlation_id(&self) -> Option<EventId> {
        self.correlation_id
    }
    
    fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string(self)
    }
    
    fn metadata(&self) -> &HashMap<String, serde_json::Value> {
        &self.metadata
    }
}

/// System event levels
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum SystemLevel {
    /// Informational
    Info,
    /// Warning
    Warning,
    /// Error
    Error,
    /// Critical
    Critical,
}

/// Event factory for creating standard events
pub struct EventFactory;

impl EventFactory {
    /// Create market data event
    pub fn create_market_data_event(
        data: MarketData,
        source: &str,
    ) -> MarketDataEvent {
        MarketDataEvent {
            id: Uuid::new_v4(),
            event_type: "market_data".to_string(),
            timestamp: Utc::now(),
            version: "1.0".to_string(),
            source: source.to_string(),
            correlation_id: None,
            metadata: HashMap::new(),
            data,
        }
    }
    
    /// Create order event
    pub fn create_order_event(
        order: Order,
        source: &str,
        previous_status: Option<OrderStatus>,
    ) -> OrderEvent {
        OrderEvent {
            id: Uuid::new_v4(),
            event_type: "order".to_string(),
            timestamp: Utc::now(),
            version: "1.0".to_string(),
            source: source.to_string(),
            correlation_id: None,
            metadata: HashMap::new(),
            order,
            previous_status,
        }
    }
    
    /// Create trade event
    pub fn create_trade_event(
        trade: Trade,
        source: &str,
    ) -> TradeEvent {
        TradeEvent {
            id: Uuid::new_v4(),
            event_type: "trade".to_string(),
            timestamp: Utc::now(),
            version: "1.0".to_string(),
            source: source.to_string(),
            correlation_id: None,
            metadata: HashMap::new(),
            trade,
        }
    }
    
    /// Create position event
    pub fn create_position_event(
        position: Position,
        source: &str,
        previous_quantity: Option<Quantity>,
    ) -> PositionEvent {
        PositionEvent {
            id: Uuid::new_v4(),
            event_type: "position".to_string(),
            timestamp: Utc::now(),
            version: "1.0".to_string(),
            source: source.to_string(),
            correlation_id: None,
            metadata: HashMap::new(),
            position,
            previous_quantity,
        }
    }
    
    /// Create risk event
    pub fn create_risk_event(
        risk_metrics: RiskMetrics,
        alert_level: RiskLevel,
        source: &str,
    ) -> RiskEvent {
        RiskEvent {
            id: Uuid::new_v4(),
            event_type: "risk".to_string(),
            timestamp: Utc::now(),
            version: "1.0".to_string(),
            source: source.to_string(),
            correlation_id: None,
            metadata: HashMap::new(),
            risk_metrics,
            alert_level,
        }
    }
    
    /// Create system event
    pub fn create_system_event(
        component: &str,
        level: SystemLevel,
        message: &str,
        source: &str,
    ) -> SystemEvent {
        SystemEvent {
            id: Uuid::new_v4(),
            event_type: "system".to_string(),
            timestamp: Utc::now(),
            version: "1.0".to_string(),
            source: source.to_string(),
            correlation_id: None,
            metadata: HashMap::new(),
            component: component.to_string(),
            level,
            message: message.to_string(),
            data: HashMap::new(),
        }
    }
}

/// Event filter for subscribing to specific events
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventFilter {
    /// Event types to include
    pub event_types: Option<Vec<EventType>>,
    /// Sources to include
    pub sources: Option<Vec<String>>,
    /// Symbols to include
    pub symbols: Option<Vec<Symbol>>,
    /// Time range
    pub time_range: Option<(DateTime<Utc>, DateTime<Utc>)>,
    /// Custom filters
    pub custom_filters: HashMap<String, serde_json::Value>,
}

impl EventFilter {
    /// Create new event filter
    pub fn new() -> Self {
        Self {
            event_types: None,
            sources: None,
            symbols: None,
            time_range: None,
            custom_filters: HashMap::new(),
        }
    }
    
    /// Add event type filter
    pub fn with_event_types(mut self, types: Vec<EventType>) -> Self {
        self.event_types = Some(types);
        self
    }
    
    /// Add source filter
    pub fn with_sources(mut self, sources: Vec<String>) -> Self {
        self.sources = Some(sources);
        self
    }
    
    /// Add symbol filter
    pub fn with_symbols(mut self, symbols: Vec<Symbol>) -> Self {
        self.symbols = Some(symbols);
        self
    }
    
    /// Add time range filter
    pub fn with_time_range(mut self, start: DateTime<Utc>, end: DateTime<Utc>) -> Self {
        self.time_range = Some((start, end));
        self
    }
    
    /// Add custom filter
    pub fn with_custom_filter(mut self, key: String, value: serde_json::Value) -> Self {
        self.custom_filters.insert(key, value);
        self
    }
    
    /// Check if event matches filter
    pub fn matches(&self, event: &dyn Event) -> bool {
        // Check event type
        if let Some(ref types) = self.event_types {
            if !types.contains(&event.event_type().to_string()) {
                return false;
            }
        }
        
        // Check source
        if let Some(ref sources) = self.sources {
            if !sources.contains(&event.source().to_string()) {
                return false;
            }
        }
        
        // Check time range
        if let Some((start, end)) = self.time_range {
            let timestamp = event.timestamp();
            if timestamp < start || timestamp > end {
                return false;
            }
        }
        
        true
    }
}

impl Default for EventFilter {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_market_data_event() {
        let market_data = MarketData {
            id: Uuid::new_v4(),
            symbol: "AAPL".to_string(),
            exchange: Exchange::NASDAQ,
            data_type: MarketDataType::Trade,
            asset_class: AssetClass::Equity,
            timestamp: Utc::now(),
            price: Some(Decimal::from(150)),
            quantity: Some(Decimal::from(100)),
            bid_price: None,
            ask_price: None,
            bid_quantity: None,
            ask_quantity: None,
            metadata: HashMap::new(),
        };
        
        let event = EventFactory::create_market_data_event(market_data, "test");
        
        assert_eq!(event.event_type(), "market_data");
        assert_eq!(event.source(), "test");
        assert_eq!(event.version(), "1.0");
    }
    
    #[test]
    fn test_event_filter() {
        let filter = EventFilter::new()
            .with_event_types(vec!["market_data".to_string()])
            .with_sources(vec!["test".to_string()]);
        
        let market_data = MarketData {
            id: Uuid::new_v4(),
            symbol: "AAPL".to_string(),
            exchange: Exchange::NASDAQ,
            data_type: MarketDataType::Trade,
            asset_class: AssetClass::Equity,
            timestamp: Utc::now(),
            price: Some(Decimal::from(150)),
            quantity: Some(Decimal::from(100)),
            bid_price: None,
            ask_price: None,
            bid_quantity: None,
            ask_quantity: None,
            metadata: HashMap::new(),
        };
        
        let event = EventFactory::create_market_data_event(market_data, "test");
        assert!(filter.matches(&event));
        
        let event2 = EventFactory::create_market_data_event(market_data, "other");
        assert!(!filter.matches(&event2));
    }
}
