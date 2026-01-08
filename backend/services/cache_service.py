"""
In-memory cache service for translation checkpoint/resume.

Provides task state management for long-running translations,
enabling resume from the last successful chunk.
"""

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum


class TaskStatus(str, Enum):
    """Status of a translation task."""
    PENDING = "pending"
    PREPARING = "preparing"      # URL 获取 + 内容分块阶段
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TranslationTask:
    """
    A translation task with state for checkpoint/resume.

    Tracks:
    - Original content split into chunks
    - Translated chunks
    - Current progress
    - Status and timing information
    """
    task_id: str
    original_content: str
    chunks: List[str]
    translated_chunks: List[str] = field(default_factory=list)
    current_chunk: int = 0
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    title: Optional[str] = None
    source_url: Optional[str] = None
    domain: str = "tech"
    error: Optional[str] = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    url: str = ""  # 待获取的 URL（用于延迟加载模式）

    @property
    def progress(self) -> int:
        """Get progress as percentage (0-100)."""
        if not self.chunks:
            return 0
        return int((len(self.translated_chunks) / len(self.chunks)) * 100)

    @property
    def is_complete(self) -> bool:
        """Check if translation is complete."""
        return len(self.translated_chunks) >= len(self.chunks)

    @property
    def partial_result(self) -> str:
        """Get the translated content so far."""
        return "\n\n".join(self.translated_chunks)


