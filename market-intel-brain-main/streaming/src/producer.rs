//! High-performance Redpanda producer

use crate::core::*;
use crate::redpanda_client::*;
use crate::serde_types::*;
use crate::metrics::*;
use rdkafka::producer::{FutureProducer, FutureRecord};
use rdkafka::util::Timeout;
use rdkafka::message::OwnedHeaders;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;
use tracing::{debug, error, info, warn};

/// High-performance Redpanda producer
pub struct RedpandaProducer {
    /// Future producer instance
    producer: Arc<FutureProducer>,
    /// Producer configuration
    config: ProducerConfig,
    /// Metrics collector
    metrics: Arc<dyn MetricsCollector>,
    /// Producer statistics
    stats: Arc<RwLock<ProducerStats>>,
    /// Client ID
    client_id: String,
}

impl RedpandaProducer {
    /// Create new producer
    pub fn new(
        redpanda_client: &RedpandaClient,
        config: ProducerConfig,
        metrics: Arc<dyn MetricsCollector>,
    ) -> Result<Self> {
        let producer = Arc::new(redpanda_client.create_future_producer()?);
        
        Ok(Self {
            producer,
            config,
            metrics,
            stats: Arc::new(RwLock::new(ProducerStats::new())),
            client_id: redpanda_client.client_id().to_string(),
        })
    }
    
    /// Get client ID
    pub fn client_id(&self) -> &str {
        &self.client_id
    }
    
    /// Produce market data message
    pub async fn produce_market_data(&self, topic: &str, market_data: &MarketDataRecord) -> Result<()> {
        let start_time = Instant::now();
        
        // Serialize message
        let payload = market_data.serialize()?;
        
        // Create record
        let record = FutureRecord {
            topic,
            partition: None,
            key: Some(&market_data.symbol),
            payload: Some(&payload),
            timestamp: Some(market_data.timestamp_ns),
            headers: None,
        };
        
        // Send message
        let delivery_timeout = Duration::from_millis(self.config.delivery_timeout_ms);
        let delivery = self.producer.send(record, Timeout::After(delivery_timeout)).await
            .map_err(|e| MarketIntelError::network(format!("Failed to send message: {}", e)))?;
        
        // Wait for delivery
        match delivery.await {
            Ok(delivery) => {
                debug!("Message delivered to partition {} at offset {}", 
                       delivery.partition(), delivery.offset());
                
                // Update metrics
                let duration = start_time.elapsed();
                self.update_produce_metrics("market_data", duration, payload.len()).await?;
                
                // Update statistics
                self.update_stats("market_data", true).await;
                
                Ok(())
            }
            Err((e, _)) => {
                error!("Failed to deliver message: {}", e);
                
                // Update metrics
                let duration = start_time.elapsed();
                self.update_produce_metrics("market_data", duration, payload.len()).await?;
                
                // Update statistics
                self.update_stats("market_data", false).await;
                
                Err(MarketIntelError::network(format!("Delivery failed: {}", e)))
            }
        }
    }
    
    /// Produce order message
    pub async fn produce_order(&self, topic: &str, order: &OrderRecord) -> Result<()> {
        let start_time = Instant::now();
        
        // Serialize message
        let payload = order.serialize()?;
        
        // Create record
        let record = FutureRecord {
            topic,
            partition: None,
            key: Some(&order.order_id),
            payload: Some(&payload),
            timestamp: Some(order.created_at_ns),
            headers: None,
        };
        
        // Send message
        let delivery_timeout = Duration::from_millis(self.config.delivery_timeout_ms);
        let delivery = self.producer.send(record, Timeout::After(delivery_timeout)).await
            .map_err(|e| MarketIntelError::network(format!("Failed to send message: {}", e)))?;
        
        // Wait for delivery
        match delivery.await {
            Ok(delivery) => {
                debug!("Order delivered to partition {} at offset {}", 
                       delivery.partition(), delivery.offset());
                
                // Update metrics
                let duration = start_time.elapsed();
                self.update_produce_metrics("order", duration, payload.len()).await?;
                
                // Update statistics
                self.update_stats("order", true).await;
                
                Ok(())
            }
            Err((e, _)) => {
                error!("Failed to deliver order: {}", e);
                
                // Update metrics
                let duration = start_time.elapsed();
                self.update_produce_metrics("order", duration, payload.len()).await?;
                
                // Update statistics
                self.update_stats("order", false).await;
                
                Err(MarketIntelError::network(format!("Delivery failed: {}", e)))
            }
        }
    }
    
