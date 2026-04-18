from __future__ import annotations

import asyncio
import importlib
from types import SimpleNamespace

import pytest

from agent_orchestration.models import (
    SubAgentResult,
    SubAgentTaskRequest,
    SupervisorResponse,
)
from agent_orchestration.registry import AgentRegistry
from agent_orchestration.supervisor_agent import (
    SupervisorDependencies,
    _run_sub_agent,
    _run_sub_agents_parallel,
)


class FakeUsage:
    pass


class FakeRunResult:
    def __init__(self, output: SubAgentResult):
        self.output = output


class FakeSpecialistAgent:
    def __init__(self, result: SubAgentResult, delay: float = 0.0):
        self.result = result
        self.delay = delay
        self.prompts: list[str] = []

    async def run(self, prompt: str, usage=None):
        self.prompts.append(prompt)
        if self.delay:
            await asyncio.sleep(self.delay)
        return FakeRunResult(self.result)


def build_ctx(registry: AgentRegistry, max_parallel: int = 3) -> SimpleNamespace:
    deps = SupervisorDependencies(
        registry=registry,
        parallel_limiter=asyncio.Semaphore(max_parallel),
    )
    return SimpleNamespace(deps=deps, usage=FakeUsage())


def register_fake_agent(
    registry: AgentRegistry,
    *,
    name: str,
    result: SubAgentResult,
    can_run_in_parallel: bool = True,
    delay: float = 0.0,
) -> FakeSpecialistAgent:
    agent = FakeSpecialistAgent(result=result, delay=delay)
    registry.register(
        name=name,
        agent=agent,  # type: ignore[arg-type]
        description=f"{name} description",
        runtime_key=name.lower(),
        can_run_in_parallel=can_run_in_parallel,
    )
    return agent


def test_subagent_result_contract() -> None:
    result = SubAgentResult(
        agent_name="GithubAgent",
        task_summary="Inspect open pull requests",
        result="Found 3 open pull requests.",
        confidence_or_status="completed",
    )

    assert result.agent_name == "GithubAgent"
    assert result.errors == []


def test_supervisor_response_contract() -> None:
    response = SupervisorResponse(
        summary="Combined answer",
        delegated_agents=["GithubAgent"],
        results=[
            SubAgentResult(
                agent_name="GithubAgent",
                task_summary="Check repositories",
                result="Repository list",
                confidence_or_status="completed",
            )
        ],
        status="completed",
    )

    assert response.status == "completed"
    assert response.delegated_agents == ["GithubAgent"]


@pytest.mark.asyncio
async def test_github_only_request_routes_only_to_github_agent() -> None:
    registry = AgentRegistry()
    github_agent = register_fake_agent(
        registry,
        name="GithubAgent",
        result=SubAgentResult(
            agent_name="GithubAgent",
            task_summary="Inspect issues",
            result="Found repository issues.",
            confidence_or_status="completed",
        ),
    )
    documentation_agent = register_fake_agent(
        registry,
        name="DocumentationAgent",
        result=SubAgentResult(
            agent_name="DocumentationAgent",
            task_summary="Summarize docs",
            result="Documentation summary.",
            confidence_or_status="completed",
        ),
    )
    ctx = build_ctx(registry)

    result = await _run_sub_agent(
        ctx,
        SubAgentTaskRequest(
            agent_name="GithubAgent",
            task_summary="Inspect issues",
            task_input="Find GitHub issue information for the requested repository.",
        ),
    )

    assert result.agent_name == "GithubAgent"
    assert len(github_agent.prompts) == 1
    assert documentation_agent.prompts == []


@pytest.mark.asyncio
async def test_non_github_request_does_not_invoke_github_agent() -> None:
    registry = AgentRegistry()
    github_agent = register_fake_agent(
        registry,
        name="GithubAgent",
        result=SubAgentResult(
            agent_name="GithubAgent",
            task_summary="Inspect repo",
            result="GitHub output",
            confidence_or_status="completed",
        ),
    )
    documentation_agent = register_fake_agent(
        registry,
        name="DocumentationAgent",
        result=SubAgentResult(
            agent_name="DocumentationAgent",
            task_summary="Summarize architecture",
            result="Architecture summary",
            confidence_or_status="completed",
        ),
    )
    ctx = build_ctx(registry)

    result = await _run_sub_agent(
        ctx,
        SubAgentTaskRequest(
            agent_name="DocumentationAgent",
            task_summary="Summarize architecture",
            task_input="Explain the documented architecture for pyrunner.",
        ),
    )

    assert result.agent_name == "DocumentationAgent"
    assert len(documentation_agent.prompts) == 1
    assert github_agent.prompts == []


