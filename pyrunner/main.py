"""mcp-codemode — MCP server with sandboxed code execution.

Exposes tools for running code, reading/writing files, and listing
directory contents inside isolated Docker containers.

The MCP server runs in stateless-HTTP mode (each request gets a fresh
transport, no session state).  The sandbox container pool is managed
by the *Starlette application* lifespan so it persists across requests.
"""

from __future__ import annotations

import contextlib
import logging

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount

from config import settings
from core.sandbox import pool  # module-level singleton
from tools import register_tools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── MCP server ───────────────────────────────────────────────────────

mcp = FastMCP(
    "mcp-codemode",
    instructions=(
        "This MCP server provides sandboxed code execution. "
        "Use the execute_code tool to run Python, Bash, or Node.js code "
        "in an isolated Docker container with no network access. "
        "Use the sandbox file tools (sandbox_read_file, sandbox_write_file, "
        "sandbox_list_files) to interact with the /workspace directory inside "
        "the sandbox."
    ),
    stateless_http=True,
    json_response=True,
    log_level="INFO",
)

# Register all tools onto the mcp instance
register_tools(mcp)

# ── Starlette wrapper ────────────────────────────────────────────────
# The pool lifecycle is tied to the *Starlette* app lifespan so it
# survives across stateless MCP requests.


@contextlib.asynccontextmanager
async def app_lifespan(_app: Starlette):
    """Start the sandbox pool on startup and tear it down on shutdown."""
    logger.info(
        "Starting sandbox pool — image=%s pool_size=%d",
        settings.sandbox_image,
        settings.pool_size,
    )
    await pool.start()
    async with mcp.session_manager.run():
        logger.info("MCP server ready at http://%s:%d/mcp", settings.mcp_host, settings.mcp_port)
        yield
    logger.info("Shutting down sandbox pool")
    await pool.shutdown()


app = Starlette(
    routes=[Mount("/", app=mcp.streamable_http_app())],
    lifespan=app_lifespan,
)

if __name__ == "__main__":
    uvicorn.run(app, host=settings.mcp_host, port=settings.mcp_port)

