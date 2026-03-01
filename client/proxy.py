"""Proxy routers for forwarding sandbox requests to third-party APIs.

The Docker sandbox calls these endpoints instead of hitting external APIs
directly.  Auth tokens are injected from client configuration so the
sandbox never needs to handle credentials.

Routes
------
/graph/{path}  → https://graph.microsoft.com/v1.0/{path}
/github/{path} → https://api.github.com/{path}
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Request, Response
from redis.asyncio import Redis

from config import settings

logger = logging.getLogger(__name__)

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GITHUB_BASE_URL = "https://api.github.com"
DEFAULT_TIMEOUT = 30.0

redis_conn = Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    username=settings.redis_username,
    password=settings.redis_password,
)

# ── Routers ──────────────────────────────────────────────────────────

graph_router = APIRouter(tags=["proxy - Microsoft Graph"])
github_router = APIRouter(tags=["proxy - GitHub"])


# ── Shared helper ────────────────────────────────────────────────────

async def _proxy_request(
    request: Request,
    base_url: str,
    path: str,
    headers: dict[str, str] | None,
) -> Response:
    """Forward an incoming request to an upstream API and relay the response.

    Parameters
    ----------
    request:
        The incoming FastAPI ``Request`` object.
    base_url:
        Upstream API base URL (no trailing slash).
    path:
        The remaining path segment to append to *base_url*.
    headers:
        Optional headers to include in the request.
    """
    target_url = f"{base_url}/{path}"
    query_string = str(request.query_params)
    if query_string:
        target_url = f"{target_url}?{query_string}"


    # Read body (relevant for POST; empty for GET)
    body = await request.body()

    logger.info("Proxy %s %s", request.method, target_url)

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        upstream = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body if body else None,
        )

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
    )


# ── Microsoft Graph routes ───────────────────────────────────────────

@graph_router.get("/{path:path}")
@graph_router.post("/{path:path}")
async def graph_proxy(request: Request, path: str) -> Response:
    """Proxy GET/POST requests to the Microsoft Graph API (v1.0).

    Requires ``CLIENT_MICROSOFT_GRAPH_TOKEN`` to be set; returns 401
    otherwise.
    """
    proxy_id = request.headers.get("X-Proxy-ID", None)
    if not proxy_id:
        return Response(
            content='unknown request, cannot continue!',
            status_code=401,
            media_type="text/plain",
        )

    token = await redis_conn.get(proxy_id)
    if not token:
        return Response(
            content='invalid proxy ID, cannot continue!',
            status_code=401,
            media_type="text/plain",
        )

    headers = {
        "Authorization": f"Bearer {token.decode("utf-8")}",
    }

    return await _proxy_request(
        request,
        base_url=GRAPH_BASE_URL,
        path=path,
        auth_header=headers,
    )


# ── GitHub routes ────────────────────────────────────────────────────

@github_router.get("/{path:path}")
@github_router.post("/{path:path}")
async def github_proxy(request: Request, path: str) -> Response:
    """Proxy GET/POST requests to the GitHub API.

    If ``CLIENT_GITHUB_TOKEN`` is set the token is forwarded; otherwise
    requests are made without authentication (public API access).
    """
    token = settings.github_token
    headers = {"accept": "application/vnd.github.v3+json"}
    return await _proxy_request(
        request,
        base_url=GITHUB_BASE_URL,
        path=path,
        headers=headers,
    )
