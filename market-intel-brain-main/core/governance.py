"""
MAIFA v3 Governance Layer - Rate limiting, quotas, API safety, agent timeouts
Enforces system-wide policies and resource management
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import threading
from collections import defaultdict, deque

from models.schemas import GovernanceRule
from models.datatypes import RateLimitKey, ResourceLimits

class RateLimiter:
    """
    Token bucket rate limiter for API and agent request management
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """Consume tokens if available"""
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def get_available_tokens(self) -> int:
        """Get current available tokens"""
        with self._lock:
            self._refill()
            return int(self.tokens)

class ResourceMonitor:
    """
    Monitor and enforce resource limits for agents
    """
    
    def __init__(self):
        self.logger = logging.getLogger("ResourceMonitor")
        self._agent_resources: Dict[str, Dict[str, Any]] = {}
        self._system_limits = {
            "max_memory_mb": 4096,
            "max_cpu_percent": 80,
            "max_concurrent_agents": 100
        }
    
    async def check_agent_resources(self, 
                                   agent_name: str, 
                                   limits: ResourceLimits) -> bool:
        """Check if agent can run within resource limits"""
        try:
            import psutil
            
            # Check system memory
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > self._system_limits["max_memory_mb"] / 40.96:  # Convert to percent
                self.logger.warning(f"System memory too high: {memory_percent}%")
                return False
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            if cpu_percent > self._system_limits["max_cpu_percent"]:
                self.logger.warning(f"System CPU too high: {cpu_percent}%")
                return False
            
            # Check concurrent agent limit
            active_agents = len(self._agent_resources)
            if active_agents >= self._system_limits["max_concurrent_agents"]:
                self.logger.warning(f"Too many concurrent agents: {active_agents}")
                return False
            
            return True
            
        except ImportError:
            self.logger.warning("psutil not available, skipping resource checks")
            return True
        except Exception as e:
            self.logger.error(f"Resource check failed: {e}")
            return True  # Allow execution if check fails
    
    def register_agent_execution(self, agent_name: str):
        """Register agent execution for monitoring"""
        self._agent_resources[agent_name] = {
            "start_time": time.time(),
            "pid": None  # Could track actual process ID
        }
    
    def unregister_agent_execution(self, agent_name: str):
        """Unregister agent execution"""
        if agent_name in self._agent_resources:
            del self._agent_resources[agent_name]
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system resource status"""
        try:
            import psutil
            
            return {
                "memory_percent": psutil.virtual_memory().percent,
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "active_agents": len(self._agent_resources),
                "max_concurrent_agents": self._system_limits["max_concurrent_agents"]
            }
        except ImportError:
            return {
                "memory_percent": 0,
                "cpu_percent": 0,
                "active_agents": len(self._agent_resources),
                "max_concurrent_agents": self._system_limits["max_concurrent_agents"]
            }

class GovernanceManager:
    """
    MAIFA v3 Governance Manager - Central policy enforcement
    
    Manages rate limiting, quotas, API safety, and agent timeouts
    across the entire system.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("GovernanceManager")
        self._rate_limiters: Dict[RateLimitKey, RateLimiter] = {}
        self._governance_rules: Dict[str, GovernanceRule] = {}
        self._resource_monitor = ResourceMonitor()
        self._blocked_ips: Set[str] = set()
        self._blocked_agents: Set[str] = set()
        self._request_counts: Dict[str, deque] = defaultdict(lambda: deque())
        self._governance_lock = asyncio.Lock()
        
        # Default governance rules
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default governance rules"""
        default_rules = [
            GovernanceRule(
                rule_id="default_agent_limits",
                name="Default Agent Limits",
                description="Default limits for all agents",
                max_requests_per_minute=60,
                max_execution_time=5.0,
                memory_limit_mb=512,
                enabled=True
            ),
            GovernanceRule(
                rule_id="filter_agent_limits",
                name="Filter Agent Limits",
                description="Specific limits for filter agent",
                agent_type="filter_agent",
                max_requests_per_minute=120,
                max_execution_time=2.0,
                memory_limit_mb=256,
                enabled=True
            ),
            GovernanceRule(
                rule_id="sentiment_agent_limits",
                name="Sentiment Agent Limits", 
                description="Specific limits for sentiment agent",
                agent_type="sentiment_agent",
                max_requests_per_minute=60,
                max_execution_time=3.0,
                memory_limit_mb=512,
                enabled=True
            ),
            GovernanceRule(
                rule_id="hunter_agent_limits",
                name="Hunter Agent Limits",
                description="Specific limits for hunter agent", 
                agent_type="hunter_agent",
                max_requests_per_minute=60,
                max_execution_time=2.0,
                memory_limit_mb=256,
                enabled=True
            )
        ]
        
        for rule in default_rules:
            self._governance_rules[rule.rule_id] = rule
    
    async def check_request_allowed(self, 
                                  agent_name: str,
                                  client_ip: str = "unknown") -> tuple[bool, str]:
        """
        Check if a request is allowed based on governance rules
        
        Args:
            agent_name: Name of the agent
            client_ip: Client IP address
            
        Returns:
            Tuple of (allowed, reason)
        """
        # Check if agent is blocked
        if agent_name in self._blocked_agents:
            return False, f"Agent {agent_name} is blocked"
        
        # Check if IP is blocked
        if client_ip in self._blocked_ips:
            return False, f"IP {client_ip} is blocked"
        
        # Get applicable rule
        rule = self._get_applicable_rule(agent_name)
        if not rule or not rule.enabled:
            return False, "No applicable governance rule found"
        
        # Check rate limits
        rate_limit_key = f"{agent_name}:{client_ip}"
        if not self._check_rate_limit(rate_limit_key, rule):
            return False, f"Rate limit exceeded for {agent_name}"
        
        # Check resource limits
        resource_limits = {
            "max_execution_time": rule.max_execution_time,
            "memory_limit_mb": rule.memory_limit_mb
        }
        
        if not await self._resource_monitor.check_agent_resources(agent_name, resource_limits):
            return False, f"Resource limits exceeded for {agent_name}"
        
        return True, "Request allowed"
    
    def _get_applicable_rule(self, agent_name: str) -> Optional[GovernanceRule]:
        """Get the most specific applicable rule for an agent"""
        # Look for agent-specific rule first
        for rule in self._governance_rules.values():
            if rule.agent_type == agent_name and rule.enabled:
                return rule
        
        # Fall back to default rule
        for rule in self._governance_rules.values():
            if rule.agent_type == "*" and rule.enabled:
                return rule
        
        return None
    
    def _check_rate_limit(self, rate_limit_key: str, rule: GovernanceRule) -> bool:
        """Check rate limit using token bucket algorithm"""
        if rate_limit_key not in self._rate_limiters:
            # Create new rate limiter for this key
            capacity = rule.max_requests_per_minute
            refill_rate = rule.max_requests_per_minute / 60.0  # per second
            self._rate_limiters[rate_limit_key] = RateLimiter(capacity, refill_rate)
        
        return self._rate_limiters[rate_limit_key].consume()
    
    async def register_agent_execution(self, agent_name: str):
        """Register agent execution for monitoring"""
        self._resource_monitor.register_agent_execution(agent_name)
    
    async def unregister_agent_execution(self, agent_name: str):
        """Unregister agent execution"""
        self._resource_monitor.unregister_agent_execution(agent_name)
    
    async def block_agent(self, agent_name: str, reason: str = ""):
        """Block an agent from executing"""
        self._blocked_agents.add(agent_name)
        self.logger.warning(f"Agent {agent_name} blocked: {reason}")
    
    async def unblock_agent(self, agent_name: str):
        """Unblock an agent"""
        self._blocked_agents.discard(agent_name)
        self.logger.info(f"Agent {agent_name} unblocked")
    
    async def block_ip(self, client_ip: str, reason: str = ""):
        """Block an IP address"""
        self._blocked_ips.add(client_ip)
        self.logger.warning(f"IP {client_ip} blocked: {reason}")
    
    async def unblock_ip(self, client_ip: str):
        """Unblock an IP address"""
        self._blocked_ips.discard(client_ip)
        self.logger.info(f"IP {client_ip} unblocked")
    
    async def add_governance_rule(self, rule: GovernanceRule) -> bool:
        """Add or update a governance rule"""
        try:
            async with self._governance_lock:
                self._governance_rules[rule.rule_id] = rule
                self.logger.info(f"Governance rule added/updated: {rule.rule_id}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to add governance rule {rule.rule_id}: {e}")
            return False
    
    async def remove_governance_rule(self, rule_id: str) -> bool:
        """Remove a governance rule"""
        try:
            async with self._governance_lock:
                if rule_id in self._governance_rules:
                    del self._governance_rules[rule_id]
                    self.logger.info(f"Governance rule removed: {rule_id}")
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Failed to remove governance rule {rule_id}: {e}")
            return False
    
    async def get_governance_status(self) -> Dict[str, Any]:
        """Get comprehensive governance status"""
        return {
            "active_rules": len([r for r in self._governance_rules.values() if r.enabled]),
            "total_rules": len(self._governance_rules),
            "blocked_agents": list(self._blocked_agents),
            "blocked_ips": list(self._blocked_ips),
            "active_rate_limiters": len(self._rate_limiters),
            "system_resources": self._resource_monitor.get_system_status(),
            "governance_rules": {
                rule_id: {
                    "name": rule.name,
                    "agent_type": rule.agent_type,
                    "max_requests_per_minute": rule.max_requests_per_minute,
                    "max_execution_time": rule.max_execution_time,
                    "memory_limit_mb": rule.memory_limit_mb,
                    "enabled": rule.enabled
                }
                for rule_id, rule in self._governance_rules.items()
            }
        }
    
    async def get_rate_limit_status(self, agent_name: str, client_ip: str = "unknown") -> Dict[str, Any]:
        """Get rate limit status for specific agent/client"""
        rate_limit_key = f"{agent_name}:{client_ip}"
        
        if rate_limit_key in self._rate_limiters:
            limiter = self._rate_limiters[rate_limit_key]
            return {
                "available_tokens": limiter.get_available_tokens(),
                "capacity": limiter.capacity,
                "refill_rate": limiter.refill_rate,
                "is_limited": limiter.get_available_tokens() == 0
            }
        
        return {"status": "no_rate_limiter_found"}
    
    async def cleanup_expired_data(self):
        """Clean up expired rate limiters and old data"""
        current_time = time.time()
        
        # Clean up old rate limiters (remove those not used for 1 hour)
        async with self._governance_lock:
            # This is a simplified cleanup - in production you'd track last usage
            if len(self._rate_limiters) > 1000:  # Arbitrary threshold
                # Remove oldest half
                items = list(self._rate_limiters.items())
                for key, _ in items[:len(items)//2]:
                    del self._rate_limiters[key]
                
                self.logger.info(f"Cleaned up old rate limiters, remaining: {len(self._rate_limiters)}")


# Global governance manager instance
governance_manager = GovernanceManager()
