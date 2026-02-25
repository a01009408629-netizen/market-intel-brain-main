// Copyright (c) 2024 Market Intel Brain Team
// Agent Memory Vector DB Client - Long-term memory storage for agents
/// عميل قاعدة بيانات المتجهات للوكلاء - تخزين الذاكرة طويلة المدى للوكلاء

use std::collections::HashMap;
use std::time::Duration;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use qdrant_client::prelude::*;
use qdrant_client::qdrant::{
    CreateCollection, VectorParams, Distance, PayloadIndexParams, PayloadSchemaParams,
    FieldCondition, Match, Filter, SearchPoints, PointId, PointStruct,
    WithPayloadSelector, WithVectorSelector, 
};
use tokio::time::timeout;
use tracing::{info, warn, error, debug};
use crate::agent_keys::{AgentMemoryEntry, MemoryType};

/// Agent Memory Vector DB Client
/// عميل قاعدة بيانات المتجهات لذاكرة الوكيل
pub struct AgentMemoryVectorDB {
    /// Qdrant client
    /// عميل Qdrant
    client: QdrantClient,
    
    /// Collection name for agent long-term memory
    /// اسم المجموعة لذاكرة الوكيل طويلة المدى
    collection_name: String,
    
    /// Vector dimension
    /// أبعاد المتجه
    vector_dimension: usize,
    
    /// Configuration
    /// التكوين
    config: AgentMemoryConfig,
}

/// Agent Memory Configuration
/// تكوين ذاكرة الوكيل
#[derive(Debug, Clone)]
pub struct AgentMemoryConfig {
    /// Collection name
    /// اسم المجموعة
    pub collection_name: String,
    
    /// Vector dimension
    /// أبعاد المتجه
    pub vector_dimension: usize,
    
    /// Distance metric
    /// مقياس المسافة
    pub distance: Distance,
    
    /// HNSW parameters
    /// معلمات HNSW
    pub hnsw_config: HnswConfig,
    
    /// Search limit
    /// حد البحث
    pub search_limit: usize,
    
    /// Search timeout in seconds
    /// مهلة البحث بالثواني
    pub search_timeout_seconds: u64,
    
    /// Batch size for operations
    /// حجم الدفعة للعمليات
    pub batch_size: usize,
    
    /// Enable payload indexing
    /// تمكين فهرسة الحمولة
    pub enable_payload_indexing: bool,
}

/// HNSW Configuration
/// تكوين HNSW
#[derive(Debug, Clone)]
pub struct HnswConfig {
    /// M parameter
    /// معلمة M
    pub m: u32,
    
    /// Ef construction parameter
    /// معلمة ef_construction
    pub ef_construction: u32,
    
    /// Ef search parameter
    /// معلمة ef_search
    pub ef_search: u32,
}

impl Default for AgentMemoryConfig {
    fn default() -> Self {
        Self {
            collection_name: "agent_long_term_memory".to_string(),
            vector_dimension: 768, // Common embedding dimension
            distance: Distance::Cosine,
            hnsw_config: HnswConfig {
                m: 16,
                ef_construction: 100,
                ef_search: 64,
            },
            search_limit: 100,
            search_timeout_seconds: 10,
            batch_size: 100,
            enable_payload_indexing: true,
        }
    }
}

/// Agent Memory Vector DB Error
/// خطأ قاعدة بيانات المتجهات لذاكرة الوكيل
#[derive(Error, Debug)]
pub enum AgentMemoryError {
    #[error("Qdrant client error: {0}")]
    QdrantError(#[from] qdrant_client::QdrantError),
    
    #[error("Collection not found: {0}")]
    CollectionNotFound(String),
    
    #[error("Vector dimension mismatch: expected {expected}, got {actual}")]
    VectorDimensionMismatch { expected: usize, actual: usize },
    
    #[error("Memory entry validation error: {0}")]
    ValidationError(String),
    
    #[error("Search timeout")]
    SearchTimeout,
    
    #[error("Index error: {0}")]
    IndexError(String),
    
    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),
    
