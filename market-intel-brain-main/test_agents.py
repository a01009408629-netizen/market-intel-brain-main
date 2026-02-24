"""
MAIFA v3 Agent System Test
Tests agent loading, registration, and execution
"""

import asyncio
import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from services.agents import initialize_agents, get_agent_registry

async def test_agent_system():
    """Test complete agent system"""
    print("MAIFA v3 Agent System Test")
    print("=" * 50)
    
    try:
        # Initialize agents with auto-loading
        print("Initializing agent system...")
        loaded_count = await initialize_agents()
        print(f"Loaded {loaded_count} agents")
        
        # Get registry
        registry = get_agent_registry()
        
        # List all agents
        print("\nRegistered Agents:")
        agent_names = await registry.list_agents()
        for name in agent_names:
            print(f"  - {name}")
        
        # Get detailed agent info
        print("\nAgent Details:")
        agents_info = await registry.list_agents_info()
        for name, info in agents_info.items():
            print(f"  {name}:")
            print(f"    Type: {info['type']}")
            print(f"    Class: {info['class']}")
            if info.get('metrics'):
                print(f"    Metrics: {info['metrics']}")
        
        # Test agent execution
        if agent_names:
            print(f"\nTesting agent execution: {agent_names[0]}")
            
            test_input = {
                "text": "This is a test message for agent analysis",
                "symbol": "TEST",
                "metadata": {"test": True}
            }
            
            result = await registry.execute_agent(agent_names[0], test_input)
            print(f"Result: {result}")
        
        print("\nAgent system test completed successfully")
        return True
        
    except Exception as e:
        print(f"\nAgent system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_agent_system())
    sys.exit(0 if success else 1)
