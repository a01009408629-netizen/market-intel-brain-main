//! Stream processing for Redpanda
//! 
//! This module provides high-level stream processing capabilities for Redpanda,
//! including windowing, aggregation, joins, and stateful operations.

use crate::config::StreamConfig;
use crate::consumer::{RedpandaConsumer, ConsumerMessage};
use crate::producer::{RedpandaProducer, BatchMessage};
use crate::serde_types::{MessageEnvelope, StreamResult};
use futures::stream::{Stream, StreamExt};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::{RwLock, mpsc};
use uuid::Uuid;

/// Stream processing engine
#[derive(Debug)]
pub struct StreamEngine {
    /// Stream ID
    stream_id: String,
    /// Stream configuration
    config: StreamConfig,
    /// Input consumer
    input_consumer: Arc<RedpandaConsumer>,
    /// Output producer
    output_producer: Arc<RedpandaProducer>,
    /// Processing state
    state: Arc<RwLock<StreamState>>,
    /// Metrics
    metrics: Arc<StreamMetrics>,
}

/// Stream processing state
#[derive(Debug)]
pub struct StreamState {
    /// Current processing status
    status: StreamStatus,
    /// Start time
    start_time: Option<Instant>,
    /// Records processed
    records_processed: u64,
    /// Records output
    records_output: u64,
    /// Errors encountered
    errors: u64,
    /// Last processed timestamp
    last_processed: Option<Instant>,
    /// Processing rate (records per second)
    processing_rate: f64,
    /// Window state
    window_state: HashMap<String, WindowState>,
}

/// Stream status
#[derive(Debug, Clone, PartialEq)]
pub enum StreamStatus {
    /// Stream is stopped
    Stopped,
    /// Stream is starting
    Starting,
    /// Stream is running
    Running,
    /// Stream is stopping
    Stopping,
    /// Stream has failed
    Failed(String),
}

/// Window state for time-based operations
#[derive(Debug, Clone)]
pub struct WindowState {
    /// Window ID
    window_id: String,
    /// Window start time
    start_time: Instant,
    /// Window end time
    end_time: Instant,
    /// Window size
    window_size: Duration,
    /// Window data
    data: Vec<MessageEnvelope>,
    /// Watermark
    watermark: Instant,
}

/// Stream metrics
#[derive(Debug)]
pub struct StreamMetrics {
    /// Records processed counter
    pub records_processed: std::sync::atomic::AtomicU64,
    /// Records output counter
    pub records_output: std::sync::atomic::AtomicU64,
    /// Processing duration histogram (simplified)
    pub processing_durations: Arc<RwLock<Vec<Duration>>>,
    /// Error counter
    pub errors: std::sync::atomic::AtomicU64,
    /// Throughput gauge
    pub throughput: Arc<RwLock<f64>>,
    /// Error rate gauge
    pub error_rate: Arc<RwLock<f64>>,
    /// Buffer size gauge
    pub buffer_size: Arc<RwLock<usize>>,
}

/// Stream processor trait
pub trait StreamProcessor: Send + Sync {
    /// Process a single message
    async fn process(&self, message: MessageEnvelope) -> Result<Vec<MessageEnvelope>, StreamError>;
    
    /// Get processor type
    fn processor_type(&self) -> &'static str;
}

/// Stream processing errors
#[derive(Debug, thiserror::Error)]
pub enum StreamError {
    #[error("Processing error: {0}")]
    ProcessingError(String),
    
    #[error("Serialization error: {0}")]
    SerializationError(String),
    
    #[error("Configuration error: {0}")]
    ConfigurationError(String),
    
    #[error("State error: {0}")]
    StateError(String),
    
    #[error("Window error: {0}")]
    WindowError(String),
    
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

/// Filter processor
#[derive(Debug)]
pub struct FilterProcessor {
    /// Filter function
    filter_fn: Arc<dyn Fn(&MessageEnvelope) -> bool + Send + Sync>,
}

impl FilterProcessor {
    /// Create new filter processor
    pub fn new<F>(filter_fn: F) -> Self
    where
        F: Fn(&MessageEnvelope) -> bool + Send + Sync + 'static,
    {
        Self {
            filter_fn: Arc::new(filter_fn),
        }
    }
}

impl StreamProcessor for FilterProcessor {
    async fn process(&self, message: MessageEnvelope) -> Result<Vec<MessageEnvelope>, StreamError> {
        if (self.filter_fn)(&message) {
            Ok(vec![message])
        } else {
            Ok(vec![])
        }
    }
    