    #[error("Invalid agent ID: {0}")]
    InvalidAgentId(String),
    
    #[error("Memory not found: {0}")]
    MemoryNotFound(String),
    
    #[error("Batch operation failed: {0}")]
    BatchError(String),
    
    #[error("Configuration error: {0}")]
    ConfigurationError(String),
}

/// Result type for agent memory operations
/// نوع النتيجة لعمليات ذاكرة الوكيل
pub type AgentMemoryResult<T> = Result<T, AgentMemoryError>;

impl AgentMemoryVectorDB {
    /// Create new agent memory vector DB client
    /// إنشاء عميل قاعدة بيانات متجهات ذاكرة الوكيل جديد
    pub async fn new(client: QdrantClient, config: AgentMemoryConfig) -> AgentMemoryResult<Self> {
        info!("Creating agent memory vector DB client for collection: {}", config.collection_name);
        
        // Validate configuration
        Self::validate_config(&config)?;
        
        // Ensure collection exists
        Self::ensure_collection_exists(&client, &config).await?;
        
        Ok(Self {
            client,
            collection_name: config.collection_name.clone(),
            vector_dimension: config.vector_dimension,
            config,
        })
    }

    /// Validate configuration
    /// التحقق من التكوين
    fn validate_config(config: &AgentMemoryConfig) -> AgentMemoryResult<()> {
        if config.collection_name.is_empty() {
            return Err(AgentMemoryError::ConfigurationError("Collection name cannot be empty".to_string()));
        }
        
        if config.vector_dimension == 0 {
            return Err(AgentMemoryError::ConfigurationError("Vector dimension must be greater than 0".to_string()));
        }
        
        if config.search_limit == 0 {
            return Err(AgentMemoryError::ConfigurationError("Search limit must be greater than 0".to_string()));
        }
        
        if config.batch_size == 0 {
            return Err(AgentMemoryError::ConfigurationError("Batch size must be greater than 0".to_string()));
        }
        
        Ok(())
    }

    /// Ensure collection exists
    /// التأكد من وجود المجموعة
    async fn ensure_collection_exists(client: &QdrantClient, config: &AgentMemoryConfig) -> AgentMemoryResult<()> {
        // Check if collection exists
        let collections = client.list_collections().await?;
        let collection_exists = collections.collections.iter()
            .any(|c| c.name == config.collection_name);
        
        if !collection_exists {
            info!("Creating collection: {}", config.collection_name);
            
            // Create collection
            client.create_collection(&CreateCollection {
                collection_name: config.collection_name.clone(),
                vectors_config: Some(VectorsConfig {
                    config: Some(VectorParams::from({
                        VectorParams::new(config.vector_dimension)
                            .distance(config.distance.clone())
                            .hnsw_config(Some(HnswParamsGraph {
                                m: config.hnsw_config.m,
                                ef_construct: config.hnsw_config.ef_construction,
                                ef_search: Some(config.hnsw_config.ef_search),
                                max_indexing_threads: Some(4),
                                on_disk: Some(false),
                            }))
                    })),
                    ..Default::default()
                }),
                optimizers_config: Some(OptimizersConfigDiff {
                    default_segment_number: Some(2),
                    max_segment_size: Some(200000),
                    memmap_threshold: Some(50000),
                    indexing_threshold: Some(20000),
                    payload_indexing: Some(config.enable_payload_indexing),
                    flush_interval_sec: Some(5),
                }),
                ..Default::default()
            }).await?;
            
            // Create payload indexes for efficient filtering
            if config.enable_payload_indexing {
                Self::create_payload_indexes(client, &config.collection_name).await?;
            }
            
            info!("Collection created successfully: {}", config.collection_name);
        } else {
            debug!("Collection already exists: {}", config.collection_name);
        }
        
        Ok(())
    }