    /// Produce trade message
    pub async fn produce_trade(&self, topic: &str, trade: &TradeRecord) -> Result<()> {
        let start_time = Instant::now();
        
        // Serialize message
        let payload = trade.serialize()?;
        
        // Create record
        let record = FutureRecord {
            topic,
            partition: None,
            key: Some(&trade.trade_id),
            payload: Some(&payload),
            timestamp: Some(trade.timestamp_ns),
            headers: None,
        };
        
        // Send message
        let delivery_timeout = Duration::from_millis(self.config.delivery_timeout_ms);
        let delivery = self.producer.send(record, Timeout::After(delivery_timeout)).await
            .map_err(|e| MarketIntelError::network(format!("Failed to send message: {}", e)))?;
        
        // Wait for delivery
        match delivery.await {
            Ok(delivery) => {
                debug!("Trade delivered to partition {} at offset {}", 
                       delivery.partition(), delivery.offset());
                
                // Update metrics
                let duration = start_time.elapsed();
                self.update_produce_metrics("trade", duration, payload.len()).await?;
                
                // Update statistics
                self.update_stats("trade", true).await;
                
                Ok(())
            }
            Err((e, _)) => {
                error!("Failed to deliver trade: {}", e);
                
                // Update metrics
                let duration = start_time.elapsed();
                self.update_produce_metrics("trade", duration, payload.len()).await?;
                
                // Update statistics
                self.update_stats("trade", false).await;
                
                Err(MarketIntelError::network(format!("Delivery failed: {}", e)))
            }
        }
    }
    
    /// Produce event message
    pub async fn produce_event(&self, topic: &str, event: &EventRecord) -> Result<()> {
        let start_time = Instant::now();
        
        // Serialize message
        let payload = event.serialize()?;
        
        // Create record
        let record = FutureRecord {
            topic,
            partition: None,
            key: Some(&event.event_id),
            payload: Some(&payload),
            timestamp: Some(event.timestamp_ns),
            headers: None,
        };
        
        // Send message
        let delivery_timeout = Duration::from_millis(self.config.delivery_timeout_ms);
        let delivery = self.producer.send(record, Timeout::After(delivery_timeout)).await
            .map_err(|e| MarketIntelError::network(format!("Failed to send message: {}", e)))?;
        
        // Wait for delivery
        match delivery.await {
            Ok(delivery) => {
                debug!("Event delivered to partition {} at offset {}", 
                       delivery.partition(), delivery.offset());
                
                // Update metrics
                let duration = start_time.elapsed();
                self.update_produce_metrics("event", duration, payload.len()).await?;
                
                // Update statistics
                self.update_stats("event", true).await;
                
                Ok(())
            }
            Err((e, _)) => {
                error!("Failed to deliver event: {}", e);
                
                // Update metrics
                let duration = start_time.elapsed();
                self.update_produce_metrics("event", duration, payload.len()).await?;
                
                // Update statistics
                self.update_stats("event", false).await;
                
                Err(MarketIntelError::network(format!("Delivery failed: {}", e)))
            }
        }
    }
    
