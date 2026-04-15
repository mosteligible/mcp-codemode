import time
from dataclasses import dataclass, field


@dataclass
class AgentMetadata:
    name: str
    description: str
    created_at: int = field(default=time.time())
    last_used_at: int = field(
        default=time.time(),
        metadata={"description": "Timestamp of the last time this agent was used"},
    )
