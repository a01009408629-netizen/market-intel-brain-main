"""
MAIFA v3 Base Agent Definition - Required for 100+ Agents
All agents MUST implement: analyze(), explain(), weights()
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import logging

from models.schemas import AgentInput, AgentOutput, AgentStatus
from models.datatypes import AgentFunction, AsyncAgentFunction

class BaseAgent(ABC):
    """
    MAIFA v3 Base Agent - Abstract base class for all agents
    
    All agents must inherit from this class and implement:
    - analyze(): Main analysis logic
    - explain(): Explain the reasoning
    - weights(): Return confidence weights for different factors
    """
    
    def __init__(self, name: str, logger: Optional[logging.Logger] = None):
        self.name = name
        self.logger = logger or logging.getLogger(f"Agent.{name}")
        self.created_at = datetime.now()
        self.execution_count = 0
        self.total_execution_time = 0.0
        self.last_execution_time = None
        
    @abstractmethod
    async def analyze(self, input_data: AgentInput) -> Dict[str, Any]:
        """
        Main analysis method - must be implemented by all agents
        
        Args:
            input_data: Standardized agent input containing text, symbol, metadata
            
        Returns:
            Dict containing analysis results specific to the agent
        """
        pass
    
    @abstractmethod
    async def explain(self, input_data: AgentInput, result: Dict[str, Any]) -> str:
        """
        Explain the reasoning behind the analysis results
        
        Args:
            input_data: Original input data
            result: Analysis result from analyze() method
            
        Returns:
            Human-readable explanation of the reasoning process
        """
        pass
    
    @abstractmethod
    async def weights(self) -> Dict[str, float]:
        """
        Return confidence weights for different factors considered by this agent
        
        Returns:
            Dict mapping factor names to weight values (0.0 to 1.0)
        """
        pass
    
    async def execute(self, input_data: AgentInput) -> AgentOutput:
        """
        Standard execution wrapper for all agents
        
        Args:
            input_data: Standardized agent input
            
        Returns:
            AgentOutput with standardized format
        """
        start_time = datetime.now()
        status = AgentStatus.RUNNING
        
        try:
            self.logger.info(f"Executing agent {self.name} for symbol {input_data.symbol}")
            
            # Execute the main analysis
            result = await self.analyze(input_data)
            
            # Generate explanation
            explanation = await self.explain(input_data, result)
            
            # Get agent weights
            weights = await self.weights()
            
            # Update metrics
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics(execution_time)
            
            # Prepare output
            output = AgentOutput(
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                result={
                    "analysis": result,
                    "explanation": explanation,
                    "weights": weights,
                    "execution_metadata": {
                        "execution_time": execution_time,
                        "timestamp": start_time.isoformat()
                    }
                },
                execution_time=execution_time,
                timestamp=start_time
            )
            
            self.logger.info(f"Agent {self.name} completed successfully in {execution_time:.2f}s")
            return output
            
        except asyncio.TimeoutError:
            status = AgentStatus.TIMEOUT
            error_msg = f"Agent {self.name} execution timed out"
            self.logger.error(error_msg)
            
        except Exception as e:
            status = AgentStatus.FAILED
            error_msg = f"Agent {self.name} failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return AgentOutput(
            agent_name=self.name,
            status=status,
            result={},
            execution_time=execution_time,
            timestamp=start_time,
            error_message=error_msg if status == AgentStatus.FAILED else None
        )
    
    def _update_metrics(self, execution_time: float):
        """Update internal performance metrics"""
        self.execution_count += 1
        self.total_execution_time += execution_time
        self.last_execution_time = execution_time
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        avg_execution_time = (
            self.total_execution_time / self.execution_count 
            if self.execution_count > 0 else 0.0
        )
        
        return {
            "name": self.name,
            "execution_count": self.execution_count,
            "avg_execution_time": avg_execution_time,
            "last_execution_time": self.last_execution_time,
            "total_execution_time": self.total_execution_time,
            "created_at": self.created_at.isoformat()
        }
    
    def reset_metrics(self):
        """Reset performance metrics"""
        self.execution_count = 0
        self.total_execution_time = 0.0
        self.last_execution_time = None
    
    async def health_check(self) -> bool:
        """
        Perform health check on the agent
        
        Returns:
            True if agent is healthy, False otherwise
        """
        try:
            # Test with minimal input
            test_input = AgentInput(text="health_check", symbol="TEST")
            await self.analyze(test_input)
            return True
        except Exception as e:
            self.logger.error(f"Health check failed for {self.name}: {e}")
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information"""
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "created_at": self.created_at.isoformat(),
            "metrics": self.get_metrics()
        }


class AgentWrapper:
    """
    Wrapper class for legacy agents to work with MAIFA v3 architecture
    """
    
    def __init__(self, legacy_agent_class, name: str):
        self.legacy_agent_class = legacy_agent_class
        self.name = name
        self.logger = logging.getLogger(f"Wrapper.{name}")
    
    async def execute_legacy(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute legacy agent with modern wrapper
        
        Args:
            input_data: Legacy input format
            
        Returns:
            Legacy output format wrapped in modern structure
        """
        try:
            # Create legacy agent instance
            agent = self.legacy_agent_class()
            
            # Execute legacy run method
            result = agent.run(input_data.get("text", ""))
            
            return {
                "agent_name": self.name,
                "status": "completed",
                "result": result,
                "execution_time": 0.0,  # Legacy agents don't track time
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Legacy agent {self.name} failed: {e}")
            return {
                "agent_name": self.name,
                "status": "failed",
                "error": str(e),
                "execution_time": 0.0,
                "timestamp": datetime.now().isoformat()
            }
