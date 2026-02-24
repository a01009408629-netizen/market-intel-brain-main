"""
MAIFA v3 Agent Registry - Centralized agent management
Manages 100+ agents without modification to core
"""

from typing import Dict, List, Any, Optional, Type
import asyncio
import logging
from datetime import datetime

from models.schemas import AgentTask, AgentStatus, Priority
from models.datatypes import AgentConfig, AgentRegistry
from services.agents.base_agent import BaseAgent, AgentWrapper

class AgentRegistry:
    """
    Centralized agent registry for managing all agents in the system
    Supports dynamic registration, discovery, and execution
    """
    
    def __init__(self):
        self.logger = logging.getLogger("AgentRegistry")
        self._agents: Dict[str, BaseAgent] = {}
        self._legacy_wrappers: Dict[str, AgentWrapper] = {}
        self._agent_configs: Dict[str, AgentConfig] = {}
        self._active_tasks: Dict[str, AgentTask] = {}
        self._execution_stats: Dict[str, Dict[str, Any]] = {}
        self._registry_lock = asyncio.Lock()
        
    async def register_agent(self, 
                           agent: BaseAgent, 
                           config: Optional[AgentConfig] = None) -> bool:
        """
        Register a new agent in the registry
        
        Args:
            agent: Agent instance to register
            config: Optional configuration for the agent
            
        Returns:
            True if registration successful, False otherwise
        """
        async with self._registry_lock:
            try:
                if agent.name in self._agents:
                    self.logger.warning(f"Agent {agent.name} already registered, updating...")
                
                self._agents[agent.name] = agent
                self._agent_configs[agent.name] = config or {}
                self._execution_stats[agent.name] = {
                    "total_executions": 0,
                    "successful_executions": 0,
                    "failed_executions": 0,
                    "avg_execution_time": 0.0,
                    "last_execution": None
                }
                
                # Perform health check
                is_healthy = await agent.health_check()
                if not is_healthy:
                    self.logger.warning(f"Agent {agent.name} failed health check during registration")
                
                self.logger.info(f"Agent {agent.name} registered successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to register agent {agent.name}: {e}")
                return False
    
    async def register_legacy_agent(self, 
                                  name: str, 
                                  agent_class: Type,
                                  config: Optional[AgentConfig] = None) -> bool:
        """
        Register a legacy agent class with wrapper
        
        Args:
            name: Agent name
            agent_class: Legacy agent class
            config: Optional configuration
            
        Returns:
            True if registration successful
        """
        try:
            wrapper = AgentWrapper(agent_class, name)
            self._legacy_wrappers[name] = wrapper
            self._agent_configs[name] = config or {}
            self._execution_stats[name] = {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "avg_execution_time": 0.0,
                "last_execution": None
            }
            
            self.logger.info(f"Legacy agent {name} registered with wrapper")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register legacy agent {name}: {e}")
            return False
    
    async def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get agent instance by name"""
        return self._agents.get(name)
    
    async def get_legacy_wrapper(self, name: str) -> Optional[AgentWrapper]:
        """Get legacy agent wrapper by name"""
        return self._legacy_wrappers.get(name)
    
    async def list_agents(self) -> List[str]:
        """List all registered agent names"""
        return list(self._agents.keys()) + list(self._legacy_wrappers.keys())
    
    async def list_agents_info(self) -> Dict[str, Any]:
        """List all registered agents with detailed information"""
        agents_info = {}
        
        # Modern agents
        for name, agent in self._agents.items():
            agents_info[name] = {
                "type": "modern",
                "class": agent.__class__.__name__,
                "metrics": agent.get_metrics(),
                "info": agent.get_info(),
                "config": self._agent_configs.get(name, {})
            }
        
        # Legacy agents
        for name, wrapper in self._legacy_wrappers.items():
            agents_info[name] = {
                "type": "legacy",
                "class": wrapper.legacy_agent_class.__name__,
                "metrics": self._execution_stats.get(name, {}),
                "config": self._agent_configs.get(name, {})
            }
        
        return agents_info
    
    async def get_agents_by_type(self, agent_type: str) -> List[str]:
        """Get agents filtered by type"""
        matching_agents = []
        
        for name, agent in self._agents.items():
            if agent_type.lower() in agent.__class__.__name__.lower():
                matching_agents.append(name)
        
        for name, wrapper in self._legacy_wrappers.items():
            if agent_type.lower() in name.lower():
                matching_agents.append(name)
        
        return matching_agents
    
    async def execute_agent(self, 
                          agent_name: str, 
                          input_data: Dict[str, Any],
                          timeout: float = 5.0) -> Dict[str, Any]:
        """
        Execute a specific agent by name
        
        Args:
            agent_name: Name of agent to execute
            input_data: Input data for the agent
            timeout: Execution timeout in seconds
            
        Returns:
            Execution result
        """
        start_time = datetime.now()
        
        try:
            # Update execution stats
            stats = self._execution_stats.get(agent_name, {})
            stats["total_executions"] += 1
            stats["last_execution"] = start_time.isoformat()
            
            # Check if it's a modern agent
            agent = await self.get_agent(agent_name)
            if agent:
                # Convert input to AgentInput format
                from models.schemas import AgentInput
                agent_input = AgentInput(
                    text=input_data.get("text", ""),
                    symbol=input_data.get("symbol", "UNKNOWN"),
                    metadata=input_data.get("metadata", {})
                )
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    agent.execute(agent_input),
                    timeout=timeout
                )
                
                if result.status == AgentStatus.COMPLETED:
                    stats["successful_executions"] += 1
                else:
                    stats["failed_executions"] += 1
                
                # Update average execution time
                self._update_avg_execution_time(agent_name, result.execution_time)
                
                return result.__dict__
            
            # Check if it's a legacy agent
            wrapper = await self.get_legacy_wrapper(agent_name)
            if wrapper:
                result = await asyncio.wait_for(
                    wrapper.execute_legacy(input_data),
                    timeout=timeout
                )
                
                if result["status"] == "completed":
                    stats["successful_executions"] += 1
                else:
                    stats["failed_executions"] += 1
                
                execution_time = (datetime.now() - start_time).total_seconds()
                self._update_avg_execution_time(agent_name, execution_time)
                
                return result
            
            raise ValueError(f"Agent {agent_name} not found in registry")
            
        except asyncio.TimeoutError:
            stats["failed_executions"] += 1
            self.logger.error(f"Agent {agent_name} execution timed out after {timeout}s")
            return {
                "agent_name": agent_name,
                "status": "timeout",
                "error": f"Execution timed out after {timeout}s",
                "execution_time": timeout,
                "timestamp": start_time.isoformat()
            }
            
        except Exception as e:
            stats["failed_executions"] += 1
            self.logger.error(f"Agent {agent_name} execution failed: {e}")
            return {
                "agent_name": agent_name,
                "status": "failed",
                "error": str(e),
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "timestamp": start_time.isoformat()
            }
    
    async def execute_parallel(self, 
                             agent_names: List[str],
                             input_data: Dict[str, Any],
                             timeout: float = 5.0) -> Dict[str, Dict[str, Any]]:
        """
        Execute multiple agents in parallel
        
        Args:
            agent_names: List of agent names to execute
            input_data: Input data (same for all agents)
            timeout: Timeout per agent
            
        Returns:
            Dict mapping agent names to their results
        """
        tasks = []
        for agent_name in agent_names:
            task = asyncio.create_task(
                self.execute_agent(agent_name, input_data, timeout)
            )
            tasks.append((agent_name, task))
        
        results = {}
        for agent_name, task in tasks:
            try:
                result = await task
                results[agent_name] = result
            except Exception as e:
                self.logger.error(f"Parallel execution failed for {agent_name}: {e}")
                results[agent_name] = {
                    "agent_name": agent_name,
                    "status": "failed",
                    "error": str(e),
                    "execution_time": 0.0,
                    "timestamp": datetime.now().isoformat()
                }
        
        return results
    
    def _update_avg_execution_time(self, agent_name: str, execution_time: float):
        """Update average execution time for an agent"""
        stats = self._execution_stats.get(agent_name, {})
        total = stats["total_executions"]
        current_avg = stats["avg_execution_time"]
        
        stats["avg_execution_time"] = (
            (current_avg * (total - 1) + execution_time) / total
        )
    
    async def get_agent_stats(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Get execution statistics for agents"""
        if agent_name:
            return self._execution_stats.get(agent_name, {})
        return self._execution_stats
    
    async def get_registry_info(self) -> Dict[str, Any]:
        """Get comprehensive registry information"""
        return {
            "total_agents": len(self._agents) + len(self._legacy_wrappers),
            "modern_agents": len(self._agents),
            "legacy_agents": len(self._legacy_wrappers),
            "agent_names": await self.list_agents(),
            "execution_stats": self._execution_stats,
            "agent_configs": self._agent_configs
        }
    
    async def unregister_agent(self, agent_name: str) -> bool:
        """Unregister an agent from the registry"""
        try:
            if agent_name in self._agents:
                del self._agents[agent_name]
            if agent_name in self._legacy_wrappers:
                del self._legacy_wrappers[agent_name]
            if agent_name in self._agent_configs:
                del self._agent_configs[agent_name]
            if agent_name in self._execution_stats:
                del self._execution_stats[agent_name]
            
            self.logger.info(f"Agent {agent_name} unregistered successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unregister agent {agent_name}: {e}")
            return False
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Perform health check on all registered agents"""
        health_results = {}
        
        for name, agent in self._agents.items():
            try:
                health_results[name] = await agent.health_check()
            except Exception as e:
                self.logger.error(f"Health check failed for {name}: {e}")
                health_results[name] = False
        
        for name in self._legacy_wrappers.keys():
            # Legacy agents don't have health checks, assume healthy
            health_results[name] = True
        
        return health_results


# Global registry instance
agent_registry = AgentRegistry()