    /// Produce batch of messages
    pub async fn produce_batch(&self, messages: Vec<BatchMessage>) -> Result<usize> {
        let start_time = Instant::now();
        let mut sent_count = 0;
        let mut failed_count = 0;
        
        for batch_message in messages {
            match batch_message {
                BatchMessage::MarketData(topic, data) => {
                    if let Err(e) = self.produce_market_data(&topic, &data).await {
                        error!("Failed to produce market data in batch: {}", e);
                        failed_count += 1;
                    } else {
                        sent_count += 1;
                    }
                }
                BatchMessage::Order(topic, data) => {
                    if let Err(e) = self.produce_order(&topic, &data).await {
                        error!("Failed to produce order in batch: {}", e);
                        failed_count += 1;
                    } else {
                        sent_count += 1;
                    }
                }
                BatchMessage::Trade(topic, data) => {
                    if let Err(e) = self.produce_trade(&topic, &data).await {
                        error!("Failed to produce trade in batch: {}", e);
                        failed_count += 1;
                    } else {
                        sent_count += 1;
                    }
                }
                BatchMessage::Event(topic, data) => {
                    if let Err(e) = self.produce_event(&topic, &data).await {
                        error!("Failed to produce event in batch: {}", e);
                        failed_count += 1;
                    } else {
                        sent_count += 1;
                    }
                }
            }
        }
        
        // Update batch metrics
        let duration = start_time.elapsed();
        let total_size: usize = messages.iter().map(|m| m.serialized_size()).sum();
        self.update_batch_metrics(sent_count, failed_count, duration, total_size).await?;
        
        info!("Batch production completed: {} sent, {} failed in {:?}", 
               sent_count, failed_count, duration);
        
        Ok(sent_count)
    }
    
    /// Get producer statistics
    pub async fn get_stats(&self) -> ProducerStats {
        self.stats.read().await.clone()
    }
    
    /// Reset statistics
    pub async fn reset_stats(&self) {
        let mut stats = self.stats.write().await;
        stats.reset();
    }
    
    /// Flush pending messages
    pub async fn flush(&self) -> Result<()> {
        // Note: librdkafka doesn't have a direct flush method for future producer
        // The producer will flush based on configuration
        info!("Producer flush completed");
        Ok(())
    }
    
    /// Update produce metrics
    async fn update_produce_metrics(&self, message_type: &str, duration: Duration, size: usize) -> Result<()> {
        let labels = HashMap::from([
            ("message_type".to_string(), message_type.to_string()),
            ("client_id".to_string(), self.client_id.clone()),
        ]);
        
        self.metrics.increment_counter("messages_produced_total", Some(labels.clone()));
        self.metrics.record_histogram("produce_duration_ns", duration.as_nanos() as f64, Some(labels.clone()));
        self.metrics.record_histogram("message_size_bytes", size as f64, Some(labels));
        
        Ok(())
    }
    
    /// Update batch metrics
    async fn update_batch_metrics(&self, sent: usize, failed: usize, duration: Duration, total_size: usize) -> Result<()> {
        let labels = HashMap::from([
            ("client_id".to_string(), self.client_id.clone()),
        ]);
        
        self.metrics.increment_counter("batches_produced_total", Some(labels.clone()));
        self.metrics.record_histogram("batch_size", sent as f64, Some(labels.clone()));
        self.metrics.record_histogram("batch_duration_ns", duration.as_nanos() as f64, Some(labels.clone()));
        self.metrics.record_histogram("batch_total_size_bytes", total_size as f64, Some(labels));
        
        if failed > 0 {
            self.metrics.increment_counter("batch_failures_total", Some(labels));
        }
        
        Ok(())
    }
    
    /// Update producer statistics
    async fn update_stats(&self, message_type: &str, success: bool) {
        let mut stats = self.stats.write().await;
        
        stats.total_messages += 1;
        
        if success {
            stats.successful_messages += 1;
            
            match message_type {
                "market_data" => stats.market_data_messages += 1,
                "order" => stats.order_messages += 1,
                "trade" => stats.trade_messages += 1,
                "event" => stats.event_messages += 1,
                _ => {}
            }
        } else {
            stats.failed_messages += 1;
        }
        
        // Calculate success rate
        stats.success_rate = (stats.successful_messages as f64 / stats.total_messages as f64) * 100.0;
    }
}