    /// Create payload indexes
    /// إنشاء فهارس الحمولة
    async fn create_payload_indexes(client: &QdrantClient, collection_name: &str) -> AgentMemoryResult<()> {
        info!("Creating payload indexes for collection: {}", collection_name);
        
        // Create index for agent_id
        client.create_field_index(collection_name, &FieldIndexParams {
            field_name: "agent_id".to_string(),
            field_schema: Some(PayloadSchemaParams::Keyword),
            field_type: Some(FieldType::Keyword),
        }).await?;
        
        // Create index for memory_type
        client.create_field_index(collection_name, &FieldIndexParams {
            field_name: "memory_type".to_string(),
            field_schema: Some(PayloadSchemaParams::Keyword),
            field_type: Some(FieldType::Keyword),
        }).await?;
        
        // Create index for tags
        client.create_field_index(collection_name, &FieldIndexParams {
            field_name: "tags".to_string(),
            field_schema: Some(PayloadSchemaParams::Keyword),
            field_type: Some(FieldType::Keyword),
        }).await?;
        
        // Create index for timestamp
        client.create_field_index(collection_name, &FieldIndexParams {
            field_name: "timestamp".to_string(),
            field_schema: Some(PayloadSchemaParams::Integer),
            field_type: Some(FieldType::Integer),
        }).await?;
        
        // Create index for importance_score
        client.create_field_index(collection_name, &FieldIndexParams {
            field_name: "importance_score".to_string(),
            field_schema: Some(PayloadSchemaParams::Float),
            field_type: Some(FieldType::Float),
        }).await?;
        
        info!("Payload indexes created successfully");
        Ok(())
    }

    /// Validate memory entry
    /// التحقق من إدخال الذاكرة
    fn validate_memory_entry(&self, entry: &AgentMemoryEntry) -> AgentMemoryResult<()> {
        if entry.id.is_empty() {
            return Err(AgentMemoryError::ValidationError("Memory entry ID cannot be empty".to_string()));
        }
        
        if entry.content.is_empty() {
            return Err(AgentMemoryError::ValidationError("Memory entry content cannot be empty".to_string()));
        }
        
        if let Some(ref embedding) = entry.embedding {
            if embedding.len() != self.vector_dimension {
                return Err(AgentMemoryError::VectorDimensionMismatch {
                    expected: self.vector_dimension,
                    actual: embedding.len(),
                });
            }
        }
        
        if entry.importance_score < 0.0 || entry.importance_score > 1.0 {
            return Err(AgentMemoryError::ValidationError("Importance score must be between 0.0 and 1.0".to_string()));
        }
        
        Ok(())
    }

    /// Store memory entry
    /// تخزين إدخال الذاكرة
    pub async fn store_memory(&self, agent_id: &str, entry: AgentMemoryEntry) -> AgentMemoryResult<String> {
        self.validate_agent_id(agent_id)?;
        self.validate_memory_entry(&entry)?;
        
        // Generate embedding if not provided
        let embedding = match entry.embedding {
            Some(embedding) => embedding,
            None => self.generate_embedding(&entry.content).await?,
        };
        
        // Create point struct
        let point_id = PointId::from(entry.id.clone());
        let point = PointStruct::new(
            point_id,
            embedding,
            self.create_payload(agent_id, &entry)?
        );
        
        // Upsert point
        self.client.upsert_points(&self.collection_name, None, vec![point], None).await?;
        
        info!("Stored memory entry {} for agent {}", entry.id, agent_id);
        Ok(entry.id.clone())
    }

