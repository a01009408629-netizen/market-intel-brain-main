//! Core Engine - Central processing engine with LMAX Disruptor architecture
//! 
//! This module provides the main core engine that orchestrates all system components
//! using lock-free ring buffers for ultra-low latency processing.

use std::sync::Arc;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::collections::HashMap;
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};
use tokio::sync::{mpsc, RwLock};
use tracing::{info, warn, error, debug};
use uuid::Uuid;

use crate::disruptor::{
    DisruptorEngine, DisruptorBuilder, EventProcessor, Event, Sequence, ProcessError
};
use crate::types::{CoreMessage, MessageType, ProcessingResult};
use crate::config::CoreEngineConfig;

/// Core Engine main structure
pub struct CoreEngine {
    /// Engine configuration
    config: CoreEngineConfig,
    /// Disruptor engine for message processing
    disruptor: DisruptorEngine<CoreMessage>,
    /// Agent registry
    agents: Arc<RwLock<HashMap<String, CoreAgent>>>,
    /// Running flag
    running: Arc<AtomicBool>,
    /// Engine statistics
    stats: Arc<RwLock<EngineStatistics>>,
    /// Message router
    router: Arc<MessageRouter>,
    /// Health monitor
    health_monitor: Arc<HealthMonitor>,
    /// Performance profiler
    profiler: Arc<PerformanceProfiler>,
}

/// Core agent representation
#[derive(Debug, Clone)]
pub struct CoreAgent {
    /// Agent ID
    pub id: String,
    /// Agent name
    pub name: String,
    /// Agent type
    pub agent_type: AgentType,
    /// Agent status
    pub status: AgentStatus,
    /// Message types handled
    pub handled_types: Vec<MessageType>,
    /// Processing statistics
    pub stats: AgentStats,
    /// Last heartbeat
    pub last_heartbeat: Instant,
    /// Thread affinity (optional)
    pub thread_affinity: Option<usize>,
}

/// Agent types
#[derive(Debug, Clone, PartialEq)]
pub enum AgentType {
    /// Data ingestion agent
    DataIngestion,
    /// Trading engine agent
    TradingEngine,
    /// Risk management agent
    RiskManagement,
    /// Analytics agent
    Analytics,
    /// Storage agent
    Storage,
    /// Network agent
    Network,
    /// Security agent
    Security,
    /// Custom agent
    Custom(String),
}

/// Agent status
#[derive(Debug, Clone, PartialEq)]
pub enum AgentStatus {
    /// Agent is starting
    Starting,
    /// Agent is running
    Running,
    /// Agent is stopping
    Stopping,
    /// Agent is stopped
    Stopped,
    /// Agent has failed
    Failed(String),
}

/// Agent statistics
#[derive(Debug, Clone, Default)]
pub struct AgentStats {
    /// Messages processed
    pub messages_processed: u64,
    /// Messages failed
    pub messages_failed: u64,
    /// Average processing time (microseconds)
    pub avg_processing_time_us: f64,
    /// Last processing time
    pub last_processing_time: Option<Duration>,
    /// Memory usage (bytes)
    pub memory_usage: u64,
    /// CPU usage (percentage)
    pub cpu_usage: f64,
}

/// Engine statistics
#[derive(Debug, Default)]
pub struct EngineStatistics {
    /// Total messages processed
    pub total_messages: u64,
    /// Messages per second
    pub messages_per_second: f64,
    /// Average latency (microseconds)
    pub avg_latency_us: f64,
    /// P99 latency (microseconds)
    pub p99_latency_us: f64,
    /// Engine uptime
    pub uptime: Duration,
    /// Active agents
    pub active_agents: usize,
    /// Failed agents
    pub failed_agents: usize,
    /// Memory usage (bytes)
    pub memory_usage: u64,
    /// CPU usage (percentage)
    pub cpu_usage: f64,
    /// Last update time
    pub last_update: Instant,
}

/// Message router for directing messages to appropriate agents
pub struct MessageRouter {
    /// Routing table
    routes: HashMap<MessageType, Vec<String>>,
    /// Default route
    default_route: Option<String>,
}

impl MessageRouter {
    /// Create new message router
    pub fn new() -> Self {
        Self {
            routes: HashMap::new(),
            default_route: None,
        }
    }
    
