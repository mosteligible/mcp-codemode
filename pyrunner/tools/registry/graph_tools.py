"""Async Microsoft Graph API tool functions for LLM tool invocation."""

from __future__ import annotations

from typing import Any

from fastmcp import Context as CurrentContext
import httpx

from .common import DEFAULT_TIMEOUT, collect_paginated_values, request_json, resolve_graph_token

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


async def get_user_information(ctx: CurrentContext, token: str | None = None) -> dict[str, Any]:
    """Get the signed-in user's profile information from Microsoft Graph.

    Args:
        ctx: Current FastMCP tool context.
        token: Optional Microsoft Graph bearer token.

    Returns:
        The Graph `/me` profile payload.
    """
    graph_token = resolve_graph_token(ctx, token)
    headers = {"Authorization": f"Bearer {graph_token}"}

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        payload = await request_json(client, "GET", f"{GRAPH_BASE_URL}/me", headers=headers)

    return payload if isinstance(payload, dict) else {"data": payload}


async def get_user_calendar_availability(
    ctx: CurrentContext,
    start_datetime: str,
    end_datetime: str,
    interval_minutes: int = 30,
    token: str | None = None,
) -> dict[str, Any]:
    """Get the signed-in user's availability from calendar via `getSchedule`.

    Args:
        ctx: Current FastMCP tool context.
        start_datetime: ISO-8601 start datetime in UTC (example: `2026-02-24T09:00:00Z`).
        end_datetime: ISO-8601 end datetime in UTC.
        interval_minutes: Availability slot interval in minutes.
        token: Optional Microsoft Graph bearer token.

    Returns:
        Availability schedule payload for the signed-in user.
    """
    graph_token = resolve_graph_token(ctx, token)
    headers = {"Authorization": f"Bearer {graph_token}", "Content-Type": "application/json"}
    body = {
        "schedules": ["me"],
        "startTime": {"dateTime": start_datetime, "timeZone": "UTC"},
        "endTime": {"dateTime": end_datetime, "timeZone": "UTC"},
        "availabilityViewInterval": interval_minutes,
    }

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        payload = await request_json(
            client,
            "POST",
            f"{GRAPH_BASE_URL}/me/calendar/getSchedule",
            headers=headers,
            json_body=body,
        )

    return payload if isinstance(payload, dict) else {"data": payload}


async def list_user_mail_folders(
    ctx: CurrentContext,
    token: str | None = None,
    max_pages: int = 5,
) -> list[dict[str, Any]]:
    """List all mail folders for the signed-in user's mailbox.

    Args:
        ctx: Current FastMCP tool context.
        token: Optional Microsoft Graph bearer token.
        max_pages: Maximum number of paginated pages to fetch.

    Returns:
        A list of mail folder objects.
    """
    graph_token = resolve_graph_token(ctx, token)
    headers = {"Authorization": f"Bearer {graph_token}"}

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        return await collect_paginated_values(
            client,
            f"{GRAPH_BASE_URL}/me/mailFolders",
            headers=headers,
            max_pages=max_pages,
        )


async def list_mailbox_messages(
    ctx: CurrentContext,
    folder_id: str | None = None,
    top: int = 25,
    token: str | None = None,
    max_pages: int = 2,
) -> list[dict[str, Any]]:
    """List messages from the user's mailbox or a specific mail folder.

    Args:
        ctx: Current FastMCP tool context.
        folder_id: Optional mail folder ID. If omitted, reads from the default mailbox root.
        top: Number of messages per page.
        token: Optional Microsoft Graph bearer token.
        max_pages: Maximum pages to fetch.

    Returns:
        A list of message objects.
    """
    graph_token = resolve_graph_token(ctx, token)
    headers = {"Authorization": f"Bearer {graph_token}"}
    endpoint = (
        f"{GRAPH_BASE_URL}/me/mailFolders/{folder_id}/messages"
        if folder_id
        else f"{GRAPH_BASE_URL}/me/messages"
    )

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        return await collect_paginated_values(
            client,
            endpoint,
            headers=headers,
            params={"$top": top},
            max_pages=max_pages,
        )


async def list_message_attachments(
    ctx: CurrentContext,
    message_id: str,
    token: str | None = None,
    max_pages: int = 2,
) -> list[dict[str, Any]]:
    """List attachments for a specific email message.

    Args:
        ctx: Current FastMCP tool context.
        message_id: Microsoft Graph message ID.
        token: Optional Microsoft Graph bearer token.
        max_pages: Maximum pages to fetch.

    Returns:
        A list of attachment objects.
    """
    graph_token = resolve_graph_token(ctx, token)
    headers = {"Authorization": f"Bearer {graph_token}"}

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        return await collect_paginated_values(
            client,
            f"{GRAPH_BASE_URL}/me/messages/{message_id}/attachments",
            headers=headers,
            max_pages=max_pages,
        )