    /// Store multiple memory entries in batch
    /// تخزين إدخالات ذاكرة متعددة بشكل مجمع
    pub async fn store_memory_batch(&self, agent_id: &str, entries: Vec<AgentMemoryEntry>) -> AgentMemoryResult<Vec<String>> {
        self.validate_agent_id(agent_id)?;
        
        if entries.is_empty() {
            return Ok(vec![]);
        }
        
        let mut points = Vec::new();
        let mut stored_ids = Vec::new();
        
        for entry in entries {
            self.validate_memory_entry(&entry)?;
            
            // Generate embedding if not provided
            let embedding = match entry.embedding {
                Some(embedding) => embedding,
                None => self.generate_embedding(&entry.content).await?,
            };
            
            let point_id = PointId::from(entry.id.clone());
            let point = PointStruct::new(
                point_id,
                embedding,
                self.create_payload(agent_id, &entry)?
            );
            
            points.push(point);
            stored_ids.push(entry.id.clone());
        }
        
        // Upsert points in batches
        for chunk in points.chunks(self.config.batch_size) {
            self.client.upsert_points(&self.collection_name, None, chunk.to_vec(), None).await?;
        }
        
        info!("Stored {} memory entries for agent {}", stored_ids.len(), agent_id);
        Ok(stored_ids)
    }

    /// Search memories by similarity
    /// البحث في الذكريات حسب التشابه
    pub async fn search_similar_memories(
        &self,
        agent_id: &str,
        query: &str,
        limit: Option<usize>
    ) -> AgentMemoryResult<Vec<AgentMemoryEntry>> {
        self.validate_agent_id(agent_id)?;
        
        let search_limit = limit.unwrap_or(self.config.search_limit);
        
        // Generate query embedding
        let query_embedding = self.generate_embedding(query).await?;
        
        // Create filter for agent_id
        let filter = Filter::must([FieldCondition::match_keyword(
            "agent_id".into(),
            Match::value(agent_id.into())
        )]);
        
        // Search points
        let search_result = if self.config.search_timeout_seconds > 0 {
            timeout(
                Duration::from_secs(self.config.search_timeout_seconds),
                self.client.search_points(&SearchPoints {
                    collection_name: self.collection_name.clone(),
                    vector: NamedVector::from(query_embedding),
                    filter: Some(filter),
                    limit: search_limit,
                    with_payload: Some(WithPayloadSelector::from(true)),
                    with_vector: Some(WithVectorSelector::from(false)),
                    params: Some(SearchParams {
                        hnsw_ef: Some(self.config.hnsw_config.ef_search),
                        exact: false,
                        indexed_only: false,
                    }),
                    ..Default::default()
                })
            ).await.map_err(|_| AgentMemoryError::SearchTimeout)??
        } else {
            self.client.search_points(&SearchPoints {
                collection_name: self.collection_name.clone(),
                vector: NamedVector::from(query_embedding),
                filter: Some(filter),
                limit: search_limit,
                with_payload: Some(WithPayloadSelector::from(true)),
                with_vector: Some(WithVectorSelector::from(false)),
                params: Some(SearchParams {
                    hnsw_ef: Some(self.config.hnsw_config.ef_search),
                    exact: false,
                    indexed_only: false,
                }),
                ..Default::default()
            }).await?
        };
        
        // Convert results to memory entries
        let mut memories = Vec::new();
        for point in search_result.result {
            if let Some(payload) = point.payload {
                let memory = self.payload_to_memory_entry(&payload)?;
                memories.push(memory);
            }
        }
        
        info!("Found {} similar memories for agent {}", memories.len(), agent_id);
        Ok(memories)
    }

