"""
06_Identity_Isolation: Resource sandboxing to prevent any agent from crashing the system
Advanced isolation and resource management for agent safety
"""

import asyncio
import psutil
import threading
import time
import resource
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import multiprocessing
import os
import signal
import uuid

@dataclass
class ResourceLimits:
    max_cpu_percent: float = 50.0  # Max CPU usage per agent
    max_memory_mb: int = 512        # Max memory per agent
    max_execution_time: float = 5.0 # Max execution time
    max_network_requests: int = 100 # Max network requests per minute
    
@dataclass
class AgentSandbox:
    agent_id: str
    process_id: Optional[int] = None
    thread_id: Optional[int] = None
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    status: str = "initialized"  # initialized, running, completed, failed, killed

class ResourceMonitor:
    """Real-time resource monitoring for agent sandboxes"""
    
    def __init__(self):
        self.agent_resources: Dict[str, Dict[str, Any]] = {}
        self.monitoring = False
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Start resource monitoring thread"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
            
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                self._update_resource_usage()
                time.sleep(0.1)  # Monitor every 100ms
            except Exception as e:
                print(f"Resource monitoring error: {e}")
                
    def _update_resource_usage(self):
        """Update resource usage for all active agents"""
        current_process = psutil.Process()
        
        for agent_id, sandbox_info in self.agent_resources.items():
            if sandbox_info.get("status") == "running":
                # Monitor CPU and memory usage
                try:
                    if sandbox_info.get("process_id"):
                        process = psutil.Process(sandbox_info["process_id"])
                        cpu_percent = process.cpu_percent()
                        memory_mb = process.memory_info().rss / 1024 / 1024
                        
                        self.agent_resources[agent_id].update({
                            "cpu_percent": cpu_percent,
                            "memory_mb": memory_mb,
                            "last_update": datetime.now()
                        })
                        
                except psutil.NoSuchProcess:
                    self.agent_resources[agent_id]["status"] = "completed"
                    
    def register_agent(self, agent_id: str, sandbox: AgentSandbox):
        """Register agent for monitoring"""
        self.agent_resources[agent_id] = {
            "sandbox": sandbox,
            "cpu_percent": 0.0,
            "memory_mb": 0.0,
            "network_requests": 0,
            "status": sandbox.status,
            "created_at": sandbox.created_at
        }
        
    def get_resource_usage(self, agent_id: str) -> Dict[str, Any]:
        """Get current resource usage for agent"""
        return self.agent_resources.get(agent_id, {})

