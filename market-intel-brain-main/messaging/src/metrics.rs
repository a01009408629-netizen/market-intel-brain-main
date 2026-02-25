//! Metrics collection for Aeron messaging

use crate::core::*;
use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;

/// Metrics collector trait
pub trait MetricsCollector: Send + Sync {
    /// Increment counter
    fn increment_counter(&self, name: &str, labels: Option<HashMap<String, String>>);
    
    /// Set gauge value
    fn set_gauge(&self, name: &str, value: f64, labels: Option<HashMap<String, String>>);
    
    /// Record histogram value
    fn record_histogram(&self, name: &str, value: f64, labels: Option<HashMap<String, String>>);
    
    /// Record timer duration
    fn record_timer(&self, name: &str, duration: Duration, labels: Option<HashMap<String, String>>);
    
    /// Get metrics snapshot
    fn get_metrics(&self) -> MetricsSnapshot;
}

/// Prometheus metrics collector
pub struct PrometheusMetrics {
    /// Counters
    counters: Arc<RwLock<HashMap<String, AtomicU64>>>,
    /// Gauges
    gauges: Arc<RwLock<HashMap<String, AtomicU64>>>,
    /// Histograms
    histograms: Arc<RwLock<HashMap<String, HistogramData>>>,
    /// Metrics metadata
    metadata: Arc<RwLock<HashMap<String, MetricMetadata>>>,
}

/// Histogram data
#[derive(Debug)]
struct HistogramData {
    /// Sum of values
    sum: AtomicU64,
    /// Count of values
    count: AtomicU64,
    /// Buckets
    buckets: Arc<RwLock<Vec<f64>>>,
    /// Bucket counts
    bucket_counts: Arc<RwLock<Vec<AtomicU64>>>,
}

/// Metric metadata
#[derive(Debug, Clone)]
struct MetricMetadata {
    /// Description
    description: String,
    /// Type
    metric_type: MetricType,
    /// Labels
    labels: HashMap<String, String>,
}

/// Metric types
#[derive(Debug, Clone, PartialEq)]
pub enum MetricType {
    Counter,
    Gauge,
    Histogram,
}

impl PrometheusMetrics {
    /// Create new metrics collector
    pub fn new() -> Self {
        Self {
            counters: Arc::new(RwLock::new(HashMap::new())),
            gauges: Arc::new(RwLock::new(HashMap::new())),
            histograms: Arc::new(RwLock::new(HashMap::new())),
            metadata: Arc::new(RwLock::new(HashMap::new())),
        }
    }
    
    /// Register counter
    pub async fn register_counter(&self, name: &str, description: &str) {
        let mut counters = self.counters.write().await;
        counters.insert(name.to_string(), AtomicU64::new(0));
        
        let mut metadata = self.metadata.write().await;
        metadata.insert(name.to_string(), MetricMetadata {
            description: description.to_string(),
            metric_type: MetricType::Counter,
            labels: HashMap::new(),
        });
    }
    
    /// Register gauge
    pub async fn register_gauge(&self, name: &str, description: &str) {
        let mut gauges = self.gauges.write().await;
        gauges.insert(name.to_string(), AtomicU64::new(0));
        
        let mut metadata = self.metadata.write().await;
        metadata.insert(name.to_string(), MetricMetadata {
            description: description.to_string(),
            metric_type: MetricType::Gauge,
            labels: HashMap::new(),
        });
    }
    
    /// Register histogram
    pub async fn register_histogram(&self, name: &str, description: &str, buckets: Vec<f64>) {
        let bucket_counts: Vec<AtomicU64> = buckets.iter().map(|_| AtomicU64::new(0)).collect();
        
        let histogram_data = HistogramData {
            sum: AtomicU64::new(0),
            count: AtomicU64::new(0),
            buckets: Arc::new(RwLock::new(buckets)),
            bucket_counts: Arc::new(RwLock::new(bucket_counts)),
        };
        
        let mut histograms = self.histograms.write().await;
        histograms.insert(name.to_string(), histogram_data);
        
        let mut metadata = self.metadata.write().await;
        metadata.insert(name.to_string(), MetricMetadata {
            description: description.to_string(),
            metric_type: MetricType::Histogram,
            labels: HashMap::new(),
        });
    }
    
    /// Get or create counter
    async fn get_or_create_counter(&self, name: &str) -> Arc<AtomicU64> {
        let counters = self.counters.read().await;
        
        if let Some(counter) = counters.get(name) {
            Arc::clone(counter)
        } else {
            drop(counters);
            self.register_counter(name, "Auto-created counter").await;
            let counters = self.counters.read().await;
            Arc::clone(counters.get(name).unwrap())
        }
    }
    
