"""
MAIFA v3 Financial Intelligence Platform - Unified Orchestrator Entry Point
Main entry point for the complete 5-stage MAIFA workflow system

This file serves as the unified orchestrator that coordinates:
1. Input → Preprocessing → Event Classification → Multi-Agent Analysis → Aggregation → Final Report
2. All MAIFA v3 components with proper initialization and cleanup
3. Performance monitoring and system health checks
4. Graceful shutdown and error handling
"""

import asyncio
import sys
import os
import time
import json
import signal
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

# Add current directory to Python path for absolute imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import MAIFA v3 components
from core.orchestrator import orchestrator
from core.context import context_manager
from core.governance import governance_manager
from core.event_fabric import event_fabric
from services.data_ingestion import get_orchestrator
from services.sentiment_engine import sentiment_engine
from services.ai_models import ai_models_service
from services.classifier import classifier_service
from services.agents.registry import agent_registry
from pipelines.preprocessing import preprocessing_pipeline
from pipelines.event_classification import event_classification_pipeline
from pipelines.multi_agent_analysis import multi_agent_analysis_pipeline
from pipelines.aggregation import aggregation_pipeline
from utils.logger import maifa_logger, get_logger
from utils.rate_limiter import rate_limiter
from utils.helpers import TimeHelper

# Initialize logger
logger = get_logger("main")

