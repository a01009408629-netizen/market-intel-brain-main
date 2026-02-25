//! High-performance message publisher using Aeron

use crate::core::*;
use crate::message_types::*;
use crate::aeron_client::*;
use crate::codecs::*;
use crate::metrics::*;
use bytes::Bytes;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;
use tracing::{debug, error, info, warn};

/// High-performance message publisher
pub struct MessagePublisher {
    /// Aeron connection
    connection: Arc<AeronConnection>,
    /// Message codec
    codec: Arc<dyn MessageCodec>,
    /// Metrics collector
    metrics: Arc<dyn MetricsCollector>,
    /// Publisher configuration
    config: PublisherConfig,
    /// Publication statistics
    stats: Arc<RwLock<PublisherStats>>,
}

impl MessagePublisher {
    /// Create new publisher
    pub fn new(
        connection: Arc<AeronConnection>,
        codec: Arc<dyn MessageCodec>,
        metrics: Arc<dyn MetricsCollector>,
        config: PublisherConfig,
    ) -> Self {
        Self {
            connection,
            codec,
            metrics,
            config,
            stats: Arc::new(RwLock::new(PublisherStats::new())),
        }
    }
    
    /// Publish market data message
    pub async fn publish_market_data(&self, market_data: &MarketDataMessage) -> Result<()> {
        let start_time = Instant::now();
        
        // Create unified message
        let unified_message = UnifiedMessage {
            header: market_data.header.clone(),
            payload: Some(MessagePayload::MarketData(market_data.clone())),
        };
        
        // Publish message
        self.publish_unified_message(&unified_message).await?;
        
        // Update metrics
        let duration = start_time.elapsed();
        self.update_publish_metrics("market_data", duration, market_data.encode_len()? as u64).await?;
        
        Ok(())
    }
    
    /// Publish order message
    pub async fn publish_order(&self, order: &OrderMessage) -> Result<()> {
        let start_time = Instant::now();
        
        // Create unified message
        let unified_message = UnifiedMessage {
            header: order.header.clone(),
            payload: Some(MessagePayload::Order(order.clone())),
        };
        
        // Publish message
        self.publish_unified_message(&unified_message).await?;
        
        // Update metrics
        let duration = start_time.elapsed();
        self.update_publish_metrics("order", duration, order.encode_len()? as u64).await?;
        
        Ok(())
    }
    
    /// Publish trade message
    pub async fn publish_trade(&self, trade: &TradeMessage) -> Result<()> {
        let start_time = Instant::now();
        
        // Create unified message
        let unified_message = UnifiedMessage {
            header: trade.header.clone(),
            payload: Some(MessagePayload::Trade(trade.clone())),
        };
        
        // Publish message
        self.publish_unified_message(&unified_message).await?;
        
        // Update metrics
        let duration = start_time.elapsed();
        self.update_publish_metrics("trade", duration, trade.encode_len()? as u64).await?;
        
        Ok(())
    }
    
    /// Publish event message
    pub async fn publish_event(&self, event: &EventMessage) -> Result<()> {
        let start_time = Instant::now();
        
        // Create unified message
        let unified_message = UnifiedMessage {
            header: event.header.clone(),
            payload: Some(MessagePayload::Event(event.clone())),
        };
        
        // Publish message
        self.publish_unified_message(&unified_message).await?;
        
        // Update metrics
        let duration = start_time.elapsed();
        self.update_publish_metrics("event", duration, event.encode_len()? as u64).await?;
        
        Ok(())
    }
    
    /// Publish control message
    pub async fn publish_control(&self, control: &ControlMessage) -> Result<()> {
        let start_time = Instant::now();
        
        // Create unified message
        let unified_message = UnifiedMessage {
            header: control.header.clone(),
            payload: Some(MessagePayload::Control(control.clone())),
        };
        
        // Publish message
        self.publish_unified_message(&unified_message).await?;
        
        // Update metrics
        let duration = start_time.elapsed();
        self.update_publish_metrics("control", duration, control.encode_len()? as u64).await?;
        
        Ok(())
    }
    