    fn processor_type(&self) -> &'static str {
        "filter"
    }
}

/// Map processor
#[derive(Debug)]
pub struct MapProcessor {
    /// Map function
    map_fn: Arc<dyn Fn(MessageEnvelope) -> Result<MessageEnvelope, StreamError> + Send + Sync>,
}

impl MapProcessor {
    /// Create new map processor
    pub fn new<F>(map_fn: F) -> Self
    where
        F: Fn(MessageEnvelope) -> Result<MessageEnvelope, StreamError> + Send + Sync + 'static,
    {
        Self {
            map_fn: Arc::new(map_fn),
        }
    }
}

impl StreamProcessor for MapProcessor {
    async fn process(&self, message: MessageEnvelope) -> Result<Vec<MessageEnvelope>, StreamError> {
        let mapped = (self.map_fn)(message)?;
        Ok(vec![mapped])
    }
    
    fn processor_type(&self) -> &'static str {
        "map"
    }
}

/// Flat map processor
#[derive(Debug)]
pub struct FlatMapProcessor {
    /// Flat map function
    flat_map_fn: Arc<dyn Fn(MessageEnvelope) -> Result<Vec<MessageEnvelope>, StreamError> + Send + Sync>,
}

impl FlatMapProcessor {
    /// Create new flat map processor
    pub fn new<F>(flat_map_fn: F) -> Self
    where
        F: Fn(MessageEnvelope) -> Result<Vec<MessageEnvelope>, StreamError> + Send + Sync + 'static,
    {
        Self {
            flat_map_fn: Arc::new(flat_map_fn),
        }
    }
}

impl StreamProcessor for FlatMapProcessor {
    async fn process(&self, message: MessageEnvelope) -> Result<Vec<MessageEnvelope>, StreamError> {
        (self.flat_map_fn)(message)
    }
    
    fn processor_type(&self) -> &'static str {
        "flat_map"
    }
}

/// Window processor for time-based aggregations
#[derive(Debug)]
pub struct WindowProcessor {
    /// Window size
    window_size: Duration,
    /// Window slide interval
    slide_interval: Duration,
    /// Aggregation function
    aggregation_fn: Arc<dyn Fn(&[MessageEnvelope]) -> Result<MessageEnvelope, StreamError> + Send + Sync>,
    /// Window state
    windows: Arc<RwLock<HashMap<String, WindowState>>>,
}

impl WindowProcessor {
    /// Create new window processor
    pub fn new<F>(window_size: Duration, slide_interval: Duration, aggregation_fn: F) -> Self
    where
        F: Fn(&[MessageEnvelope]) -> Result<MessageEnvelope, StreamError> + Send + Sync + 'static,
    {
        Self {
            window_size,
            slide_interval,
            aggregation_fn: Arc::new(aggregation_fn),
            windows: Arc::new(RwLock::new(HashMap::new())),
        }
    }
    
    /// Get or create window for a message timestamp
    async fn get_window(&self, timestamp: Instant) -> String {
        let mut windows = self.windows.write().await;
        
        // Calculate window start time based on slide interval
        let elapsed = timestamp.duration_since(Instant::now() - Duration::from_secs(3600)); // Rough reference
        let window_start_nanos = (elapsed.as_nanos() / self.slide_interval.as_nanos()) * self.slide_interval.as_nanos();
        let window_start = Instant::now() - Duration::from_nanos(window_start_nanos as u64);
        let window_end = window_start + self.window_size;
        
        let window_id = format!("window_{}_{}", window_start.as_secs(), window_end.as_secs());
        
        if !windows.contains_key(&window_id) {
            windows.insert(window_id.clone(), WindowState {
                window_id: window_id.clone(),
                start_time: window_start,
                end_time: window_end,
                window_size: self.window_size,
                data: Vec::new(),
                watermark: window_start,
            });
        }
        
        window_id
    }
    
    /// Clean up expired windows
    async fn cleanup_expired_windows(&self) {
        let mut windows = self.windows.write().await;
        let now = Instant::now();
        
        windows.retain(|_, window| {
            now < window.end_time + self.window_size
        });
    }
}

