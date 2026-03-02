use std::net::SocketAddr;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use tonic::{Request, Response, Status};
use tracing::{info, warn, error};

use crate::config::CoreEngineConfig;
use crate::data_ingestion::DataIngestionService;
use crate::proto::common::*;
use crate::proto::core_engine::*;
use crate::analytics::{AnalyticsManager, AnalyticsEvent, AnalyticsEventType, AnalyticsEventSeverity};
use crate::vector_store::{VectorStoreManager, VectorStoreConfig};
use std::collections::HashMap;

pub struct CoreEngineServiceImpl {
    config: CoreEngineConfig,
    data_ingestion: DataIngestionService,
    analytics: Option<AnalyticsManager>,
    vector_store: Option<VectorStoreManager>,
}

impl CoreEngineServiceImpl {
    pub fn new(config: CoreEngineConfig) -> Result<Self, Box<dyn std::error::Error>> {
        let data_ingestion = DataIngestionService::new()
            .map_err(|e| format!("Failed to create data ingestion service: {}", e))?;

        // Initialize analytics manager if enabled
        let analytics = if config.analytics_enabled {
            match AnalyticsManager::new(config.analytics_config.clone()).await {
                Ok(analytics) => {
                    info!("Analytics manager initialized successfully");
                    Some(analytics)
                }
                Err(e) => {
                    warn!("Failed to initialize analytics manager: {}. Continuing without analytics.", e);
                    None
                }
            }
        } else {
            info!("Analytics is disabled");
            None
        };

        // Initialize vector store manager if enabled
        let vector_store = if config.vector_store_enabled {
            match VectorStoreManager::new(config.vector_store_config.clone()).await {
                Ok(vector_store) => {
                    info!("Vector store manager initialized successfully");
                    Some(vector_store)
                }
                Err(e) => {
                    warn!("Failed to initialize vector store manager: {}. Continuing without vector store.", e);
                    None
                }
            }
        } else {
            info!("Vector store is disabled");
            None
        };

        Ok(Self { 
            config,
            data_ingestion,
            analytics,
            vector_store,
        })
    }
    
    /// Publish analytics event (fire-and-forget)
    async fn publish_analytics_event(&self, event_type: AnalyticsEventType, payload: Option<serde_json::Value>) {
        if let Some(analytics) = &self.analytics {
            let event = AnalyticsEvent {
                event_type,
                service: "core-engine".to_string(),
                instance_id: self.config.instance_id.clone(),
                payload,
                ..Default::default()
            };
            
            if let Err(e) = analytics.publish_event(event).await {
                error!("Failed to publish analytics event: {}", e);
            }
        }
    }
    
    /// Get predictive insights using vector store
    async fn get_predictive_insights(&self, market_data: &MarketData) -> Result<Vec<String>, Status> {
        if let Some(vector_store) = &self.vector_store {
            match vector_store.find_similar_patterns(market_data).await {
                Ok(similar_results) => {
                    let mut insights = Vec::new();
                    
                    for result in similar_results {
                        if let Some(pattern) = result.metadata.get("pattern") {
                            insights.push(format!("Similar pattern detected: {} (confidence: {:.2})", pattern, result.score));
                        }
                        
                        if let Some(prediction) = result.metadata.get("prediction") {
                            insights.push(format!("Predictive insight: {} (similarity: {:.2})", prediction, result.score));
                        }
                    }
                    
                    if insights.is_empty() {
                        insights.push("No similar patterns found in historical data".to_string());
                    }
                    
                    Ok(insights)
                }
                Err(e) => {
                    error!("Failed to get predictive insights: {}", e);
                    Err(Status::internal(format!("Failed to get predictive insights: {}", e)))
                }
            }
        } else {
            Ok(vec!["Vector store is not enabled".to_string()])
        }
    }
    
    /// Upsert market data to vector store
    async fn upsert_market_data_to_vector_store(&self, market_data: &[MarketData]) {
        if let Some(vector_store) = &self.vector_store {
            match vector_store.upsert_market_data(market_data).await {
                Ok(response) => {
                    info!("Successfully upserted {} market data embeddings to vector store", response.upserted_count);
                }
                Err(e) => {
                    error!("Failed to upsert market data to vector store: {}", e);
                }
            }
        }
    }
    
