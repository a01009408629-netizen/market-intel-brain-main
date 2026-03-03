use tonic::{Request, Response, Status};
use tracing::{error, info, warn};

use crate::config::CoreEngineConfig;

// ── generated types (تولّدها tonic-build من proto) ──────────────────────────
// استخدم include! لاستيراد الكود المولّد مباشرة
pub mod proto {
    pub mod core_engine {
        tonic::include_proto!("market_intel.core_engine.v1");
    }
    pub mod common {
        tonic::include_proto!("market_intel.common.v1");
    }
}

use proto::core_engine::core_engine_service_server::{
    CoreEngineService, CoreEngineServiceServer,
};
use proto::core_engine::*;
use proto::common::*;

pub struct CoreEngineServiceImpl {
    config: CoreEngineConfig,
}

impl CoreEngineServiceImpl {
    pub async fn new(config: CoreEngineConfig) 
        -> Result<Self, Box<dyn std::error::Error>> 
    {
        info!("Initializing CoreEngineServiceImpl");
        Ok(Self { config })
    }

    /// Convert into a tonic service ready for Server::add_service()
    pub fn into_service(self) -> CoreEngineServiceServer<Self> {
        CoreEngineServiceServer::new(self)
    }
}

#[tonic::async_trait]
impl CoreEngineService for CoreEngineServiceImpl {
    async fn health_check(
        &self,
        _request: Request<HealthCheckRequest>,
    ) -> Result<Response<HealthCheckResponse>, Status> {
        Ok(Response::new(HealthCheckResponse {
            status: health_check_response::ServingStatus::Serving as i32,
            message: "healthy".to_string(),
            details: std::collections::HashMap::new(),
        }))
    }

    async fn process_message(
        &self, _request: Request<ProcessMessageRequest>,
    ) -> Result<Response<ProcessMessageResponse>, Status> {
        Err(Status::unimplemented("ProcessMessage not implemented"))
    }

    async fn process_batch_messages(
        &self, _request: Request<ProcessBatchMessagesRequest>,
    ) -> Result<Response<ProcessBatchMessagesResponse>, Status> {
        Err(Status::unimplemented("ProcessBatchMessages not implemented"))
    }

    type ProcessStreamMessagesStream = 
        tokio_stream::wrappers::ReceiverStream<Result<ProcessStreamMessagesResponse, Status>>;

    async fn process_stream_messages(
        &self,
        _request: Request<tonic::Streaming<ProcessStreamMessagesRequest>>,
    ) -> Result<Response<Self::ProcessStreamMessagesStream>, Status> {
        Err(Status::unimplemented("ProcessStreamMessages not implemented"))
    }

