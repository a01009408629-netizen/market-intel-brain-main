//! Redpanda client wrapper for high-performance streaming

use crate::core::*;
use crate::config::*;
use crate::metrics::*;
use rdkafka::config::ClientConfig;
use rdkafka::consumer::{BaseConsumer, BaseConsumer as RdKafkaBaseConsumer};
use rdkafka::producer::{BaseProducer, BaseProducer as RdKafkaBaseProducer, ThreadedProducer};
use rdkafka::producer::FutureProducer as RdKafkaFutureProducer;
use rdkafka::message::OwnedMessage;
use rdkafka::util::Timeout;
use rdkafka::error::KafkaResult;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::RwLock;
use tracing::{debug, error, info, warn};

/// Redpanda client wrapper
pub struct RedpandaClient {
    /// Client configuration
    config: RedpandaConfig,
    /// Metrics collector
    metrics: Arc<dyn MetricsCollector>,
    /// Client ID
    client_id: String,
    /// Connection status
    connection_status: Arc<RwLock<ConnectionStatus>>,
}

/// Connection status
#[derive(Debug, Clone, PartialEq)]
pub enum ConnectionStatus {
    Disconnected,
    Connecting,
    Connected,
    Reconnecting,
    Error(String),
}

impl RedpandaClient {
    /// Create new Redpanda client
    pub fn new(config: RedpandaConfig, metrics: Arc<dyn MetricsCollector>) -> Self {
        let client_id = format!("{}-{}", defaults::CLIENT_ID_PREFIX, uuid::Uuid::new_v4());
        
        Self {
            config,
            metrics,
            client_id,
            connection_status: Arc::new(RwLock::new(ConnectionStatus::Disconnected)),
        }
    }
    
    /// Get client ID
    pub fn client_id(&self) -> &str {
        &self.client_id
    }
    
    /// Get connection status
    pub async fn connection_status(&self) -> ConnectionStatus {
        self.connection_status.read().await.clone()
    }
    
    /// Create base consumer configuration
    pub fn create_consumer_config(&self, group_id: &str) -> KafkaResult<ClientConfig> {
        let mut config = ClientConfig::new();
        
        // Bootstrap servers
        config.set("bootstrap.servers", &self.config.bootstrap_servers);
        
        // Client ID
        config.set("client.id", &self.client_id);
        config.set("group.id", group_id);
        
        // Session settings
        config.set("session.timeout.ms", &self.config.session_timeout_ms.to_string());
        config.set("heartbeat.interval.ms", &self.config.heartbeat_interval_ms.to_string());
        
        // Auto offset reset
        config.set("auto.offset.reset", "earliest");
        config.set("enable.auto.commit", "false");
        
        // Security
        if let Some(sasl_username) = &self.config.sasl_username {
            config.set("sasl.mechanisms", "PLAIN");
            config.set("sasl.username", sasl_username);
            config.set("sasl.password", self.config.sasl_password.as_ref().unwrap_or(&String::new()));
        }
        
        // SSL/TLS
        if self.config.ssl_enabled {
            config.set("security.protocol", "ssl");
            config.set("ssl.ca.location", &self.config.ssl_ca_location);
            if let Some(ssl_cert_location) = &self.config.ssl_cert_location {
                config.set("ssl.certificate.location", ssl_cert_location);
            }
            if let Some(ssl_key_location) = &self.config.ssl_key_location {
                config.set("ssl.key.location", ssl_key_location);
            }
            config.set("ssl.key.password", self.config.ssl_key_password.as_ref().unwrap_or(&String::new()));
        }
        
        // Performance tuning
        config.set("socket.timeout.ms", "6000");
        config.set("socket.keepalive.enable", "true");
        config.set("reconnect.backoff.ms", "100");
        config.set("reconnect.backoff.max.ms", "10000");
        
        // Compression
        config.set("compression.type", &self.config.compression_type);
        
        Ok(config)
    }
    
