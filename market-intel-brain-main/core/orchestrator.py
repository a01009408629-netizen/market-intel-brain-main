"""
MAIFA v3 Orchestration Layer - Manages 100+ agents without modification to core
Coordinates the 5-stage workflow: Input → Preprocessing → Classification → Analysis → Aggregation
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from models.schemas import (
    AgentInput, AgentOutput, IntelligenceReport, 
    AgentTask, AgentStatus, Priority, SystemMetrics
)
from models.datatypes import PipelineStage, PipelineResult
from services.agents.registry import agent_registry

class Orchestrator:
    """
    MAIFA v3 Orchestrator - Central coordination of all agents and pipelines
    
    Manages the complete workflow without requiring modifications to core
    when new agents are added to the registry.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("Orchestrator")
        self._active_tasks: Dict[str, AgentTask] = {}
        self._pipeline_stages = [
            "preprocessing",
            "event_classification", 
            "multi_agent_analysis",
            "aggregation"
        ]
        self._system_metrics = SystemMetrics()
        self._orchestrator_lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize orchestrator and register all available agents"""
        self.logger.info("Initializing MAIFA v3 Orchestrator...")
        
        # Auto-discover and register agents
        await self._auto_register_agents()
        
        # Start background monitoring
        asyncio.create_task(self._monitor_system_health())
        
        self.logger.info(f"Orchestrator initialized with {len(await agent_registry.list_agents())} agents")
    
    async def _auto_register_agents(self):
        """Auto-discover and register available agents"""
        # Register legacy agents from existing codebase
        try:
            # Import and register FilterAgent
            from agents.filter_agent import FilterAgent
            await agent_registry.register_legacy_agent(
                "filter_agent", 
                FilterAgent,
                {"type": "filtering", "priority": Priority.HIGH.value}
            )
            
            # Import and register SentimentAgent  
            from agents.sentiment_agent import SentimentAgent
            await agent_registry.register_legacy_agent(
                "sentiment_agent",
                SentimentAgent, 
                {"type": "sentiment", "priority": Priority.MEDIUM.value}
            )
            
            # Import and register HunterAgent
            from agents.hunter_agent import HunterAgent
            await agent_registry.register_legacy_agent(
                "hunter_agent",
                HunterAgent,
                {"type": "keyword", "priority": Priority.MEDIUM.value}
            )
            
            self.logger.info("Legacy agents registered successfully")
            
        except ImportError as e:
            self.logger.warning(f"Could not import legacy agents: {e}")
    
    async def process_request(self, 
                            text: str, 
                            symbol: str = "UNKNOWN",
                            agent_filter: Optional[List[str]] = None) -> IntelligenceReport:
        """
        Main entry point for processing market intelligence requests
        
        Args:
            text: Input text to analyze
            symbol: Financial symbol (default: "UNKNOWN")
            agent_filter: Optional list of specific agents to run
            
        Returns:
            Complete intelligence report
        """
        start_time = datetime.now()
        request_id = f"req_{start_time.timestamp()}"
        
        try:
            self.logger.info(f"Processing request {request_id} for symbol {symbol}")
            
            # Update system metrics
            self._system_metrics.total_requests += 1
            
            # Create standardized input
            agent_input = AgentInput(
                text=text,
                symbol=symbol,
                metadata={"request_id": request_id}
            )
            
            # Execute 5-stage pipeline
            pipeline_results = await self._execute_pipeline(
                agent_input, 
                agent_filter or await agent_registry.list_agents()
            )
            
            # Generate final report
            execution_time = (datetime.now() - start_time).total_seconds()
            report = IntelligenceReport(
                symbol=symbol,
                agent_results=pipeline_results.get("agent_results", {}),
                trading_signal=pipeline_results.get("trading_signal"),
                events_created=pipeline_results.get("events_created", 0),
                system_metrics=self._get_current_metrics(),
                execution_time=execution_time,
                performance_target_met=execution_time < 5.0
            )
            
            # Update performance metrics
            self._update_performance_metrics(execution_time)
            
            self.logger.info(f"Request {request_id} completed in {execution_time:.2f}s")
            return report
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Request {request_id} failed: {e}")
            
            # Return error report
            return IntelligenceReport(
                symbol=symbol,
                system_metrics=self._get_current_metrics(),
                execution_time=execution_time,
                performance_target_met=False
            )
    
    async def _execute_pipeline(self, 
                              input_data: AgentInput, 
                              agent_names: List[str]) -> Dict[str, Any]:
        """Execute the 5-stage MAIFA pipeline"""
        
        # Stage 1: Preprocessing (Filter Agent)
        preprocessing_result = await self._stage_preprocessing(input_data, agent_names)
        
        # Check if filtered as noise
        if preprocessing_result.get("is_noise", False):
            return {
                "agent_results": {"filter_agent": preprocessing_result},
                "events_created": 0,
                "trading_signal": None
            }
        
        # Stage 2: Event Classification
        classification_result = await self._stage_event_classification(
            input_data, preprocessing_result
        )
        
        # Stage 3: Multi-Agent Analysis (Parallel execution)
        analysis_results = await self._stage_multi_agent_analysis(
            input_data, agent_names, classification_result
        )
        
        # Stage 4: Aggregation
        aggregation_result = await self._stage_aggregation(analysis_results)
        
        # Stage 5: Final Report Generation
        final_results = await self._stage_final_report(
            input_data, preprocessing_result, analysis_results, aggregation_result
        )
        
        return final_results
    
    async def _stage_preprocessing(self, 
                                 input_data: AgentInput, 
                                 agent_names: List[str]) -> Dict[str, Any]:
        """Stage 1: Preprocessing - Filter and clean input data"""
        self.logger.debug("Stage 1: Preprocessing")
        
        # Run filter agent first
        filter_result = await agent_registry.execute_agent(
            "filter_agent",
            {"text": input_data.text, "symbol": input_data.symbol},
            timeout=2.0
        )
        
        return filter_result
    
    async def _stage_event_classification(self, 
                                        input_data: AgentInput,
                                        preprocessing_result: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 2: Event Classification - Classify the type of market event"""
        self.logger.debug("Stage 2: Event Classification")
        
        # Simple classification based on keywords and sentiment
        text = input_data.text.lower()
        
        event_type = "general"
        if any(word in text for word in ["price", "market", "stock"]):
            event_type = "price_movement"
        elif any(word in text for word in ["news", "report", "announcement"]):
            event_type = "news_event"
        elif any(word in text for word in ["buy", "sell", "trade"]):
            event_type = "trading_signal"
        
        return {
            "event_type": event_type,
            "confidence": 0.8,  # Simple confidence for now
            "preprocessing_result": preprocessing_result
        }
    
    async def _stage_multi_agent_analysis(self, 
                                         input_data: AgentInput,
                                         agent_names: List[str],
                                         classification_result: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 3: Multi-Agent Analysis - Run agents in parallel"""
        self.logger.debug("Stage 3: Multi-Agent Analysis")
        
        # Prepare input data for agents
        agent_input = {
            "text": input_data.text,
            "symbol": input_data.symbol,
            "metadata": {
                **input_data.metadata,
                "event_type": classification_result.get("event_type")
            }
        }
        
        # Execute agents in parallel (exclude filter agent since already run)
        analysis_agents = [name for name in agent_names if name != "filter_agent"]
        
        if analysis_agents:
            results = await agent_registry.execute_parallel(
                analysis_agents,
                agent_input,
                timeout=3.0
            )
        else:
            results = {}
        
        return results
    
    async def _stage_aggregation(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 4: Aggregation - Combine and weight agent results"""
        self.logger.debug("Stage 4: Aggregation")
        
        # Aggregate sentiment from sentiment agent
        sentiment_data = None
        if "sentiment_agent" in analysis_results:
            sentiment_result = analysis_results["sentiment_agent"]
            if sentiment_result.get("status") == "completed":
                sentiment_data = sentiment_result.get("result", {})
        
        # Aggregate keywords from hunter agent
        keyword_data = None
        if "hunter_agent" in analysis_results:
            hunter_result = analysis_results["hunter_agent"]
            if hunter_result.get("status") == "completed":
                keyword_data = hunter_result.get("result", {})
        
        # Generate simple trading signal
        trading_signal = self._generate_trading_signal(sentiment_data, keyword_data)
        
        return {
            "sentiment_data": sentiment_data,
            "keyword_data": keyword_data,
            "trading_signal": trading_signal,
            "agent_count": len(analysis_results),
            "successful_agents": len([
                r for r in analysis_results.values() 
                if r.get("status") == "completed"
            ])
        }
    
    async def _stage_final_report(self, 
                                input_data: AgentInput,
                                preprocessing_result: Dict[str, Any],
                                analysis_results: Dict[str, Any],
                                aggregation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 5: Final Report Generation"""
        self.logger.debug("Stage 5: Final Report Generation")
        
        # Combine all results
        agent_results = {
            "filter_agent": preprocessing_result,
            **analysis_results
        }
        
        # Count events (simplified)
        events_created = len([r for r in agent_results.values() if r.get("status") == "completed"])
        
        return {
            "agent_results": agent_results,
            "events_created": events_created,
            "trading_signal": aggregation_result.get("trading_signal"),
            "aggregation_summary": aggregation_result
        }
    
    def _generate_trading_signal(self, 
                                sentiment_data: Optional[Dict[str, Any]], 
                                keyword_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Generate simple trading signal from aggregated data"""
        if not sentiment_data and not keyword_data:
            return None
        
        # Simple signal generation logic
        signal_strength = 0.0
        recommendation = "HOLD"
        
        # Factor in sentiment
        if sentiment_data:
            polarity = sentiment_data.get("polarity", 0)
            label = sentiment_data.get("label", "neutral")
            
            if label == "positive":
                signal_strength += abs(polarity) * 0.6
            elif label == "negative":
                signal_strength -= abs(polarity) * 0.6
        
        # Factor in keywords
        if keyword_data:
            keyword_count = keyword_data.get("count", 0)
            signal_strength += min(keyword_count * 0.1, 0.4)
        
        # Generate recommendation
        if signal_strength > 0.5:
            recommendation = "BUY"
        elif signal_strength < -0.5:
            recommendation = "SELL"
        else:
            recommendation = "HOLD"
        
        return {
            "signal": recommendation,
            "strength": abs(signal_strength),
            "confidence": min(abs(signal_strength), 1.0),
            "factors": {
                "sentiment": sentiment_data,
                "keywords": keyword_data
            }
        }
    
    def _update_performance_metrics(self, execution_time: float):
        """Update system performance metrics"""
        if execution_time < 5.0:
            self._system_metrics.sub_5s_requests += 1
        
        total = self._system_metrics.total_requests
        current_avg = self._system_metrics.avg_response_time
        self._system_metrics.avg_response_time = (
            (current_avg * (total - 1) + execution_time) / total
        )
    
    def _get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        return {
            "total_requests": self._system_metrics.total_requests,
            "avg_response_time": self._system_metrics.avg_response_time,
            "sub_5s_requests": self._system_metrics.sub_5s_requests,
            "timeout_requests": self._system_metrics.timeout_requests,
            "active_agents": len(agent_registry._agents) + len(agent_registry._legacy_wrappers)
        }
    
    async def _monitor_system_health(self):
        """Background task to monitor system health"""
        while True:
            try:
                # Check agent health every 60 seconds
                await asyncio.sleep(60)
                health_results = await agent_registry.health_check_all()
                
                unhealthy_agents = [name for name, healthy in health_results.items() if not healthy]
                if unhealthy_agents:
                    self.logger.warning(f"Unhealthy agents detected: {unhealthy_agents}")
                
            except Exception as e:
                self.logger.error(f"Health monitoring failed: {e}")
    
    async def get_orchestrator_status(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator status"""
        registry_info = await agent_registry.get_registry_info()
        
        return {
            "status": "running",
            "active_tasks": len(self._active_tasks),
            "pipeline_stages": self._pipeline_stages,
            "system_metrics": self._get_current_metrics(),
            "agent_registry": registry_info,
            "performance_target_met": self._system_metrics.avg_response_time < 5.0
        }


# Global orchestrator instance
orchestrator = Orchestrator()