class CacheService:
    """
    In-memory cache service for translation tasks.

    Features:
    - Thread-safe operations
    - TTL-based expiration
    - Maximum entry limit with LRU eviction
    - Progress tracking
    """

    def __init__(
        self,
        ttl_minutes: int = 30,
        max_entries: int = 100,
    ):
        """
        Initialize the cache service.

        Args:
            ttl_minutes: Time-to-live for cached tasks in minutes.
            max_entries: Maximum number of cached tasks.
        """
        self._cache: Dict[str, TranslationTask] = {}
        self._lock = threading.Lock()
        self._ttl = timedelta(minutes=ttl_minutes)
        self._max_entries = max_entries

    def create_task(
        self,
        original_content: str,
        chunks: List[str],
        title: Optional[str] = None,
        source_url: Optional[str] = None,
        domain: str = "tech",
    ) -> str:
        """
        Create a new translation task.

        Args:
            original_content: The original content to translate.
            chunks: Pre-split chunks of the content.
            title: Optional title.
            source_url: Optional source URL.
            domain: Translation domain.

        Returns:
            Task ID for the new task.
        """
        task_id = str(uuid.uuid4())
        task = TranslationTask(
            task_id=task_id,
            original_content=original_content,
            chunks=chunks,
            title=title,
            source_url=source_url,
            domain=domain,
            status=TaskStatus.IN_PROGRESS,
        )

        with self._lock:
            self._cleanup_expired()
            self._ensure_capacity()
            self._cache[task_id] = task

        return task_id

    def create_task_with_id(
        self,
        task_id: str,
        original_content: str,
        chunks: List[str],
        title: Optional[str] = None,
        source_url: Optional[str] = None,
        domain: str = "tech",
    ) -> str:
        """
        Create a new translation task with specified ID.

        Used for simple translation mode where task_id is generated earlier.

        Args:
            task_id: The task ID to use.
            original_content: The original content to translate.
            chunks: Pre-split chunks of the content.
            title: Optional title.
            source_url: Optional source URL.
            domain: Translation domain.

        Returns:
            The same task ID.
        """
        task = TranslationTask(
            task_id=task_id,
            original_content=original_content,
            chunks=chunks,
            title=title,
            source_url=source_url,
            domain=domain,
            status=TaskStatus.IN_PROGRESS,
        )

        with self._lock:
            self._cleanup_expired()
            self._ensure_capacity()
            self._cache[task_id] = task

        return task_id

    def get_task(self, task_id: str) -> Optional[TranslationTask]:
        """
        Get a task by ID.

        Args:
            task_id: The task ID.

        Returns:
            The task if found and not expired, None otherwise.
        """
        with self._lock:
            task = self._cache.get(task_id)
            if task and self._is_expired(task):
                del self._cache[task_id]
                return None
            return task

    def update_progress(
        self,
        task_id: str,
        translated_chunk: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> bool:
        """
        Update task with a newly translated chunk.

        Args:
            task_id: The task ID.
            translated_chunk: The translated chunk text.
            input_tokens: Tokens used for input.
            output_tokens: Tokens generated for output.

        Returns:
            True if update was successful, False if task not found.
        """
        with self._lock:
            task = self._cache.get(task_id)
            if not task:
                return False

            task.translated_chunks.append(translated_chunk)
            task.current_chunk = len(task.translated_chunks)
            task.total_input_tokens += input_tokens
            task.total_output_tokens += output_tokens
            task.updated_at = datetime.now()

            # Check if complete
            if task.is_complete:
                task.status = TaskStatus.COMPLETED

            return True

    def mark_completed(self, task_id: str) -> bool:
        """
        Mark a task as completed.

        Args:
            task_id: The task ID.

        Returns:
            True if successful, False if task not found.
        """
        with self._lock:
            task = self._cache.get(task_id)
            if not task:
                return False

            task.status = TaskStatus.COMPLETED
            task.updated_at = datetime.now()
            return True

    def mark_failed(self, task_id: str, error: str) -> bool:
        """
        Mark a task as failed.

        Args:
            task_id: The task ID.
            error: Error message.

        Returns:
            True if successful, False if task not found.
        """
        with self._lock:
            task = self._cache.get(task_id)
            if not task:
                return False

            task.status = TaskStatus.FAILED
            task.error = error
            task.updated_at = datetime.now()
            return True

    def get_progress(self, task_id: str) -> dict:
        """
        Get task progress information.

        Args:
            task_id: The task ID.

        Returns:
            Dictionary with progress information.
        """
        task = self.get_task(task_id)

        if not task:
            return {
                "status": "not_found",
                "progress": 0,
                "partial_result": None,
            }

        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "progress": task.progress,
            "partial_result": task.partial_result,
            "original_content": task.original_content,
            "title": task.title,
            "source_url": task.source_url,
            "domain": task.domain,
            "error": task.error,
            "chunks_completed": len(task.translated_chunks),
            "chunks_total": len(task.chunks),
            "total_input_tokens": task.total_input_tokens,
            "total_output_tokens": task.total_output_tokens,
        }

    def get_pending_chunks(self, task_id: str) -> List[str]:
        """
        Get the remaining chunks to translate.

        Args:
            task_id: The task ID.

        Returns:
            List of chunk texts that haven't been translated yet.
        """
        task = self.get_task(task_id)
        if not task:
            return []

        return task.chunks[len(task.translated_chunks):]

    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task from cache.

        Args:
            task_id: The task ID.

        Returns:
            True if task was deleted, False if not found.
        """
        with self._lock:
            if task_id in self._cache:
                del self._cache[task_id]
                return True
            return False

    def clear_all(self) -> int:
        """
        Clear all cached tasks.

        Returns:
            Number of tasks cleared.
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics.
        """
        with self._lock:
            total = len(self._cache)
            by_status = {}
            for task in self._cache.values():
                status = task.status.value
                by_status[status] = by_status.get(status, 0) + 1

            return {
                "total_tasks": total,
                "by_status": by_status,
                "max_entries": self._max_entries,
                "ttl_minutes": self._ttl.total_seconds() / 60,
            }

    def _is_expired(self, task: TranslationTask) -> bool:
        """Check if a task has expired."""
        return datetime.now() - task.created_at > self._ttl

    def _cleanup_expired(self) -> int:
        """
        Remove expired tasks.

        Must be called with lock held.

        Returns:
            Number of tasks removed.
        """
        now = datetime.now()
        expired = [
            task_id
            for task_id, task in self._cache.items()
            if now - task.created_at > self._ttl
        ]
        for task_id in expired:
            del self._cache[task_id]
        return len(expired)

    def _ensure_capacity(self) -> None:
        """
        Ensure cache doesn't exceed max entries.

        Removes oldest tasks if necessary.
        Must be called with lock held.
        """
        if len(self._cache) < self._max_entries:
            return

        # Sort by created_at and remove oldest
        sorted_tasks = sorted(
            self._cache.items(),
            key=lambda x: x[1].created_at,
        )

        # Remove oldest 10% of tasks
        to_remove = max(1, len(sorted_tasks) // 10)
        for task_id, _ in sorted_tasks[:to_remove]:
            del self._cache[task_id]

    # ============================================================
    # Extended methods for background task support
    # ============================================================

    def get_all_tasks(self) -> Dict[str, TranslationTask]:
        """
        Get all tasks in cache.

        Used for persistence/snapshot operations.

        Returns:
            Dictionary of all tasks (task_id -> TranslationTask)
        """
        with self._lock:
            return dict(self._cache)

    def restore_tasks(self, tasks: Dict[str, TranslationTask]) -> int:
        """
        Restore tasks from external source (persistence).

        Used during service recovery.

        Args:
            tasks: Dictionary of tasks to restore

        Returns:
            Number of tasks restored
        """
        with self._lock:
            restored = 0
            for task_id, task in tasks.items():
                if task_id not in self._cache:
                    self._cache[task_id] = task
                    restored += 1
            return restored

    def get_task_metadata(self, task_id: str) -> Optional[dict]:
        """
        Get task metadata without translation result.

        Lightweight version of get_progress() for listing.

        Args:
            task_id: The task ID

        Returns:
            Dictionary with task metadata (no result), or None if not found
        """
        task = self.get_task(task_id)
        if not task:
            return None

        # Generate title from content if not set
        title = task.title
        if not title:
            # Use first 50 characters of content as title
            content_preview = task.original_content[:50]
            if len(task.original_content) > 50:
                content_preview += "..."
            title = content_preview

        return {
            "task_id": task.task_id,
            "title": title,
            "status": task.status.value,
            "progress": task.progress,
            "domain": task.domain,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "error_message": task.error,
            "total_chunks": len(task.chunks),
            "completed_chunks": len(task.translated_chunks),
        }

    def get_tasks_list(
        self,
        offset: int = 0,
        limit: int = 20,
        status_filter: Optional[TaskStatus] = None,
    ) -> tuple[List[dict], int, bool]:
        """
        Get paginated list of task metadata.

        Args:
            offset: Number of tasks to skip
            limit: Maximum number of tasks to return
            status_filter: Optional status filter

        Returns:
            Tuple of (tasks_list, total_count, has_more)
        """
        with self._lock:
            # Filter and sort tasks
            tasks = list(self._cache.values())

            if status_filter:
                tasks = [t for t in tasks if t.status == status_filter]

            # Sort by created_at descending (newest first)
            tasks.sort(key=lambda t: t.created_at, reverse=True)

            total = len(tasks)

            # Apply pagination
            paginated = tasks[offset:offset + limit]
            has_more = offset + limit < total

            # Convert to metadata dicts
            result = []
            for task in paginated:
                title = task.title
                if not title:
                    content_preview = task.original_content[:50]
                    if len(task.original_content) > 50:
                        content_preview += "..."
                    title = content_preview

                result.append({
                    "task_id": task.task_id,
                    "title": title,
                    "status": task.status.value,
                    "progress": task.progress,
                    "domain": task.domain,
                    "created_at": task.created_at.isoformat(),
                })

            return result, total, has_more

    def set_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        error: Optional[str] = None,
    ) -> bool:
        """
        Update task status with notification support.

        Args:
            task_id: The task ID
            status: New status
            error: Optional error message (for FAILED status)

        Returns:
            True if updated, False if task not found
        """
        with self._lock:
            task = self._cache.get(task_id)
            if not task:
                return False

            old_status = task.status
            task.status = status
            task.updated_at = datetime.now()

            if error:
                task.error = error

            # Note: Status change notification handled by persistence service
            return True

    def create_task_pending(
        self,
        task_id: str,
        original_content: str = "",
        url: str = "",
        title: Optional[str] = None,
        source_url: Optional[str] = None,
        domain: str = "tech",
    ) -> str:
        """
        Create a PENDING status task (without chunks).

        Used for fast API response - URL fetching and chunking
        will be done later in the background worker.

        Args:
            task_id: The task ID to use
            original_content: Content (may be empty for URL mode)
            url: URL to fetch (may be empty for content mode)
            title: Optional title
            source_url: Optional source URL
            domain: Translation domain

        Returns:
            The same task ID
        """
        task = TranslationTask(
            task_id=task_id,
            original_content=original_content,
            chunks=[],  # Empty, will be filled later
            title=title,
            source_url=source_url,
            domain=domain,
            status=TaskStatus.PENDING,
            url=url,
        )

        with self._lock:
            self._cleanup_expired()
            self._ensure_capacity()
            self._cache[task_id] = task

        return task_id

    def update_task_prepared(
        self,
        task_id: str,
        original_content: str,
        chunks: List[str],
        title: Optional[str] = None,
    ) -> bool:
        """
        Update a task after preparation is complete.

        Fills in content and chunks, transitions to IN_PROGRESS.

        Args:
            task_id: The task ID
            original_content: The fetched/provided content
            chunks: Split content chunks
            title: Optional title (from URL fetch)

        Returns:
            True if updated, False if task not found
        """
        with self._lock:
            task = self._cache.get(task_id)
            if not task:
                return False

            task.original_content = original_content
            task.chunks = chunks
            if title and not task.title:
                task.title = title
            task.status = TaskStatus.IN_PROGRESS
            task.updated_at = datetime.now()
            return True

    def get_task_result(self, task_id: str) -> Optional[str]:
        """
        Get full translation result for a task.

        Args:
            task_id: The task ID

        Returns:
            Full translated content or None if not found/completed
        """
        task = self.get_task(task_id)
        if not task:
            return None

        if task.status != TaskStatus.COMPLETED:
            return task.partial_result if task.translated_chunks else None

        return task.partial_result


# Singleton instance
_cache_service: Optional[CacheService] = None


def get_cache_service(
    ttl_minutes: int = 30,
    max_entries: int = 100,
) -> CacheService:
    """
    Get the cache service singleton.

    Args:
        ttl_minutes: TTL for new service (ignored if already created).
        max_entries: Max entries for new service (ignored if already created).

    Returns:
        CacheService singleton instance.
    """
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService(
            ttl_minutes=ttl_minutes,
            max_entries=max_entries,
        )
    return _cache_service