    /// Get or create gauge
    async fn get_or_create_gauge(&self, name: &str) -> Arc<AtomicU64> {
        let gauges = self.gauges.read().await;
        
        if let Some(gauge) = gauges.get(name) {
            Arc::clone(gauge)
        } else {
            drop(gauges);
            self.register_gauge(name, "Auto-created gauge").await;
            let gauges = self.gauges.read().await;
            Arc::clone(gauges.get(name).unwrap())
        }
    }
    
    /// Get or create histogram
    async fn get_or_create_histogram(&self, name: &str) -> Option<Arc<HistogramData>> {
        let histograms = self.histograms.read().await;
        
        if let Some(histogram) = histograms.get(name) {
            Some(Arc::clone(histogram))
        } else {
            None
        }
    }
    
    /// Record histogram value
    async fn record_histogram_value(&self, name: &str, value: f64) {
        if let Some(histogram) = self.get_or_create_histogram(name).await {
            // Update sum and count
            let value_scaled = (value * 1_000_000.0) as u64; // Convert to nanoseconds
            histogram.sum.fetch_add(value_scaled, Ordering::Relaxed);
            histogram.count.fetch_add(1, Ordering::Relaxed);
            
            // Update bucket counts
            let buckets = histogram.buckets.read().await;
            let mut bucket_counts = histogram.bucket_counts.write().await;
            
            for (i, &bucket) in buckets.iter().enumerate() {
                if value <= bucket {
                    bucket_counts[i].fetch_add(1, Ordering::Relaxed);
                    break;
                }
            }
        }
    }
}

impl MetricsCollector for PrometheusMetrics {
    fn increment_counter(&self, name: &str, labels: Option<HashMap<String, String>>) {
        let rt = tokio::runtime::Handle::current();
        rt.block_on(async {
            let counter = self.get_or_create_counter(name).await;
            counter.fetch_add(1, Ordering::Relaxed);
        });
    }
    
    fn set_gauge(&self, name: &str, value: f64, labels: Option<HashMap<String, String>>) {
        let rt = tokio::runtime::Handle::current();
        rt.block_on(async {
            let gauge = self.get_or_create_gauge(name).await;
            gauge.store(value as u64, Ordering::Relaxed);
        });
    }
    
    fn record_histogram(&self, name: &str, value: f64, labels: Option<HashMap<String, String>>) {
        let rt = tokio::runtime::Handle::current();
        rt.block_on(async {
            self.record_histogram_value(name, value).await;
        });
    }
    
    fn record_timer(&self, name: &str, duration: Duration, labels: Option<HashMap<String, String>>) {
        self.record_histogram(name, duration.as_nanos() as f64, labels);
    }
    
    fn get_metrics(&self) -> MetricsSnapshot {
        let rt = tokio::runtime::Handle::current();
        rt.block_on(async {
            let mut snapshot = MetricsSnapshot::new();
            
            // Collect counters
            let counters = self.counters.read().await;
            for (name, counter) in counters.iter() {
                snapshot.counters.insert(name.clone(), counter.load(Ordering::Relaxed));
            }
            
            // Collect gauges
            let gauges = self.gauges.read().await;
            for (name, gauge) in gauges.iter() {
                snapshot.gauges.insert(name.clone(), gauge.load(Ordering::Relaxed));
            }
            
            // Collect histograms
            let histograms = self.histograms.read().await;
            for (name, histogram) in histograms.iter() {
                let sum = histogram.sum.load(Ordering::Relaxed);
                let count = histogram.count.load(Ordering::Relaxed);
                let buckets = histogram.buckets.read().await.clone();
                let bucket_counts = histogram.bucket_counts.read().await
                    .iter().map(|c| c.load(Ordering::Relaxed))
                    .collect();
                
                snapshot.histograms.insert(name.clone(), HistogramSnapshot {
                    sum,
                    count,
                    buckets,
                    bucket_counts,
                });
            }
            
            // Collect metadata
            let metadata = self.metadata.read().await;
            for (name, meta) in metadata.iter() {
                snapshot.metadata.insert(name.clone(), meta.clone());
            }
            
            snapshot
        })
    }
}

/// Metrics snapshot
#[derive(Debug, Clone, Default)]
pub struct MetricsSnapshot {
    /// Counters
    pub counters: HashMap<String, u64>,
    /// Gauges
    pub gauges: HashMap<String, u64>,
    /// Histograms
    pub histograms: HashMap<String, HistogramSnapshot>,
    /// Metadata
    pub metadata: HashMap<String, MetricMetadata>,
}

impl MetricsSnapshot {
    /// Create new snapshot
    pub fn new() -> Self {
        Self::default()
    }
    
    /// Get counter value
    pub fn get_counter(&self, name: &str) -> Option<u64> {
        self.counters.get(name).copied()
    }
    
