//! Aeron client wrapper for ultra-low latency messaging

use crate::core::*;
use crate::message_types::*;
use crate::config::*;
use aeron::client::concurrent::Aeron;
use aeron::client::publication::Publication;
use aeron::client::subscription::Subscription;
use aeron::concurrent::atomic_buffer::AtomicBuffer;
use aeron::concurrent::logbuffer::header::Header;
use aeron::concurrent::status::ReadablePosition;
use aeron::driver::MediaDriver;
use aeron::utils::concurrent::broadcast::CopyBroadcastReceiver;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{mpsc, oneshot, RwLock};
use tokio::time::timeout;
use tracing::{debug, error, info, warn};

/// Aeron client wrapper
pub struct AeronClient {
    /// Aeron instance
    aeron: Arc<Aeron>,
    /// Media driver context
    _driver: Option<MediaDriver>,
    /// Configuration
    config: AeronConfig,
    /// Active publications
    publications: Arc<RwLock<HashMap<String, Arc<Publication>>>>,
    /// Active subscriptions
    subscriptions: Arc<RwLock<HashMap<String, Arc<Subscription>>>>,
}

impl AeronClient {
    /// Create new Aeron client
    pub async fn new(config: AeronConfig) -> Result<Self> {
        info!("Initializing Aeron client with config: {:?}", config);
        
        // Start media driver if embedded
        let driver = if config.embedded_media_driver {
            let driver = MediaDriver::new()
                .aeron_dir(&config.aeron_dir)
                .dirs_delete_on_start(config.dirs_delete_on_start)
                .dirs_delete_on_shutdown(config.dirs_delete_on_shutdown)
                .threading_mode(config.threading_mode.clone())
                .spawn()?;
            
            // Wait for driver to be ready
            tokio::time::sleep(Duration::from_millis(100)).await;
            Some(driver)
        } else {
            None
        };
        
        // Create Aeron context
        let aeron_context = aeron::client::Context::new()
            .aeron_dir(&config.aeron_dir)
            .new_publication_handler(Box::new(|_publication_id, _channel, _stream_id, _session_id, _correlation_id| {
                debug!("New publication created");
            }))
            .new_subscription_handler(Box::new(|_subscription_id, _channel, _stream_id, _correlation_id| {
                debug!("New subscription created");
            }));
        
        // Connect to Aeron
        let aeron = Arc::new(aeron_context.await_connect()?);
        
        info!("Aeron client connected successfully");
        
        Ok(Self {
            aeron,
            _driver: driver,
            config,
            publications: Arc::new(RwLock::new(HashMap::new())),
            subscriptions: Arc::new(RwLock::new(HashMap::new())),
        })
    }
    
    /// Add publication
    pub async fn add_publication(&self, channel: &str, stream_id: i32) -> Result<Arc<Publication>> {
        let key = format!("{}:{}", channel, stream_id);
        
        // Check if publication already exists
        {
            let publications = self.publications.read().await;
            if let Some(publ) = publications.get(&key) {
                return Ok(Arc::clone(publ));
            }
        }
        
        // Create new publication
        let publication = Arc::new(
            self.aeron
                .add_publication(channel, stream_id)
                .await?
        );
        
        // Store publication
        {
            let mut publications = self.publications.write().await;
            publications.insert(key, Arc::clone(&publication));
        }
        
        info!("Added publication on channel: {}, stream: {}", channel, stream_id);
        Ok(publication)
    }
    
    /// Add subscription
    pub async fn add_subscription(&self, channel: &str, stream_id: i32) -> Result<Arc<Subscription>> {
        let key = format!("{}:{}", channel, stream_id);
        
        // Check if subscription already exists
        {
            let subscriptions = self.subscriptions.read().await;
            if let Some(sub) = subscriptions.get(&key) {
                return Ok(Arc::clone(sub));
            }
        }
        
        // Create new subscription
        let subscription = Arc::new(
            self.aeron
                .add_subscription(channel, stream_id)
                .await?
        );
        
        // Store subscription
        {
            let mut subscriptions = self.subscriptions.write().await;
            subscriptions.insert(key, Arc::clone(&subscription));
        }
        
        info!("Added subscription on channel: {}, stream: {}", channel, stream_id);
        Ok(subscription)
    }
    
