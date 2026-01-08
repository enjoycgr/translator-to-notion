"""
Background task manager for async translation processing.

Provides:
- Thread-safe task queue management
- Single worker thread for serial execution
- Retry mechanism with exponential backoff
- Graceful shutdown support
"""

import logging
import queue
import threading
import time
import uuid
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Callable, Any

from backend.services.cache_service import (
    CacheService,
    get_cache_service,
    TaskStatus,
    TranslationTask,
)

logger = logging.getLogger(__name__)


@dataclass
class BackgroundTask:
    """
    A background translation task to be processed.

    Attributes:
        task_id: Unique identifier for the task
        content: Text content to translate (may be empty for URL mode)
        url: URL to fetch content from (may be empty for content mode)
        title: Optional title for the translation
        source_url: Optional source URL
        domain: Translation domain (tech, business, academic)
        source_lang: Source language code
        target_lang: Target language code
        sync_to_notion: Whether to sync to Notion after completion
        created_at: Task creation timestamp
    """
    task_id: str
    content: str = ""
    url: str = ""
    title: Optional[str] = None
    source_url: Optional[str] = None
    domain: str = "tech"
    source_lang: str = "en"
    target_lang: str = "zh"
    sync_to_notion: bool = False
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class BackgroundTaskManager:
    """
    Manages background translation tasks.

    Features:
    - Thread-safe task queue (unlimited capacity)
    - Single worker thread for serial execution
    - Retry mechanism with exponential backoff
    - Integration with CacheService for state management
    - Graceful shutdown

    Configuration:
    - MAX_RETRY_COUNT: Maximum retry attempts per chunk (3)
    - CHUNK_TIMEOUT_SECONDS: Timeout for each chunk translation (300s / 5min)
    """

    # Configuration constants
    MAX_RETRY_COUNT = 3
    CHUNK_TIMEOUT_SECONDS = 300  # 5 minutes

    def __init__(
        self,
        cache_service: Optional[CacheService] = None,
        translation_executor: Optional[Callable] = None,
    ):
        """
        Initialize the background task manager.

        Args:
            cache_service: CacheService instance for task state management.
                          Uses singleton if not provided.
            translation_executor: Callable for executing translations.
                                 Should accept (content, domain, context) and return translated text.
        """
        self._cache = cache_service or get_cache_service()
        self._translation_executor = translation_executor

        # Task queue (thread-safe, unlimited capacity)
        self._task_queue: queue.Queue[BackgroundTask] = queue.Queue()

        # Pending task IDs for cancellation support
        self._pending_tasks: set[str] = set()
        self._pending_lock = threading.Lock()

        # Worker thread
        self._worker: Optional[threading.Thread] = None
        self._running = False
        self._shutdown_event = threading.Event()

        # Async event loop for translation execution
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the background task manager."""
        if self._running:
            logger.warning("BackgroundTaskManager is already running")
            return

        self._running = True
        self._shutdown_event.clear()

        # Start async event loop in separate thread
        self._start_event_loop()

        # Start worker thread
        self._worker = threading.Thread(
            target=self._worker_loop,
            name="BackgroundTaskWorker",
            daemon=True,
        )
        self._worker.start()

        logger.info("BackgroundTaskManager started")

    def _start_event_loop(self) -> None:
        """Start the async event loop in a separate thread."""
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()

        self._loop_thread = threading.Thread(
            target=run_loop,
            name="BackgroundTaskEventLoop",
            daemon=True,
        )
        self._loop_thread.start()

        # Wait for loop to be ready
        while self._loop is None:
            time.sleep(0.01)

    def submit_task(
        self,
        content: str,
        title: Optional[str] = None,
        source_url: Optional[str] = None,
        domain: str = "tech",
        source_lang: str = "en",
        target_lang: str = "zh",
    ) -> str:
        """
        Submit a new translation task to the queue.

        Args:
            content: Text content to translate
            title: Optional title
            source_url: Optional source URL
            domain: Translation domain
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            Task ID for tracking

        Raises:
            RuntimeError: If manager is not running
        """
        if not self._running:
            raise RuntimeError("BackgroundTaskManager is not running")

        task_id = str(uuid.uuid4())

        # Create background task
        task = BackgroundTask(
            task_id=task_id,
            content=content,
            title=title,
            source_url=source_url,
            domain=domain,
            source_lang=source_lang,
            target_lang=target_lang,
        )

        # Add to pending set for cancellation support
        with self._pending_lock:
            self._pending_tasks.add(task_id)

        # Add to queue
        self._task_queue.put(task)

        logger.info(
            f"Task submitted: {task_id}, "
            f"content_length={len(content)}, "
            f"domain={domain}"
        )

        return task_id

    def submit_task_with_cache(
        self,
        content: str,
        chunks: list[str],
        title: Optional[str] = None,
        source_url: Optional[str] = None,
        domain: str = "tech",
        source_lang: str = "en",
        target_lang: str = "zh",
    ) -> str:
        """
        Submit a task with pre-created cache entry.

        This method creates the cache entry first, then submits to the queue.
        Used when the task needs to be tracked in cache immediately.

        Args:
            content: Original content
            chunks: Pre-split chunks
            title: Optional title
            source_url: Optional source URL
            domain: Translation domain
            source_lang: Source language
            target_lang: Target language

        Returns:
            Task ID
        """
        if not self._running:
            raise RuntimeError("BackgroundTaskManager is not running")

        # Create task in cache first (pending status)
        task_id = self._cache.create_task(
            original_content=content,
            chunks=chunks,
            title=title,
            source_url=source_url,
            domain=domain,
        )

        # Update status to pending (create_task sets IN_PROGRESS by default)
        task = self._cache.get_task(task_id)
        if task:
            task.status = TaskStatus.PENDING

        # Create background task
        bg_task = BackgroundTask(
            task_id=task_id,
            content=content,
            title=title,
            source_url=source_url,
            domain=domain,
            source_lang=source_lang,
            target_lang=target_lang,
        )

        # Add to pending set
        with self._pending_lock:
            self._pending_tasks.add(task_id)

        # Add to queue
        self._task_queue.put(bg_task)

        logger.info(
            f"Task submitted with cache: {task_id}, "
            f"chunks={len(chunks)}, "
            f"domain={domain}"
        )

        return task_id

    def submit_task_fast(
        self,
        content: str = "",
        url: str = "",
        title: Optional[str] = None,
        source_url: Optional[str] = None,
        domain: str = "tech",
        source_lang: str = "en",
        target_lang: str = "zh",
        sync_to_notion: bool = False,
    ) -> str:
        """
        Fast submit task without URL fetching or chunking.

        This method creates a minimal cache entry and immediately returns.
        URL fetching and content chunking will be done in the background worker.

        Used for fast API response (< 100ms).

        Args:
            content: Text content to translate (may be empty for URL mode)
            url: URL to fetch content from (may be empty for content mode)
            title: Optional title
            source_url: Optional source URL
            domain: Translation domain
            source_lang: Source language
            target_lang: Target language
            sync_to_notion: Whether to sync to Notion after completion

        Returns:
            Task ID for tracking

        Raises:
            RuntimeError: If manager is not running
        """
        if not self._running:
            raise RuntimeError("BackgroundTaskManager is not running")

        task_id = str(uuid.uuid4())

        # Create lightweight cache entry (PENDING status, no chunks)
        self._cache.create_task_pending(
            task_id=task_id,
            original_content=content,
            url=url,
            title=title,
            source_url=source_url or url,
            domain=domain,
        )

        # Create background task
        bg_task = BackgroundTask(
            task_id=task_id,
            content=content,
            url=url,
            title=title,
            source_url=source_url or url,
            domain=domain,
            source_lang=source_lang,
            target_lang=target_lang,
            sync_to_notion=sync_to_notion,
        )

        # Add to pending set for cancellation support
        with self._pending_lock:
            self._pending_tasks.add(task_id)

        # Add to queue
        self._task_queue.put(bg_task)

        logger.info(
            f"Task submitted fast: {task_id}, "
            f"has_content={bool(content)}, "
            f"has_url={bool(url)}, "
            f"domain={domain}, "
            f"sync_to_notion={sync_to_notion}"
        )

        return task_id

    def retry_task(self, task_id: str) -> bool:
        """
        Retry a failed task.

        Args:
            task_id: ID of the failed task to retry

        Returns:
            True if task was re-queued, False if task not found or not failed
        """
        task = self._cache.get_task(task_id)
        if not task:
            logger.warning(f"Retry failed: task {task_id} not found")
            return False

        if task.status != TaskStatus.FAILED:
            logger.warning(
                f"Retry failed: task {task_id} is not in failed state "
                f"(current: {task.status.value})"
            )
            return False

        # Reset task state for retry
        task.status = TaskStatus.PENDING
        task.error = None
        task.translated_chunks = []
        task.current_chunk = 0
        task.updated_at = datetime.now()

        # Create background task for re-execution
        bg_task = BackgroundTask(
            task_id=task_id,
            content=task.original_content,
            title=task.title,
            source_url=task.source_url,
            domain=task.domain,
        )

        # Add to pending set and queue
        with self._pending_lock:
            self._pending_tasks.add(task_id)

        self._task_queue.put(bg_task)

        logger.info(f"Task re-queued for retry: {task_id}")
        return True

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a pending task.

        Note: Can only cancel tasks that haven't started execution yet.

        Args:
            task_id: ID of the task to cancel

        Returns:
            True if task was cancelled, False otherwise
        """
        with self._pending_lock:
            if task_id in self._pending_tasks:
                self._pending_tasks.discard(task_id)

                # Update cache status
                task = self._cache.get_task(task_id)
                if task and task.status == TaskStatus.PENDING:
                    self._cache.mark_failed(task_id, "Task cancelled by user")
                    logger.info(f"Task cancelled: {task_id}")
                    return True

        logger.warning(f"Cannot cancel task {task_id}: not in pending state")
        return False

    def get_queue_size(self) -> int:
        """Get the current queue size."""
        return self._task_queue.qsize()

    def shutdown(self, wait: bool = True, timeout: float = 30.0) -> None:
        """
        Gracefully shutdown the task manager.

        Args:
            wait: If True, wait for current task to complete
            timeout: Maximum seconds to wait for shutdown
        """
        if not self._running:
            return

        logger.info("Shutting down BackgroundTaskManager...")

        self._running = False
        self._shutdown_event.set()

        if wait and self._worker and self._worker.is_alive():
            self._worker.join(timeout=timeout)

        # Stop event loop
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=5.0)

        logger.info("BackgroundTaskManager shutdown complete")

    def _worker_loop(self) -> None:
        """Main worker loop - processes tasks serially."""
        logger.info("Worker loop started")

        while self._running or not self._task_queue.empty():
            try:
                # Get task with timeout to allow shutdown check
                try:
                    task = self._task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                # Check if shutdown was requested
                if self._shutdown_event.is_set():
                    # Re-queue the task for recovery after restart
                    self._task_queue.put(task)
                    break

                # Check if task was cancelled
                with self._pending_lock:
                    if task.task_id not in self._pending_tasks:
                        logger.info(f"Task {task.task_id} was cancelled, skipping")
                        self._task_queue.task_done()
                        continue
                    self._pending_tasks.discard(task.task_id)

                # Execute the task
                self._execute_task(task)
                self._task_queue.task_done()

            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)

        logger.info("Worker loop stopped")

    def _execute_task(self, task: BackgroundTask) -> None:
        """
        Execute a single translation task.

        This method handles the complete task lifecycle:
        1. PREPARING phase: URL fetch (if needed) + content chunking
        2. IN_PROGRESS phase: Translation of all chunks

        Args:
            task: The background task to execute
        """
        task_id = task.task_id

        logger.info(f"Executing task: {task_id}")

        # Get cache entry
        cache_task = self._cache.get_task(task_id)
        if not cache_task:
            logger.error(f"Cache task not found: {task_id}")
            return

        # ============================================================
        # Phase 1: PREPARING (URL fetch + chunking)
        # ============================================================
        self._cache.set_task_status(task_id, TaskStatus.PREPARING)

        try:
            content = task.content
            title = task.title

            # Fetch URL content if needed
            if task.url and not content:
                logger.info(f"Task {task_id}: Fetching URL: {task.url}")
                fetch_result = self._fetch_url_content(task.url)
                if not fetch_result.success:
                    error_msg = f"URL 获取失败: {fetch_result.error}"
                    logger.error(f"Task {task_id}: {error_msg}")
                    self._cache.mark_failed(task_id, error_msg)
                    return
                content = fetch_result.content
                if not title and fetch_result.title:
                    title = fetch_result.title
                logger.info(f"Task {task_id}: URL fetched, content_length={len(content)}")

            # Validate content
            if not content:
                error_msg = "内容为空（URL 获取返回空内容）"
                logger.error(f"Task {task_id}: {error_msg}")
                self._cache.mark_failed(task_id, error_msg)
                return

            # Split content into chunks
            chunks = self._split_content_to_chunks(content)
            logger.info(f"Task {task_id}: Content split into {len(chunks)} chunks")

            # Update cache with prepared content
            self._cache.update_task_prepared(
                task_id=task_id,
                original_content=content,
                chunks=chunks,
                title=title,
            )

            # Refresh cache_task reference
            cache_task = self._cache.get_task(task_id)
            if not cache_task:
                logger.error(f"Failed to get updated cache task: {task_id}")
                return

        except Exception as e:
            error_msg = f"准备阶段失败: {str(e)}"
            logger.error(f"Task {task_id}: {error_msg}", exc_info=True)
            self._cache.mark_failed(task_id, error_msg)
            return

        # ============================================================
        # Phase 2: IN_PROGRESS (Translation)
        # ============================================================
        # Note: status is already set to IN_PROGRESS by update_task_prepared()

        try:
            self._translate_chunks(
                task_id=task_id,
                cache_task=cache_task,
                domain=task.domain,
                title=title,
                sync_to_notion=task.sync_to_notion,
            )
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            self._cache.mark_failed(task_id, str(e))

    def _fetch_url_content(self, url: str):
        """
        Fetch content from URL.

        Args:
            url: URL to fetch

        Returns:
            FetchResult object with success, content, title, and error fields
        """
        from agent.tools.web_fetcher import WebFetcher
        fetcher = WebFetcher()
        return fetcher.fetch(url)

    def _split_content_to_chunks(self, content: str) -> list[str]:
        """
        Split content into chunks for translation.

        Args:
            content: Text content to split

        Returns:
            List of content chunks
        """
        from backend.services.chunking_service import ChunkingService
        from config.settings import get_config

        config = get_config()
        chunking = ChunkingService(
            max_tokens=config.translation.chunking.max_chunk_tokens,
            overlap_sentences=config.translation.chunking.overlap_sentences,
        )

        if chunking.needs_chunking(content):
            return chunking.split_by_semantic(content)
        else:
            return [content]

    def _translate_chunks(
        self,
        task_id: str,
        cache_task: TranslationTask,
        domain: str,
        title: Optional[str] = None,
        sync_to_notion: bool = False,
    ) -> None:
        """
        Translate all chunks for a task.

        Args:
            task_id: Task identifier
            cache_task: Cache task object
            domain: Translation domain
            title: Optional title for Notion page
            sync_to_notion: Whether to sync to Notion after completion
        """
        chunks = cache_task.chunks
        total_chunks = len(chunks)
        context = ""

        logger.info(f"Translating {total_chunks} chunks for task {task_id}")

        for i, chunk_text in enumerate(chunks):
            # Check if already translated (for resume)
            if i < len(cache_task.translated_chunks):
                context = cache_task.translated_chunks[i][-500:] if cache_task.translated_chunks[i] else ""
                continue

            # Translate chunk with retry
            try:
                translated = self._execute_chunk_with_retry(
                    chunk_text=chunk_text,
                    chunk_number=i + 1,
                    total_chunks=total_chunks,
                    context=context,
                    domain=domain,
                    task_id=task_id,
                )

                # Update progress
                self._cache.update_progress(
                    task_id=task_id,
                    translated_chunk=translated,
                )

                # Update context for next chunk
                context = translated[-500:] if len(translated) > 500 else translated

                logger.info(
                    f"Task {task_id}: chunk {i + 1}/{total_chunks} completed"
                )

            except Exception as e:
                logger.error(
                    f"Task {task_id}: chunk {i + 1}/{total_chunks} failed "
                    f"after {self.MAX_RETRY_COUNT} retries: {e}"
                )
                self._cache.mark_failed(task_id, f"Chunk {i + 1} failed: {str(e)}")
                return

        # Mark task as completed
        self._cache.mark_completed(task_id)
        logger.info(f"Task {task_id} completed successfully")

        # Sync to Notion if requested
        if sync_to_notion:
            self._sync_to_notion(task_id, title)

    def _execute_chunk_with_retry(
        self,
        chunk_text: str,
        chunk_number: int,
        total_chunks: int,
        context: str,
        domain: str,
        task_id: str,
    ) -> str:
        """
        Execute a single chunk translation with retry.

        Args:
            chunk_text: Text to translate
            chunk_number: Current chunk number (1-based)
            total_chunks: Total number of chunks
            context: Previous translation context
            domain: Translation domain
            task_id: Task ID for logging

        Returns:
            Translated text

        Raises:
            Exception: If translation fails after all retries
        """
        last_error = None

        for retry in range(self.MAX_RETRY_COUNT):
            try:
                # Calculate timeout with exponential backoff for retries
                timeout = self.CHUNK_TIMEOUT_SECONDS

                if self._translation_executor:
                    # Use custom executor if provided
                    return self._translation_executor(
                        chunk_text,
                        domain,
                        context,
                    )
                else:
                    # Use SDK translator agent
                    return self._execute_chunk_translation(
                        chunk_text=chunk_text,
                        chunk_number=chunk_number,
                        total_chunks=total_chunks,
                        context=context,
                        domain=domain,
                    )

            except Exception as e:
                last_error = e
                retry_delay = self._get_retry_delay(retry)

                logger.warning(
                    f"Task {task_id}: chunk {chunk_number} failed "
                    f"(attempt {retry + 1}/{self.MAX_RETRY_COUNT}), "
                    f"retrying in {retry_delay}s: {e}"
                )

                if retry < self.MAX_RETRY_COUNT - 1:
                    time.sleep(retry_delay)

        raise last_error or Exception("Translation failed after all retries")

    def _execute_chunk_translation(
        self,
        chunk_text: str,
        chunk_number: int,
        total_chunks: int,
        context: str,
        domain: str,
    ) -> str:
        """
        Execute chunk translation using SDK translator agent.

        Args:
            chunk_text: Text to translate
            chunk_number: Current chunk number
            total_chunks: Total chunks
            context: Previous context
            domain: Translation domain

        Returns:
            Translated text
        """
        from agent.sdk_translator_agent import SDKTranslatorAgent
        from config.settings import get_config

        config = get_config()
        agent = SDKTranslatorAgent(config)

        # Run async translation in the event loop
        async def do_translate():
            result_parts = []
            async for chunk in agent.translate_chunk_stream(
                content=chunk_text,
                chunk_number=chunk_number,
                total_chunks=total_chunks,
                context=context,
                domain=domain,
            ):
                if not chunk.is_complete:
                    result_parts.append(chunk.text)
            return "".join(result_parts)

        # Execute in the async event loop with timeout
        future = asyncio.run_coroutine_threadsafe(do_translate(), self._loop)
        try:
            return future.result(timeout=self.CHUNK_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            future.cancel()
            raise TimeoutError(
                f"Chunk translation timed out after {self.CHUNK_TIMEOUT_SECONDS}s"
            )

    @staticmethod
    def _get_retry_delay(retry_count: int) -> float:
        """
        Calculate retry delay using exponential backoff.

        Formula: 2^retry_count seconds
        - retry 0: 1 second
        - retry 1: 2 seconds
        - retry 2: 4 seconds

        Args:
            retry_count: Current retry attempt (0-based)

        Returns:
            Delay in seconds
        """
        return float(2 ** retry_count)

    def _sync_to_notion(self, task_id: str, title: Optional[str] = None) -> None:
        """
        Sync completed translation to Notion.

        Args:
            task_id: Task identifier
            title: Optional title for Notion page
        """
        try:
            from config.settings import get_config
            from agent.tools.notion_publisher import NotionPublisher

            config = get_config()

            # Check Notion configuration
            if not config.notion.api_key:
                logger.warning(
                    f"Task {task_id}: Notion sync skipped - API key not configured"
                )
                return

            if not config.notion.parent_page_id:
                logger.warning(
                    f"Task {task_id}: Notion sync skipped - parent page ID not configured"
                )
                return

            # Get task data
            task = self._cache.get_task(task_id)
            if not task:
                logger.error(f"Task {task_id}: Notion sync failed - task not found")
                return

            if task.status != TaskStatus.COMPLETED:
                logger.warning(
                    f"Task {task_id}: Notion sync skipped - task not completed "
                    f"(status: {task.status.value})"
                )
                return

            # Prepare publisher
            publisher = NotionPublisher(
                api_key=config.notion.api_key,
                parent_page_id=config.notion.parent_page_id,
            )

            # Use provided title or task title
            page_title = title or task.title or "翻译结果"

            # Publish to Notion
            result = publisher.publish_markdown(
                title=page_title,
                content=task.partial_result,
                source_url=task.source_url,
                domain=task.domain,
            )

            if result.success:
                logger.info(
                    f"Task {task_id}: Notion sync successful - page_url={result.page_url}"
                )
            else:
                logger.error(
                    f"Task {task_id}: Notion sync failed - {result.error}"
                )

        except Exception as e:
            logger.error(
                f"Task {task_id}: Notion sync error - {e}",
                exc_info=True
            )


# Singleton instance
_task_manager: Optional[BackgroundTaskManager] = None
_manager_lock = threading.Lock()


def get_task_manager() -> BackgroundTaskManager:
    """
    Get the background task manager singleton.

    Creates and starts the manager if not already running.

    Returns:
        BackgroundTaskManager singleton instance
    """
    global _task_manager

    if _task_manager is None:
        with _manager_lock:
            if _task_manager is None:
                _task_manager = BackgroundTaskManager()
                _task_manager.start()

    return _task_manager


def shutdown_task_manager() -> None:
    """Shutdown the task manager singleton."""
    global _task_manager

    if _task_manager is not None:
        _task_manager.shutdown()
        _task_manager = None