    /// Create base producer configuration
    pub fn create_producer_config(&self) -> KafkaResult<ClientConfig> {
        let mut config = ClientConfig::new();
        
        // Bootstrap servers
        config.set("bootstrap.servers", &self.config.bootstrap_servers);
        
        // Client ID
        config.set("client.id", &self.client_id);
        
        // Delivery settings
        config.set("acks", &self.config.acks);
        config.set("delivery.timeout.ms", "10000");
        config.set("request.timeout.ms", "30000");
        
        // Queueing
        config.set("queue.buffering.max.messages", &self.config.queue_buffering_max_messages.to_string());
        config.set("queue.buffering.max.kbytes", &self.config.queue_buffering_max_kb.to_string());
        config.set("queue.buffering.max.ms", &self.config.queue_buffering_max_ms.to_string());
        
        // Compression
        config.set("compression.type", &self.config.compression_type);
        config.set("compression.type", "lz4"); // Force LZ4 for best performance
        
        // Security (same as consumer)
        if let Some(sasl_username) = &self.config.sasl_username {
            config.set("sasl.mechanisms", "PLAIN");
            config.set("sasl.username", sasl_username);
            config.set("sasl.password", self.config.sasl_password.as_ref().unwrap_or(&String::new()));
        }
        
        if self.config.ssl_enabled {
            config.set("security.protocol", "ssl");
            config.set("ssl.ca.location", &self.config.ssl_ca_location);
            if let Some(ssl_cert_location) = &self.config.ssl_cert_location {
                config.set("ssl.certificate.location", ssl_cert_location);
            }
            if let Some(ssl_key_location) = &self.config.ssl_key_location {
                config.set("ssl.key.location", ssl_key_location);
            }
            config.set("ssl.key.password", self.config.ssl_key_password.as_ref().unwrap_or(&String::new()));
        }
        
        // Performance tuning
        config.set("socket.timeout.ms", "6000");
        config.set("socket.keepalive.enable", "true");
        config.set("reconnect.backoff.ms", "100");
        config.set("reconnect.backoff.max.ms", "10000");
        config.set("batch.num.messages", "1000");
        config.set("batch.size", "16384");
        
        Ok(config)
    }
    
    /// Create admin client configuration
    pub fn create_admin_config(&self) -> KafkaResult<ClientConfig> {
        let mut config = ClientConfig::new();
        
        // Bootstrap servers
        config.set("bootstrap.servers", &self.config.bootstrap_servers);
        
        // Client ID
        config.set("client.id", &self.client_id);
        
        // Admin settings
        config.set("socket.timeout.ms", "6000");
        config.set("request.timeout.ms", "30000");
        
        // Security (same as producer/consumer)
        if let Some(sasl_username) = &self.config.sasl_username {
            config.set("sasl.mechanisms", "PLAIN");
            config.set("sasl.username", sasl_username);
            config.set("sasl.password", self.config.sasl_password.as_ref().unwrap_or(&String::new()));
        }
        
        if self.config.ssl_enabled {
            config.set("security.protocol", "ssl");
            config.set("ssl.ca.location", &self.config.ssl_ca_location);
            if let Some(ssl_cert_location) = &self.config.ssl_cert_location {
                config.set("ssl.certificate.location", ssl_cert_location);
            }
            if let Some(ssl_key_location) = &self.config.ssl_key_location {
                config.set("ssl.key.location", ssl_key_location);
            }
            config.set("ssl.key.password", self.config.ssl_key_password.as_ref().unwrap_or(&String::new()));
        }
        
        Ok(config)
    }
    
    /// Create base consumer
    pub fn create_base_consumer(&self, group_id: &str) -> KafkaResult<BaseConsumer> {
        let config = self.create_consumer_config(group_id)?;
        let consumer = BaseConsumer::from_config(&config)?;
        
        // Update connection status
        let mut status = self.connection_status.blocking_write();
        *status = ConnectionStatus::Connected;
        drop(status);
        
        info!("Created base consumer with group ID: {}", group_id);
        Ok(consumer)
    }
    
    /// Create threaded producer
    pub fn create_threaded_producer(&self) -> KafkaResult<ThreadedProducer> {
        let config = self.create_producer_config()?;
        let producer = ThreadedProducer::from_config(&config)?;
        
        // Update connection status
        let mut status = self.connection_status.blocking_write();
        *status = ConnectionStatus::Connected;
        drop(status);
        
        info!("Created threaded producer");
        Ok(producer)
    }
    
