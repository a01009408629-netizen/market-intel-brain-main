//! High-performance message subscriber using Aeron

use crate::core::*;
use crate::message_types::*;
use crate::aeron_client::*;
use crate::codecs::*;
use crate::metrics::*;
use bytes::Bytes;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::{mpsc, RwLock};
use tokio::time::timeout;
use tracing::{debug, error, info, warn};

/// High-performance message subscriber
pub struct MessageSubscriber {
    /// Aeron connection
    connection: Arc<AeronConnection>,
    /// Message codec
    codec: Arc<dyn MessageCodec>,
    /// Metrics collector
    metrics: Arc<dyn MetricsCollector>,
    /// Subscriber configuration
    config: SubscriberConfig,
    /// Subscription statistics
    stats: Arc<RwLock<SubscriberStats>>,
    /// Message handlers
    handlers: Arc<RwLock<Vec<Arc<dyn MessageHandler>>>>,
    /// Running state
    is_running: Arc<RwLock<bool>>,
}

impl MessageSubscriber {
    /// Create new subscriber
    pub fn new(
        connection: Arc<AeronConnection>,
        codec: Arc<dyn MessageCodec>,
        metrics: Arc<dyn MetricsCollector>,
        config: SubscriberConfig,
    ) -> Self {
        Self {
            connection,
            codec,
            metrics,
            config,
            stats: Arc::new(RwLock::new(SubscriberStats::new())),
            handlers: Arc::new(RwLock::new(Vec::new())),
            is_running: Arc::new(RwLock::new(false)),
        }
    }
    
    /// Start subscribing to messages
    pub async fn start(&self) -> Result<mpsc::UnboundedReceiver<UnifiedMessage>> {
        let mut is_running = self.is_running.write().await;
        if *is_running {
            return Err(MarketIntelError::conflict("Subscriber already running"));
        }
        
        *is_running = true;
        drop(is_running);
        
        info!("Starting message subscriber on {}:{}", self.connection.channel(), self.connection.stream_id());
        
        // Get message receiver from connection
        let receiver = self.connection.subscribe().await;
        
        // Start message processing task
        self.start_message_processing().await?;
        
        Ok(receiver)
    }
    
    /// Stop subscribing
    pub async fn stop(&self) -> Result<()> {
        let mut is_running = self.is_running.write().await;
        *is_running = false;
        drop(is_running);
        
        info!("Stopped message subscriber");
        Ok(())
    }
    
    /// Add message handler
    pub async fn add_handler(&self, handler: Arc<dyn MessageHandler>) {
        let mut handlers = self.handlers.write().await;
        handlers.push(handler);
    }
    
    /// Remove message handler
    pub async fn remove_handler(&self, handler_id: &str) -> bool {
        let mut handlers = self.handlers.write().await;
        let initial_len = handlers.len();
        handlers.retain(|h| h.id() != handler_id);
        handlers.len() < initial_len
    }
    
    /// Process single message
    pub async fn process_message(&self, raw_data: &[u8]) -> Result<UnifiedMessage> {
        let start_time = Instant::now();
        
        // Decrypt if configured
        let decrypted_data = if self.config.encryption_enabled {
            self.codec.decrypt(raw_data)?
        } else {
            raw_data.to_vec()
        };
        
        // Decompress if configured
        let decompressed_data = if self.config.compression_enabled {
            self.codec.decompress(&decrypted_data)?
        } else {
            decrypted_data
        };
        
        // Decode message
        let message = self.codec.decode(&decompressed_data)?;
        
        // Update metrics
        let duration = start_time.elapsed();
        self.update_receive_metrics(&message, duration, raw_data.len() as u64).await?;
        
        // Update statistics
        self.update_stats(&message).await;
        
        // Handle message
        self.handle_message(&message).await?;
        
        debug!("Processed message: {}", message.header.message_id);
        Ok(message)
    }
    
    /// Process batch of messages
    pub async fn process_batch(&self, messages: &[UnifiedMessage]) -> Result<usize> {
        let mut processed_count = 0;
        let start_time = Instant::now();
        
        for message in messages {
            match self.handle_message(message).await {
                Ok(()) => processed_count += 1,
                Err(e) => {
                    error!("Failed to handle message in batch: {}", e);
                    if self.config.fail_fast {
                        return Err(e);
                    }
                }
            }
        }
        
        // Update batch metrics
        let duration = start_time.elapsed();
        let total_size: u64 = messages.iter().map(|m| m.encode_len().unwrap_or(0) as u64).sum();
        self.update_batch_metrics(processed_count, duration, total_size).await?;
        
        info!("Processed batch: {}/{} messages in {:?}", processed_count, messages.len(), duration);
        Ok(processed_count)
    }
    