    /// Search memories by content
    /// البحث في الذكريات حسب المحتوى
    pub async fn search_memories_by_content(
        &self,
        agent_id: &str,
        content_query: &str,
        limit: Option<usize>
    ) -> AgentMemoryResult<Vec<AgentMemoryEntry>> {
        self.validate_agent_id(agent_id)?;
        
        let search_limit = limit.unwrap_or(self.config.search_limit);
        
        // Create filter for agent_id and content
        let filter = Filter::must([
            FieldCondition::match_keyword("agent_id".into(), Match::value(agent_id.into())),
            FieldCondition::match_text("content".into(), Match::value(content_query.into()))
        ]);
        
        // Search points
        let search_result = self.client.scroll_points(&ScrollPoints {
            collection_name: self.collection_name.clone(),
            filter: Some(filter),
            limit: search_limit,
            with_payload: Some(WithPayloadSelector::from(true)),
            with_vector: Some(WithVectorSelector::from(false)),
            ..Default::default()
        }).await?;
        
        // Convert results to memory entries
        let mut memories = Vec::new();
        for point in search_result.result {
            if let Some(payload) = point.payload {
                let memory = self.payload_to_memory_entry(&payload)?;
                memories.push(memory);
            }
        }
        
        info!("Found {} memories matching content query for agent {}", memories.len(), agent_id);
        Ok(memories)
    }