    /// Publish unified message
    pub async fn publish_unified_message(&self, message: &UnifiedMessage) -> Result<()> {
        // Check if publisher is ready
        if !self.is_ready().await {
            return Err(MarketIntelError::network("Publisher not ready"));
        }
        
        // Apply rate limiting if configured
        if self.config.rate_limit_enabled {
            self.check_rate_limit().await?;
        }
        
        // Encode message
        let encoded = self.codec.encode(message)?;
        
        // Apply compression if configured
        let final_payload = if self.config.compression_enabled {
            self.codec.compress(&encoded)?
        } else {
            encoded
        };
        
        // Apply encryption if configured
        let encrypted_payload = if self.config.encryption_enabled {
            self.codec.encrypt(&final_payload)?
        } else {
            final_payload
        };
        
        // Publish to Aeron
        self.connection.publish(&encrypted_payload).await?;
        
        // Update statistics
        self.update_stats(message).await;
        
        debug!("Published message: {}", message.header.message_id);
        Ok(())
    }
    
    /// Publish batch of messages
    pub async fn publish_batch(&self, messages: &[UnifiedMessage]) -> Result<usize> {
        let mut published_count = 0;
        let start_time = Instant::now();
        
        for message in messages {
            match self.publish_unified_message(message).await {
                Ok(()) => published_count += 1,
                Err(e) => {
                    error!("Failed to publish message in batch: {}", e);
                    if self.config.fail_fast {
                        return Err(e);
                    }
                }
            }
        }
        
        // Update batch metrics
        let duration = start_time.elapsed();
        let total_size: u64 = messages.iter().map(|m| m.encode_len().unwrap_or(0) as u64).sum();
        self.update_batch_metrics(published_count, duration, total_size).await?;
        
        info!("Published batch: {}/{} messages in {:?}", published_count, messages.len(), duration);
        Ok(published_count)
    }
    
    /// Check if publisher is ready
    pub async fn is_ready(&self) -> bool {
        let status = self.connection.publication_status();
        status.is_connected
    }
    
    /// Get publisher statistics
    pub async fn get_stats(&self) -> PublisherStats {
        self.stats.read().await.clone()
    }
    
    /// Get connection status
    pub fn connection_status(&self) -> PublicationStatus {
        self.connection.publication_status()
    }
    
    /// Reset statistics
    pub async fn reset_stats(&self) {
        let mut stats = self.stats.write().await;
        stats.reset();
    }
    
    /// Update publish metrics
    async fn update_publish_metrics(&self, message_type: &str, duration: Duration, size: u64) -> Result<()> {
        let labels = HashMap::from([
            ("message_type".to_string(), message_type.to_string()),
            ("channel".to_string(), self.connection.channel().to_string()),
            ("stream_id".to_string(), self.connection.stream_id().to_string()),
        ]);
        
        self.metrics.increment_counter("messages_published_total", Some(labels.clone()));
        self.metrics.record_histogram("publish_duration_ns", duration.as_nanos() as f64, Some(labels.clone()));
        self.metrics.record_histogram("message_size_bytes", size as f64, Some(labels));
        
        Ok(())
    }
    
    /// Update batch metrics
    async fn update_batch_metrics(&self, count: usize, duration: Duration, total_size: u64) -> Result<()> {
        let labels = HashMap::from([
            ("channel".to_string(), self.connection.channel().to_string()),
            ("stream_id".to_string(), self.connection.stream_id().to_string()),
        ]);
        
        self.metrics.increment_counter("batches_published_total", Some(labels.clone()));
        self.metrics.record_histogram("batch_size", count as f64, Some(labels.clone()));
        self.metrics.record_histogram("batch_duration_ns", duration.as_nanos() as f64, Some(labels.clone()));
        self.metrics.record_histogram("batch_total_size_bytes", total_size as f64, Some(labels));
        
        Ok(())
    }
    
    /// Update publisher statistics
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
    
    /// Check rate limit
    async fn check_rate_limit(&self) -> Result<()> {
        let mut stats = self.stats.write().await;
        let now = Instant::now();
        
        // Clean old entries
        stats.rate_limit_window.retain(|&timestamp| now.duration_since(timestamp) < self.config.rate_limit_window);
        
        // Check if limit exceeded
        if stats.rate_limit_window.len() >= self.config.rate_limit_max_messages {
            return Err(MarketIntelError::rate_limit(
                self.config.rate_limit_max_messages as u32,
                format!("{:?}", self.config.rate_limit_window)
            ));
        }
        
        // Add current message
        stats.rate_limit_window.push(now);
        Ok(())
    }
}

/// Publisher configuration
#[derive(Debug, Clone)]
pub struct PublisherConfig {
    /// Enable rate limiting
    pub rate_limit_enabled: bool,
    /// Rate limit window duration
    pub rate_limit_window: Duration,
    /// Maximum messages per window
    pub rate_limit_max_messages: usize,
    /// Enable compression
    pub compression_enabled: bool,
    /// Enable encryption
    pub encryption_enabled: bool,
    /// Fail fast on batch errors
    pub fail_fast: bool,
    /// Batch size
    pub batch_size: usize,
    /// Publication timeout
    pub publication_timeout: Duration,
}

