"""
Serialization Layer - Protobuf and Msgpack Support

Enterprise-grade serialization for minimal network payload
and reduced CPU parsing overhead compared to JSON.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Type
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import uuid

try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False
    msgpack = None

try:
    # Try to import protobuf
    import google.protobuf
    import google.protobuf.message
    import google.protobuf.json_format
    PROTOBUF_AVAILABLE = True
except ImportError:
    PROTOBUF_AVAILABLE = False
    google = None


class SerializationFormat(Enum):
    """Supported serialization formats."""
    PROTOBUF = "protobuf"
    MSGPACK = "msgpack"
    JSON = "json"


@dataclass
class SerializationResult:
    """Serialization operation result."""
    data: bytes
    format: SerializationFormat
    size_bytes: int
    compression_ratio: Optional[float] = None
    serialization_time_ms: Optional[float] = None


class BaseSerializer(ABC):
    """Abstract base class for serializers."""
    
    @abstractmethod
    def serialize(self, data: Any) -> SerializationResult:
        """Serialize data to bytes."""
        pass
    
    @abstractmethod
    def deserialize(self, data: bytes, target_type: Optional[Type] = None) -> Any:
        """Deserialize bytes to data."""
        pass
    
    @abstractmethod
    def get_format(self) -> SerializationFormat:
        """Get serialization format."""
        pass


class ProtobufSerializer(BaseSerializer):
    """
    Protocol Buffers serializer for maximum efficiency.
    
    Features:
    - Minimal payload size
    - Fast serialization/deserialization
    - Schema evolution support
    - Language agnostic
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        if not PROTOBUF_AVAILABLE:
            raise ImportError("protobuf package is required. Install with: pip install protobuf")
        
        self.logger = logger or logging.getLogger("ProtobufSerializer")
        self._message_classes = {}
        self._initialize_message_classes()
    
    def _initialize_message_classes(self):
        """Initialize protobuf message classes."""
        try:
            # Import generated protobuf classes
            from ..schemas.market_data_pb2 import (
                MarketTick,
                NewsArticle,
                SentimentData,
                MarketDataBatch
            )
            
            self._message_classes = {
                'MarketTick': MarketTick,
                'NewsArticle': NewsArticle,
                'SentimentData': SentimentData,
                'MarketDataBatch': MarketDataBatch
            }
            
            self.logger.info("Protobuf message classes initialized")
            
        except ImportError as e:
            self.logger.error(f"Failed to import protobuf classes: {e}")
            raise
    
    def serialize(self, data: Any) -> SerializationResult:
        """Serialize data using Protocol Buffers."""
        import time
        start_time = time.time()
        
        try:
            # Convert dict to protobuf message
            protobuf_message = self._dict_to_protobuf(data)
            
            # Serialize to bytes
            serialized_data = protobuf_message.SerializeToString()
            
            serialization_time = (time.time() - start_time) * 1000
            
            return SerializationResult(
                data=serialized_data,
                format=SerializationFormat.PROTOBUF,
                size_bytes=len(serialized_data),
                serialization_time_ms=serialization_time
            )
            
        except Exception as e:
            self.logger.error(f"Protobuf serialization failed: {e}")
            raise
    
    def deserialize(self, data: bytes, target_type: Optional[str] = None) -> Any:
        """Deserialize bytes using Protocol Buffers."""
        try:
            if not target_type:
                # Try to detect message type
                target_type = self._detect_message_type(data)
            
            if target_type not in self._message_classes:
                raise ValueError(f"Unknown protobuf message type: {target_type}")
            
            message_class = self._message_classes[target_type]
            protobuf_message = message_class()
            protobuf_message.ParseFromString(data)
            
            # Convert to dict
            return self._protobuf_to_dict(protobuf_message)
            
        except Exception as e:
            self.logger.error(f"Protobuf deserialization failed: {e}")
            raise
    
    def _dict_to_protobuf(self, data: Dict[str, Any]) -> 'google.protobuf.message.Message':
        """Convert dictionary to protobuf message."""
        data_type = data.get('type', 'MarketTick')
        
        if data_type not in self._message_classes:
            raise ValueError(f"Unknown data type: {data_type}")
        
        message_class = self._message_classes[data_type]
        protobuf_message = message_class()
        
        # Map fields based on data type
        if data_type == 'MarketTick':
            self._populate_market_tick(protobuf_message, data)
        elif data_type == 'NewsArticle':
            self._populate_news_article(protobuf_message, data)
        elif data_type == 'SentimentData':
            self._populate_sentiment_data(protobuf_message, data)
        elif data_type == 'MarketDataBatch':
            self._populate_market_data_batch(protobuf_message, data)
        
        return protobuf_message
    
    def _populate_market_tick(self, message, data: Dict[str, Any]):
        """Populate MarketTick protobuf message."""
        if 'symbol' in data:
            message.symbol = data['symbol']
        if 'price' in data:
            message.price = float(data['price'])
        if 'volume' in data:
            message.volume = float(data['volume'])
        if 'timestamp' in data:
            if isinstance(data['timestamp'], str):
                message.timestamp = data['timestamp']
            else:
                message.timestamp = data['timestamp'].isoformat()
        if 'source' in data:
            message.source = data['source']
        if 'change' in data:
            message.change = float(data['change'])
        if 'change_percent' in data:
            message.change_percent = float(data['change_percent'])
    
    def _populate_news_article(self, message, data: Dict[str, Any]):
        """Populate NewsArticle protobuf message."""
        if 'id' in data:
            message.id = data['id']
        if 'title' in data:
            message.title = data['title']
        if 'content' in data:
            message.content = data['content']
        if 'source' in data:
            message.source = data['source']
        if 'author' in data:
            message.author = data['author']
        if 'published_at' in data:
            if isinstance(data['published_at'], str):
                message.published_at = data['published_at']
            else:
                message.published_at = data['published_at'].isoformat()
        if 'url' in data:
            message.url = data['url']
        if 'sentiment' in data:
            message.sentiment = data['sentiment']
    
    def _populate_sentiment_data(self, message, data: Dict[str, Any]):
        """Populate SentimentData protobuf message."""
        if 'symbol' in data:
            message.symbol = data['symbol']
        if 'sentiment' in data:
            message.sentiment = data['sentiment']
        if 'score' in data:
            message.score = float(data['score'])
        if 'confidence' in data:
            message.confidence = float(data['confidence'])
        if 'timestamp' in data:
            if isinstance(data['timestamp'], str):
                message.timestamp = data['timestamp']
            else:
                message.timestamp = data['timestamp'].isoformat()
        if 'source' in data:
            message.source = data['source']
    
    def _populate_market_data_batch(self, message, data: Dict[str, Any]):
        """Populate MarketDataBatch protobuf message."""
        if 'batch_id' in data:
            message.batch_id = data['batch_id']
        if 'timestamp' in data:
            if isinstance(data['timestamp'], str):
                message.timestamp = data['timestamp']
            else:
                message.timestamp = data['timestamp'].isoformat()
        
        if 'items' in data:
            for item in data['items']:
                item_message = message.items.add()
                self._populate_market_tick(item_message, item)
    
    def _protobuf_to_dict(self, protobuf_message: 'google.protobuf.message.Message') -> Dict[str, Any]:
        """Convert protobuf message to dictionary."""
        try:
            # Use protobuf's built-in conversion
            return google.protobuf.json_format.MessageToDict(
                protobuf_message,
                preserving_proto_field_name=True,
                including_default_value_fields=True
            )
        except Exception as e:
            self.logger.error(f"Protobuf to dict conversion failed: {e}")
            # Fallback to manual conversion
            return self._manual_protobuf_to_dict(protobuf_message)
    
    def _manual_protobuf_to_dict(self, protobuf_message) -> Dict[str, Any]:
        """Manual protobuf to dict conversion fallback."""
        result = {}
        
        for field in protobuf_message.DESCRIPTOR.fields:
            value = getattr(protobuf_message, field.name)
            
            if value is not None and value != field.default_value:
                if field.message_type:
                    # Nested message
                    result[field.name] = self._protobuf_to_dict(value)
                elif field.label == field.LABEL_REPEATED:
                    # Repeated field
                    result[field.name] = [self._convert_field_value(v) for v in value]
                else:
                    # Simple field
                    result[field.name] = self._convert_field_value(value)
        
        return result
    
    def _convert_field_value(self, value):
        """Convert protobuf field value to Python type."""
        if hasattr(value, 'DESCRIPTOR'):
            # Nested message
            return self._protobuf_to_dict(value)
        elif isinstance(value, list):
            return [self._convert_field_value(v) for v in value]
        else:
            return value
    
    def _detect_message_type(self, data: bytes) -> str:
        """Detect protobuf message type from bytes."""
        # This is a simplified detection - in production, you might use
        # message type prefixes or a registry
        try:
            # Try to parse as each message type
            for message_type, message_class in self._message_classes.items():
                try:
                    message = message_class()
                    message.ParseFromString(data)
                    return message_type
                except:
                    continue
        except:
            pass
        
        # Default to MarketTick
        return 'MarketTick'
    
    def get_format(self) -> SerializationFormat:
        """Get serialization format."""
        return SerializationFormat.PROTOBUF