async def list_user_meetings(
    ctx: CurrentContext,
    start_datetime: str,
    end_datetime: str,
    top: int = 100,
    token: str | None = None,
) -> list[dict[str, Any]]:
    """List meetings from the signed-in user's calendar view for a time range.

    Args:
        ctx: Current FastMCP tool context.
        start_datetime: ISO-8601 range start in UTC.
        end_datetime: ISO-8601 range end in UTC.
        top: Max number of events to request.
        token: Optional Microsoft Graph bearer token.

    Returns:
        A list of meeting/event objects.
    """
    graph_token = resolve_graph_token(ctx, token)
    headers = {"Authorization": f"Bearer {graph_token}"}

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        payload = await request_json(
            client,
            "GET",
            f"{GRAPH_BASE_URL}/me/calendarView",
            headers=headers,
            params={"startDateTime": start_datetime, "endDateTime": end_datetime, "$top": top},
        )

    if isinstance(payload, dict):
        value = payload.get("value", [])
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


async def search_sharepoint(
    ctx: CurrentContext,
    query: str,
    token: str | None = None,
) -> dict[str, Any]:
    """Search SharePoint content with Microsoft Graph search endpoint.

    Args:
        ctx: Current FastMCP tool context.
        query: Free-text search string.
        token: Optional Microsoft Graph bearer token.

    Returns:
        Raw Graph search response payload.
    """
    graph_token = resolve_graph_token(ctx, token)
    headers = {"Authorization": f"Bearer {graph_token}", "Content-Type": "application/json"}
    body = {
        "requests": [
            {
                "entityTypes": ["driveItem", "listItem", "site"],
                "query": {"queryString": query},
                "from": 0,
                "size": 25,
            }
        ]
    }

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        payload = await request_json(
            client,
            "POST",
            f"{GRAPH_BASE_URL}/search/query",
            headers=headers,
            json_body=body,
        )

    return payload if isinstance(payload, dict) else {"data": payload}


async def list_sharepoint_sites(
    ctx: CurrentContext,
    token: str | None = None,
    max_pages: int = 5,
) -> list[dict[str, Any]]:
    """List SharePoint sites accessible to the signed-in user.

    Args:
        ctx: Current FastMCP tool context.
        token: Optional Microsoft Graph bearer token.
        max_pages: Maximum pages to fetch.

    Returns:
        A list of SharePoint site objects.
    """
    graph_token = resolve_graph_token(ctx, token)
    headers = {"Authorization": f"Bearer {graph_token}"}

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        return await collect_paginated_values(
            client,
            f"{GRAPH_BASE_URL}/sites",
            headers=headers,
            params={"search": "*"},
            max_pages=max_pages,
        )


async def list_sharepoint_site_items(
    ctx: CurrentContext,
    site_id: str,
    list_id: str,
    token: str | None = None,
    max_pages: int = 5,
) -> list[dict[str, Any]]:
    """List items from a SharePoint list in a site the user can access.

    Args:
        ctx: Current FastMCP tool context.
        site_id: SharePoint site ID.
        list_id: SharePoint list ID.
        token: Optional Microsoft Graph bearer token.
        max_pages: Maximum pages to fetch.

    Returns:
        A list of list-item objects.
    """
    graph_token = resolve_graph_token(ctx, token)
    headers = {"Authorization": f"Bearer {graph_token}"}

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        return await collect_paginated_values(
            client,
            f"{GRAPH_BASE_URL}/sites/{site_id}/lists/{list_id}/items",
            headers=headers,
            params={"expand": "fields"},
            max_pages=max_pages,
        )


async def list_user_drives(
    ctx: CurrentContext,
    token: str | None = None,
    max_pages: int = 5,
) -> list[dict[str, Any]]:
    """List all drives the signed-in user has access to.

    Args:
        ctx: Current FastMCP tool context.
        token: Optional Microsoft Graph bearer token.
        max_pages: Maximum pages to fetch.

    Returns:
        A list of drive objects.
    """
    graph_token = resolve_graph_token(ctx, token)
    headers = {"Authorization": f"Bearer {graph_token}"}

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        return await collect_paginated_values(
            client,
            f"{GRAPH_BASE_URL}/me/drives",
            headers=headers,
            max_pages=max_pages,
        )


async def list_sharepoint_drive_items(
    ctx: CurrentContext,
    site_id: str,
    drive_id: str,
    token: str | None = None,
    max_pages: int = 5,
) -> list[dict[str, Any]]:
    """List root-level items from a drive in a SharePoint site.

    Args:
        ctx: Current FastMCP tool context.
        site_id: SharePoint site ID.
        drive_id: Drive ID in the site.
        token: Optional Microsoft Graph bearer token.
        max_pages: Maximum pages to fetch.

    Returns:
        A list of drive item objects.
    """
    graph_token = resolve_graph_token(ctx, token)
    headers = {"Authorization": f"Bearer {graph_token}"}

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        return await collect_paginated_values(
            client,
            f"{GRAPH_BASE_URL}/sites/{site_id}/drives/{drive_id}/root/children",
            headers=headers,
            max_pages=max_pages,
        )