    async fn create_agent(&self, _r: Request<CreateAgentRequest>)
        -> Result<Response<CreateAgentResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn get_agent(&self, _r: Request<GetAgentRequest>)
        -> Result<Response<GetAgentResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn update_agent(&self, _r: Request<UpdateAgentRequest>)
        -> Result<Response<UpdateAgentResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn delete_agent(&self, _r: Request<DeleteAgentRequest>)
        -> Result<Response<DeleteAgentResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn list_agents(&self, _r: Request<ListAgentsRequest>)
        -> Result<Response<ListAgentsResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn start_agent(&self, _r: Request<StartAgentRequest>)
        -> Result<Response<StartAgentResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn stop_agent(&self, _r: Request<StopAgentRequest>)
        -> Result<Response<StopAgentResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn restart_agent(&self, _r: Request<RestartAgentRequest>)
        -> Result<Response<RestartAgentResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn get_configuration(&self, _r: Request<GetConfigurationRequest>)
        -> Result<Response<GetConfigurationResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn update_configuration(&self, _r: Request<UpdateConfigurationRequest>)
        -> Result<Response<UpdateConfigurationResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn reset_configuration(&self, _r: Request<ResetConfigurationRequest>)
        -> Result<Response<ResetConfigurationResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn get_metrics(&self, _r: Request<GetMetricsRequest>)
        -> Result<Response<GetMetricsResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn get_performance_metrics(&self, _r: Request<GetPerformanceMetricsRequest>)
        -> Result<Response<GetPerformanceMetricsResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn get_resource_usage(&self, _r: Request<GetResourceUsageRequest>)
        -> Result<Response<GetResourceUsageResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn ingest_data(&self, _r: Request<IngestDataRequest>)
        -> Result<Response<IngestDataResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn ingest_batch_data(&self, _r: Request<IngestBatchDataRequest>)
        -> Result<Response<IngestBatchDataResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn get_data_ingestion_status(&self, _r: Request<GetDataIngestionStatusRequest>)
        -> Result<Response<GetDataIngestionStatusResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn run_analysis(&self, _r: Request<RunAnalysisRequest>)
        -> Result<Response<RunAnalysisResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn get_analysis_results(&self, _r: Request<GetAnalysisResultsRequest>)
        -> Result<Response<GetAnalysisResultsResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn generate_signals(&self, _r: Request<GenerateSignalsRequest>)
        -> Result<Response<GenerateSignalsResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn get_signals(&self, _r: Request<GetSignalsRequest>)
        -> Result<Response<GetSignalsResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn create_vector(&self, _r: Request<CreateVectorRequest>)
        -> Result<Response<CreateVectorResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn search_vectors(&self, _r: Request<SearchVectorsRequest>)
        -> Result<Response<SearchVectorsResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn update_vector(&self, _r: Request<UpdateVectorRequest>)
        -> Result<Response<UpdateVectorResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn delete_vector(&self, _r: Request<DeleteVectorRequest>)
        -> Result<Response<DeleteVectorResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn get_from_cache(&self, _r: Request<GetFromCacheRequest>)
        -> Result<Response<GetFromCacheResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn set_in_cache(&self, _r: Request<SetInCacheRequest>)
        -> Result<Response<SetInCacheResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn delete_from_cache(&self, _r: Request<DeleteFromCacheRequest>)
        -> Result<Response<DeleteFromCacheResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn clear_cache(&self, _r: Request<ClearCacheRequest>)
        -> Result<Response<ClearCacheResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }

    type SubscribeToEventsStream =
        tokio_stream::wrappers::ReceiverStream<Result<EventMessage, Status>>;

    async fn subscribe_to_events(&self, _r: Request<SubscribeToEventsRequest>)
        -> Result<Response<Self::SubscribeToEventsStream>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn publish_event(&self, _r: Request<PublishEventRequest>)
        -> Result<Response<PublishEventResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn get_event_history(&self, _r: Request<GetEventHistoryRequest>)
        -> Result<Response<GetEventHistoryResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn create_task(&self, _r: Request<CreateTaskRequest>)
        -> Result<Response<CreateTaskResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn get_task(&self, _r: Request<GetTaskRequest>)
        -> Result<Response<GetTaskResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn update_task(&self, _r: Request<UpdateTaskRequest>)
        -> Result<Response<UpdateTaskResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn cancel_task(&self, _r: Request<CancelTaskRequest>)
        -> Result<Response<CancelTaskResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn list_tasks(&self, _r: Request<ListTasksRequest>)
        -> Result<Response<ListTasksResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn create_pipeline(&self, _r: Request<CreatePipelineRequest>)
        -> Result<Response<CreatePipelineResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn get_pipeline(&self, _r: Request<GetPipelineRequest>)
        -> Result<Response<GetPipelineResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn update_pipeline(&self, _r: Request<UpdatePipelineRequest>)
        -> Result<Response<UpdatePipelineResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn delete_pipeline(&self, _r: Request<DeletePipelineRequest>)
        -> Result<Response<DeletePipelineResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
    async fn list_pipelines(&self, _r: Request<ListPipelinesRequest>)
        -> Result<Response<ListPipelinesResponse>, Status> {
        Err(Status::unimplemented("not implemented"))
    }

    type ExecutePipelineStream =
        tokio_stream::wrappers::ReceiverStream<Result<ExecutePipelineResponse, Status>>;

    async fn execute_pipeline(&self, _r: Request<ExecutePipelineRequest>)
        -> Result<Response<Self::ExecutePipelineStream>, Status> {
        Err(Status::unimplemented("not implemented"))
    }
}