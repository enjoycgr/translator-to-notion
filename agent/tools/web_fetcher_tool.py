"""
Web fetcher tool using Claude Agent SDK @tool decorator.

Wraps the existing WebFetcher logic for use with Claude Agent SDK.
"""

from typing import Any

from claude_agent_sdk import tool

from .web_fetcher import WebFetcher


# Singleton instance for reuse
_web_fetcher: WebFetcher | None = None


def _get_web_fetcher() -> WebFetcher:
    """Get or create WebFetcher singleton."""
    global _web_fetcher
    if _web_fetcher is None:
        _web_fetcher = WebFetcher()
    return _web_fetcher


@tool(
    name="web_fetch",
    description="Fetch article content from a URL and convert to Markdown format. "
    "Extracts main content, removes navigation/ads, and returns clean text.",
    input_schema={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch content from (must be http or https)"
            }
        },
        "required": ["url"]
    }
)
async def web_fetch_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    Fetch and extract article content from a URL.

    Args:
        args: Dictionary containing:
            - url: The URL to fetch

    Returns:
        Tool result with content or error information.
    """
    url = args.get("url", "")

    if not url:
        return {
            "content": [{
                "type": "text",
                "text": "Error: URL is required"
            }],
            "is_error": True
        }

    fetcher = _get_web_fetcher()
    result = fetcher.fetch(url)

    if not result.success:
        return {
            "content": [{
                "type": "text",
                "text": f"Error fetching URL: {result.error}"
            }],
            "is_error": True
        }

    # Build response with title and content
    response_text = f"# {result.title}\n\n{result.content}"

    return {
        "content": [{
            "type": "text",
            "text": response_text
        }]
    }


# Export for use in tools_server.py
__all__ = ["web_fetch_tool"]
