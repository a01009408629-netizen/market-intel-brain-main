"""
Enterprise Data Pipeline & Processing System
Message queues, stream processing, ETL/ELT processes, and real-time data synchronization
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
from abc import ABC, abstractmethod
import aiofiles
from pathlib import Path
import pickle
import zlib
import hashlib
from concurrent.futures import ThreadPoolExecutor
import aioredis
import aio_pika
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Message types for data pipeline."""
    MARKET_DATA = "market_data"
    NEWS_DATA = "news_data"
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"
    ALERT = "alert"
    COMMAND = "command"


class ProcessingStatus(Enum):
    """Processing status for data pipeline."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class PipelineMessage:
    """Pipeline message structure."""
    id: str
    type: MessageType
    data: Dict[str, Any]
    timestamp: datetime
    source: str
    destination: Optional[str] = None
    priority: int = 0
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            **asdict(self),
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PipelineMessage':
        """Create from dictionary."""
        data["type"] = MessageType(data["type"])
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class ProcessingResult:
    """Processing result structure."""
    message_id: str
    status: ProcessingStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DataProcessor(ABC):
    """Abstract base class for data processors."""
    
    @abstractmethod
    async def process(self, message: PipelineMessage) -> ProcessingResult:
        """Process pipeline message."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get processor name."""
        pass


class MarketDataProcessor(DataProcessor):
    """Market data processor."""
    
    def __init__(self):
        self.processed_count = 0
        self.error_count = 0
    
    def get_name(self) -> str:
        return "market_data_processor"
    
    async def process(self, message: PipelineMessage) -> ProcessingResult:
        """Process market data message."""
        start_time = time.time()
        
        try:
            if message.type != MessageType.MARKET_DATA:
                return ProcessingResult(
                    message_id=message.id,
                    status=ProcessingStatus.FAILED,
                    error="Invalid message type for market data processor"
                )
            
            data = message.data
            
            # Validate market data
            if not self._validate_market_data(data):
                return ProcessingResult(
                    message_id=message.id,
                    status=ProcessingStatus.FAILED,
                    error="Invalid market data format"
                )
            
            # Process market data
            processed_data = await self._process_market_data(data)
            
            processing_time = time.time() - start_time
            self.processed_count += 1
            
            return ProcessingResult(
                message_id=message.id,
                status=ProcessingStatus.COMPLETED,
                result=processed_data,
                processing_time=processing_time
            )
            
        except Exception as e:
            self.error_count += 1
            processing_time = time.time() - start_time
            
            return ProcessingResult(
                message_id=message.id,
                status=ProcessingStatus.FAILED,
                error=str(e),
                processing_time=processing_time
            )
    
    def _validate_market_data(self, data: Dict[str, Any]) -> bool:
        """Validate market data format."""
        required_fields = ["symbol", "price", "timestamp", "volume"]
        return all(field in data for field in required_fields)
    
    async def _process_market_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process market data."""
        # Add processing metadata
        processed_data = {
            **data,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "price_change": 0.0,  # Calculate from previous price
            "volume_change": 0.0,  # Calculate from previous volume
            "market_cap": data.get("price", 0) * data.get("volume", 0),
            "processed_by": self.get_name()
        }
        
        return processed_data


class NewsDataProcessor(DataProcessor):
    """News data processor."""
    
    def __init__(self):
        self.processed_count = 0
        self.error_count = 0
    
    def get_name(self) -> str:
        return "news_data_processor"
    
    async def process(self, message: PipelineMessage) -> ProcessingResult:
        """Process news data message."""
        start_time = time.time()
        
        try:
            if message.type != MessageType.NEWS_DATA:
                return ProcessingResult(
                    message_id=message.id,
                    status=ProcessingStatus.FAILED,
                    error="Invalid message type for news data processor"
                )
            
            data = message.data
            
            # Validate news data
            if not self._validate_news_data(data):
                return ProcessingResult(
                    message_id=message.id,
                    status=ProcessingStatus.FAILED,
                    error="Invalid news data format"
                )
            
            # Process news data
            processed_data = await self._process_news_data(data)
            
            processing_time = time.time() - start_time
            self.processed_count += 1
            
            return ProcessingResult(
                message_id=message.id,
                status=ProcessingStatus.COMPLETED,
                result=processed_data,
                processing_time=processing_time
            )
            
        except Exception as e:
            self.error_count += 1
            processing_time = time.time() - start_time
            
            return ProcessingResult(
                message_id=message.id,
                status=ProcessingStatus.FAILED,
                error=str(e),
                processing_time=processing_time
            )
    
    def _validate_news_data(self, data: Dict[str, Any]) -> bool:
        """Validate news data format."""
        required_fields = ["title", "content", "source", "timestamp"]
        return all(field in data for field in required_fields)
    
    async def _process_news_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process news data."""
        # Add processing metadata
        processed_data = {
            **data,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "sentiment_score": 0.0,  # Calculate sentiment
            "relevance_score": 0.0,  # Calculate relevance
            "keywords": [],  # Extract keywords
            "processed_by": self.get_name()
        }
        
        return processed_data


