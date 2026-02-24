"""Execute code in a sandboxed Docker container."""

from __future__ import annotations

from core.sandbox import pool


def register(mcp) -> None:  # noqa: ANN001
    """Register the execute_code tool on the given FastMCP instance."""

    @mcp.tool()
    async def execute_code(
        code: str,
        language: str = "python",
    ) -> str:
        """Execute code in an isolated Docker sandbox with no network access.

        The sandbox has a /workspace directory for file operations.
        Supported languages: python, bash, sh, node, javascript.

        Args:
            code: The source code to execute.
            language: Programming language to use (default: python).

        Returns:
            Formatted string with stdout, stderr, and exit code.
        """
        container = await pool.acquire()
        try:
            result = await pool.exec_code(container, code, language)
        finally:
            await pool.release(container)

        parts: list[str] = []
        if result.stdout:
            parts.append(f"[stdout]\n{result.stdout}")
        if result.stderr:
            parts.append(f"[stderr]\n{result.stderr}")
        parts.append(f"[exit_code] {result.exit_code}")
        if result.truncated:
            parts.append("[note] Output was truncated due to size limits.")
        return "\n".join(parts)
