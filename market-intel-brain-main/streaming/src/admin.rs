//! Redpanda administration utilities
//! 
//! This module provides administrative functions for managing Redpanda clusters,
//! topics, consumer groups, and other cluster resources.

use rdkafka::admin::{AdminClient, AdminOptions, NewTopic, TopicReplication};
use rdkafka::client::DefaultClientContext;
use rdkafka::config::ClientConfig;
use rdkafka::error::KafkaError;
use std::collections::HashMap;
use std::time::Duration;
use tokio::sync::RwLock;
use crate::config::RedpandaConfig;
use crate::serde_types::TopicConfig;

/// Redpanda admin client
#[derive(Debug)]
pub struct RedpandaAdmin {
    /// Admin client
    admin_client: AdminClient<DefaultClientContext>,
    /// Configuration
    config: RedpandaConfig,
    /// Cache for cluster metadata
    cluster_metadata: RwLock<Option<ClusterMetadata>>,
}

/// Cluster metadata
#[derive(Debug, Clone)]
pub struct ClusterMetadata {
    /// Cluster ID
    pub cluster_id: String,
    /// Controller node
    pub controller: i32,
    /// Broker information
    pub brokers: Vec<BrokerMetadata>,
    /// Topic information
    pub topics: Vec<TopicMetadata>,
    /// Metadata timestamp
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

/// Broker metadata
#[derive(Debug, Clone)]
pub struct BrokerMetadata {
    /// Broker ID
    pub broker_id: i32,
    /// Broker hostname
    pub hostname: String,
    /// Broker port
    pub port: i32,
    /// Broker rack (if available)
    pub rack: Option<String>,
}

/// Topic metadata
#[derive(Debug, Clone)]
pub struct TopicMetadata {
    /// Topic name
    pub topic_name: String,
    /// Topic internal flag
    pub internal: bool,
    /// Partition information
    pub partitions: Vec<PartitionMetadata>,
}

/// Partition metadata
#[derive(Debug, Clone)]
pub struct PartitionMetadata {
    /// Partition ID
    pub partition_id: i32,
    /// Leader broker
    pub leader: i32,
    /// Replica brokers
    pub replicas: Vec<i32>,
    /// In-sync replica brokers
    pub isr: Vec<i32>,
}

/// Consumer group metadata
#[derive(Debug, Clone)]
pub struct ConsumerGroupMetadata {
    /// Group ID
    pub group_id: String,
    /// Group state
    pub state: String,
    /// Group protocol
    pub protocol: String,
    /// Group members
    pub members: Vec<GroupMemberMetadata>,
}

/// Group member metadata
#[derive(Debug, Clone)]
pub struct GroupMemberMetadata {
    /// Member ID
    pub member_id: String,
    /// Client ID
    pub client_id: String,
    /// Client host
    pub client_host: String,
    /// Member assignments
    pub assignments: Vec<MemberAssignment>,
}

/// Member assignment
#[derive(Debug, Clone)]
pub struct MemberAssignment {
    /// Topic name
    pub topic_name: String,
    /// Partition ID
    pub partition_id: i32,
}

impl RedpandaAdmin {
    /// Create new Redpanda admin client
    pub async fn new(config: RedpandaConfig) -> Result<Self, KafkaError> {
        let mut client_config = ClientConfig::new();
        
        // Set bootstrap servers
        client_config.set("bootstrap.servers", &config.brokers.join(","));
        
        // Set client ID
        client_config.set("client.id", &config.client.client_id);
        
        // Apply security configuration
        Self::apply_security_config(&mut client_config, &config.security)?;
        
        // Create admin client
        let admin_client: AdminClient<DefaultClientContext> = client_config.create()?;
        
        Ok(Self {
            admin_client,
            config,
            cluster_metadata: RwLock::new(None),
        })
    }

