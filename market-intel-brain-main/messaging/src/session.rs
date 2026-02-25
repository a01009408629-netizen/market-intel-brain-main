//! Session management for Aeron messaging

use crate::core::*;
use crate::aeron_client::*;
use crate::publisher::*;
use crate::subscriber::*;
use crate::codecs::*;
use crate::config::*;
use crate::metrics::*;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::{RwLock, oneshot};
use tracing::{debug, error, info, warn};

/// Messaging session manager
pub struct MessagingSession {
    /// Session ID
    id: String,
    /// Aeron client
    client: Arc<AeronClient>,
    /// Connection manager
    connection_manager: Arc<AeronConnectionManager>,
    /// Message codec
    codec: Arc<dyn MessageCodec>,
    /// Metrics collector
    metrics: Arc<dyn MetricsCollector>,
    /// Configuration
    config: AeronMessagingConfig,
    /// Active publishers
    publishers: Arc<RwLock<HashMap<String, Arc<MessagePublisher>>>>,
    /// Active subscribers
    subscribers: Arc<RwLock<HashMap<String, Arc<MessageSubscriber>>>>,
    /// Session state
    state: Arc<RwLock<SessionState>>,
    /// Shutdown signal
    shutdown_signal: Arc<RwLock<Option<oneshot::Sender<()>>>>,
}

/// Session state
#[derive(Debug, Clone, PartialEq)]
pub enum SessionState {
    /// Session is initializing
    Initializing,
    /// Session is active
    Active,
    /// Session is shutting down
    ShuttingDown,
    /// Session is terminated
    Terminated,
}

impl MessagingSession {
    /// Create new messaging session
    pub async fn new(config: AeronMessagingConfig) -> Result<Self> {
        let session_id = uuid::Uuid::new_v4().to_string();
        info!("Creating messaging session: {}", session_id);
        
        // Create Aeron client
        let client = Arc::new(AeronClient::new(config.aeron.clone()).await?);
        
        // Create connection manager
        let connection_manager = Arc::new(AeronConnectionManager::new(Arc::clone(&client)));
        
        // Create codec
        let codec = Self::create_codec(&config.codec)?;
        
        // Create metrics collector
        let metrics = Arc::new(PrometheusMetrics::new());
        
        let session = Self {
            id: session_id,
            client,
            connection_manager,
            codec,
            metrics,
            config,
            publishers: Arc::new(RwLock::new(HashMap::new())),
            subscribers: Arc::new(RwLock::new(HashMap::new())),
            state: Arc::new(RwLock::new(SessionState::Initializing)),
            shutdown_signal: Arc::new(RwLock::new(None)),
        };
        
        // Initialize session
        session.initialize().await?;
        
        Ok(session)
    }
    
    /// Initialize session
    async fn initialize(&self) -> Result<()> {
        let mut state = self.state.write().await;
        *state = SessionState::Active;
        drop(state);
        
        info!("Messaging session {} initialized successfully", self.id);
        Ok(())
    }
    
    /// Get session ID
    pub fn id(&self) -> &str {
        &self.id
    }
    
    /// Get session state
    pub async fn state(&self) -> SessionState {
        self.state.read().await.clone()
    }
    
    /// Create publisher for channel
    pub async fn create_publisher(&self, channel_name: &str) -> Result<Arc<MessagePublisher>> {
        let channel_config = self.config.channels.get(channel_name)
            .ok_or_else(|| MarketIntelError::configuration(format!("Channel {} not found", channel_name)))?;
        
        // Check if publisher already exists
        {
            let publishers = self.publishers.read().await;
            if let Some(publisher) = publishers.get(channel_name) {
                return Ok(Arc::clone(publisher));
            }
        }
        
        // Create connection
        let connection = self.connection_manager.get_connection(
            &channel_config.channel,
            channel_config.stream_id,
        ).await?;
        
        // Create publisher
        let publisher = Arc::new(MessagePublisher::new(
            connection,
            Arc::clone(&self.codec),
            Arc::clone(&self.metrics),
            self.config.publisher.clone(),
        ));
        
        // Store publisher
        {
            let mut publishers = self.publishers.write().await;
            publishers.insert(channel_name.to_string(), Arc::clone(&publisher));
        }
        
        info!("Created publisher for channel: {}", channel_name);
        Ok(publisher)
    }
    