    /// Get gauge value
    pub fn get_gauge(&self, name: &str) -> Option<u64> {
        self.gauges.get(name).copied()
    }
    
    /// Get histogram value
    pub fn get_histogram(&self, name: &str) -> Option<&HistogramSnapshot> {
        self.histograms.get(name)
    }
    
    /// Format as Prometheus text
    pub fn format_prometheus(&self) -> String {
        let mut output = String::new();
        
        // Format counters
        for (name, value) in &self.counters {
            if let Some(metadata) = self.metadata.get(name) {
                output.push_str(&format!("# HELP {} {}\n", name, metadata.description));
                output.push_str(&format!("# TYPE {} {}\n", name, "counter"));
            }
            output.push_str(&format!("{} {}\n", name, value));
        }
        
        // Format gauges
        for (name, value) in &self.gauges {
            if let Some(metadata) = self.metadata.get(name) {
                output.push_str(&format!("# HELP {} {}\n", name, metadata.description));
                output.push_str(&format!("# TYPE {} {}\n", name, "gauge"));
            }
            output.push_str(&format!("{} {}\n", name, value));
        }
        
        // Format histograms
        for (name, histogram) in &self.histograms {
            if let Some(metadata) = self.metadata.get(name) {
                output.push_str(&format!("# HELP {} {}\n", name, metadata.description));
                output.push_str(&format!("# TYPE {} {}\n", name, "histogram"));
            }
            
            // Output bucket counts
            for (i, bucket) in histogram.buckets.iter().enumerate() {
                let count = histogram.bucket_counts.get(i).unwrap_or(&0);
                output.push_str(&format!("{}_bucket{{le=\"{}\"}} {}\n", name, bucket, count));
            }
            
            // Output sum and count
            output.push_str(&format!("{}_sum {}\n", name, histogram.sum));
            output.push_str(&format!("{}_count {}\n", name, histogram.count));
        }
        
        output
    }
}

/// Histogram snapshot
#[derive(Debug, Clone)]
pub struct HistogramSnapshot {
    /// Sum of values (scaled)
    pub sum: u64,
    /// Count of values
    pub count: u64,
    /// Bucket boundaries
    pub buckets: Vec<f64>,
    /// Bucket counts
    pub bucket_counts: Vec<u64>,
}

impl HistogramSnapshot {
    /// Calculate average value
    pub fn average(&self) -> f64 {
        if self.count == 0 {
            0.0
        } else {
            (self.sum as f64 / self.count as f64) / 1_000_000.0 // Convert back from nanoseconds
        }
    }
    
    /// Calculate percentile
    pub fn percentile(&self, p: f64) -> f64 {
        if self.count == 0 {
            return 0.0;
        }
        
        let target_count = (self.count as f64 * p / 100.0) as u64;
        let mut cumulative = 0;
        
        for (i, bucket) in self.buckets.iter().enumerate() {
            cumulative += self.bucket_counts.get(i).unwrap_or(&0);
            if cumulative >= target_count {
                return *bucket;
            }
        }
        
        // If we haven't reached the target, return the last bucket
        self.buckets.last().copied().unwrap_or(0.0)
    }
    
    /// Get 50th percentile (median)
    pub fn median(&self) -> f64 {
        self.percentile(50.0)
    }
    
    /// Get 95th percentile
    pub fn p95(&self) -> f64 {
        self.percentile(95.0)
    }
    
    /// Get 99th percentile
    pub fn p99(&self) -> f64 {
        self.percentile(99.0)
    }
}

/// Default histogram buckets
pub fn default_histogram_buckets() -> Vec<f64> {
    vec![
        0.001,   // 1 microsecond
        0.01,    // 10 microseconds
        0.1,     // 100 microseconds
        1.0,     // 1 millisecond
        5.0,     // 5 milliseconds
        10.0,    // 10 milliseconds
        50.0,    // 50 milliseconds
        100.0,   // 100 milliseconds
        500.0,   // 500 milliseconds
        1000.0,  // 1 second
        5000.0,  // 5 seconds
        10000.0, // 10 seconds
    ]
}

/// Low latency histogram buckets (for ultra-low latency systems)
pub fn low_latency_buckets() -> Vec<f64> {
    vec![
        0.000001,  // 1 nanosecond
        0.00001,   // 10 nanoseconds
        0.0001,    // 100 nanoseconds
        0.001,     // 1 microsecond
        0.01,      // 10 microseconds
        0.1,       // 100 microseconds
        1.0,       // 1 millisecond
        10.0,      // 10 milliseconds
        100.0,     // 100 milliseconds
    ]
}

