import time
from typing import Literal, TypeAlias
from dataclasses import dataclass, field


AgentType: TypeAlias = Literal["static", "dynamic"]


@dataclass
class AgentMetadata:
    name: str
    description: str
    agent_type: AgentType
    runtime_key: str
    can_run_in_parallel: bool = False
    capability_summary: str | None = None
    created_at: int = field(default_factory=lambda: int(time.time()))
    last_used_at: int = field(
        default_factory=lambda: int(time.time()),
        metadata={"description": "Timestamp of the last time this agent was used"},
    )
