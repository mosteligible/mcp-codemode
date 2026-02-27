"""PydanticAI agent with MCP toolset for sandboxed code execution.

PydanticAI's Agent drives the full tool-use loop automatically:
  1. Send user prompt + MCP tools to the LLM.
  2. If the LLM returns tool calls, PydanticAI executes them via MCP.
  3. Results are fed back to the LLM until it produces a final text answer.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.usage import UsageLimits

from config import settings
from log import app_logger

logger = logging.getLogger(__name__)

# Ensure PydanticAI can pick up the API key from our config
if settings.openai_api_key and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key

SYSTEM_PROMPT = f"""
You are a helpful coding assistant with access to a sandboxed code execution
environment. You can run Python, Bash, and Node.js code, and read/write files
inside an isolated /workspace directory.

The tool registry under /workspace/pyrunner/tools/registry is intended to host
operation-specific tools that an LLM can invoke (for example, dedicated
modules for Microsoft Graph and GitHub operations).

When tasks involve external APIs (especially Microsoft Graph APIs and GitHub
APIs), use the API proxy available from inside the sandbox. The proxy injects
authentication tokens automatically so you do NOT need to supply any tokens or
credentials.

Proxy base URLs (usable from the sandbox with curl or Python requests):
  - Microsoft Graph: http://host.docker.internal:{settings.port}/graph/
    Example: curl http://host.docker.internal:{settings.port}/graph/me
  - GitHub:          http://host.docker.internal:{settings.port}/github/
    Example: curl http://host.docker.internal:{settings.port}/github/users/octocat

The proxy auto-prepends the Graph API version (v1.0), so use paths like
/graph/me rather than /graph/v1.0/me.

For POST requests, pass the JSON body as-is:
  curl -X POST http://host.docker.internal:{settings.port}/graph/me/sendMail \\
       -H "Content-Type: application/json" -d '{{"message": ...}}'

Understand that whenever you need to make external api calls or run code to
complete a task, you should use the execute_code tool to run code in the sandbox.
You have following options for executing code in the sandbox:
1. Use the execute_code tool to run code.
2. Use sandbox_write_file / sandbox_read_file / sandbox_list_files for file ops.
3. Examine tool results carefully and iterate if there are errors.
4. Always share the final output or answer with the user.

Keep explanations concise. Prefer showing results over describing what you would do.
"""

CONCRETE_TOOLS_SYSTEM_PROMPT = f"""
You are a task-focused assistant using the no-code-execute MCP server only.
You do NOT have code execution or sandbox file tools.

Tool schemas (name, description, parameters, required fields) come from the MCP
server at runtime and are the source of truth.

Operating rules:
- Use tools directly when facts are needed; do not guess.
- Ask for missing required arguments before making a tool call.
- Do not invent identifiers (message_id, site_id, list_id, drive_id, chat_id, team_id).
- For Microsoft Graph tools, auth is provided via request context middleware; do not
  ask the user for tokens unless a tool result indicates auth failure.
- Prefer minimal calls first, then expand only as needed.
- When returning results, summarize clearly and include key IDs for next steps.

Workflow hints:
- For attachments, get message IDs first from mailbox messages.
- For SharePoint items, discover site/list/drive IDs before listing contents.
- For broad requests, start with high-level listing tools, then drill down.

