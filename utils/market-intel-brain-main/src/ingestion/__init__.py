"""
Market Intel Brain - Data Ingestion Engine

High-frequency data aggregation system with <100ms p95 latency.
Supports 13+ financial and news sources with concurrent processing.
"""

from .engine import IngestionEngine, get_ingestion_engine, start_ingestion_engine, stop_ingestion_engine
from .config import IngestionConfig, SourceConfig, get_config, reload_config
from .workers import WorkerPool, DataSourceWorker

__all__ = [
    "IngestionEngine",
    "get_ingestion_engine",
    "start_ingestion_engine", 
    "stop_ingestion_engine",
    "IngestionConfig", 
    "SourceConfig",
    "get_config",
    "reload_config",
    "WorkerPool",
    "DataSourceWorker"
]
