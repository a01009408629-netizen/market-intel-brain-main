//! Kafka Configuration Module
use serde::{Deserialize, Serialize};
use std::env;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KafkaConfig {
    pub brokers: String,
    pub topic_prefix: String,
    pub consumer_group: String,
    pub security_protocol: String,
    pub sasl_mechanism: Option<String>,
    pub sasl_username: Option<String>,
    pub sasl_password: Option<String>,
}

impl KafkaConfig {
    pub fn from_env() -> Result<Self, String> {
        Ok(Self {
            brokers: env::var("KAFKA_BROKERS").unwrap_or_else(|_| "localhost:9092".into()),
            topic_prefix: env::var("KAFKA_TOPIC_PREFIX").unwrap_or_else(|_| "market-intel".into()),
            consumer_group: env::var("KAFKA_CONSUMER_GROUP").unwrap_or_else(|_| "core-engine".into()),
            security_protocol: env::var("KAFKA_SECURITY_PROTOCOL").unwrap_or_else(|_| "PLAINTEXT".into()),
            sasl_mechanism: env::var("KAFKA_SASL_MECHANISM").ok(),
            sasl_username: env::var("KAFKA_SASL_USERNAME").ok(),
            sasl_password: env::var("KAFKA_SASL_PASSWORD").ok(),
        })
    }
}
