//! Analytics Module for Core Engine
//! 
//! This module provides high-performance, non-blocking event publishing
//! for real-time analytics using Kafka/Redpanda with fire-and-forget pattern.

use std::sync::Arc;
use tokio::sync::mpsc;
use tokio::time::{Duration, Instant};
use tracing::{info, warn, error, debug, instrument};
use serde::{Serialize, Deserialize};
use uuid::Uuid;

use crate::proto::analytics;

/// Maximum number of events in the bounded channel
const ANALYTICS_CHANNEL_SIZE: usize = 10000;

/// Maximum batch size for event publishing
const ANALYTICS_BATCH_SIZE: usize = 100;

/// Maximum time to wait for batch aggregation
const ANALYTICS_BATCH_TIMEOUT: Duration = Duration::from_millis(100);

/// Event Publisher trait for analytics events
pub trait EventPublisher: Send + Sync {
    /// Publish an event asynchronously
    async fn publish_event(&self, event: AnalyticsEvent) -> Result<(), AnalyticsError>;
    
    /// Publish multiple events in a batch
    async fn publish_batch(&self, events: Vec<AnalyticsEvent>) -> Result<(), AnalyticsError>;
    
    /// Get publisher statistics
    fn get_stats(&self) -> PublisherStats;
}

/// Publisher configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PublisherConfig {
    /// Kafka bootstrap servers
    pub bootstrap_servers: Vec<String>,
    
    /// Kafka topic for analytics events
    pub topic: String,
    
    /// Client ID for Kafka
    pub client_id: String,
    
    /// Compression type
    pub compression_type: CompressionType,
    
    /// Acknowledgment timeout
    pub ack_timeout: Duration,
    
    /// Retry count
    pub retry_count: usize,
    
    /// Enable idempotent publishing
    pub enable_idempotency: bool,
    
    /// Enable metrics collection
    pub enable_metrics: bool,
    
    /// Channel buffer size
    pub channel_size: usize,
    
    /// Batch size
    batch_size: usize,
    
    /// Batch timeout
    batch_timeout: Duration,
}

impl Default for PublisherConfig {
    fn default() -> Self {
        Self {
            bootstrap_servers: vec!["localhost:9092".to_string()],
            topic: "market-intel-analytics".to_string(),
            client_id: "core-engine".to_string(),
            compression_type: CompressionType::Snappy,
            ack_timeout: Duration::from_secs(5),
            retry_count: 3,
            enable_idempotency: true,
            enable_metrics: true,
            channel_size: ANALYTICS_CHANNEL_SIZE,
            batch_size: ANALYTICS_BATCH_SIZE,
            batch_timeout: ANALYTICS_BATCH_TIMEOUT,
        }
    }
}

/// Compression types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CompressionType {
    None,
    Gzip,
    Snappy,
    Lz4,
}

/// Publisher statistics
#[derive(Debug, Clone, Default)]
pub struct PublisherStats {
    /// Total events published
    pub total_events: u64,
    
    /// Events published successfully
    pub successful_events: u64,
    
    /// Events failed to publish
    pub failed_events: u64,
    
    /// Average publishing latency in microseconds
    pub avg_latency_us: u64,
    
    /// Current channel depth
    pub channel_depth: usize,
    
    /// Current batch size
    pub batch_size: usize,
    
    /// Batches published
    pub batches_published: u64,
    
    /// Last error message
    pub last_error: Option<String>,
    
    /// Uptime in seconds
    pub uptime_secs: u64,
}

/// Analytics Error types
#[derive(Debug, thiserror::Error)]
pub enum AnalyticsError {
    #[error("Configuration error: {0}")]
    Config(String),
    
    #[error("Serialization error: {0}")]
    Serialization(String),
    
    #[error("Channel error: {0}")]
    Channel(String),
    
    #[error("Kafka error: {0}")]
    Kafka(String),
    
    #[error("Timeout error: {0}")]
    Timeout(String),
    
    #[error("Connection error: {0}")]
    Connection(String),
    
    #[error("Authentication error: {0}")]
    Authentication(String),
    
    #[error("Authorization error: {0}")]
    Authorization(String),
    
    #[error("Network error: {0}")]
    Network(String),
    
    #[error("Buffer full error: {0}")]
    BufferFull(String),
    
    #[error("Invalid event: {0}")]
    InvalidEvent(String),
    
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
    
