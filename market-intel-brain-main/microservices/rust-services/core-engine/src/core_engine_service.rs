use std::net::SocketAddr;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use tonic::{Request, Response, Status};

use crate::config::CoreEngineConfig;
use crate::data_ingestion::DataIngestionService;
use crate::proto::common::*;
use crate::proto::core_engine::*;

pub struct CoreEngineServiceImpl {
    config: CoreEngineConfig,
    data_ingestion: DataIngestionService,
}

impl CoreEngineServiceImpl {
    pub fn new(config: CoreEngineConfig) -> Result<Self, Box<dyn std::error::Error>> {
        let data_ingestion = DataIngestionService::new()
            .map_err(|e| format!("Failed to create data ingestion service: {}", e))?;

        Ok(Self { 
            config,
            data_ingestion,
        })
    }
}

#[tonic::async_trait]
impl core_engine_service_server::CoreEngineService for CoreEngineServiceImpl {
    async fn health_check(
        &self,
        request: Request<HealthCheckRequest>,
    ) -> Result<Response<HealthCheckResponse>, Status> {
        let req = request.into_inner();
        
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
}
