"""
MAIFA v3 Agent Loader - Auto-discovery and loading
Automatically discovers and loads all agents from services/agents/list/
"""

import os
import importlib
import inspect
from typing import Dict, List, Any, Type
from pathlib import Path
import logging

from services.agents.base_agent import BaseAgent
from services.agents.registry import agent_registry

class AgentLoader:
    """
    Auto-discovery and loading system for MAIFA v3 agents
    Scans services/agents/list/ directory and loads all agent classes
    """
    
    def __init__(self):
        self.logger = logging.getLogger("AgentLoader")
        self.agents_dir = Path(__file__).parent / "list"
        self.loaded_agents: Dict[str, Type[BaseAgent]] = {}
        self.agent_configs: Dict[str, Dict[str, Any]] = {}
        
    async def auto_load_agents(self) -> int:
        """
        Automatically discover and load all agents
        
        Returns:
            Number of agents successfully loaded
        """
        if not self.agents_dir.exists():
            self.logger.warning(f"Agents directory not found: {self.agents_dir}")
            return 0
        
        loaded_count = 0
        
        # Scan for Python files in agents/list/
        for agent_file in self.agents_dir.glob("*.py"):
            if agent_file.name.startswith("__"):
                continue
                
            try:
                # Import module
                module_name = f"services.agents.list.{agent_file.stem}"
                module = importlib.import_module(module_name)
                
                # Find BaseAgent subclasses
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseAgent) and 
                        obj != BaseAgent and 
                        obj.__module__ == module_name):
                        
                        # Register agent
                        success = await self._register_agent_class(obj, name)
                        if success:
                            loaded_count += 1
                            self.logger.info(f"Loaded agent: {name}")
                        
            except Exception as e:
                self.logger.error(f"Failed to load agent from {agent_file}: {e}")
        
        self.logger.info(f"Auto-load completed: {loaded_count} agents loaded")
        return loaded_count
    
    async def _register_agent_class(self, agent_class: Type[BaseAgent], class_name: str) -> bool:
        """
        Register an agent class with the registry
        
        Args:
            agent_class: Agent class to register
            class_name: Name of the class
            
        Returns:
            True if registration successful
        """
        try:
            # Create agent instance
            agent_instance = agent_class()
            
            # Get agent configuration if available
            config = getattr(agent_class, "CONFIG", {})
            
            # Register with global registry
            success = await agent_registry.register_agent(agent_instance, config)
            
            if success:
                self.loaded_agents[class_name] = agent_class
                self.agent_configs[class_name] = config
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to register agent {class_name}: {e}")
            return False
    
    async def reload_agent(self, agent_name: str) -> bool:
        """
        Reload a specific agent
        
        Args:
            agent_name: Name of agent to reload
            
        Returns:
            True if reload successful
        """
        try:
            # Unregister existing agent
            await agent_registry.unregister_agent(agent_name)
            
            # Remove from loaded agents
            if agent_name in self.loaded_agents:
                del self.loaded_agents[agent_name]
            if agent_name in self.agent_configs:
                del self.agent_configs[agent_name]
            
            # Reload all agents
            return await self.auto_load_agents() > 0
            
        except Exception as e:
            self.logger.error(f"Failed to reload agent {agent_name}: {e}")
            return False
    
    async def get_loaded_agents(self) -> List[str]:
        """Get list of loaded agent names"""
        return list(self.loaded_agents.keys())
    
    async def get_agent_class(self, agent_name: str) -> Type[BaseAgent]:
        """Get agent class by name"""
        return self.loaded_agents.get(agent_name)
    
    async def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Get agent configuration"""
        return self.agent_configs.get(agent_name, {})

# Global agent loader instance
agent_loader = AgentLoader()