    /// Generate basic market analysis
    async fn generate_market_analysis(&self, market_data: &MarketData) -> MarketAnalysis {
        MarketAnalysis {
            symbol: market_data.symbol.clone(),
            current_price: market_data.price,
            price_change: 0.0, // Mock calculation
            price_change_percent: 0.0, // Mock calculation
            volume: market_data.volume,
            volume_change: 0.0, // Mock calculation
            volatility: 0.15, // Mock calculation
            momentum: 0.05, // Mock calculation
            trend_strength: 0.7, // Mock calculation
            technical_indicators: vec![
                "RSI: 65".to_string(),
                "MACD: Bullish".to_string(),
                "Moving Average: Above".to_string(),
            ],
            support_levels: vec![
                "145.00".to_string(),
                "140.00".to_string(),
                "135.00".to_string(),
            ],
            resistance_levels: vec![
                "155.00".to_string(),
                "160.00".to_string(),
                "165.00".to_string(),
            ],
            analysis_time: Some(prost_types::Timestamp {
                seconds: SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_secs(),
                nanos: 0,
            }),
            analysis_confidence: "medium".to_string(),
        }
    }
}

#[tonic::async_trait]
impl core_engine_service_server::CoreEngineService for CoreEngineServiceImpl {
    async fn health_check(
        &self,
        request: Request<HealthCheckRequest>,
    ) -> Result<Response<HealthCheckResponse>, Status> {
        let req = request.into_inner();
        
        // Publish analytics event
        self.publish_analytics_event(
            AnalyticsEventType::HealthCheck,
            Some(serde_json::json!({
                "request_id": req.request_id,
                "service": "core-engine",
                "instance_id": self.config.instance_id
            }))
        ).await;
        
        // Basic health check - always return healthy for now
        let response = HealthCheckResponse {
            healthy: true,
            status: "healthy".to_string(),
            version: env!("CARGO_PKG_VERSION").to_string(),
            uptime: Some(prost_types::Timestamp {
                seconds: SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_secs() as i64,
                nanos: 0,
            }),
            details: {
                let mut details = std::collections::HashMap::new();
                details.insert("service".to_string(), "core-engine".to_string());
                details.insert("port".to_string(), self.config.grpc_port.to_string());
                details.insert("processors".to_string(), self.config.num_processors.to_string());
                details
            },
            dependencies: vec![
                HealthCheckDependency {
                    name: "database".to_string(),
                    healthy: true, // TODO: Actually check database
                    status: "connected".to_string(),
                    response_time_ms: 5,
                },
                HealthCheckDependency {
                    name: "redis".to_string(),
                    healthy: true, // TODO: Actually check redis
                    status: "connected".to_string(),
                    response_time_ms: 2,
                },
                HealthCheckDependency {
                    name: "redpanda".to_string(),
                    healthy: true, // TODO: Actually check redpanda
                    status: "connected".to_string(),
                    response_time_ms: 10,
                },
            ],
        };

        Ok(Response::new(response))
    }

    async fn get_status(
        &self,
        _request: Request<prost_types::Empty>,
    ) -> Result<Response<EngineStatusResponse>, Status> {
        let response = EngineStatusResponse {
            status: ResponseStatus::ResponseStatusSuccess as i32,
            message: "Core Engine is running".to_string(),
            engine_status: Some(EngineStatus {
                status: EngineStatus::EngineStatusRunning as i32,
                version: env!("CARGO_PKG_VERSION").to_string(),
                start_time: Some(prost_types::Timestamp {
                    seconds: SystemTime::now()
                        .duration_since(UNIX_EPOCH)
                        .unwrap()
                        .as_secs() as i64,
                    nanos: 0,
                }),
                uptime: Some(prost_types::Timestamp {
                    seconds: SystemTime::now()
                        .duration_since(UNIX_EPOCH)
                        .unwrap()
                        .as_secs() as i64,
                    nanos: 0,
                }),
                num_processors: self.config.num_processors as i32,
                buffer_size: self.config.buffer_size as i64,
                total_messages_processed: 0,
                messages_per_second: 0.0,
                avg_latency_us: 0.0,
                p99_latency_us: 0.0,
                memory_usage_bytes: 0,
                cpu_usage_percent: 0.0,
            }),
            engine_info: Some(EngineInfo {
                version: env!("CARGO_PKG_VERSION").to_string(),
                start_time: Some(prost_types::Timestamp {
                    seconds: SystemTime::now()
                        .duration_since(UNIX_EPOCH)
                        .unwrap()
                        .as_secs() as i64,
                    nanos: 0,
                }),
                uptime: Some(prost_types::Timestamp {
                    seconds: SystemTime::now()
                        .duration_since(UNIX_EPOCH)
                        .unwrap()
                        .as_secs() as i64,
                    nanos: 0,
                }),
                num_processors: self.config.num_processors as i32,
                buffer_size: self.config.buffer_size as i64,
                total_messages_processed: 0,
                messages_per_second: 0.0,
                avg_latency_us: 0.0,
                p99_latency_us: 0.0,
                memory_usage_bytes: 0,
                cpu_usage_percent: 0.0,
            }),
            active_agents: vec![],
        };

        self.record_request_metrics("GetStatus", &Status::ok(()), start.elapsed());
        
        Ok(Response::new(response))
    }

