"""mcp-codemode client — FastAPI server with /chat endpoint.

Uses PydanticAI with MCPServerStreamableHTTP to drive an agentic
tool-use loop against the mcp-codemode MCP server.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from agent import AgentResponse, mcp_server, run_agent
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Keep the MCP server connection open for the app's lifetime."""
    async with mcp_server:
        yield


app = FastAPI(
    title="mcp-codemode client",
    description="LLM-powered chat that uses MCP tools for sandboxed code execution",
    lifespan=lifespan,
)


# ── Request / Response models ────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user message to send to the agent")
    conversation_history: list[dict[str, Any]] | None = Field(
        default=None,
        description=(
            "Optional prior messages (PydanticAI ModelMessage format) "
            "for multi-turn context. Pass back the 'new_messages' field "
            "from a previous ChatResponse."
        ),
    )


class ToolCallInfo(BaseModel):
    round: int
    tool: str
    input: dict[str, Any]
    output: str
    is_error: bool = False


class ChatResponse(BaseModel):
    response: str = Field(..., description="The agent's final text response")
    tool_calls: list[ToolCallInfo] = Field(
        default_factory=list,
        description="Log of tool calls made during this request",
    )
    rounds: int = Field(0, description="Number of LLM requests made")
    new_messages: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "PydanticAI messages from this run — pass back as "
            "conversation_history to continue the conversation."
        ),
    )


# ── Endpoints ────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a message to the LLM agent which can execute code via MCP tools.

    PydanticAI handles the full tool-use loop: the LLM calls MCP tools,
    gets results, and iterates until it produces a final text answer
    (or hits the safety limit on rounds).
    """
    logger.info("Received chat request: %.120s", request.message)

    # Deserialize conversation history if provided
    message_history = None
    if request.conversation_history:
        from pydantic import TypeAdapter
        from pydantic_ai.messages import ModelMessage

        ta = TypeAdapter(list[ModelMessage])
        message_history = ta.validate_python(request.conversation_history)

    result: AgentResponse = await run_agent(
        request.message,
        message_history=message_history,
    )

    return ChatResponse(
        response=result.text,
        tool_calls=[ToolCallInfo(**tc) for tc in result.tool_calls],
        rounds=result.rounds,
        new_messages=[m.model_dump(mode="json") for m in result.new_messages],
    )


@app.get("/tools")
async def list_tools():
    """Return the MCP tools currently available to the agent."""
    tools = await mcp_server.list_tools()
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.inputSchema,
            }
            for t in tools
        ]
    }


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "mcp_url": settings.mcp_server_url}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
