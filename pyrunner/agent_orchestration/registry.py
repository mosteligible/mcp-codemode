from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import Agent

from agent_orchestration.agent_states import AgentState
from core.types.agent import AgentMetadata


@dataclass
class AgentRegistry:
    state: AgentState = field(default_factory=AgentState)
    _agents: dict[str, Agent[Any, Any]] = field(default_factory=dict)

    def register(
        self,
        *,
        name: str,
        agent: Agent[Any, Any],
        description: str,
        runtime_key: str,
        can_run_in_parallel: bool,
        capability_summary: str | None = None,
    ) -> None:
        self._agents[name] = agent
        self.state.add_agent(
            name,
            AgentMetadata(
                name=name,
                description=description,
                agent_type="static",
                runtime_key=runtime_key,
                can_run_in_parallel=can_run_in_parallel,
                capability_summary=capability_summary or description,
            ),
        )

    def get_agent(self, name: str) -> Agent[Any, Any]:
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' is not registered.")

        metadata = self.state.get_agent(name)
        if metadata is not None:
            metadata.last_used_at = int(time.time())
        return self._agents[name]

    def get_metadata(self, name: str) -> AgentMetadata:
        metadata = self.state.get_agent(name)
        if metadata is None:
            raise KeyError(f"Agent '{name}' metadata is not registered.")
        return metadata

    def list_metadata(self) -> list[AgentMetadata]:
        return list(self.state.agent_metadata.values())

    def available_agent_names(self) -> list[str]:
        return [metadata.name for metadata in self.list_metadata()]

    def can_run_in_parallel(self, name: str) -> bool:
        return self.get_metadata(name).can_run_in_parallel


def build_parallel_limiter(max_parallel_agents: int) -> asyncio.Semaphore:
    return asyncio.Semaphore(max(1, max_parallel_agents))
