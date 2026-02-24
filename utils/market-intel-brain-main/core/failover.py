"""
MAIFA v3 Failover & Graceful Degradation
Comprehensive failover system with partial results and automatic recovery
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

from core.distributed_state import distributed_state_manager
from utils.logger import get_logger

logger = get_logger("failover")

class FailoverStrategy(Enum):
    ACTIVE_PASSIVE = "active_passive"
    ACTIVE_ACTIVE = "active_active"
    GRACEFUL_DEGRADATION = "graceful_degradation"

@dataclass
class FailoverConfig:
    strategy: FailoverStrategy = FailoverStrategy.GRACEFUL_DEGRADATION
    health_check_interval: int = 10
    failure_threshold: int = 3
    recovery_threshold: int = 2
    max_failover_time: float = 60.0
    enable_partial_results: bool = True
    backup_timeout: float = 30.0

class FailoverManager:
    def __init__(self, service_name: str, config: FailoverConfig):
        self.service_name = service_name
        self.config = config
        self.logger = get_logger(f"FailoverManager.{service_name}")
        self.primary_active = True
        self.backup_active = False
        self.failure_count = 0
        self.recovery_count = 0
        self.last_failover = 0.0
        self.last_health_check = 0.0
        
    async def execute_with_failover(self, 
                                   primary_func: Callable,
                                   backup_func: Callable,
                                   *args, **kwargs) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            if self.primary_active:
                # Try primary
                result = await self._execute_with_timeout(primary_func, *args, **kwargs)
                await self._record_success("primary", time.time() - start_time)
                return {"status": "success", "source": "primary", "result": result}
            else:
                # Use backup
                result = await self._execute_with_timeout(backup_func, *args, **kwargs)
                await self._record_success("backup", time.time() - start_time)
                return {"status": "success", "source": "backup", "result": result}
                
        except Exception as e:
            if self.primary_active:
                self.failure_count += 1
                await self._handle_primary_failure(e, backup_func, args, kwargs)
            else:
                await self._handle_backup_failure(e)
            
            return {
                "status": "failed", 
                "source": "backup" if not self.primary_active else "primary",
                "error": str(e),
                "partial_results": await self._get_partial_results()
            }
    
    async def _execute_with_timeout(self, func: Callable, *args, **kwargs) -> Any:
        try:
            return await asyncio.wait_for(func(*args, **kwargs), timeout=self.config.backup_timeout)
        except asyncio.TimeoutError:
            raise Exception(f"Function execution timed out after {self.config.backup_timeout}s")
    
    async def _handle_primary_failure(self, error: Exception, backup_func: Callable, args: tuple, kwargs: dict):
        self.logger.error(f"Primary service failed: {error}")
        
        if self.failure_count >= self.config.failure_threshold:
            await self._initiate_failover(backup_func, args, kwargs)
        elif self.config.enable_partial_results:
            # Try to get partial results
            partial = await self._get_partial_results()
            if partial:
                self.logger.info("Returning partial results due to primary failure")
                return {"status": "partial", "source": "primary", "result": partial}
    
    async def _initiate_failover(self, backup_func: Callable, args: tuple, kwargs: dict):
        self.logger.warning(f"Initiating failover for {self.service_name}")
        self.primary_active = False
        self.backup_active = True
        self.last_failover = time.time()
        
        # Store failover state
        await distributed_state_manager.set_state(
            f"failover:{self.service_name}:state",
            {"primary_active": False, "backup_active": True, "timestamp": time.time()},
            ttl=3600
        )
        
        # Try backup immediately
        try:
            result = await backup_func(*args, **kwargs)
            await self._record_success("backup", 0)
            return {"status": "success", "source": "backup", "result": result}
        except Exception as e:
            self.logger.error(f"Backup service also failed: {e}")
            return {"status": "failed", "source": "backup", "error": str(e)}
    
    async def _get_partial_results(self) -> Optional[Dict[str, Any]]:
        # Try to get cached or partial results
        return await distributed_state_manager.get_state(
            f"partial_results:{self.service_name}"
        )
    
    async def _record_success(self, source: str, response_time: float):
        if source == "primary":
            self.failure_count = 0
            if not self.primary_active:
                # Recovery detected
                self.recovery_count += 1
                if self.recovery_count >= self.config.recovery_threshold:
                    await self._recover_primary()
        else:
            # Backup success
            pass
        
        # Store metrics
        await distributed_state_manager.set_state(
            f"failover:{self.service_name}:metrics",
            {
                "last_success_source": source,
                "last_success_time": time.time(),
                "response_time": response_time,
                "failure_count": self.failure_count,
                "recovery_count": self.recovery_count
            },
            ttl=3600
        )
    
    async def _recover_primary(self):
        self.logger.info(f"Primary service {self.service_name} recovered")
        self.primary_active = True
        self.backup_active = False
        self.recovery_count = 0
        
        await distributed_state_manager.set_state(
            f"failover:{self.service_name}:state",
            {"primary_active": True, "backup_active": False, "timestamp": time.time()},
            ttl=3600
        )

# Global failover managers
failover_managers: Dict[str, FailoverManager] = {}
