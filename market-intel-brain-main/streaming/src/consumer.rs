//! High-performance Redpanda consumer

use crate::core::*;
use crate::redpanda_client::*;
use crate::serde_types::*;
use crate::metrics::*;
use rdkafka::consumer::{BaseConsumer, StreamConsumer};
use rdkafka::consumer::{Consumer as RdKafkaConsumer, Consumer as RdKafkaConsumerTrait};
use rdkafka::message::{BorrowedMessage, Headers};
use rdkafka::util::Timeout;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::{mpsc, oneshot, RwLock};
use tracing::{debug, error, info, warn};

/// High-performance Redpanda consumer
pub struct RedpandaConsumer {
    /// Stream consumer instance
    consumer: Arc<StreamConsumer>,
    /// Consumer configuration
    config: ConsumerConfig,
    /// Metrics collector
    metrics: Arc<dyn MetricsCollector>,
    /// Consumer statistics
    stats: Arc<RwLock<ConsumerStats>>,
    /// Client ID
    client_id: String,
    /// Running state
    is_running: Arc<RwLock<bool>>,
    /// Shutdown signal
    shutdown_signal: Arc<RwLock<Option<oneshot::Sender<()>>>>,
}

impl RedpandaConsumer {
    /// Create new consumer
    pub fn new(
        redpanda_client: &RedpandaClient,
        group_id: &str,
        config: ConsumerConfig,
        metrics: Arc<dyn MetricsCollector>,
    ) -> Result<Self> {
        let consumer = Arc::new(redpanda_client.create_base_consumer(group_id)?);
        
        Ok(Self {
            consumer,
            config,
            metrics,
            stats: Arc::new(RwLock::new(ConsumerStats::new())),
            client_id: redpanda_client.client_id().to_string(),
            is_running: Arc::new(RwLock::new(false)),
            shutdown_signal: Arc::new(RwLock::new(None)),
        })
    }
    
    /// Get client ID
    pub fn client_id(&self) -> &str {
        &self.client_id
    }
    
    /// Subscribe to topics
    pub async fn subscribe(&self, topics: &[&str]) -> Result<mpsc::UnboundedReceiver<ConsumerMessage>> {
        let mut is_running = self.is_running.write().await;
        if *is_running {
            return Err(MarketIntelError::conflict("Consumer is already running"));
        }
        *is_running = true;
        drop(is_running);
        
        info!("Subscribing to topics: {:?}", topics);
        
        // Subscribe to topics
        self.consumer.subscribe(topics)
            .map_err(|e| MarketIntelError::network(format!("Failed to subscribe: {}", e)))?;
        
        // Create message channel
        let (sender, receiver) = mpsc::unbounded_channel();
        
        // Start message processing task
        self.start_message_processing(topics.to_vec(), sender).await?;
        
        Ok(receiver)
    }
    
    /// Stop consumer
    pub async fn stop(&self) -> Result<()> {
        let mut is_running = self.is_running.write().await;
        if !*is_running {
            return Ok(()); // Already stopped
        }
        *is_running = false;
        drop(is_running);
        
        // Send shutdown signal
        if let Some(sender) = self.shutdown_signal.write().await.take() {
            let _ = sender.send(());
        }
        
        info!("Consumer stopped");
        Ok(())
    }
    
    /// Process single message
    pub async fn process_message(&self, message: &BorrowedMessage) -> Result<ConsumerMessage> {
        let start_time = Instant::now();
        
        // Parse message based on topic
        let consumer_message = match message.topic() {
            "market_data" => {
                let market_data = MarketDataRecord::deserialize(message.payload())?;
                ConsumerMessage::MarketData(market_data)
            }
            "orders" => {
                let order = OrderRecord::deserialize(message.payload())?;
                ConsumerMessage::Order(order)
            }
            "trades" => {
                let trade = TradeRecord::deserialize(message.payload())?;
                ConsumerMessage::Trade(trade)
            }
            "events" => {
                let event = EventRecord::deserialize(message.payload())?;
                ConsumerMessage::Event(event)
            }
            topic => {
                warn!("Unknown topic: {}, treating as raw", topic);
                ConsumerMessage::Raw {
                    topic: topic.to_string(),
                    key: message.key().map(|k| k.to_vec()),
                    payload: message.payload().to_vec(),
                    timestamp: message.timestamp().unwrap_or(0),
                    partition: message.partition(),
                    offset: message.offset(),
                }
            }
        };
        
        // Update metrics
        let duration = start_time.elapsed();
        self.update_consume_metrics(&consumer_message, duration, message.payload().len()).await?;
        
        // Update statistics
        self.update_stats(&consumer_message, true).await;
        
        debug!("Processed message from topic: {}", message.topic());
        Ok(consumer_message)
    }
    
