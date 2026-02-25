//! Metrics collection for Redpanda streaming
//! 
//! This module provides comprehensive metrics collection for Redpanda producers,
//! consumers, and stream processing components using Prometheus.

use prometheus::{Counter, Gauge, Histogram, Registry, Opts, HistogramOpts};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;
use uuid::Uuid;

/// Metrics collector trait
pub trait MetricsCollector: Send + Sync {
    /// Increment a counter
    fn increment_counter(&self, name: &str, labels: &HashMap<String, String>, value: f64);
    
    /// Set a gauge value
    fn set_gauge(&self, name: &str, labels: &HashMap<String, String>, value: f64);
    
    /// Record a histogram observation
    fn record_histogram(&self, name: &str, labels: &HashMap<String, String>, value: f64);
    
    /// Get metrics snapshot
    fn get_snapshot(&self) -> MetricsSnapshot;
}

/// Prometheus metrics collector
#[derive(Debug)]
pub struct PrometheusMetrics {
    /// Registry for metrics
    registry: Arc<Registry>,
    /// Counters
    counters: Arc<RwLock<HashMap<String, Counter>>>,
    /// Gauges
    gauges: Arc<RwLock<HashMap<String, Gauge>>>,
    /// Histograms
    histograms: Arc<RwLock<HashMap<String, Histogram>>>,
    /// Metrics namespace
    namespace: String,
    /// Metrics subsystem
    subsystem: String,
}

impl PrometheusMetrics {
    /// Create new Prometheus metrics collector
    pub fn new(namespace: &str, subsystem: &str) -> Self {
        Self {
            registry: Arc::new(Registry::new()),
            counters: Arc::new(RwLock::new(HashMap::new())),
            gauges: Arc::new(RwLock::new(HashMap::new())),
            histograms: Arc::new(RwLock::new(HashMap::new())),
            namespace: namespace.to_string(),
            subsystem: subsystem.to_string(),
        }
    }

    /// Get the Prometheus registry
    pub fn registry(&self) -> Arc<Registry> {
        Arc::clone(&self.registry)
    }

    /// Get or create a counter
    async fn get_or_create_counter(&self, name: &str, help: &str) -> Counter {
        let mut counters = self.counters.write().await;
        
        if let Some(counter) = counters.get(name) {
            counter.clone()
        } else {
            let full_name = format!("{}_{}_{}", self.namespace, self.subsystem, name);
            let counter = Counter::with_opts(Opts::new(full_name, help))
                .expect("Failed to create counter");
            self.registry
                .register(Box::new(counter.clone()))
                .expect("Failed to register counter");
            counters.insert(name.to_string(), counter.clone());
            counter
        }
    }

    /// Get or create a gauge
    async fn get_or_create_gauge(&self, name: &str, help: &str) -> Gauge {
        let mut gauges = self.gauges.write().await;
        
        if let Some(gauge) = gauges.get(name) {
            gauge.clone()
        } else {
            let full_name = format!("{}_{}_{}", self.namespace, self.subsystem, name);
            let gauge = Gauge::with_opts(Opts::new(full_name, help))
                .expect("Failed to create gauge");
            self.registry
                .register(Box::new(gauge.clone()))
                .expect("Failed to register gauge");
            gauges.insert(name.to_string(), gauge.clone());
            gauge
        }
    }

    /// Get or create a histogram
    async fn get_or_create_histogram(&self, name: &str, help: &str, buckets: Vec<f64>) -> Histogram {
        let mut histograms = self.histograms.write().await;
        
        if let Some(histogram) = histograms.get(name) {
            histogram.clone()
        } else {
            let full_name = format!("{}_{}_{}", self.namespace, self.subsystem, name);
            let histogram = Histogram::with_opts(HistogramOpts::new(full_name, help).buckets(buckets))
                .expect("Failed to create histogram");
            self.registry
                .register(Box::new(histogram.clone()))
                .expect("Failed to register histogram");
            histograms.insert(name.to_string(), histogram.clone());
            histogram
        }
    }

    /// Format labels for Prometheus
    fn format_labels(labels: &HashMap<String, String>) -> HashMap<String, String> {
        labels.clone()
    }
}