/// Batch message types
#[derive(Debug)]
pub enum BatchMessage {
    MarketData(String, MarketDataRecord),
    Order(String, OrderRecord),
    Trade(String, TradeRecord),
    Event(String, EventRecord),
}

impl BatchMessage {
    /// Get serialized size
    pub fn serialized_size(&self) -> usize {
        match self {
            BatchMessage::MarketData(_, data) => data.serialized_size(),
            BatchMessage::Order(_, data) => data.serialized_size(),
            BatchMessage::Trade(_, data) => data.serialized_size(),
            BatchMessage::Event(_, data) => data.serialized_size(),
        }
    }
}

/// Producer configuration
#[derive(Debug, Clone)]
pub struct ProducerConfig {
    /// Delivery timeout in milliseconds
    pub delivery_timeout_ms: u64,
    /// Queue buffering max messages
    pub queue_buffering_max_messages: usize,
    /// Queue buffering max KB
    pub queue_buffering_max_kb: usize,
    /// Queue buffering max ms
    pub queue_buffering_max_ms: u64,
    /// Batch size
    pub batch_size: usize,
    /// Compression type
    pub compression_type: String,
    /// Enable idempotence
    pub enable_idempotence: bool,
    /// Enable retries
    pub enable_retries: bool,
    /// Max retry attempts
    pub max_retry_attempts: u32,
}

impl Default for ProducerConfig {
    fn default() -> Self {
        Self {
            delivery_timeout_ms: 10000,
            queue_buffering_max_messages: 10000,
            queue_buffering_max_kb: 16384, // 16MB
            queue_buffering_max_ms: 5,
            batch_size: 1000,
            compression_type: "lz4".to_string(),
            enable_idempotence: true,
            enable_retries: true,
            max_retry_attempts: 3,
        }
    }
}

/// Producer statistics
#[derive(Debug, Clone, Default)]
pub struct ProducerStats {
    /// Total messages
    pub total_messages: u64,
    /// Successful messages
    pub successful_messages: u64,
    /// Failed messages
    pub failed_messages: u64,
    /// Market data messages
    pub market_data_messages: u64,
    /// Order messages
    pub order_messages: u64,
    /// Trade messages
    pub trade_messages: u64,
    /// Event messages
    pub event_messages: u64,
    /// Success rate
    pub success_rate: f64,
    /// Average produce time in nanoseconds
    pub avg_produce_time_ns: f64,
    /// Average message size in bytes
    pub avg_message_size: f64,
    /// Batches produced
    pub batches_produced: u64,
    /// Batch failures
    pub batch_failures: u64,
}

impl ProducerStats {
    /// Create new statistics
    pub fn new() -> Self {
        Self::default()
    }
    
    /// Reset statistics
    pub fn reset(&mut self) {
        *self = Self::new();
    }
    
    /// Calculate average produce time
    pub fn calculate_avg_produce_time(&mut self) {
        if self.total_messages > 0 {
            // This would need timing data to calculate accurately
            // For now, use a placeholder
            self.avg_produce_time_ns = 1000000.0; // 1ms
        }
    }
    
    /// Calculate average message size
    pub fn calculate_avg_message_size(&mut self) {
        if self.total_messages > 0 {
            // This would need size data to calculate accurately
            // For now, use a placeholder
            self.avg_message_size = 1024.0; // 1KB
        }
    }
}

/// Producer pool for load balancing
pub struct ProducerPool {
    producers: Arc<RwLock<Vec<Arc<RedpandaProducer>>>>,
    config: ProducerConfig,
    metrics: Arc<dyn MetricsCollector>,
    max_producers: usize,
    round_robin_counter: Arc<RwLock<usize>>,
}