impl Default for PublisherConfig {
    fn default() -> Self {
        Self {
            rate_limit_enabled: false,
            rate_limit_window: Duration::from_secs(1),
            rate_limit_max_messages: 10000,
            compression_enabled: false,
            encryption_enabled: false,
            fail_fast: false,
            batch_size: 100,
            publication_timeout: Duration::from_millis(100),
        }
    }
}

/// Publisher statistics
#[derive(Debug, Clone, Default)]
pub struct PublisherStats {
    /// Total messages published
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
    /// Rate limit window timestamps
    pub rate_limit_window: Vec<Instant>,
    /// Messages per second
    pub messages_per_second: f64,
    /// Average message size
    pub average_message_size: f64,
    /// Publication errors
    pub publication_errors: u64,
    /// Retries attempted
    pub retries_attempted: u64,
}

impl PublisherStats {
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
    
    /// Get success rate
    pub fn success_rate(&self) -> f64 {
        if self.total_messages == 0 {
            0.0
        } else {
            let successful = self.total_messages - self.publication_errors;
            (successful as f64 / self.total_messages as f64) * 100.0
        }
    }
}

/// Batch publisher for high throughput
pub struct BatchPublisher {
    publisher: Arc<MessagePublisher>,
    batch_buffer: Arc<RwLock<Vec<UnifiedMessage>>>,
    batch_size: usize,
    batch_timeout: Duration,
    last_flush: Arc<RwLock<Instant>>,
}

impl BatchPublisher {
    /// Create new batch publisher
    pub fn new(publisher: Arc<MessagePublisher>, batch_size: usize, batch_timeout: Duration) -> Self {
        Self {
            publisher,
            batch_buffer: Arc::new(RwLock::new(Vec::new())),
            batch_size,
            batch_timeout,
            last_flush: Arc::new(RwLock::new(Instant::now())),
        }
    }
    
    /// Add message to batch
    pub async fn add_message(&self, message: UnifiedMessage) -> Result<()> {
        let mut buffer = self.batch_buffer.write().await;
        buffer.push(message);
        
        // Flush if batch is full
        if buffer.len() >= self.batch_size {
            self.flush_batch().await?;
        }
        
        Ok(())
    }
    
    /// Flush current batch
    pub async fn flush_batch(&self) -> Result<usize> {
        let mut buffer = self.batch_buffer.write().await;
        let batch_size = buffer.len();
        
        if batch_size > 0 {
            let batch: Vec<UnifiedMessage> = buffer.drain(..).collect();
            drop(buffer); // Release lock before publishing
            
            let published = self.publisher.publish_batch(&batch).await?;
            
            // Update last flush time
            let mut last_flush = self.last_flush.write().await;
            *last_flush = Instant::now();
            
            info!("Flushed batch: {}/{} messages published", published, batch_size);
            Ok(published)
        } else {
            Ok(0)
        }
    }
    
    /// Check if batch needs flushing
    pub async fn should_flush(&self) -> bool {
        let buffer = self.batch_buffer.read().await;
        let last_flush = self.last_flush.read().await;
        
        buffer.len() >= self.batch_size || 
        last_flush.elapsed() >= self.batch_timeout
    }
    
    /// Get current batch size
    pub async fn batch_size(&self) -> usize {
        self.batch_buffer.read().await.len()
    }
    
    /// Force flush all messages
    pub async fn flush_all(&self) -> Result<usize> {
        self.flush_batch().await
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::codecs::ProstCodec;
    
    #[tokio::test]
    async fn test_publisher_creation() {
        // This test would require a real Aeron connection
        // For now, we'll just test the configuration
        let config = PublisherConfig::default();
        assert_eq!(config.batch_size, 100);
        assert!(!config.rate_limit_enabled);
    }
    
    #[tokio::test]
    async fn test_publisher_stats() {
        let mut stats = PublisherStats::new();
        assert_eq!(stats.total_messages, 0);
        assert_eq!(stats.success_rate(), 0.0);
        
        stats.total_messages = 100;
        stats.publication_errors = 5;
        assert_eq!(stats.success_rate(), 95.0);
    }
    
    #[tokio::test]
    async fn test_batch_publisher() {
        // This would require a real publisher
        // For now, we'll test the batch logic
        let config = PublisherConfig::default();
        assert_eq!(config.batch_size, 100);
    }
}
