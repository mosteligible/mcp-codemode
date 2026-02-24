"""File I/O tools for the sandboxed environment."""

from __future__ import annotations

import posixpath

from core.sandbox import pool


_WORKSPACE_ROOT = "/workspace"


def _safe_path(path: str) -> str:
    """Resolve *path* relative to /workspace and reject traversal attempts."""
    if not path.startswith("/"):
        resolved = posixpath.normpath(posixpath.join(_WORKSPACE_ROOT, path))
    else:
        resolved = posixpath.normpath(path)

    if not resolved.startswith(_WORKSPACE_ROOT):
        raise ValueError(
            f"Path '{path}' resolves outside the sandbox workspace. "
            f"All paths must be within {_WORKSPACE_ROOT}."
        )
    return resolved


def register(mcp) -> None:  # noqa: ANN001
    """Register file I/O tools on the given FastMCP instance."""

    @mcp.tool()
    async def sandbox_read_file(path: str) -> str:
        """Read a file from the sandbox's /workspace directory.

        Args:
            path: File path (relative to /workspace, or absolute within /workspace).

        Returns:
            The file contents as text.
        """
        resolved = _safe_path(path)
        container = await pool.acquire()
        try:
            data = await pool.file_read(container, resolved)
        finally:
            await pool.release(container)
        return data.decode("utf-8", errors="replace")

    @mcp.tool()
    async def sandbox_write_file(path: str, content: str) -> str:
        """Write content to a file in the sandbox's /workspace directory.

        Creates parent directories as needed.

        Args:
            path: File path (relative to /workspace, or absolute within /workspace).
            content: Text content to write.

        Returns:
            Confirmation with the number of bytes written.
        """
        resolved = _safe_path(path)
        container = await pool.acquire()
        try:
            nbytes = await pool.file_write(container, resolved, content.encode("utf-8"))
        finally:
            await pool.release(container)
        return f"Wrote {nbytes} bytes to {resolved}"

    @mcp.tool()
    async def sandbox_list_files(path: str = "/workspace") -> str:
        """List directory contents inside the sandbox.

        Args:
            path: Directory path (default: /workspace). Must be within /workspace.

        Returns:
            Directory listing (ls -la output).
        """
        resolved = _safe_path(path)
        container = await pool.acquire()
        try:
            listing = await pool.file_list(container, resolved)
        finally:
            await pool.release(container)
        return listing
