"""
MAIFA v3 Backpressure & Flow Control
Intelligent queue management with memory protection and request throttling
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import collections

from core.distributed_state import distributed_state_manager
from utils.logger import get_logger

logger = get_logger("backpressure")

class BackpressureAction(Enum):
    ACCEPT = "accept"
    DELAY = "delay"
    DROP = "drop"
    REJECT = "reject"

@dataclass
class BackpressureConfig:
    max_queue_size: int = 10000
    high_watermark: float = 0.8
    low_watermark: float = 0.3
    delay_threshold: float = 0.9
    drop_threshold: float = 0.95
    max_delay: float = 5.0
    cleanup_interval: int = 30

class BackpressureController:
    def __init__(self, name: str, config: BackpressureConfig):
        self.name = name
        self.config = config
        self.queue = collections.deque(maxlen=config.max_queue_size)
        self.metrics = {"total": 0, "dropped": 0, "delayed": 0}
        self._lock = asyncio.Lock()
    
    async def add_request(self, request_data: Dict[str, Any]) -> BackpressureAction:
        async with self._lock:
            self.metrics["total"] += 1
            current_load = len(self.queue) / self.config.max_queue_size
            
            if current_load >= self.config.drop_threshold:
                self.metrics["dropped"] += 1
                return BackpressureAction.DROP
            elif current_load >= self.config.delay_threshold:
                self.metrics["delayed"] += 1
                delay = min(self.config.max_delay, current_load * 2)
                await asyncio.sleep(delay)
                self.queue.append(request_data)
                return BackpressureAction.DELAY
            else:
                self.queue.append(request_data)
                return BackpressureAction.ACCEPT
    
    async def get_request(self) -> Optional[Dict[str, Any]]:
        async with self._lock:
            if self.queue:
                return self.queue.popleft()
            return None

# Global backpressure controllers
backpressure_controllers: Dict[str, BackpressureController] = {}