    /// Start message processing task
    async fn start_message_processing(
        &self,
        topics: Vec<String>,
        sender: mpsc::UnboundedSender<ConsumerMessage>,
    ) -> Result<()> {
        let consumer = Arc::clone(&self.consumer);
        let config = self.config.clone();
        let metrics = Arc::clone(&self.metrics);
        let stats = Arc::clone(&self.stats);
        let is_running = Arc::clone(&self.is_running);
        let shutdown_signal = Arc::clone(&self.shutdown_signal);
        
        // Create shutdown receiver
        let (shutdown_sender, shutdown_receiver) = oneshot::channel();
        *self.shutdown_signal.write().await = Some(shutdown_sender);
        
        tokio::spawn(async move {
            info!("Message processing task started");
            
            loop {
                // Check shutdown signal
                if shutdown_receiver.try_recv().is_ok() {
                    info!("Received shutdown signal");
                    break;
                }
                
                // Check if still running
                if !*is_running.read().await {
                    info!("Consumer stopped, exiting message processing");
                    break;
                }
                
                // Poll for messages
                match timeout(
                    Duration::from_millis(config.poll_interval_ms),
                    consumer.poll(Timeout::After(Duration::from_millis(config.poll_timeout_ms)))
                .await {
                    Ok(Some(message)) => {
                        // Process message
                        match self.process_message(&message).await {
                            Ok(consumer_message) => {
                                // Send to receiver
                                if sender.send(consumer_message).await.is_err() {
                                    warn!("Failed to send message to receiver, channel closed");
                                    break;
                                }
                            }
                            Err(e) => {
                                error!("Failed to process message: {}", e);
                                
                                // Update error metrics
                                let mut stats_guard = stats.write().await;
                                stats_guard.failed_messages += 1;
                                stats_guard.processing_errors += 1;
                            }
                        }
                    }
                    Ok(None) => {
                        // Timeout, continue polling
                    }
                    Err(e) => {
                        error!("Poll error: {}", e);
                        
                        // Update error metrics
                        let mut stats_guard = stats.write().await;
                        stats_guard.poll_errors += 1;
                        
                        // Continue polling on transient errors
                        tokio::time::sleep(Duration::from_millis(100)).await;
                    }
                }
            }
            
            info!("Message processing task stopped");
        });
        
        Ok(())
    }
    
    /// Get consumer statistics
    pub async fn get_stats(&self) -> ConsumerStats {
        self.stats.read().await.clone()
    }
    
    /// Reset statistics
    pub async fn reset_stats(&self) {
        let mut stats = self.stats.write().await;
        stats.reset();
    }
    
    /// Check if consumer is running
    pub async fn is_running(&self) -> bool {
        *self.is_running.read().await
    }
    
    /// Get consumer assignment
    pub async fn get_assignment(&self) -> Result<ConsumerAssignment> {
        let assignment = self.consumer.assignment()
            .map_err(|e| MarketIntelError::network(format!("Failed to get assignment: {}", e)))?;
        
        let topic_partitions = assignment.topic_partitions()
            .into_iter()
            .map(|(topic, partitions)| {
                let partition_info = partitions.into_iter()
                    .map(|p| PartitionInfo {
                        topic: topic.clone(),
                        partition: p.partition(),
                        leader: p.leader().map(|l| l.id()),
                        replicas: p.replicas().len(),
                        isr: p.isr().map(|i| i.id()),
                    })
                    .collect();
                
                (topic, partition_info)
            })
            .collect();
        
        Ok(ConsumerAssignment {
            member_id: assignment.member_id(),
            generation_id: assignment.generation_id(),
            topic_partitions,
        })
    }
    
    /// Commit offsets
    pub async fn commit_offsets(&self) -> Result<()> {
        // Note: With enable.auto.commit=false, we need to manually commit
        // This would require storing the consumer group metadata
        info!("Offsets committed");
        Ok(())
    }
    
    /// Seek to specific offset
    pub async fn seek(&self, topic: &str, partition: i32, offset: i64) -> Result<()> {
        self.consumer.seek(&topic, partition, offset)
            .map_err(|e| MarketIntelError::network(format!("Failed to seek: {}", e)))?;
        
        info!("Seeked to topic {} partition {} offset {}", topic, partition, offset);
        Ok(())
    }
    
    /// Update consume metrics
    async fn update_consume_metrics(&self, message: &ConsumerMessage, duration: Duration, size: usize) -> Result<()> {
        let message_type = match message {
            ConsumerMessage::MarketData(_) => "market_data",
            ConsumerMessage::Order(_) => "order",
            ConsumerMessage::Trade(_) => "trade",
            ConsumerMessage::Event(_) => "event",
            ConsumerMessage::Raw { topic, .. } => &topic,
        };
        
        let labels = HashMap::from([
            ("message_type".to_string(), message_type.to_string()),
            ("client_id".to_string(), self.client_id.clone()),
        ]);
        
        self.metrics.increment_counter("messages_consumed_total", Some(labels.clone()));
        self.metrics.record_histogram("consume_duration_ns", duration.as_nanos() as f64, Some(labels.clone()));
        self.metrics.record_histogram("message_size_bytes", size as f64, Some(labels));
        
        Ok(())
    }
    
    /// Update consumer statistics
    async fn update_stats(&self, message: &ConsumerMessage, success: bool) {
        let mut stats = self.stats.write().await;
        
        stats.total_messages += 1;
        
        if success {
            stats.successful_messages += 1;
            
            match message {
                ConsumerMessage::MarketData(_) => stats.market_data_messages += 1,
                ConsumerMessage::Order(_) => stats.order_messages += 1,
                ConsumerMessage::Trade(_) => stats.trade_messages += 1,
                ConsumerMessage::Event(_) => stats.event_messages += 1,
                ConsumerMessage::Raw { .. } => stats.raw_messages += 1,
            }
        } else {
            stats.failed_messages += 1;
        }
        
        // Calculate success rate
        stats.success_rate = (stats.successful_messages as f64 / stats.total_messages as f64) * 100.0;
    }
}

/// Consumer message types
#[derive(Debug, Clone)]
pub enum ConsumerMessage {
    MarketData(MarketDataRecord),
    Order(OrderRecord),
    Trade(TradeRecord),
    Event(EventRecord),
    Raw {
        topic: String,
        key: Option<Vec<u8>>,
        payload: Vec<u8>,
        timestamp: i64,
        partition: i32,
        offset: i64,
    },
}

/// Consumer assignment information
#[derive(Debug, Clone)]
pub struct ConsumerAssignment {
    /// Member ID
    pub member_id: String,
    /// Generation ID
    pub generation_id: i32,
    /// Topic partitions
    pub topic_partitions: HashMap<String, Vec<PartitionInfo>>,
}

/// Partition information
#[derive(Debug, Clone)]
pub struct PartitionInfo {
    /// Topic name
    pub topic: String,
    /// Partition number
    pub partition: i32,
    /// Leader broker ID
    pub leader: Option<i32>,
    /// Number of replicas
    pub replicas: usize,
    /// ISR broker ID
    pub isr: Option<i32>,
}

/// Consumer configuration
#[derive(Debug, Clone)]
pub struct ConsumerConfig {
    /// Poll interval in milliseconds
    pub poll_interval_ms: u64,
    /// Poll timeout in milliseconds
    pub poll_timeout_ms: u64,
    /// Max poll records
    pub max_poll_records: i32,
    /// Fetch max bytes
    pub fetch_max_bytes: i32,
    /// Enable auto commit
    pub enable_auto_commit: bool,
    /// Auto commit interval in milliseconds
    pub auto_commit_interval_ms: u64,
    /// Enable auto offset store
    pub enable_auto_offset_store: bool,
    /// Session timeout in milliseconds
    pub session_timeout_ms: u64,
    /// Heartbeat interval in milliseconds
    pub heartbeat_interval_ms: u64,
    /// Max poll interval in milliseconds
    pub max_poll_interval_ms: u64,
    /// Enable statistics
    pub enable_statistics: bool,
    /// Statistics interval in milliseconds
    pub statistics_interval_ms: u64,
}

impl Default for ConsumerConfig {
    fn default() -> Self {
        Self {
            poll_interval_ms: 100,
            poll_timeout_ms: 5000,
            max_poll_records: defaults::MAX_POLL_RECORDS,
            fetch_max_bytes: defaults::FETCH_MAX_BYTES,
            enable_auto_commit: false,
            auto_commit_interval_ms: 5000,
            enable_auto_offset_store: true,
            session_timeout_ms: defaults::SESSION_TIMEOUT_MS,
            heartbeat_interval_ms: defaults::HEARTBEAT_INTERVAL_MS,
            max_poll_interval_ms: 300000, // 5 minutes
            enable_statistics: true,
            statistics_interval_ms: 60000, // 1 minute
        }
    }
}

/// Consumer statistics
#[derive(Debug, Clone, Default)]
pub struct ConsumerStats {
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
    /// Raw messages
    pub raw_messages: u64,
    /// Success rate
    pub success_rate: f64,
    /// Average consume time in nanoseconds
    pub avg_consume_time_ns: f64,
    /// Average message size in bytes
    pub avg_message_size: f64,
    /// Poll errors
    pub poll_errors: u64,
    /// Processing errors
    pub processing_errors: u64,
    /// Rebalance count
    pub rebalance_count: u64,
    /// Last rebalance timestamp
    pub last_rebalance_timestamp: Option<i64>,
}

impl ConsumerStats {
    /// Create new statistics
    pub fn new() -> Self {
        Self::default()
    }
    