/// High throughput histogram buckets
pub fn high_throughput_buckets() -> Vec<f64> {
    vec![
        0.1,      // 100 microseconds
        1.0,      // 1 millisecond
        10.0,     // 10 milliseconds
        50.0,     // 50 milliseconds
        100.0,    // 100 milliseconds
        500.0,    // 500 milliseconds
        1000.0,   // 1 second
        5000.0,   // 5 seconds
        10000.0,  // 10 seconds
        30000.0,  // 30 seconds
        60000.0,  // 1 minute
    ]
}

/// Metrics registry
pub struct MetricsRegistry {
    collectors: Arc<RwLock<HashMap<String, Arc<dyn MetricsCollector>>>>,
}

impl MetricsRegistry {
    /// Create new registry
    pub fn new() -> Self {
        Self {
            collectors: Arc::new(RwLock::new(HashMap::new())),
        }
    }
    
    /// Register collector
    pub async fn register(&self, name: &str, collector: Arc<dyn MetricsCollector>) {
        let mut collectors = self.collectors.write().await;
        collectors.insert(name.to_string(), collector);
    }
    
    /// Get collector
    pub async fn get(&self, name: &str) -> Option<Arc<dyn MetricsCollector>> {
        let collectors = self.collectors.read().await;
        collectors.get(name).cloned()
    }
    
    /// Get all metrics
    pub async fn get_all_metrics(&self) -> HashMap<String, MetricsSnapshot> {
        let collectors = self.collectors.read().await;
        let mut all_metrics = HashMap::new();
        
        for (name, collector) in collectors.iter() {
            all_metrics.insert(name.clone(), collector.get_metrics());
        }
        
        all_metrics
    }
    
    /// Format all metrics as Prometheus
    pub async fn format_prometheus(&self) -> String {
        let all_metrics = self.get_all_metrics().await;
        let mut output = String::new();
        
        for (collector_name, snapshot) in all_metrics {
            output.push_str(&format!("# Metrics from collector: {}\n", collector_name));
            output.push_str(&snapshot.format_prometheus());
            output.push_str("\n");
        }
        
        output
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
    async fn test_prometheus_metrics() {
        let metrics = PrometheusMetrics::new();
        
        // Register metrics
        metrics.register_counter("test_counter", "Test counter").await;
        metrics.register_gauge("test_gauge", "Test gauge").await;
        metrics.register_histogram("test_histogram", "Test histogram", default_histogram_buckets()).await;
        
        // Increment counter
        metrics.increment_counter("test_counter", None);
        metrics.increment_counter("test_counter", None);
        
        // Set gauge
        metrics.set_gauge("test_gauge", 42.0, None);
        
        // Record histogram
        metrics.record_histogram("test_histogram", 1.5, None);
        metrics.record_histogram("test_histogram", 2.5, None);
        
        // Get snapshot
        let snapshot = metrics.get_metrics();
        
        assert_eq!(snapshot.get_counter("test_counter"), Some(2));
        assert_eq!(snapshot.get_gauge("test_gauge"), Some(42));
        
        let histogram = snapshot.get_histogram("test_histogram").unwrap();
        assert_eq!(histogram.count, 2);
        assert!(histogram.average() > 0.0);
    }
    
    #[tokio::test]
    async fn test_histogram_percentiles() {
        let mut histogram = HistogramSnapshot {
            sum: 1_500_000, // 1.5ms in nanoseconds
            count: 3,
            buckets: vec![1.0, 10.0, 100.0],
            bucket_counts: vec![1, 1, 1],
        };
        
        assert_eq!(histogram.average(), 0.5); // 1.5ms / 3 = 0.5ms
        assert_eq!(histogram.median(), 10.0);
        assert_eq!(histogram.p95(), 100.0);
    }
    
    #[tokio::test]
    async fn test_metrics_registry() {
        let registry = MetricsRegistry::new();
        let metrics = Arc::new(PrometheusMetrics::new());
        
        registry.register("test", metrics).await;
        
        let retrieved = registry.get("test").await;
        assert!(retrieved.is_some());
        
        let all_metrics = registry.get_all_metrics().await;
        assert!(all_metrics.contains_key("test"));
    }
    
    #[tokio::test]
    fn test_default_buckets() {
        let buckets = default_histogram_buckets();
        assert_eq!(buckets.len(), 12);
        assert_eq!(buckets[0], 0.001); // 1 microsecond
        assert_eq!(buckets.last(), Some(&10000.0)); // 10 seconds
    }
    
    #[tokio::test]
    fn test_low_latency_buckets() {
        let buckets = low_latency_buckets();
        assert_eq!(buckets.len(), 9);
        assert_eq!(buckets[0], 0.000001); // 1 nanosecond
        assert_eq!(buckets.last(), Some(&100.0)); // 100 milliseconds
    }
}