class AgentSandboxManager:
    """Advanced sandboxing system for agent isolation"""
    
    def __init__(self):
        self.active_sandboxes: Dict[str, AgentSandbox] = {}
        self.resource_monitor = ResourceMonitor()
        self.executor = ThreadPoolExecutor(max_workers=100)
        self.process_executor = ThreadPoolExecutor(max_workers=20)
        self.resource_monitor.start_monitoring()
        
    async def execute_agent(self, agent_id: str, agent_function: Callable, 
                          input_data: Dict[str, Any], limits: ResourceLimits = None) -> Any:
        """Execute agent in isolated sandbox"""
        limits = limits or ResourceLimits()
        
        # Create sandbox
        sandbox = AgentSandbox(
            agent_id=agent_id,
            resource_limits=limits,
            status="running"
        )
        
        self.active_sandboxes[agent_id] = sandbox
        self.resource_monitor.register_agent(agent_id, sandbox)
        
        try:
            # Execute with resource limits
            if limits.max_memory_mb > 1024:  # Use process isolation for memory-intensive tasks
                result = await self._execute_in_process(agent_id, agent_function, input_data, limits)
            else:
                result = await self._execute_in_thread(agent_id, agent_function, input_data, limits)
                
            sandbox.status = "completed"
            return result
            
        except Exception as e:
            sandbox.status = "failed"
            raise e
            
        finally:
            sandbox.last_activity = datetime.now()
            
    async def _execute_in_thread(self, agent_id: str, agent_function: Callable, 
                               input_data: Dict[str, Any], limits: ResourceLimits) -> Any:
        """Execute agent in isolated thread with resource monitoring"""
        
        def monitored_execution():
            start_time = time.time()
            
            # Set resource limits
            try:
                # Note: resource module only works on Unix systems
                if hasattr(resource, 'RLIMIT_AS'):
                    resource.setrlimit(resource.RLIMIT_AS, 
                                     (limits.max_memory_mb * 1024 * 1024, 
                                      limits.max_memory_mb * 1024 * 1024))
            except (ImportError, OSError):
                pass  # Windows or permission issues
                
            try:
                return agent_function(input_data)
            finally:
                execution_time = time.time() - start_time
                if execution_time > limits.max_execution_time:
                    raise TimeoutError(f"Agent execution exceeded {limits.max_execution_time}s")
                    
        # Execute with timeout
        try:
            future = self.executor.submit(monitored_execution)
            return await asyncio.wait_for(
                asyncio.wrap_future(future),
                timeout=limits.max_execution_time
            )
        except FutureTimeoutError:
            # Cancel the future
            future.cancel()
            raise TimeoutError(f"Agent {agent_id} timed out")
            
    async def _execute_in_process(self, agent_id: str, agent_function: Callable,
                                input_data: Dict[str, Any], limits: ResourceLimits) -> Any:
        """Execute agent in separate process for full isolation"""
        
        def process_execution(queue, func, data, limits):
            """Execute in separate process"""
            try:
                # Set process resource limits
                try:
                    if hasattr(resource, 'RLIMIT_AS'):
                        resource.setrlimit(resource.RLIMIT_AS,
                                         (limits.max_memory_mb * 1024 * 1024,
                                          limits.max_memory_mb * 1024 * 1024))
                except (ImportError, OSError):
                    pass
                    
                result = func(data)
                queue.put(("success", result))
                
            except Exception as e:
                queue.put(("error", str(e)))
                
        # Create process-safe queue
        queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=process_execution,
            args=(queue, agent_function, input_data, limits)
        )
        
        # Update sandbox with process info
        self.active_sandboxes[agent_id].process_id = process.pid
        process.start()
        
        try:
            # Wait for result with timeout
            process.join(timeout=limits.max_execution_time)
            
            if process.is_alive():
                # Kill the process if it's still running
                process.terminate()
                process.join(timeout=1.0)
                if process.is_alive():
                    process.kill()
                    process.join()
                raise TimeoutError(f"Agent {agent_id} process timed out and was killed")
                
            # Get result from queue
            if not queue.empty():
                status, result = queue.get()
                if status == "success":
                    return result
                else:
                    raise Exception(result)
            else:
                raise Exception(f"Agent {agent_id} process failed to return result")
                
        except Exception as e:
            # Ensure process is cleaned up
            if process.is_alive():
                process.terminate()
                process.join(timeout=1.0)
                if process.is_alive():
                    process.kill()
                    process.join()
            raise e
            
    async def kill_agent(self, agent_id: str) -> bool:
        """Force kill an agent"""
        if agent_id not in self.active_sandboxes:
            return False
            
        sandbox = self.active_sandboxes[agent_id]
        
        # Kill process if exists
        if sandbox.process_id:
            try:
                process = psutil.Process(sandbox.process_id)
                process.terminate()
                process.wait(timeout=5.0)
                if process.is_running():
                    process.kill()
                    process.wait()
            except psutil.NoSuchProcess:
                pass
                
        sandbox.status = "killed"
        return True
        
    def get_sandbox_status(self, agent_id: str) -> Optional[AgentSandbox]:
        """Get sandbox status"""
        return self.active_sandboxes.get(agent_id)
        
    def cleanup_completed_sandboxes(self, max_age_hours: int = 1):
        """Clean up old completed sandboxes"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        to_remove = []
        for agent_id, sandbox in self.active_sandboxes.items():
            if (sandbox.status in ["completed", "failed", "killed"] and 
                sandbox.last_activity < cutoff_time):
                to_remove.append(agent_id)
                
        for agent_id in to_remove:
            del self.active_sandboxes[agent_id]
            
    def get_system_resources(self) -> Dict[str, Any]:
        """Get overall system resource usage"""
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "active_sandboxes": len(self.active_sandboxes),
            "running_agents": sum(1 for s in self.active_sandboxes.values() if s.status == "running")
        }
        
    def shutdown(self):
        """Shutdown sandbox manager"""
        self.resource_monitor.stop_monitoring()
        self.executor.shutdown(wait=True)
        self.process_executor.shutdown(wait=True)
        
        # Kill all running processes
        for sandbox in self.active_sandboxes.values():
            if sandbox.process_id and sandbox.status == "running":
                try:
                    process = psutil.Process(sandbox.process_id)
                    process.terminate()
                except psutil.NoSuchProcess:
                    pass