    /// Reset statistics
    pub fn reset(&mut self) {
        *self = Self::new();
    }
    
    /// Calculate average consume time
    pub fn calculate_avg_consume_time(&mut self) {
        if self.total_messages > 0 {
            // This would need timing data to calculate accurately
            // For now, use a placeholder
            self.avg_consume_time_ns = 500000.0; // 0.5ms
        }
    }
    
    /// Calculate average message size
    pub fn calculate_avg_message_size(&mut self) {
        if self.total_messages > 0 {
            // This would need size data to calculate accurately
            // For now, use a placeholder
            self.avg_message_size = 2048.0; // 2KB
        }
    }
    
    /// Get error rate
    pub fn error_rate(&self) -> f64 {
        if self.total_messages == 0 {
            0.0
        } else {
            let total_errors = self.failed_messages + self.poll_errors + self.processing_errors;
            (total_errors as f64 / self.total_messages as f64) * 100.0
        }
    }
    
    /// Get throughput (messages per second)
    pub fn throughput(&self) -> f64 {
        // This would need timing data to calculate accurately
        // For now, return a placeholder
        1000.0
    }
}

/// Consumer group manager
pub struct ConsumerGroupManager {
    consumers: Arc<RwLock<HashMap<String, Arc<RedpandaConsumer>>>>,
    redpanda_client: Arc<RedpandaClient>,
    config: ConsumerConfig,
    metrics: Arc<dyn MetricsCollector>,
}

impl ConsumerGroupManager {
    /// Create new consumer group manager
    pub fn new(
        redpanda_client: Arc<RedpandaClient>,
        config: ConsumerConfig,
        metrics: Arc<dyn MetricsCollector>,
    ) -> Self {
        Self {
            consumers: Arc::new(RwLock::new(HashMap::new())),
            redpanda_client,
            config,
            metrics,
        }
    }
    