    /// Create subscriber for channel
    pub async fn create_subscriber(&self, channel_name: &str) -> Result<Arc<MessageSubscriber>> {
        let channel_config = self.config.channels.get(channel_name)
            .ok_or_else(|| MarketIntelError::configuration(format!("Channel {} not found", channel_name)))?;
        
        // Check if subscriber already exists
        {
            let subscribers = self.subscribers.read().await;
            if let Some(subscriber) = subscribers.get(channel_name) {
                return Ok(Arc::clone(subscriber));
            }
        }
        
        // Create connection
        let connection = self.connection_manager.get_connection(
            &channel_config.channel,
            channel_config.stream_id,
        ).await?;
        
        // Create subscriber
        let subscriber = Arc::new(MessageSubscriber::new(
            connection,
            Arc::clone(&self.codec),
            Arc::clone(&self.metrics),
            self.config.subscriber.clone(),
        ));
        
        // Store subscriber
        {
            let mut subscribers = self.subscribers.write().await;
            subscribers.insert(channel_name.to_string(), Arc::clone(&subscriber));
        }
        
        info!("Created subscriber for channel: {}", channel_name);
        Ok(subscriber)
    }
    
    /// Get publisher for channel
    pub async fn get_publisher(&self, channel_name: &str) -> Option<Arc<MessagePublisher>> {
        let publishers = self.publishers.read().await;
        publishers.get(channel_name).cloned()
    }
    
    /// Get subscriber for channel
    pub async fn get_subscriber(&self, channel_name: &str) -> Option<Arc<MessageSubscriber>> {
        let subscribers = self.subscribers.read().await;
        subscribers.get(channel_name).cloned()
    }
    
    /// Publish market data
    pub async fn publish_market_data(&self, channel_name: &str, market_data: &MarketDataMessage) -> Result<()> {
        let publisher = self.get_publisher(channel_name).await
            .ok_or_else(|| MarketIntelError::configuration(format!("Publisher not found for channel: {}", channel_name)))?;
        
        publisher.publish_market_data(market_data).await
    }
    
    /// Publish order
    pub async fn publish_order(&self, channel_name: &str, order: &OrderMessage) -> Result<()> {
        let publisher = self.get_publisher(channel_name).await
            .ok_or_else(|| MarketIntelError::configuration(format!("Publisher not found for channel: {}", channel_name)))?;
        
        publisher.publish_order(order).await
    }
    
    /// Publish trade
    pub async fn publish_trade(&self, channel_name: &str, trade: &TradeMessage) -> Result<()> {
        let publisher = self.get_publisher(channel_name).await
            .ok_or_else(|| MarketIntelError::configuration(format!("Publisher not found for channel: {}", channel_name)))?;
        
        publisher.publish_trade(trade).await
    }
    
    /// Publish event
    pub async fn publish_event(&self, channel_name: &str, event: &EventMessage) -> Result<()> {
        let publisher = self.get_publisher(channel_name).await
            .ok_or_else(|| MarketIntelError::configuration(format!("Publisher not found for channel: {}", channel_name)))?;
        
        publisher.publish_event(event).await
    }
    
    /// Publish control message
    pub async fn publish_control(&self, channel_name: &str, control: &ControlMessage) -> Result<()> {
        let publisher = self.get_publisher(channel_name).await
            .ok_or_else(|| MarketIntelError::configuration(format!("Publisher not found for channel: {}", channel_name)))?;
        
        publisher.publish_control(control).await
    }
    
    /// Subscribe to messages
    pub async fn subscribe(&self, channel_name: &str) -> Result<tokio::sync::mpsc::UnboundedReceiver<UnifiedMessage>> {
        let subscriber = self.create_subscriber(channel_name).await?;
        subscriber.start().await
    }
    
    /// Get session statistics
    pub async fn get_stats(&self) -> SessionStats {
        let mut stats = SessionStats::new();
        
        stats.session_id = self.id.clone();
        stats.state = self.state().await;
        stats.client_id = self.client.client_id();
        stats.active_publishers = self.publishers.read().await.len();
        stats.active_subscribers = self.subscribers.read().await.len();
        stats.active_connections = self.connection_manager.get_connections().await.len();
        
        // Collect publisher stats
        for publisher in self.publishers.read().await.values() {
            let pub_stats = publisher.get_stats().await;
            stats.total_messages_published += pub_stats.total_messages;
            stats.market_data_published += pub_stats.market_data_count;
            stats.order_published += pub_stats.order_count;
            stats.trade_published += pub_stats.trade_count;
            stats.event_published += pub_stats.event_count;
            stats.control_published += pub_stats.control_count;
        }
        
        // Collect subscriber stats
        for subscriber in self.subscribers.read().await.values() {
            let sub_stats = subscriber.get_stats().await;
            stats.total_messages_received += sub_stats.total_messages;
            stats.market_data_received += sub_stats.market_data_count;
            stats.order_received += sub_stats.order_count;
            stats.trade_received += sub_stats.trade_count;
            stats.event_received += sub_stats.event_count;
            stats.control_received += sub_stats.control_count;
        }
        
        stats
    }
    