    async fn fetch_market_data(
        &self,
        request: Request<FetchMarketDataRequest>,
    ) -> Result<Response<FetchMarketDataResponse>, Status> {
        let start = Instant::now();
        let (context, _span) = self.extract_trace_context(&request);
        let _guard = context.enter();

        let req = request.into_inner();
        
        // Publish analytics event for market data request
        self.publish_analytics_event(
            AnalyticsEventType::MarketDataReceived,
            Some(serde_json::json!({
                "symbols": req.symbols,
                "source_id": req.source_id,
                "request_size": req.symbols.len()
            }))
        ).await;
        
        match self.data_ingestion.fetch_market_data(req.symbols, &req.source_id).await {
            Ok(market_data) => {
                let proto_market_data: Vec<MarketData> = market_data
                    .into_iter()
                    .map(|data| MarketData {
                        symbol: data.symbol,
                        price: data.price,
                        volume: data.volume,
                        timestamp: Some(prost_types::Timestamp {
                            seconds: data.timestamp.timestamp(),
                            nanos: data.timestamp.timestamp_nanos() as i32,
                        }),
                        source: data.source,
                        additional_data: data.additional_data,
                    })
                    .collect();

                let response = FetchMarketDataResponse {
                    status: ResponseStatus::ResponseStatusSuccess as i32,
                    message: format!("Fetched {} market data items", proto_market_data.len()),
                    market_data: proto_market_data,
                };

                // Publish analytics event for successful market data processing
                self.publish_analytics_event(
                    AnalyticsEventType::MarketDataProcessed,
                    Some(serde_json::json!({
                        "symbols_count": proto_market_data.len(),
                        "processing_time_us": start.elapsed().as_micros(),
                        "source_id": req.source_id
                    }))
                ).await;
                
                // Upsert market data to vector store for AI analysis
                if !proto_market_data.is_empty() {
                    self.upsert_market_data_to_vector_store(&proto_market_data).await;
                }

                self.record_request_metrics("FetchMarketData", &Status::ok(()), start.elapsed());
                
                Ok(Response::new(response))
            }
            Err(e) => {
                error!("Failed to fetch market data: {}", e);
                
                let status = Status::internal(format!("Failed to fetch market data: {}", e));
                self.record_request_metrics("FetchMarketData", &status, start.elapsed());
                
                Err(status)
            }
        }
    }

    async fn fetch_news_data(
        &self,
        request: Request<FetchNewsDataRequest>,
    ) -> Result<Response<FetchNewsDataResponse>, Status> {
        let start = Instant::now();
        let (context, _span) = self.extract_trace_context(&request);
        let _guard = context.enter();

        let req = request.into_inner();
        
        match self.data_ingestion.fetch_news_data(req.keywords, &req.source_id, req.hours_back).await {
            Ok(news_items) => {
                let proto_news_items: Vec<NewsItem> = news_items
                    .into_iter()
                    .map(|news| NewsItem {
                        title: news.title,
                        content: news.content,
                        source: news.source,
                        timestamp: Some(prost_types::Timestamp {
                            seconds: news.timestamp.timestamp(),
                            nanos: news.timestamp.timestamp_nanos() as i32,
                        }),
                        sentiment_score: news.sentiment_score,
                        relevance_score: news.relevance_score,
                    })
                    .collect();

                let response = FetchNewsDataResponse {
                    status: ResponseStatus::ResponseStatusSuccess as i32,
                    message: format!("Fetched {} news items", proto_news_items.len()),
                    news_items: proto_news_items,
                };

                self.record_request_metrics("FetchNewsData", &Status::ok(()), start.elapsed());
                
                Ok(Response::new(response))
            }
            Err(e) => {
                error!("Failed to fetch news data: {}", e);
                
                let status = Status::internal(format!("Failed to fetch news data: {}", e));
                self.record_request_metrics("FetchNewsData", &status, start.elapsed());
                
                Err(status)
            }
        }
    }

