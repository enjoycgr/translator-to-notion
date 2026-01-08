"""
Notion publisher for bilingual translation results.

Publishes translations to Notion with interleaved paragraph format
(original quote + translated paragraph alternating).
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from notion_client import Client
from notion_client.errors import APIResponseError


@dataclass
class PublishResult:
    """Result of publishing to Notion."""

    success: bool
    page_url: Optional[str] = None
    page_id: Optional[str] = None
    error: Optional[str] = None


class NotionPublisher:
    """
    Publishes bilingual translations to Notion.

    Features:
    - Interleaved paragraph format (original as quote, translation as paragraph)
    - Metadata support (source URL, domain, timestamp)
    - Automatic text splitting for long content (Notion 2000 char limit)
    """

    # Notion block text content limit
    MAX_BLOCK_TEXT_LENGTH = 2000

    def __init__(self, api_key: str, parent_page_id: str):
        """
        Initialize the Notion publisher.

        Args:
            api_key: Notion integration API key.
            parent_page_id: ID of the parent page where translations will be created.
        """
        self.client = Client(auth=api_key)
        self.parent_page_id = parent_page_id

    def publish(
        self,
        title: str,
        original_paragraphs: List[str],
        translated_paragraphs: List[str],
        source_url: Optional[str] = None,
        domain: Optional[str] = None,
        include_metadata: bool = True,
    ) -> PublishResult:
        """
        Publish a bilingual translation to Notion.

        Args:
            title: Page title.
            original_paragraphs: List of original text paragraphs.
            translated_paragraphs: List of translated paragraphs.
            source_url: Optional source URL of the original article.
            domain: Optional translation domain (tech, business, academic).
            include_metadata: Whether to include metadata at the top.

        Returns:
            PublishResult with page URL or error information.
        """
        try:
            # Build page content blocks
            blocks = []

            # Add metadata section if requested
            if include_metadata:
                metadata_blocks = self._build_metadata_blocks(
                    source_url=source_url,
                    domain=domain,
                )
                blocks.extend(metadata_blocks)

            # Build interleaved content blocks
            content_blocks = self._build_interleaved_blocks(
                original_paragraphs,
                translated_paragraphs,
            )
            blocks.extend(content_blocks)

            # Create the page
            page = self.client.pages.create(
                parent={"page_id": self.parent_page_id},
                properties={
                    "title": {
                        "title": [{"text": {"content": title}}]
                    }
                },
                children=blocks,
            )

            return PublishResult(
                success=True,
                page_url=page.get("url"),
                page_id=page.get("id"),
            )

        except APIResponseError as e:
            return PublishResult(
                success=False,
                error=f"Notion API error: {e.message}",
            )
        except Exception as e:
            return PublishResult(
                success=False,
                error=f"Unexpected error: {str(e)}",
            )

    def publish_markdown(
        self,
        title: str,
        content: str,
        source_url: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> PublishResult:
        """
        Publish from interleaved markdown format.

        Parses the markdown content in the format:
        > original paragraph
        translated paragraph

        Args:
            title: Page title.
            content: Markdown content with interleaved original/translation.
            source_url: Optional source URL.
            domain: Optional translation domain.

        Returns:
            PublishResult with page URL or error information.
        """
        # Parse the interleaved markdown
        original_paragraphs, translated_paragraphs = self._parse_interleaved_markdown(content)

        return self.publish(
            title=title,
            original_paragraphs=original_paragraphs,
            translated_paragraphs=translated_paragraphs,
            source_url=source_url,
            domain=domain,
        )

    def _parse_interleaved_markdown(self, content: str) -> tuple[List[str], List[str]]:
        """
        Parse interleaved markdown format.

        Expected format:
        > original paragraph

        translated paragraph

        Returns:
            Tuple of (original_paragraphs, translated_paragraphs).
        """
        original_paragraphs = []
        translated_paragraphs = []

        # Split by double newlines to get blocks
        blocks = re.split(r'\n\s*\n', content.strip())

        i = 0
        while i < len(blocks):
            block = blocks[i].strip()

            # Check if this is a quote block (original)
            if block.startswith('>'):
                # Extract the original text (remove > prefix)
                original = '\n'.join(
                    line[1:].strip() if line.startswith('>') else line.strip()
                    for line in block.split('\n')
                ).strip()
                original_paragraphs.append(original)

                # Look for the next non-quote block as translation
                i += 1
                if i < len(blocks):
                    next_block = blocks[i].strip()
                    if not next_block.startswith('>'):
                        translated_paragraphs.append(next_block)
                        i += 1
                    else:
                        # No translation found, add empty
                        translated_paragraphs.append("")
                else:
                    translated_paragraphs.append("")
            else:
                # Non-quote block without preceding original
                # This might be a translation that lost its original
                # or standalone text - skip it
                i += 1

        return original_paragraphs, translated_paragraphs

    def _build_metadata_blocks(
        self,
        source_url: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Build metadata blocks for the page header."""
        blocks = []

        # Add callout block with metadata
        metadata_lines = []

        if source_url:
            metadata_lines.append(f"📄 原文链接: {source_url}")

        if domain:
            domain_names = {
                "tech": "技术/编程",
                "business": "商务/金融",
                "academic": "学术研究",
            }
            domain_name = domain_names.get(domain, domain)
            metadata_lines.append(f"📚 翻译领域: {domain_name}")

        # Add translation time
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        metadata_lines.append(f"🕐 翻译时间: {timestamp}")

        if metadata_lines:
            blocks.append({
                "type": "callout",
                "callout": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "\n".join(metadata_lines)}}
                    ],
                    "icon": {"type": "emoji", "emoji": "📝"},
                    "color": "gray_background",
                }
            })

            # Add divider after metadata
            blocks.append({"type": "divider", "divider": {}})

        return blocks

    def _build_interleaved_blocks(
        self,
        original_paragraphs: List[str],
        translated_paragraphs: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Build interleaved Notion blocks.

        Format:
        - Original: Gray quote block
        - Translation: Normal paragraph
        - Spacing: Empty paragraph
        """
        blocks = []

        for i, (orig, trans) in enumerate(zip(original_paragraphs, translated_paragraphs)):
            # Original paragraph as quote (gray)
            if orig.strip():
                quote_blocks = self._create_quote_blocks(orig)
                blocks.extend(quote_blocks)

            # Translated paragraph
            if trans.strip():
                para_blocks = self._create_paragraph_blocks(trans)
                blocks.extend(para_blocks)

            # Add spacing between pairs (but not after the last pair)
            if i < len(original_paragraphs) - 1:
                blocks.append(self._create_empty_paragraph())

        return blocks

    def _create_quote_blocks(self, text: str) -> List[Dict[str, Any]]:
        """Create quote blocks, splitting if text is too long."""
        blocks = []
        chunks = self._split_text(text)

        for chunk in chunks:
            blocks.append({
                "type": "quote",
                "quote": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}],
                    "color": "gray",
                }
            })

        return blocks

    def _create_paragraph_blocks(self, text: str) -> List[Dict[str, Any]]:
        """Create paragraph blocks, splitting if text is too long."""
        blocks = []
        chunks = self._split_text(text)

        for chunk in chunks:
            blocks.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}],
                }
            })

        return blocks

    def _create_empty_paragraph(self) -> Dict[str, Any]:
        """Create an empty paragraph for spacing."""
        return {
            "type": "paragraph",
            "paragraph": {"rich_text": []},
        }

    def _split_text(self, text: str) -> List[str]:
        """
        Split text into chunks that fit Notion's block limit.

        Args:
            text: Text to split.

        Returns:
            List of text chunks, each <= MAX_BLOCK_TEXT_LENGTH.
        """
        if len(text) <= self.MAX_BLOCK_TEXT_LENGTH:
            return [text]

        chunks = []
        remaining = text

        while remaining:
            if len(remaining) <= self.MAX_BLOCK_TEXT_LENGTH:
                chunks.append(remaining)
                break

            # Find a good split point (prefer sentence or word boundaries)
            split_point = self.MAX_BLOCK_TEXT_LENGTH

            # Try to split at sentence boundary
            for sep in ['. ', '。', '! ', '！', '? ', '？', '\n']:
                last_sep = remaining[:split_point].rfind(sep)
                if last_sep > split_point // 2:
                    split_point = last_sep + len(sep)
                    break
            else:
                # Try to split at word boundary
                last_space = remaining[:split_point].rfind(' ')
                if last_space > split_point // 2:
                    split_point = last_space + 1

            chunks.append(remaining[:split_point].strip())
            remaining = remaining[split_point:].strip()

        return chunks

    def test_connection(self) -> bool:
        """
        Test the Notion API connection.

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            # Try to retrieve the parent page
            self.client.pages.retrieve(page_id=self.parent_page_id)
            return True
        except Exception:
            return False