    /// Get publication
    pub async fn get_publication(&self, channel: &str, stream_id: i32) -> Option<Arc<Publication>> {
        let key = format!("{}:{}", channel, stream_id);
        let publications = self.publications.read().await;
        publications.get(&key).cloned()
    }
    
    /// Get subscription
    pub async fn get_subscription(&self, channel: &str, stream_id: i32) -> Option<Arc<Subscription>> {
        let key = format!("{}:{}", channel, stream_id);
        let subscriptions = self.subscriptions.read().await;
        subscriptions.get(&key).cloned()
    }
    
    /// Remove publication
    pub async fn remove_publication(&self, channel: &str, stream_id: i32) -> Result<()> {
        let key = format!("{}:{}", channel, stream_id);
        let mut publications = self.publications.write().await;
        
        if let Some(publication) = publications.remove(&key) {
            // Close publication
            publication.close();
            info!("Removed publication on channel: {}, stream: {}", channel, stream_id);
        }
        
        Ok(())
    }
    
    /// Remove subscription
    pub async fn remove_subscription(&self, channel: &str, stream_id: i32) -> Result<()> {
        let key = format!("{}:{}", channel, stream_id);
        let mut subscriptions = self.subscriptions.write().await;
        
        if let Some(subscription) = subscriptions.remove(&key) {
            // Close subscription
            subscription.close();
            info!("Removed subscription on channel: {}, stream: {}", channel, stream_id);
        }
        
        Ok(())
    }
    
    /// Get Aeron instance
    pub fn aeron(&self) -> Arc<Aeron> {
        Arc::clone(&self.aeron)
    }
    
    /// Get client ID
    pub fn client_id(&self) -> i64 {
        self.aeron.client_id()
    }
    
    /// Get status counters
    pub async fn get_status(&self) -> AeronStatus {
        let publications_count = self.publications.read().await.len();
        let subscriptions_count = self.subscriptions.read().await.len();
        
        AeronStatus {
            client_id: self.client_id(),
            publications_count,
            subscriptions_count,
            aeron_dir: self.config.aeron_dir.clone(),
        }
    }
}

impl Drop for AeronClient {
    fn drop(&mut self) {
        info!("Shutting down Aeron client");
        
        // Close all publications and subscriptions
        if let Ok(publications) = self.publications.try_write() {
            for (_, publication) in publications.drain() {
                publication.close();
            }
        }
        
        if let Ok(subscriptions) = self.subscriptions.try_write() {
            for (_, subscription) in subscriptions.drain() {
                subscription.close();
            }
        }
    }
}

/// Aeron status information
#[derive(Debug, Clone)]
pub struct AeronStatus {
    /// Client ID
    pub client_id: i64,
    /// Number of active publications
    pub publications_count: usize,
    /// Number of active subscriptions
    pub subscriptions_count: usize,
    /// Aeron directory
    pub aeron_dir: String,
}

/// Aeron configuration
#[derive(Debug, Clone)]
pub struct AeronConfig {
    /// Aeron directory
    pub aeron_dir: String,
    /// Use embedded media driver
    pub embedded_media_driver: bool,
    /// Delete directories on start
    pub dirs_delete_on_start: bool,
    /// Delete directories on shutdown
    pub dirs_delete_on_shutdown: bool,
    /// Threading mode
    pub threading_mode: String,
    /// Publication timeout
    pub publication_timeout_ns: u64,
    /// Subscription timeout
    pub subscription_timeout_ns: u64,
    /// Linger timeout
    pub linger_timeout_ns: u64,
    /// Resource linger timeout
    pub resource_linger_timeout_ns: u64,
}