    async fn get_market_data_buffer(
        &self,
        request: Request<GetMarketDataBufferRequest>,
    ) -> Result<Response<GetMarketDataBufferResponse>, Status> {
        let start = Instant::now();
        let (context, _span) = self.extract_trace_context(&request);
        let _guard = context.enter();

        let req = request.into_inner();
        
        let symbol = if req.symbol.is_empty() { None } else { Some(req.symbol) };
        let limit = if req.limit == 0 { 100 } else { req.limit as usize };
        
        match self.data_ingestion.get_market_data(symbol, limit).await {
            Ok(market_data) => {
                let proto_market_data: Vec<MarketData> = market_data
                    .into_iter()
                    .map(|data| MarketData {
                        symbol: data.symbol,
                        price: data.price,
                        volume: data.volume,
                        timestamp: Some(prost_types::Timestamp {
                            seconds: data.timestamp.timestamp(),
                            nanos: data.timestamp.timestamp_nanos() as i32,
                        }),
                        source: data.source,
                        additional_data: data.additional_data,
                    })
                    .collect();

                let response = GetMarketDataBufferResponse {
                    status: ResponseStatus::ResponseStatusSuccess as i32,
                    message: format!("Retrieved {} market data items from buffer", proto_market_data.len()),
                    market_data: proto_market_data,
                };

                self.record_request_metrics("GetMarketDataBuffer", &Status::ok(()), start.elapsed());
                
                Ok(Response::new(response))
            }
            Err(e) => {
                error!("Failed to get market data buffer: {}", e);
                
                let status = Status::internal(format!("Failed to get market data buffer: {}", e));
                self.record_request_metrics("GetMarketDataBuffer", &status, start.elapsed());
                
                Err(status)
            }
        }
    }

    async fn get_news_buffer(
        &self,
        request: Request<GetNewsBufferRequest>,
    ) -> Result<Response<GetNewsBufferResponse>, Status> {
        let start = Instant::now();
        let (context, _span) = self.extract_trace_context(&request);
        let _guard = context.enter();

        let req = request.into_inner();
        
        let keywords = if req.keywords.is_empty() { None } else { Some(req.keywords) };
        let limit = if req.limit == 0 { 100 } else { req.limit as usize };
        
        match self.data_ingestion.get_news_data(keywords, limit).await {
            Ok(news_items) => {
                let proto_news_items: Vec<NewsItem> = news_items
                    .into_iter()
                    .map(|news| NewsItem {
                        title: news.title,
                        content: news.content,
                        source: news.source,
                        timestamp: Some(prost_types::Timestamp {
                            seconds: news.timestamp.timestamp(),
                            nanos: news.timestamp.timestamp_nanos() as i32,
                        }),
                        sentiment_score: news.sentiment_score,
                        relevance_score: news.relevance_score,
                    })
                    .collect();

                let response = GetNewsBufferResponse {
                    status: ResponseStatus::ResponseStatusSuccess as i32,
                    message: format!("Retrieved {} news items from buffer", proto_news_items.len()),
                    news_items: proto_news_items,
                };

                self.record_request_metrics("GetNewsBuffer", &Status::ok(()), start.elapsed());
                
                Ok(Response::new(response))
            }
            Err(e) => {
                error!("Failed to get news buffer: {}", e);
                
                let status = Status::internal(format!("Failed to get news buffer: {}", e));
                self.record_request_metrics("GetNewsBuffer", &status, start.elapsed());
                
                Err(status)
            }
        }
    }

