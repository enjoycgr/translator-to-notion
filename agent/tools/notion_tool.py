"""
Notion publisher tool using Claude Agent SDK @tool decorator.

Wraps the existing NotionPublisher logic for use with Claude Agent SDK.
"""

import os
from typing import Any

from claude_agent_sdk import tool

from .notion_publisher import NotionPublisher


# Singleton instance for reuse
_notion_publisher: NotionPublisher | None = None


def _get_notion_publisher() -> NotionPublisher | None:
    """Get or create NotionPublisher singleton if configured."""
    global _notion_publisher

    if _notion_publisher is None:
        api_key = os.environ.get("NOTION_API_KEY")
        parent_page_id = os.environ.get("NOTION_PARENT_PAGE_ID")

        if api_key and parent_page_id:
            _notion_publisher = NotionPublisher(
                api_key=api_key,
                parent_page_id=parent_page_id,
            )

    return _notion_publisher


@tool(
    name="notion_publish",
    description="Publish translated content to Notion as a new page. "
    "Creates a bilingual page with original quotes and translations interleaved.",
    input_schema={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "The page title for the Notion page"
            },
            "content": {
                "type": "string",
                "description": "The translated content in Markdown format with interleaved original/translation"
            },
            "source_url": {
                "type": "string",
                "description": "Optional source URL of the original article"
            },
            "domain": {
                "type": "string",
                "description": "Translation domain (tech, business, academic)",
                "enum": ["tech", "business", "academic"]
            }
        },
        "required": ["title", "content"]
    }
)
async def notion_publish_tool(args: dict[str, Any]) -> dict[str, Any]:
    """
    Publish translation to Notion.

    Args:
        args: Dictionary containing:
            - title: Page title
            - content: Translated content in Markdown
            - source_url: Optional source URL
            - domain: Optional translation domain

    Returns:
        Tool result with page URL or error information.
    """
    title = args.get("title", "")
    content = args.get("content", "")
    source_url = args.get("source_url")
    domain = args.get("domain")

    if not title:
        return {
            "content": [{
                "type": "text",
                "text": "Error: Title is required"
            }],
            "is_error": True
        }

    if not content:
        return {
            "content": [{
                "type": "text",
                "text": "Error: Content is required"
            }],
            "is_error": True
        }

    publisher = _get_notion_publisher()

    if publisher is None:
        return {
            "content": [{
                "type": "text",
                "text": "Error: Notion is not configured. "
                "Set NOTION_API_KEY and NOTION_PARENT_PAGE_ID environment variables."
            }],
            "is_error": True
        }

    # Publish to Notion
    result = publisher.publish_markdown(
        title=title,
        content=content,
        source_url=source_url,
        domain=domain,
    )

    if not result.success:
        return {
            "content": [{
                "type": "text",
                "text": f"Error publishing to Notion: {result.error}"
            }],
            "is_error": True
        }

    return {
        "content": [{
            "type": "text",
            "text": f"Successfully published to Notion!\nPage URL: {result.page_url}"
        }]
    }


# Export for use in tools_server.py
__all__ = ["notion_publish_tool"]