impl Default for AeronConfig {
    fn default() -> Self {
        Self {
            aeron_dir: defaults::AERON_DIR.to_string(),
            embedded_media_driver: true,
            dirs_delete_on_start: false,
            dirs_delete_on_shutdown: false,
            threading_mode: "SHARED".to_string(),
            publication_timeout_ns: defaults::PUBLICATION_TIMEOUT_NS,
            subscription_timeout_ns: defaults::PUBLICATION_TIMEOUT_NS,
            linger_timeout_ns: defaults::LINGER_TIMEOUT_NS,
            resource_linger_timeout_ns: defaults::LINGER_TIMEOUT_NS,
        }
    }
}

/// Aeron connection manager
pub struct AeronConnectionManager {
    client: Arc<AeronClient>,
    connection_pool: Arc<RwLock<HashMap<String, Arc<AeronConnection>>>>,
}

impl AeronConnectionManager {
    /// Create new connection manager
    pub fn new(client: Arc<AeronClient>) -> Self {
        Self {
            client,
            connection_pool: Arc::new(RwLock::new(HashMap::new())),
        }
    }
    
    /// Get or create connection
    pub async fn get_connection(&self, channel: &str, stream_id: i32) -> Result<Arc<AeronConnection>> {
        let key = format!("{}:{}", channel, stream_id);
        
        // Check if connection already exists
        {
            let pool = self.connection_pool.read().await;
            if let Some(conn) = pool.get(&key) {
                return Ok(Arc::clone(conn));
            }
        }
        
        // Create new connection
        let publication = self.client.add_publication(channel, stream_id).await?;
        let subscription = self.client.add_subscription(channel, stream_id).await?;
        
        let connection = Arc::new(AeronConnection::new(
            Arc::clone(&self.client),
            publication,
            subscription,
            channel.to_string(),
            stream_id,
        ));
        
        // Store connection
        {
            let mut pool = self.connection_pool.write().await;
            pool.insert(key, Arc::clone(&connection));
        }
        
        Ok(connection)
    }
    
    /// Close connection
    pub async fn close_connection(&self, channel: &str, stream_id: i32) -> Result<()> {
        let key = format!("{}:{}", channel, stream_id);
        let mut pool = self.connection_pool.write().await;
        
        if let Some(connection) = pool.remove(&key) {
            connection.close().await?;
        }
        
        Ok(())
    }
    
    /// Get all connections
    pub async fn get_connections(&self) -> Vec<Arc<AeronConnection>> {
        let pool = self.connection_pool.read().await;
        pool.values().cloned().collect()
    }
    
    /// Close all connections
    pub async fn close_all(&self) -> Result<()> {
        let mut pool = self.connection_pool.write().await;
        
        for (_, connection) in pool.drain() {
            if let Err(e) = connection.close().await {
                error!("Error closing connection: {}", e);
            }
        }
        
        Ok(())
    }
}

/// Aeron connection wrapper
pub struct AeronConnection {
    client: Arc<AeronClient>,
    publication: Arc<Publication>,
    subscription: Arc<Subscription>,
    channel: String,
    stream_id: i32,
    message_sender: mpsc::UnboundedSender<UnifiedMessage>,
    message_receiver: Arc<RwLock<Option<mpsc::UnboundedReceiver<UnifiedMessage>>>>,
}

impl AeronConnection {
    /// Create new connection
    pub fn new(
        client: Arc<AeronClient>,
        publication: Arc<Publication>,
        subscription: Arc<Subscription>,
        channel: String,
        stream_id: i32,
    ) -> Self {
        let (sender, receiver) = mpsc::unbounded_channel();
        
        Self {
            client,
            publication,
            subscription,
            channel,
            stream_id,
            message_sender: sender,
            message_receiver: Arc::new(RwLock::new(Some(receiver))),
        }
    }
    
