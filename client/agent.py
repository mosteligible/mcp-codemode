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

logger = logging.getLogger(__name__)

# Ensure PydanticAI can pick up the API key from our config
if settings.openai_api_key and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key

SYSTEM_PROMPT = """\
You are a helpful coding assistant with access to a sandboxed code execution \
environment. You can run Python, Bash, and Node.js code, and read/write files \
inside an isolated /workspace directory.

When the user asks you to write, run, or debug code:
1. Use the execute_code tool to run code.
2. Use sandbox_write_file / sandbox_read_file / sandbox_list_files for file ops.
3. Examine tool results carefully and iterate if there are errors.
4. Always share the final output or answer with the user.

Keep explanations concise. Prefer showing results over describing what you \
would do.\
"""

# ── MCP server connection ────────────────────────────────────────────
# Managed via ``async with mcp_server`` in the FastAPI lifespan so the
# connection stays open for the app's entire lifetime.
mcp_server = MCPServerStreamableHTTP(settings.mcp_server_url)

# ── PydanticAI Agent ─────────────────────────────────────────────────
# Model is NOT set at init time to avoid requiring OPENAI_API_KEY at
# import.  It is passed to ``agent.run()`` at request time instead.
agent = Agent(
    instructions=SYSTEM_PROMPT,
    toolsets=[mcp_server],
)


# ── Response helpers ─────────────────────────────────────────────────
@dataclass
class AgentResponse:
    """Structured response from the agent."""

    text: str
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
                    tool_calls[idx]["output"] = str(part.content)

    return tool_calls


async def run_agent(
    user_message: str,
    *,
    message_history: list[ModelMessage] | None = None,
) -> AgentResponse:
    """Run the PydanticAI agent and return the structured result.

    Args:
        user_message: The latest user message.
        message_history: Optional prior PydanticAI messages for multi-turn context.

    Returns:
        AgentResponse with the final text, tool call log, round count,
        and the new messages produced by this run.
    """
    logger.info("Running agent for: %.120s", user_message)

    result = await agent.run(
        user_message,
        model=f"openai:{settings.openai_model}",
        message_history=message_history,
        usage_limits=UsageLimits(request_limit=settings.max_tool_rounds),
    )

    new_messages = result.new_messages()
    tool_calls = extract_tool_calls(new_messages)

    return AgentResponse(
        text=result.output,
        tool_calls=tool_calls,
        rounds=result.usage().requests,
        new_messages=new_messages,
    )