class MAIFASystem:
    """
    MAIFA v3 System Manager - Complete system lifecycle management
    
    Handles initialization, execution, monitoring, and shutdown of all
    MAIFA v3 components in the correct order with proper dependency management.
    """
    
    def __init__(self):
        self.logger = get_logger("MAIFASystem")
        self.start_time = time.time()
        self.is_running = False
        self.is_shutting_down = False
        
        # Component status tracking
        self.component_status = {
            "logger": "not_initialized",
            "context": "not_initialized", 
            "governance": "not_initialized",
            "event_fabric": "not_initialized",
            "services": "not_initialized",
            "agents": "not_initialized",
            "pipelines": "not_initialized",
            "orchestrator": "not_initialized"
        }
        
        # Performance metrics
        self.system_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "sub_5s_requests": 0,
            "system_uptime": 0.0
        }
    
    async def initialize(self) -> bool:
        """Initialize all MAIFA v3 components in dependency order"""
        try:
            self.logger.info("🚀 Initializing MAIFA v3 Financial Intelligence Platform...")
            
            # Stage 1: Core Infrastructure
            await self._initialize_core_infrastructure()
            
            # Stage 2: Services Layer
            await self._initialize_services()
            
            # Stage 3: Agent Registry
            await self._initialize_agents()
            
            # Stage 4: Pipeline Layer
            await self._initialize_pipelines()
            
            # Stage 5: Orchestrator (last, depends on all others)
            await self._initialize_orchestrator()
            
            # Stage 6: Start background processes
            await self._start_background_processes()
            
            self.is_running = True
            initialization_time = time.time() - self.start_time
            
            self.logger.info(f"✅ MAIFA v3 initialized successfully in {initialization_time:.2f}s")
            await self._log_system_status()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ MAIFA v3 initialization failed: {e}")
            await self.shutdown()
            return False
    
    async def _initialize_core_infrastructure(self):
        """Initialize core infrastructure components"""
        self.logger.info("🔧 Initializing core infrastructure...")
        
        # Logger is already initialized via maifa_logger
        self.component_status["logger"] = "initialized"
        
        # Context Manager (Memory Layer)
        self.logger.info("📊 Initializing Context Manager (Memory Layer)...")
        # context_manager is already initialized as global instance
        self.component_status["context"] = "initialized"
        
        # Governance Manager
        self.logger.info("⚖️ Initializing Governance Manager...")
        # governance_manager is already initialized as global instance
        self.component_status["governance"] = "initialized"
        
        # Event Fabric
        self.logger.info("🌐 Initializing Event Fabric...")
        await event_fabric.start_streaming()
        self.component_status["event_fabric"] = "initialized"
        
        # Rate Limiter
        self.logger.info("🚦 Initializing Rate Limiter...")
        # Add default rate limits
        from utils.rate_limiter import add_rate_limit
        add_rate_limit("global_api", 100, 60)  # 100 requests per minute
        add_rate_limit("analysis", 60, 60)     # 60 analyses per minute
        self.component_status["rate_limiter"] = "initialized"
    
    async def _initialize_services(self):
        """Initialize service layer components"""
        self.logger.info("🔌 Initializing services layer...")
        
        # Data Ingestion Service
        self.logger.info("📡 Initializing Data Ingestion Service...")
        await data_ingestion_service.initialize()
        self.component_status["data_ingestion"] = "initialized"
        
        # Sentiment Engine
        self.logger.info("💭 Initializing Sentiment Engine...")
        # sentiment_engine is already initialized as global instance
        self.component_status["sentiment_engine"] = "initialized"
        
        # AI Models Service
        self.logger.info("🤖 Initializing AI Models Service...")
        # ai_models_service is already initialized as global instance
        self.component_status["ai_models"] = "initialized"
        
        # Classifier Service
        self.logger.info("🏷️ Initializing Classifier Service...")
        # classifier_service is already initialized as global instance
        self.component_status["classifier"] = "initialized"
        
        self.component_status["services"] = "initialized"
    
    async def _initialize_agents(self):
        """Initialize agent registry and register agents"""
        self.logger.info("🤝 Initializing agent registry...")
        
        # agent_registry is already initialized as global instance
        # Agents are auto-registered when orchestrator initializes
        
        self.component_status["agents"] = "initialized"
    
    async def _initialize_pipelines(self):
        """Initialize pipeline components"""
        self.logger.info("⚡ Initializing pipeline layer...")
        
        # Preprocessing Pipeline
        self.logger.info("🧹 Initializing Preprocessing Pipeline...")
        # preprocessing_pipeline is already initialized as global instance
        self.component_status["preprocessing"] = "initialized"
        
        # Event Classification Pipeline
        self.logger.info("📋 Initializing Event Classification Pipeline...")
        # event_classification_pipeline is already initialized as global instance
        self.component_status["event_classification"] = "initialized"
        
        # Multi-Agent Analysis Pipeline
        self.logger.info("👥 Initializing Multi-Agent Analysis Pipeline...")
        # multi_agent_analysis_pipeline is already initialized as global instance
        self.component_status["multi_agent_analysis"] = "initialized"
        
        # Aggregation Pipeline
        self.logger.info("🔄 Initializing Aggregation Pipeline...")
        # aggregation_pipeline is already initialized as global instance
        self.component_status["aggregation"] = "initialized"
        
        self.component_status["pipelines"] = "initialized"
    
    async def _initialize_orchestrator(self):
        """Initialize the main orchestrator"""
        self.logger.info("🎯 Initializing Orchestrator...")
        
        await orchestrator.initialize()
        self.component_status["orchestrator"] = "initialized"
    
    async def _start_background_processes(self):
        """Start background monitoring and maintenance processes"""
        self.logger.info("🔄 Starting background processes...")
        
        # Start rate limiter cleanup
        rate_limiter.start_background_cleanup()
        
        # Start system monitoring
        asyncio.create_task(self._system_monitoring_loop())
        
        # Start metrics collection
        asyncio.create_task(self._metrics_collection_loop())
    
    async def process_request(self, 
                            text: str, 
                            symbol: str = "UNKNOWN",
                            agent_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Process a market intelligence request through the complete MAIFA pipeline
        
        Args:
            text: Input text to analyze
            symbol: Financial symbol (default: "UNKNOWN")
            agent_filter: Optional list of specific agents to run
            
        Returns:
            Complete intelligence report with all pipeline results
        """
        if not self.is_running:
            return {
                "status": "error",
                "message": "MAIFA system is not running",
                "timestamp": datetime.now().isoformat()
            }
        
        request_start = time.time()
        request_id = f"req_{request_start}"
        
        try:
            self.logger.info(f"📊 Processing request {request_id} for symbol {symbol}")
            self.system_metrics["total_requests"] += 1
            
            # Process through orchestrator (which runs the 5-stage pipeline)
            result = await orchestrator.process_request(
                text=text,
                symbol=symbol,
                agent_filter=agent_filter
            )
            
            # Update metrics
            execution_time = time.time() - request_start
            self._update_metrics(execution_time, True)
            
            # Log performance
            self.logger.info(f"✅ Request {request_id} completed in {execution_time:.3f}s")
            
            # Return comprehensive result
            return {
                "request_id": request_id,
                "status": "success",
                "symbol": symbol,
                "intelligence_report": result.__dict__ if hasattr(result, '__dict__') else result,
                "system_metrics": self.system_metrics,
                "processing_time": execution_time,
                "performance_target_met": execution_time < 5.0,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            execution_time = time.time() - request_start
            self._update_metrics(execution_time, False)
            
            self.logger.error(f"❌ Request {request_id} failed: {e}")
            
            return {
                "request_id": request_id,
                "status": "error",
                "symbol": symbol,
                "error": str(e),
                "execution_time": execution_time,
                "performance_target_met": False,
                "timestamp": datetime.now().isoformat()
            }
    
    def _update_metrics(self, execution_time: float, success: bool):
        """Update system performance metrics"""
        if success:
            self.system_metrics["successful_requests"] += 1
        else:
            self.system_metrics["failed_requests"] += 1
        
        if execution_time < 5.0:
            self.system_metrics["sub_5s_requests"] += 1
        
        # Update average response time
        total = self.system_metrics["total_requests"]
        current_avg = self.system_metrics["avg_response_time"]
        self.system_metrics["avg_response_time"] = (
            (current_avg * (total - 1) + execution_time) / total
        )
        
        # Update system uptime
        self.system_metrics["system_uptime"] = time.time() - self.start_time
    
    async def _system_monitoring_loop(self):
        """Background system health monitoring"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Monitor component health
                await self._check_component_health()
                
                # Cleanup expired data
                await context_manager.cleanup_expired_entries()
                rate_limiter.cleanup_expired_data()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"System monitoring error: {e}")
    
    async def _check_component_health(self):
        """Check health of all components"""
        try:
            # Check orchestrator
            orchestrator_status = await orchestrator.get_orchestrator_status()
            if orchestrator_status.get("status") != "running":
                self.logger.warning("Orchestrator not healthy")
            
            # Check agent registry
            agent_health = await agent_registry.health_check_all()
            unhealthy_agents = [name for name, healthy in agent_health.items() if not healthy]
            if unhealthy_agents:
                self.logger.warning(f"Unhealthy agents: {unhealthy_agents}")
            
            # Check event fabric
            event_stats = await event_fabric.get_event_stats()
            if event_stats.get("queue_size", 0) > 1000:
                self.logger.warning("Event fabric queue size high")
                
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
    
    async def _metrics_collection_loop(self):
        """Background metrics collection"""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Collect every 5 minutes
                
                # Log system metrics
                self.logger.info(f"📈 System Metrics: {self.system_metrics}")
                
                # Log component stats
                await self._log_component_stats()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics collection error: {e}")
    
    async def _log_component_stats(self):
        """Log statistics from all components"""
        try:
            # Agent registry stats
            agent_stats = await agent_registry.get_registry_info()
            self.logger.info(f"🤖 Agents: {agent_stats['total_agents']} total, {agent_stats['modern_agents']} modern, {agent_stats['legacy_agents']} legacy")
            
            # Event fabric stats
            event_stats = await event_fabric.get_event_stats()
            self.logger.info(f"🌐 Events: {event_stats['events_published']} published, {event_stats['events_delivered']} delivered")
            
            # Governance stats
            governance_stats = await governance_manager.get_governance_status()
            self.logger.info(f"⚖️ Governance: {governance_stats['active_rules']} active rules, {len(governance_stats['blocked_agents'])} blocked agents")
            
        except Exception as e:
            self.logger.error(f"Component stats logging failed: {e}")
    
    async def _log_system_status(self):
        """Log complete system status"""
        self.logger.info("=" * 60)
        self.logger.info("🎯 MAIFA v3 SYSTEM STATUS")
        self.logger.info("=" * 60)
        
        for component, status in self.component_status.items():
            status_emoji = "✅" if status == "initialized" else "❌"
            self.logger.info(f"{status_emoji} {component}: {status}")
        
        self.logger.info("=" * 60)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            # Get status from all components
            orchestrator_status = await orchestrator.get_orchestrator_status()
            agent_status = await agent_registry.get_registry_info()
            event_status = await event_fabric.get_event_stats()
            governance_status = await governance_manager.get_governance_status()
            
            return {
                "system": {
                    "is_running": self.is_running,
                    "uptime_seconds": time.time() - self.start_time,
                    "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                    "component_status": self.component_status
                },
                "metrics": self.system_metrics,
                "components": {
                    "orchestrator": orchestrator_status,
                    "agents": agent_status,
                    "events": event_status,
                    "governance": governance_status
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"System status retrieval failed: {e}")
            return {
                "system": {"is_running": self.is_running, "error": str(e)},
                "timestamp": datetime.now().isoformat()
            }
    
    async def shutdown(self):
        """Graceful shutdown of all components"""
        if self.is_shutting_down:
            return
        
        self.is_shutting_down = True
        self.logger.info("🛑 Shutting down MAIFA v3 system...")
        
        try:
            # Stop background processes
            rate_limiter.stop_background_cleanup()
            
            # Stop event fabric
            await event_fabric.stop_streaming()
            
            # Shutdown services
            await data_ingestion_service.shutdown()
            
            self.is_running = False
            
            shutdown_time = time.time() - self.start_time
            self.logger.info(f"✅ MAIFA v3 shutdown complete. Uptime: {shutdown_time:.2f}s")
            
        except Exception as e:
            self.logger.error(f"❌ Shutdown error: {e}")

# Global system instance
maifa_system = MAIFASystem()

# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    asyncio.create_task(maifa_system.shutdown())

# Main execution functions
async def run_interactive_mode():
    """Run MAIFA in interactive mode"""
    print("\n🚀 MAIFA v3 Financial Intelligence Platform - Interactive Mode")
    print("=" * 60)
    print("Enter 'help' for commands or 'quit' to exit")
    print("=" * 60)
    
    while maifa_system.is_running:
        try:
            user_input = input("\n📊 Enter text to analyze (or command): ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() == 'quit':
                break
            elif user_input.lower() == 'help':
                print_commands()
                continue
            elif user_input.lower() == 'status':
                status = await maifa_system.get_system_status()
                print(json.dumps(status, indent=2, default=str))
                continue
            elif user_input.lower() == 'agents':
                agents = await agent_registry.list_agents()
                print(f"🤖 Available agents: {agents}")
                continue
            
            # Process as analysis request
            symbol = input("📈 Enter symbol (default: UNKNOWN): ").strip() or "UNKNOWN"
            
            print(f"\n🔄 Analyzing: '{user_input}' for {symbol}...")
            result = await maifa_system.process_request(user_input, symbol)
            
            print("\n" + "=" * 60)
            print("📊 ANALYSIS RESULTS:")
            print("=" * 60)
            print(json.dumps(result, indent=2, default=str))
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def print_commands():
    """Print available commands"""
    print("\n📋 Available Commands:")
    print("  help     - Show this help")
    print("  status   - Show system status")
    print("  agents   - List available agents")
    print("  quit     - Exit the program")
    print("  text     - Enter text to analyze (will prompt for symbol)")

async def run_sample_analysis():
    """Run sample analysis for demonstration"""
    print("\n🚀 MAIFA v3 Sample Analysis")
    print("=" * 60)
    
    sample_requests = [
        {
            "text": "Bitcoin price is surging to the moon! 🚀🚀🚀 Market sentiment is extremely bullish with massive volume increase.",
            "symbol": "BTC"
        },
        {
            "text": "Apple stock drops sharply after disappointing earnings report, missing analyst expectations by 15%.",
            "symbol": "AAPL"
        },
        {
            "text": "Federal Reserve signals potential interest rate cuts in response to slowing economic growth and inflation concerns.",
            "symbol": "SPY"
        }
    ]
    
    for i, request in enumerate(sample_requests, 1):
        print(f"\n📊 Sample Analysis {i}: {request['symbol']}")
        print("-" * 40)
        print(f"Text: {request['text']}")
        
        result = await maifa_system.process_request(
            request['text'], 
            request['symbol']
        )
        
        print(f"\n✅ Completed in {result['processing_time']:.3f}s")
        print(f"🎯 Performance Target Met: {result['performance_target_met']}")
        
        if result['status'] == 'success':
            report = result['intelligence_report']
            print(f"📈 Signal: {report.get('trading_signal', {}).get('signal', 'N/A')}")
            print(f"🤖 Agents: {len(report.get('agent_results', {}))}")
            print(f"⚡ Events: {report.get('events_created', 0)}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")

async def main():
    """Main entry point"""
    print("🎯 MAIFA v3 Financial Intelligence Platform")
    print("=" * 60)
    print("Multi-Agent Intelligence for Financial Analysis")
    print("=" * 60)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize system
        if not await maifa_system.initialize():
            print("❌ Failed to initialize MAIFA system")
            return 1
        
        # Check command line arguments
        if len(sys.argv) > 1:
            arg = sys.argv[1].lower()
            if arg == "--sample":
                await run_sample_analysis()
            elif arg == "--interactive":
                await run_interactive_mode()
            else:
                print(f"Unknown argument: {arg}")
                print("Usage: python main.py [--sample|--interactive]")
        else:
            # Default: run sample analysis
            await run_sample_analysis()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        return 0
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 1
    finally:
        # Ensure cleanup
        await maifa_system.shutdown()

if __name__ == "__main__":
    # Run the main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