impl MetricsCollector for PrometheusMetrics {
    fn increment_counter(&self, name: &str, labels: &HashMap<String, String>, value: f64) {
        let counters = Arc::clone(&self.counters);
        let registry = Arc::clone(&self.registry);
        let name = name.to_string();
        let labels = Self::format_labels(labels);
        let namespace = self.namespace.clone();
        let subsystem = self.subsystem.clone();

        tokio::spawn(async move {
            let counter = {
                let mut counters = counters.write().await;
                
                if let Some(counter) = counters.get(&name) {
                    counter.clone()
                } else {
                    let full_name = format!("{}_{}_{}", namespace, subsystem, name);
                    let counter = Counter::with_opts(Opts::new(full_name, &name))
                        .expect("Failed to create counter");
                    registry
                        .register(Box::new(counter.clone()))
                        .expect("Failed to register counter");
                    counters.insert(name.clone(), counter.clone());
                    counter
                }
            };

            if labels.is_empty() {
                counter.inc_by(value);
            } else {
                let counter_with_labels = counter.with_label_values(&labels.values().collect::<Vec<_>>());
                counter_with_labels.inc_by(value);
            }
        });
    }

    fn set_gauge(&self, name: &str, labels: &HashMap<String, String>, value: f64) {
        let gauges = Arc::clone(&self.gauges);
        let registry = Arc::clone(&self.registry);
        let name = name.to_string();
        let labels = Self::format_labels(labels);
        let namespace = self.namespace.clone();
        let subsystem = self.subsystem.clone();

        tokio::spawn(async move {
            let gauge = {
                let mut gauges = gauges.write().await;
                
                if let Some(gauge) = gauges.get(&name) {
                    gauge.clone()
                } else {
                    let full_name = format!("{}_{}_{}", namespace, subsystem, name);
                    let gauge = Gauge::with_opts(Opts::new(full_name, &name))
                        .expect("Failed to create gauge");
                    registry
                        .register(Box::new(gauge.clone()))
                        .expect("Failed to register gauge");
                    gauges.insert(name.clone(), gauge.clone());
                    gauge
                }
            };

            if labels.is_empty() {
                gauge.set(value);
            } else {
                let gauge_with_labels = gauge.with_label_values(&labels.values().collect::<Vec<_>>());
                gauge_with_labels.set(value);
            }
        });
    }

    fn record_histogram(&self, name: &str, labels: &HashMap<String, String>, value: f64) {
        let histograms = Arc::clone(&self.histograms);
        let registry = Arc::clone(&self.registry);
        let name = name.to_string();
        let labels = Self::format_labels(labels);
        let namespace = self.namespace.clone();
        let subsystem = self.subsystem.clone();

        tokio::spawn(async move {
            let histogram = {
                let mut histograms = histograms.write().await;
                
                if let Some(histogram) = histograms.get(&name) {
                    histogram.clone()
                } else {
                    let full_name = format!("{}_{}_{}", namespace, subsystem, name);
                    let buckets = Self::default_buckets(&name);
                    let histogram = Histogram::with_opts(HistogramOpts::new(full_name, &name).buckets(buckets))
                        .expect("Failed to create histogram");
                    registry
                        .register(Box::new(histogram.clone()))
                        .expect("Failed to register histogram");
                    histograms.insert(name.clone(), histogram.clone());
                    histogram
                }
            };

            if labels.is_empty() {
                histogram.observe(value);
            } else {
                let histogram_with_labels = histogram.with_label_values(&labels.values().collect::<Vec<_>>());
                histogram_with_labels.observe(value);
            }
        });
    }

    fn get_snapshot(&self) -> MetricsSnapshot {
        // This is a simplified snapshot implementation
        // In a real implementation, you would collect actual metric values
        MetricsSnapshot {
            timestamp: chrono::Utc::now(),
            counters: HashMap::new(),
            gauges: HashMap::new(),
            histograms: HashMap::new(),
        }
    }
}