    /// Add route for message type
    pub fn add_route(&mut self, message_type: MessageType, agent_id: String) {
        self.routes.entry(message_type)
            .or_insert_with(Vec::new)
            .push(agent_id);
    }
    
    /// Set default route
    pub fn set_default_route(&mut self, agent_id: String) {
        self.default_route = Some(agent_id);
    }
    
    /// Get target agents for message
    pub fn get_targets(&self, message_type: MessageType) -> Vec<String> {
        self.routes.get(&message_type)
            .cloned()
            .or_else(|| self.default_route.clone().map(|id| vec![id]))
            .unwrap_or_default()
    }
}

/// Health monitor for engine and agents
pub struct HealthMonitor {
    /// Health checks
    health_checks: HashMap<String, Box<dyn HealthCheck + Send + Sync>>,
    /// Last health check results
    last_results: HashMap<String, HealthStatus>,
    /// Check interval
    check_interval: Duration,
}

/// Health check trait
pub trait HealthCheck {
    /// Check health
    fn check(&self) -> HealthStatus;
    /// Get check name
    fn name(&self) -> &str;
}

/// Health status
#[derive(Debug, Clone)]
pub struct HealthStatus {
    /// Check name
    pub name: String,
    /// Status
    pub status: Status,
    /// Message
    pub message: String,
    /// Timestamp
    pub timestamp: Instant,
}

/// Health status enum
#[derive(Debug, Clone, PartialEq)]
pub enum Status {
    /// Healthy
    Healthy,
    /// Warning
    Warning,
    /// Critical
    Critical,
    /// Unknown
    Unknown,
}

/// Performance profiler for monitoring engine performance
pub struct PerformanceProfiler {
    /// Performance metrics
    metrics: HashMap<String, PerformanceMetric>,
    /// Profiling enabled flag
    enabled: Arc<AtomicBool>,
}

/// Performance metric
#[derive(Debug, Clone)]
pub struct PerformanceMetric {
    /// Metric name
    pub name: String,
    /// Metric value
    pub value: f64,
    /// Unit
    pub unit: String,
    /// Timestamp
    pub timestamp: Instant,
    /// Tags
    pub tags: HashMap<String, String>,
}

/// Core message processor implementation
pub struct CoreMessageProcessor {
    /// Agent ID
    agent_id: String,
    /// Message router
    router: Arc<MessageRouter>,
    /// Agent registry
    agents: Arc<RwLock<HashMap<String, CoreAgent>>>,
    /// Processing statistics
    stats: AgentStats,
}

impl EventProcessor<CoreMessage> for CoreMessageProcessor {
    fn process_event(&mut self, event: &Event<CoreMessage>) -> Result<(), ProcessError> {
        let start_time = Instant::now();
        let message = unsafe { event.data() };
        
        // Route message to appropriate agents
        let targets = self.router.get_targets(message.message_type);
        
        for agent_id in targets {
            if let Ok(agents) = self.agents.try_read() {
                if let Some(agent) = agents.get(&agent_id) {
                    // Process message in agent context
                    if let Err(e) = self.process_message_for_agent(message, agent) {
                        warn!("Failed to process message for agent {}: {}", agent_id, e);
                        self.stats.messages_failed += 1;
                    } else {
                        self.stats.messages_processed += 1;
                    }
                }
            }
        }
        
        // Update processing statistics
        let processing_time = start_time.elapsed();
        self.stats.last_processing_time = Some(processing_time);
        
        // Update average processing time
        let total_processed = self.stats.messages_processed + self.stats.messages_failed;
        if total_processed > 0 {
            self.stats.avg_processing_time_us = 
                (self.stats.avg_processing_time_us * (total_processed - 1) as f64 + 
                 processing_time.as_micros() as f64) / total_processed as f64;
        }
        
        Ok(())
    }
    
    fn name(&self) -> &str {
        &self.agent_id
    }
}

impl CoreMessageProcessor {
    /// Create new core message processor
    pub fn new(
        agent_id: String,
        router: Arc<MessageRouter>,
        agents: Arc<RwLock<HashMap<String, CoreAgent>>>,
    ) -> Self {
        Self {
            agent_id,
            router,
            agents,
            stats: AgentStats::default(),
        }
    }
    
