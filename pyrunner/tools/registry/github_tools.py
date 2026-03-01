"""Async GitHub API tool functions for public, no-token data retrieval."""

from __future__ import annotations

from typing import Any

from fastmcp import Context as CurrentContext
import httpx

from .common import DEFAULT_TIMEOUT, request_json

GITHUB_BASE_URL = "https://api.github.com"


async def list_user_repositories(
    ctx: CurrentContext,
    username: str,
    type_filter: str = "owner",
    sort: str = "updated",
    per_page: int = 100,
    max_pages: int = 5,
) -> list[dict[str, Any]]:
    """List public repositories owned by or associated with a GitHub user.

    Args:
        ctx: Current FastMCP tool context.
        username: GitHub username.
        type_filter: Repository type (`all`, `owner`, `member`).
        sort: Sort field (`created`, `updated`, `pushed`, `full_name`).
        per_page: Number of repositories per page.
        max_pages: Maximum pages to fetch.

    Returns:
        A list of repository objects.
    """
    headers = {"Accept": "application/vnd.github+json"}
    repositories: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        for page in range(1, max_pages + 1):
            payload = await request_json(
                client,
                "GET",
                f"{GITHUB_BASE_URL}/users/{username}/repos",
                headers=headers,
                params={
                    "type": type_filter,
                    "sort": sort,
                    "per_page": per_page,
                    "page": page,
                },
            )

            if isinstance(payload, list):
                repositories.extend(item for item in payload if isinstance(item, dict))
                if len(payload) < per_page:
                    break
            else:
                break

    return repositories


async def list_pull_requests_opened_by_user(
    ctx: CurrentContext,
    username: str,
    per_page: int = 100,
    max_pages: int = 5,
) -> list[dict[str, Any]]:
    """List pull requests authored by a GitHub user using public search API.

    Args:
        ctx: Current FastMCP tool context.
        username: GitHub username.
        per_page: Number of results per page.
        max_pages: Maximum pages to fetch.

    Returns:
        A list of pull request search-result items.
    """
    headers = {"Accept": "application/vnd.github+json"}
    pull_requests: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        for page in range(1, max_pages + 1):
            payload = await request_json(
                client,
                "GET",
                f"{GITHUB_BASE_URL}/search/issues",
                headers=headers,
                params={
                    "q": f"type:pr author:{username}",
                    "per_page": per_page,
                    "page": page,
                },
            )

            if not isinstance(payload, dict):
                break

            items = payload.get("items", [])
            if not isinstance(items, list) or not items:
                break

            pull_requests.extend(item for item in items if isinstance(item, dict))
            if len(items) < per_page:
                break

    return pull_requests


async def list_pull_requests_closed_by_user(
    ctx: CurrentContext,
    username: str,
    per_page: int = 100,
    max_pages: int = 5,
) -> dict[str, Any]:
    """List closed pull requests authored by a GitHub user and total PRs created.

    Args:
        ctx: Current FastMCP tool context.
        username: GitHub username.
        per_page: Number of closed PR results per page.
        max_pages: Maximum pages of closed PR results to fetch.

    Returns:
        A payload with total PR count created by the user and fetched closed PR items.
    """
    headers = {"Accept": "application/vnd.github+json"}
    closed_pull_requests: list[dict[str, Any]] = []
    total_pull_requests_created = 0

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        total_payload = await request_json(
            client,
            "GET",
            f"{GITHUB_BASE_URL}/search/issues",
            headers=headers,
            params={
                "q": f"type:pr author:{username}",
                "per_page": 1,
                "page": 1,
            },
        )

        if isinstance(total_payload, dict):
            total_count = total_payload.get("total_count")
            if isinstance(total_count, int) and total_count >= 0:
                total_pull_requests_created = total_count

        for page in range(1, max_pages + 1):
            payload = await request_json(
                client,
                "GET",
                f"{GITHUB_BASE_URL}/search/issues",
                headers=headers,
                params={
                    "q": f"type:pr author:{username} is:closed",
                    "per_page": per_page,
                    "page": page,
                },
            )

            if not isinstance(payload, dict):
                break

            items = payload.get("items", [])
            if not isinstance(items, list) or not items:
                break

            closed_pull_requests.extend(item for item in items if isinstance(item, dict))
            if len(items) < per_page:
                break

    return {
        "username": username,
        "total_pull_requests_created": total_pull_requests_created,
        "total_closed_pull_requests_fetched": len(closed_pull_requests),
        "closed_pull_requests": closed_pull_requests,
    }


async def list_issues_opened_by_user(
    ctx: CurrentContext,
    username: str,
    per_page: int = 100,
    max_pages: int = 5,
) -> list[dict[str, Any]]:
    """List issues authored by a GitHub user using public search API.

    Args:
        ctx: Current FastMCP tool context.
        username: GitHub username.
        per_page: Number of results per page.
        max_pages: Maximum pages to fetch.

    Returns:
        A list of issue search-result items.
    """
    headers = {"Accept": "application/vnd.github+json"}
    issues: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        for page in range(1, max_pages + 1):
            payload = await request_json(
                client,
                "GET",
                f"{GITHUB_BASE_URL}/search/issues",
                headers=headers,
                params={
                    "q": f"type:issue author:{username}",
                    "per_page": per_page,
                    "page": page,
                },
            )

            if not isinstance(payload, dict):
                break

            items = payload.get("items", [])
            if not isinstance(items, list) or not items:
                break

            issues.extend(item for item in items if isinstance(item, dict))
            if len(items) < per_page:
                break

    return issues