Keep responses concise, factual, and action-oriented.
"""

# ── MCP server connection ────────────────────────────────────────────
# Managed via ``async with mcp_server`` in the FastAPI lifespan so the
# connection stays open for the app's entire lifetime.
mcp_server = MCPServerStreamableHTTP(settings.mcp_server_url)
mcp_server_no_code_execute = MCPServerStreamableHTTP(settings.mcp_server_no_code_execute_url)

# ── PydanticAI Agent ─────────────────────────────────────────────────
# Model is NOT set at init time to avoid requiring OPENAI_API_KEY at
# import.  It is passed to ``agent.run()`` at request time instead.
agent = Agent(
    instructions=SYSTEM_PROMPT,
    toolsets=[mcp_server],
)
concrete_tool_agent = Agent(
    instructions=CONCRETE_TOOLS_SYSTEM_PROMPT,
    toolsets=[mcp_server_no_code_execute],
)


# ── Response helpers ─────────────────────────────────────────────────
@dataclass
class AgentResponse:
    """Structured response from the agent."""

    text: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    requests: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    rounds: int = 0
    new_messages: list[ModelMessage] = field(default_factory=list)


def extract_tool_calls(messages: list[ModelMessage]) -> list[dict[str, Any]]:
    """Walk through PydanticAI messages and extract tool-call info."""
    tool_calls: list[dict[str, Any]] = []
    pending: dict[str, int] = {}  # tool_call_id -> index in tool_calls
    round_num = 0

    for msg in messages:
        if isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, ToolCallPart):
                    round_num += 1
                    idx = len(tool_calls)
                    args = part.args if isinstance(part.args, dict) else {}
                    tool_calls.append(
                        {
                            "round": round_num,
                            "tool": part.tool_name,
                            "input": args,
                            "output": "",
                            "is_error": False,
                        }
                    )
                    if part.tool_call_id:
                        pending[part.tool_call_id] = idx

        elif isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, ToolReturnPart) and part.tool_call_id in pending:
                    idx = pending.pop(part.tool_call_id)
                    content = str(part.content)
                    tool_calls[idx]["output"] = content
                    # MCP errors surface as text starting with known prefixes
                    tool_calls[idx]["is_error"] = getattr(part, "is_error", False) or any(
                        content.lstrip().startswith(prefix)
                        for prefix in ("Error", "error", "Traceback", "Exception")
                    )

    return tool_calls


async def run_agent(
    user_message: str,
    message_history: list[ModelMessage] | None = None,
    use_code_exec_agent: bool = False,
) -> AgentResponse:
    """Run the PydanticAI agent and return the structured result.

    Args:
        user_message: The latest user message.
        message_history: Optional prior PydanticAI messages for multi-turn context.
        use_code_exec_agent: Whether to use the code-execution agent with broader tool access
            or the no-code agent with only non-code tools.

    Returns:
        AgentResponse with the final text, tool call log, round count,
        and the new messages produced by this run.
    """
    logger.info("Running agent for: %.120s", user_message)

    history: list[ModelMessage] = list(message_history or [])

    if use_code_exec_agent:
        app_logger.info("Using code-execution agent with broader tool access.")
        result = await agent.run(
            user_message,
            model=f"openai:{settings.openai_model}",
            message_history=history,
            usage_limits=UsageLimits(request_limit=settings.max_tool_rounds),
        )
    else:
        app_logger.info("Using no-code agent with limited tool access.")
        result = await concrete_tool_agent.run(
            user_message,
            model=f"openai:{settings.openai_model}",
            message_history=history,
            usage_limits=UsageLimits(request_limit=settings.max_tool_rounds),
        )

    usage = result.usage()
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens
    total_tokens = usage.total_tokens
    usage.requests
    new_messages = result.new_messages()
    tool_calls = extract_tool_calls(new_messages)
    total_requests = usage.requests

    # If any tool call returned an error, retry once with accumulated history so
    # the LLM can see what went wrong and attempt a corrected approach.
    if any(tc["is_error"] for tc in tool_calls):
        logger.warning("Tool errors detected – retrying with error context.")
        history = history + new_messages
        retry_result = await agent.run(
            "One or more tool calls above returned errors. "
            "Review the errors carefully and try a corrected approach to complete the original task.",
            model=f"openai:{settings.openai_model}",
            message_history=history,
            usage_limits=UsageLimits(request_limit=settings.max_tool_rounds),
        )
        usage = retry_result.usage()
        retry_messages = retry_result.new_messages()
        tool_calls += extract_tool_calls(retry_messages)
        total_requests += usage.requests
        new_messages = new_messages + retry_messages
        result = retry_result
        input_tokens += usage.input_tokens
        output_tokens += usage.output_tokens
        total_tokens += usage.total_tokens

    return AgentResponse(
        text=result.output,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        requests=total_requests,
        tool_calls=tool_calls,
        rounds=total_requests,
        new_messages=new_messages,
    )
