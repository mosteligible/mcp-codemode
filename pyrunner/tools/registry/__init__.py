"""Tool registry package for third-party API integrations.

This package exports async tool functions for:
- Microsoft Graph API (token-based)
- GitHub public API (no token required)
"""

from .github_tools import (
    list_issues_opened_by_user,
    list_pull_requests_opened_by_user,
    list_user_repositories,
)
from .graph_tools import (
    get_user_calendar_availability,
    get_user_information,
    list_all_items_in_sharepoint_drive_folders,
    list_chat_messages,
    list_joined_teams,
    list_mailbox_messages,
    list_message_attachments,
    list_sharepoint_drive_items,
    list_sharepoint_site_items,
    list_sharepoint_sites,
    list_team_channels,
    list_user_chats,
    list_user_drives,
    list_user_mail_folders,
    list_user_meetings,
    search_sharepoint,
)

__all__ = [
    "get_user_information",
    "get_user_calendar_availability",
    "list_user_mail_folders",
    "list_mailbox_messages",
    "list_message_attachments",
    "list_user_meetings",
    "search_sharepoint",
    "list_sharepoint_sites",
    "list_sharepoint_site_items",
    "list_user_drives",
    "list_sharepoint_drive_items",
    "list_all_items_in_sharepoint_drive_folders",
    "list_user_chats",
    "list_chat_messages",
    "list_joined_teams",
    "list_team_channels",
    "list_user_repositories",
    "list_pull_requests_opened_by_user",
    "list_issues_opened_by_user",
]