    /// Process message for specific agent
    fn process_message_for_agent(&self, message: &CoreMessage, agent: &CoreAgent) -> Result<(), ProcessError> {
        // Check if agent handles this message type
        if !agent.handled_types.contains(&message.message_type) {
            return Err(ProcessError::ProcessingFailed(
                format!("Agent {} does not handle message type {:?}", agent.id, message.message_type)
            ));
        }
        
        // Process message based on agent type
        match agent.agent_type {
            AgentType::DataIngestion => self.process_data_ingestion_message(message),
            AgentType::TradingEngine => self.process_trading_message(message),
            AgentType::RiskManagement => self.process_risk_message(message),
            AgentType::Analytics => self.process_analytics_message(message),
            AgentType::Storage => self.process_storage_message(message),
            AgentType::Network => self.process_network_message(message),
            AgentType::Security => self.process_security_message(message),
            AgentType::Custom(_) => self.process_custom_message(message),
        }
    }
    
    /// Process data ingestion message
    fn process_data_ingestion_message(&self, message: &CoreMessage) -> Result<(), ProcessError> {
        debug!("Processing data ingestion message: {:?}", message);
        // Implementation specific to data ingestion
        Ok(())
    }
    
    /// Process trading message
    fn process_trading_message(&self, message: &CoreMessage) -> Result<(), ProcessError> {
        debug!("Processing trading message: {:?}", message);
        // Implementation specific to trading engine
        Ok(())
    }
    
    /// Process risk message
    fn process_risk_message(&self, message: &CoreMessage) -> Result<(), ProcessError> {
        debug!("Processing risk message: {:?}", message);
        // Implementation specific to risk management
        Ok(())
    }
    
    /// Process analytics message
    fn process_analytics_message(&self, message: &CoreMessage) -> Result<(), ProcessError> {
        debug!("Processing analytics message: {:?}", message);
        // Implementation specific to analytics
        Ok(())
    }
    
    /// Process storage message
    fn process_storage_message(&self, message: &CoreMessage) -> Result<(), ProcessError> {
        debug!("Processing storage message: {:?}", message);
        // Implementation specific to storage
        Ok(())
    }
    
    /// Process network message
    fn process_network_message(&self, message: &CoreMessage) -> Result<(), ProcessError> {
        debug!("Processing network message: {:?}", message);
        // Implementation specific to networking
        Ok(())
    }
    
    /// Process security message
    fn process_security_message(&self, message: &CoreMessage) -> Result<(), ProcessError> {
        debug!("Processing security message: {:?}", message);
        // Implementation specific to security
        Ok(())
    }
    
    /// Process custom message
    fn process_custom_message(&self, message: &CoreMessage) -> Result<(), ProcessError> {
        debug!("Processing custom message: {:?}", message);
        // Implementation for custom agents
        Ok(())
    }
}

impl CoreEngine {
    /// Create new core engine
    pub fn new(config: CoreEngineConfig) -> Result<Self, Box<dyn std::error::Error>> {
        // Create message router
        let router = Arc::new(MessageRouter::new());
        
        // Create agent registry
        let agents = Arc::new(RwLock::new(HashMap::new()));
        
        // Create disruptor engine
        let disruptor = DisruptorBuilder::new()
            .with_consumers(config.num_processors)
            .with_processor(CoreMessageProcessor::new(
                "core_processor".to_string(),
                Arc::clone(&router),
                Arc::clone(&agents),
            ))
            .build();
        
        // Create health monitor
        let health_monitor = Arc::new(HealthMonitor {
            health_checks: HashMap::new(),
            last_results: HashMap::new(),
            check_interval: Duration::from_secs(30),
        });
        
        // Create performance profiler
        let profiler = Arc::new(PerformanceProfiler {
            metrics: HashMap::new(),
            enabled: Arc::new(AtomicBool::new(config.enable_profiling)),
        });
        
        Ok(Self {
            config,
            disruptor,
            agents,
            running: Arc::new(AtomicBool::new(false)),
            stats: Arc::new(RwLock::new(EngineStatistics::default())),
            router,
            health_monitor,
            profiler,
        })
    }
    
    /// Start the core engine
    pub async fn start(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        if self.running.load(Ordering::Acquire) {
            return Err("Engine already running".into());
        }
        
        info!("Starting Core Engine with {} processors", self.config.num_processors);
        
        // Start disruptor engine
        self.disruptor.start()?;
        
        // Set running flag
        self.running.store(true, Ordering::Release);
        
        // Start background tasks
        self.start_background_tasks().await?;
        
        info!("Core Engine started successfully");
        Ok(())
    }
    
