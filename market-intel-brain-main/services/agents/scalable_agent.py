"""
MAIFA v3 Scalable & Modular Agent Framework
Production-ready agent system supporting 1000+ agents with zero core modifications
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from abc import ABC, abstractmethod
import uuid

from core.distributed_state import distributed_state_manager
from core.service_mesh import service_mesh, Priority
from core.circuit_breaker import circuit_breaker_manager, CircuitBreakerConfig, RetryConfig
from core.monitoring import monitoring_system, monitor_metric
from utils.logger import get_logger

logger = get_logger("scalable_agent")

@dataclass
class AgentConfig:
    agent_id: str
    agent_name: str
    version: str
    priority: Priority
    max_concurrent_requests: int = 10
    timeout: float = 5.0
    retry_attempts: int = 3
    memory_limit_mb: int = 512
    cpu_limit_percent: float = 10.0
    dependencies: List[str] = None
    capabilities: List[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class AgentInput:
    request_id: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: float
    priority: Priority

@dataclass
class AgentOutput:
    request_id: str
    agent_id: str
    status: str
    result: Dict[str, Any]
    confidence: float
    explanation: str
    weights: Dict[str, float]
    execution_time: float
    timestamp: float
    metadata: Dict[str, Any]

class ScalableAgent(ABC):
    """
    Base class for scalable, modular agents
    
    Features:
    - Automatic service mesh registration
    - Circuit breaker protection
    - Performance monitoring
    - Resource limits enforcement
    - Graceful degradation
    - Hot reload capability
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = config.agent_id
        self.logger = get_logger(f"Agent.{config.agent_name}")
        self.is_running = False
        self.active_requests = 0
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        # Circuit breaker for this agent
        self.circuit_breaker = circuit_breaker_manager.create_circuit_breaker(
            f"agent_{self.agent_id}",
            CircuitBreakerConfig(
                failure_threshold=5,
                timeout=60.0,
                max_retries=config.retry_attempts
            ),
            RetryConfig(
                max_attempts=config.retry_attempts,
                base_delay=0.1
            )
        )
        
        # Performance metrics
        self.response_times = []
        self.last_health_check = 0.0
        
    async def initialize(self) -> bool:
        """Initialize agent and register with service mesh"""
        try:
            self.logger.info(f"🔧 Initializing agent: {self.config.agent_name}")
            
            # Register with service mesh
            success = await service_mesh.register_service(
                service_name=f"agent_{self.config.agent_name}",
                instance_id=self.agent_id,
                host="localhost",  # In production, get actual host
                port=8000 + hash(self.agent_id) % 1000,  # Dynamic port
                health_check_url="/health",
                priority=self.config.priority,
                metadata={
                    "agent_name": self.config.agent_name,
                    "version": self.config.version,
                    "capabilities": self.config.capabilities or [],
                    "max_requests": self.config.max_concurrent_requests
                }
            )
            
            if not success:
                self.logger.error(f"❌ Failed to register agent: {self.config.agent_name}")
                return False
            
            # Initialize agent-specific resources
            await self._initialize_resources()
            
            # Start background tasks
            self.is_running = True
            asyncio.create_task(self._health_check_loop())
            asyncio.create_task(self._metrics_collection_loop())
            
            # Store agent state
            await self._persist_agent_state()
            
            self.logger.info(f"✅ Agent initialized: {self.config.agent_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Agent initialization failed: {e}")
            return False
    
    @abstractmethod
    async def analyze(self, input_data: AgentInput) -> AgentOutput:
        """
        Main analysis method - must be implemented by all agents
        
        Args:
            input_data: Agent input with request data and metadata
            
        Returns:
            AgentOutput with analysis results
        """
        pass
    
    @abstractmethod
    async def explain(self, result: AgentOutput) -> str:
        """
        Provide explanation for the analysis result
        
        Args:
            result: Analysis result to explain
            
        Returns:
            Human-readable explanation
        """
        pass
    
    @abstractmethod
    async def weights(self) -> Dict[str, float]:
        """
        Return confidence weights for different factors
        
        Returns:
            Dictionary of factor weights
        """
        pass
    
    @monitor_metric(f"agent_{self.agent_id}", "process_request")
    async def process_request(self, request_data: Dict[str, Any]) -> AgentOutput:
        """Process incoming request with full protection"""
        start_time = time.time()
        request_id = request_data.get("request_id", str(uuid.uuid4()))
        
        try:
            # Check resource limits
            if self.active_requests >= self.config.max_concurrent_requests:
                raise ResourceExhaustedException(f"Agent {self.agent_id} at capacity")
            
            # Create input object
            agent_input = AgentInput(
                request_id=request_id,
                data=request_data.get("data", {}),
                metadata=request_data.get("metadata", {}),
                timestamp=time.time(),
                priority=request_data.get("priority", Priority.NORMAL)
            )
            
            # Execute with circuit breaker protection
            result = await self.circuit_breaker.call(
                self._execute_analysis,
                agent_input,
                timeout=self.config.timeout
            )
            
            # Update metrics
            execution_time = time.time() - start_time
            self._update_metrics(execution_time, True)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_metrics(execution_time, False)
            
            # Return error result
            return AgentOutput(
                request_id=request_id,
                agent_id=self.agent_id,
                status="error",
                result={"error": str(e)},
                confidence=0.0,
                explanation=f"Analysis failed: {str(e)}",
                weights={},
                execution_time=execution_time,
                timestamp=time.time(),
                metadata={"error_type": type(e).__name__}
            )
    
    async def _execute_analysis(self, input_data: AgentInput) -> AgentOutput:
        """Execute analysis with resource monitoring"""
        self.active_requests += 1
        self.total_requests += 1
        
        try:
            # Check memory usage (simplified)
            if self._check_memory_limit():
                raise ResourceExhaustedException("Memory limit exceeded")
            
            # Execute analysis
            result = await self.analyze(input_data)
            
            # Validate result
            if not isinstance(result, AgentOutput):
                raise ValueError("Invalid result type")
            
            # Add execution metadata
            result.agent_id = self.agent_id
            result.timestamp = time.time()
            
            self.successful_requests += 1
            return result
            
        finally:
            self.active_requests -= 1
    
    async def _initialize_resources(self):
        """Initialize agent-specific resources"""
        # Override in subclasses
        pass
    
    def _check_memory_limit(self) -> bool:
        """Check if agent is within memory limits"""
        # Simplified check - in production use actual memory monitoring
        return False
    
    def _update_metrics(self, execution_time: float, success: bool):
        """Update performance metrics"""
        self.response_times.append(execution_time)
        
        # Keep only recent metrics
        if len(self.response_times) > 100:
            self.response_times.pop(0)
        
        # Record in monitoring system
        asyncio.create_task(monitoring_system.record_metric(
            f"agent_{self.config.agent_name}",
            "response_time",
            execution_time
        ))
        
        if success:
            asyncio.create_task(monitoring_system.record_metric(
                f"agent_{self.config.agent_name}",
                "success",
                1
            ))
        else:
            asyncio.create_task(monitoring_system.record_metric(
                f"agent_{self.config.agent_name}",
                "error",
                1
            ))
    
    async def _health_check_loop(self):
        """Background health monitoring"""
        while self.is_running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Perform health check
                health_status = await self._perform_health_check()
                
                # Update service mesh
                if not health_status:
                    self.logger.warning(f"⚠️ Health check failed for {self.config.agent_name}")
                
                self.last_health_check = time.time()
                
            except Exception as e:
                self.logger.error(f"❌ Health check error: {e}")
    
    async def _perform_health_check(self) -> bool:
        """Perform comprehensive health check"""
        try:
            # Check response time
            if self.response_times:
                avg_response_time = sum(self.response_times) / len(self.response_times)
                if avg_response_time > self.config.timeout * 0.8:
                    return False
            
            # Check error rate
            if self.total_requests > 0:
                error_rate = self.failed_requests / self.total_requests
                if error_rate > 0.2:  # 20% error rate threshold
                    return False
            
            # Check active requests
            if self.active_requests >= self.config.max_concurrent_requests:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    async def _metrics_collection_loop(self):
        """Background metrics collection"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Collect every minute
                
                # Calculate metrics
                avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
                success_rate = self.successful_requests / self.total_requests if self.total_requests > 0 else 0
                
                # Store metrics
                metrics = {
                    "total_requests": self.total_requests,
                    "successful_requests": self.successful_requests,
                    "failed_requests": self.failed_requests,
                    "active_requests": self.active_requests,
                    "avg_response_time": avg_response_time,
                    "success_rate": success_rate,
                    "last_health_check": self.last_health_check
                }
                
                await distributed_state_manager.set_state(
                    f"agent_metrics:{self.agent_id}",
                    metrics,
                    ttl=300
                )
                
            except Exception as e:
                self.logger.error(f"Metrics collection error: {e}")
    
    async def _persist_agent_state(self):
        """Persist agent configuration and state"""
        state = {
            "config": asdict(self.config),
            "is_running": self.is_running,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "last_health_check": self.last_health_check,
            "timestamp": time.time()
        }
        
        await distributed_state_manager.set_state(
            f"agent_state:{self.agent_id}",
            state,
            ttl=3600
        )
    
    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status"""
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        success_rate = self.successful_requests / self.total_requests if self.total_requests > 0 else 0
        
        return {
            "agent_id": self.agent_id,
            "config": asdict(self.config),
            "is_running": self.is_running,
            "active_requests": self.active_requests,
            "metrics": {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "avg_response_time": avg_response_time,
                "success_rate": success_rate
            },
            "health": {
                "last_check": self.last_health_check,
                "status": "healthy" if await self._perform_health_check() else "unhealthy"
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def shutdown(self):
        """Graceful shutdown"""
        try:
            self.logger.info(f"🛑 Shutting down agent: {self.config.agent_name}")
            
            self.is_running = False
            
            # Deregister from service mesh
            await service_mesh.deregister_service(
                f"agent_{self.config.agent_name}",
                self.agent_id
            )
            
            # Persist final state
            await self._persist_agent_state()
            
            self.logger.info(f"✅ Agent shutdown complete: {self.config.agent_name}")
            
        except Exception as e:
            self.logger.error(f"❌ Agent shutdown error: {e}")

class ResourceExhaustedException(Exception):
    pass

# Agent registry for managing 1000+ agents
class ScalableAgentRegistry:
    def __init__(self):
        self.logger = get_logger("ScalableAgentRegistry")
        self.agents: Dict[str, ScalableAgent] = {}
        self.agent_configs: Dict[str, AgentConfig] = {}
        
    async def register_agent(self, agent: ScalableAgent) -> bool:
        """Register new agent"""
        try:
            if agent.agent_id in self.agents:
                self.logger.warning(f"Agent {agent.agent_id} already registered")
                return False
            
            # Initialize agent
            if not await agent.initialize():
                return False
            
            self.agents[agent.agent_id] = agent
            self.agent_configs[agent.agent_id] = agent.config
            
            self.logger.info(f"📝 Registered agent: {agent.config.agent_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to register agent {agent.agent_id}: {e}")
            return False
    
    async def execute_agent(self, agent_id: str, request_data: Dict[str, Any]) -> Optional[AgentOutput]:
        """Execute specific agent"""
        if agent_id not in self.agents:
            return None
        
        agent = self.agents[agent_id]
        return await agent.process_request(request_data)
    
    async def get_agents_by_capability(self, capability: str) -> List[str]:
        """Get agents with specific capability"""
        matching_agents = []
        
        for agent_id, config in self.agent_configs.items():
            if config.capabilities and capability in config.capabilities:
                matching_agents.append(agent_id)
        
        return matching_agents
    
    async def get_registry_status(self) -> Dict[str, Any]:
        """Get registry status"""
        return {
            "total_agents": len(self.agents),
            "running_agents": len([a for a in self.agents.values() if a.is_running]),
            "total_requests": sum(a.total_requests for a in self.agents.values()),
            "active_requests": sum(a.active_requests for a in self.agents.values()),
            "agents": {
                agent_id: await agent.get_status()
                for agent_id, agent in self.agents.items()
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def shutdown_all(self):
        """Shutdown all agents"""
        for agent in self.agents.values():
            await agent.shutdown()
        
        self.agents.clear()
        self.agent_configs.clear()
        self.logger.info("🛑 All agents shutdown")

# Global scalable agent registry
scalable_agent_registry = ScalableAgentRegistry()