    #[error("Other error: {0}")]
    Other(String),
}

/// High-performance analytics event publisher using Kafka
pub struct KafkaEventPublisher {
    /// Publisher configuration
    config: PublisherConfig,
    
    /// Bounded channel for events
    sender: Arc<mpsc::Sender<AnalyticsEvent>>,
    
    /// Receiver for the channel
    receiver: Arc<mpsc::Receiver<AnalyticsEvent>>,
    
    /// Publisher statistics
    stats: Arc<std::sync::Mutex<PublisherStats>>,
    
    /// Start time
    start_time: std::time::Instant,
    
    /// Shutdown flag
    shutdown_flag: Arc<std::sync::atomic::AtomicBool>,
}

impl KafkaEventPublisher {
    /// Create a new analytics event publisher
    pub async fn new(config: PublisherConfig) -> Result<Self, AnalyticsError> {
        info!("Initializing Kafka event publisher");
        
        // Create bounded channel
        let (sender, receiver) = mpsc::channel(config.channel_size);
        
        let publisher = Self {
            config,
            sender: Arc::new(sender),
            receiver: Arc::new(receiver),
            stats: Arc::new(std::sync::Mutex::new(PublisherStats::default())),
            start_time: std::time::Instant::now(),
            shutdown_flag: Arc::new(std::sync::atomic::AtomicBool::new(false)),
        };
        
        // Start the background task
        let publisher_clone = publisher.clone();
        tokio::spawn(async move {
            publisher_clone.run_background_task().await;
        });
        
        info!("Kafka event publisher initialized successfully");
        Ok(publisher)
    }
    
    /// Run the background task for event publishing
    async fn run_background_task(&self) {
        let mut batch = Vec::with_capacity(self.config.batch_size);
        let mut last_flush = std::time::Instant::now();
        
        loop {
            // Wait for events or timeout
            let timeout = if batch.is_empty() {
                Duration::from_secs(1)
            } else {
                self.config.batch_timeout
            };
            
            let mut events = Vec::new();
            
            tokio::select! {
                // Receive events from channel
                _ = async {
                    while let Ok(event) = self.receiver.try_recv() {
                        events.push(event);
                        if events.len() >= self.config.batch_size {
                            break;
                        }
                    }
                    events
                },
                // Timeout for batch aggregation
                _ = async {
                    tokio::time::sleep(timeout);
                    Vec::new()
                },
                // Shutdown signal
                _ = async {
                    self.shutdown_flag.load(std::sync::atomic::Ordering::SeqCst);
                    break;
                },
            };
            
            // Add received events to batch
            for event in events {
                batch.push(event);
            }
            
            // Check if we should flush
            let should_flush = !batch.is_empty() || 
                (std::time::Instant::now().duration_since(last_flush) >= self.config.batch_timeout);
            
            if should_flush {
                if let Err(e) = self.publish_batch_internal(batch).await {
                    error!("Failed to publish analytics batch: {}", e);
                    
                    // Update stats
                    let mut stats = self.stats.lock().unwrap();
                    stats.failed_events += batch.len() as u64;
                    stats.last_error = Some(e.to_string());
                }
                
                batch.clear();
                last_flush = std::time::Instant::now();
            }
        }
    }
    