impl StreamProcessor for WindowProcessor {
    async fn process(&self, message: MessageEnvelope) -> Result<Vec<MessageEnvelope>, StreamError> {
        let timestamp = Instant::now(); // Use message timestamp in real implementation
        let window_id = self.get_window(timestamp).await;
        
        {
            let mut windows = self.windows.write().await;
            if let Some(window) = windows.get_mut(&window_id) {
                window.data.push(message);
                
                // Check if window is ready to emit
                if Instant::now() >= window.end_time {
                    let data = window.data.clone();
                    match (self.aggregation_fn)(&data) {
                        Ok(result) => {
                            // Clear window data after emission
                            window.data.clear();
                            return Ok(vec![result]);
                        }
                        Err(e) => return Err(e),
                    }
                }
            }
        }
        
        // Clean up expired windows periodically
        self.cleanup_expired_windows().await;
        
        Ok(vec![])
    }
    
    fn processor_type(&self) -> &'static str {
        "window"
    }
}

/// Join processor for joining streams
#[derive(Debug)]
pub struct JoinProcessor {
    /// Join type
    join_type: JoinType,
    /// Join window size
    window_size: Duration,
    /// Join key extractor
    key_extractor: Arc<dyn Fn(&MessageEnvelope) -> Result<String, StreamError> + Send + Sync>,
    /// Left stream buffer
    left_buffer: Arc<RwLock<HashMap<String, Vec<MessageEnvelope>>>>,
    /// Right stream buffer
    right_buffer: Arc<RwLock<HashMap<String, Vec<MessageEnvelope>>>>,
}

/// Join types
#[derive(Debug, Clone)]
pub enum JoinType {
    /// Inner join
    Inner,
    /// Left join
    Left,
    /// Right join
    Right,
    /// Full outer join
    FullOuter,
}

impl JoinProcessor {
    /// Create new join processor
    pub fn new<F>(
        join_type: JoinType,
        window_size: Duration,
        key_extractor: F,
    ) -> Self
    where
        F: Fn(&MessageEnvelope) -> Result<String, StreamError> + Send + Sync + 'static,
    {
        Self {
            join_type,
            window_size,
            key_extractor: Arc::new(key_extractor),
            left_buffer: Arc::new(RwLock::new(HashMap::new())),
            right_buffer: Arc::new(RwLock::new(HashMap::new())),
        }
    }
    
    /// Clean up expired entries from buffers
    async fn cleanup_expired_buffers(&self) {
        let cutoff = Instant::now() - self.window_size;
        
        // Clean left buffer
        {
            let mut left_buffer = self.left_buffer.write().await;
            for (_, messages) in left_buffer.iter_mut() {
                messages.retain(|msg| {
                    // Use message timestamp in real implementation
                    Instant::now() < cutoff
                });
            }
        }
        
        // Clean right buffer
        {
            let mut right_buffer = self.right_buffer.write().await;
            for (_, messages) in right_buffer.iter_mut() {
                messages.retain(|msg| {
                    // Use message timestamp in real implementation
                    Instant::now() < cutoff
                });
            }
        }
    }
    
    /// Perform join operation
    async fn perform_join(&self, message: MessageEnvelope, is_left: bool) -> Result<Vec<MessageEnvelope>, StreamError> {
        let key = (self.key_extractor)(&message)?;
        let mut results = Vec::new();
        
        if is_left {
            // Add to left buffer
            {
                let mut left_buffer = self.left_buffer.write().await;
                left_buffer.entry(key.clone()).or_insert_with(Vec::new).push(message.clone());
            }
            
            // Check right buffer for matches
            {
                let right_buffer = self.right_buffer.read().await;
                if let Some(right_messages) = right_buffer.get(&key) {
                    for right_msg in right_messages {
                        let joined = self.create_joined_message(&message, right_msg)?;
                        results.push(joined);
                    }
                }
            }
        } else {
            // Add to right buffer
            {
                let mut right_buffer = self.right_buffer.write().await;
                right_buffer.entry(key.clone()).or_insert_with(Vec::new).push(message.clone());
            }
            
            // Check left buffer for matches
            {
                let left_buffer = self.left_buffer.read().await;
                if let Some(left_messages) = left_buffer.get(&key) {
                    for left_msg in left_messages {
                        let joined = self.create_joined_message(left_msg, &message)?;
                        results.push(joined);
                    }
                }
            }
        }
        
        // Handle join types
        match self.join_type {
            JoinType::Inner => {
                if results.is_empty() {
                    return Ok(vec![]);
                }
            }
            JoinType::Left => {
                if is_left && results.is_empty() {
                    // Add left message with null right side
                    let null_joined = self.create_null_joined_message(&message, true)?;
                    results.push(null_joined);
                }
            }
            JoinType::Right => {
                if !is_left && results.is_empty() {
                    // Add right message with null left side
                    let null_joined = self.create_null_joined_message(&message, false)?;
                    results.push(null_joined);
                }
            }
            JoinType::FullOuter => {
                if results.is_empty() {
                    let null_joined = self.create_null_joined_message(&message, is_left)?;
                    results.push(null_joined);
                }
            }
        }
        
        // Cleanup expired entries
        self.cleanup_expired_buffers().await;
        
        Ok(results)
    }
    
