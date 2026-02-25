"""
Real-time Data Pipeline Infrastructure
بنية تحتية لمعالجة البيانات الفورية

High-performance data processing pipeline for 30+ data sources
Supports WebSockets, FIX protocol, and zero-copy deserialization
"""

from .realtime_processor import (
    RealTimeDataPipeline,
    DataSourceConfig,
    ProcessedData,
    ZeroCopyDeserializer,
    WebSocketDataReceiver,
    FIXProtocolReceiver
)

from .protobuf_schemas import (
    ProtobufConverter,
    ProtobufFactory,
    MarketDataProto,
    FIXMessageProto,
    WebSocketMessageProto
)

__version__ = "1.0.0"
__author__ = "Market Intel Brain Team"

# Export main components
__all__ = [
    # Main pipeline
    'RealTimeDataPipeline',
    'DataSourceConfig',
    'ProcessedData',
    
    # Receivers
    'ZeroCopyDeserializer',
    'WebSocketDataReceiver',
    'FIXProtocolReceiver',
    
    # Protobuf schemas
    'ProtobufConverter',
    'ProtobufFactory',
    'MarketDataProto',
    'FIXMessageProto',
    'WebSocketMessageProto'
]
