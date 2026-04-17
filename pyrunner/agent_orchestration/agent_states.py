from dataclasses import dataclass, field

from core.types.agent import AgentMetadata


@dataclass
class AgentState:
    agent_metadata: dict[str, AgentMetadata] = field(default_factory=dict)

    def add_agent(self, agent_name: str, metadata: AgentMetadata) -> None:
        """Add a new agent to the state."""
        self.agent_metadata[agent_name] = metadata

    def remove_agent(self, agent_name: str) -> bool:
        """Remove an agent from the state."""
        if agent_name in self.agent_metadata:
            del self.agent_metadata[agent_name]
            return True
        return False

    def get_agent(self, agent_name: str) -> AgentMetadata | None:
        """Retrieve an agent's metadata."""
        return self.agent_metadata.get(agent_name)

    def reset(self) -> None:
        """Reset the agent state to an empty state."""
        self.agent_metadata.clear()