    /// Check if subscriber is running
    pub async fn is_running(&self) -> bool {
        *self.is_running.read().await
    }
    
    /// Get subscriber statistics
    pub async fn get_stats(&self) -> SubscriberStats {
        self.stats.read().await.clone()
    }
    
    /// Get connection status
    pub fn connection_status(&self) -> SubscriptionStatus {
        self.connection.subscription_status()
    }
    
    /// Reset statistics
    pub async fn reset_stats(&self) {
        let mut stats = self.stats.write().await;
        stats.reset();
    }
    
    /// Start message processing task
    async fn start_message_processing(&self) -> Result<()> {
        let connection = Arc::clone(&self.connection);
        let codec = Arc::clone(&self.codec);
        let config = self.config.clone();
        let stats = Arc::clone(&self.stats);
        let metrics = Arc::clone(&self.metrics);
        let handlers = Arc::clone(&self.handlers);
        let is_running = Arc::clone(&self.is_running);
        
        tokio::spawn(async move {
            info!("Message processing task started");
            
            while *is_running.read().await {
                // Poll for messages
                match timeout(
                    Duration::from_millis(config.poll_interval_ms),
                    self.poll_messages(&connection, &codec, &config, &stats, &metrics, &handlers)
                ).await {
                    Ok(Ok(())) => {
                        // Messages processed successfully
                    }
                    Ok(Err(e)) => {
                        error!("Error processing messages: {}", e);
                        if config.fail_fast {
                            break;
                        }
                    }
                    Err(_) => {
                        // Timeout, continue polling
                    }
                }
                
                // Small delay to prevent busy waiting
                tokio::time::sleep(Duration::from_millis(1)).await;
            }
            
            info!("Message processing task stopped");
        });
        
        Ok(())
    }
    
    /// Poll for messages from Aeron
    async fn poll_messages(
        &self,
        connection: &Arc<AeronConnection>,
        codec: &Arc<dyn MessageCodec>,
        config: &SubscriberConfig,
        stats: &Arc<RwLock<SubscriberStats>>,
        metrics: &Arc<dyn MetricsCollector>,
        handlers: &Arc<RwLock<Vec<Arc<dyn MessageHandler>>>>,
    ) -> Result<()> {
        let subscription = &connection.subscription;
        
        // Poll for fragments
        while let Some(fragment) = subscription.poll()? {
            let start_time = Instant::now();
            
            // Process fragment
            match self.process_fragment(fragment, codec, config).await {
                Ok(message) => {
                    // Handle message
                    let handlers_guard = handlers.read().await;
                    for handler in handlers_guard.iter() {
                        if let Err(e) = handler.handle_message(&message).await {
                            error!("Handler {} failed: {}", handler.id(), e);
                        }
                    }
                    
                    // Update metrics
                    let duration = start_time.elapsed();
                    self.update_fragment_metrics(duration, fragment.len() as u64).await?;
                }
                Err(e) => {
                    error!("Failed to process fragment: {}", e);
                    let mut stats_guard = stats.write().await;
                    stats.fragment_errors += 1;
                }
            }
        }
        
        Ok(())
    }
    
    /// Process single fragment
    async fn process_fragment(
        &self,
        fragment: &[u8],
        codec: &Arc<dyn MessageCodec>,
        config: &SubscriberConfig,
    ) -> Result<UnifiedMessage> {
        // Decrypt if configured
        let decrypted_data = if config.encryption_enabled {
            codec.decrypt(fragment)?
        } else {
            fragment.to_vec()
        };
        
        // Decompress if configured
        let decompressed_data = if config.compression_enabled {
            codec.decompress(&decrypted_data)?
        } else {
            decrypted_data
        };
        
        // Decode message
        let message = codec.decode(&decompressed_data)?;
        
        Ok(message)
    }
    
    /// Handle message
    async fn handle_message(&self, message: &UnifiedMessage) -> Result<()> {
        let handlers = self.handlers.read().await;
        
        for handler in handlers.iter() {
            if let Err(e) = handler.handle_message(message).await {
                error!("Handler {} failed: {}", handler.id(), e);
                if self.config.fail_fast {
                    return Err(e);
                }
            }
        }
        
        Ok(())
    }
    