    async fn get_ingestion_stats(
        &self,
        request: Request<prost_types::Empty>,
    ) -> Result<Response<GetIngestionStatsResponse>, Status> {
        let start = Instant::now();
        let (context, _span) = self.extract_trace_context(&request);
        let _guard = context.enter();

        info!("Getting ingestion statistics");

        match self.data_ingestion.get_ingestion_stats().await {
            Ok(stats) => {
                let proto_data_sources: std::collections::HashMap<String, DataSourceInfo> = stats
                    .data_sources
                    .into_iter()
                    .map(|(id, info)| {
                        (id, DataSourceInfo {
                            r#type: info.r#type,
                            enabled: info.enabled,
                            connected: info.connected,
                        })
                    })
                    .collect();

                let proto_stats = IngestionStats {
                    active_connections: stats.active_connections,
                    configured_sources: stats.configured_sources,
                    market_data_buffer_size: stats.market_data_buffer_size,
                    news_buffer_size: stats.news_buffer_size,
                    max_buffer_size: stats.max_buffer_size,
                    data_sources: proto_data_sources,
                };

                let response = GetIngestionStatsResponse {
                    status: ResponseStatus::ResponseStatusSuccess as i32,
                    message: "Retrieved ingestion statistics".to_string(),
                    stats: Some(proto_stats),
                };

                self.record_request_metrics("GetIngestionStats", &Status::ok(()), start.elapsed());
                
                Ok(Response::new(response))
            }
            Err(e) => {
                error!("Failed to get ingestion stats: {}", e);
                
                let status = Status::internal(format!("Failed to get ingestion stats: {}", e));
                self.record_request_metrics("GetIngestionStats", &status, start.elapsed());
                
                Err(status)
            }
        }
    }

    async fn connect_data_source(
        &self,
        request: Request<ConnectDataSourceRequest>,
    ) -> Result<Response<ConnectDataSourceResponse>, Status> {
        let start = Instant::now();
        let (context, _span) = self.extract_trace_context(&request);
        let _guard = context.enter();

        let req = request.into_inner();
        
        let api_key = if req.api_key.is_empty() { None } else { Some(req.api_key) };
        
        match self.data_ingestion.connect_data_source(&req.source_id, api_key).await {
            Ok(connected) => {
                let response = ConnectDataSourceResponse {
                    status: ResponseStatus::ResponseStatusSuccess as i32,
                    message: if connected {
                        format!("Successfully connected to data source: {}", req.source_id)
                    } else {
                        format!("Failed to connect to data source: {}", req.source_id)
                    },
                    connected,
                };
                self.record_request_metrics("ConnectDataSource", &Status::ok(()), start.elapsed());
                
                Ok(Response::new(response))
            }
            Err(e) => {
                error!("Failed to connect to data source: {}", e);
                
                let status = Status::internal(format!("Failed to connect to data source: {}", e));
                self.record_request_metrics("ConnectDataSource", &status, start.elapsed());
                
                Err(status)
            }
        }
    }

    async fn process_message(
        &self,
        _request: Request<ProcessMessageRequest>,
    ) -> Result<Response<ProcessMessageResponse>, Status> {
        // TODO: Implement actual message processing
        Err(Status::unimplemented("ProcessMessage not yet implemented"))
    }

    async fn process_message_stream(
        &self,
        _request: tonic::Streaming<ProcessMessageRequest>,
    ) -> Result<Response<tonic::codec::Streaming<ProcessMessageResponse>>, Status> {
        // TODO: Implement actual message stream processing
        Err(Status::unimplemented("ProcessMessageStream not yet implemented"))
    }

    async fn batch_process_messages(
        &self,
        _request: Request<BatchProcessMessagesRequest>,
    ) -> Result<Response<BatchProcessMessagesResponse>, Status> {
        // TODO: Implement actual batch processing
        Err(Status::unimplemented("BatchProcessMessages not yet implemented"))
    }

    async fn register_agent(
        &self,
        _request: Request<RegisterAgentRequest>,
    ) -> Result<Response<StandardResponse>, Status> {
        // TODO: Implement agent registration
        Err(Status::unimplemented("RegisterAgent not yet implemented"))
    }

    async fn unregister_agent(
        &self,
        _request: Request<UnregisterAgentRequest>,
    ) -> Result<Response<StandardResponse>, Status> {
        // TODO: Implement agent unregistration
        Err(Status::unimplemented("UnregisterAgent not yet implemented"))
    }

    async fn list_agents(
        &self,
        _request: Request<ListAgentsRequest>,
    ) -> Result<Response<ListAgentsResponse>, Status> {
        // TODO: Implement agent listing
        Err(Status::unimplemented("ListAgents not yet implemented"))
    }

    async fn get_agent_status(
        &self,
        _request: Request<GetAgentStatusRequest>,
    ) -> Result<Response<GetAgentStatusResponse>, Status> {
        // TODO: Implement agent status
        Err(Status::unimplemented("GetAgentStatus not yet implemented"))
    }