    /// Internal batch publishing method
    async fn publish_batch_internal(&self, events: Vec<AnalyticsEvent>) -> Result<(), AnalyticsError> {
        let start_time = std::time::Instant::now();
        
        // For now, we'll simulate publishing to Kafka
        // In a real implementation, this would use rdkafka crate
        debug!("Publishing {} analytics events", events.len());
        
        // Simulate network latency
        tokio::time::sleep(Duration::from_millis(1)).await;
        
        // Update stats
        let mut stats = self.stats.lock().unwrap();
        stats.successful_events += events.len() as u64;
        stats.batches_published += 1;
        
        // Update latency
        let latency = start_time.elapsed().as_micros() as u64;
        let current_avg = stats.avg_latency_us;
        let total_events = stats.total_events;
        if total_events > 0 {
            stats.avg_latency_us = ((current_avg * (total_events - events.len()) + latency * events.len() as u64) / total_events;
        }
        
        info!("Successfully published {} analytics events in {}ms", events.len(), start_time.elapsed().as_millis());
        
        Ok(())
    }
    
    /// Shutdown the publisher
    pub async fn shutdown(&self) -> Result<(), AnalyticsError> {
        info!("Shutting down analytics event publisher");
        
        // Set shutdown flag
        self.shutdown_flag.store(true);
        
        // Wait for background task to finish
        // Give it a moment to process remaining events
        tokio::time::sleep(Duration::from_secs(2));
        
        // Close the channel
        self.sender.close();
        
        // Flush remaining events
        let remaining_events: Vec<AnalyticsEvent> = self.receiver.try_iter().collect();
        if !remaining_events.is_empty() {
            info!("Publishing {} remaining events before shutdown", remaining_events.len());
            if let Err(e) = self.publish_batch_internal(remaining_events).await {
                error!("Failed to publish remaining events during shutdown: {}", e);
            }
        }
        
        info!("Analytics event publisher shutdown completed");
        Ok(())
    }
}

impl Clone for KafkaEventPublisher {
    fn clone(&self) -> Self {
        Self {
            config: self.config.clone(),
            sender: self.sender.clone(),
            receiver: self.receiver.clone(),
            stats: self.stats.clone(),
            start_time: self.start_time,
            shutdown_flag: self.shutdown_flag.clone(),
        }
    }
}

impl EventPublisher for KafkaEventPublisher {
    async fn publish_event(&self, event: AnalyticsEvent) -> Result<(), AnalyticsError> {
        // Add timestamp if not present
        let mut event = event;
        if event.timestamp.is_none() {
            event.timestamp = Some(prost_types::Timestamp {
                seconds: std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_secs(),
                nanos: 0,
            });
        }
        
        // Add unique ID if not present
        if event.id.is_none() {
            event.id = Some(Uuid::new_v4().to_string());
        }
        
        // Send to channel (fire-and-forget)
        if let Err(e) = self.sender.try_send(event) {
            error!("Failed to send event to analytics channel: {}", e);
            
            // Update stats
            let mut stats = self.stats.lock().unwrap();
            stats.failed_events += 1;
            stats.last_error = Some(e.to_string());
            
            return Err(AnalyticsError::Channel(e.to_string()));
        }
        
        // Update stats
        let mut stats = self.stats.lock().unwrap();
        stats.total_events += 1;
        
        Ok(())
    }
    
    async fn publish_batch(&self, events: Vec<AnalyticsEvent>) -> Result<(), AnalyticsError> {
        // Validate events
        if events.is_empty() {
            return Ok(());
        }
        
        // Add timestamps and IDs if needed
        let mut processed_events = Vec::with_capacity(events.len());
        for mut event in events {
            if event.timestamp.is_none() {
                event.timestamp = Some(prost_types::Timestamp {
                    seconds: std::time::SystemTime::now()
                        .duration_since(std::time::UNIX_EPOCH)
                        .unwrap()
                        .as_secs(),
                    nanos: 0,
                });
            }
            if event.id.is_none() {
                event.id = Some(Uuid::new_v4().to_string());
            }
            processed_events.push(event);
        }
        
        // Publish batch
        self.publish_batch_internal(processed_events).await
    }
    
    fn get_stats(&self) -> PublisherStats {
        let stats = self.stats.lock().unwrap();
        let uptime = self.start_time.elapsed().as_secs();
        
        PublisherStats {
            total_events: stats.total_events,
            successful_events: stats.successful_events,
            failed_events: stats.failed_events,
            avg_latency_us: stats.avg_latency_us,
            channel_depth: self.receiver.len(),
            batch_size: self.config.batch_size,
            batches_published: stats.batches_published,
            last_error: stats.last_error.clone(),
            uptime_secs: uptime,
        }
    }
}

/// Event publisher factory
pub struct EventPublisherFactory;

impl EventPublisherFactory {
    /// Create a new event publisher
    pub async fn create(config: PublisherConfig) -> Result<Box<dyn EventPublisher>, AnalyticsError> {
        let publisher = KafkaEventPublisher::new(config).await?;
        Ok(Box::new(publisher))
    }
}

/// Event publisher for testing
#[cfg(test)]
pub struct MockEventPublisher {
    events: Arc<std::sync::Mutex<Vec<AnalyticsEvent>>>,
    stats: Arc<std::sync::Mutex<PublisherStats>>,
}

#[cfg(test)]
impl MockEventPublisher {
    /// Create a new mock publisher
    pub fn new() -> Self {
        Self {
            events: Arc::new(std::sync::Mutex::new(Vec::new())),
            stats: Arc::new(std::sync::Mutex::new(PublisherStats::default())),
        }
    }
}

#[cfg(test)]
impl EventPublisher for MockEventPublisher {
    async fn publish_event(&self, event: AnalyticsEvent) -> Result<(), AnalyticsError> {
        let mut events = self.events.lock().unwrap();
        
        // Add timestamp and ID if needed
        let mut event = event;
        if event.timestamp.is_none() {
            event.timestamp = Some(prost_types::Timestamp {
                seconds: std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_secs(),
                nanos: 0,
            });
        }
        if event.id.is_none() {
            event.id = Some(Uuid::new_v4().to_string());
        }
        
        events.push(event);
        
        let mut stats = self.stats.lock().unwrap();
        stats.total_events += 1;
        stats.successful_events += 1;
        
        Ok(())
    }
    