class EnterpriseMessageQueue:
    """Enterprise message queue with Redis and RabbitMQ support."""
    
    def __init__(self, queue_type: str = "redis", **kwargs):
        self.queue_type = queue_type
        self.kwargs = kwargs
        self.connection = None
        self.channel = None
        self.queues = {}
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0
        }
    
    async def initialize(self):
        """Initialize message queue."""
        try:
            if self.queue_type == "redis":
                await self._initialize_redis()
            elif self.queue_type == "rabbitmq":
                await self._initialize_rabbitmq()
            else:
                raise ValueError(f"Unsupported queue type: {self.queue_type}")
            
            logger.info(f"✅ Message queue initialized ({self.queue_type})")
            
        except Exception as e:
            logger.error(f"❌ Message queue initialization failed: {e}")
            raise
    
    async def _initialize_redis(self):
        """Initialize Redis message queue."""
        redis_url = self.kwargs.get("redis_url", "redis://localhost:6379")
        self.connection = aioredis.from_url(redis_url)
        await self.connection.ping()
    
    async def _initialize_rabbitmq(self):
        """Initialize RabbitMQ message queue."""
        connection_url = self.kwargs.get("rabbitmq_url", "amqp://localhost:5672")
        self.connection = await aio_pika.connect_robust(connection_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)
    
    async def send_message(self, queue_name: str, message: PipelineMessage):
        """Send message to queue."""
        try:
            message_data = message.to_dict()
            
            if self.queue_type == "redis":
                await self.connection.lpush(queue_name, json.dumps(message_data))
            elif self.queue_type == "rabbitmq":
                if queue_name not in self.queues:
                    self.queues[queue_name] = await self.channel.declare_queue(
                        queue_name, durable=True
                    )
                
                await self.channel.default_exchange.publish(
                    aio_pika.Message(
                        json.dumps(message_data).encode(),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                    ),
                    routing_key=queue_name
                )
            
            self.stats["messages_sent"] += 1
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Failed to send message to {queue_name}: {e}")
            raise
    
    async def receive_message(self, queue_name: str) -> Optional[PipelineMessage]:
        """Receive message from queue."""
        try:
            if self.queue_type == "redis":
                message_data = await self.connection.brpop(queue_name, timeout=1)
                if message_data:
                    message_json = message_data[1]
                    message = PipelineMessage.from_dict(json.loads(message_json))
                    self.stats["messages_received"] += 1
                    return message
                    
            elif self.queue_type == "rabbitmq":
                if queue_name not in self.queues:
                    self.queues[queue_name] = await self.channel.declare_queue(
                        queue_name, durable=True
                    )
                
                message = await self.queues[queue_name].get(timeout=1)
                if message:
                    message.ack()
                    message_data = json.loads(message.body.decode())
                    message_obj = PipelineMessage.from_dict(message_data)
                    self.stats["messages_received"] += 1
                    return message_obj
            
            return None
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Failed to receive message from {queue_name}: {e}")
            return None
    
    async def close(self):
        """Close message queue connection."""
        try:
            if self.queue_type == "redis" and self.connection:
                await self.connection.close()
            elif self.queue_type == "rabbitmq" and self.connection:
                await self.connection.close()
            
            logger.info("Message queue connection closed")
            
        except Exception as e:
            logger.error(f"Error closing message queue: {e}")


