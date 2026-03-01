"""FastMCP request middleware and request-scoped context helpers."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_REQUEST_CONTEXT: ContextVar[dict[str, Any] | None] = ContextVar("mcp_request_context", default=None)


def get_request_context() -> dict[str, Any]:
    """Return request-scoped context populated by middleware for the current request."""
    return _REQUEST_CONTEXT.get() or {}


class FastMCPContextMiddleware(BaseHTTPMiddleware):
    """Populate request-scoped context values for FastMCP tool execution.

    The middleware extracts commonly used values from request headers and stores
    them in a context variable so async tool functions can access them reliably.
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        authorization = request.headers.get("authorization", "")
        bearer_token = ""
        if authorization.lower().startswith("bearer "):
            bearer_token = authorization[7:].strip()

        request_context = {
            "graph_token": request.headers.get("x-microsoft-graph-token")
            or request.headers.get("x-graph-token")
            or bearer_token
            or None,
            "github_username": request.headers.get("x-github-username") or None,
            "request_id": request.headers.get("x-request-id") or None,
        }

        request.state.mcp_context = request_context
        request.state.graph_token = request_context["graph_token"]
        request.state.github_username = request_context["github_username"]
        request.state.request_id = request_context["request_id"]

        token = _REQUEST_CONTEXT.set(request_context)
        try:
            response: Response = await call_next(request)
        finally:
            _REQUEST_CONTEXT.reset(token)

        return response
