"""
Chaos Engine

This module provides chaos engineering capabilities for testing system resilience
with configurable fault injection and experiment management.
"""

import asyncio
import time
import logging
import json
import random
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
from collections import defaultdict, deque
import threading

from .exceptions import (
    ChaosEngineError,
    ConfigurationError,
    FaultInjectionError,
    ExperimentError,
    RedisConnectionError
)
from .randomness import get_deterministic_random


class ChaosType(Enum):
    """Types of chaos experiments."""
    LATENCY = "latency"
    ERROR = "error"
    PACKET_LOSS = "packet_loss"
    CORRUPTION = "corruption"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    NETWORK_PARTITION = "network_partition"
    SERVICE_UNAVAILABLE = "service_unavailable"
    DATABASE_ERROR = "database_error"
    CACHE_INVALIDATION = "cache_invalidation"


class ExperimentStatus(Enum):
    """Status of chaos experiments."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class ChaosExperiment:
    """Configuration for a chaos experiment."""
    id: str
    name: str
    chaos_type: ChaosType
    target: str
    configuration: Dict[str, Any]
    status: ExperimentStatus
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    metrics: Dict[str, Any]
    error: Optional[str] = None
    results: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any]


@dataclass
class ChaosConfig:
    """Configuration for chaos engine."""
    enable_chaos: bool = True
    default_latency_range: tuple = (0.1, 1.0)
    default_error_rate: float = 0.01
    enable_redis: bool = False
    redis_url: Optional[str] = None
    experiment_timeout: float = 300.0  # 5 minutes
    max_concurrent_experiments: int = 5
    enable_metrics: bool = True
    enable_state_persistence: bool = False
    enable_safety_checks: bool = True
    dry_run_mode: bool = False


@dataclass
class ChaosMetrics:
    """Metrics collected during chaos experiments."""
    total_experiments: int = 0
    running_experiments: int = 0
    completed_experiments: int = 0
    failed_experiments: int = 0
    cancelled_experiments: int = 0
    total_injected_faults: int = 0
    total_requests_affected: int = 0
    avg_latency_increase: float = 0.0
    error_rate_increase: float = 0.0
    packet_loss_rate: float = 0.0
    resource_usage_increase: float = 0.0


class ChaosEngine:
    """
    Chaos engine for fault injection and experiment management.
    
    This class provides comprehensive chaos engineering capabilities
    for testing system resilience and graceful degradation.
    """
    
    def __init__(
        self,
        config: Optional[ChaosConfig] = None,
        logger: Optional[redis.asyncio.Redis] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize chaos engine.
        
        Args:
            config: Chaos engine configuration
            redis_client: Redis client for state persistence
            logger: Logger instance
        """
        self.config = config or ChaosConfig()
        self.logger = logger or logging.getLogger("ChaosEngine")
        
        # Components
        self._random = get_deterministic_random()
        self._redis_client = redis_client
        self._experiments: Dict[str, ChaosExperiment] = {}
        self._running_experiments: Dict[str, str] = {}
        self._experiment_tasks: Dict[str, asyncio.Task] = {}
        
        # Statistics
        self._metrics = ChaosMetrics()
        self._lock = threading.Lock()
        
        # Safety checks
        self._safety_checks_enabled = self.config.enable_safety_checks
        
        # Initialize Redis connection if enabled
        if self.config.enable_redis and self._redis_client is None:
            try:
                import redis.asyncio as redis
                self._redis_client = redis.from_url(self.config.redis_url)
                await self._redis_client.ping()
                self.logger.info(f"Connected to Redis: {self.config.redis_url}")
            except Exception as e:
                self.logger.error(f"Failed to connect to Redis: {e}")
                raise RedisConnectionError(f"Redis connection failed: {e}")
        
        self.logger.info("ChaosEngine initialized")
    
    async def start_experiment(self, experiment: ChaosExperiment) -> str:
        """
        Start a chaos experiment.
        
        Args:
            experiment: Chaos experiment configuration
            experiment_id: Experiment ID string
            
        Returns:
            Experiment ID string
        """
        if experiment.id in self._experiments:
            raise ExperimentError(f"Experiment {experiment.id} already exists")
        
        experiment.status = ExperimentStatus.PENDING
        experiment.start_time = time.time()
        experiment.results = []
        
        self._experiments[experiment.id] = experiment
        self._running_experiments[experiment.id] = experiment
        
        # Start experiment task
        task = asyncio.create_task(self._run_experiment(experiment))
        self._experiment_tasks[experiment.id] = task
        
        self.logger.info(f"Started chaos experiment: {experiment.name} ({experiment.id})")
        
        return experiment.id
    
    async def stop_experiment(self, experiment_id: str) -> bool:
        """
        Stop a running experiment.
        
        Args:
            experiment_id: Experiment ID string
            
        Returns:
            True if experiment was stopped, False otherwise
        """
        if experiment_id not in self._experiments:
            return False
        
        experiment = self._experiments[experiment_id]
        
        if experiment.status not in [ExperimentStatus.RUNNING, ExperimentStatus.PENDING]:
            return False
        
        experiment.status = ExperimentStatus.CANCELLED
        experiment.end_time = time.time()
        
        # Cancel experiment task
        if experiment_id in self._running_experiments:
            task = self._running_experiments[experiment_id]
            task.cancel()
            del self._running_experiments[experiment_id]
        
        self.logger.info(f"Stopped chaos experiment: {experiment.name} ({experiment.id})")
        
        return True
    
    async def _run_experiment(self, experiment: ChaosExperiment) -> None:
        """Run a chaos experiment."""
        try:
            experiment.status = ExperimentStatus.RUNNING
            
            # Configure chaos based on experiment type
            chaos_config = self._configure_chaos(experiment)
            
            # Run experiment with periodic updates
            start_time = time.time()
            end_time = start_time + experiment.configuration.get("duration", 300.0)
            
            while time.time() < end_time and experiment.status == ExperimentStatus.RUNNING:
                # Apply chaos
                await self._apply_chaos(experiment)
                
                # Wait for next update interval
                await asyncio.sleep(experiment.configuration.get("update_interval", 10.0))
                
                # Update experiment status
                if time.time() >= end_time:
                    experiment.status = ExperimentStatus.COMPLETED
                    experiment.end_time = time.time()
                
                # Record metrics
                self._record_experiment_metrics(experiment)
                
                # Stop experiment
                if experiment.id in self._running_experiments:
                    task = self._running_experiments[experiment.id]
                    del self._running_experiments[experiment.id]
                
                self.logger.info(f"Completed chaos experiment: {experiment.name} ({experiment.id})")
        
        except Exception as e:
            experiment.status = ExperimentStatus.FAILED
            experiment.end_time = time.time()
            experiment.error = str(e)
            self.logger.error(f"Chaos experiment failed: {experiment.name} ({experiment.id}): {e}")
    
    async def _configure_chaos(self, experiment: ChaosExperiment) -> Dict[str, Any]:
        """Configure chaos based on experiment type."""
        chaos_config = experiment.configuration.copy()
        
        if experiment.chaos_type == ChaosType.LATENCY:
            chaos_config.update({
                "latency_range": experiment.configuration.get("latency_range", (0.5, 5.0),
                "latency_distribution": experiment.configuration.get("latency_distribution", "normal"),
                "target_latency": experiment.configuration.get("target_latency", 2.0)
                "jitter": experiment.configuration.get("jitter", False)
            })
        elif experiment.chaos_type == ChaosType.ERROR:
            chaos_config.update({
                "error_types": experiment.configuration.get("error_types", [
                    "timeout",
                    "connection_error",
                    "http_error",
                    "validation_error"
                ]),
                "error_rate": experiment.configuration.get("error_rate", 0.1),
                "error_distribution": experiment.configuration.get("error_distribution", "random")
            })
        elif experiment.chaos_type == ChaosType.PACKET_LOSS:
            chaos_config.update({
                "packet_loss_rate": experiment.configuration.get("packet_loss_rate", 0.01),
                "target_hosts": experiment.configuration.get("target_hosts", []),
                "affected_endpoints": experiment.configuration.get("affected_endpoints", ["/api/*"]),
                "packet_loss_pattern": experiment.configuration.get("packet_loss_pattern", "random")
            })
        elif experiment.chaos_type == ChaosType.CORRUPTION:
            chaos_config.update({
                "corruption_types": experiment.configuration.get("corruption_types", [
                    "header_manipulation",
                    "data_manipulation",
                    "status_code_manipulation",
                    "content_manipulation"
                ]),
                "corruption_rate": experiment.configuration.get("corruption_rate", 0.02),
                "target_services": experiment.configuration.get("target_services", []),
                "corruption_methods": experiment.configuration.get("corruption_methods", ["header_manipulation"])
            })
        elif experiment.chaos_type == ChaosType.RESOURCE_EXHAUSTION:
            chaos_config.update({
                "resource_types": experiment.configuration.get("resource_types", [
                    "cpu",
                    "memory",
                    "disk",
                    "network"
                ]),
                "exhaustion_rate": experiment.configuration.get("exhaustion_rate", 0.8),
                "exhaustion_pattern": experiment.configuration.get("exhaustion_pattern", "gradual")
            })
        elif experiment.chaos_type == ChaosType.NETWORK_PARTITION:
            chaos_config.update({
                "partition_strategy": experiment.configuration.get("partition_strategy", "random"),
                "affected_subnets": experiment.configuration.get("affected_subnets", ["10.0.0.0/8", "192.168.1.0/16"]),
                "drop_rate": experiment.configuration.get("drop_rate", 0.1),
                "affected_hosts": experiment.configuration.get("affected_hosts", [])
                "isolation_duration": experiment.configuration.get("isolation_duration", 30.0)
            })
        elif experiment.chaos_type == ChaosType.SERVICE_UNAVAILABLE:
            chaos_config.update({
                "unavailable_services": experiment.configuration.get("unavailable_services", []),
                "unavailable_duration": experiment.configuration.get("unavailable_duration", 60.0),
                "error_responses": experiment.configuration.get("error_responses", ["503", "504", "502"]),
                "unavailable_strategy": experiment.configuration.get("unavailable_strategy", "fail_fast")
            })
        
        return chaos_config
    
    async def _apply_chaos(self, experiment: ChaosExperiment) -> None:
            """Apply chaos based on experiment configuration."""
        chaos_config = experiment.configuration
        
        if not chaos_config:
            return
        
        # Apply chaos based on type
        if experiment.chaos_type == ChaosType.LATENCY:
            await self._apply_latency_chaos(experiment, chaos_config)
        elif experiment.chaos_type == ChaosType.ERROR:
            await self._apply_error_chaos(experiment, chaos_config)
        elif experiment.chaos_type == ChaosType.PACKET_LOSS:
            await self._apply_packet_loss_chaos(experiment, chaos_config)
        elif experiment.chaos_type == ChaosType.CORRUPTION:
            await self._apply_corruption_chaos(experiment, chaos_config)
        elif experiment.chaos_type == ChaosType.RESOURCE_EXHAUSTION:
            await self._apply_resource_exhaustion_chaos(experiment, chaos_config)
        elif experiment.chaos_type == ChaosType.NETWORK_PARTITION:
            await self._apply_network_partition_chaos(experiment, chaos_config)
        elif experiment.chaos_type == ChaosType.SERVICE_UNAVAILABLE:
            await self._apply_service_unavailable_chaos(experiment, chaos_config)
        
        # Add delay for chaos to take effect
        await asyncio.sleep(0.1)
    
    async def _apply_latency_chaos(self, experiment: ChaosExperiment, config: Dict[str, Any]) -> None:
            """Apply latency chaos."""
        latency_range = config.get("latency_range", (0.5, 5.0)
            target_latency = config.get("target_latency", 2.0)
            jitter = config.get("jitter", False)
            distribution = config.get("latency_distribution", "normal")
            
            # Get all active requests
            active_requests = self._get_active_requests()
            
            for request_id in active_requests:
                # Calculate target latency
                base_latency = self._random.next_float(*latency_range)
                
                if distribution == "normal":
                    latency = base_latency
                elif distribution == "exponential":
                    # Exponential distribution
                    lambda_factor = config.get("lambda_factor", 1.5)
                    latency = base_latency * (1 + lambda_factor * self._random.next_exponential(1.0))
                elif distribution == "uniform":
                    latency = self._random.next_float(*latency_range)
                
                # Add jitter if enabled
                if jitter:
                    jitter = self._random.next_float(-0.1, 0.1)
                    latency = max(0.1, latency + jitter)
                
                # Apply latency
                await self._inject_latency(request_id, latency)
        
        # Wait for chaos to take effect
        await asyncio.sleep(0.1)
    
    async def _apply_error_chaos(self, experiment: ChaosExperiment, config: Dict[str, Any]) -> None:
            """Apply error chaos."""
        error_types = config.get("error_types", ["timeout", "connection_error", "http_error"])
        error_rate = config.get("error_rate", 0.1)
        error_distribution = config.get("error_distribution", "random")
        
        # Get all active requests
        active_requests = self._get_active_requests()
        
        for request_id in active_requests:
            # Inject error based on error rate
            if self._random.next_float() < error_rate:
                await self._inject_error(request_id, "timeout")
            elif self._random.next_float() < error_rate * 2:
                await self._inject_error(request_id, "connection_error")
            else:
                await self._inject_error(request_id, "http_error")
        
        # Wait for chaos to take effect
        await asyncio.sleep(0.1)
    
    async def _apply_packet_loss_chaos(self, experiment: ChaosExperiment, config: Dict[str, Any]) -> None:
            """Apply packet loss chaos."""
        packet_loss_rate = config.get("packet_loss_rate", 0.01)
        target_hosts = config.get("target_hosts", [])
        affected_endpoints = config.get("affected_endpoints", ["/api/*"])
        packet_loss_pattern = config.get("packet_loss_pattern", "random")
        
        # Get all active requests
        active_requests = self._get_active_requests()
        
        for request_id in active_requests:
            # Inject packet loss based on rate
            if self._random.next_float() < packet_loss_rate:
                await self._inject_packet_loss(request_id)
        
        # Wait for chaos to take effect
        await asyncio.sleep(0.1)
    
    async def _apply_corruption_chaos(self, experiment: ChaosExperiment, config: Dict[str, Any]) -> None:
            """Apply data corruption chaos."""
        corruption_types = config.get("corruption_types", [
            "header_manipulation",
            "data_manipulation",
            "status_code_manipulation",
            "content_manipulation"
        ])
        corruption_rate = config.get("corruption_rate", 0.02)
        corruption_methods = config.get("corruption_methods", ["header_manipulation"])
        
        # Get all active requests
        active_requests = self._get_active_requests()
        
        for request_id in active_requests:
            # Apply corruption based on rate
            if self._random.next_float() < corruption_rate:
                corruption_method = self._random.next_choice(corruption_methods)
                
                if corruption_method == "header_manipulation":
                    await self._inject_header_manipulation(request_id)
                elif corruption_method == "data_manipulation":
                    await self._inject_data_manipulation(request_id)
                elif corruption_method == "status_code_manipulation":
                    await self._inject_status_code_manipulation(request_id)
                
                # Wait for chaos to take effect
                await asyncio.sleep(0.1)
    
    async def _apply_resource_exhaustion_chaos(self, experiment: ChaosExperiment, config: Dict[str, any]) -> None:
            """Apply resource exhaustion chaos."""
        resource_types = config.get("resource_types", ["cpu", "memory", "disk", "network"])
        exhaustion_rate = config.get("exhaustion_rate", 0.8)
        exhaustion_pattern = config.get("exhaustion_pattern", "gradual")
        
        # Get all active requests
        active_requests = self._get_active_requests()
        
        for request_id in active_requests:
            # Apply resource exhaustion based on rate
            if self._random.next_float() < exhaustion_rate:
                resource_type = self._random.next_choice(resource_types)
                
                if resource_type == "cpu":
                    await self._inject_cpu_exhaustion(request_id)
                elif resource_type == "memory":
                    await self._inject_memory_exhaustion(request_id)
                elif resource_type == "disk":
                    await self._inject_disk_exhaustion(request_id)
                elif resource_type == "network":
                    await self._inject_network_partition(request_id)
                
                # Wait for chaos to take effect
                await asyncio.sleep(0.1)
    
    async def _apply_network_partition_chaos(self, experiment: ChaosExperiment, config: Dict[str, any]) -> None:
            """Apply network partition chaos."""
        partition_strategy = config.get("partition_strategy", "random")
        affected_subnets = config.get("affected_subnets", ["10.0.0.0/8", "192.168.1.0/16"])
        drop_rate = config.get("drop_rate", 0.1)
        isolation_duration = config.get("isolation_duration", 30.0)
        target_hosts = config.get("target_hosts", [])
        affected_endpoints = config.get("affected_endpoints", ["/api/*"])
        
        # Get all active requests
        active_requests = self._get_active_requests()
        
        for request_id in active_requests:
            # Apply network partition based on strategy
            if partition_strategy == "random":
                # Randomly select subnet to partition
                affected_subnet = self._random.choice(affected_subnets)
                await self._inject_network_partition(request_id, affected_subnet)
            elif partition_strategy == "round_robin":
                # Round-robin through subnets
                current_subnet = self._get_current_subnet(request_id)
                next_subnet = self._get_next_subnet(current_subnet, affected_subnets)
                await self._inject_network_partition(request_id, next_subnet)
            
            # Wait for chaos to take effect
            await asyncio.sleep(0.1)
    
    def _apply_service_unavailable_chaos(self, experiment: ChaosExperiment, config: Dict[str, any]) -> None:
            """Apply service unavailability chaos."""
            unavailable_services = config.get("unavailable_services", [])
            unavailable_duration = config.get("unavailable_duration", 60.0)
            error_responses = config.get("error_responses", ["503", "504", "502"])
            unavailable_strategy = config.get("unavailable_strategy", "fail_fast")
        
        # Get all active requests
        active_requests = self._get_active_requests()
        
        for request_id in active_requests:
            # Apply service unavailability based on rate
            if self._random.next_float() < 0.05:  # 5% error rate
                error_response = self._random.next_choice(error_responses)
                await self._inject_service_unavailable(request_id, error_response)
            elif self._random.next_float() < 0.1:  # 10% error rate
                error_response = self._random.next_choice(error_responses)
            
            # Wait for chaos to take effect
            await asyncio.sleep(0.1)
    
    def _get_active_requests(self) -> List[str]:
        """Get list of currently active request IDs."""
        # This would be implemented by the mock server
        return []
    
    def _inject_latency(self, request_id: str, latency: float) -> None:
            """Inject latency into a request."""
        # This would be implemented by the mock server
        pass
    
    def _inject_error(self, request_id: str, error_type: str) -> None:
            """Inject error into a request."""
        # This would be implemented by the mock server
        pass
    
    def _inject_packet_loss(self, request_id: str) -> None:
            """Inject packet loss into a request."""
            # This would be implemented by the mock server
            pass
    
    def _inject_header_manipulation(self, request_id: str) -> None:
            """Inject header manipulation into a request."""
            # This would be implemented by the mock server
            pass
    
    def _inject_data_manipulation(self, request_id: str) -> None:
            """Inject data manipulation into a request."""
            # This would be implemented by the mock server
            pass
    
    def _inject_status_code_manipulation(self, request_id: str) -> None:
            """Inject status code manipulation into a request."""
            # This would be implemented by the mock server
            pass
    
    def _inject_cpu_exhaustion(self, request_id: str) -> None:
            """Inject CPU exhaustion into a request."""
            # This would be implemented by the mock server
            pass
    
    def _inject_memory_exhaustion(self, request_id: str) -> None:
            """Inject memory exhaustion into a request."""
            # This would be implemented by the mock server
            pass
    
    def _inject_disk_exhaustion(self, request_id: str) -> None:
            """Inject disk exhaustion into a request."""
            # This would be implemented by the mock server
            pass
    
    def _inject_network_partition(self, request_id: str, subnet: str) -> None:
            """Inject network partition for a request."""
            # This would be implemented by the mock server
            pass
    
    def _inject_service_unavailable(self, request_id: str, error_response: str) -> None:
            """Inject service unavailability for a request."""
            # This would be implemented by the mock server
            pass
    
    def _get_current_subnet(self, request_id: str) -> str:
            """Get current subnet for a request."""
            # This would be implemented by the mock server
            return "10.0.0.0/8"
    
    def _get_next_subnet(self, current_subnet: str, available_subnets: List[str]) -> str:
            """Get next subnet in round-robin pattern."""
            current_index = available_subnets.index(current_subnet) if current_subnet in available_subnets else 0
            next_index = (current_index + 1) % len(available_subnets))
            return available_subnets[next_index]
    
    def _inject_network_partition(self, request_id: str, subnet: str) -> None:
            """Inject network partition for a request."""
            # This would be implemented by the mock server
            pass
    
    def _get_active_requests(self) -> List[str]:
            """Get list of active request IDs."""
        return []


# Global chaos engine instance
_global_chaos_engine: Optional[ChaosEngine] = None


def get_chaos_engine(**kwargs) -> ChaosEngine:
    """
    Get or create global chaos engine.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global ChaosEngine instance
    """
    global _global_chaos_engine
    if _global_chaos_engine is None:
        _global_chaos_engine = ChaosEngine(**kwargs)
    return _global_chaos_engine


# Convenience functions for global usage
async def start_chaos_experiment(experiment: Dict[str, Any]) -> str:
    """Start chaos experiment using global engine."""
    engine = get_chaos_engine()
    return await engine.start_experiment(ChaosExperiment(**experiment))


def get_chaos_engine_status() -> Dict[str, Any]:
    """Get chaos engine status."""
    engine = get_chaos_engine()
    return engine.get_status()


def stop_chaos_experiment(experiment_id: str) -> bool:
    """Stop chaos experiment using global engine."""
    engine = get_chaos_engine()
    return await engine.stop_experiment(experiment_id)


def get_chaos_engine_info() -> Dict[str, Any]:
    """Get chaos engine information."""
    engine = get_chaos_engine()
    return engine.get_engine_info()
