"""
MAIFA v3 Data Types - Core data structures and type definitions
"""

from typing import (
    Dict, List, Any, Optional, Union, Callable, Awaitable,
    Tuple, Set, FrozenSet, Type, Generic, TypeVar,
    Protocol, runtime_checkable, AsyncIterator
)
from dataclasses import dataclass
import asyncio
from datetime import datetime

# Type aliases for better readability
JSONDict = Dict[str, Any]
JSONList = List[Dict[str, Any]]
AgentFunction = Callable[[Dict[str, Any]], Dict[str, Any]]
AsyncAgentFunction = Callable[[Dict[str, Any]], Any]
EventHandler = Callable[[Dict[str, Any]], None]
AsyncEventHandler = Callable[[Dict[str, Any]], Any]

# Pipeline stage types
PipelineStage = str
PipelineResult = Dict[str, Any]

# Agent registry types
AgentConfig = Dict[str, Any]
AgentRegistry = Dict[str, AgentConfig]

# Event fabric types
EventStream = AsyncIterator[Dict[str, Any]]
EventFilter = Callable[[Dict[str, Any]], bool]

# Memory layer types
CacheKey = str
CacheValue = Any
ContextData = Dict[str, Any]

# Governance types
RateLimitKey = str
ResourceLimits = Dict[str, Union[int, float]]

# API types
APIResponse = Dict[str, Any]
WebSocketMessage = Dict[str, Any]

# Performance types
PerformanceMetrics = Dict[str, Union[int, float]]
LatencyMeasurement = float

# Error types
ErrorDict = Dict[str, Any]
ExceptionHandler = Callable[[Exception], ErrorDict]

# Configuration types
ConfigDict = Dict[str, Any]
EnvironmentConfig = Dict[str, str]

# Data source types
DataSourceConfig = Dict[str, Any]
DataQuality = Dict[str, Union[float, int]]

# Market data specific types
Symbol = str
Price = float
Volume = int
Timestamp = datetime

# Analysis result types
SentimentScore = float
ConfidenceScore = float
RiskScore = float

# Trading signal types
SignalStrength = float
Probability = float

# System state types
SystemHealth = str  # "healthy", "degraded", "critical"
ComponentStatus = Dict[str, str]

# Logging types
LogLevel = str  # "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
LogContext = Dict[str, Any]

# Security types
AuthToken = str
Permission = str
Role = str

# Validation types
ValidationRule = Callable[[Any], bool]
ValidationError = Dict[str, Any]

# Monitoring types
MetricName = str
MetricValue = Union[int, float, str]
MetricTags = Dict[str, str]

# Task management types
TaskID = str
TaskStatus = str  # "pending", "running", "completed", "failed", "cancelled"
TaskResult = Dict[str, Any]

# Communication types
MessageID = str
MessagePayload = Dict[str, Any]
MessageHeaders = Dict[str, str]

# Storage types
StorageKey = str
StorageValue = Any
StorageMetadata = Dict[str, Any]

# Time series types
TimeSeriesData = List[Tuple[Timestamp, float]]
TimeSeriesAggregation = str  # "avg", "sum", "min", "max", "count"

# Feature engineering types
FeatureVector = List[float]
FeatureName = str
FeatureImportance = Dict[FeatureName, float]

# Model types
ModelPrediction = Dict[str, Any]
ModelConfidence = float
ModelVersion = str

# Network types
NetworkRequest = Dict[str, Any]
NetworkResponse = Dict[str, Any]
NetworkError = Dict[str, Any]

# Database types
QueryResult = List[Dict[str, Any]]
QueryError = Dict[str, Any]

# File system types
FilePath = str
FileContent = Union[str, bytes]
FileMetadata = Dict[str, Any]

# External API types
ExternalAPIConfig = Dict[str, Any]
ExternalAPIResponse = Dict[str, Any]

# Notification types
NotificationMessage = Dict[str, Any]
NotificationChannel = str

# Backup and recovery types
BackupConfig = Dict[str, Any]
RestorePoint = str

# Testing types
TestCase = Dict[str, Any]
TestResult = Dict[str, Any]

# Documentation types
DocumentationSection = str
DocumentationContent = str