    /// Update receive metrics
    async fn update_receive_metrics(&self, message: &UnifiedMessage, duration: Duration, size: u64) -> Result<()> {
        let message_type = match message.payload {
            Some(MessagePayload::MarketData(_)) => "market_data",
            Some(MessagePayload::Order(_)) => "order",
            Some(MessagePayload::Trade(_)) => "trade",
            Some(MessagePayload::Event(_)) => "event",
            Some(MessagePayload::Control(_)) => "control",
            None => "unknown",
        };
        
        let labels = HashMap::from([
            ("message_type".to_string(), message_type.to_string()),
            ("channel".to_string(), self.connection.channel().to_string()),
            ("stream_id".to_string(), self.connection.stream_id().to_string()),
        ]);
        
        self.metrics.increment_counter("messages_received_total", Some(labels.clone()));
        self.metrics.record_histogram("receive_duration_ns", duration.as_nanos() as f64, Some(labels.clone()));
        self.metrics.record_histogram("message_size_bytes", size as f64, Some(labels));
        
        Ok(())
    }
    
    /// Update fragment metrics
    async fn update_fragment_metrics(&self, duration: Duration, size: u64) -> Result<()> {
        let labels = HashMap::from([
            ("channel".to_string(), self.connection.channel().to_string()),
            ("stream_id".to_string(), self.connection.stream_id().to_string()),
        ]);
        
        self.metrics.increment_counter("fragments_received_total", Some(labels.clone()));
        self.metrics.record_histogram("fragment_processing_duration_ns", duration.as_nanos() as f64, Some(labels.clone()));
        self.metrics.record_histogram("fragment_size_bytes", size as f64, Some(labels));
        
        Ok(())
    }
    
    /// Update batch metrics
    async fn update_batch_metrics(&self, count: usize, duration: Duration, total_size: u64) -> Result<()> {
        let labels = HashMap::from([
            ("channel".to_string(), self.connection.channel().to_string()),
            ("stream_id".to_string(), self.connection.stream_id().to_string()),
        ]);
        
        self.metrics.increment_counter("batches_processed_total", Some(labels.clone()));
        self.metrics.record_histogram("batch_size", count as f64, Some(labels.clone()));
        self.metrics.record_histogram("batch_duration_ns", duration.as_nanos() as f64, Some(labels.clone()));
        self.metrics.record_histogram("batch_total_size_bytes", total_size as f64, Some(labels));
        
        Ok(())
    }
    
    /// Update subscriber statistics
    async fn update_stats(&self, message: &UnifiedMessage) {
        let mut stats = self.stats.write().await;
        stats.total_messages += 1;
        stats.last_message_id = Some(message.header.message_id.clone());
        stats.last_message_timestamp = Some(message.header.timestamp_ns);
        
        match message.payload {
            Some(MessagePayload::MarketData(_)) => stats.market_data_count += 1,
            Some(MessagePayload::Order(_)) => stats.order_count += 1,
            Some(MessagePayload::Trade(_)) => stats.trade_count += 1,
            Some(MessagePayload::Event(_)) => stats.event_count += 1,
            Some(MessagePayload::Control(_)) => stats.control_count += 1,
            None => {}
        }
    }
}

/// Message handler trait
#[async_trait]
pub trait MessageHandler: Send + Sync {
    /// Get handler ID
    fn id(&self) -> &str;
    
    /// Handle message
    async fn handle_message(&self, message: &UnifiedMessage) -> Result<()>;
    
    /// Get handler priority
    fn priority(&self) -> u32 {
        100 // Default priority
    }
}

/// Subscriber configuration
#[derive(Debug, Clone)]
pub struct SubscriberConfig {
    /// Enable compression
    pub compression_enabled: bool,
    /// Enable encryption
    pub encryption_enabled: bool,
    /// Fail fast on errors
    pub fail_fast: bool,
    /// Poll interval in milliseconds
    pub poll_interval_ms: u64,
    /// Buffer size
    pub buffer_size: usize,
    /// Max batch size
    pub max_batch_size: usize,
    /// Subscription timeout
    pub subscription_timeout: Duration,
}

impl Default for SubscriberConfig {
    fn default() -> Self {
        Self {
            compression_enabled: false,
            encryption_enabled: false,
            fail_fast: false,
            poll_interval_ms: 1,
            buffer_size: 8192,
            max_batch_size: 1000,
            subscription_timeout: Duration::from_secs(5),
        }
    }
}

/// Subscriber statistics
#[derive(Debug, Clone, Default)]
pub struct SubscriberStats {
    /// Total messages received
    pub total_messages: u64,
    /// Market data messages count
    pub market_data_count: u64,
    /// Order messages count
    pub order_count: u64,
    /// Trade messages count
    pub trade_count: u64,
    /// Event messages count
    pub event_count: u64,
    /// Control messages count
    pub control_count: u64,
    /// Last message ID
    pub last_message_id: Option<String>,
    /// Last message timestamp
    pub last_message_timestamp: Option<u64>,
    /// Fragment errors
    pub fragment_errors: u64,
    /// Processing errors
    pub processing_errors: u64,
    /// Messages per second
    pub messages_per_second: f64,
    /// Average message size
    pub average_message_size: f64,
    /// Buffer utilization
    pub buffer_utilization: f64,
}

