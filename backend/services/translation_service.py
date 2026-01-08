"""
Translation service layer using Claude Agent SDK.

Orchestrates the translation process:
- SDKTranslatorAgent for Claude API calls via SDK
- ChunkingService for long text splitting
- CacheService for checkpoint/resume
- SSE event generation for streaming
"""

import json
import uuid
from dataclasses import dataclass
from typing import AsyncGenerator, Optional

from config.settings import AppConfig, get_config
from agent.sdk_translator_agent import SDKTranslatorAgent, SDKStreamChunk
from backend.services.chunking_service import ChunkingService
from backend.services.cache_service import CacheService, get_cache_service, TaskStatus


@dataclass
class SSEEvent:
    """Server-Sent Event data structure."""

    event: Optional[str] = None
    data: Optional[dict] = None
    id: Optional[str] = None
    retry: Optional[int] = None

    def to_string(self) -> str:
        """Convert to SSE format string."""
        lines = []
        if self.id:
            lines.append(f"id: {self.id}")
        if self.event:
            lines.append(f"event: {self.event}")
        if self.retry:
            lines.append(f"retry: {self.retry}")
        if self.data is not None:
            lines.append(f"data: {json.dumps(self.data, ensure_ascii=False)}")
        lines.append("")  # Empty line to end the event
        return "\n".join(lines) + "\n"