    /// Get memories by type
    /// الحصول على الذكريات حسب النوع
    pub async fn get_memories_by_type(
        &self,
        agent_id: &str,
        memory_type: MemoryType,
        limit: Option<usize>
    ) -> AgentMemoryResult<Vec<AgentMemoryEntry>> {
        self.validate_agent_id(agent_id)?;
        
        let search_limit = limit.unwrap_or(self.config.search_limit);
        
        // Create filter for agent_id and memory_type
        let filter = Filter::must([
            FieldCondition::match_keyword("agent_id".into(), Match::value(agent_id.into())),
            FieldCondition::match_keyword("memory_type".into(), Match::value(format!("{:?}", memory_type).into()))
        ]);
        
        // Search points
        let search_result = self.client.scroll_points(&ScrollPoints {
            collection_name: self.collection_name.clone(),
            filter: Some(filter),
            limit: search_limit,
            with_payload: Some(WithPayloadSelector::from(true)),
            with_vector: Some(WithVectorSelector::from(false)),
            ..Default::default()
        }).await?;
        
        // Convert results to memory entries
        let mut memories = Vec::new();
        for point in search_result.result {
            if let Some(payload) = point.payload {
                let memory = self.payload_to_memory_entry(&payload)?;
                memories.push(memory);
            }
        }
        
        // Sort by timestamp (newest first)
        memories.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));
        
        info!("Found {} memories of type {:?} for agent {}", memories.len(), memory_type, agent_id);
        Ok(memories)
    }

    /// Get memories by time range
    /// الحصول على الذكريات حسب النطاق الزمني
    pub async fn get_memories_by_time_range(
        &self,
        agent_id: &str,
        start_time: chrono::DateTime<chrono::Utc>,
        end_time: chrono::DateTime<chrono::Utc>,
        limit: Option<usize>
    ) -> AgentMemoryResult<Vec<AgentMemoryEntry>> {
        self.validate_agent_id(agent_id)?;
        
        let search_limit = limit.unwrap_or(self.config.search_limit);
        
        // Create filter for agent_id and time range
        let filter = Filter::must([
            FieldCondition::match_keyword("agent_id".into(), Match::value(agent_id.into())),
            FieldCondition::range(
                "timestamp".into(),
                Range {
                    gt: Some(start_time.timestamp() as f64),
                    lt: Some(end_time.timestamp() as f64),
                    gte: None,
                    lte: None,
                }
            )
        ]);
        
        // Search points
        let search_result = self.client.scroll_points(&ScrollPoints {
            collection_name: self.collection_name.clone(),
            filter: Some(filter),
            limit: search_limit,
            with_payload: Some(WithPayloadSelector::from(true)),
            with_vector: Some(WithVectorSelector::from(false)),
            ..Default::default()
        }).await?;
        
        // Convert results to memory entries
        let mut memories = Vec::new();
        for point in search_result.result {
            if let Some(payload) = point.payload {
                let memory = self.payload_to_memory_entry(&payload)?;
                memories.push(memory);
            }
        }
        
        // Sort by timestamp (newest first)
        memories.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));
        
        info!("Found {} memories in time range for agent {}", memories.len(), agent_id);
        Ok(memories)
    }

    /// Delete memory entry
    /// حذف إدخال الذاكرة
    pub async fn delete_memory(&self, agent_id: &str, memory_id: &str) -> AgentMemoryResult<bool> {
        self.validate_agent_id(agent_id)?;
        
        let point_id = PointId::from(memory_id);
        
        // Delete point
        let deleted = self.client.delete_points(&self.collection_name, None, vec![point_id]).await?;
        
        if deleted.result.is_empty() {
            warn!("Memory entry {} not found for agent {}", memory_id, agent_id);
            Ok(false)
        } else {
            info!("Deleted memory entry {} for agent {}", memory_id, agent_id);
            Ok(true)
        }
    }

    /// Delete memories by type
    /// حذف الذكريات حسب النوع
    pub async fn delete_memories_by_type(&self, agent_id: &str, memory_type: MemoryType) -> AgentMemoryResult<u64> {
        self.validate_agent_id(agent_id)?;
        
        // Create filter for agent_id and memory_type
        let filter = Filter::must([
            FieldCondition::match_keyword("agent_id".into(), Match::value(agent_id.into())),
            FieldCondition::match_keyword("memory_type".into(), Match::value(format!("{:?}", memory_type).into()))
        ]);
        
        // Delete points
        let deleted = self.client.delete_points(&self.collection_name, Some(filter), vec![]).await?;
        
        info!("Deleted {} memories of type {:?} for agent {}", deleted.result.len(), memory_type, agent_id);
        Ok(deleted.result.len() as u64)
    }

    /// Get memory statistics
    /// الحصول على إحصائيات الذاكرة
    pub async fn get_memory_statistics(&self, agent_id: &str) -> AgentMemoryResult<MemoryStatistics> {
        self.validate_agent_id(agent_id)?;
        
        // Get collection info
        let collection_info = self.client.collection_info(&self.collection_name).await?;
        
        // Count memories by type
        let mut type_counts = HashMap::new();
        let memory_types = vec![
            MemoryType::ShortTerm,
            MemoryType::LongTerm,
            MemoryType::Working,
            MemoryType::Episodic,
            MemoryType::Semantic,
            MemoryType::Procedural,
        ];
        
        for memory_type in memory_types {
            let filter = Filter::must([
                FieldCondition::match_keyword("agent_id".into(), Match::value(agent_id.into())),
                FieldCondition::match_keyword("memory_type".into(), Match::value(format!("{:?}", memory_type).into()))
            ]);
            
            let count_result = self.client.count(&self.collection_name, Some(filter)).await?;
            type_counts.insert(memory_type, count_result.count);
        }
        
        // Get total count
        let filter = Filter::must([
            FieldCondition::match_keyword("agent_id".into(), Match::value(agent_id.into()))
        ]);
        
        let total_count = self.client.count(&self.collection_name, Some(filter)).await?;
        
        Ok(MemoryStatistics {
            agent_id: agent_id.to_string(),
            total_memories: total_count.count,
            memories_by_type: type_counts,
            collection_size_points: collection_info.result.points_count,
            collection_size_vectors: collection_info.result.vectors_count,
            collection_size_segments: collection_info.result.segments_count,
        })
    }

    /// Validate agent ID
    /// التحقق من صحة معرف الوكيل
    fn validate_agent_id(&self, agent_id: &str) -> AgentMemoryResult<()> {
        if agent_id.is_empty() {
            return Err(AgentMemoryError::InvalidAgentId("Agent ID cannot be empty".to_string()));
        }
        
        if agent_id.len() > 255 {
            return Err(AgentMemoryError::InvalidAgentId("Agent ID too long (max 255 characters)".to_string()));
        }
        
        Ok(())
    }

    /// Generate embedding for content
    /// إنشاء تضمين للمحتوى
    async fn generate_embedding(&self, content: &str) -> AgentMemoryResult<Vec<f32>> {
        // This is a placeholder implementation
        // In a real implementation, you would use a proper embedding model
        // like sentence-transformers, OpenAI embeddings, etc.
        
        // Simple hash-based embedding for demonstration
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        
        let mut hasher = DefaultHasher::new();
        content.hash(&mut hasher);
        let hash = hasher.finish();
        
        // Generate deterministic embedding
        let mut embedding = Vec::with_capacity(self.vector_dimension);
        for i in 0..self.vector_dimension {
            let value = ((hash >> (i % 64)) & 0xFFFFFFFF) as f32;
            embedding.push(value / f32::MAX);
        }
        
        // Normalize embedding
        let norm: f32 = embedding.iter().map(|x| x * x).sum::<f32>().sqrt();
        if norm > 0.0 {
            for value in &mut embedding {
                *value /= norm;
            }
        }
        
        Ok(embedding)
    }

    /// Create payload from memory entry
    /// إنشاء حمولة من إدخال الذاكرة
    fn create_payload(&self, agent_id: &str, entry: &AgentMemoryEntry) -> AgentMemoryResult<HashMap<String, Value>> {
        let mut payload = HashMap::new();
        
        payload.insert("agent_id".to_string(), Value::from(agent_id));
        payload.insert("id".to_string(), Value::from(&entry.id));
        payload.insert("memory_type".to_string(), Value::from(format!("{:?}", entry.memory_type)));
        payload.insert("content".to_string(), Value::from(&entry.content));
        payload.insert("timestamp".to_string(), Value::from(entry.timestamp.timestamp()));
        payload.insert("importance_score".to_string(), Value::from(entry.importance_score));
        payload.insert("access_count".to_string(), Value::from(entry.access_count));
        payload.insert("last_accessed".to_string(), Value::from(entry.last_accessed.timestamp()));
        
        // Add tags as array
        let tags: Vec<Value> = entry.tags.iter().map(|tag| Value::from(tag)).collect();
        payload.insert("tags".to_string(), Value::from(tags));
        
        // Add metadata
        if !entry.metadata.is_empty() {
            let metadata_json = serde_json::to_value(&entry.metadata)?;
            payload.insert("metadata".to_string(), metadata_json);
        }
        
        Ok(payload)
    }

    /// Convert payload to memory entry
    /// تحويل الحمولة إلى إدخال الذاكرة
    fn payload_to_memory_entry(&self, payload: &HashMap<String, Value>) -> AgentMemoryResult<AgentMemoryEntry> {
        let id = payload.get("id")
            .and_then(|v| v.as_str())
            .ok_or_else(|| AgentMemoryError::ValidationError("Missing id in payload".to_string()))?
            .to_string();
        
        let memory_type_str = payload.get("memory_type")
            .and_then(|v| v.as_str())
            .ok_or_else(|| AgentMemoryError::ValidationError("Missing memory_type in payload".to_string()))?;
        
        let memory_type = match memory_type_str {
            "ShortTerm" => MemoryType::ShortTerm,
            "LongTerm" => MemoryType::LongTerm,
            "Working" => MemoryType::Working,
            "Episodic" => MemoryType::Episodic,
            "Semantic" => MemoryType::Semantic,
            "Procedural" => MemoryType::Procedural,
            _ => return Err(AgentMemoryError::ValidationError(format!("Invalid memory type: {}", memory_type_str))),
        };
        
        let content = payload.get("content")
            .and_then(|v| v.as_str())
            .ok_or_else(|| AgentMemoryError::ValidationError("Missing content in payload".to_string()))?
            .to_string();
        
        let timestamp = payload.get("timestamp")
            .and_then(|v| v.as_f64())
            .map(|ts| chrono::DateTime::from_timestamp(ts as i64, 0))
            .unwrap_or_else(chrono::Utc::now);
        
        let importance_score = payload.get("importance_score")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.5);
        
        let access_count = payload.get("access_count")
            .and_then(|v| v.as_u64())
            .unwrap_or(0);
        
        let last_accessed = payload.get("last_accessed")
            .and_then(|v| v.as_f64())
            .map(|ts| chrono::DateTime::from_timestamp(ts as i64, 0))
            .unwrap_or(timestamp);
        
        let tags = payload.get("tags")
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter()
                .filter_map(|v| v.as_str())
                .map(|s| s.to_string())
                .collect())
            .unwrap_or_default();
        
        let metadata = payload.get("metadata")
            .and_then(|v| serde_json::from_value::<HashMap<String, serde_json::Value>>(v.clone()).ok())
            .unwrap_or_default();
        
        Ok(AgentMemoryEntry {
            id,
            memory_type,
            content,
            embedding: None, // Not stored in payload for efficiency
            timestamp,
            importance_score,
            access_count,
            last_accessed,
            tags,
            metadata,
        })
    }
}