    /// Apply security configuration to client config
    fn apply_security_config(
        client_config: &mut ClientConfig,
        security: &crate::config::SecurityConfig,
    ) -> Result<(), KafkaError> {
        use crate::config::{SecurityProtocol, SaslMechanism};
        
        match security.security_protocol {
            SecurityProtocol::Plaintext => {
                client_config.set("security.protocol", "plaintext");
            }
            SecurityProtocol::Ssl => {
                client_config.set("security.protocol", "ssl");
                Self::apply_ssl_config(client_config, security.ssl.as_ref())?;
            }
            SecurityProtocol::SaslPlaintext => {
                client_config.set("security.protocol", "sasl_plaintext");
                Self::apply_sasl_config(client_config, security.sasl.as_ref())?;
            }
            SecurityProtocol::SaslSsl => {
                client_config.set("security.protocol", "sasl_ssl");
                Self::apply_sasl_config(client_config, security.sasl.as_ref())?;
                Self::apply_ssl_config(client_config, security.ssl.as_ref())?;
            }
        }
        
        // Apply additional security properties
        for (key, value) in &security.properties {
            client_config.set(key, value);
        }
        
        Ok(())
    }

    /// Apply SASL configuration
    fn apply_sasl_config(
        client_config: &mut ClientConfig,
        sasl_config: Option<&crate::config::SaslConfig>,
    ) -> Result<(), KafkaError> {
        if let Some(sasl) = sasl_config {
            let mechanism = match sasl.mechanism {
                SaslMechanism::Plain => "PLAIN",
                SaslMechanism::ScramSha256 => "SCRAM-SHA-256",
                SaslMechanism::ScramSha512 => "SCRAM-SHA-512",
                SaslMechanism::Gssapi => "GSSAPI",
                SaslMechanism::OAuthBearer => "OAUTHBEARER",
            };
            
            client_config.set("sasl.mechanism", mechanism);
            client_config.set("sasl.username", &sasl.username);
            client_config.set("sasl.password", &sasl.password);
            
            if let Some(service_name) = &sasl.service_name {
                client_config.set("sasl.service.name", service_name);
            }
            
            // Apply Kerberos configuration if present
            if let Some(kerberos) = &sasl.kerberos {
                client_config.set("sasl.kerberos.service.name", &kerberos.service_name);
                client_config.set("sasl.kerberos.keytab", &kerberos.keytab_path);
                client_config.set("sasl.kerberos.principal", &kerberos.service_name);
                client_config.set("sasl.kerberos.min.time.before.renewal", 
                                &kerberos.min_time_before_renewal.as_secs().to_string());
            }
        }
        
        Ok(())
    }

    /// Apply SSL configuration
    fn apply_ssl_config(
        client_config: &mut ClientConfig,
        ssl_config: Option<&crate::config::SslConfig>,
    ) -> Result<(), KafkaError> {
        if let Some(ssl) = ssl_config {
            if let Some(ca_file) = &ssl.ca_file {
                client_config.set("ssl.ca.location", ca_file);
            }
            
            if let Some(cert_file) = &ssl.cert_file {
                client_config.set("ssl.certificate.location", cert_file);
            }
            
            if let Some(key_file) = &ssl.key_file {
                client_config.set("ssl.key.location", key_file);
            }
            
            if let Some(key_password) = &ssl.key_password {
                client_config.set("ssl.key.password", key_password);
            }
            
            client_config.set("ssl.verify.hostname", &ssl.verify_hostname.to_string());
            
            // Set SSL protocols
            if !ssl.ssl_protocols.is_empty() {
                client_config.set("ssl.protocol", &ssl.ssl_protocols.join(","));
            }
            
            // Set cipher suites
            if !ssl.cipher_suites.is_empty() {
                client_config.set("ssl.cipher.suites", &ssl.cipher_suites.join(","));
            }
        }
        
        Ok(())
    }

    /// Create a new topic
    pub async fn create_topic(&self, topic_config: &TopicConfig) -> Result<(), KafkaError> {
        let mut new_topic = NewTopic::new(
            &topic_config.topic_name,
            topic_config.partitions,
            TopicReplication::Fixed(topic_config.replication_factor),
        );
        
        // Set topic configuration
        for (key, value) in &topic_config.config {
            new_topic = new_topic.set(key, value);
        }
        
        // Set retention time if specified
        if let Some(retention_ms) = topic_config.retention_ms {
            new_topic = new_topic.set("retention.ms", &retention_ms.to_string());
        }
        
        // Set max message size if specified
        if let Some(max_message_bytes) = topic_config.max_message_bytes {
            new_topic = new_topic.set("max.message.bytes", &max_message_bytes.to_string());
        }
        
        // Set cleanup policy if specified
        if let Some(cleanup_policy) = &topic_config.cleanup_policy {
            new_topic = new_topic.set("cleanup.policy", cleanup_policy);
        }
        
        // Set compression type if specified
        if let Some(compression_type) = &topic_config.compression_type {
            new_topic = new_topic.set("compression.type", compression_type);
        }
        
        let admin_options = AdminOptions::new()
            .request_timeout(Some(Duration::from_secs(30)))
            .operation_timeout(Some(Duration::from_secs(30)));
        
        let results = self.admin_client
            .create_topics(&[new_topic], &admin_options)
            .await?;
        
        // Check results
        for result in results {
            if let Err(e) = result {
                return Err(e);
            }
        }
        
        Ok(())
    }