    /// Create joined message from two messages
    fn create_joined_message(&self, left: &MessageEnvelope, right: &MessageEnvelope) -> Result<MessageEnvelope, StreamError> {
        let joined_payload = serde_json::json!({
            "left": left.payload,
            "right": right.payload
        });
        
        Ok(MessageEnvelope::new(
            "joined".to_string(),
            Uuid::new_v4().to_string(),
            joined_payload,
            format!("join_{}", left.source),
        ))
    }
    
    /// Create null-joined message for outer joins
    fn create_null_joined_message(&self, message: &MessageEnvelope, is_left: bool) -> Result<MessageEnvelope, StreamError> {
        let joined_payload = if is_left {
            serde_json::json!({
                "left": message.payload,
                "right": null
            })
        } else {
            serde_json::json!({
                "left": null,
                "right": message.payload
            })
        };
        
        Ok(MessageEnvelope::new(
            "joined".to_string(),
            Uuid::new_v4().to_string(),
            joined_payload,
            format!("join_{}", message.source),
        ))
    }
}

impl StreamProcessor for JoinProcessor {
    async fn process(&self, message: MessageEnvelope) -> Result<Vec<MessageEnvelope>, StreamError> {
        // This is a simplified implementation
        // In practice, you'd need to determine which stream this message comes from
        self.perform_join(message, true).await
    }
    
    fn processor_type(&self) -> &'static str {
        "join"
    }
}

/// Aggregation processor
#[derive(Debug)]
pub struct AggregationProcessor {
    /// Aggregation type
    aggregation_type: AggregationType,
    /// Group by key extractor
    key_extractor: Arc<dyn Fn(&MessageEnvelope) -> Result<String, StreamError> + Send + Sync>,
    /// Value extractor
    value_extractor: Arc<dyn Fn(&MessageEnvelope) -> Result<f64, StreamError> + Send + Sync>,
    /// Aggregation state
    state: Arc<RwLock<HashMap<String, AggregationState>>>,
}

/// Aggregation types
#[derive(Debug, Clone)]
pub enum AggregationType {
    /// Sum aggregation
    Sum,
    /// Count aggregation
    Count,
    /// Average aggregation
    Average,
    /// Min aggregation
    Min,
    /// Max aggregation
    Max,
}

/// Aggregation state
#[derive(Debug, Clone)]
pub struct AggregationState {
    /// Current value
    value: f64,
    /// Count of items
    count: u64,
    /// Last update timestamp
    last_update: Instant,
}

impl AggregationProcessor {
    /// Create new aggregation processor
    pub fn new<F1, F2>(
        aggregation_type: AggregationType,
        key_extractor: F1,
        value_extractor: F2,
    ) -> Self
    where
        F1: Fn(&MessageEnvelope) -> Result<String, StreamError> + Send + Sync + 'static,
        F2: Fn(&MessageEnvelope) -> Result<f64, StreamError> + Send + Sync + 'static,
    {
        Self {
            aggregation_type,
            key_extractor: Arc::new(key_extractor),
            value_extractor: Arc::new(value_extractor),
            state: Arc::new(RwLock::new(HashMap::new())),
        }
    }
    