    /// Publish message
    pub async fn publish(&self, message: &UnifiedMessage) -> Result<()> {
        let buffer = message.encode_to_vec()?;
        
        // Try to publish with timeout
        let result = timeout(
            Duration::from_nanos(client.config.publication_timeout_ns),
            self.publication.offer(&buffer)
        ).await;
        
        match result {
            Ok(Ok(Some(position))) => {
                debug!("Message published at position: {}", position);
                Ok(())
            }
            Ok(Ok(None)) => {
                warn!("Publication buffer full, message dropped");
                Err(MarketIntelError::network("Publication buffer full"))
            }
            Ok(Err(e)) => {
                error!("Publication error: {}", e);
                Err(MarketIntelError::network(format!("Publication failed: {}", e)))
            }
            Err(_) => {
                error!("Publication timeout");
                Err(MarketIntelError::timeout(client.config.publication_timeout_ns))
            }
        }
    }
    
    /// Subscribe to messages
    pub async fn subscribe(&self) -> mpsc::UnboundedReceiver<UnifiedMessage> {
        // Take receiver if available
        let mut receiver_guard = self.message_receiver.write().await;
        if let Some(receiver) = receiver_guard.take() {
            receiver
        } else {
            // Create new receiver if none available
            let (_, receiver) = mpsc::unbounded_channel();
            receiver
        }
    }
    
    /// Get channel
    pub fn channel(&self) -> &str {
        &self.channel
    }
    
    /// Get stream ID
    pub fn stream_id(&self) -> i32 {
        self.stream_id
    }
    
    /// Get publication status
    pub fn publication_status(&self) -> PublicationStatus {
        PublicationStatus {
            channel: self.channel.clone(),
            stream_id: self.stream_id,
            session_id: self.publication.session_id(),
            position: self.publication.position(),
            is_connected: self.publication.is_connected(),
        }
    }
    
    /// Get subscription status
    pub fn subscription_status(&self) -> SubscriptionStatus {
        SubscriptionStatus {
            channel: self.channel.clone(),
            stream_id: self.stream_id,
            session_id: self.subscription.session_id(),
            position: self.subscription.position(),
            is_connected: self.subscription.is_connected(),
            image_count: self.subscription.image_count(),
            image_length: self.subscription.image_length(),
        }
    }
    
    /// Close connection
    pub async fn close(self) -> Result<()> {
        info!("Closing Aeron connection: {}:{}", self.channel, self.stream_id);
        
        // Close publication and subscription
        self.publication.close();
        self.subscription.close();
        
        // Remove from client
        self.client.remove_publication(&self.channel, self.stream_id).await?;
        self.client.remove_subscription(&self.channel, self.stream_id).await?;
        
        Ok(())
    }
}

/// Publication status
#[derive(Debug, Clone)]
pub struct PublicationStatus {
    pub channel: String,
    pub stream_id: i32,
    pub session_id: i64,
    pub position: i64,
    pub is_connected: bool,
}

/// Subscription status
#[derive(Debug, Clone)]
pub struct SubscriptionStatus {
    pub channel: String,
    pub stream_id: i32,
    pub session_id: i64,
    pub position: i64,
    pub is_connected: bool,
    pub image_count: i32,
    pub image_length: i32,
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_aeron_client_creation() {
        let config = AeronConfig::default();
        let client = AeronClient::new(config).await;
        assert!(client.is_ok());
    }
    
    #[tokio::test]
    async fn test_publication_subscription() {
        let config = AeronConfig::default();
        let client = AeronClient::new(config).await.unwrap();
        
        let channel = defaults::MARKET_DATA_CHANNEL;
        let stream_id = defaults::MARKET_DATA_STREAM_ID;
        
        let publication = client.add_publication(channel, stream_id).await;
        assert!(publication.is_ok());
        
        let subscription = client.add_subscription(channel, stream_id).await;
        assert!(subscription.is_ok());
    }
    
    #[tokio::test]
    async fn test_connection_manager() {
        let config = AeronConfig::default();
        let client = Arc::new(AeronClient::new(config).await.unwrap());
        let manager = AeronConnectionManager::new(Arc::clone(&client));
        
        let channel = defaults::MARKET_DATA_CHANNEL;
        let stream_id = defaults::MARKET_DATA_STREAM_ID;
        
        let connection = manager.get_connection(channel, stream_id).await;
        assert!(connection.is_ok());
        
        let connections = manager.get_connections().await;
        assert_eq!(connections.len(), 1);
    }
}