    /// Create future producer
    pub fn create_future_producer(&self) -> KafkaResult<RdKafkaFutureProducer> {
        let config = self.create_producer_config()?;
        let producer = RdKafkaFutureProducer::from_config(&config)?;
        
        // Update connection status
        let mut status = self.connection_status.blocking_write();
        *status = ConnectionStatus::Connected;
        drop(status);
        
        info!("Created future producer");
        Ok(producer)
    }
    
    /// Test connection
    pub async fn test_connection(&self) -> Result<()> {
        let mut status = self.connection_status.write().await;
        *status = ConnectionStatus::Connecting;
        drop(status);
        
        // Try to create a temporary producer to test connection
        match self.create_threaded_producer() {
            Ok(producer) => {
                // Test with a simple metadata request
                let metadata = producer.client().fetch_metadata(None, Timeout::After(Duration::from_secs(5)))?;
                
                if metadata.brokers().len() > 0 {
                    let mut status = self.connection_status.write().await;
                    *status = ConnectionStatus::Connected;
                    drop(status);
                    
                    info!("Redpanda connection test successful");
                    Ok(())
                } else {
                    let mut status = self.connection_status.write().await;
                    *status = ConnectionStatus::Error("No brokers available".to_string());
                    drop(status);
                    
                    Err(MarketIntelError::network("No brokers available"))
                }
            }
            Err(e) => {
                let mut status = self.connection_status.write().await;
                *status = ConnectionStatus::Error(format!("Connection failed: {}", e));
                drop(status);
                
                error!("Redpanda connection test failed: {}", e);
                Err(MarketIntelError::network(format!("Connection failed: {}", e)))
            }
        }
    }
    
    /// Get cluster metadata
    pub async fn get_cluster_metadata(&self) -> Result<ClusterMetadata> {
        let producer = self.create_threaded_producer()?;
        let metadata = producer.client().fetch_metadata(None, Timeout::After(Duration::from_secs(10)))?;
        
        let brokers = metadata.brokers().iter()
            .map(|broker| BrokerInfo {
                id: broker.id(),
                host: broker.host().to_string(),
                port: broker.port(),
            })
            .collect();
        
        let topics = metadata.topics().iter()
            .map(|topic| TopicInfo {
                name: topic.name().to_string(),
                partitions: topic.partitions().len(),
                replication_factor: topic.partitions()
                    .first()
                    .map(|p| p.replicas().len() as i32)
                    .unwrap_or(0),
            })
            .collect();
        
        Ok(ClusterMetadata {
            brokers,
            topics,
            controller_id: metadata.controller_id(),
            cluster_id: metadata.cluster_id().unwrap_or("unknown").to_string(),
        })
    }
    
    /// Update connection status
    async fn update_connection_status(&self, status: ConnectionStatus) {
        let mut current_status = self.connection_status.write().await;
        *current_status = status;
    }
}

impl Drop for RedpandaClient {
    fn drop(&mut self) {
        info!("Redpanda client {} shutting down", self.client_id);
    }
}

/// Cluster metadata information
#[derive(Debug, Clone)]
pub struct ClusterMetadata {
    /// Brokers in the cluster
    pub brokers: Vec<BrokerInfo>,
    /// Topics in the cluster
    pub topics: Vec<TopicInfo>,
    /// Controller broker ID
    pub controller_id: i32,
    /// Cluster ID
    pub cluster_id: String,
}

/// Broker information
#[derive(Debug, Clone)]
pub struct BrokerInfo {
    /// Broker ID
    pub id: i32,
    /// Broker host
    pub host: String,
    /// Broker port
    pub port: i32,
}

/// Topic information
#[derive(Debug, Clone)]
pub struct TopicInfo {
    /// Topic name
    pub name: String,
    /// Number of partitions
    pub partitions: usize,
    /// Replication factor
    pub replication_factor: i32,
}

/// Connection pool for Redpanda clients
pub struct RedpandaConnectionPool {
    clients: Arc<RwLock<Vec<Arc<RedpandaClient>>>>,
    config: RedpandaConfig,
    metrics: Arc<dyn MetricsCollector>,
    max_connections: usize,
}

