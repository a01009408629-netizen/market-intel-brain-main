"""
Telemetry Configuration - OpenTelemetry Settings

Enterprise-grade telemetry configuration with environment variable
integration and observability settings.
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class TelemetryConfig:
    """Telemetry configuration for OpenTelemetry."""
    
    # Service identification
    service_name: str = field(default_factory=lambda: os.getenv("OTEL_SERVICE_NAME", "market-intel-brain"))
    service_version: str = field(default_factory=lambda: os.getenv("OTEL_SERVICE_VERSION", "1.0.0"))
    service_namespace: str = field(default_factory=lambda: os.getenv("SERVICE_NAMESPACE", "production"))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "production"))
    
    # OTLP exporter configuration
    otlp_endpoint: Optional[str] = field(default_factory=lambda: os.getenv("OTEL_ENDPOINT"))
    otlp_headers: Dict[str, str] = field(default_factory=lambda: {
        header.split("=")[0]: header.split("=")[1] 
        for header in os.getenv("OTEL_HEADERS", "").split(",") 
        if "=" in header
    })
    otlp_insecure: bool = field(default_factory=lambda: os.getenv("OTEL_INSECURE", "false").lower() == "true")
    
    # Sampling configuration
    sample_rate: float = field(default_factory=lambda: float(os.getenv("OTEL_SAMPLE_RATE", "1.0")))
    trace_parent_ratio: float = field(default_factory=lambda: float(os.getenv("OTEL_TRACE_PARENT_RATIO", "1.0")))
    
    # Resource configuration
    resource_attributes: Dict[str, str] = field(default_factory=lambda: {
        attr.split("=")[0]: attr.split("=")[1]
        for attr in os.getenv("OTEL_RESOURCE_ATTRIBUTES", "").split(",") 
        if "=" in attr
    })
    
    # Performance configuration
    span_processor_max_queue_size: int = field(default_factory=lambda: int(os.getenv("OTEL_SPAN_PROCESSOR_MAX_QUEUE_SIZE", "2048")))
    span_processor_max_export_batch_size: int = field(default_factory=lambda: int(os.getenv("OTEL_SPAN_PROCESSOR_MAX_EXPORT_BATCH_SIZE", "512")))
    span_processor_export_timeout_millis: int = field(default_factory=lambda: int(os.getenv("OTEL_SPAN_PROCESSOR_EXPORT_TIMEOUT_MILLIS", "30000")))
    span_processor_max_export_batch_size: int = field(default_factory=lambda: int(os.getenv("OTEL_SPAN_PROCESSOR_MAX_EXPORT_BATCH_SIZE", "512")))
    
    # Metrics configuration
    metrics_export_interval: int = field(default_factory=lambda: int(os.getenv("OTEL_METRICS_EXPORT_INTERVAL", "60000")))
    metrics_export_timeout: int = field(default_factory=lambda: int(os.getenv("OTEL_METRICS_EXPORT_TIMEOUT", "30000")))
    
    # Logging configuration
    logging_level: str = field(default_factory=lambda: os.getenv("OTEL_LOG_LEVEL", "INFO"))
    
    @classmethod
    def from_env(cls) -> "TelemetryConfig":
        """Create configuration from environment variables."""
        return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "service_name": self.service_name,
            "service_version": self.service_version,
            "service_namespace": self.service_namespace,
            "environment": self.environment,
            "otlp_endpoint": self.otlp_endpoint,
            "otlp_insecure": self.otlp_insecure,
            "sample_rate": self.sample_rate,
            "trace_parent_ratio": self.trace_parent_ratio,
            "resource_attributes": self.resource_attributes,
            "span_processor_max_queue_size": self.span_processor_max_queue_size,
            "span_processor_max_export_batch_size": self.span_processor_max_export_batch_size,
            "span_processor_export_timeout_millis": self.span_processor_export_timeout_millis,
            "metrics_export_interval": self.metrics_export_interval,
            "metrics_export_timeout": self.metrics_export_timeout,
            "logging_level": self.logging_level
        }