class EnterpriseDataPipeline:
    """Enterprise data pipeline with multiple processors and queues."""
    
    def __init__(self):
        self.processors: Dict[str, DataProcessor] = {}
        self.queues: Dict[str, EnterpriseMessageQueue] = {}
        self.running = False
        self.tasks = []
        self.stats = {
            "total_processed": 0,
            "total_failed": 0,
            "processing_time_total": 0.0,
            "processor_stats": {}
        }
    
    def add_processor(self, processor: DataProcessor):
        """Add data processor."""
        self.processors[processor.get_name()] = processor
        self.stats["processor_stats"][processor.get_name()] = {
            "processed": 0,
            "failed": 0,
            "avg_processing_time": 0.0
        }
        logger.info(f"Added processor: {processor.get_name()}")
    
    def add_queue(self, name: str, queue: EnterpriseMessageQueue):
        """Add message queue."""
        self.queues[name] = queue
        logger.info(f"Added queue: {name}")
    
    async def initialize(self):
        """Initialize all components."""
        try:
            # Initialize queues
            for name, queue in self.queues.items():
                await queue.initialize()
            
            logger.info("✅ Enterprise Data Pipeline initialized")
            
        except Exception as e:
            logger.error(f"❌ Data pipeline initialization failed: {e}")
            raise
    
    async def start_processing(self):
        """Start data processing."""
        if self.running:
            return
        
        self.running = True
        
        # Start processing tasks for each queue
        for queue_name in self.queues.keys():
            task = asyncio.create_task(self._process_queue(queue_name))
            self.tasks.append(task)
        
        logger.info("Data processing started")
    
    async def stop_processing(self):
        """Stop data processing."""
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        logger.info("Data processing stopped")
    
    async def _process_queue(self, queue_name: str):
        """Process messages from queue."""
        queue = self.queues[queue_name]
        
        while self.running:
            try:
                # Receive message
                message = await queue.receive_message(queue_name)
                if not message:
                    await asyncio.sleep(0.1)
                    continue
                
                # Process message
                await self._process_message(message)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing queue {queue_name}: {e}")
                await asyncio.sleep(1)
    
    async def _process_message(self, message: PipelineMessage):
        """Process single message."""
        try:
            # Select appropriate processor
            processor_name = None
            if message.type == MessageType.MARKET_DATA:
                processor_name = "market_data_processor"
            elif message.type == MessageType.NEWS_DATA:
                processor_name = "news_data_processor"
            
            if not processor_name or processor_name not in self.processors:
                logger.warning(f"No processor found for message type: {message.type}")
                return
            
            processor = self.processors[processor_name]
            
            # Process message
            result = await processor.process(message)
            
            # Update statistics
            self.stats["total_processed"] += 1
            self.stats["processing_time_total"] += result.processing_time
            
            processor_stats = self.stats["processor_stats"][processor_name]
            if result.status == ProcessingStatus.COMPLETED:
                processor_stats["processed"] += 1
            else:
                processor_stats["failed"] += 1
                self.stats["total_failed"] += 1
            
            # Update average processing time
            total_processed = processor_stats["processed"] + processor_stats["failed"]
            if total_processed > 0:
                processor_stats["avg_processing_time"] = (
                    self.stats["processing_time_total"] / total_processed
                )
            
            # Log processing result
            if result.status == ProcessingStatus.COMPLETED:
                logger.debug(f"Processed message {message.id} in {result.processing_time:.3f}s")
            else:
                logger.error(f"Failed to process message {message.id}: {result.error}")
            
        except Exception as e:
            logger.error(f"Error processing message {message.id}: {e}")
            self.stats["total_failed"] += 1
    
    async def send_message(self, queue_name: str, message: PipelineMessage):
        """Send message to queue."""
        if queue_name not in self.queues:
            raise ValueError(f"Queue {queue_name} not found")
        
        await self.queues[queue_name].send_message(queue_name, message)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        total_messages = self.stats["total_processed"] + self.stats["total_failed"]
        success_rate = (self.stats["total_processed"] / total_messages * 100) if total_messages > 0 else 0
        
        return {
            **self.stats,
            "success_rate_percent": round(success_rate, 2),
            "avg_processing_time": (
                self.stats["processing_time_total"] / total_messages
                if total_messages > 0 else 0
            ),
            "queue_stats": {
                name: queue.stats for name, queue in self.queues.items()
            }
        }
    
    async def close(self):
        """Close all components."""
        await self.stop_processing()
        
        for queue in self.queues.values():
            await queue.close()
        
        logger.info("Data pipeline closed")


# Global instances
enterprise_pipeline = None


async def initialize_data_pipeline():
    """Initialize enterprise data pipeline."""
    global enterprise_pipeline
    
    try:
        # Create pipeline
        enterprise_pipeline = EnterpriseDataPipeline()
        
        # Add processors
        enterprise_pipeline.add_processor(MarketDataProcessor())
        enterprise_pipeline.add_processor(NewsDataProcessor())
        
        # Add queues
        redis_queue = EnterpriseMessageQueue("redis", redis_url="redis://localhost:6379")
        enterprise_pipeline.add_queue("market_data", redis_queue)
        enterprise_pipeline.add_queue("news_data", redis_queue)
        enterprise_pipeline.add_queue("user_actions", redis_queue)
        
        # Initialize and start
        await enterprise_pipeline.initialize()
        await enterprise_pipeline.start_processing()
        
        logger.info("✅ Enterprise Data Pipeline system initialized")
        
    except Exception as e:
        logger.error(f"❌ Data Pipeline system initialization failed: {e}")
        raise


async def cleanup_data_pipeline():
    """Cleanup data pipeline resources."""
    global enterprise_pipeline
    
    if enterprise_pipeline:
        await enterprise_pipeline.close()
        logger.info("✅ Enterprise Data Pipeline system cleaned up")