    /// Get health status
    pub async fn health_check(&self) -> HealthStatus {
        let state = self.state().await;
        
        match state {
            SessionState::Active => {
                let stats = self.get_stats().await;
                
                // Check if we have active connections
                if stats.active_connections == 0 {
                    return HealthStatus {
                        component: "messaging_session".to_string(),
                        status: ComponentHealth::Degraded,
                        message: "No active connections".to_string(),
                        details: HashMap::new(),
                    };
                }
                
                // Check error rates
                let total_published = stats.total_messages_published;
                let total_received = stats.total_messages_received;
                let total_messages = total_published + total_received;
                
                if total_messages > 0 {
                    let error_rate = (stats.publish_errors + stats.receive_errors) as f64 / total_messages as f64;
                    
                    if error_rate > 0.05 { // 5% error rate threshold
                        return HealthStatus {
                            component: "messaging_session".to_string(),
                            status: ComponentHealth::Degraded,
                            message: format!("High error rate: {:.2}%", error_rate * 100.0),
                            details: HashMap::new(),
                        };
                    }
                }
                
                HealthStatus {
                    component: "messaging_session".to_string(),
                    status: ComponentHealth::Healthy,
                    message: "Session is healthy".to_string(),
                    details: HashMap::new(),
                }
            }
            SessionState::Initializing => HealthStatus {
                component: "messaging_session".to_string(),
                status: ComponentHealth::Degraded,
                message: "Session is initializing".to_string(),
                details: HashMap::new(),
            },
            SessionState::ShuttingDown | SessionState::Terminated => HealthStatus {
                component: "messaging_session".to_string(),
                status: ComponentHealth::Unhealthy,
                message: format!("Session is {:?}", state),
                details: HashMap::new(),
            },
        }
    }
    
    /// Shutdown session
    pub async fn shutdown(&self) -> Result<()> {
        info!("Shutting down messaging session: {}", self.id);
        
        // Set state to shutting down
        {
            let mut state = self.state.write().await;
            *state = SessionState::ShuttingDown;
        }
        
        // Stop all subscribers
        let subscribers = self.subscribers.read().await.clone();
        for (channel_name, subscriber) in subscribers {
            if let Err(e) = subscriber.stop().await {
                error!("Failed to stop subscriber {}: {}", channel_name, e);
            }
        }
        
        // Close all connections
        if let Err(e) = self.connection_manager.close_all().await {
            error!("Failed to close connections: {}", e);
        }
        
        // Set state to terminated
        {
            let mut state = self.state.write().await;
            *state = SessionState::Terminated;
        }
        
        info!("Messaging session {} shutdown complete", self.id);
        Ok(())
    }
    
    /// Create codec from configuration
    fn create_codec(codec_config: &CodecConfig) -> Result<Arc<dyn MessageCodec>> {
        let compression_type = CompressionType::from_str(&codec_config.compression_type);
        
        let codec = if codec_config.encryption_enabled {
            let key = codec_config.encryption_key.as_ref()
                .ok_or_else(|| MarketIntelError::configuration("Encryption enabled but no key provided"))?;
            
            // Decode base64 key
            let key_bytes = base64::decode(key)
                .map_err(|e| MarketIntelError::configuration(format!("Invalid base64 key: {}", e)))?;
            
            CodecFactory::create_secure(key_bytes)
        } else {
            match compression_type {
                CompressionType::None => CodecFactory::create_default(),
                CompressionType::LZ4 => CodecFactory::create_high_performance(),
                CompressionType::Zstd | CompressionType::Gzip => CodecFactory::create_balanced(),
            }
        };
        
        Ok(codec)
    }
}