    /// Stop the core engine
    pub async fn stop(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        if !self.running.load(Ordering::Acquire) {
            return Ok(());
        }
        
        info!("Stopping Core Engine");
        
        // Set running flag to false
        self.running.store(false, Ordering::Release);
        
        // Stop disruptor engine
        self.disruptor.stop()?;
        
        info!("Core Engine stopped successfully");
        Ok(())
    }
    
    /// Register new agent
    pub async fn register_agent(&self, agent: CoreAgent) -> Result<(), Box<dyn std::error::Error>> {
        let mut agents = self.agents.write().await;
        
        // Add routes for agent's handled message types
        for message_type in &agent.handled_types {
            self.router.add_route(*message_type, agent.id.clone());
        }
        
        agents.insert(agent.id.clone(), agent);
        
        info!("Registered agent: {}", agent.id);
        Ok(())
    }
    
    /// Unregister agent
    pub async fn unregister_agent(&self, agent_id: &str) -> Result<(), Box<dyn std::error::Error>> {
        let mut agents = self.agents.write().await;
        
        if let Some(agent) = agents.remove(agent_id) {
            // Remove routes for this agent
            for message_type in &agent.handled_types {
                // Remove from routing table
                // This is simplified - in practice, you'd need more sophisticated route management
            }
            
            info!("Unregistered agent: {}", agent_id);
        }
        
        Ok(())
    }
    
    /// Publish message to core engine
    pub async fn publish_message(&self, message: CoreMessage) -> Result<(), Box<dyn std::error::Error>> {
        if !self.running.load(Ordering::Acquire) {
            return Err("Engine not running".into());
        }
        
        // Publish to disruptor
        self.disruptor.publish(message, message.message_type as u32)?;
        
        // Update statistics
        {
            let mut stats = self.stats.write().await;
            stats.total_messages += 1;
            stats.last_update = Instant::now();
            
            // Calculate messages per second
            if let Some(uptime) = stats.uptime.checked_add(Duration::from_secs(1)) {
                stats.messages_per_second = stats.total_messages as f64 / uptime.as_secs_f64();
            }
        }
        
        Ok(())
    }
    
    /// Get engine statistics
    pub async fn get_statistics(&self) -> EngineStatistics {
        self.stats.read().await.clone()
    }
    
    /// Get all agents
    pub async fn get_agents(&self) -> HashMap<String, CoreAgent> {
        self.agents.read().await.clone()
    }
    
    /// Get agent by ID
    pub async fn get_agent(&self, agent_id: &str) -> Option<CoreAgent> {
        self.agents.read().await.get(agent_id).cloned()
    }
    
    /// Update agent heartbeat
    pub async fn update_agent_heartbeat(&self, agent_id: &str) -> Result<(), Box<dyn std::error::Error>> {
        let mut agents = self.agents.write().await;
        if let Some(agent) = agents.get_mut(agent_id) {
            agent.last_heartbeat = Instant::now();
            agent.status = AgentStatus::Running;
        }
        Ok(())
    }
    
    /// Start background tasks
    async fn start_background_tasks(&self) -> Result<(), Box<dyn std::error::Error>> {
        // Start health monitoring task
        let health_monitor = Arc::clone(&self.health_monitor);
        let agents = Arc::clone(&self.agents);
        let running = Arc::clone(&self.running);
        
        tokio::spawn(async move {
            let mut interval = tokio::time::interval(health_monitor.check_interval);
            
            while running.load(Ordering::Acquire) {
                interval.tick().await;
                
                // Check agent health
                if let Ok(agent_list) = agents.try_read() {
                    for (agent_id, agent) in agent_list.iter() {
                        let time_since_heartbeat = agent.last_heartbeat.elapsed();
                        
                        if time_since_heartbeat > Duration::from_secs(60) {
                            warn!("Agent {} appears to be unhealthy", agent_id);
                            // Update agent status
                            // In practice, you'd implement more sophisticated health checking
                        }
                    }
                }
            }
        });
        
        // Start performance monitoring task
        let profiler = Arc::clone(&self.profiler);
        let stats = Arc::clone(&self.stats);
        let running_profiler = Arc::clone(&self.running);
        
        tokio::spawn(async move {
            let mut interval = tokio::time::interval(Duration::from_secs(5));
            
            while running_profiler.load(Ordering::Acquire) {
                interval.tick().await;
                
                if profiler.enabled.load(Ordering::Acquire) {
                    // Collect performance metrics
                    // Update engine statistics
                    if let Ok(mut engine_stats) = stats.try_write() {
                        // Update performance metrics
                        engine_stats.memory_usage = Self::get_memory_usage();
                        engine_stats.cpu_usage = Self::get_cpu_usage();
                    }
                }
            }
        });
        
        Ok(())
    }
    
