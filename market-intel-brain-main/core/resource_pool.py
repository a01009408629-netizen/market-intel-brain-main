"""
MAIFA v3 Resource Pooling & I/O Optimization
Advanced connection pooling, rate limiting, and resource management
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import aiohttp
import asyncpg
import redis.asyncio as redis

from core.distributed_state import distributed_state_manager
from utils.logger import get_logger

logger = get_logger("resource_pool")

class ResourceType(Enum):
    HTTP_CONNECTION = "http_connection"
    DATABASE_CONNECTION = "database_connection"
    REDIS_CONNECTION = "redis_connection"
    API_TOKEN = "api_token"
    BUFFER = "buffer"

@dataclass
class PoolConfig:
    max_size: int = 100
    min_size: int = 5
    max_idle_time: float = 300.0
    connection_timeout: float = 10.0
    read_timeout: float = 30.0
    write_timeout: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0

class ResourcePool:
    def __init__(self, resource_type: ResourceType, config: PoolConfig):
        self.resource_type = resource_type
        self.config = config
        self.logger = get_logger(f"ResourcePool.{resource_type.value}")
        self.pool = asyncio.Queue(maxsize=config.max_size)
        self.active_connections = 0
        self.total_created = 0
        self.total_destroyed = 0
        self.last_cleanup = time.time()
        
    async def acquire(self, timeout: Optional[float] = None) -> Any:
        try:
            # Try to get from pool
            resource = await asyncio.wait_for(self.pool.get(), timeout=timeout or self.config.connection_timeout)
            self.active_connections += 1
            return resource
        except asyncio.TimeoutError:
            # Create new connection if pool is empty
            if self.total_created - self.total_destroyed < self.config.max_size:
                resource = await self._create_resource()
                self.active_connections += 1
                self.total_created += 1
                return resource
            else:
                raise ResourceExhaustedException(f"Resource pool exhausted: {self.resource_type.value}")
    
    async def release(self, resource):
        try:
            # Validate resource is still valid
            if await self._is_resource_valid(resource):
                await self.pool.put(resource)
            else:
                await self._destroy_resource(resource)
                self.total_destroyed += 1
            self.active_connections -= 1
        except Exception as e:
            self.logger.error(f"Error releasing resource: {e}")
            await self._destroy_resource(resource)
            self.total_destroyed += 1
            self.active_connections -= 1
    
    async def _create_resource(self):
        if self.resource_type == ResourceType.HTTP_CONNECTION:
            connector = aiohttp.TCPConnector(
                limit=self.config.max_size,
                limit_per_host=20,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            return aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(
                    total=self.config.connection_timeout,
                    connect=self.config.connection_timeout,
                    sock_read=self.config.read_timeout
                )
            )
        elif self.resource_type == ResourceType.REDIS_CONNECTION:
            return redis.Redis(
                connection_pool=redis.ConnectionPool(
                    max_connections=self.config.max_size,
                    retry_on_timeout=True
                )
            )
        else:
            raise ValueError(f"Unsupported resource type: {self.resource_type}")
    
    async def _is_resource_valid(self, resource) -> bool:
        if self.resource_type == ResourceType.HTTP_CONNECTION:
            return not resource.closed
        elif self.resource_type == ResourceType.REDIS_CONNECTION:
            try:
                await resource.ping()
                return True
            except:
                return False
        return True
    
    async def _destroy_resource(self, resource):
        if self.resource_type == ResourceType.HTTP_CONNECTION:
            await resource.close()
        elif self.resource_type == ResourceType.REDIS_CONNECTION:
            await resource.close()

class ResourceExhaustedException(Exception):
    pass

# Global resource pools
resource_pools: Dict[ResourceType, ResourcePool] = {}

async def initialize_resource_pools():
    configs = {
        ResourceType.HTTP_CONNECTION: PoolConfig(max_size=50, min_size=5),
        ResourceType.REDIS_CONNECTION: PoolConfig(max_size=20, min_size=2)
    }
    
    for resource_type, config in configs.items():
        pool = ResourcePool(resource_type, config)
        resource_pools[resource_type] = pool
        logger.info(f"Initialized resource pool: {resource_type.value}")

async def get_http_session() -> aiohttp.ClientSession:
    return await resource_pools[ResourceType.HTTP_CONNECTION].acquire()

async def release_http_session(session: aiohttp.ClientSession):
    await resource_pools[ResourceType.HTTP_CONNECTION].release(session)

async def get_redis_connection():
    return await resource_pools[ResourceType.REDIS_CONNECTION].acquire()

async def release_redis_connection(conn):
    await resource_pools[ResourceType.REDIS_CONNECTION].release(conn)
