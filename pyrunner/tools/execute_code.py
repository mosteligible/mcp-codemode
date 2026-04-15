"""Execute code in a sandboxed Docker container."""

from __future__ import annotations

import httpx
from config import settings
from fastmcp import FastMCP

from core.types.schemas import CodeRunnerRequest, CodeRunnerResponse
from log import app_logger


async def execution_handler(code: str, language: str) -> CodeRunnerResponse:
    """Handler function for the execute_code tool."""
    url = f"{settings.code_execution_host}/run"
    postbody = CodeRunnerRequest(code=code, language=language)

    with httpx.Client(timeout=30.0) as client:
        try:
            response = client.post(url, json=postbody.model_dump(by_alias=True))
            response.raise_for_status()
            data = response.json()
            return CodeRunnerResponse.model_validate(data)
        except httpx.RequestError as exc:
            app_logger.error(f"HTTP request failed: {exc}")
            return CodeRunnerResponse(output="", error=-1)
        except httpx.HTTPStatusError as exc:
            app_logger.error(
                f"HTTP error response: {exc.response.status_code} - {exc.response.text}"
            )
            return CodeRunnerResponse(output="", error=-1)
        except Exception as exc:
            app_logger.error(f"Unexpected error: {exc}")
            return CodeRunnerResponse(output="", error=-1)


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

        result = await execution_handler(code, language)

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
