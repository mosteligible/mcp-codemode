"""mcp-codemode — MCP server with sandboxed code execution.

Exposes tools for running code, reading/writing files, and listing
directory contents inside isolated Docker containers.

The MCP server runs in stateless-HTTP mode (each request gets a fresh
transport, no session state).  The sandbox container pool is managed
by the FastMCP app lifespan so it persists across requests.
"""

from __future__ import annotations

import contextlib
import logging
from contextlib import AsyncExitStack

import uvicorn
from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import Mount

from config import settings
from core.sandbox import pool  # module-level singleton
from middleware import FastMCPContextMiddleware
from tools import register_tools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── FastMCP app lifecycle ────────────────────────────────────────────
# The pool lifecycle is tied to FastMCP app lifespan so it
# survives across stateless MCP requests.


@contextlib.asynccontextmanager
async def app_lifespan(_app: Starlette):
    """Start shared resources and enter mounted MCP app lifespan."""
    logger.info(
        "Starting sandbox pool — image=%s pool_size=%d",
        settings.sandbox_image,
        settings.pool_size,
    )
    await pool.start()
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(mcp_app.router.lifespan_context(mcp_app))
        await stack.enter_async_context(mcp_no_execute_app.router.lifespan_context(mcp_no_execute_app))
        logger.info("MCP server ready at http://%s:%d/mcp", settings.mcp_host, settings.mcp_port)
        logger.info(
            "MCP server ready at http://%s:%d/mcp-no-code-execute",
            settings.mcp_host,
            settings.mcp_port,
        )
        yield
    logger.info("Shutting down sandbox pool")
    await pool.shutdown()


# ── MCP server ───────────────────────────────────────────────────────

mcp = FastMCP(
    "mcp-codemode",
    instructions=(
        "This MCP server provides sandboxed code execution. "
        "Use the execute_code tool to run Python, Bash with curl, or Node.js code "
        "in an isolated Docker container with network access to public sites and apis. It has no access" \
        "to the host system and all file operations are confined to the /workspace directory. "
        "Use the sandbox file tools (sandbox_read_file, sandbox_write_file, "
        "sandbox_list_files) to interact with the /workspace directory inside "
        "the sandbox."
    ),
)

# Register all tools onto the mcp instance
register_tools(mcp)

mcp_no_execute = FastMCP(
    "mcp-codemode-no-execute",
    instructions=(
        "This MCP server does not expose code execution tools. "
        "Use endpoint /mcp for code execution and sandbox file operations."
    ),
)


mcp_app = mcp.http_app(
    path="/",
    transport="streamable-http",
    stateless_http=True,
    json_response=True,
    middleware=[Middleware(FastMCPContextMiddleware)],
)

mcp_no_execute_app = mcp_no_execute.http_app(
    path="/",
    transport="streamable-http",
    stateless_http=True,
    json_response=True,
    middleware=[Middleware(FastMCPContextMiddleware)],
)

app = Starlette(
    routes=[
        Mount("/mcp", app=mcp_app),
        Mount("/mcp-no-code-execute", app=mcp_no_execute_app),
    ],
    lifespan=app_lifespan,
)

if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.mcp_host, port=settings.mcp_port)