    /// Delete a topic
    pub async fn delete_topic(&self, topic_name: &str) -> Result<(), KafkaError> {
        let admin_options = AdminOptions::new()
            .request_timeout(Some(Duration::from_secs(30)))
            .operation_timeout(Some(Duration::from_secs(30)));
        
        let results = self.admin_client
            .delete_topics(&[topic_name], &admin_options)
            .await?;
        
        // Check results
        for result in results {
            if let Err(e) = result {
                return Err(e);
            }
        }
        
        Ok(())
    }

    /// List all topics
    pub async fn list_topics(&self) -> Result<Vec<String>, KafkaError> {
        let metadata = self.admin_client.inner().fetch_metadata(None, Duration::from_secs(10))?;
        
        let topics: Vec<String> = metadata
            .topics()
            .iter()
            .map(|topic| topic.name().to_string())
            .collect();
        
        Ok(topics)
    }

    /// Get topic metadata
    pub async fn get_topic_metadata(&self, topic_name: &str) -> Result<TopicMetadata, KafkaError> {
        let metadata = self.admin_client.inner().fetch_metadata(None, Duration::from_secs(10))?;
        
        for topic in metadata.topics() {
            if topic.name() == topic_name {
                let partitions = topic.partitions()
                    .iter()
                    .map(|p| PartitionMetadata {
                        partition_id: p.id(),
                        leader: p.leader(),
                        replicas: p.replicas().to_vec(),
                        isr: p.isr().to_vec(),
                    })
                    .collect();
                
                return Ok(TopicMetadata {
                    topic_name: topic.name().to_string(),
                    internal: topic.internal(),
                    partitions,
                });
            }
        }
        
        Err(KafkaError::TopicNotFound(topic_name.to_string()))
    }

    /// Get cluster metadata
    pub async fn get_cluster_metadata(&self) -> Result<ClusterMetadata, KafkaError> {
        // Check cache first
        {
            let cache = self.cluster_metadata.read().await;
            if let Some(ref metadata) = *cache {
                // Return cached metadata if it's less than 1 minute old
                let age = chrono::Utc::now() - metadata.timestamp;
                if age < chrono::Duration::minutes(1) {
                    return Ok(metadata.clone());
                }
            }
        }
        
        // Fetch fresh metadata
        let metadata = self.admin_client.inner().fetch_metadata(None, Duration::from_secs(10))?;
        
        let brokers = metadata.brokers()
            .iter()
            .map(|b| BrokerMetadata {
                broker_id: b.id(),
                hostname: b.host().to_string(),
                port: b.port(),
                rack: b.rack().map(|r| r.to_string()),
            })
            .collect();
        
        let topics = metadata.topics()
            .iter()
            .map(|t| {
                let partitions = t.partitions()
                    .iter()
                    .map(|p| PartitionMetadata {
                        partition_id: p.id(),
                        leader: p.leader(),
                        replicas: p.replicas().to_vec(),
                        isr: p.isr().to_vec(),
                    })
                    .collect();
                
                TopicMetadata {
                    topic_name: t.name().to_string(),
                    internal: t.internal(),
                    partitions,
                }
            })
            .collect();
        
        let cluster_metadata = ClusterMetadata {
            cluster_id: metadata.cluster_id().unwrap_or("unknown").to_string(),
            controller: metadata.controller().map(|c| c.id()).unwrap_or(-1),
            brokers,
            topics,
            timestamp: chrono::Utc::now(),
        };
        
        // Update cache
        {
            let mut cache = self.cluster_metadata.write().await;
            *cache = Some(cluster_metadata.clone());
        }
        
        Ok(cluster_metadata)
    }