impl SubscriberStats {
    /// Create new statistics
    pub fn new() -> Self {
        Self::default()
    }
    
    /// Reset statistics
    pub fn reset(&mut self) {
        *self = Self::new();
    }
    
    /// Calculate messages per second
    pub fn calculate_rate(&mut self) {
        if let Some(last_timestamp) = self.last_message_timestamp {
            let now = crate::message_types::utils::current_timestamp_ns();
            let duration_ns = now.saturating_sub(last_timestamp);
            
            if duration_ns > 0 {
                self.messages_per_second = (self.total_messages as f64 * 1_000_000_000.0) / duration_ns as f64;
            }
        }
    }
    
    /// Get error rate
    pub fn error_rate(&self) -> f64 {
        let total_errors = self.fragment_errors + self.processing_errors;
        if self.total_messages == 0 {
            0.0
        } else {
            (total_errors as f64 / self.total_messages as f64) * 100.0
        }
    }
}

/// Default message handler for logging
pub struct LoggingMessageHandler {
    id: String,
    log_level: String,
}

impl LoggingMessageHandler {
    /// Create new logging handler
    pub fn new(id: String, log_level: String) -> Self {
        Self { id, log_level }
    }
}

#[async_trait]
impl MessageHandler for LoggingMessageHandler {
    fn id(&self) -> &str {
        &self.id
    }
    
    async fn handle_message(&self, message: &UnifiedMessage) -> Result<()> {
        let message_type = match message.payload {
            Some(MessagePayload::MarketData(_)) => "market_data",
            Some(MessagePayload::Order(_)) => "order",
            Some(MessagePayload::Trade(_)) => "trade",
            Some(MessagePayload::Event(_)) => "event",
            Some(MessagePayload::Control(_)) => "control",
            None => "unknown",
        };
        
        match self.log_level.as_str() {
            "debug" => debug!("Received {}: {}", message_type, message.header.message_id),
            "info" => info!("Received {}: {}", message_type, message.header.message_id),
            "warn" => warn!("Received {}: {}", message_type, message.header.message_id),
            "error" => error!("Received {}: {}", message_type, message.header.message_id),
            _ => tracing::trace!("Received {}: {}", message_type, message.header.message_id),
        }
        
        Ok(())
    }
}

/// Metrics collection handler
pub struct MetricsMessageHandler {
    id: String,
    metrics: Arc<dyn MetricsCollector>,
}

impl MetricsMessageHandler {
    /// Create new metrics handler
    pub fn new(id: String, metrics: Arc<dyn MetricsCollector>) -> Self {
        Self { id, metrics }
    }
}

#[async_trait]
impl MessageHandler for MetricsMessageHandler {
    fn id(&self) -> &str {
        &self.id
    }
    
    async fn handle_message(&self, message: &UnifiedMessage) -> Result<()> {
        let message_type = match message.payload {
            Some(MessagePayload::MarketData(_)) => "market_data",
            Some(MessagePayload::Order(_)) => "order",
            Some(MessagePayload::Trade(_)) => "trade",
            Some(MessagePayload::Event(_)) => "event",
            Some(MessagePayload::Control(_)) => "control",
            None => "unknown",
        };
        
        let labels = HashMap::from([
            ("handler_id".to_string(), self.id.clone()),
            ("message_type".to_string(), message_type.to_string()),
        ]);
        
        self.metrics.increment_counter("messages_handled_total", Some(labels));
        
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_subscriber_config() {
        let config = SubscriberConfig::default();
        assert_eq!(config.poll_interval_ms, 1);
        assert_eq!(config.buffer_size, 8192);
        assert!(!config.compression_enabled);
    }
    
    #[tokio::test]
    async fn test_subscriber_stats() {
        let mut stats = SubscriberStats::new();
        assert_eq!(stats.total_messages, 0);
        assert_eq!(stats.error_rate(), 0.0);
        
        stats.total_messages = 100;
        stats.fragment_errors = 5;
        stats.processing_errors = 3;
        assert_eq!(stats.error_rate(), 8.0);
    }
    
    #[tokio::test]
    async fn test_logging_handler() {
        let handler = LoggingMessageHandler::new("test".to_string(), "info".to_string());
        assert_eq!(handler.id(), "test");
        assert_eq!(handler.priority(), 100);
    }
    
    #[tokio::test]
    async fn test_metrics_handler() {
        // This would require a real metrics collector
        let handler = MetricsMessageHandler::new("test".to_string(), Arc::new(crate::metrics::PrometheusMetrics::new()));
        assert_eq!(handler.id(), "test");
    }
}