    /// Get current memory usage
    fn get_memory_usage() -> u64 {
        // Simplified memory usage calculation
        // In practice, you'd use system-specific APIs
        0
    }
    
    /// Get current CPU usage
    fn get_cpu_usage() -> f64 {
        // Simplified CPU usage calculation
        // In practice, you'd use system-specific APIs
        0.0
    }
}

/// Builder for Core Engine
pub struct CoreEngineBuilder {
    config: CoreEngineConfig,
}

impl CoreEngineBuilder {
    /// Create new builder
    pub fn new() -> Self {
        Self {
            config: CoreEngineConfig::default(),
        }
    }
    
    /// Set number of processors
    pub fn with_processors(mut self, count: usize) -> Self {
        self.config.num_processors = count;
        self
    }
    
    /// Enable profiling
    pub fn with_profiling(mut self, enabled: bool) -> Self {
        self.config.enable_profiling = enabled;
        self
    }
    
    /// Set buffer size
    pub fn with_buffer_size(mut self, size: usize) -> Self {
        self.config.buffer_size = size;
        self
    }
    
    /// Build core engine
    pub fn build(self) -> Result<CoreEngine, Box<dyn std::error::Error>> {
        CoreEngine::new(self.config)
    }
}

impl Default for CoreEngineBuilder {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{CoreMessage, MessageType};
    
    #[test]
    fn test_core_agent_creation() {
        let agent = CoreAgent {
            id: "test_agent".to_string(),
            name: "Test Agent".to_string(),
            agent_type: AgentType::DataIngestion,
            status: AgentStatus::Running,
            handled_types: vec![MessageType::MarketData],
            stats: AgentStats::default(),
            last_heartbeat: Instant::now(),
            thread_affinity: None,
        };
        
        assert_eq!(agent.id, "test_agent");
        assert_eq!(agent.agent_type, AgentType::DataIngestion);
        assert_eq!(agent.status, AgentStatus::Running);
    }
    
    #[test]
    fn test_message_router() {
        let mut router = MessageRouter::new();
        
        router.add_route(MessageType::MarketData, "data_agent".to_string());
        router.add_route(MessageType::Order, "trading_agent".to_string());
        router.set_default_route("default_agent".to_string());
        
        let targets = router.get_targets(MessageType::MarketData);
        assert_eq!(targets, vec!["data_agent"]);
        
        let unknown_targets = router.get_targets(MessageType::Event);
        assert_eq!(unknown_targets, vec!["default_agent"]);
    }
    
    #[tokio::test]
    async fn test_core_engine_builder() {
        let engine = CoreEngineBuilder::new()
            .with_processors(4)
            .with_profiling(true)
            .with_buffer_size(2048)
            .build();
        
        assert!(engine.is_ok());
    }
    
    #[tokio::test]
    async fn test_agent_registration() {
        let mut engine = CoreEngineBuilder::new()
            .with_processors(2)
            .build()
            .unwrap();
        
        let agent = CoreAgent {
            id: "test_agent".to_string(),
            name: "Test Agent".to_string(),
            agent_type: AgentType::DataIngestion,
            status: AgentStatus::Starting,
            handled_types: vec![MessageType::MarketData, MessageType::Order],
            stats: AgentStats::default(),
            last_heartbeat: Instant::now(),
            thread_affinity: None,
        };
        
        engine.start().await.unwrap();
        engine.register_agent(agent).await.unwrap();
        
        let retrieved_agent = engine.get_agent("test_agent").await;
        assert!(retrieved_agent.is_some());
        assert_eq!(retrieved_agent.unwrap().id, "test_agent");
        
        engine.stop().await.unwrap();
    }
}