/// Session statistics
#[derive(Debug, Clone, Default)]
pub struct SessionStats {
    /// Session ID
    pub session_id: String,
    /// Session state
    pub state: SessionState,
    /// Client ID
    pub client_id: i64,
    /// Active publishers
    pub active_publishers: usize,
    /// Active subscribers
    pub active_subscribers: usize,
    /// Active connections
    pub active_connections: usize,
    /// Total messages published
    pub total_messages_published: u64,
    /// Total messages received
    pub total_messages_received: u64,
    /// Market data published
    pub market_data_published: u64,
    /// Market data received
    pub market_data_received: u64,
    /// Orders published
    pub order_published: u64,
    /// Orders received
    pub order_received: u64,
    /// Trades published
    pub trade_published: u64,
    /// Trades received
    pub trade_received: u64,
    /// Events published
    pub event_published: u64,
    /// Events received
    pub event_received: u64,
    /// Control messages published
    pub control_published: u64,
    /// Control messages received
    pub control_received: u64,
    /// Publish errors
    pub publish_errors: u64,
    /// Receive errors
    pub receive_errors: u64,
}

impl SessionStats {
    /// Create new statistics
    pub fn new() -> Self {
        Self::default()
    }
    
    /// Get total message rate
    pub fn total_message_rate(&self) -> f64 {
        // This would need timestamp tracking for accurate rate calculation
        // For now, return a placeholder
        0.0
    }
    
    /// Get publish success rate
    pub fn publish_success_rate(&self) -> f64 {
        if self.total_messages_published == 0 {
            100.0
        } else {
            let successful = self.total_messages_published - self.publish_errors;
            (successful as f64 / self.total_messages_published as f64) * 100.0
        }
    }
    
    /// Get receive success rate
    pub fn receive_success_rate(&self) -> f64 {
        if self.total_messages_received == 0 {
            100.0
        } else {
            let successful = self.total_messages_received - self.receive_errors;
            (successful as f64 / self.total_messages_received as f64) * 100.0
        }
    }
}

/// Session factory
pub struct SessionFactory;

impl SessionFactory {
    /// Create session from configuration file
    pub async fn from_config_file(config_path: &str) -> Result<MessagingSession> {
        let config = ConfigLoader::load_from_file(config_path)?;
        MessagingSession::new(config).await
    }
    
    /// Create session from environment
    pub async fn from_env() -> Result<MessagingSession> {
        let config = ConfigLoader::load_from_env()?;
        MessagingSession::new(config).await
    }
    
    /// Create session with precedence
    pub async fn with_precedence(config_file: Option<&str>) -> Result<MessagingSession> {
        let config = ConfigLoader::load_with_precedence(config_file)?;
        MessagingSession::new(config).await
    }
    
    /// Create high-performance session
    pub async fn create_high_performance() -> Result<MessagingSession> {
        let config = ConfigBuilder::new()
            .service_name("market-intel-high-perf")
            .compression_type("lz4")
            .build()?;
        
        MessagingSession::new(config).await
    }
    
    /// Create low-latency session
    pub async fn create_low_latency() -> Result<MessagingSession> {
        let config = ConfigBuilder::new()
            .service_name("market-intel-low-latency")
            .compression_type("none")
            .build()?;
        
        MessagingSession::new(config).await
    }
    
    /// Create secure session
    pub async fn create_secure(encryption_key: &str) -> Result<MessagingSession> {
        let config = ConfigBuilder::new()
            .service_name("market-intel-secure")
            .compression_type("zstd")
            .encryption_key(encryption_key)
            .build()?;
        
        MessagingSession::new(config).await
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_session_creation() {
        let config = AeronMessagingConfig::default();
        let session = MessagingSession::new(config).await;
        assert!(session.is_ok());
    }
    
    #[tokio::test]
    async fn test_session_stats() {
        let mut stats = SessionStats::new();
        stats.total_messages_published = 100;
        stats.publish_errors = 5;
        assert_eq!(stats.publish_success_rate(), 95.0);
        
        stats.total_messages_received = 200;
        stats.receive_errors = 10;
        assert_eq!(stats.receive_success_rate(), 95.0);
    }
    
    #[tokio::test]
    async fn test_session_factory() {
        let session = SessionFactory::create_high_performance().await;
        assert!(session.is_ok());
        
        let session = SessionFactory::create_low_latency().await;
        assert!(session.is_ok());
        
        let session = SessionFactory::create_secure("dGVzdGtleWZvcmVuY3J5cHRpb24xMjM="); // base64 encoded "testkeyforencryption123"
        assert!(session.is_ok());
    }
}