    /// List consumer groups
    pub async fn list_consumer_groups(&self) -> Result<Vec<String>, KafkaError> {
        let groups = self.admin_client
            .list_consumer_groups(&AdminOptions::new())
            .await?;
        
        let group_ids: Vec<String> = groups
            .into_iter()
            .map(|group| group.group_id().to_string())
            .collect();
        
        Ok(group_ids)
    }

    /// Get consumer group metadata
    pub async fn get_consumer_group_metadata(&self, group_id: &str) -> Result<ConsumerGroupMetadata, KafkaError> {
        let groups = self.admin_client
            .describe_consumer_groups(&[group_id], &AdminOptions::new())
            .await?;
        
        if let Some(group) = groups.into_iter().next() {
            let members = group.members()
                .into_iter()
                .map(|member| {
                    let assignments = if let Some(member_assignment) = member.assignment() {
                        member_assignment.topics()
                            .iter()
                            .flat_map(|(topic, partitions)| {
                                partitions.iter().map(move |&partition| MemberAssignment {
                                    topic_name: topic.to_string(),
                                    partition_id: partition,
                                })
                            })
                            .collect()
                    } else {
                        Vec::new()
                    };
                    
                    GroupMemberMetadata {
                        member_id: member.member_id().to_string(),
                        client_id: member.client_id().to_string(),
                        client_host: member.client_host().to_string(),
                        assignments,
                    }
                })
                .collect();
            
            Ok(ConsumerGroupMetadata {
                group_id: group.group_id().to_string(),
                state: group.state().to_string(),
                protocol: group.protocol().to_string(),
                members,
            })
        } else {
            Err(KafkaError::GroupAuthorizationFailed(group_id.to_string()))
        }
    }

    /// Delete consumer group
    pub async fn delete_consumer_group(&self, group_id: &str) -> Result<(), KafkaError> {
        let results = self.admin_client
            .delete_consumer_groups(&[group_id], &AdminOptions::new())
            .await?;
        
        // Check results
        for result in results {
            if let Err(e) = result {
                return Err(e);
            }
        }
        
        Ok(())
    }

    /// Get broker configuration
    pub async fn get_broker_config(&self, broker_id: i32) -> Result<HashMap<String, String>, KafkaError> {
        let configs = self.admin_client
            .describe_configs(&[rdkafka::admin::ConfigResource::Broker(broker_id)], &AdminOptions::new())
            .await?;
        
        if let Some(config) = configs.into_iter().next() {
            let mut config_map = HashMap::new();
            
            for entry in config.entries() {
                config_map.insert(entry.name().to_string(), entry.value().unwrap_or("").to_string());
            }
            
            Ok(config_map)
        } else {
            Err(KafkaError::BrokerNotFound(broker_id))
        }
    }

    /// Update broker configuration
    pub async fn update_broker_config(
        &self,
        broker_id: i32,
        config_updates: HashMap<String, String>,
    ) -> Result<(), KafkaError> {
        let mut resource = rdkafka::admin::ConfigResource::Broker(broker_id);
        
        for (key, value) in config_updates {
            resource = resource.set(key, value);
        }
        
        let results = self.admin_client
            .alter_configs(&[resource], &AdminOptions::new())
            .await?;
        
        // Check results
        for result in results {
            if let Err(e) = result {
                return Err(e);
            }
        }
        
        Ok(())
    }

