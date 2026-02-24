"""
Distributed Middleware Layer - Phase 2

Enterprise-grade middleware for decoupling ingestion from AI processing,
ensuring infinite horizontal scalability and 10k+ RPS handling.
"""

from .redis_client import RedisClient, DistributedLock, RateLimiter
from .event_bus import EventBus, Publisher, Subscriber, AckHandler
from .serialization import ProtobufSerializer, MsgpackSerializer

__all__ = [
    # Redis Components
    "RedisClient",
    "DistributedLock", 
    "RateLimiter",
    
    # Event Bus Components
    "EventBus",
    "Publisher",
    "Subscriber", 
    "AckHandler",
    
    # Serialization
    "ProtobufSerializer",
    "MsgpackSerializer"
]
