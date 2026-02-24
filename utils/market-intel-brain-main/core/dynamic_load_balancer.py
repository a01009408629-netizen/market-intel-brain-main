"""
MAIFA v3 Dynamic Load Balancing
Intelligent load distribution with latency-based routing and performance monitoring
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import statistics
import random

from core.distributed_state import distributed_state_manager
from utils.logger import get_logger

logger = get_logger("dynamic_load_balancer")

class LoadBalancingAlgorithm(Enum):
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RESPONSE_TIME_BASED = "response_time_based"
    CONSISTENT_HASH = "consistent_hash"

@dataclass
class NodeMetrics:
    node_id: str
    host: str
    port: int
    active_connections: int = 0
    max_connections: int = 100
    avg_response_time: float = 0.0
    last_response_time: float = 0.0
    success_rate: float = 1.0
    total_requests: int = 0
    failed_requests: int = 0
    last_health_check: float = 0.0
    is_healthy: bool = True
    weight: float = 1.0

class DynamicLoadBalancer:
    def __init__(self, service_name: str, algorithm: LoadBalancingAlgorithm = LoadBalancingAlgorithm.RESPONSE_TIME_BASED):
        self.service_name = service_name
        self.algorithm = algorithm
        self.logger = get_logger(f"LoadBalancer.{service_name}")
        self.nodes: Dict[str, NodeMetrics] = {}
        self.round_robin_index = 0
        self.metrics_update_interval = 30
        self.health_check_interval = 10
        
    async def add_node(self, node_id: str, host: str, port: int, max_connections: int = 100):
        node = NodeMetrics(
            node_id=node_id,
            host=host,
            port=port,
            max_connections=max_connections
        )
        self.nodes[node_id] = node
        await self._persist_node_state(node)
        
    async def select_node(self, request_data: Dict[str, Any] = None) -> Optional[NodeMetrics]:
        healthy_nodes = [n for n in self.nodes.values() if n.is_healthy and n.active_connections < n.max_connections]
        if not healthy_nodes:
            return None
        
        if self.algorithm == LoadBalancingAlgorithm.RESPONSE_TIME_BASED:
            return self._select_by_response_time(healthy_nodes)
        elif self.algorithm == LoadBalancingAlgorithm.LEAST_CONNECTIONS:
            return min(healthy_nodes, key=lambda n: n.active_connections)
        elif self.algorithm == LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN:
            return self._select_weighted_round_robin(healthy_nodes)
        else:
            return healthy_nodes[self.round_robin_index % len(healthy_nodes)]
    
    def _select_by_response_time(self, nodes: List[NodeMetrics]) -> NodeMetrics:
        # Weight nodes by inverse response time and success rate
        weights = []
        for node in nodes:
            if node.avg_response_time > 0:
                weight = (1.0 / node.avg_response_time) * node.success_rate
            else:
                weight = node.success_rate
            weights.append(weight)
        
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(nodes)
        
        r = random.uniform(0, total_weight)
        cumulative = 0
        for node, weight in zip(nodes, weights):
            cumulative += weight
            if r <= cumulative:
                return node
        return nodes[-1]
    
    def _select_weighted_round_robin(self, nodes: List[NodeMetrics]) -> NodeMetrics:
        weights = [node.weight for node in nodes]
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(nodes)
        
        r = random.uniform(0, total_weight)
        cumulative = 0
        for node, weight in zip(nodes, weights):
            cumulative += weight
            if r <= cumulative:
                return node
        return nodes[-1]
    
    async def update_node_metrics(self, node_id: str, response_time: float, success: bool):
        if node_id not in self.nodes:
            return
        
        node = self.nodes[node_id]
        node.total_requests += 1
        node.last_response_time = response_time
        
        if not success:
            node.failed_requests += 1
        
        # Update rolling average response time
        alpha = 0.1  # Smoothing factor
        node.avg_response_time = alpha * response_time + (1 - alpha) * node.avg_response_time
        
        # Update success rate
        node.success_rate = (node.total_requests - node.failed_requests) / node.total_requests
        
        await self._persist_node_state(node)
    
    async def _persist_node_state(self, node: NodeMetrics):
        await distributed_state_manager.set_state(
            f"load_balancer:{self.service_name}:node:{node.node_id}",
            asdict(node),
            ttl=300
        )

# Global load balancers
load_balancers: Dict[str, DynamicLoadBalancer] = {}