impl PrometheusMetrics {
    /// Get default buckets for histogram based on metric name
    fn default_buckets(name: &str) -> Vec<f64> {
        match name {
            name if name.contains("duration") || name.contains("latency") => {
                vec![0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
            }
            name if name.contains("size") || name.contains("bytes") => {
                vec![1024.0, 4096.0, 16384.0, 65536.0, 262144.0, 1048576.0, 4194304.0, 16777216.0]
            }
            name if name.contains("throughput") || name.contains("rate") => {
                vec![1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0, 10000.0]
            }
            _ => {
                vec![0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0]
            }
        }
    }
}

/// Metrics snapshot
#[derive(Debug, Clone)]
pub struct MetricsSnapshot {
    /// Snapshot timestamp
    pub timestamp: chrono::DateTime<chrono::Utc>,
    /// Counter values
    pub counters: HashMap<String, f64>,
    /// Gauge values
    pub gauges: HashMap<String, f64>,
    /// Histogram values
    pub histograms: HashMap<String, HistogramSnapshot>,
}

/// Histogram snapshot
#[derive(Debug, Clone)]
pub struct HistogramSnapshot {
    /// Sample count
    pub count: u64,
    /// Sample sum
    pub sum: f64,
    /// Bucket values
    pub buckets: Vec<(f64, u64)>,
}

/// Producer metrics
#[derive(Debug)]
pub struct ProducerMetrics {
    /// Messages sent counter
    pub messages_sent: Counter,
    /// Bytes sent counter
    pub bytes_sent: Counter,
    /// Send duration histogram
    pub send_duration: Histogram,
    /// Compression ratio gauge
    pub compression_ratio: Gauge,
    /// In-flight messages gauge
    pub in_flight_messages: Gauge,
    /// Error counter
    pub errors: Counter,
    /// Retries counter
    pub retries: Counter,
}

impl ProducerMetrics {
    /// Create new producer metrics
    pub fn new(namespace: &str, producer_id: &str) -> Self {
        let labels = HashMap::from([("producer_id".to_string(), producer_id.to_string())]);
        
        Self {
            messages_sent: Counter::with_opts(
                Opts::new(format!("{}_producer_messages_sent_total", namespace), "Total messages sent")
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create messages_sent counter"),
            
            bytes_sent: Counter::with_opts(
                Opts::new(format!("{}_producer_bytes_sent_total", namespace), "Total bytes sent")
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create bytes_sent counter"),
            
            send_duration: Histogram::with_opts(
                HistogramOpts::new(format!("{}_producer_send_duration_seconds", namespace), "Send duration in seconds")
                    .buckets(vec![0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0])
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create send_duration histogram"),
            
            compression_ratio: Gauge::with_opts(
                Opts::new(format!("{}_producer_compression_ratio", namespace), "Compression ratio")
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create compression_ratio gauge"),
            
            in_flight_messages: Gauge::with_opts(
                Opts::new(format!("{}_producer_in_flight_messages", namespace), "Number of in-flight messages")
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create in_flight_messages gauge"),
            
            errors: Counter::with_opts(
                Opts::new(format!("{}_producer_errors_total", namespace), "Total producer errors")
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create errors counter"),
            
            retries: Counter::with_opts(
                Opts::new(format!("{}_producer_retries_total", namespace), "Total producer retries")
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create retries counter"),
        }
    }

    /// Record message sent
    pub fn record_message_sent(&self, size_bytes: usize, duration: Duration) {
        let label_values = vec!["default"]; // This would be dynamic in real implementation
        
        self.messages_sent.with_label_values(&label_values).inc();
        self.bytes_sent.with_label_values(&label_values).inc_by(size_bytes as f64);
        self.send_duration.with_label_values(&label_values).observe(duration.as_secs_f64());
    }

    /// Record error
    pub fn record_error(&self) {
        let label_values = vec!["default"];
        self.errors.with_label_values(&label_values).inc();
    }

    /// Record retry
    pub fn record_retry(&self) {
        let label_values = vec!["default"];
        self.retries.with_label_values(&label_values).inc();
    }

    /// Set compression ratio
    pub fn set_compression_ratio(&self, ratio: f64) {
        let label_values = vec!["default"];
        self.compression_ratio.with_label_values(&label_values).set(ratio);
    }

    /// Set in-flight messages
    pub fn set_in_flight_messages(&self, count: u64) {
        let label_values = vec!["default"];
        self.in_flight_messages.with_label_values(&label_values).set(count as f64);
    }
}

/// Consumer metrics
#[derive(Debug)]
pub struct ConsumerMetrics {
    /// Messages received counter
    pub messages_received: Counter,
    /// Bytes received counter
    pub bytes_received: Counter,
    /// Process duration histogram
    pub process_duration: Histogram,
    /// Poll duration histogram
    pub poll_duration: Histogram,
    /// Lag gauge
    pub lag: Gauge,
    /// Error counter
    pub errors: Counter,
    /// Rebalances counter
    pub rebalances: Counter,
}

impl ConsumerMetrics {
    /// Create new consumer metrics
    pub fn new(namespace: &str, consumer_id: &str) -> Self {
        let labels = HashMap::from([("consumer_id".to_string(), consumer_id.to_string())]);
        
        Self {
            messages_received: Counter::with_opts(
                Opts::new(format!("{}_consumer_messages_received_total", namespace), "Total messages received")
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create messages_received counter"),
            
            bytes_received: Counter::with_opts(
                Opts::new(format!("{}_consumer_bytes_received_total", namespace), "Total bytes received")
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create bytes_received counter"),
            
            process_duration: Histogram::with_opts(
                HistogramOpts::new(format!("{}_consumer_process_duration_seconds", namespace), "Process duration in seconds")
                    .buckets(vec![0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0])
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create process_duration histogram"),
            
            poll_duration: Histogram::with_opts(
                HistogramOpts::new(format!("{}_consumer_poll_duration_seconds", namespace), "Poll duration in seconds")
                    .buckets(vec![0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0])
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create poll_duration histogram"),
            
            lag: Gauge::with_opts(
                Opts::new(format!("{}_consumer_lag", namespace), "Consumer lag")
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create lag gauge"),
            
            errors: Counter::with_opts(
                Opts::new(format!("{}_consumer_errors_total", namespace), "Total consumer errors")
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create errors counter"),
            
            rebalances: Counter::with_opts(
                Opts::new(format!("{}_consumer_rebalances_total", namespace), "Total consumer rebalances")
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create rebalances counter"),
        }
    }

    /// Record message received
    pub fn record_message_received(&self, size_bytes: usize, process_duration: Duration) {
        let label_values = vec!["default"];
        
        self.messages_received.with_label_values(&label_values).inc();
        self.bytes_received.with_label_values(&label_values).inc_by(size_bytes as f64);
        self.process_duration.with_label_values(&label_values).observe(process_duration.as_secs_f64());
    }

    /// Record poll duration
    pub fn record_poll_duration(&self, duration: Duration) {
        let label_values = vec!["default"];
        self.poll_duration.with_label_values(&label_values).observe(duration.as_secs_f64());
    }

    /// Set lag
    pub fn set_lag(&self, lag: u64) {
        let label_values = vec!["default"];
        self.lag.with_label_values(&label_values).set(lag as f64);
    }

    /// Record error
    pub fn record_error(&self) {
        let label_values = vec!["default"];
        self.errors.with_label_values(&label_values).inc();
    }

    /// Record rebalance
    pub fn record_rebalance(&self) {
        let label_values = vec!["default"];
        self.rebalances.with_label_values(&label_values).inc();
    }
}

/// Stream processing metrics
#[derive(Debug)]
pub struct StreamMetrics {
    /// Records processed counter
    pub records_processed: Counter,
    /// Records output counter
    pub records_output: Counter,
    /// Processing duration histogram
    pub processing_duration: Histogram,
    /// Throughput gauge
    pub throughput: Gauge,
    /// Error rate gauge
    pub error_rate: Gauge,
    /// Buffer size gauge
    pub buffer_size: Gauge,
}

impl StreamMetrics {
    /// Create new stream metrics
    pub fn new(namespace: &str, stream_id: &str) -> Self {
        let labels = HashMap::from([("stream_id".to_string(), stream_id.to_string())]);
        
        Self {
            records_processed: Counter::with_opts(
                Opts::new(format!("{}_stream_records_processed_total", namespace), "Total records processed")
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create records_processed counter"),
            
            records_output: Counter::with_opts(
                Opts::new(format!("{}_stream_records_output_total", namespace), "Total records output")
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create records_output counter"),
            
            processing_duration: Histogram::with_opts(
                HistogramOpts::new(format!("{}_stream_processing_duration_seconds", namespace), "Processing duration in seconds")
                    .buckets(vec![0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0])
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create processing_duration histogram"),
            
            throughput: Gauge::with_opts(
                Opts::new(format!("{}_stream_throughput", namespace), "Records per second")
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create throughput gauge"),
            
            error_rate: Gauge::with_opts(
                Opts::new(format!("{}_stream_error_rate", namespace), "Error rate")
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create error_rate gauge"),
            
            buffer_size: Gauge::with_opts(
                Opts::new(format!("{}_stream_buffer_size", namespace), "Buffer size")
                    .variable_labels(labels.keys().cloned().collect())
            ).expect("Failed to create buffer_size gauge"),
        }
    }

    /// Record processing
    pub fn record_processing(&self, input_count: u64, output_count: u64, duration: Duration) {
        let label_values = vec!["default"];
        
        self.records_processed.with_label_values(&label_values).inc_by(input_count as f64);
        self.records_output.with_label_values(&label_values).inc_by(output_count as f64);
        self.processing_duration.with_label_values(&label_values).observe(duration.as_secs_f64());
    }

    /// Set throughput
    pub fn set_throughput(&self, records_per_second: f64) {
        let label_values = vec!["default"];
        self.throughput.with_label_values(&label_values).set(records_per_second);
    }

    /// Set error rate
    pub fn set_error_rate(&self, error_rate: f64) {
        let label_values = vec!["default"];
        self.error_rate.with_label_values(&label_values).set(error_rate);
    }

    /// Set buffer size
    pub fn set_buffer_size(&self, size: u64) {
        let label_values = vec!["default"];
        self.buffer_size.with_label_values(&label_values).set(size as f64);
    }
}

/// Metrics registry for managing multiple collectors
#[derive(Debug)]
pub struct MetricsRegistry {
    /// Registry instance
    registry: Arc<Registry>,
    /// Metrics collectors
    collectors: Arc<RwLock<HashMap<String, Box<dyn MetricsCollector>>>>,
    /// Producer metrics
    producer_metrics: Arc<RwLock<HashMap<String, ProducerMetrics>>>,
    /// Consumer metrics
    consumer_metrics: Arc<RwLock<HashMap<String, ConsumerMetrics>>>,
    /// Stream metrics
    stream_metrics: Arc<RwLock<HashMap<String, StreamMetrics>>>,
}

impl MetricsRegistry {
    /// Create new metrics registry
    pub fn new() -> Self {
        Self {
            registry: Arc::new(Registry::new()),
            collectors: Arc::new(RwLock::new(HashMap::new())),
            producer_metrics: Arc::new(RwLock::new(HashMap::new())),
            consumer_metrics: Arc::new(RwLock::new(HashMap::new())),
            stream_metrics: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Get the Prometheus registry
    pub fn registry(&self) -> Arc<Registry> {
        Arc::clone(&self.registry)
    }

    /// Add a metrics collector
    pub async fn add_collector(&self, name: String, collector: Box<dyn MetricsCollector>) {
        let mut collectors = self.collectors.write().await;
        collectors.insert(name, collector);
    }

    /// Get or create producer metrics
    pub async fn get_producer_metrics(&self, namespace: &str, producer_id: &str) -> ProducerMetrics {
        let mut producer_metrics = self.producer_metrics.write().await;
        
        if let Some(metrics) = producer_metrics.get(producer_id) {
            // Return a clone-like instance (in real implementation, you'd need proper cloning)
            ProducerMetrics::new(namespace, producer_id)
        } else {
            let metrics = ProducerMetrics::new(namespace, producer_id);
            // Register metrics with the registry
            self.registry.register(Box::new(metrics.messages_sent.clone())).ok();
            self.registry.register(Box::new(metrics.bytes_sent.clone())).ok();
            self.registry.register(Box::new(metrics.send_duration.clone())).ok();
            self.registry.register(Box::new(metrics.compression_ratio.clone())).ok();
            self.registry.register(Box::new(metrics.in_flight_messages.clone())).ok();
            self.registry.register(Box::new(metrics.errors.clone())).ok();
            self.registry.register(Box::new(metrics.retries.clone())).ok();
            
            producer_metrics.insert(producer_id.to_string(), metrics.clone());
            metrics
        }
    }

    /// Get or create consumer metrics
    pub async fn get_consumer_metrics(&self, namespace: &str, consumer_id: &str) -> ConsumerMetrics {
        let mut consumer_metrics = self.consumer_metrics.write().await;
        
        if let Some(metrics) = consumer_metrics.get(consumer_id) {
            ConsumerMetrics::new(namespace, consumer_id)
        } else {
            let metrics = ConsumerMetrics::new(namespace, consumer_id);
            // Register metrics with the registry
            self.registry.register(Box::new(metrics.messages_received.clone())).ok();
            self.registry.register(Box::new(metrics.bytes_received.clone())).ok();
            self.registry.register(Box::new(metrics.process_duration.clone())).ok();
            self.registry.register(Box::new(metrics.poll_duration.clone())).ok();
            self.registry.register(Box::new(metrics.lag.clone())).ok();
            self.registry.register(Box::new(metrics.errors.clone())).ok();
            self.registry.register(Box::new(metrics.rebalances.clone())).ok();
            
            consumer_metrics.insert(consumer_id.to_string(), metrics.clone());
            metrics
        }
    }

    /// Get or create stream metrics
    pub async fn get_stream_metrics(&self, namespace: &str, stream_id: &str) -> StreamMetrics {
        let mut stream_metrics = self.stream_metrics.write().await;
        
        if let Some(metrics) = stream_metrics.get(stream_id) {
            StreamMetrics::new(namespace, stream_id)
        } else {
            let metrics = StreamMetrics::new(namespace, stream_id);
            // Register metrics with the registry
            self.registry.register(Box::new(metrics.records_processed.clone())).ok();
            self.registry.register(Box::new(metrics.records_output.clone())).ok();
            self.registry.register(Box::new(metrics.processing_duration.clone())).ok();
            self.registry.register(Box::new(metrics.throughput.clone())).ok();
            self.registry.register(Box::new(metrics.error_rate.clone())).ok();
            self.registry.register(Box::new(metrics.buffer_size.clone())).ok();
            
            stream_metrics.insert(stream_id.to_string(), metrics.clone());
            metrics
        }
    }

    /// Get metrics snapshot from all collectors
    pub async fn get_snapshot(&self) -> HashMap<String, MetricsSnapshot> {
        let collectors = self.collectors.read().await;
        let mut snapshots = HashMap::new();
        
        for (name, collector) in collectors.iter() {
            snapshots.insert(name.clone(), collector.get_snapshot());
        }
        
        snapshots
    }
}

impl Default for MetricsRegistry {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_prometheus_metrics_creation() {
        let metrics = PrometheusMetrics::new("test", "redpanda");
        assert_eq!(metrics.namespace, "test");
        assert_eq!(metrics.subsystem, "redpanda");
    }

    #[tokio::test]
    async fn test_metrics_registry() {
        let registry = MetricsRegistry::new();
        let producer_metrics = registry.get_producer_metrics("test", "producer_1").await;
        
        // Test that metrics are created without panicking
        producer_metrics.record_message_sent(1024, Duration::from_millis(10));
        producer_metrics.record_error();
        producer_metrics.set_compression_ratio(0.7);
        producer_metrics.set_in_flight_messages(5);
    }

    #[tokio::test]
    async fn test_consumer_metrics() {
        let registry = MetricsRegistry::new();
        let consumer_metrics = registry.get_consumer_metrics("test", "consumer_1").await;
        
        consumer_metrics.record_message_received(512, Duration::from_millis(5));
        consumer_metrics.record_poll_duration(Duration::from_millis(2));
        consumer_metrics.set_lag(100);
        consumer_metrics.record_error();
        consumer_metrics.record_rebalance();
    }

    #[tokio::test]
    async fn test_stream_metrics() {
        let registry = MetricsRegistry::new();
        let stream_metrics = registry.get_stream_metrics("test", "stream_1").await;
        
        stream_metrics.record_processing(100, 95, Duration::from_millis(50));
        stream_metrics.set_throughput(1000.0);
        stream_metrics.set_error_rate(0.05);
        stream_metrics.set_buffer_size(10000);
    }
}
