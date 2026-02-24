"""
MAIFA v3 Distributed State Management
Redis Cluster-based distributed state with atomicity, replication, and failover
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.asyncio import RedisCluster
from redis.exceptions import RedisError, ConnectionError, ClusterError

from utils.logger import get_logger
from utils.helpers import TimeHelper, SerializationHelper

logger = get_logger("distributed_state")

@dataclass
class StateConfig:
    """Configuration for distributed state management"""
    redis_nodes: List[str]
    password: Optional[str] = None
    max_connections: int = 100
    retry_attempts: int = 3
    retry_delay: float = 0.1
    ttl_default: int = 3600  # 1 hour
    cluster_enabled: bool = True

class DistributedStateManager:
    """
    High-performance distributed state manager with Redis Cluster
    
    Features:
    - Redis Cluster for horizontal scaling
    - Automatic failover and replication
    - Atomic operations with transactions
    - Connection pooling and optimization
    - Health monitoring and recovery
    """
    
    def __init__(self, config: StateConfig):
        self.config = config
        self.logger = get_logger("DistributedStateManager")
        self.redis_cluster: Optional[RedisCluster] = None
        self.connection_pool = None
        self.health_checker = None
        self.is_healthy = False
        self.last_health_check = 0.0
        
        # Performance metrics
        self.metrics = {
            "operations_total": 0,
            "operations_success": 0,
            "operations_failed": 0,
            "avg_latency": 0.0,
            "connection_errors": 0,
            "cluster_failures": 0
        }
    
    async def initialize(self) -> bool:
        """Initialize Redis Cluster with connection pooling"""
        try:
            self.logger.info("🔧 Initializing Redis Cluster...")
            
            # Create connection pool
            self.connection_pool = redis.ConnectionPool.from_url(
                self.config.redis_nodes[0] if len(self.config.redis_nodes) == 1 else None,
                max_connections=self.config.max_connections,
                retry_on_timeout=True,
                retry_on_error=[ConnectionError, ClusterError],
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            if self.config.cluster_enabled and len(self.config.redis_nodes) > 1:
                # Initialize Redis Cluster
                self.redis_cluster = RedisCluster(
                    startup_nodes=self._get_startup_nodes(),
                    password=self.config.password,
                    max_connections=self.config.max_connections,
                    decode_responses=True,
                    skip_full_coverage_check=True,
                    health_check_interval=30
                )
            else:
                # Single Redis instance
                self.redis_cluster = redis.Redis(
                    connection_pool=self.connection_pool,
                    decode_responses=True,
                    password=self.config.password
                )
            
            # Test connection
            await self._test_connection()
            
            # Start health monitoring
            self.health_checker = asyncio.create_task(self._health_monitoring_loop())
            
            self.is_healthy = True
            self.logger.info("✅ Redis Cluster initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Redis Cluster initialization failed: {e}")
            self.is_healthy = False
            return False
    
    def _get_startup_nodes(self) -> List[Dict[str, Any]]:
        """Get startup nodes for Redis Cluster"""
        nodes = []
        for node in self.config.redis_nodes:
            if ':' in node:
                host, port = node.split(':')
                nodes.append({"host": host, "port": int(port)})
            else:
                nodes.append({"host": node, "port": 6379})
        return nodes
    
    async def _test_connection(self):
        """Test Redis connection and cluster health"""
        try:
            # Test basic operations
            await self.redis_cluster.ping()
            
            # Test cluster info if available
            if hasattr(self.redis_cluster, 'cluster_info'):
                cluster_info = await self.redis_cluster.cluster_info()
                self.logger.info(f"📊 Cluster Info: {cluster_info}")
            
            # Test set/get operations
            test_key = "maifa:health:test"
            await self.redis_cluster.setex(test_key, 10, "ok")
            result = await self.redis_cluster.get(test_key)
            await self.redis_cluster.delete(test_key)
            
            if result != "ok":
                raise Exception("Redis test operation failed")
            
            self.logger.info("✅ Redis connection test passed")
            
        except Exception as e:
            self.logger.error(f"❌ Redis connection test failed: {e}")
            raise
    
    async def set_state(self, 
                       key: str, 
                       value: Any, 
                       ttl: Optional[int] = None,
                       atomic: bool = True) -> bool:
        """
        Set state with atomicity and optional TTL
        
        Args:
            key: State key (supports hierarchical keys like "agent:123:state")
            value: State value (any serializable object)
            ttl: Time to live in seconds (default from config)
            atomic: Use atomic operation (default: True)
        """
        start_time = time.time()
        
        try:
            # Serialize value
            serialized_value = SerializationHelper.serialize(value)
            
            # Set with TTL
            actual_ttl = ttl or self.config.ttl_default
            
            if atomic:
                # Use atomic SET with EX
                success = await self.redis_cluster.setex(
                    f"maifa:{key}", 
                    actual_ttl, 
                    serialized_value
                )
            else:
                # Regular SET
                success = await self.redis_cluster.set(
                    f"maifa:{key}", 
                    serialized_value, 
                    ex=actual_ttl
                )
            
            # Update metrics
            self._update_metrics(time.time() - start_time, True)
            
            self.logger.debug(f"📝 State set: {key} (TTL: {actual_ttl}s)")
            return success
            
        except Exception as e:
            self._update_metrics(time.time() - start_time, False)
            self.logger.error(f"❌ Failed to set state {key}: {e}")
            return False
    
    async def get_state(self, key: str, default: Any = None) -> Any:
        """
        Get state value with deserialization
        
        Args:
            key: State key
            default: Default value if key doesn't exist
            
        Returns:
            Deserialized state value or default
        """
        start_time = time.time()
        
        try:
            # Get from Redis
            value = await self.redis_cluster.get(f"maifa:{key}")
            
            if value is None:
                self.logger.debug(f"📭 State not found: {key}")
                return default
            
            # Deserialize value
            deserialized_value = SerializationHelper.deserialize(value)
            
            # Update metrics
            self._update_metrics(time.time() - start_time, True)
            
            self.logger.debug(f"📖 State retrieved: {key}")
            return deserialized_value
            
        except Exception as e:
            self._update_metrics(time.time() - start_time, False)
            self.logger.error(f"❌ Failed to get state {key}: {e}")
            return default
    
    async def delete_state(self, key: str) -> bool:
        """Delete state key"""
        start_time = time.time()
        
        try:
            result = await self.redis_cluster.delete(f"maifa:{key}")
            
            # Update metrics
            self._update_metrics(time.time() - start_time, True)
            
            self.logger.debug(f"🗑️ State deleted: {key}")
            return result > 0
            
        except Exception as e:
            self._update_metrics(time.time() - start_time, False)
            self.logger.error(f"❌ Failed to delete state {key}: {e}")
            return False
    
    async def atomic_transaction(self, 
                              operations: List[Dict[str, Any]]) -> bool:
        """
        Execute atomic transaction with multiple operations
        
        Args:
            operations: List of operations like [{"type": "set", "key": "...", "value": "..."}, ...]
            
        Returns:
            True if transaction succeeded, False otherwise
        """
        start_time = time.time()
        
        try:
            # Create pipeline for atomic execution
            pipe = self.redis_cluster.pipeline()
            
            for op in operations:
                op_type = op.get("type")
                key = f"maifa:{op.get('key')}"
                
                if op_type == "set":
                    value = SerializationHelper.serialize(op.get("value"))
                    ttl = op.get("ttl", self.config.ttl_default)
                    pipe.setex(key, ttl, value)
                elif op_type == "delete":
                    pipe.delete(key)
                elif op_type == "increment":
                    pipe.incrby(key, op.get("amount", 1))
                elif op_type == "hset":
                    field = op.get("field")
                    value = SerializationHelper.serialize(op.get("value"))
                    pipe.hset(key, field, value)
                else:
                    self.logger.warning(f"Unknown operation type: {op_type}")
            
            # Execute transaction atomically
            results = await pipe.execute()
            
            # Check if all operations succeeded
            success = all(result is not None and result is not False for result in results)
            
            # Update metrics
            self._update_metrics(time.time() - start_time, success)
            
            self.logger.info(f"🔄 Atomic transaction: {len(operations)} ops, success: {success}")
            return success
            
        except Exception as e:
            self._update_metrics(time.time() - start_time, False)
            self.logger.error(f"❌ Atomic transaction failed: {e}")
            return False
    
    async def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """Get complete agent state including metadata"""
        try:
            # Get agent state keys
            state_keys = [
                f"agent:{agent_id}:state",
                f"agent:{agent_id}:config",
                f"agent:{agent_id}:metrics",
                f"agent:{agent_id}:health"
            ]
            
            # Pipeline get for efficiency
            pipe = self.redis_cluster.pipeline()
            for key in state_keys:
                pipe.get(f"maifa:{key}")
            
            results = await pipe.execute()
            
            # Deserialize results
            agent_state = {
                "agent_id": agent_id,
                "state": SerializationHelper.deserialize(results[0]) or {},
                "config": SerializationHelper.deserialize(results[1]) or {},
                "metrics": SerializationHelper.deserialize(results[2]) or {},
                "health": SerializationHelper.deserialize(results[3]) or {},
                "last_updated": time.time()
            }
            
            return agent_state
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get agent state {agent_id}: {e}")
            return {"agent_id": agent_id, "error": str(e)}
    
    async def set_agent_state(self, 
                           agent_id: str, 
                           state: Dict[str, Any],
                           ttl: Optional[int] = None) -> bool:
        """Set complete agent state atomically"""
        operations = [
            {
                "type": "set",
                "key": f"agent:{agent_id}:state",
                "value": state,
                "ttl": ttl or self.config.ttl_default
            }
        ]
        
        return await self.atomic_transaction(operations)
    
    async def get_pipeline_state(self, workflow_id: str) -> Dict[str, Any]:
        """Get pipeline workflow state"""
        try:
            # Get all pipeline stage states
            stage_keys = [
                f"pipeline:{workflow_id}:preprocessing",
                f"pipeline:{workflow_id}:classification",
                f"pipeline:{workflow_id}:analysis",
                f"pipeline:{workflow_id}:aggregation",
                f"pipeline:{workflow_id}:metadata"
            ]
            
            pipe = self.redis_cluster.pipeline()
            for key in stage_keys:
                pipe.get(f"maifa:{key}")
            
            results = await pipe.execute()
            
            pipeline_state = {
                "workflow_id": workflow_id,
                "preprocessing": SerializationHelper.deserialize(results[0]) or {},
                "classification": SerializationHelper.deserialize(results[1]) or {},
                "analysis": SerializationHelper.deserialize(results[2]) or {},
                "aggregation": SerializationHelper.deserialize(results[3]) or {},
                "metadata": SerializationHelper.deserialize(results[4]) or {},
                "last_updated": time.time()
            }
            
            return pipeline_state
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get pipeline state {workflow_id}: {e}")
            return {"workflow_id": workflow_id, "error": str(e)}
    
    async def set_pipeline_stage_state(self, 
                                   workflow_id: str,
                                   stage: str,
                                   state: Dict[str, Any],
                                   ttl: Optional[int] = None) -> bool:
        """Set specific pipeline stage state"""
        key = f"pipeline:{workflow_id}:{stage}"
        return await self.set_state(key, state, ttl)
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of distributed state"""
        try:
            start_time = time.time()
            
            # Basic connectivity test
            await self.redis_cluster.ping()
            
            # Memory usage
            info = await self.redis_cluster.info("memory")
            memory_usage = info.get("used_memory_human", "unknown")
            
            # Connected clients
            clients = await self.redis_cluster.info("clients")
            connected_clients = clients.get("connected_clients", 0)
            
            # Cluster info if available
            cluster_info = {}
            if hasattr(self.redis_cluster, 'cluster_info'):
                cluster_info = await self.redis_cluster.cluster_info()
            
            # Test read/write performance
            test_start = time.time()
            await self.redis_cluster.setex("health_test", 10, "test")
            await self.redis_cluster.get("health_test")
            await self.redis_cluster.delete("health_test")
            test_latency = (time.time() - test_start) * 1000  # ms
            
            health_status = {
                "status": "healthy" if self.is_healthy else "unhealthy",
                "latency_ms": round(test_latency, 2),
                "memory_usage": memory_usage,
                "connected_clients": connected_clients,
                "cluster_info": cluster_info,
                "metrics": self.metrics,
                "uptime_seconds": time.time() - self.last_health_check,
                "timestamp": datetime.now().isoformat()
            }
            
            self.last_health_check = time.time()
            return health_status
            
        except Exception as e:
            self.logger.error(f"❌ Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _health_monitoring_loop(self):
        """Background health monitoring"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Perform health check
                health = await self.health_check()
                
                if health["status"] != "healthy":
                    self.is_healthy = False
                    self.logger.warning(f"⚠️ Distributed state unhealthy: {health}")
                else:
                    self.is_healthy = True
                
                # Log metrics periodically
                if int(time.time()) % 300 == 0:  # Every 5 minutes
                    self.logger.info(f"📊 Distributed State Metrics: {self.metrics}")
                
            except Exception as e:
                self.logger.error(f"❌ Health monitoring error: {e}")
                self.is_healthy = False
    
    def _update_metrics(self, latency: float, success: bool):
        """Update performance metrics"""
        self.metrics["operations_total"] += 1
        
        if success:
            self.metrics["operations_success"] += 1
        else:
            self.metrics["operations_failed"] += 1
        
        # Update average latency
        total_ops = self.metrics["operations_total"]
        current_avg = self.metrics["avg_latency"]
        self.metrics["avg_latency"] = (current_avg * (total_ops - 1) + latency) / total_ops
    
    async def cleanup_expired_states(self):
        """Clean up expired state entries"""
        try:
            # Get all MAIFA keys
            keys = await self.redis_cluster.keys("maifa:*")
            expired_keys = []
            
            for key in keys:
                ttl = await self.redis_cluster.ttl(key)
                if ttl == -1:  # No expiry set
                    await self.redis_cluster.expire(key, self.config.ttl_default)
                elif ttl == -2:  # Key expired
                    expired_keys.append(key)
            
            # Delete expired keys
            if expired_keys:
                await self.redis_cluster.delete(*expired_keys)
                self.logger.info(f"🧹 Cleaned {len(expired_keys)} expired state entries")
                
        except Exception as e:
            self.logger.error(f"❌ Cleanup failed: {e}")
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics"""
        return {
            "state_metrics": self.metrics,
            "health_status": "healthy" if self.is_healthy else "unhealthy",
            "last_health_check": self.last_health_check,
            "config": {
                "cluster_enabled": self.config.cluster_enabled,
                "max_connections": self.config.max_connections,
                "ttl_default": self.config.ttl_default
            }
        }
    
    async def shutdown(self):
        """Graceful shutdown"""
        try:
            self.logger.info("🛑 Shutting down distributed state manager...")
            
            # Cancel health monitoring
            if self.health_checker:
                self.health_checker.cancel()
            
            # Close Redis connections
            if self.redis_cluster:
                await self.redis_cluster.close()
            
            if self.connection_pool:
                await self.connection_pool.disconnect()
            
            self.logger.info("✅ Distributed state manager shutdown complete")
            
        except Exception as e:
            self.logger.error(f"❌ Shutdown error: {e}")


# Global distributed state manager instance
distributed_state_config = StateConfig(
    redis_nodes=["redis://localhost:6379"],  # Configure for your environment
    password=None,
    max_connections=100,
    cluster_enabled=True
)

distributed_state_manager = DistributedStateManager(distributed_state_config)