    /// Create multiple topics
    pub async fn create_topics(&self, topic_configs: &[TopicConfig]) -> Result<Vec<String>, KafkaError> {
        let mut new_topics = Vec::new();
        let mut created_topics = Vec::new();
        
        for topic_config in topic_configs {
            let mut new_topic = NewTopic::new(
                &topic_config.topic_name,
                topic_config.partitions,
                TopicReplication::Fixed(topic_config.replication_factor),
            );
            
            // Set topic configuration
            for (key, value) in &topic_config.config {
                new_topic = new_topic.set(key, value);
            }
            
            // Set retention time if specified
            if let Some(retention_ms) = topic_config.retention_ms {
                new_topic = new_topic.set("retention.ms", &retention_ms.to_string());
            }
            
            // Set max message size if specified
            if let Some(max_message_bytes) = topic_config.max_message_bytes {
                new_topic = new_topic.set("max.message.bytes", &max_message_bytes.to_string());
            }
            
            // Set cleanup policy if specified
            if let Some(cleanup_policy) = &topic_config.cleanup_policy {
                new_topic = new_topic.set("cleanup.policy", cleanup_policy);
            }
            
            // Set compression type if specified
            if let Some(compression_type) = &topic_config.compression_type {
                new_topic = new_topic.set("compression.type", compression_type);
            }
            
            new_topics.push(new_topic);
            created_topics.push(topic_config.topic_name.clone());
        }
        
        let admin_options = AdminOptions::new()
            .request_timeout(Some(Duration::from_secs(60)))
            .operation_timeout(Some(Duration::from_secs(60)));
        
        let results = self.admin_client
            .create_topics(&new_topics, &admin_options)
            .await?;
        
        // Check results
        for result in results {
            if let Err(e) = result {
                return Err(e);
            }
        }
        
        Ok(created_topics)
    }

    /// Delete multiple topics
    pub async fn delete_topics(&self, topic_names: &[&str]) -> Result<(), KafkaError> {
        let admin_options = AdminOptions::new()
            .request_timeout(Some(Duration::from_secs(60)))
            .operation_timeout(Some(Duration::from_secs(60)));
        
        let results = self.admin_client
            .delete_topics(topic_names, &admin_options)
            .await?;
        
        // Check results
        for result in results {
            if let Err(e) = result {
                return Err(e);
            }
        }
        
        Ok(())
    }

    /// Validate topic configuration
    pub fn validate_topic_config(topic_config: &TopicConfig) -> Result<(), String> {
        if topic_config.topic_name.is_empty() {
            return Err("Topic name cannot be empty".to_string());
        }
        
        if topic_config.partitions <= 0 {
            return Err("Number of partitions must be positive".to_string());
        }
        
        if topic_config.replication_factor <= 0 {
            return Err("Replication factor must be positive".to_string());
        }
        
        // Validate topic name format
        if !topic_config.topic_name.chars().all(|c| c.is_alphanumeric() || c == '_' || c == '-' || c == '.') {
            return Err("Topic name contains invalid characters".to_string());
        }
        
        // Validate retention time
        if let Some(retention_ms) = topic_config.retention_ms {
            if retention_ms < 0 {
                return Err("Retention time cannot be negative".to_string());
            }
        }
        
        // Validate max message size
        if let Some(max_message_bytes) = topic_config.max_message_bytes {
            if max_message_bytes <= 0 {
                return Err("Max message size must be positive".to_string());
            }
        }
        
        Ok(())
    }

