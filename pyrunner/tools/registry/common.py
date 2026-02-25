"""Shared async HTTP helper utilities for registry tools."""

from __future__ import annotations

import os
from typing import Any, TypeAlias

import httpx

from middleware import get_request_context

CurrentContext: TypeAlias = Any

try:  # FastMCP standalone package
    from fastmcp.dependencies import CurrentContext as _CurrentContext  # type: ignore[import-not-found]

    CurrentContext = _CurrentContext
except ImportError:  # pragma: no cover - compatibility fallback
    pass


DEFAULT_TIMEOUT = 30.0


def get_context_value(ctx: CurrentContext, key: str) -> str | None:
    """Read a string value from CurrentContext or middleware request context.

    Args:
        ctx: Current tool execution context.
        key: Context key to read.

    Returns:
        The context value when present, otherwise ``None``.
    """
    if ctx is not None:
        # Dict-like context
        if isinstance(ctx, dict):
            value = ctx.get(key)
            if isinstance(value, str) and value:
                return value

        # Generic object attribute
        value = getattr(ctx, key, None)
        if isinstance(value, str) and value:
            return value

        # CurrentContext-like accessors
        for method_name in ("get", "get_state", "state"):
            accessor = getattr(ctx, method_name, None)
            if callable(accessor):
                try:
                    candidate = accessor(key) if method_name != "state" else accessor().get(key)
                except Exception:  # pragma: no cover - defensive fallback
                    candidate = None
                if isinstance(candidate, str) and candidate:
                    return candidate

        # Nested request context patterns
        request_context = getattr(ctx, "request_context", None)
        if request_context is not None:
            request = getattr(request_context, "request", None)
            state = getattr(request, "state", None)
            if state is not None:
                candidate = getattr(state, key, None)
                if isinstance(candidate, str) and candidate:
                    return candidate
                container = getattr(state, "mcp_context", None)
                if isinstance(container, dict):
                    nested = container.get(key)
                    if isinstance(nested, str) and nested:
                        return nested

    middleware_value = get_request_context().get(key)
    return middleware_value if isinstance(middleware_value, str) and middleware_value else None


def resolve_graph_token(ctx: CurrentContext, token: str | None = None) -> str:
    """Return a Microsoft Graph bearer token from argument or environment.

    Args:
        ctx: Current tool execution context.
        token: Optional explicitly supplied bearer token.

    Returns:
        A non-empty bearer token string.

    Raises:
        ValueError: If no token is provided and no supported environment variable exists.
    """
    resolved = (
        token
        or get_context_value(ctx, "graph_token")
        or os.getenv("MICROSOFT_GRAPH_TOKEN")
        or os.getenv("GRAPH_TOKEN")
    )
    if not resolved:
        raise ValueError(
            "Microsoft Graph token is required. Provide token argument or set MICROSOFT_GRAPH_TOKEN/GRAPH_TOKEN."
        )
    return resolved


async def request_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any]:
    """Send an HTTP request and return decoded JSON response.

    Args:
        client: Configured async HTTP client.
        method: HTTP method (GET, POST, ...).
        url: Fully-qualified endpoint URL.
        headers: Optional request headers.
        params: Optional query parameters.
        json_body: Optional JSON payload.

    Returns:
        Parsed JSON response body.

    Raises:
        httpx.HTTPStatusError: If response status is non-successful.
    """
    response = await client.request(
        method,
        url,
        headers=headers,
        params=params,
        json=json_body,
    )
    response.raise_for_status()
    return response.json()


async def collect_paginated_values(
    client: httpx.AsyncClient,
    first_url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    max_pages: int = 10,
) -> list[dict[str, Any]]:
    """Collect Graph-style paginated resources from `value` arrays.

    Args:
        client: Configured async HTTP client.
        first_url: Initial API endpoint.
        headers: Optional request headers.
        params: Optional query parameters for the first page only.
        max_pages: Maximum number of pages to traverse.

    Returns:
        Flattened list of resource objects across all traversed pages.
    """
    results: list[dict[str, Any]] = []
    next_url = first_url
    page = 0
    current_params = params

    while next_url and page < max_pages:
        payload = await request_json(
            client,
            "GET",
            next_url,
            headers=headers,
            params=current_params,
        )
        current_params = None

        if isinstance(payload, dict):
            value = payload.get("value", [])
            if isinstance(value, list):
                results.extend(item for item in value if isinstance(item, dict))
            next_url = payload.get("@odata.nextLink")
        else:
            break

        page += 1

    return results
