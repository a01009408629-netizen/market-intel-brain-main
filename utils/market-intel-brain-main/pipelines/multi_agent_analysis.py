"""
MAIFA v3 Multi-Agent Analysis Pipeline - Stage 3 of the 5-stage workflow
Coordinates parallel execution of multiple agents
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

from models.schemas import AgentOutput, AgentStatus, Priority
from models.datatypes import PipelineResult
from services.agents.registry import agent_registry
from core.governance import governance_manager
from core.context import context_manager

class MultiAgentAnalysisPipeline:
    """
    MAIFA v3 Multi-Agent Analysis Pipeline - Parallel agent coordination
    
    Handles:
    - Agent selection and routing
    - Parallel agent execution
    - Governance and rate limiting
    - Result collection and validation
    - Performance monitoring
    - Error handling and recovery
    """
    
    def __init__(self):
        self.logger = logging.getLogger("MultiAgentAnalysisPipeline")
        self._execution_strategies = self._initialize_execution_strategies()
        self._agent_capabilities = self._initialize_agent_capabilities()
        self._performance_thresholds = self._initialize_performance_thresholds()
        
    def _initialize_execution_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Initialize different execution strategies"""
        return {
            "parallel": {
                "description": "Execute all agents in parallel",
                "timeout_strategy": "individual",
                "error_handling": "continue",
                "max_concurrent": 10
            },
            "sequential": {
                "description": "Execute agents sequentially",
                "timeout_strategy": "cumulative",
                "error_handling": "stop_on_error",
                "max_concurrent": 1
            },
            "adaptive": {
                "description": "Adaptive execution based on agent type",
                "timeout_strategy": "hybrid",
                "error_handling": "retry",
                "max_concurrent": 5
            },
            "priority_based": {
                "description": "Execute based on agent priority",
                "timeout_strategy": "weighted",
                "error_handling": "fallback",
                "max_concurrent": 3
            }
        }
    
    def _initialize_agent_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Initialize agent capability mappings"""
        return {
            "filter_agent": {
                "category": "preprocessing",
                "priority": 1,
                "typical_duration": 1.0,
                "dependencies": [],
                "resource_requirements": {"memory_mb": 128, "cpu_percent": 10}
            },
            "sentiment_agent": {
                "category": "analysis",
                "priority": 2,
                "typical_duration": 2.0,
                "dependencies": ["filter_agent"],
                "resource_requirements": {"memory_mb": 256, "cpu_percent": 20}
            },
            "hunter_agent": {
                "category": "analysis",
                "priority": 2,
                "typical_duration": 1.5,
                "dependencies": ["filter_agent"],
                "resource_requirements": {"memory_mb": 256, "cpu_percent": 15}
            },
            "risk_agent": {
                "category": "analysis",
                "priority": 3,
                "typical_duration": 3.0,
                "dependencies": ["sentiment_agent"],
                "resource_requirements": {"memory_mb": 512, "cpu_percent": 30}
            },
            "prediction_agent": {
                "category": "prediction",
                "priority": 4,
                "typical_duration": 4.0,
                "dependencies": ["sentiment_agent", "hunter_agent"],
                "resource_requirements": {"memory_mb": 1024, "cpu_percent": 40}
            }
        }
    
    def _initialize_performance_thresholds(self) -> Dict[str, Any]:
        """Initialize performance thresholds and limits"""
        return {
            "max_total_execution_time": 10.0,  # seconds
            "max_agent_execution_time": 5.0,   # seconds per agent
            "min_success_rate": 0.7,          # 70% minimum success rate
            "max_retry_attempts": 2,
            "circuit_breaker_threshold": 5,    # failures before circuit breaking
            "resource_monitoring_interval": 1.0  # seconds
        }
    
    async def process(self, 
                     classification_result: Dict[str, Any],
                     processed_input: Dict[str, Any]) -> PipelineResult:
        """
        Main multi-agent analysis pipeline
        
        Args:
            classification_result: Results from event classification
            processed_input: Preprocessed input data
            
        Returns:
            Multi-agent analysis results
        """
        try:
            self.logger.debug("Starting multi-agent analysis pipeline")
            
            # Step 1: Determine agent selection
            agent_selection = await self._select_agents(classification_result)
            
            # Step 2: Choose execution strategy
            execution_strategy = await self._choose_execution_strategy(agent_selection)
            
            # Step 3: Prepare agent inputs
            agent_inputs = await self._prepare_agent_inputs(processed_input, classification_result)
            
            # Step 4: Execute agents
            execution_results = await self._execute_agents(
                agent_selection, agent_inputs, execution_strategy
            )
            
            # Step 5: Validate and process results
            validated_results = await self._validate_results(execution_results)
            
            # Step 6: Aggregate agent outputs
            aggregated_results = await self._aggregate_agent_outputs(validated_results)
            
            # Step 7: Performance analysis
            performance_analysis = await self._analyze_performance(execution_results)
            
            # Step 8: Create analysis result
            analysis_result = {
                "status": "completed",
                "agent_selection": agent_selection,
                "execution_strategy": execution_strategy,
                "execution_results": execution_results,
                "validated_results": validated_results,
                "aggregated_results": aggregated_results,
                "performance_analysis": performance_analysis,
                "processing_stats": {
                    "total_agents": len(agent_selection),
                    "successful_agents": len([r for r in execution_results if r.get("status") == "completed"]),
                    "failed_agents": len([r for r in execution_results if r.get("status") == "failed"]),
                    "total_execution_time": performance_analysis.get("total_execution_time", 0.0),
                    "average_execution_time": performance_analysis.get("average_execution_time", 0.0),
                    "processing_timestamp": datetime.now().isoformat()
                }
            }
            
            self.logger.debug(f"Multi-agent analysis completed: {len(validated_results)} successful agents")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Multi-agent analysis pipeline failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "stage": "multi_agent_analysis"
            }
    
    async def _select_agents(self, classification_result: Dict[str, Any]) -> List[str]:
        """Select appropriate agents based on classification"""
        try:
            # Get routing info from classification
            routing_info = classification_result.get("routing_info", {})
            required_agents = routing_info.get("required_agents", [])
            
            # Always include filter agent for preprocessing validation
            if "filter_agent" not in required_agents:
                required_agents.insert(0, "filter_agent")
            
            # Get available agents
            available_agents = await agent_registry.list_agents()
            
            # Filter to only available agents
            selected_agents = [
                agent for agent in required_agents
                if agent in available_agents
            ]
            
            # Sort by priority and dependencies
            selected_agents = await self._sort_agents_by_priority(selected_agents)
            
            self.logger.debug(f"Selected {len(selected_agents)} agents: {selected_agents}")
            return selected_agents
            
        except Exception as e:
            self.logger.error(f"Agent selection failed: {e}")
            return ["filter_agent", "sentiment_agent"]  # Fallback agents
    
    async def _sort_agents_by_priority(self, agents: List[str]) -> List[str]:
        """Sort agents by execution priority and dependencies"""
        try:
            # Get agent capabilities
            agent_info = {}
            for agent in agents:
                if agent in self._agent_capabilities:
                    agent_info[agent] = self._agent_capabilities[agent]
                else:
                    agent_info[agent] = {"priority": 999, "dependencies": []}
            
            # Sort by priority first
            sorted_by_priority = sorted(agents, key=lambda x: agent_info[x]["priority"])
            
            # Then resolve dependencies
            final_order = []
            remaining = sorted_by_priority.copy()
            
            while remaining:
                # Find agents with no unmet dependencies
                ready_agents = []
                for agent in remaining:
                    dependencies = agent_info[agent]["dependencies"]
                    unmet_deps = [dep for dep in dependencies if dep not in final_order]
                    
                    if not unmet_deps:
                        ready_agents.append(agent)
                
                if not ready_agents:
                    # Circular dependency or missing dependency
                    # Add remaining agents in priority order
                    final_order.extend(remaining)
                    break
                
                # Add ready agents (highest priority first)
                ready_agents.sort(key=lambda x: agent_info[x]["priority"])
                final_order.append(ready_agents[0])
                remaining.remove(ready_agents[0])
            
            return final_order
            
        except Exception as e:
            self.logger.error(f"Agent sorting failed: {e}")
            return agents  # Return original order on error
    
    async def _choose_execution_strategy(self, agent_selection: List[str]) -> str:
        """Choose optimal execution strategy based on agent selection"""
        try:
            agent_count = len(agent_selection)
            
            # Check for high-priority agents
            has_high_priority = any(
                self._agent_capabilities.get(agent, {}).get("priority", 999) <= 2
                for agent in agent_selection
            )
            
            # Check for resource-intensive agents
            has_resource_intensive = any(
                self._agent_capabilities.get(agent, {}).get("resource_requirements", {}).get("memory_mb", 0) > 512
                for agent in agent_selection
            )
            
            # Choose strategy based on conditions
            if agent_count <= 2:
                return "sequential"
            elif has_high_priority and agent_count <= 4:
                return "priority_based"
            elif has_resource_intensive:
                return "adaptive"
            else:
                return "parallel"
                
        except Exception as e:
            self.logger.error(f"Strategy selection failed: {e}")
            return "parallel"  # Default strategy
    
    async def _prepare_agent_inputs(self, 
                                   processed_input: Dict[str, Any],
                                   classification_result: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Prepare inputs for each agent"""
        try:
            base_input = {
                "text": processed_input.get("text", ""),
                "symbol": processed_input.get("symbol", "UNKNOWN"),
                "metadata": {
                    **processed_input.get("metadata", {}),
                    "classification": classification_result,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            agent_inputs = {}
            
            # Customize inputs for specific agents
            for agent_name in await agent_registry.list_agents():
                agent_input = base_input.copy()
                
                # Add agent-specific metadata
                if agent_name == "sentiment_agent":
                    agent_input["metadata"]["analysis_type"] = "sentiment"
                elif agent_name == "hunter_agent":
                    agent_input["metadata"]["analysis_type"] = "keywords"
                    agent_input["metadata"]["target_keywords"] = [
                        "market", "price", "stock", "bitcoin", "analysis",
                        "trading", "investment", "bullish", "bearish"
                    ]
                elif agent_name == "filter_agent":
                    agent_input["metadata"]["analysis_type"] = "filtering"
                
                agent_inputs[agent_name] = agent_input
            
            return agent_inputs
            
        except Exception as e:
            self.logger.error(f"Agent input preparation failed: {e}")
            return {}
    
    async def _execute_agents(self, 
                             agent_selection: List[str],
                             agent_inputs: Dict[str, Dict[str, Any]],
                             execution_strategy: str) -> List[Dict[str, Any]]:
        """Execute agents using the chosen strategy"""
        try:
            strategy_config = self._execution_strategies[execution_strategy]
            
            if execution_strategy == "parallel":
                return await self._execute_parallel(agent_selection, agent_inputs, strategy_config)
            elif execution_strategy == "sequential":
                return await self._execute_sequential(agent_selection, agent_inputs, strategy_config)
            elif execution_strategy == "adaptive":
                return await self._execute_adaptive(agent_selection, agent_inputs, strategy_config)
            elif execution_strategy == "priority_based":
                return await self._execute_priority_based(agent_selection, agent_inputs, strategy_config)
            else:
                return await self._execute_parallel(agent_selection, agent_inputs, strategy_config)
                
        except Exception as e:
            self.logger.error(f"Agent execution failed: {e}")
            return []
    
    async def _execute_parallel(self, 
                               agent_selection: List[str],
                               agent_inputs: Dict[str, Dict[str, Any]],
                               strategy_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute agents in parallel"""
        try:
            max_concurrent = strategy_config["max_concurrent"]
            timeout = self._performance_thresholds["max_agent_execution_time"]
            
            # Create execution tasks
            tasks = []
            for agent_name in agent_selection:
                if agent_name in agent_inputs:
                    task = asyncio.create_task(
                        self._execute_single_agent(agent_name, agent_inputs[agent_name], timeout)
                    )
                    tasks.append((agent_name, task))
            
            # Execute with concurrency limit
            results = []
            for i in range(0, len(tasks), max_concurrent):
                batch = tasks[i:i + max_concurrent]
                batch_results = await asyncio.gather(
                    *[task for _, task in batch],
                    return_exceptions=True
                )
                
                for (agent_name, _), result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        results.append({
                            "agent_name": agent_name,
                            "status": "failed",
                            "error": str(result),
                            "execution_time": 0.0
                        })
                    else:
                        results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Parallel execution failed: {e}")
            return []
    
    async def _execute_sequential(self, 
                                 agent_selection: List[str],
                                 agent_inputs: Dict[str, Dict[str, Any]],
                                 strategy_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute agents sequentially"""
        try:
            timeout = self._performance_thresholds["max_agent_execution_time"]
            results = []
            
            for agent_name in agent_selection:
                if agent_name in agent_inputs:
                    result = await self._execute_single_agent(
                        agent_name, agent_inputs[agent_name], timeout
                    )
                    results.append(result)
                    
                    # Stop on error if configured
                    if (result.get("status") == "failed" and 
                        strategy_config["error_handling"] == "stop_on_error"):
                        break
            
            return results
            
        except Exception as e:
            self.logger.error(f"Sequential execution failed: {e}")
            return []
    
    async def _execute_adaptive(self, 
                               agent_selection: List[str],
                               agent_inputs: Dict[str, Dict[str, Any]],
                               strategy_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute agents with adaptive strategy"""
        try:
            # Start with parallel execution for lightweight agents
            lightweight_agents = [
                agent for agent in agent_selection
                if self._agent_capabilities.get(agent, {}).get("resource_requirements", {}).get("memory_mb", 0) <= 256
            ]
            
            heavyweight_agents = [
                agent for agent in agent_selection
                if agent not in lightweight_agents
            ]
            
            results = []
            
            # Execute lightweight agents in parallel
            if lightweight_agents:
                parallel_results = await self._execute_parallel(
                    lightweight_agents, agent_inputs, strategy_config
                )
                results.extend(parallel_results)
            
            # Execute heavyweight agents sequentially
            if heavyweight_agents:
                sequential_results = await self._execute_sequential(
                    heavyweight_agents, agent_inputs, strategy_config
                )
                results.extend(sequential_results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Adaptive execution failed: {e}")
            return []
    
    async def _execute_priority_based(self, 
                                     agent_selection: List[str],
                                     agent_inputs: Dict[str, Dict[str, Any]],
                                     strategy_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute agents based on priority"""
        try:
            # Group agents by priority
            priority_groups = {}
            for agent_name in agent_selection:
                priority = self._agent_capabilities.get(agent_name, {}).get("priority", 999)
                if priority not in priority_groups:
                    priority_groups[priority] = []
                priority_groups[priority].append(agent_name)
            
            results = []
            
            # Execute groups in priority order
            for priority in sorted(priority_groups.keys()):
                agents_in_group = priority_groups[priority]
                
                if len(agents_in_group) == 1:
                    # Single agent, execute directly
                    agent_name = agents_in_group[0]
                    if agent_name in agent_inputs:
                        result = await self._execute_single_agent(
                            agent_name, agent_inputs[agent_name],
                            self._performance_thresholds["max_agent_execution_time"]
                        )
                        results.append(result)
                else:
                    # Multiple agents, execute in parallel
                    parallel_results = await self._execute_parallel(
                        agents_in_group, agent_inputs, strategy_config
                    )
                    results.extend(parallel_results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Priority-based execution failed: {e}")
            return []
    
    async def _execute_single_agent(self, 
                                   agent_name: str,
                                   agent_input: Dict[str, Any],
                                   timeout: float) -> Dict[str, Any]:
        """Execute a single agent with governance and monitoring"""
        try:
            start_time = datetime.now()
            
            # Check governance rules
            governance_result = await governance_manager.check_request_allowed(agent_name)
            if not governance_result[0]:
                return {
                    "agent_name": agent_name,
                    "status": "blocked",
                    "error": governance_result[1],
                    "execution_time": 0.0
                }
            
            # Register agent execution for monitoring
            await governance_manager.register_agent_execution(agent_name)
            
            try:
                # Execute the agent
                result = await asyncio.wait_for(
                    agent_registry.execute_agent(agent_name, agent_input, timeout),
                    timeout=timeout
                )
                
                # Calculate execution time
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # Add execution metadata
                result["execution_time"] = execution_time
                result["start_time"] = start_time.isoformat()
                
                return result
                
            except asyncio.TimeoutError:
                execution_time = (datetime.now() - start_time).total_seconds()
                return {
                    "agent_name": agent_name,
                    "status": "timeout",
                    "error": f"Agent execution timed out after {timeout}s",
                    "execution_time": execution_time
                }
            
            finally:
                # Unregister agent execution
                await governance_manager.unregister_agent_execution(agent_name)
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Single agent execution failed for {agent_name}: {e}")
            return {
                "agent_name": agent_name,
                "status": "failed",
                "error": str(e),
                "execution_time": execution_time
            }
    
    async def _validate_results(self, execution_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and filter agent execution results"""
        try:
            validated_results = []
            
            for result in execution_results:
                # Check for required fields
                if not all(field in result for field in ["agent_name", "status"]):
                    continue
                
                # Validate status
                if result["status"] not in ["completed", "failed", "timeout", "blocked"]:
                    result["status"] = "failed"
                    result["error"] = "Invalid status"
                
                # Validate result data for successful executions
                if result["status"] == "completed":
                    if "result" not in result or not isinstance(result["result"], dict):
                        result["status"] = "failed"
                        result["error"] = "Invalid result data"
                
                validated_results.append(result)
            
            return validated_results
            
        except Exception as e:
            self.logger.error(f"Result validation failed: {e}")
            return execution_results  # Return original results on error
    
    async def _aggregate_agent_outputs(self, validated_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate outputs from multiple agents"""
        try:
            aggregation = {
                "successful_agents": [],
                "failed_agents": [],
                "combined_results": {},
                "insights": {},
                "confidence_scores": {},
                "execution_summary": {}
            }
            
            total_confidence = 0.0
            confidence_count = 0
            
            for result in validated_results:
                agent_name = result["agent_name"]
                status = result["status"]
                
                if status == "completed":
                    aggregation["successful_agents"].append(agent_name)
                    
                    # Add result data
                    result_data = result.get("result", {})
                    aggregation["combined_results"][agent_name] = result_data
                    
                    # Extract confidence if available
                    if "confidence" in result_data:
                        aggregation["confidence_scores"][agent_name] = result_data["confidence"]
                        total_confidence += result_data["confidence"]
                        confidence_count += 1
                    
                    # Extract insights
                    if "analysis" in result_data:
                        aggregation["insights"][agent_name] = result_data["analysis"]
                    
                else:
                    aggregation["failed_agents"].append({
                        "agent_name": agent_name,
                        "status": status,
                        "error": result.get("error", "Unknown error")
                    })
            
            # Calculate aggregate confidence
            if confidence_count > 0:
                aggregation["aggregate_confidence"] = total_confidence / confidence_count
            else:
                aggregation["aggregate_confidence"] = 0.0
            
            # Execution summary
            aggregation["execution_summary"] = {
                "total_agents": len(validated_results),
                "success_rate": len(aggregation["successful_agents"]) / len(validated_results),
                "average_confidence": aggregation["aggregate_confidence"],
                "has_failures": len(aggregation["failed_agents"]) > 0
            }
            
            return aggregation
            
        except Exception as e:
            self.logger.error(f"Output aggregation failed: {e}")
            return {}
    
    async def _analyze_performance(self, execution_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance of agent execution"""
        try:
            if not execution_results:
                return {
                    "total_execution_time": 0.0,
                    "average_execution_time": 0.0,
                    "max_execution_time": 0.0,
                    "min_execution_time": 0.0,
                    "success_rate": 0.0
                }
            
            execution_times = [
                result.get("execution_time", 0.0)
                for result in execution_results
            ]
            
            successful_results = [
                result for result in execution_results
                if result.get("status") == "completed"
            ]
            
            total_time = sum(execution_times)
            avg_time = total_time / len(execution_times)
            max_time = max(execution_times)
            min_time = min(execution_times)
            success_rate = len(successful_results) / len(execution_results)
            
            return {
                "total_execution_time": total_time,
                "average_execution_time": avg_time,
                "max_execution_time": max_time,
                "min_execution_time": min_time,
                "success_rate": success_rate,
                "performance_rating": self._calculate_performance_rating(success_rate, avg_time)
            }
            
        except Exception as e:
            self.logger.error(f"Performance analysis failed: {e}")
            return {}
    
    def _calculate_performance_rating(self, success_rate: float, avg_time: float) -> str:
        """Calculate overall performance rating"""
        if success_rate >= 0.9 and avg_time <= 2.0:
            return "excellent"
        elif success_rate >= 0.8 and avg_time <= 3.0:
            return "good"
        elif success_rate >= 0.7 and avg_time <= 5.0:
            return "acceptable"
        else:
            return "poor"
    
    async def get_analysis_stats(self) -> Dict[str, Any]:
        """Get multi-agent analysis pipeline statistics"""
        return {
            "execution_strategies_count": len(self._execution_strategies),
            "agent_capabilities_count": len(self._agent_capabilities),
            "available_strategies": list(self._execution_strategies.keys()),
            "performance_thresholds": self._performance_thresholds,
            "registered_agents": await agent_registry.list_agents()
        }


# Global multi-agent analysis pipeline instance
multi_agent_analysis_pipeline = MultiAgentAnalysisPipeline()
