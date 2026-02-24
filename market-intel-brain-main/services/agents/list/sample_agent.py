"""
MAIFA v3 Sample Agent
Example implementation showing how to create a new agent
"""

from typing import Dict, Any
from services.agents.base_agent import BaseAgent
from models.schemas import AgentInput, AgentOutput, AgentStatus

class SampleAgent(BaseAgent):
    """
    Sample agent implementation for MAIFA v3
    Demonstrates the required interface and best practices
    """
    
    CONFIG = {
        "name": "SampleAgent",
        "description": "Example agent for testing",
        "version": "1.0.0",
        "timeout": 5.0,
        "max_retries": 3
    }
    
    def __init__(self):
        super().__init__("SampleAgent")
    
    async def analyze(self, input_data: AgentInput) -> Dict[str, Any]:
        """
        Main analysis method
        
        Args:
            input_data: Standardized agent input
            
        Returns:
            Analysis results specific to this agent
        """
        # Simple analysis logic
        text = input_data.text.lower()
        symbol = input_data.symbol
        
        # Example analysis
        result = {
            "text_length": len(text),
            "symbol": symbol,
            "sentiment": "neutral",
            "confidence": 0.5,
            "keywords": ["sample", "analysis"],
            "analysis_type": "sample"
        }
        
        return result
    
    async def explain(self, input_data: AgentInput, result: Dict[str, Any]) -> str:
        """
        Explain the reasoning behind the analysis
        
        Args:
            input_data: Original input data
            result: Analysis result from analyze() method
            
        Returns:
            Human-readable explanation
        """
        explanation = f"""
        SampleAgent Analysis Explanation:
        - Analyzed text: '{input_data.text[:50]}...'
        - Symbol: {input_data.symbol}
        - Text length: {result.get('text_length', 0)} characters
        - Sentiment: {result.get('sentiment', 'unknown')}
        - Confidence: {result.get('confidence', 0):.2f}
        - Keywords found: {result.get('keywords', [])}
        
        This is a sample analysis for demonstration purposes.
        """
        
        return explanation.strip()
    
    async def weights(self) -> Dict[str, float]:
        """
        Return confidence weights for different factors
        
        Returns:
            Dict mapping factor names to weight values
        """
        return {
            "text_length": 0.2,
            "sentiment": 0.3,
            "keywords": 0.3,
            "symbol_relevance": 0.2
        }
