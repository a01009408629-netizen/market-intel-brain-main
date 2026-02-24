"""
MAIFA v3 Schema Layer - Data contracts for every input/output object
Defines standardized schemas for all system components
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
import uuid

class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class MarketData:
    """Raw market data input schema"""
    symbol: str
    price: float
    volume: int
    timestamp: datetime
    source: str
    additional_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class NewsItem:
    """News item input schema"""
    title: str
    content: str
    source: str
    timestamp: datetime
    sentiment_score: float = 0.0
    relevance_score: float = 0.0

@dataclass
class AgentInput:
    """Standard input schema for all agents"""
    text: str
    symbol: str = "UNKNOWN"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentOutput:
    """Standard output schema for all agents"""
    agent_name: str
    status: AgentStatus
    result: Dict[str, Any]
    execution_time: float
    timestamp: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None

@dataclass
class FilterResult:
    """Filter agent specific output"""
    original_text: str
    cleaned_text: str
    noise_score: int
    is_noise: bool

@dataclass
class SentimentResult:
    """Sentiment agent specific output"""
    polarity: float
    label: str  # positive, negative, neutral
    confidence: float

@dataclass
class KeywordResult:
    """Hunter agent specific output"""
    found_keywords: List[str]
    count: int
    relevance_score: float

@dataclass
class FinancialEvent:
    """Event fabric event schema"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    symbol: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    priority: Priority = Priority.MEDIUM

@dataclass
class TradingSignal:
    """Final trading signal output"""
    signal: SignalType
    confidence: float
    recommendation: str
    risk_factors: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None

@dataclass
class IntelligenceReport:
    """Final intelligence report schema"""
    symbol: str
    timestamp: datetime = field(default_factory=datetime.now)
    agent_results: Dict[str, AgentOutput] = field(default_factory=dict)
    trading_signal: Optional[TradingSignal] = None
    events_created: int = 0
    system_metrics: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    performance_target_met: bool = False

@dataclass
class SystemMetrics:
    """System performance metrics"""
    total_requests: int = 0
    avg_response_time: float = 0.0
    sub_5s_requests: int = 0
    timeout_requests: int = 0
    active_agents: int = 0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0

@dataclass
class AgentTask:
    """Orchestration task schema"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_type: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    priority: Priority = Priority.MEDIUM
    timeout: float = 5.0
    created_at: datetime = field(default_factory=datetime.now)
    status: AgentStatus = AgentStatus.IDLE

@dataclass
class ContextState:
    """Memory layer context state"""
    session_id: str
    symbol: str
    data: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)
    ttl_seconds: int = 3600

@dataclass
class GovernanceRule:
    """Governance layer rule definition"""
    rule_id: str
    name: str
    description: str
    agent_type: str = "*"
    max_requests_per_minute: int = 100
    max_execution_time: float = 5.0
    memory_limit_mb: int = 512
    enabled: bool = True