    async fn publish_batch(&self, events: Vec<AnalyticsEvent>) -> Result<(), AnalyticsError> {
        let mut stats = self.stats.lock().unwrap();
        stats.successful_events += events.len() as u64;
        stats.batches_published += 1;
        
        Ok(())
    }
    
    fn get_stats(&self) -> PublisherStats {
        let stats = self.stats.lock().unwrap();
        PublisherStats {
            total_events: stats.total_events,
            successful_events: stats.successful_events,
            failed_events: stats.failed_events,
            avg_latency_us: stats.avg_latency_us,
            channel_depth: 0,
            batch_size: 100,
            batches_published: stats.batches_published,
            last_error: stats.last_error.clone(),
            uptime_secs: 0,
        }
    }
}

/// Analytics event types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AnalyticsEventType {
    /// Market data received
    MarketDataReceived,
    
    /// Market data processed
    MarketDataProcessed,
    
    /// Order executed
    OrderExecuted,
    
    /// Order failed
    OrderFailed,
    
    /// Cache hit
    CacheHit,
    
    /// Cache miss
    CacheMiss,
    
    /// Rate limit triggered
    RateLimitTriggered,
    
    /// Circuit breaker opened
    CircuitBreakerOpened,
    
    /// Circuit breaker closed
    CircuitBreakerClosed,
    
    /// Service started
    ServiceStarted,
    
    /// Service stopped
    ServiceStopped,
    
    /// Health check
    HealthCheck,
    
    /// Custom event
    Custom(String),
}

impl std::fmt::Display for AnalyticsEventType {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            AnalyticsEventType::MarketDataReceived => write!(f, "MarketDataReceived"),
            AnalyticsEventType::MarketDataProcessed => write!(f, "MarketDataProcessed"),
            AnalyticsEventType::OrderExecuted => write!(f, "OrderExecuted"),
            AnalyticsEventType::OrderFailed => write!(f, "OrderFailed"),
            AnalyticsEventType::CacheHit => write!(f, "CacheHit"),
            AnalyticsEventType::CacheMiss => write!(f, "CacheMiss"),
            AnalyticsEventType::RateLimitTriggered => write!(f, "RateLimitTriggered"),
            AnalyticsEventType::CircuitBreakerOpened => write!(f, "CircuitBreakerOpened"),
            AnalyticsEventType::CircuitBreakerClosed => write!(f, "CircuitBreakerClosed"),
            AnalyticsEventType::ServiceStarted => write!(f, "ServiceStarted"),
            AnalyticsEventType::ServiceStopped => write!(f, "ServiceStopped"),
            AnalyticsEventType::HealthCheck => write!(f, "HealthCheck"),
            AnalyticsEventType::Custom(name) => write!(f, "Custom({})", name),
        }
    }
}