async def list_all_items_in_sharepoint_drive_folders(
    ctx: CurrentContext,
    site_id: str,
    drive_id: str,
    token: str | None = None,
    max_pages_per_folder: int = 3,
) -> dict[str, list[dict[str, Any]]]:
    """List items from all folders in a SharePoint drive.

    This function first lists root items, then recursively traverses folders and
    returns a map of folder path to its child items.

    Args:
        ctx: Current FastMCP tool context.
        site_id: SharePoint site ID.
        drive_id: Drive ID in the site.
        token: Optional Microsoft Graph bearer token.
        max_pages_per_folder: Pagination cap for each folder listing call.

    Returns:
        Mapping of folder path to list of child drive item objects.
    """
    graph_token = resolve_graph_token(ctx, token)
    headers = {"Authorization": f"Bearer {graph_token}"}

    folder_items: dict[str, list[dict[str, Any]]] = {}

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        queue: list[tuple[str, str]] = [("root", f"{GRAPH_BASE_URL}/sites/{site_id}/drives/{drive_id}/root/children")]

        while queue:
            folder_path, url = queue.pop(0)
            items = await collect_paginated_values(
                client,
                url,
                headers=headers,
                max_pages=max_pages_per_folder,
            )
            folder_items[folder_path] = items

            for item in items:
                if "folder" in item and "id" in item:
                    item_name = str(item.get("name", item["id"]))
                    next_folder_path = f"{folder_path}/{item_name}" if folder_path != "root" else item_name
                    queue.append(
                        (
                            next_folder_path,
                            f"{GRAPH_BASE_URL}/sites/{site_id}/drives/{drive_id}/items/{item['id']}/children",
                        )
                    )

    return folder_items


async def list_user_chats(
    ctx: CurrentContext,
    token: str | None = None,
    max_pages: int = 5,
) -> list[dict[str, Any]]:
    """List Microsoft Teams chats available to the signed-in user.

    Useful for LLM context-building from recent chat metadata.

    Args:
        ctx: Current FastMCP tool context.
        token: Optional Microsoft Graph bearer token.
        max_pages: Maximum pages to fetch.

    Returns:
        A list of chat objects.
    """
    graph_token = resolve_graph_token(ctx, token)
    headers = {"Authorization": f"Bearer {graph_token}"}

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        return await collect_paginated_values(
            client,
            f"{GRAPH_BASE_URL}/me/chats",
            headers=headers,
            max_pages=max_pages,
        )


async def list_chat_messages(
    ctx: CurrentContext,
    chat_id: str,
    token: str | None = None,
    max_pages: int = 3,
) -> list[dict[str, Any]]:
    """List messages in a Teams chat conversation.

    Args:
        ctx: Current FastMCP tool context.
        chat_id: Chat identifier.
        token: Optional Microsoft Graph bearer token.
        max_pages: Maximum pages to fetch.

    Returns:
        A list of chat message objects.
    """
    graph_token = resolve_graph_token(ctx, token)
    headers = {"Authorization": f"Bearer {graph_token}"}

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        return await collect_paginated_values(
            client,
            f"{GRAPH_BASE_URL}/chats/{chat_id}/messages",
            headers=headers,
            max_pages=max_pages,
        )


async def list_joined_teams(
    ctx: CurrentContext,
    token: str | None = None,
    max_pages: int = 5,
) -> list[dict[str, Any]]:
    """List Microsoft Teams teams joined by the signed-in user.

    Args:
        ctx: Current FastMCP tool context.
        token: Optional Microsoft Graph bearer token.
        max_pages: Maximum pages to fetch.

    Returns:
        A list of team objects.
    """
    graph_token = resolve_graph_token(ctx, token)
    headers = {"Authorization": f"Bearer {graph_token}"}

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        return await collect_paginated_values(
            client,
            f"{GRAPH_BASE_URL}/me/joinedTeams",
            headers=headers,
            max_pages=max_pages,
        )


async def list_team_channels(
    ctx: CurrentContext,
    team_id: str,
    token: str | None = None,
    max_pages: int = 5,
) -> list[dict[str, Any]]:
    """List channels for a Microsoft Team.

    Args:
        ctx: Current FastMCP tool context.
        team_id: Team identifier.
        token: Optional Microsoft Graph bearer token.
        max_pages: Maximum pages to fetch.

    Returns:
        A list of channel objects.
    """
    graph_token = resolve_graph_token(ctx, token)
    headers = {"Authorization": f"Bearer {graph_token}"}

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        return await collect_paginated_values(
            client,
            f"{GRAPH_BASE_URL}/teams/{team_id}/channels",
            headers=headers,
            max_pages=max_pages,
        )