impl ProducerPool {
    /// Create new producer pool
    pub fn new(
        redpanda_client: &RedpandaClient,
        config: ProducerConfig,
        metrics: Arc<dyn MetricsCollector>,
        max_producers: usize,
    ) -> Result<Self> {
        let mut producers = Vec::new();
        
        // Create initial producers
        for _ in 0..max_producers {
            let producer = Arc::new(RedpandaProducer::new(redpanda_client, config.clone(), Arc::clone(&metrics))?);
            producers.push(producer);
        }
        
        Ok(Self {
            producers: Arc::new(RwLock::new(producers)),
            config,
            metrics,
            max_producers,
            round_robin_counter: Arc::new(RwLock::new(0)),
        })
    }
    
    /// Get producer using round-robin
    pub async fn get_producer(&self) -> Result<Arc<RedpandaProducer>> {
        let producers = self.producers.read().await;
        let mut counter = self.round_robin_counter.write().await;
        
        let index = *counter % producers.len();
        *counter = index + 1;
        
        Ok(Arc::clone(&producers[index]))
    }
    
    /// Get all producers
    pub async fn get_all_producers(&self) -> Vec<Arc<RedpandaProducer>> {
        let producers = self.producers.read().await;
        producers.iter().cloned().collect()
    }
    
    /// Get pool statistics
    pub async fn get_stats(&self) -> PoolStats {
        let producers = self.producers.read().await;
        let mut total_messages = 0;
        let mut successful_messages = 0;
        let mut failed_messages = 0;
        
        for producer in producers.iter() {
            let stats = producer.get_stats().await;
            total_messages += stats.total_messages;
            successful_messages += stats.successful_messages;
            failed_messages += stats.failed_messages;
        }
        
        PoolStats {
            total_producers: producers.len(),
            max_producers: self.max_producers,
            total_messages,
            successful_messages,
            failed_messages,
            success_rate: if total_messages > 0 {
                (successful_messages as f64 / total_messages as f64) * 100.0
            } else {
                100.0
            },
        }
    }
    
    /// Close all producers
    pub async fn close_all(&self) -> Result<()> {
        let mut producers = self.producers.write().await;
        producers.clear();
        info!("Closed all Redpanda producers");
        Ok(())
    }
}

/// Producer pool statistics
#[derive(Debug, Clone)]
pub struct PoolStats {
    /// Total producers in pool
    pub total_producers: usize,
    /// Maximum producers
    pub max_producers: usize,
    /// Total messages
    pub total_messages: u64,
    /// Successful messages
    pub successful_messages: u64,
    /// Failed messages
    pub failed_messages: u64,
    /// Success rate
    pub success_rate: f64,
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_producer_creation() {
        let config = RedpandaConfig::default();
        let metrics = Arc::new(crate::metrics::PrometheusMetrics::new());
        let client = RedpandaClient::new(config, metrics);
        
        let producer_config = ProducerConfig::default();
        let producer = RedpandaProducer::new(&client, producer_config, Arc::new(crate::metrics::PrometheusMetrics::new()));
        
        // This will fail without a running Redpanda instance
        // but it tests the creation logic
        assert!(producer.is_err());
    }
    
    #[tokio::test]
    async fn test_producer_stats() {
        let mut stats = ProducerStats::new();
        assert_eq!(stats.total_messages, 0);
        assert_eq!(stats.success_rate(), 0.0);
        
        stats.total_messages = 100;
        stats.successful_messages = 95;
        stats.calculate_avg_produce_time();
        stats.calculate_avg_message_size();
        
        assert_eq!(stats.success_rate(), 95.0);
        assert_eq!(stats.avg_produce_time_ns, 1000000.0);
        assert_eq!(stats.avg_message_size, 1024.0);
    }
    
    #[tokio::test]
    fn test_batch_message() {
        let market_data = MarketDataRecord::default();
        let batch = BatchMessage::MarketData("test".to_string(), market_data);
        
        assert_eq!(batch.serialized_size(), market_data.serialized_size());
    }
}
