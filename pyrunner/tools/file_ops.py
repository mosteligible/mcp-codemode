"""File I/O tools for the sandboxed environment."""

from __future__ import annotations

import posixpath

from fastmcp import FastMCP

from core.sandbox import pool
from log import app_logger


_WORKSPACE_ROOT = "/workspace"


def _safe_path(path: str) -> str:
    """Resolve *path* relative to /workspace and reject traversal attempts."""
    app_logger.info("[file_ops] Resolving path | input_path=%r", path)
    if not path.startswith("/"):
        resolved = posixpath.normpath(posixpath.join(_WORKSPACE_ROOT, path))
    else:
        resolved = posixpath.normpath(path)

    if not resolved.startswith(_WORKSPACE_ROOT):
        app_logger.warning(
            "[file_ops] Rejected path traversal | input_path=%r | resolved_path=%r",
            path,
            resolved,
        )
        raise ValueError(
            f"Path '{path}' resolves outside the sandbox workspace. "
            f"All paths must be within {_WORKSPACE_ROOT}."
        )
    app_logger.info("[file_ops] Resolved path | input_path=%r | resolved_path=%r", path, resolved)
    return resolved


def register(mcp: FastMCP) -> None:
    """Register file I/O tools on the given FastMCP instance."""

    @mcp.tool()
    async def sandbox_read_file(path: str) -> str:
        """Read a file from the sandbox's /workspace directory.

        Args:
            path: File path (relative to /workspace, or absolute within /workspace).

        Returns:
            The file contents as text.
        """
        app_logger.info("[sandbox_read_file] Request received | path=%r", path)
        resolved = _safe_path(path)
        container = await pool.acquire()
        app_logger.info(
            "[sandbox_read_file] Acquired container | container_id=%s | resolved_path=%r",
            container.short_id,
            resolved,
        )
        try:
            data = await pool.file_read(container, resolved)
            app_logger.info(
                "[sandbox_read_file] Read completed | container_id=%s | resolved_path=%r | bytes=%d | content=%r",
                container.short_id,
                resolved,
                len(data),
                data.decode("utf-8", errors="replace"),
            )
        finally:
            await pool.release(container)
            app_logger.info(
                "[sandbox_read_file] Released container | container_id=%s",
                container.short_id,
            )
        response = data.decode("utf-8", errors="replace")
        app_logger.info(
            "[sandbox_read_file] Returning response | resolved_path=%r | response_length=%d",
            resolved,
            len(response),
        )
        return response

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
        app_logger.info(
            "[sandbox_write_file] Request received | path=%r | content_length=%d | content=%r",
            path,
            len(content),
            content,
        )
        resolved = _safe_path(path)
        container = await pool.acquire()
        app_logger.info(
            "[sandbox_write_file] Acquired container | container_id=%s | resolved_path=%r",
            container.short_id,
            resolved,
        )
        try:
            nbytes = await pool.file_write(container, resolved, content.encode("utf-8"))
            app_logger.info(
                "[sandbox_write_file] Write completed | container_id=%s | resolved_path=%r | bytes_written=%d",
                container.short_id,
                resolved,
                nbytes,
            )
        finally:
            await pool.release(container)
            app_logger.info(
                "[sandbox_write_file] Released container | container_id=%s",
                container.short_id,
            )
        response = f"Wrote {nbytes} bytes to {resolved}"
        app_logger.info("[sandbox_write_file] Returning response | response=%r", response)
        return response

    @mcp.tool()
    async def sandbox_list_files(path: str = "/workspace") -> str:
        """List directory contents inside the sandbox.

        Args:
            path: Directory path (default: /workspace). Must be within /workspace.

        Returns:
            Directory listing (ls -la output).
        """
        app_logger.info("[sandbox_list_files] Request received | path=%r", path)
        resolved = _safe_path(path)
        container = await pool.acquire()
        app_logger.info(
            "[sandbox_list_files] Acquired container | container_id=%s | resolved_path=%r",
            container.short_id,
            resolved,
        )
        try:
            listing = await pool.file_list(container, resolved)
            app_logger.info(
                "[sandbox_list_files] Listing completed | container_id=%s | resolved_path=%r | listing_length=%d | listing=%r",
                container.short_id,
                resolved,
                len(listing),
                listing,
            )
        finally:
            await pool.release(container)
            app_logger.info(
                "[sandbox_list_files] Released container | container_id=%s",
                container.short_id,
            )
        app_logger.info(
            "[sandbox_list_files] Returning response | resolved_path=%r | response_length=%d",
            resolved,
            len(listing),
        )
        return listing