class TranslationService:
    """
    High-level translation service using Claude Agent SDK.

    Features:
    - Automatic long text chunking
    - Progress tracking via cache
    - SSE streaming support
    - Checkpoint/resume for interrupted translations
    """

    def __init__(self, config: Optional[AppConfig] = None):
        """
        Initialize the translation service.

        Args:
            config: Application configuration. Uses default if not provided.
        """
        self.config = config or get_config()

        # Initialize components
        self.agent = SDKTranslatorAgent(self.config)
        self.chunking = ChunkingService(
            max_tokens=self.config.translation.chunking.max_chunk_tokens,
            overlap_sentences=self.config.translation.chunking.overlap_sentences,
        )
        self.cache = get_cache_service(
            ttl_minutes=self.config.cache.ttl_minutes,
            max_entries=self.config.cache.max_entries,
        )

    async def translate_stream_sse(
        self,
        content: Optional[str] = None,
        url: Optional[str] = None,
        title: Optional[str] = None,
        domain: str = "tech",
        sync_to_notion: bool = False,
    ) -> AsyncGenerator[str, None]:
        """
        Generate SSE format event stream for translation.

        Args:
            content: Text content to translate.
            url: URL to fetch and translate.
            title: Optional title.
            domain: Translation domain.
            sync_to_notion: Whether to sync to Notion after translation.

        Yields:
            SSE formatted strings.
        """
        task_id = str(uuid.uuid4())

        # Send initial event with task ID
        yield SSEEvent(
            event="start",
            data={"task_id": task_id, "status": "started"}
        ).to_string()

        # Handle URL fetching first
        if url and not content:
            fetch_result = self.agent.web_fetcher.fetch(url)
            if not fetch_result.success:
                yield SSEEvent(
                    event="error",
                    data={
                        "text": f"Error fetching URL: {fetch_result.error}",
                        "is_complete": True
                    }
                ).to_string()
                return
            content = fetch_result.content
            if not title:
                title = fetch_result.title

            # Send fetch complete event
            yield SSEEvent(
                event="fetch_complete",
                data={"title": title, "content_length": len(content)}
            ).to_string()

        if not content:
            yield SSEEvent(
                event="error",
                data={"text": "Error: No content to translate", "is_complete": True}
            ).to_string()
            return

        # Check if chunking is needed
        if self.chunking.needs_chunking(content):
            async for sse_string in self._stream_chunked_translation_sse(
                content=content,
                title=title,
                domain=domain,
                task_id=task_id,
                source_url=url,
                sync_to_notion=sync_to_notion,
            ):
                yield sse_string
        else:
            async for sse_string in self._stream_simple_translation_sse(
                content=content,
                title=title,
                domain=domain,
                task_id=task_id,
                source_url=url,
                sync_to_notion=sync_to_notion,
            ):
                yield sse_string

    async def _stream_simple_translation_sse(
        self,
        content: str,
        title: Optional[str],
        domain: str,
        task_id: str,
        source_url: Optional[str] = None,
        sync_to_notion: bool = False,
    ) -> AsyncGenerator[str, None]:
        """Stream simple (non-chunked) translation as SSE."""
        total_input_tokens = 0
        total_output_tokens = 0
        total_cost = 0.0

        # Create cache task if syncing to Notion
        if sync_to_notion:
            self.cache.create_task_with_id(
                task_id=task_id,
                original_content=content,
                chunks=[content],
                title=title,
                source_url=source_url,
                domain=domain,
            )

        translated_result = []

        async for chunk in self.agent.translate_stream(
            content=content,
            title=title,
            domain=domain,
            task_id=task_id,
        ):
            if not chunk.is_complete:
                translated_result.append(chunk.text)
                yield SSEEvent(
                    event="text",
                    data={"text": chunk.text, "is_complete": False}
                ).to_string()
            else:
                total_input_tokens = chunk.input_tokens
                total_output_tokens = chunk.output_tokens
                total_cost = chunk.cost_usd

        # Update cache with translated result
        if sync_to_notion:
            full_translation = "".join(translated_result)
            self.cache.update_progress(
                task_id=task_id,
                translated_chunk=full_translation,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
            )
            self.cache.mark_completed(task_id)

        # Send completion event
        yield SSEEvent(
            event="complete",
            data={
                "text": "",
                "is_complete": True,
                "task_id": task_id,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "cost_usd": total_cost,
            }
        ).to_string()

        # Sync to Notion if requested
        if sync_to_notion:
            result = self.publish_to_notion(task_id, title)
            yield SSEEvent(
                event="notion_synced",
                data=result
            ).to_string()

    async def _stream_chunked_translation_sse(
        self,
        content: str,
        title: Optional[str],
        domain: str,
        task_id: str,
        source_url: Optional[str] = None,
        sync_to_notion: bool = False,
    ) -> AsyncGenerator[str, None]:
        """Stream chunked translation as SSE."""
        # Split content
        chunks = self.chunking.split_by_semantic(content)
        total_chunks = len(chunks)

        # Create task in cache
        self.cache.create_task(
            original_content=content,
            chunks=chunks,
            title=title,
            source_url=source_url,
            domain=domain,
        )

        # Send chunking info
        yield SSEEvent(
            event="chunking",
            data={"total_chunks": total_chunks, "task_id": task_id}
        ).to_string()

        context = ""
        total_input_tokens = 0
        total_output_tokens = 0
        total_cost = 0.0

        for i, chunk_text in enumerate(chunks):
            # Send chunk progress
            yield SSEEvent(
                event="chunk_start",
                data={
                    "chunk_number": i + 1,
                    "total_chunks": total_chunks,
                    "progress": int((i / total_chunks) * 100),
                }
            ).to_string()

            chunk_result = []

            async for stream_chunk in self.agent.translate_chunk_stream(
                content=chunk_text,
                chunk_number=i + 1,
                total_chunks=total_chunks,
                context=context,
                domain=domain,
            ):
                if not stream_chunk.is_complete:
                    chunk_result.append(stream_chunk.text)
                    yield SSEEvent(
                        event="text",
                        data={"text": stream_chunk.text, "is_complete": False}
                    ).to_string()
                else:
                    total_input_tokens += stream_chunk.input_tokens
                    total_output_tokens += stream_chunk.output_tokens
                    total_cost += stream_chunk.cost_usd

            # Update context for next chunk
            full_chunk = "".join(chunk_result)
            context = full_chunk[-500:] if len(full_chunk) > 500 else full_chunk

            # Update cache
            self.cache.update_progress(
                task_id=task_id,
                translated_chunk=full_chunk,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
            )

            # Send chunk complete
            yield SSEEvent(
                event="chunk_complete",
                data={
                    "chunk_number": i + 1,
                    "total_chunks": total_chunks,
                    "progress": int(((i + 1) / total_chunks) * 100),
                }
            ).to_string()

        # Mark complete in cache
        self.cache.mark_completed(task_id)

        # Send final completion event
        yield SSEEvent(
            event="complete",
            data={
                "text": "",
                "is_complete": True,
                "task_id": task_id,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "cost_usd": total_cost,
            }
        ).to_string()

        # Sync to Notion if requested
        if sync_to_notion:
            result = self.publish_to_notion(task_id, title)
            yield SSEEvent(
                event="notion_synced",
                data=result
            ).to_string()

    async def translate_with_agent_sse(
        self,
        prompt: str,
        domain: str = "tech",
    ) -> AsyncGenerator[str, None]:
        """
        Translate using agentic mode with MCP tools.

        This allows Claude to autonomously fetch URLs and publish to Notion.

        Args:
            prompt: User prompt describing the task.
            domain: Translation domain.

        Yields:
            SSE formatted strings.
        """
        task_id = str(uuid.uuid4())

        yield SSEEvent(
            event="start",
            data={"task_id": task_id, "status": "agent_mode"}
        ).to_string()

        total_input_tokens = 0
        total_output_tokens = 0
        total_cost = 0.0

        async for chunk in self.agent.translate_with_tools(
            prompt=prompt,
            domain=domain,
        ):
            if not chunk.is_complete:
                yield SSEEvent(
                    event="text",
                    data={"text": chunk.text, "is_complete": False}
                ).to_string()
            else:
                total_input_tokens = chunk.input_tokens
                total_output_tokens = chunk.output_tokens
                total_cost = chunk.cost_usd

        yield SSEEvent(
            event="complete",
            data={
                "text": "",
                "is_complete": True,
                "task_id": task_id,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "cost_usd": total_cost,
            }
        ).to_string()

    def get_task_progress(self, task_id: str) -> dict:
        """
        Get progress information for a task.

        Args:
            task_id: The task ID.

        Returns:
            Progress information dictionary.
        """
        return self.cache.get_progress(task_id)

    def publish_to_notion(
        self,
        task_id: str,
        title: Optional[str] = None,
    ) -> dict:
        """
        Publish a completed translation to Notion.

        Args:
            task_id: The translation task ID.
            title: Optional title override for the Notion page.

        Returns:
            Dictionary with success status, notion_page_url, page_id or error.
        """
        # 检查 Notion 配置
        if not self.config.notion.api_key:
            return {
                "success": False,
                "error": "Notion API key not configured",
            }

        if not self.config.notion.parent_page_id:
            return {
                "success": False,
                "error": "Notion parent page ID not configured",
            }

        # 获取任务信息
        task = self.cache.get_task(task_id)
        if not task:
            return {
                "success": False,
                "error": f"Task '{task_id}' not found or expired",
            }

        # 检查任务是否完成
        from backend.services.cache_service import TaskStatus
        if task.status != TaskStatus.COMPLETED:
            return {
                "success": False,
                "error": f"Task not completed. Current status: {task.status.value}",
            }

        # 准备发布内容
        from agent.tools.notion_publisher import NotionPublisher

        publisher = NotionPublisher(
            api_key=self.config.notion.api_key,
            parent_page_id=self.config.notion.parent_page_id,
        )

        # 使用提供的标题或任务中的标题
        page_title = title or task.title or "翻译结果"

        # 发布到 Notion（使用 markdown 格式，因为翻译结果是 markdown 格式的）
        result = publisher.publish_markdown(
            title=page_title,
            content=task.partial_result,
            source_url=task.source_url,
            domain=task.domain,
        )

        if result.success:
            return {
                "success": True,
                "notion_page_url": result.page_url,
                "page_id": result.page_id,
            }
        else:
            return {
                "success": False,
                "error": result.error,
            }


# Singleton instance
_service: Optional[TranslationService] = None


def get_translation_service(config: Optional[AppConfig] = None) -> TranslationService:
    """
    Get the translation service singleton.

    Args:
        config: Optional configuration.

    Returns:
        TranslationService singleton instance.
    """
    global _service
    if _service is None:
        _service = TranslationService(config)
    return _service


# Aliases for backward compatibility
SDKTranslationService = TranslationService
get_sdk_translation_service = get_translation_service