    async fn get_configuration(
        &self,
        _request: Request<GetConfigurationRequest>,
    ) -> Result<Response<GetConfigurationResponse>, Status> {
        // TODO: Implement configuration retrieval
        Err(Status::unimplemented("GetConfiguration not yet implemented"))
    }

    async fn update_configuration(
        &self,
        _request: Request<UpdateConfigurationRequest>,
    ) -> Result<Response<StandardResponse>, Status> {
        // TODO: Implement configuration update
        Err(Status::unimplemented("UpdateConfiguration not yet implemented"))
    }

    async fn get_metrics(
        &self,
        _request: Request<GetMetricsRequest>,
    ) -> Result<Response<GetMetricsResponse>, Status> {
        // TODO: Implement metrics retrieval
        Err(Status::unimplemented("GetMetrics not yet implemented"))
    }

    async fn get_performance_stats(
        &self,
        _request: Request<prost_types::Empty>,
    ) -> Result<Response<PerformanceStatsResponse>, Status> {
        // TODO: Implement performance stats
        Err(Status::unimplemented("GetPerformanceStats not yet implemented"))
    }

    async fn analyze_market_data(
        &self,
        request: Request<AnalyzeMarketDataRequest>,
    ) -> Result<Response<AnalyzeMarketDataResponse>, Status> {
        let start = Instant::now();
        let req = request.into_inner();
        
        info!("Analyzing market data for symbols: {:?}", req.symbols);
        
        // Fetch market data first
        let market_data_result = self.data_ingestion.fetch_market_data(req.symbols.clone(), &req.source_id).await;
        
        match market_data_result {
            Ok(market_data) => {
                let proto_market_data: Vec<MarketData> = market_data
                    .into_iter()
                    .map(|data| MarketData {
                        symbol: data.symbol.clone(),
                        price: data.price,
                        volume: data.volume,
                        timestamp: Some(prost_types::Timestamp {
                            seconds: data.timestamp.timestamp(),
                            nanos: data.timestamp.timestamp_nanos() as i32,
                        }),
                        source: data.source.clone(),
                        additional_data: data.additional_data,
                    })
                    .collect();

                // Upsert to vector store for future analysis
                if !proto_market_data.is_empty() {
                    self.upsert_market_data_to_vector_store(&proto_market_data).await;
                }

                // Generate market analysis
                let mut analysis_results = Vec::new();
                let mut all_insights = Vec::new();
                let mut all_patterns = Vec::new();

                for data in &proto_market_data {
                    // Generate basic market analysis
                    let analysis = self.generate_market_analysis(data).await;
                    analysis_results.push(analysis);

                    // Get predictive insights if requested
                    if req.include_predictive_insights {
                        match self.get_predictive_insights(data).await {
                            Ok(insights) => {
                                let predictive_insights: Vec<PredictiveInsight> = insights
                                    .into_iter()
                                    .enumerate()
                                    .map(|(i, insight)| PredictiveInsight {
                                        insight_type: "price_prediction".to_string(),
                                        prediction: insight,
                                        confidence_score: 0.8 - (i as f64 * 0.1), // Decreasing confidence
                                        time_horizon_hours: 24,
                                        supporting_factors: vec![
                                            "historical_pattern_match".to_string(),
                                            "volume_analysis".to_string(),
                                            "technical_indicators".to_string(),
                                        ],
                                        risk_factors: vec![
                                            "market_volatility".to_string(),
                                            "external_factors".to_string(),
                                        ],
                                        probability_distribution: HashMap::from([
                                            ("up".to_string(), 0.45),
                                            ("down".to_string(), 0.35),
                                            ("sideways".to_string(), 0.20),
                                        ]),
                                        generated_at: Some(prost_types::Timestamp {
                                            seconds: SystemTime::now()
                                                .duration_since(UNIX_EPOCH)
                                                .unwrap()
                                                .as_secs(),
                                            nanos: 0,
                                        }),
                                    })
                                    .collect();
                                all_insights.extend(predictive_insights);
                            }
                            Err(e) => {
                                warn!("Failed to get predictive insights for {}: {}", data.symbol, e);
                            }
                        }
                    }
                }

                let response = AnalyzeMarketDataResponse {
                    status: ResponseStatus::ResponseStatusSuccess as i32,
                    message: format!("Successfully analyzed {} symbols", proto_market_data.len()),
                    market_data: proto_market_data,
                    analysis: analysis_results.into_iter().next(), // Return first analysis for simplicity
                    insights: all_insights,
                    patterns: all_patterns,
                };

                self.record_request_metrics("AnalyzeMarketData", &Status::ok(()), start.elapsed());
                
                Ok(Response::new(response))
            }
            Err(e) => {
                error!("Failed to fetch market data for analysis: {}", e);
                
                let status = Status::internal(format!("Failed to fetch market data for analysis: {}", e));
                self.record_request_metrics("AnalyzeMarketData", &status, start.elapsed());
                
                Err(status)
            }
        }
    }

