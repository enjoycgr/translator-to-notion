"""Agent tools module."""

# Original tools (used directly)
from .web_fetcher import WebFetcher
from .notion_publisher import NotionPublisher

# SDK-compatible tools (using @tool decorator)
from .web_fetcher_tool import web_fetch_tool
from .notion_tool import notion_publish_tool

# MCP Server
from .tools_server import (
    create_translation_tools_server,
    get_translation_tools_server,
    get_all_tool_names,
    TOOL_WEB_FETCH,
    TOOL_NOTION_PUBLISH,
)

__all__ = [
    # Original tools
    "WebFetcher",
    "NotionPublisher",
    # SDK tools
    "web_fetch_tool",
    "notion_publish_tool",
    # MCP Server
    "create_translation_tools_server",
    "get_translation_tools_server",
    "get_all_tool_names",
    "TOOL_WEB_FETCH",
    "TOOL_NOTION_PUBLISH",
]
