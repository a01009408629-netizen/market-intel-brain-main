from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class AgentMessage:
    id: str
    sender: str
    content: str
    metadata: Dict[str, Any]