    async fn get_predictive_insights(
        &self,
        request: Request<GetPredictiveInsightsRequest>,
    ) -> Result<Response<GetPredictiveInsightsResponse>, Status> {
        let start = Instant::now();
        let req = request.into_inner();
        
        info!("Getting predictive insights for symbol: {}", req.symbol);
        
        // Create a mock market data object for the symbol
        let market_data = MarketData {
            symbol: req.symbol.clone(),
            price: 150.0, // Mock price
            volume: 1000000, // Mock volume
            timestamp: Some(prost_types::Timestamp {
                seconds: SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_secs(),
                nanos: 0,
            }),
            source: "mock".to_string(),
            additional_data: HashMap::new(),
        };

        // Get predictive insights
        match self.get_predictive_insights(&market_data).await {
            Ok(insights) => {
                let predictive_insights: Vec<PredictiveInsight> = insights
                    .into_iter()
                    .enumerate()
                    .take(req.max_insights as usize)
                    .map(|(i, insight)| PredictiveInsight {
                        insight_type: "price_prediction".to_string(),
                        prediction: insight,
                        confidence_score: (0.9 - (i as f64 * 0.1)).max(req.confidence_threshold),
                        time_horizon_hours: req.time_horizon_hours as i32,
                        supporting_factors: vec![
                            "historical_pattern_match".to_string(),
                            "volume_analysis".to_string(),
                            "technical_indicators".to_string(),
                        ],
                        risk_factors: vec![
                            "market_volatility".to_string(),
                            "external_factors".to_string(),
                        ],
                        probability_distribution: HashMap::from([
                            ("up".to_string(), 0.45),
                            ("down".to_string(), 0.35),
                            ("sideways".to_string(), 0.20),
                        ]),
                        generated_at: Some(prost_types::Timestamp {
                            seconds: SystemTime::now()
                                .duration_since(UNIX_EPOCH)
                                .unwrap()
                                .as_secs(),
                            nanos: 0,
                        }),
                    })
                    .collect();

                // Get vector store stats
                let vector_store_stats = if let Some(vector_store) = &self.vector_store {
                    match vector_store.get_stats().await {
                        Ok(stats) => Some(VectorStoreStats {
                            total_vectors: stats.total_vectors,
                            collection_size_bytes: stats.collection_size_bytes,
                            index_size_bytes: stats.index_size_bytes,
                            segments_count: stats.segments_count,
                            index_status: stats.index_status,
                            avg_search_time_ms: stats.search_metrics.avg_search_time_ms,
                            cache_hit_rate: stats.search_metrics.cache_hit_rate,
                            active_connections: stats.pool_metrics.active_connections as i64,
                            last_updated: Some(prost_types::Timestamp {
                                seconds: SystemTime::now()
                                    .duration_since(UNIX_EPOCH)
                                    .unwrap()
                                    .as_secs(),
                                nanos: 0,
                            }),
                        }),
                        Err(_) => None,
                    }
                } else {
                    None
                };

                let response = GetPredictiveInsightsResponse {
                    status: ResponseStatus::ResponseStatusSuccess as i32,
                    message: format!("Successfully retrieved {} predictive insights", predictive_insights.len()),
                    insights: predictive_insights,
                    vector_store_stats,
                };

                self.record_request_metrics("GetPredictiveInsights", &Status::ok(()), start.elapsed());
                
                Ok(Response::new(response))
            }
            Err(e) => {
                error!("Failed to get predictive insights: {}", e);
                
                let status = Status::internal(format!("Failed to get predictive insights: {}", e));
                self.record_request_metrics("GetPredictiveInsights", &status, start.elapsed());
                
                Err(status)
            }
        }
    }
}
