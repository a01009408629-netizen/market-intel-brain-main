"""
05_Reasoning_Orchestration: Coordinating decision-making between agents
Advanced orchestration engine for multi-agent coordination and decision-making
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
from concurrent.futures import ThreadPoolExecutor

class DecisionPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

@dataclass
class AgentTask:
    task_id: str
    agent_type: str
    input_data: Dict[str, Any]
    priority: DecisionPriority
    dependencies: List[str] = field(default_factory=list)
    timeout: float = 5.0  # 5-second performance target
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class DecisionResult:
    task_id: str
    agent_results: Dict[str, Any]
    confidence_score: float
    recommendation: str
    metadata: Dict[str, Any]
    execution_time: float

class OrchestrationEngine:
    """High-performance orchestration engine for coordinating 100+ agents"""
    
    def __init__(self):
        self.active_tasks: Dict[str, AgentTask] = {}
        self.agent_registry: Dict[str, Callable] = {}
        self.task_queue = asyncio.Queue(maxsize=1000)
        self.executor = ThreadPoolExecutor(max_workers=50)
        self.running = False
        self.performance_metrics = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'avg_execution_time': 0.0
        }
        
    async def start_orchestration(self):
        """Start the orchestration engine"""
        self.running = True
        # Start multiple orchestration workers for parallel processing
        workers = [asyncio.create_task(self._orchestration_worker()) for _ in range(20)]
        await asyncio.gather(*workers)
        
    async def _orchestration_worker(self):
        """Orchestration worker for processing tasks"""
        while self.running:
            try:
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                await self._execute_task(task)
            except asyncio.TimeoutError:
                continue
                
    async def _execute_task(self, task: AgentTask):
        """Execute task with parallel agent coordination"""
        start_time = datetime.now()
        
        try:
            # Check dependencies
            if not await self._check_dependencies(task):
                await self.task_queue.put(task)  # Requeue for later
                return
                
            # Execute agents in parallel
            agent_tasks = []
            for agent_type in self._get_required_agents(task):
                if agent_type in self.agent_registry:
                    agent_task = asyncio.create_task(
                        self._execute_agent(agent_type, task.input_data, task.timeout)
                    )
                    agent_tasks.append((agent_type, agent_task))
                    
            # Wait for all agents with timeout
            results = {}
            if agent_tasks:
                completed, pending = await asyncio.wait(
                    [task for _, task in agent_tasks],
                    timeout=task.timeout
                )
                
                # Cancel pending tasks
                for pending_task in pending:
                    pending_task.cancel()
                    
                # Collect results
                for (agent_type, _), result_task in zip(agent_tasks, completed):
                    try:
                        results[agent_type] = result_task.result()
                    except Exception as e:
                        results[agent_type] = {"error": str(e)}
                        
            # Generate decision
            decision = await self._generate_decision(task, results)
            
            # Update metrics
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics(execution_time, success=True)
            
            # Store result
            await self._store_decision_result(task, decision, execution_time)
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics(execution_time, success=False)
            print(f"Task execution failed: {e}")
            
    async def _execute_agent(self, agent_type: str, input_data: Dict[str, Any], timeout: float) -> Any:
        """Execute single agent with timeout"""
        try:
            agent_func = self.agent_registry[agent_type]
            if asyncio.iscoroutinefunction(agent_func):
                return await asyncio.wait_for(agent_func(input_data), timeout=timeout)
            else:
                return await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        self.executor, agent_func, input_data
                    ),
                    timeout=timeout
                )
        except asyncio.TimeoutError:
            raise Exception(f"Agent {agent_type} timed out after {timeout}s")
            
    async def _check_dependencies(self, task: AgentTask) -> bool:
        """Check if task dependencies are satisfied"""
        for dep_id in task.dependencies:
            if dep_id not in self.active_tasks:
                return False
        return True
        
    def _get_required_agents(self, task: AgentTask) -> List[str]:
        """Determine which agents are needed for this task"""
        # Logic to determine required agents based on task type
        if task.agent_type == "market_analysis":
            return ["filter_agent", "sentiment_agent", "hunter_agent"]
        elif task.agent_type == "technical_analysis":
            return ["technical_analyst", "volume_analyzer"]
        return [task.agent_type]
        
    async def _generate_decision(self, task: AgentTask, agent_results: Dict[str, Any]) -> DecisionResult:
        """Generate final decision from agent results"""
        # Simple decision logic - enhance with ML models
        confidence = 0.0
        recommendation = "HOLD"
        
        # Analyze sentiment
        if "sentiment_agent" in agent_results:
            sentiment = agent_results["sentiment_agent"]
            if sentiment.get("label") == "positive":
                recommendation = "BUY"
                confidence += 0.3
            elif sentiment.get("label") == "negative":
                recommendation = "SELL"
                confidence += 0.3
                
        # Analyze keywords
        if "hunter_agent" in agent_results:
            keywords = agent_results["hunter_agent"].get("found_keywords", [])
            if len(keywords) > 2:
                confidence += 0.2
                
        return DecisionResult(
            task_id=task.task_id,
            agent_results=agent_results,
            confidence_score=min(confidence, 1.0),
            recommendation=recommendation,
            metadata={"execution_time": datetime.now().isoformat()},
            execution_time=0.0
        )
        
    async def _store_decision_result(self, task: AgentTask, decision: DecisionResult, execution_time: float):
        """Store decision result in memory layer"""
        # This would integrate with the Unified Memory Layer
        pass
        
    def _update_metrics(self, execution_time: float, success: bool):
        """Update performance metrics"""
        self.performance_metrics['total_tasks'] += 1
        if success:
            self.performance_metrics['completed_tasks'] += 1
        else:
            self.performance_metrics['failed_tasks'] += 1
            
        # Update average execution time
        total = self.performance_metrics['total_tasks']
        current_avg = self.performance_metrics['avg_execution_time']
        self.performance_metrics['avg_execution_time'] = (
            (current_avg * (total - 1) + execution_time) / total
        )
        
    async def submit_task(self, task: AgentTask):
        """Submit new task for orchestration"""
        self.active_tasks[task.task_id] = task
        await self.task_queue.put(task)
        
    def register_agent(self, agent_type: str, agent_function: Callable):
        """Register agent function"""
        self.agent_registry[agent_type] = agent_function
        
    async def get_metrics(self) -> Dict[str, Any]:
        """Get orchestration performance metrics"""
        return self.performance_metrics.copy()

class WorkflowManager:
    """Advanced workflow management for complex multi-agent processes"""
    
    def __init__(self, orchestration_engine: OrchestrationEngine):
        self.orchestration = orchestration_engine
        self.workflows: Dict[str, Dict] = {}
        self.workflow_templates = {
            "market_intelligence": {
                "steps": [
                    {"agent": "filter_agent", "timeout": 2.0},
                    {"agent": "sentiment_agent", "timeout": 3.0},
                    {"agent": "hunter_agent", "timeout": 2.0},
                    {"agent": "technical_analyst", "timeout": 4.0}
                ],
                "aggregation": "weighted_voting"
            },
            "risk_assessment": {
                "steps": [
                    {"agent": "volatility_analyzer", "timeout": 3.0},
                    {"agent": "correlation_analyzer", "timeout": 4.0},
                    {"agent": "risk_calculator", "timeout": 2.0}
                ],
                "aggregation": "consensus"
            }
        }
        
    async def execute_workflow(self, workflow_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute predefined workflow"""
        if workflow_name not in self.workflow_templates:
            raise ValueError(f"Unknown workflow: {workflow_name}")
            
        workflow = self.workflow_templates[workflow_name]
        results = {}
        
        for step in workflow["steps"]:
            task = AgentTask(
                task_id=f"{workflow_name}_{step['agent']}_{datetime.now().timestamp()}",
                agent_type=step["agent"],
                input_data=input_data,
                priority=DecisionPriority.MEDIUM,
                timeout=step["timeout"]
            )
            
            # Submit and wait for completion
            await self.orchestration.submit_task(task)
            # In real implementation, we'd wait for result here
            
        return results