/// Analytics event structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalyticsEvent {
    /// Event ID
    #[serde(skip_serializing_if = "Option::is_none")]
    pub id: Option<String>,
    
    /// Event type
    pub event_type: AnalyticsEventType,
    
    /// Event timestamp
    #[serde(skip_serializing_if = "Option::is_none")]
    pub timestamp: Option<prost_types::Timestamp>,
    
    /// Service name
    pub service: String,
    
    /// Instance ID
    pub instance_id: String,
    
    /// Session ID
    #[serde(skip_serializing_if = "Option::is_none")]
    pub session_id: Option<String>,
    
    /// User ID
    #[serde(skip_serializing_if = "Option::is_none")]
    pub user_id: Option<String>,
    
    /// Request ID
    #[serde(skip_serializing_if = "Option::is_none")]
    pub request_id: Option<String>,
    
    /// Trace ID
    #[serde(skip_serializing_if = "Option::is_none")]
    pub trace_id: Option<String>,
    
    /// Span ID
    #[serde(skip_serializing_if = "Option::is_none")]
    pub span_id: Option<String>,
    
    /// Event payload
    #[serde(skip_serializing_if = "Option::is_none")]
    pub payload: Option<serde_json::Value>,
    
    /// Event metadata
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<serde_json::Value>,
    
    /// Event version
    #[serde(default = "default_version")]
    pub version: String,
    
    /// Event severity
    #[serde(default)]
    pub severity: AnalyticsEventSeverity,
    
    /// Event source
    pub source: String,
    
    /// Event tags
    #[serde(default)]
    pub tags: Vec<String>,
    
    /// Event duration in microseconds
    #[serde(skip_serializing_if = "Option::is_none")]
    pub duration_us: Option<u64>,
    
    /// Event size in bytes
    #[serde(skip_serializing_if = "Option::is_none")]
    pub size_bytes: Option<u64>,
    
    /// Error information
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<AnalyticsErrorInfo>,
}

impl Default for AnalyticsEvent {
    fn default() -> Self {
        Self {
            id: None,
            event_type: AnalyticsEventType::Custom("unknown".to_string()),
            timestamp: None,
            service: "core-engine".to_string(),
            instance_id: "unknown".to_string(),
            session_id: None,
            user_id: None,
            request_id: None,
            trace_id: None,
            span_id: None,
            payload: None,
            metadata: None,
            version: default_version(),
            severity: AnalyticsEventSeverity::Info,
            source: "core-engine".to_string(),
            tags: Vec::new(),
            duration_us: None,
            size_bytes: None,
            error: None,
        }
    }
}

fn default_version() -> String {
    "1.0".to_string()
}

/// Analytics event severity
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AnalyticsEventSeverity {
    /// Info level
    Info,
    
    /// Warning level
    Warning,
    
    /// Error level
    Error,
    
    /// Critical level
    Critical,
}

impl Default for AnalyticsEventSeverity {
    fn default() -> Self {
        Self::Info
    }
}

impl std::fmt::Display for AnalyticsEventSeverity {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            AnalyticsEventSeverity::Info => write!(f, "info"),
            AnalyticsEventSeverity::Warning => write!(f, "warning"),
            AnalyticsEventSeverity::Error => write!(f, "error"),
            AnalyticsEventSeverity::Critical => write!(f, "critical"),
        }
    }
}

/// Analytics error information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalyticsErrorInfo {
    /// Error code
    pub code: String,
    
    /// Error message
    pub message: String,
    
    /// Error stack trace
    #[serde(skip_serializing_if = "Option::is_none")]
    pub stack_trace: Option<String>,
    
    /// Error context
    #[serde(skip_serializing_if = "Option::is_none")]
    pub context: Option<serde_json::Value>,
}

/// Analytics configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalyticsConfig {
    /// Enable analytics
    pub enabled: bool,
    
    /// Event publisher configuration
    pub publisher: PublisherConfig,
    
    /// Metrics collection interval
    pub metrics_interval: Duration,
    
    /// Enable metrics collection
    pub enable_metrics: bool,
    
    /// Enable event validation
    pub enable_validation: bool,
}

impl Default for AnalyticsConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            publisher: PublisherConfig::default(),
            metrics_interval: Duration::from_secs(30),
            enable_metrics: true,
            enable_validation: true,
        }
    }
}

/// Analytics manager
pub struct AnalyticsManager {
    /// Event publisher
    publisher: Arc<dyn EventPublisher>,
    
    /// Configuration
    config: AnalyticsConfig,
    
    /// Start time
    start_time: std::time::Instant,
}

impl AnalyticsManager {
    /// Create a new analytics manager
    pub async fn new(config: AnalyticsConfig) -> Result<Self, AnalyticsError> {
        if !config.enabled {
            return Err(AnalyticsError::Config("Analytics is disabled"));
        }
        
        // Create event publisher
        let publisher = EventPublisherFactory::create(config.publisher.clone()).await?;
        
        let manager = Self {
            publisher,
            config,
            start_time: std::time::Instant::now(),
        };
        
        info!("Analytics manager initialized");
        Ok(manager)
    }
    