class MsgpackSerializer(BaseSerializer):
    """
    MessagePack serializer for efficient binary serialization.
    
    Features:
    - Compact binary format
    - Fast serialization/deserialization
    - Compatible with many languages
    - Good for real-time data
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        if not MSGPACK_AVAILABLE:
            raise ImportError("msgpack package is required. Install with: pip install msgpack")
        
        self.logger = logger or logging.getLogger("MsgpackSerializer")
    
    def serialize(self, data: Any) -> SerializationResult:
        """Serialize data using MessagePack."""
        import time
        start_time = time.time()
        
        try:
            # Convert datetime objects to ISO strings
            processed_data = self._preprocess_data(data)
            
            # Serialize to bytes
            serialized_data = msgpack.packb(processed_data, use_bin_type=True)
            
            serialization_time = (time.time() - start_time) * 1000
            
            # Calculate compression ratio compared to JSON
            json_data = json.dumps(processed_data).encode('utf-8')
            compression_ratio = len(serialized_data) / len(json_data)
            
            return SerializationResult(
                data=serialized_data,
                format=SerializationFormat.MSGPACK,
                size_bytes=len(serialized_data),
                compression_ratio=compression_ratio,
                serialization_time_ms=serialization_time
            )
            
        except Exception as e:
            self.logger.error(f"Msgpack serialization failed: {e}")
            raise
    
    def deserialize(self, data: bytes, target_type: Optional[Type] = None) -> Any:
        """Deserialize bytes using MessagePack."""
        try:
            deserialized_data = msgpack.unpackb(data, raw=False, strict_map_key=False)
            
            # Post-process data
            return self._postprocess_data(deserialized_data)
            
        except Exception as e:
            self.logger.error(f"Msgpack deserialization failed: {e}")
            raise
    
    def _preprocess_data(self, data: Any) -> Any:
        """Preprocess data for MessagePack serialization."""
        if isinstance(data, dict):
            processed = {}
            for key, value in data.items():
                processed[key] = self._preprocess_data(value)
            return processed
        elif isinstance(data, list):
            return [self._preprocess_data(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, uuid.UUID):
            return str(data)
        else:
            return data
    
    def _postprocess_data(self, data: Any) -> Any:
        """Post-process data after MessagePack deserialization."""
        if isinstance(data, dict):
            processed = {}
            for key, value in data.items():
                processed[key] = self._postprocess_data(value)
            return processed
        elif isinstance(data, list):
            return [self._postprocess_data(item) for item in data]
        elif isinstance(data, str):
            # Try to parse as datetime
            try:
                return datetime.fromisoformat(data.replace('Z', '+00:00'))
            except:
                return data
        else:
            return data
    
    def get_format(self) -> SerializationFormat:
        """Get serialization format."""
        return SerializationFormat.MSGPACK


class JsonSerializer(BaseSerializer):
    """
    JSON serializer for compatibility and debugging.
    
    Features:
    - Human readable
    - Widely supported
    - Good for debugging
    - Larger payload size
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("JsonSerializer")
    
    def serialize(self, data: Any) -> SerializationResult:
        """Serialize data using JSON."""
        import time
        start_time = time.time()
        
        try:
            # Convert datetime objects to ISO strings
            processed_data = self._preprocess_data(data)
            
            # Serialize to bytes
            json_str = json.dumps(processed_data, separators=(',', ':'), ensure_ascii=False)
            serialized_data = json_str.encode('utf-8')
            
            serialization_time = (time.time() - start_time) * 1000
            
            return SerializationResult(
                data=serialized_data,
                format=SerializationFormat.JSON,
                size_bytes=len(serialized_data),
                serialization_time_ms=serialization_time
            )
            
        except Exception as e:
            self.logger.error(f"JSON serialization failed: {e}")
            raise
    
    def deserialize(self, data: bytes, target_type: Optional[Type] = None) -> Any:
        """Deserialize bytes using JSON."""
        try:
            json_str = data.decode('utf-8')
            deserialized_data = json.loads(json_str)
            
            # Post-process data
            return self._postprocess_data(deserialized_data)
            
        except Exception as e:
            self.logger.error(f"JSON deserialization failed: {e}")
            raise
    
    def _preprocess_data(self, data: Any) -> Any:
        """Preprocess data for JSON serialization."""
        if isinstance(data, dict):
            processed = {}
            for key, value in data.items():
                processed[key] = self._preprocess_data(value)
            return processed
        elif isinstance(data, list):
            return [self._preprocess_data(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, uuid.UUID):
            return str(data)
        else:
            return data
    
    def _postprocess_data(self, data: Any) -> Any:
        """Post-process data after JSON deserialization."""
        if isinstance(data, dict):
            processed = {}
            for key, value in data.items():
                processed[key] = self._postprocess_data(value)
            return processed
        elif isinstance(data, list):
            return [self._postprocess_data(item) for item in data]
        elif isinstance(data, str):
            # Try to parse as datetime
            try:
                return datetime.fromisoformat(data.replace('Z', '+00:00'))
            except:
                return data
        else:
            return data
    
    def get_format(self) -> SerializationFormat:
        """Get serialization format."""
        return SerializationFormat.JSON


class SerializationFactory:
    """
    Factory for creating serializers based on format preference.
    """
    
    @staticmethod
    def create_serializer(
        format: SerializationFormat,
        logger: Optional[logging.Logger] = None
    ) -> BaseSerializer:
        """Create serializer for specified format."""
        if format == SerializationFormat.PROTOBUF:
            return ProtobufSerializer(logger)
        elif format == SerializationFormat.MSGPACK:
            return MsgpackSerializer(logger)
        elif format == SerializationFormat.JSON:
            return JsonSerializer(logger)
        else:
            raise ValueError(f"Unsupported serialization format: {format}")
    
    @staticmethod
    def get_best_available_serializer(
        logger: Optional[logging.Logger] = None
    ) -> BaseSerializer:
        """Get best available serializer in order of preference."""
        if PROTOBUF_AVAILABLE:
            return ProtobufSerializer(logger)
        elif MSGPACK_AVAILABLE:
            return MsgpackSerializer(logger)
        else:
            return JsonSerializer(logger)
    
    @staticmethod
    def get_available_formats() -> List[SerializationFormat]:
        """Get list of available serialization formats."""
        formats = [SerializationFormat.JSON]  # Always available
        
        if MSGPACK_AVAILABLE:
            formats.append(SerializationFormat.MSGPACK)
        
        if PROTOBUF_AVAILABLE:
            formats.append(SerializationFormat.PROTOBUF)
        
        return formats


# Performance comparison utilities
class SerializationBenchmark:
    """Benchmark different serialization formats."""
    
    @staticmethod
    async def benchmark_serializers(
        test_data: List[Dict[str, Any]],
        iterations: int = 1000
    ) -> Dict[str, Dict[str, Any]]:
        """Benchmark different serialization formats."""
        import time
        
        results = {}
        available_formats = SerializationFactory.get_available_formats()
        
        for format_enum in available_formats:
            try:
                serializer = SerializationFactory.create_serializer(format_enum)
                
                # Warm up
                for data in test_data[:10]:
                    serializer.serialize(data)
                
                # Benchmark serialization
                serialize_times = []
                sizes = []
                
                for _ in range(iterations):
                    data = test_data[_ % len(test_data)]
                    
                    start_time = time.time()
                    result = serializer.serialize(data)
                    end_time = time.time()
                    
                    serialize_times.append((end_time - start_time) * 1000)
                    sizes.append(result.size_bytes)
                
                # Benchmark deserialization
                deserialize_times = []
                
                for _ in range(iterations):
                    data = test_data[_ % len(test_data)]
                    serialized = serializer.serialize(data)
                    
                    start_time = time.time()
                    serializer.deserialize(serialized.data)
                    end_time = time.time()
                    
                    deserialize_times.append((end_time - start_time) * 1000)
                
                results[format_enum.value] = {
                    'avg_serialize_time_ms': sum(serialize_times) / len(serialize_times),
                    'avg_deserialize_time_ms': sum(deserialize_times) / len(deserialize_times),
                    'avg_size_bytes': sum(sizes) / len(sizes),
                    'min_size_bytes': min(sizes),
                    'max_size_bytes': max(sizes),
                    'compression_ratio_vs_json': None  # Will be calculated later
                }
                
            except Exception as e:
                results[format_enum.value] = {'error': str(e)}
        
        # Calculate compression ratios
        if SerializationFormat.JSON.value in results:
            json_size = results[SerializationFormat.JSON.value]['avg_size_bytes']
            
            for format_name, result in results.items():
                if 'avg_size_bytes' in result:
                    result['compression_ratio_vs_json'] = result['avg_size_bytes'] / json_size
        
        return results