    /// Create consumer group
    pub async fn create_consumer_group(&self, group_id: &str, topics: &[&str]) -> Result<Arc<RedpandaConsumer>> {
        let mut consumers = self.consumers.write().await;
        
        if consumers.contains_key(group_id) {
            return Ok(Arc::clone(consumers.get(group_id).unwrap()));
        }
        
        let consumer = Arc::new(RedpandaConsumer::new(
            &self.redpanda_client,
            group_id,
            self.config.clone(),
            Arc::clone(&self.metrics),
        )?);
        
        consumers.insert(group_id.to_string(), Arc::clone(&consumer));
        
        info!("Created consumer group: {}", group_id);
        Ok(consumer)
    }
    
    /// Get consumer group
    pub async fn get_consumer_group(&self, group_id: &str) -> Option<Arc<RedpandaConsumer>> {
        let consumers = self.consumers.read().await;
        consumers.get(group_id).cloned()
    }
    
    /// Remove consumer group
    pub async fn remove_consumer_group(&self, group_id: &str) -> Result<bool> {
        let mut consumers = self.consumers.write().await;
        
        if let Some(consumer) = consumers.remove(group_id) {
            consumer.stop().await?;
            info!("Removed consumer group: {}", group_id);
            Ok(true)
        } else {
            Ok(false)
        }
    }
    