    /// Publish an analytics event
    pub async fn publish_event(&self, event: AnalyticsEvent) -> Result<(), AnalyticsError> {
        // Publish event
        self.publisher.publish_event(event).await
    }
    
    /// Publish multiple analytics events
    pub async fn publish_batch(&self, events: Vec<AnalyticsEvent>) -> Result<(), AnalyticsError> {
        if events.is_empty() {
            return Ok(());
        }
        
        // Publish events
        self.publisher.publish_batch(events).await
    }
    
    /// Get publisher statistics
    pub fn get_stats(&self) -> PublisherStats {
        self.publisher.get_stats()
    }
    
    /// Shutdown analytics manager
    pub async fn shutdown(&self) -> Result<(), AnalyticsError> {
        info!("Shutting down analytics manager");
        
        // Shutdown publisher
        self.publisher.shutdown().await?;
        
        info!("Analytics manager shutdown completed");
        Ok(())
    }
}

/// Analytics module initialization
pub fn init() {
    info!("Initializing analytics module");
}

/// Analytics module cleanup
pub fn cleanup() {
    info!("Cleaning up analytics module");
}

#[cfg(test)]
mod tests {
    use super::*;
    
    use tokio::time::{sleep, Duration};
    
    #[tokio::test]
    async fn test_event_publisher() {
        let config = PublisherConfig::default();
        let publisher = KafkaEventPublisher::new(config).await.unwrap();
        
        // Test single event publishing
        let event = AnalyticsEvent {
            event_type: AnalyticsEventType::MarketDataReceived,
            service: "core-engine".to_string(),
            instance_id: "test-instance".to_string(),
            payload: Some(serde_json::json!({"symbol": "AAPL", "price": 150.25})),
            ..Default::default()
        };
        
        assert!(publisher.publish_event(event).await.is_ok());
        
        // Test batch publishing
        let events = vec![
            AnalyticsEvent {
                event_type: AnalyticsEventType::MarketDataProcessed,
                service: "core-engine".to_string(),
                instance_id: "test-instance".to_string(),
                payload: Some(serde_json::json!({"symbol": "GOOGL", "price": 150.50})),
                ..Default::default()
            },
            AnalyticsEvent {
                event_type: AnalyticsEventType::OrderExecuted,
                service: "core-engine".to_string(),
                instance_id: "test-instance".to_string(),
                payload: Some(serde_json::json!({"order_id": "order-123", "symbol": "MSFT", "price": 150.75})),
                ..Default::default()
            },
        ];
        
        assert!(publisher.publish_batch(events).await.is_ok());
        
        // Test statistics
        let stats = publisher.get_stats();
        assert_eq!(stats.total_events, 3);
        assert_eq!(stats.successful_events, 3);
        assert_eq!(stats.batches_published, 1);
        
        // Shutdown
        publisher.shutdown().await.unwrap();
    }
    
    #[tokio::test]
    async fn test_channel_overflow() {
        let config = PublisherConfig {
            channel_size: 10,
            ..Default::default()
        };
        
        let publisher = KafkaEventPublisher::new(config).await.unwrap();
        
        // Fill the channel
        for i in 0..15 {
            let event = AnalyticsEvent {
                event_type: AnalyticsEventType::MarketDataReceived,
                service: "core-engine".to_string(),
                instance_id: "test-instance".to_string(),
                ..Default::default()
            };
            
            if publisher.publish_event(event).await.is_err() {
                // Channel is full, which is expected
                break;
            }
        }
        
        // Check channel depth
        let stats = publisher.get_stats();
        assert_eq!(stats.channel_depth, 10);
        
        // Wait for some events to be processed
        sleep(Duration::from_millis(100));
        
        // Publish one more event (should fail)
        let event = AnalyticsEvent {
            event_type: AnalyticsEventType::CacheHit,
            service: "core-engine".to_string(),
            instance_id: "test-instance".to_string(),
            ..Default::default()
        };
        
        assert!(publisher.publish_event(event).await.is_err());
        
        // Shutdown
        publisher.shutdown().await.unwrap();
    }
}