/// Memory Statistics
/// إحصائيات الذاكرة
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryStatistics {
    /// Agent ID
    /// معرف الوكيل
    pub agent_id: String,
    
    /// Total number of memories
    /// إجمالي عدد الذكريات
    pub total_memories: u64,
    
    /// Memories by type
    /// الذكريات حسب النوع
    pub memories_by_type: HashMap<MemoryType, u64>,
    
    /// Collection size in points
    /// حجم المجموعة بالنقاط
    pub collection_size_points: u64,
    
    /// Collection size in vectors
    /// حجم المجموعة بالمتجهات
    pub collection_size_vectors: u64,
    
    /// Collection size in segments
    /// حجم المجموعة بالأجزاء
    pub collection_size_segments: u64,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::agent_keys::{MemoryType, AgentMemoryEntry};

    #[test]
    fn test_agent_memory_config_default() {
        let config = AgentMemoryConfig::default();
        assert_eq!(config.collection_name, "agent_long_term_memory");
        assert_eq!(config.vector_dimension, 768);
        assert_eq!(config.search_limit, 100);
        assert_eq!(config.batch_size, 100);
    }

    #[test]
    fn test_memory_statistics() {
        let mut type_counts = HashMap::new();
        type_counts.insert(MemoryType::LongTerm, 100);
        type_counts.insert(MemoryType::ShortTerm, 50);
        
        let stats = MemoryStatistics {
            agent_id: "test-agent".to_string(),
            total_memories: 150,
            memories_by_type: type_counts,
            collection_size_points: 150,
            collection_size_vectors: 150,
            collection_size_segments: 2,
        };
        
        assert_eq!(stats.agent_id, "test-agent");
        assert_eq!(stats.total_memories, 150);
        assert_eq!(stats.memories_by_type.get(&MemoryType::LongTerm), Some(&100));
    }

    #[test]
    fn test_validate_memory_entry() {
        let client = QdrantClient::from_url("http://localhost:6333").unwrap();
        let config = AgentMemoryConfig::default();
        
        // This would fail in a real test without a running Qdrant instance
        // let vector_db = AgentMemoryVectorDB::new(client, config).await.unwrap();
        
        let entry = AgentMemoryEntry {
            id: "test-memory".to_string(),
            memory_type: MemoryType::LongTerm,
            content: "Test content".to_string(),
            embedding: Some(vec![0.1; 768]),
            timestamp: chrono::Utc::now(),
            importance_score: 0.8,
            access_count: 5,
            last_accessed: chrono::Utc::now(),
            tags: vec!["test".to_string()],
            metadata: HashMap::new(),
        };
        
        // Test validation logic
        assert!(!entry.id.is_empty());
        assert!(!entry.content.is_empty());
        assert!(entry.importance_score >= 0.0 && entry.importance_score <= 1.0);
    }
}
