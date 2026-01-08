"""
MCP Server for translation tools.

Aggregates all translation-related tools into a single MCP server
that can be used with Claude Agent SDK.
"""

from claude_agent_sdk import create_sdk_mcp_server

from .web_fetcher_tool import web_fetch_tool
from .notion_tool import notion_publish_tool


# Tool name constants for reference
TOOL_WEB_FETCH = "mcp__translation-tools__web_fetch"
TOOL_NOTION_PUBLISH = "mcp__translation-tools__notion_publish"


def create_translation_tools_server():
    """
    Create an MCP server with all translation tools.

    Returns:
        SDK MCP server instance ready for use with ClaudeAgentOptions.
    """
    return create_sdk_mcp_server(
        name="translation-tools",
        version="1.0.0",
        tools=[
            web_fetch_tool,
            notion_publish_tool,
        ],
    )


def get_all_tool_names() -> list[str]:
    """
    Get list of all tool names in the translation tools server.

    Returns:
        List of fully qualified tool names (mcp__server__tool format).
    """
    return [
        TOOL_WEB_FETCH,
        TOOL_NOTION_PUBLISH,
    ]


# Pre-created server instance for convenience
_translation_server = None


def get_translation_tools_server():
    """
    Get or create the singleton translation tools server.

    Returns:
        SDK MCP server instance.
    """
    global _translation_server
    if _translation_server is None:
        _translation_server = create_translation_tools_server()
    return _translation_server


__all__ = [
    "create_translation_tools_server",
    "get_translation_tools_server",
    "get_all_tool_names",
    "TOOL_WEB_FETCH",
    "TOOL_NOTION_PUBLISH",
]
