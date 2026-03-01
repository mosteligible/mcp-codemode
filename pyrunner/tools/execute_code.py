"""Execute code in a sandboxed Docker container."""

from __future__ import annotations

from fastmcp import FastMCP

from core.sandbox import pool
from log import app_logger


def register(mcp: FastMCP) -> None:
    """Register the execute_code tool on the given FastMCP instance."""

    @mcp.tool()
    async def execute_code(
        code: str,
        language: str = "python",
    ) -> str:
        """Execute code in an isolated Docker sandbox with network access.

        The sandbox has a /workspace directory for file operations.
        Supported languages: python, bash, sh, node, javascript.

        Args:
            code: The source code to execute.
            language: Programming language to use (default: python).

        Returns:
            Formatted string with stdout, stderr, and exit code.
        """
        app_logger.info(
            "[execute_code] Received request | language=%s | code_length=%d | code=%r",
            language,
            len(code),
            code,
        )

        container = await pool.acquire()
        app_logger.info(
            "[execute_code] Acquired container | container_id=%s",
            container.short_id,
        )
        try:
            app_logger.info(
                "[execute_code] Starting sandbox execution | container_id=%s",
                container.short_id,
            )
            result = await pool.exec_code(container, code, language)
            app_logger.info(
                "[execute_code] Execution finished | container_id=%s | exit_code=%s | truncated=%s",
                container.short_id,
                result.exit_code,
                result.truncated,
            )
        finally:
            await pool.release(container)
            app_logger.info(
                "[execute_code] Released container | container_id=%s",
                container.short_id,
            )

        parts: list[str] = []
        if result.stdout:
            parts.append(f"[stdout]\n{result.stdout}")
        if result.stderr:
            parts.append(f"[stderr]\n{result.stderr}")
        parts.append(f"[exit_code] {result.exit_code}")
        if result.truncated:
            parts.append("[note] Output was truncated due to size limits.")
        response = "\n".join(parts)
        app_logger.info(
            "[execute_code] Returning response | stdout=%r | stderr=%r | response=%r",
            result.stdout,
            result.stderr,
            response,
        )
        return response