    /// Update aggregation state
    async fn update_state(&self, key: String, value: f64) -> f64 {
        let mut state = self.state.write().await;
        let aggregation_state = state.entry(key).or_insert(AggregationState {
            value: 0.0,
            count: 0,
            last_update: Instant::now(),
        });
        
        match self.aggregation_type {
            AggregationType::Sum => {
                aggregation_state.value += value;
                aggregation_state.count += 1;
            }
            AggregationType::Count => {
                aggregation_state.value += 1.0;
                aggregation_state.count += 1;
            }
            AggregationType::Average => {
                let new_count = aggregation_state.count + 1;
                aggregation_state.value = (aggregation_state.value * aggregation_state.count as f64 + value) / new_count as f64;
                aggregation_state.count = new_count;
            }
            AggregationType::Min => {
                if aggregation_state.count == 0 || value < aggregation_state.value {
                    aggregation_state.value = value;
                }
                aggregation_state.count += 1;
            }
            AggregationType::Max => {
                if aggregation_state.count == 0 || value > aggregation_state.value {
                    aggregation_state.value = value;
                }
                aggregation_state.count += 1;
            }
        }
        
        aggregation_state.last_update = Instant::now();
        aggregation_state.value
    }
}

impl StreamProcessor for AggregationProcessor {
    async fn process(&self, message: MessageEnvelope) -> Result<Vec<MessageEnvelope>, StreamError> {
        let key = (self.key_extractor)(&message)?;
        let value = (self.value_extractor)(&message)?;
        
        let aggregated_value = self.update_state(key, value).await;
        
        let result_payload = serde_json::json!({
            "key": key,
            "value": aggregated_value,
            "aggregation_type": format!("{:?}", self.aggregation_type),
            "timestamp": chrono::Utc::now()
        });
        
        let result = MessageEnvelope::new(
            "aggregated".to_string(),
            Uuid::new_v4().to_string(),
            result_payload,
            "aggregation_processor".to_string(),
        );
        
        Ok(vec![result])
    }
    
    fn processor_type(&self) -> &'static str {
        "aggregation"
    }
}

impl StreamEngine {
    /// Create new stream engine
    pub async fn new(
        stream_id: String,
        config: StreamConfig,
        input_consumer: Arc<RedpandaConsumer>,
        output_producer: Arc<RedpandaProducer>,
    ) -> Result<Self, StreamError> {
        let state = Arc::new(RwLock::new(StreamState {
            status: StreamStatus::Stopped,
            start_time: None,
            records_processed: 0,
            records_output: 0,
            errors: 0,
            last_processed: None,
            processing_rate: 0.0,
            window_state: HashMap::new(),
        }));
        
        let metrics = Arc::new(StreamMetrics {
            records_processed: std::sync::atomic::AtomicU64::new(0),
            records_output: std::sync::atomic::AtomicU64::new(0),
            processing_durations: Arc::new(RwLock::new(Vec::new())),
            errors: std::sync::atomic::AtomicU64::new(0),
            throughput: Arc::new(RwLock::new(0.0)),
            error_rate: Arc::new(RwLock::new(0.0)),
            buffer_size: Arc::new(RwLock::new(0)),
        });
        
        Ok(Self {
            stream_id,
            config,
            input_consumer,
            output_producer,
            state,
            metrics,
        })
    }
    
    /// Start stream processing
    pub async fn start(&self) -> Result<(), StreamError> {
        let mut state = self.state.write().await;
        
        if state.status != StreamStatus::Stopped {
            return Err(StreamError::StateError("Stream is already running".to_string()));
        }
        
        state.status = StreamStatus::Starting;
        state.start_time = Some(Instant::now());
        
        // Start processing loop
        let stream_id = self.stream_id.clone();
        let input_consumer = Arc::clone(&self.input_consumer);
        let output_producer = Arc::clone(&self.output_producer);
        let state = Arc::clone(&self.state);
        let metrics = Arc::clone(&self.metrics);
        let config = self.config.clone();
        
        tokio::spawn(async move {
            if let Err(e) = Self::processing_loop(
                stream_id,
                input_consumer,
                output_producer,
                state,
                metrics,
                config,
            ).await {
                eprintln!("Stream processing error: {}", e);
            }
        });
        
        state.status = StreamStatus::Running;
        Ok(())
    }
    
    /// Stop stream processing
    pub async fn stop(&self) -> Result<(), StreamError> {
        let mut state = self.state.write().await;
        
        if state.status == StreamStatus::Stopped {
            return Ok(());
        }
        
        state.status = StreamStatus::Stopping;
        
        // In a real implementation, you'd signal the processing loop to stop
        
        state.status = StreamStatus::Stopped;
        Ok(())
    }
    
    /// Get stream status
    pub async fn get_status(&self) -> StreamStatus {
        let state = self.state.read().await;
        state.status.clone()
    }
    