impl RedpandaConnectionPool {
    /// Create new connection pool
    pub fn new(config: RedpandaConfig, metrics: Arc<dyn MetricsCollector>, max_connections: usize) -> Self {
        Self {
            clients: Arc::new(RwLock::new(Vec::new())),
            config,
            metrics,
            max_connections,
        }
    }
    
    /// Get client from pool
    pub async fn get_client(&self) -> Result<Arc<RedpandaClient>> {
        let mut clients = self.clients.write().await;
        
        // Try to find an available client
        for client in clients.iter() {
            if client.connection_status().await == ConnectionStatus::Connected {
                return Ok(Arc::clone(client));
            }
        }
        
        // Create new client if under limit
        if clients.len() < self.max_connections {
            let client = Arc::new(RedpandaClient::new(self.config.clone(), Arc::clone(&self.metrics)));
            clients.push(Arc::clone(&client));
            
            // Test connection
            client.test_connection().await?;
            Ok(client)
        } else {
            Err(MarketIntelError::network("Connection pool exhausted"))
        }
    }
    
    /// Return client to pool
    pub async fn return_client(&self, _client: Arc<RedpandaClient>) {
        // In this implementation, clients are kept in the pool
        // The connection status will be checked on next use
    }
    
    /// Get pool statistics
    pub async fn get_stats(&self) -> PoolStats {
        let clients = self.clients.read().await;
        let mut connected = 0;
        let mut connecting = 0;
        let mut error = 0;
        
        for client in clients.iter() {
            match client.connection_status().await {
                ConnectionStatus::Connected => connected += 1,
                ConnectionStatus::Connecting => connecting += 1,
                ConnectionStatus::Error(_) => error += 1,
                _ => {}
            }
        }
        
        PoolStats {
            total_clients: clients.len(),
            connected_clients: connected,
            connecting_clients: connecting,
            error_clients: error,
            max_connections: self.max_connections,
        }
    }
    
    /// Close all connections
    pub async fn close_all(&self) -> Result<()> {
        let mut clients = self.clients.write().await;
        clients.clear();
        info!("Closed all Redpanda connections");
        Ok(())
    }
}

/// Connection pool statistics
#[derive(Debug, Clone)]
pub struct PoolStats {
    /// Total clients in pool
    pub total_clients: usize,
    /// Connected clients
    pub connected_clients: usize,
    /// Connecting clients
    pub connecting_clients: usize,
    /// Error clients
    pub error_clients: usize,
    /// Maximum connections
    pub max_connections: usize,
}

impl PoolStats {
    /// Get connection success rate
    pub fn success_rate(&self) -> f64 {
        if self.total_clients == 0 {
            100.0
        } else {
            (self.connected_clients as f64 / self.total_clients as f64) * 100.0
        }
    }
    
    /// Check if pool is healthy
    pub fn is_healthy(&self) -> bool {
        self.success_rate() >= 80.0 && self.error_clients == 0
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_redpanda_client_creation() {
        let config = RedpandaConfig::default();
        let metrics = Arc::new(crate::metrics::PrometheusMetrics::new());
        let client = RedpandaClient::new(config, metrics);
        
        assert!(!client.client_id().is_empty());
        assert_eq!(client.connection_status().blocking_read(), &ConnectionStatus::Disconnected);
    }
    
    #[test]
    fn test_connection_pool() {
        let config = RedpandaConfig::default();
        let metrics = Arc::new(crate::metrics::PrometheusMetrics::new());
        let pool = RedpandaConnectionPool::new(config, metrics, 5);
        
        let stats = pool.blocking_get_stats();
        assert_eq!(stats.total_clients, 0);
        assert_eq!(stats.max_connections, 5);
        assert!(stats.is_healthy());
    }
    
    #[test]
    fn test_pool_stats() {
        let stats = PoolStats {
            total_clients: 10,
            connected_clients: 8,
            connecting_clients: 1,
            error_clients: 1,
            max_connections: 15,
        };
        
        assert_eq!(stats.success_rate(), 80.0);
        assert!(stats.is_healthy());
        
        let unhealthy_stats = PoolStats {
            total_clients: 10,
            connected_clients: 5,
            connecting_clients: 2,
            error_clients: 3,
            max_connections: 15,
        };
        
        assert_eq!(unhealthy_stats.success_rate(), 50.0);
        assert!(!unhealthy_stats.is_healthy());
    }
}