@pytest.mark.asyncio
async def test_mixed_request_invokes_multiple_agents_in_parallel() -> None:
    registry = AgentRegistry()
    github_agent = register_fake_agent(
        registry,
        name="GithubAgent",
        result=SubAgentResult(
            agent_name="GithubAgent",
            task_summary="Check repo health",
            result="Repository health summary",
            confidence_or_status="completed",
        ),
        delay=0.01,
    )
    documentation_agent = register_fake_agent(
        registry,
        name="DocumentationAgent",
        result=SubAgentResult(
            agent_name="DocumentationAgent",
            task_summary="Summarize runtime docs",
            result="Runtime docs summary",
            confidence_or_status="completed",
        ),
        delay=0.01,
    )
    ctx = build_ctx(registry, max_parallel=2)

    results = await _run_sub_agents_parallel(
        ctx,
        [
            SubAgentTaskRequest(
                agent_name="GithubAgent",
                task_summary="Check repo health",
                task_input="Analyze GitHub state for the repository.",
            ),
            SubAgentTaskRequest(
                agent_name="DocumentationAgent",
                task_summary="Summarize runtime docs",
                task_input="Summarize the runtime architecture documentation.",
            ),
        ],
    )

    assert [result.agent_name for result in results] == [
        "GithubAgent",
        "DocumentationAgent",
    ]
    assert len(github_agent.prompts) == 1
    assert len(documentation_agent.prompts) == 1


@pytest.mark.asyncio
async def test_partial_failure_returns_bounded_result() -> None:
    registry = AgentRegistry()
    register_fake_agent(
        registry,
        name="GithubAgent",
        result=SubAgentResult(
            agent_name="GithubAgent",
            task_summary="Check repo",
            result="Repository answer",
            confidence_or_status="completed",
        ),
    )
    ctx = build_ctx(registry)

    results = await _run_sub_agents_parallel(
        ctx,
        [
            SubAgentTaskRequest(
                agent_name="GithubAgent",
                task_summary="Check repo",
                task_input="Analyze the repository state.",
            ),
            SubAgentTaskRequest(
                agent_name="MissingAgent",
                task_summary="Unknown task",
                task_input="This agent does not exist.",
            ),
        ],
    )

    assert results[0].confidence_or_status == "completed"
    assert results[1].confidence_or_status == "failed"
    assert results[1].errors


@pytest.mark.asyncio
async def test_sequential_delegation_path_handles_unknown_agent() -> None:
    ctx = build_ctx(AgentRegistry())

    result = await _run_sub_agent(
        ctx,
        SubAgentTaskRequest(
            agent_name="UnknownAgent",
            task_summary="Unknown task",
            task_input="No-op",
        ),
    )

    assert result.confidence_or_status == "failed"
    assert "not registered" in result.errors[0]


def test_config_loading_for_supervisor_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPERVISOR_AGENT_MODEL", "openai:gpt-5.4-mini")
    monkeypatch.setenv("DEFAULT_STATIC_AGENT_MODEL", "openai:gpt-5.3-mini")
    monkeypatch.setenv("GITHUB_AGENT_MODEL", "openai:gpt-5.3")
    monkeypatch.setenv("SUPERVISOR_MAX_PARALLEL_AGENTS", "7")
    monkeypatch.setenv("SUPERVISOR_TOOL_TIMEOUT", "45")

    config_module = importlib.import_module("config")
    config_module = importlib.reload(config_module)

    assert config_module.settings.supervisor_agent_model == "openai:gpt-5.4-mini"
    assert config_module.settings.default_static_agent_model == "openai:gpt-5.3-mini"
    assert config_module.settings.github_agent_model == "openai:gpt-5.3"
    assert config_module.settings.supervisor_max_parallel_agents == 7
    assert config_module.settings.supervisor_tool_timeout == 45
