"""Tool registration entrypoint.

Each tool module exposes a ``register(mcp)`` function that decorates its
tools onto the given FastMCP instance.  This avoids circular imports since
``main.py`` creates the ``mcp`` instance and passes it here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_tools(mcp: FastMCP) -> None:
    """Discover and register all tool modules."""
    from tools import execute_code, file_ops

    execute_code.register(mcp)
    file_ops.register(mcp)
