from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SubAgentTaskRequest(BaseModel):
    agent_name: str = Field(..., description="Registered sub-agent name.")
    task_summary: str = Field(
        ..., description="Short summary of the delegated task for the specialist agent."
    )
    task_input: str = Field(
        ..., description="Concrete task instructions for the specialist."
    )


class SubAgentResult(BaseModel):
    agent_name: str = Field(
        ..., description="Name of the sub-agent that handled the task."
    )
    task_summary: str = Field(
        ..., description="Summary of the task the sub-agent handled."
    )
    result: str = Field(..., description="Normalized result returned by the sub-agent.")
    confidence_or_status: str = Field(
        ..., description="Confidence or execution status of the delegated task."
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Any failure details or issues encountered by the sub-agent.",
    )


class SupervisorResponse(BaseModel):
    summary: str = Field(..., description="Single end-user response from the supervisor.")
    delegated_agents: list[str] = Field(
        default_factory=list,
        description="Names of all sub-agents used while solving the request.",
    )
    results: list[SubAgentResult] = Field(
        default_factory=list,
        description="Structured results produced by delegated sub-agents.",
    )
    status: Literal["completed", "partial", "failed"] = Field(
        ..., description="Overall orchestration status."
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Top-level orchestration errors or unresolved issues.",
    )