    /// Get stream metrics
    pub async fn get_metrics(&self) -> StreamMetricsSnapshot {
        let state = self.state.read().await;
        let throughput = *self.metrics.throughput.read().await;
        let error_rate = *self.metrics.error_rate.read().await;
        let buffer_size = *self.metrics.buffer_size.read().await;
        
        StreamMetricsSnapshot {
            stream_id: self.stream_id.clone(),
            status: state.status.clone(),
            records_processed: state.records_processed,
            records_output: state.records_output,
            errors: state.errors,
            processing_rate: state.processing_rate,
            throughput,
            error_rate,
            buffer_size,
            uptime: state.start_time.map(|start| start.elapsed()),
        }
    }
    
    /// Main processing loop
    async fn processing_loop(
        stream_id: String,
        input_consumer: Arc<RedpandaConsumer>,
        output_producer: Arc<RedpandaProducer>,
        state: Arc<RwLock<StreamState>>,
        metrics: Arc<StreamMetrics>,
        config: StreamConfig,
    ) -> Result<(), StreamError> {
        let mut last_metrics_update = Instant::now();
        let mut processed_count = 0u64;
        
        loop {
            // Check if stream should stop
            {
                let state_guard = state.read().await;
                if matches!(state_guard.status, StreamStatus::Stopping | StreamStatus::Stopped) {
                    break;
                }
            }
            
            // Process messages
            match input_consumer.poll().await {
                Ok(Some(consumer_message)) => {
                    let start_time = Instant::now();
                    
                    // Convert consumer message to envelope
                    let envelope = match Self::consumer_message_to_envelope(consumer_message) {
                        Ok(envelope) => envelope,
                        Err(e) => {
                            metrics.errors.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                            continue;
                        }
                    };
                    
                    // Process message based on configuration
                    let results = Self::process_message(&config, envelope).await?;
                    
                    // Send results to output
                    for result in results {
                        if let Err(e) = output_producer.send_message(result).await {
                            metrics.errors.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        } else {
                            metrics.records_output.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                    }
                    
                    // Update metrics
                    let processing_duration = start_time.elapsed();
                    metrics.records_processed.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    processed_count += 1;
                    
                    {
                        let mut durations = metrics.processing_durations.write().await;
                        durations.push(processing_duration);
                        
                        // Keep only last 1000 durations
                        if durations.len() > 1000 {
                            durations.remove(0);
                        }
                    }
                    
                    // Update state
                    {
                        let mut state_guard = state.write().await;
                        state_guard.records_processed += 1;
                        state_guard.last_processed = Some(Instant::now());
                    }
                    
                    // Update metrics every second
                    if last_metrics_update.elapsed() >= Duration::from_secs(1) {
                        let elapsed = last_metrics_update.elapsed();
                        let rate = processed_count as f64 / elapsed.as_secs_f64();
                        
                        *metrics.throughput.write().await = rate;
                        
                        let total_processed = metrics.records_processed.load(std::sync::atomic::Ordering::Relaxed);
                        let total_errors = metrics.errors.load(std::sync::atomic::Ordering::Relaxed);
                        let error_rate = if total_processed > 0 {
                            total_errors as f64 / total_processed as f64
                        } else {
                            0.0
                        };
                        
                        *metrics.error_rate.write().await = error_rate;
                        
                        {
                            let mut state_guard = state.write().await;
                            state_guard.processing_rate = rate;
                        }
                        
                        processed_count = 0;
                        last_metrics_update = Instant::now();
                    }
                }
                Ok(None) => {
                    // No message available, sleep briefly
                    tokio::time::sleep(Duration::from_millis(10)).await;
                }
                Err(e) => {
                    metrics.errors.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    tokio::time::sleep(Duration::from_millis(100)).await;
                }
            }
        }
        
        Ok(())
    }
    
    /// Convert consumer message to envelope
    fn consumer_message_to_envelope(consumer_message: ConsumerMessage) -> Result<MessageEnvelope, StreamError> {
        // This is a simplified conversion
        // In practice, you'd deserialize the message payload
        let payload = serde_json::json!({
            "consumer_message": "deserialized_payload"
        });
        
        Ok(MessageEnvelope::new(
            "consumer_message".to_string(),
            Uuid::new_v4().to_string(),
            payload,
            "stream_engine".to_string(),
        ))
    }
    
    /// Process a single message based on configuration
    async fn process_message(config: &StreamConfig, message: MessageEnvelope) -> Result<Vec<MessageEnvelope>, StreamError> {
        match config.processing_type.as_str() {
            "filter" => {
                // Simple filter implementation
                // In practice, you'd use a FilterProcessor
                Ok(vec![message])
            }
            "map" => {
                // Simple map implementation
                // In practice, you'd use a MapProcessor
                Ok(vec![message])
            }
            "window" => {
                // Simple window implementation
                // In practice, you'd use a WindowProcessor
                Ok(vec![message])
            }
            "join" => {
                // Simple join implementation
                // In practice, you'd use a JoinProcessor
                Ok(vec![message])
            }
            "aggregation" => {
                // Simple aggregation implementation
                // In practice, you'd use an AggregationProcessor
                Ok(vec![message])
            }
            _ => Ok(vec![message]),
        }
    }
}

/// Stream metrics snapshot
#[derive(Debug, Clone)]
pub struct StreamMetricsSnapshot {
    /// Stream ID
    pub stream_id: String,
    /// Stream status
    pub status: StreamStatus,
    /// Records processed
    pub records_processed: u64,
    /// Records output
    pub records_output: u64,
    /// Errors
    pub errors: u64,
    /// Processing rate
    pub processing_rate: f64,
    /// Throughput
    pub throughput: f64,
    /// Error rate
    pub error_rate: f64,
    /// Buffer size
    pub buffer_size: usize,
    /// Uptime
    pub uptime: Option<Duration>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::RedpandaConfig;

