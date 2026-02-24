"""
MAIFA v3 Agents Package
Base agent framework, registry, and auto-loading system
"""

from .base_agent import BaseAgent, AgentWrapper
from .registry import agent_registry
from .loader import agent_loader

# Auto-load agents on import
import asyncio

async def initialize_agents():
    """Initialize agent system with auto-loading"""
    loaded_count = await agent_loader.auto_load_agents()
    print(f"MAIFA v3 Agents Initialized: {loaded_count} agents loaded")
    return loaded_count

# Global initialization function
def get_agent_registry():
    """Get global agent registry instance"""
    return agent_registry

def get_agent_loader():
    """Get global agent loader instance"""
    return agent_loader
