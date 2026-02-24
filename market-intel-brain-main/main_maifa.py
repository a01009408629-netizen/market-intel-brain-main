"""
MAIFA Market Intelligence Brain - High-Performance Main Entry Point
Async parallel processing for <5 second execution target
"""

import asyncio
import time
import json
from typing import Dict, List, Any
from datetime import datetime

# Import MAIFA Layers
from 01_Perception_Layer import DataIngestionEngine, NewsFeedProcessor
from 02_Event_Fabric import EventStream, SignalProcessor, FinancialEvent
from 03_Cognitive_Agents.sentiment_analysis import SentimentAgent
from 03_Cognitive_Agents.financial_analysts import HunterAgent
from 03_Cognitive_Agents.sentiment_analysis.filter_agent import FilterAgent
from 04_Unified_Memory_Layer import VectorStore, HistoricalDataManager, StateManager
from 05_Reasoning_Orchestration import OrchestrationEngine, AgentTask, DecisionPriority
from 06_Identity_Isolation import AgentSandboxManager, ResourceLimits
from 07_Outcome_Fusion import DataFusionEngine, TradingInsightGenerator, DataSource

class MarketIntelligenceBrain:
    """High-performance market intelligence system with <5s execution target"""
    
    def __init__(self):
        self.start_time = time.time()
        
        # Initialize MAIFA Layers
        self.perception_layer = DataIngestionEngine()
        self.news_processor = NewsFeedProcessor()
        self.event_fabric = EventStream()
        self.signal_processor = SignalProcessor(self.event_fabric)
        
        # Memory Layer
        self.vector_store = VectorStore()
        self.historical_data = HistoricalDataManager()
        self.state_manager = StateManager()
        
        # Orchestration
        self.orchestration = OrchestrationEngine()
        self.sandbox_manager = AgentSandboxManager()
        
        # Fusion
        self.data_fusion = DataFusionEngine()
        self.insight_generator = TradingInsightGenerator(self.data_fusion)
        
        # Performance tracking
        self.performance_metrics = {
            'total_requests': 0,
            'avg_response_time': 0.0,
            'sub_5s_requests': 0,
            'timeout_requests': 0
        }
        
    async def initialize(self):
        """Initialize all layers and start background processes"""
        print("🚀 Initializing MAIFA Market Intelligence Brain...")
        
        # Start event streaming
        asyncio.create_task(self.event_fabric.start_streaming())
        
        # Start orchestration
        asyncio.create_task(self.orchestration.start_orchestration())
        
        # Register agents with orchestration
        await self._register_agents()
        
        # Register data sources for fusion
        await self._register_data_sources()
        
        print("✅ MAIFA Brain initialized and ready!")
        
    async def _register_agents(self):
        """Register agents with orchestration engine"""
        # Wrap agents for async execution
        async def filter_agent_wrapper(data):
            return await self.sandbox_manager.execute_agent(
                "filter_agent", 
                lambda d: FilterAgent().run(d.get("text", "")),
                data,
                ResourceLimits(max_execution_time=2.0)
            )
            
        async def sentiment_agent_wrapper(data):
            return await self.sandbox_manager.execute_agent(
                "sentiment_agent",
                lambda d: SentimentAgent().run(d.get("text", "")),
                data,
                ResourceLimits(max_execution_time=3.0)
            )
            
        async def hunter_agent_wrapper(data):
            return await self.sandbox_manager.execute_agent(
                "hunter_agent",
                lambda d: HunterAgent().run(d.get("text", "")),
                data,
                ResourceLimits(max_execution_time=2.0)
            )
            
        # Register with orchestration
        self.orchestration.register_agent("filter_agent", filter_agent_wrapper)
        self.orchestration.register_agent("sentiment_agent", sentiment_agent_wrapper)
        self.orchestration.register_agent("hunter_agent", hunter_agent_wrapper)
        
    async def _register_data_sources(self):
        """Register data sources for fusion"""
        sources = [
            DataSource("filter_agent", "sentiment_analysis", weight=0.2, reliability=0.8),
            DataSource("sentiment_agent", "sentiment_analysis", weight=0.3, reliability=0.9),
            DataSource("hunter_agent", "financial_analysts", weight=0.2, reliability=0.7),
            DataSource("technical_analysis", "technical_analysis", weight=0.3, reliability=0.85),
        ]
        
        for source in sources:
            self.data_fusion.register_data_source(source)
            
    async def analyze_market_data(self, text: str, symbol: str = "UNKNOWN") -> Dict[str, Any]:
        """Main analysis pipeline with <5s performance target"""
        request_start = time.time()
        self.performance_metrics['total_requests'] += 1
        
        try:
            # Create timeout for entire pipeline
            timeout_task = asyncio.create_task(asyncio.sleep(4.5))  # 4.5s timeout
            analysis_task = asyncio.create_task(self._execute_analysis_pipeline(text, symbol))
            
            done, pending = await asyncio.wait(
                [timeout_task, analysis_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
                
            if timeout_task in done:
                self.performance_metrics['timeout_requests'] += 1
                return {
                    "status": "timeout",
                    "message": "Analysis exceeded 5-second limit",
                    "execution_time": time.time() - request_start
                }
                
            result = analysis_task.result()
            execution_time = time.time() - request_start
            
            # Update performance metrics
            self._update_performance_metrics(execution_time)
            
            result["execution_time"] = execution_time
            result["performance_target_met"] = execution_time < 5.0
            
            return result
            
        except Exception as e:
            execution_time = time.time() - request_start
            return {
                "status": "error",
                "error": str(e),
                "execution_time": execution_time,
                "performance_target_met": = False
            }
            
    async def _execute_analysis_pipeline(self, text: str, symbol: str) -> Dict[str, Any]:
        """Execute the full analysis pipeline in parallel"""
        
        # Step 1: Create and submit orchestration task
        task = AgentTask(
            task_id=f"analysis_{datetime.now().timestamp()}",
            agent_type="market_analysis",
            input_data={"text": text, "symbol": symbol},
            priority=DecisionPriority.HIGH,
            timeout=4.0  # 4 second timeout for agents
        )
        
        # Submit to orchestration
        await self.orchestration.submit_task(task)
        
        # Step 2: Parallel data processing
        tasks = []
        
        # Filter and sentiment analysis (parallel)
        tasks.append(asyncio.create_task(self._run_filter_analysis(text)))
        tasks.append(asyncio.create_task(self._run_sentiment_analysis(text)))
        tasks.append(asyncio.create_task(self._run_keyword_analysis(text)))
        
        # Wait for all agent analyses
        agent_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Step 3: Process results and create events
        processed_results = {}
        for i, result in enumerate(agent_results):
            if not isinstance(result, Exception):
                agent_name = ["filter", "sentiment", "hunter"][i]
                processed_results[agent_name] = result
                
        # Step 4: Create financial events
        events = self._create_financial_events(text, symbol, processed_results)
        
        # Step 5: Publish events to event fabric
        event_tasks = [self.event_fabric.publish_event(event) for event in events]
        await asyncio.gather(*event_tasks)
        
        # Step 6: Generate fused insight
        insight = await self.insight_generator.generate_insight(symbol)
        
        # Step 7: Store in memory layer
        await self._store_results(symbol, processed_results, insight)
        
        return {
            "status": "success",
            "symbol": symbol,
            "agent_results": processed_results,
            "events_created": len(events),
            "trading_insight": {
                "signal": insight.overall_signal.value,
                "confidence": insight.confidence_score,
                "recommendation": insight.recommendation,
                "risk_factors": insight.risk_factors,
                "opportunities": insight.opportunities
            },
            "system_metrics": await self._get_system_metrics()
        }
        
    async def _run_filter_analysis(self, text: str) -> Dict[str, Any]:
        """Run filter agent analysis"""
        try:
            result = await self.sandbox_manager.execute_agent(
                "filter_agent",
                lambda d: FilterAgent().run(d.get("text", "")),
                {"text": text},
                ResourceLimits(max_execution_time=2.0)
            )
            return result
        except Exception as e:
            return {"error": str(e), "agent": "filter_agent"}
            
    async def _run_sentiment_analysis(self, text: str) -> Dict[str, Any]:
        """Run sentiment agent analysis"""
        try:
            result = await self.sandbox_manager.execute_agent(
                "sentiment_agent",
                lambda d: SentimentAgent().run(d.get("text", "")),
                {"text": text},
                ResourceLimits(max_execution_time=3.0)
            )
            return result
        except Exception as e:
            return {"error": str(e), "agent": "sentiment_agent"}
            
    async def _run_keyword_analysis(self, text: str) -> Dict[str, Any]:
        """Run hunter agent analysis"""
        try:
            result = await self.sandbox_manager.execute_agent(
                "hunter_agent",
                lambda d: HunterAgent().run(d.get("text", "")),
                {"text": text},
                ResourceLimits(max_execution_time=2.0)
            )
            return result
        except Exception as e:
            return {"error": str(e), "agent": "hunter_agent"}
            
    def _create_financial_events(self, text: str, symbol: str, results: Dict[str, Any]) -> List[FinancialEvent]:
        """Create financial events from analysis results"""
        events = []
        
        # Sentiment event
        if "sentiment" in results:
            sentiment_data = results["sentiment"]
            if sentiment_data.get("label") in ["positive", "negative"]:
                events.append(FinancialEvent(
                    event_id=f"sentiment_{datetime.now().timestamp()}",
                    event_type="sentiment_shift",
                    symbol=symbol,
                    data={
                        "sentiment": sentiment_data.get("label"),
                        "polarity": sentiment_data.get("polarity", 0),
                        "source_text": text[:100]  # First 100 chars
                    },
                    timestamp=datetime.now(),
                    priority=3 if sentiment_data.get("label") == "positive" else 4
                ))
                
        # Keyword event
        if "hunter" in results:
            hunter_data = results["hunter"]
            keywords = hunter_data.get("found_keywords", [])
            if len(keywords) > 2:
                events.append(FinancialEvent(
                    event_id=f"keywords_{datetime.now().timestamp()}",
                    event_type="keyword_spike",
                    symbol=symbol,
                    data={
                        "keywords": keywords,
                        "count": len(keywords),
                        "source_text": text[:100]
                    },
                    timestamp=datetime.now(),
                    priority=2
                ))
                
        return events
        
    async def _store_results(self, symbol: str, results: Dict[str, Any], insight):
        """Store results in unified memory layer"""
        # Store in vector store for similarity search
        if "sentiment" in results:
            await self.vector_store.store_embedding(
                f"sentiment_{datetime.now().timestamp()}",
                json.dumps(results["sentiment"]),
                {"symbol": symbol, "type": "sentiment_analysis"}
            )
            
        # Update system state
        await self.state_manager.update_state("last_analysis", {
            "symbol": symbol,
            "timestamp": datetime.now(),
            "results_count": len(results)
        })
        
    async def _get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        orchestration_metrics = await self.orchestration.get_metrics()
        system_resources = self.sandbox_manager.get_system_resources()
        
        return {
            "orchestration": orchestration_metrics,
            "system_resources": system_resources,
            "active_sandboxes": len(self.sandbox_manager.active_sandboxes),
            "memory_usage": system_resources.get("memory_percent", 0)
        }
        
    def _update_performance_metrics(self, execution_time: float):
        """Update performance metrics"""
        if execution_time < 5.0:
            self.performance_metrics['sub_5s_requests'] += 1
            
        total = self.performance_metrics['total_requests']
        current_avg = self.performance_metrics['avg_response_time']
        self.performance_metrics['avg_response_time'] = (
            (current_avg * (total - 1) + execution_time) / total
        )
        
    async def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        total = self.performance_metrics['total_requests']
        if total == 0:
            return {"message": "No requests processed yet"}
            
        return {
            "total_requests": total,
            "avg_response_time": self.performance_metrics['avg_response_time'],
            "sub_5s_success_rate": (self.performance_metrics['sub_5s_requests'] / total) * 100,
            "timeout_rate": (self.performance_metrics['timeout_requests'] / total) * 100,
            "performance_target_met": self.performance_metrics['avg_response_time'] < 5.0,
            "uptime_seconds": time.time() - self.start_time
        }

# Global brain instance
brain = MarketIntelligenceBrain()

async def run_market_intelligence_pipeline(text: str, symbol: str = "UNKNOWN") -> Dict[str, Any]:
    """Main entry point for market intelligence analysis"""
    return await brain.analyze_market_data(text, symbol)

if __name__ == "__main__":
    async def main():
        # Initialize the brain
        await brain.initialize()
        
        # Test with sample data
        sample_text = "Bitcoin price is surging to the moon! 🚀🚀🚀 Market sentiment is extremely bullish with massive volume increase."
        
        print("🚀 Starting Market Intelligence Analysis...")
        print("=" * 60)
        
        start_time = time.time()
        result = await run_market_intelligence_pipeline(sample_text, "BTC")
        execution_time = time.time() - start_time
        
        print(f"⚡ Analysis completed in {execution_time:.2f} seconds")
        print("=" * 60)
        print("📊 ANALYSIS RESULTS:")
        print("=" * 60)
        print(json.dumps(result, indent=2, default=str))
        
        # Performance report
        print("\n" + "=" * 60)
        print("📈 PERFORMANCE REPORT:")
        print("=" * 60)
        performance = await brain.get_performance_report()
        print(json.dumps(performance, indent=2, default=str))
        
    # Run the main function
    asyncio.run(main())