    #[tokio::test]
    async fn test_filter_processor() {
        let processor = FilterProcessor::new(|msg| {
            msg.message_type == "market_data"
        });
        
        let market_data_msg = MessageEnvelope::new(
            "market_data".to_string(),
            "msg1".to_string(),
            serde_json::json!({"symbol": "AAPL"}),
            "test".to_string(),
        );
        
        let order_msg = MessageEnvelope::new(
            "order".to_string(),
            "msg2".to_string(),
            serde_json::json!({"order_id": "123"}),
            "test".to_string(),
        );
        
        let result1 = processor.process(market_data_msg).await.unwrap();
        assert_eq!(result1.len(), 1);
        
        let result2 = processor.process(order_msg).await.unwrap();
        assert_eq!(result2.len(), 0);
    }

    #[tokio::test]
    async fn test_map_processor() {
        let processor = MapProcessor::new(|msg| {
            let mut new_msg = msg.clone();
            new_msg.message_type = "mapped".to_string();
            Ok(new_msg)
        });
        
        let input_msg = MessageEnvelope::new(
            "market_data".to_string(),
            "msg1".to_string(),
            serde_json::json!({"symbol": "AAPL"}),
            "test".to_string(),
        );
        
        let result = processor.process(input_msg).await.unwrap();
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].message_type, "mapped");
    }

    #[tokio::test]
    async fn test_aggregation_processor() {
        let processor = AggregationProcessor::new(
            AggregationType::Sum,
            |msg| Ok("test_key".to_string()),
            |msg| Ok(42.0),
        );
        
        let input_msg = MessageEnvelope::new(
            "market_data".to_string(),
            "msg1".to_string(),
            serde_json::json!({"symbol": "AAPL"}),
            "test".to_string(),
        );
        
        let result = processor.process(input_msg).await.unwrap();
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].message_type, "aggregated");
    }

    #[test]
    fn test_stream_metrics() {
        let metrics = StreamMetrics {
            records_processed: std::sync::atomic::AtomicU64::new(100),
            records_output: std::sync::atomic::AtomicU64::new(95),
            processing_durations: Arc::new(RwLock::new(vec![
                Duration::from_millis(10),
                Duration::from_millis(20),
                Duration::from_millis(15),
            ])),
            errors: std::sync::atomic::AtomicU64::new(5),
            throughput: Arc::new(RwLock::new(1000.0)),
            error_rate: Arc::new(RwLock::new(0.05)),
            buffer_size: Arc::new(RwLock::new(1000)),
        };
        
        assert_eq!(metrics.records_processed.load(std::sync::atomic::Ordering::Relaxed), 100);
        assert_eq!(metrics.records_output.load(std::sync::atomic::Ordering::Relaxed), 95);
        assert_eq!(metrics.errors.load(std::sync::atomic::Ordering::Relaxed), 5);
    }
}
