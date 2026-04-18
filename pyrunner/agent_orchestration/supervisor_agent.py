from __future__ import annotations

import asyncio
from dataclasses import dataclass

from pydantic_ai import Agent, RunContext

from agent_orchestration.models import (
    SubAgentResult,
    SubAgentTaskRequest,
    SupervisorResponse,
)
from agent_orchestration.registry import AgentRegistry, build_parallel_limiter
from agent_orchestration.static_agents import DocumentationAgent, GithubAgent
from config import settings


@dataclass
class SupervisorDependencies:
    registry: AgentRegistry
    parallel_limiter: asyncio.Semaphore


def build_static_registry() -> AgentRegistry:
    registry = AgentRegistry()
    registry.register(
        name="GithubAgent",
        agent=GithubAgent,
        description="Handles GitHub repository analysis, GitHub API lookups, and code execution for GitHub tasks.",
        runtime_key="github",
        can_run_in_parallel=True,
        capability_summary="GitHub repositories, issues, pull requests, and code execution-backed GitHub analysis.",
    )
    registry.register(
        name="DocumentationAgent",
        agent=DocumentationAgent,
        description="Handles repository documentation, architecture summaries, and README-backed questions.",
        runtime_key="documentation",
        can_run_in_parallel=True,
        capability_summary="Repository documentation, README guidance, and documented architecture behavior.",
    )
    return registry


STATIC_AGENT_REGISTRY = build_static_registry()


def get_supervisor_dependencies(
    registry: AgentRegistry | None = None,
) -> SupervisorDependencies:
    resolved_registry = registry or STATIC_AGENT_REGISTRY
    return SupervisorDependencies(
        registry=resolved_registry,
        parallel_limiter=build_parallel_limiter(settings.supervisor_max_parallel_agents),
    )


SupervisorAgent = Agent[SupervisorDependencies, SupervisorResponse](
    model=settings.supervisor_agent_model,
    name="SupervisorAgent",
    output_type=SupervisorResponse,
    instructions="""You are the single user-facing supervisor agent for pyrunner.

Your job is to decide whether a request should be solved directly by you or delegated
to one or more specialist sub-agents.

Rules:
- You own the final response and must return exactly one structured supervisor response.
- Delegate only when a specialist agent clearly improves the answer.
- Prefer a single specialist when one agent can handle the request.
- Use parallel delegation only for independent specialist tasks that can be solved concurrently.
- When multiple specialists are used, synthesize the final answer, resolve contradictions,
  and note any missing information.
- If no registered specialist is relevant, answer directly with no delegated agents.
- Do not expose internal orchestration mechanics unless they help explain limitations.
""",
    tool_timeout=settings.supervisor_tool_timeout,
    retries=2,
)


@SupervisorAgent.system_prompt
def add_registered_agents(ctx: RunContext[SupervisorDependencies]) -> str:
    lines = ["Available specialist agents:"]
    for metadata in ctx.deps.registry.list_metadata():
        parallel_note = (
            "parallel-safe" if metadata.can_run_in_parallel else "sequential-only"
        )
        lines.append(
            f"- {metadata.name}: {metadata.capability_summary or metadata.description} ({parallel_note})"
        )
    return "\n".join(lines)


async def _run_sub_agent(
    ctx: RunContext[SupervisorDependencies], request: SubAgentTaskRequest
) -> SubAgentResult:
    try:
        agent = ctx.deps.registry.get_agent(request.agent_name)
    except KeyError as exc:
        return SubAgentResult(
            agent_name=request.agent_name,
            task_summary=request.task_summary,
            result="",
            confidence_or_status="failed",
            errors=[str(exc)],
        )

    prompt = (
        f"Delegated task summary: {request.task_summary}\n"
        f"Specialist instructions:\n{request.task_input}"
    )

    try:
        run_result = await asyncio.wait_for(
            agent.run(prompt, usage=ctx.usage),
            timeout=settings.supervisor_tool_timeout,
        )
        output = run_result.output
        if not output.agent_name:
            output.agent_name = request.agent_name
        if not output.task_summary:
            output.task_summary = request.task_summary
        return output
    except Exception as exc:  # pragma: no cover - defensive branch
        return SubAgentResult(
            agent_name=request.agent_name,
            task_summary=request.task_summary,
            result="",
            confidence_or_status="failed",
            errors=[str(exc)],
        )


async def _run_sub_agents_parallel(
    ctx: RunContext[SupervisorDependencies], requests: list[SubAgentTaskRequest]
) -> list[SubAgentResult]:
    if not requests:
        return []

    async def _limited_run(request: SubAgentTaskRequest) -> SubAgentResult:
        try:
            can_run_in_parallel = ctx.deps.registry.can_run_in_parallel(
                request.agent_name
            )
        except KeyError:
            return await _run_sub_agent(ctx, request)

        if not can_run_in_parallel:
            return await _run_sub_agent(ctx, request)

        async with ctx.deps.parallel_limiter:
            return await _run_sub_agent(ctx, request)

    return await asyncio.gather(*(_limited_run(request) for request in requests))


@SupervisorAgent.tool
async def delegate_to_agent(
    ctx: RunContext[SupervisorDependencies], request: SubAgentTaskRequest
) -> SubAgentResult:
    """Delegate a bounded task to one specialist agent."""

    return await _run_sub_agent(ctx, request)


@SupervisorAgent.tool
async def delegate_to_agents_parallel(
    ctx: RunContext[SupervisorDependencies], requests: list[SubAgentTaskRequest]
) -> list[SubAgentResult]:
    """Delegate independent tasks to multiple specialist agents in parallel."""

    return await _run_sub_agents_parallel(ctx, requests)


async def run_supervisor(
    prompt: str,
    *,
    deps: SupervisorDependencies | None = None,
):
    return await SupervisorAgent.run(prompt, deps=deps or get_supervisor_dependencies())


def run_supervisor_sync(
    prompt: str,
    *,
    deps: SupervisorDependencies | None = None,
):
    return SupervisorAgent.run_sync(prompt, deps=deps or get_supervisor_dependencies())