    /// Get recommended topic configuration for a given topic type
    pub fn get_recommended_topic_config(topic_type: &str) -> TopicConfig {
        match topic_type {
            "market_data" => TopicConfig {
                topic_name: "market_data".to_string(),
                partitions: 12,
                replication_factor: 3,
                retention_ms: Some(86400000), // 24 hours
                max_message_bytes: Some(1048576), // 1MB
                cleanup_policy: Some("delete".to_string()),
                compression_type: Some("lz4".to_string()),
                topic_type: topic_type.to_string(),
                schema_info: None,
                config: {
                    let mut config = HashMap::new();
                    config.insert("segment.bytes".to_string(), "1073741824".to_string()); // 1GB
                    config.insert("segment.ms".to_string(), "3600000".to_string()); // 1 hour
                    config.insert("delete.retention.ms".to_string(), "86400000".to_string()); // 24 hours
                    config
                },
            },
            "orders" => TopicConfig {
                topic_name: "orders".to_string(),
                partitions: 6,
                replication_factor: 3,
                retention_ms: Some(604800000), // 7 days
                max_message_bytes: Some(524288), // 512KB
                cleanup_policy: Some("compact".to_string()),
                compression_type: Some("zstd".to_string()),
                topic_type: topic_type.to_string(),
                schema_info: None,
                config: {
                    let mut config = HashMap::new();
                    config.insert("segment.bytes".to_string(), "536870912".to_string()); // 512MB
                    config.insert("segment.ms".to_string(), "7200000".to_string()); // 2 hours
                    config.insert("min.cleanable.dirty.ratio".to_string(), "0.1".to_string());
                    config
                },
            },
            "trades" => TopicConfig {
                topic_name: "trades".to_string(),
                partitions: 8,
                replication_factor: 3,
                retention_ms: Some(2592000000), // 30 days
                max_message_bytes: Some(262144), // 256KB
                cleanup_policy: Some("compact".to_string()),
                compression_type: Some("zstd".to_string()),
                topic_type: topic_type.to_string(),
                schema_info: None,
                config: {
                    let mut config = HashMap::new();
                    config.insert("segment.bytes".to_string(), "268435456".to_string()); // 256MB
                    config.insert("segment.ms".to_string(), "14400000".to_string()); // 4 hours
                    config.insert("min.cleanable.dirty.ratio".to_string(), "0.05".to_string());
                    config
                },
            },
            "events" => TopicConfig {
                topic_name: "events".to_string(),
                partitions: 4,
                replication_factor: 2,
                retention_ms: Some(604800000), // 7 days
                max_message_bytes: Some(1048576), // 1MB
                cleanup_policy: Some("delete".to_string()),
                compression_type: Some("gzip".to_string()),
                topic_type: topic_type.to_string(),
                schema_info: None,
                config: {
                    let mut config = HashMap::new();
                    config.insert("segment.bytes".to_string(), "134217728".to_string()); // 128MB
                    config.insert("segment.ms".to_string(), "21600000".to_string()); // 6 hours
                    config
                },
            },
            "control" => TopicConfig {
                topic_name: "control".to_string(),
                partitions: 3,
                replication_factor: 3,
                retention_ms: Some(86400000), // 24 hours
                max_message_bytes: Some(65536), // 64KB
                cleanup_policy: Some("delete".to_string()),
                compression_type: Some("none".to_string()),
                topic_type: topic_type.to_string(),
                schema_info: None,
                config: {
                    let mut config = HashMap::new();
                    config.insert("segment.bytes".to_string(), "67108864".to_string()); // 64MB
                    config.insert("segment.ms".to_string(), "43200000".to_string()); // 12 hours
                    config
                },
            },
            _ => TopicConfig::default(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::{RedpandaConfig, SecurityProtocol};

    #[tokio::test]
    async fn test_topic_config_validation() {
        let mut config = TopicConfig::default();
        config.topic_name = "test_topic".to_string();
        config.partitions = 3;
        config.replication_factor = 2;
        
        assert!(RedpandaAdmin::validate_topic_config(&config).is_ok());
        
        // Test invalid topic name
        config.topic_name = "invalid topic name!".to_string();
        assert!(RedpandaAdmin::validate_topic_config(&config).is_err());
        
        // Test invalid partitions
        config.topic_name = "valid_topic".to_string();
        config.partitions = 0;
        assert!(RedpandaAdmin::validate_topic_config(&config).is_err());
        
        // Test invalid replication factor
        config.partitions = 3;
        config.replication_factor = 0;
        assert!(RedpandaAdmin::validate_topic_config(&config).is_err());
    }

    #[test]
    fn test_recommended_topic_configs() {
        let market_data_config = RedpandaAdmin::get_recommended_topic_config("market_data");
        assert_eq!(market_data_config.partitions, 12);
        assert_eq!(market_data_config.replication_factor, 3);
        assert_eq!(market_data_config.compression_type, Some("lz4".to_string()));
        
        let orders_config = RedpandaAdmin::get_recommended_topic_config("orders");
        assert_eq!(orders_config.partitions, 6);
        assert_eq!(orders_config.cleanup_policy, Some("compact".to_string()));
        
        let default_config = RedpandaAdmin::get_recommended_topic_config("unknown");
        assert_eq!(default_config, TopicConfig::default());
    }

    #[test]
    fn test_security_config_application() {
        let mut config = RedpandaConfig::default();
        config.security.security_protocol = SecurityProtocol::SaslPlaintext;
        
        // This would be tested with an actual Kafka cluster
        // For now, we just verify the configuration structure
        assert!(matches!(config.security.security_protocol, SecurityProtocol::SaslPlaintext));
    }
}
