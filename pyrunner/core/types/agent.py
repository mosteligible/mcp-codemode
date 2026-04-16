import time
from typing import Literal, TypeAlias
from dataclasses import dataclass, field


AgentType: TypeAlias = Literal["static", "dynamic"]


@dataclass
class AgentMetadata:
    name: str
    description: str
    agent_type: AgentType
    created_at: int = field(default=time.time())
    last_used_at: int = field(
        default=time.time(),
        metadata={"description": "Timestamp of the last time this agent was used"},
    )