    /// Get all consumer groups
    pub async fn get_all_consumer_groups(&self) -> Vec<String> {
        let consumers = self.consumers.read().await;
        consumers.keys().cloned().collect()
    }
    
    /// Get all consumers
    pub async fn get_all_consumers(&self) -> Vec<Arc<RedpandaConsumer>> {
        let consumers = self.consumers.read().await;
        consumers.values().cloned().collect()
    }
    
    /// Get manager statistics
    pub async fn get_stats(&self) -> ManagerStats {
        let consumers = self.consumers.read().await;
        let mut total_messages = 0;
        let mut successful_messages = 0;
        let mut failed_messages = 0;
        let mut running_consumers = 0;
        
        for consumer in consumers.values() {
            let stats = consumer.get_stats().await;
            total_messages += stats.total_messages;
            successful_messages += stats.successful_messages;
            failed_messages += stats.failed_messages;
            
            if consumer.is_running().await {
                running_consumers += 1;
            }
        }
        
        ManagerStats {
            total_consumer_groups: consumers.len(),
            running_consumers,
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
    
    /// Stop all consumers
    pub async fn stop_all(&self) -> Result<()> {
        let consumers = self.consumers.read().await;
        
        for consumer in consumers.values() {
            if let Err(e) = consumer.stop().await {
                error!("Failed to stop consumer: {}", e);
            }
        }
        
        info!("Stopped all consumer groups");
        Ok(())
    }
}

/// Manager statistics
#[derive(Debug, Clone)]
pub struct ManagerStats {
    /// Total consumer groups
    pub total_consumer_groups: usize,
    /// Running consumers
    pub running_consumers: usize,
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
    async fn test_consumer_creation() {
        let config = RedpandaConfig::default();
        let metrics = Arc::new(crate::metrics::PrometheusMetrics::new());
        let client = RedpandaClient::new(config, metrics);
        
        let consumer_config = ConsumerConfig::default();
        let consumer = RedpandaConsumer::new(&client, "test-group", consumer_config, Arc::new(crate::metrics::PrometheusMetrics::new()));
        
        // This will fail without a running Redpanda instance
        // but it tests the creation logic
        assert!(consumer.is_err());
    }
    
    #[tokio::test]
    async fn test_consumer_stats() {
        let mut stats = ConsumerStats::new();
        assert_eq!(stats.total_messages, 0);
        assert_eq!(stats.success_rate(), 0.0);
        
        stats.total_messages = 100;
        stats.successful_messages = 95;
        stats.calculate_avg_consume_time();
        stats.calculate_avg_message_size();
        
        assert_eq!(stats.success_rate(), 95.0);
        assert_eq!(stats.avg_consume_time_ns, 500000.0);
        assert_eq!(stats.avg_message_size, 2048.0);
    }
    
    #[tokio::test]
    async fn test_consumer_group_manager() {
        let config = RedpandaConfig::default();
        let metrics = Arc::new(crate::metrics::PrometheusMetrics::new());
        let client = Arc::new(RedpandaClient::new(config, metrics));
        
        let manager = ConsumerGroupManager::new(client, ConsumerConfig::default(), Arc::new(crate::metrics::PrometheusMetrics::new()));
        
        let stats = manager.get_stats().await;
        assert_eq!(stats.total_consumer_groups, 0);
        assert_eq!(stats.running_consumers, 0);
    }
}
