"""
Task persistence service for saving/loading tasks to/from disk.

Provides:
- Periodic snapshots to JSON file
- Immediate persistence on state changes
- Task recovery on service restart
- Expired task cleanup
- Result file management
"""

import json
import logging
import os
import threading
import time
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from backend.services.cache_service import (
    CacheService,
    get_cache_service,
    TaskStatus,
    TranslationTask,
)

logger = logging.getLogger(__name__)


class TaskPersistenceService:
    """
    Manages task persistence to disk.

    Features:
    - Periodic snapshots (every 30 seconds)
    - Immediate persistence on status changes
    - Recovery of pending/in_progress tasks on startup
    - Cleanup of expired tasks (7+ days old)
    - Separate result files to minimize memory usage

    File structure:
    - data/tasks.json: Task metadata (without results)
    - data/results/{task_id}.txt: Translation results
    """

    # Configuration
    SNAPSHOT_INTERVAL_SECONDS = 30
    TASK_RETENTION_DAYS = 7
    DATA_DIR = Path("data")
    RESULTS_DIR = Path("data/results")
    TASKS_FILE = Path("data/tasks.json")

    # JSON schema version
    SCHEMA_VERSION = 1

    def __init__(
        self,
        cache_service: Optional[CacheService] = None,
        data_dir: Optional[Path] = None,
    ):
        """
        Initialize the persistence service.

        Args:
            cache_service: CacheService instance to sync with.
                          Uses singleton if not provided.
            data_dir: Base data directory. Uses default if not provided.
        """
        self._cache = cache_service or get_cache_service()

        # Configure paths
        if data_dir:
            self.DATA_DIR = Path(data_dir)
            self.RESULTS_DIR = self.DATA_DIR / "results"
            self.TASKS_FILE = self.DATA_DIR / "tasks.json"

        # Ensure directories exist
        self._ensure_directories()

        # Snapshot thread
        self._snapshot_thread: Optional[threading.Thread] = None
        self._running = False
        self._stop_event = threading.Event()
        self._last_snapshot: Optional[datetime] = None

        # Lock for file operations
        self._file_lock = threading.Lock()

    def _ensure_directories(self) -> None:
        """Ensure data directories exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    def start(self) -> None:
        """Start the persistence service with periodic snapshots."""
        if self._running:
            logger.warning("TaskPersistenceService is already running")
            return

        self._running = True
        self._stop_event.clear()

        # Start snapshot thread
        self._snapshot_thread = threading.Thread(
            target=self._snapshot_loop,
            name="TaskPersistenceSnapshot",
            daemon=True,
        )
        self._snapshot_thread.start()

        logger.info("TaskPersistenceService started")

    def stop(self) -> None:
        """Stop the persistence service."""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._snapshot_thread and self._snapshot_thread.is_alive():
            self._snapshot_thread.join(timeout=5.0)

        # Final snapshot
        self.save_snapshot()

        logger.info("TaskPersistenceService stopped")

    def _snapshot_loop(self) -> None:
        """Periodic snapshot loop."""
        while self._running and not self._stop_event.is_set():
            try:
                self.save_snapshot()
            except Exception as e:
                logger.error(f"Snapshot failed: {e}", exc_info=True)

            # Wait for interval or stop event
            self._stop_event.wait(timeout=self.SNAPSHOT_INTERVAL_SECONDS)

    def save_snapshot(self) -> bool:
        """
        Save current task state to disk.

        Returns:
            True if snapshot was saved successfully
        """
        with self._file_lock:
            try:
                # Get all tasks from cache
                tasks_data = self._serialize_tasks()

                # Build snapshot data
                snapshot = {
                    "version": self.SCHEMA_VERSION,
                    "last_updated": datetime.now().isoformat(),
                    "tasks": tasks_data,
                }

                # Write atomically using temp file
                temp_file = self.TASKS_FILE.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(snapshot, f, ensure_ascii=False, indent=2)

                # Rename to final location (atomic on most systems)
                temp_file.replace(self.TASKS_FILE)

                self._last_snapshot = datetime.now()
                logger.debug(f"Snapshot saved: {len(tasks_data)} tasks")

                return True

            except Exception as e:
                logger.error(f"Failed to save snapshot: {e}", exc_info=True)
                return False

    def _serialize_tasks(self) -> Dict[str, Any]:
        """
        Serialize all tasks from cache to dict format.

        Note: Does not include translated_chunks (stored in result files).

        Returns:
            Dictionary of task_id -> task_data
        """
        tasks_data = {}

        # Get all tasks from cache (we need to add this method to CacheService)
        cache_tasks = self._get_all_tasks_from_cache()

        for task_id, task in cache_tasks.items():
            task_data = {
                "task_id": task.task_id,
                "status": task.status.value,
                "progress": task.progress,
                "original_content": task.original_content,
                "total_chunks": len(task.chunks),
                "completed_chunks": len(task.translated_chunks),
                "title": task.title,
                "source_url": task.source_url,
                "domain": task.domain,
                "error_message": task.error,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "total_input_tokens": task.total_input_tokens,
                "total_output_tokens": task.total_output_tokens,
            }

            # Store result file reference if completed
            if task.status == TaskStatus.COMPLETED:
                task_data["result_file"] = f"results/{task_id}.txt"

            tasks_data[task_id] = task_data

        return tasks_data

    def _get_all_tasks_from_cache(self) -> Dict[str, TranslationTask]:
        """Get all tasks from cache service."""
        # Access internal cache dict (we'll add a proper method later)
        with self._cache._lock:
            return dict(self._cache._cache)

    def load_and_recover(self) -> int:
        """
        Load tasks from disk and recover pending/in_progress tasks.

        Recovery rules:
        - pending tasks: Keep pending, re-add to queue
        - in_progress tasks: Reset to pending, re-add to queue
        - completed/failed tasks: Keep as is

        Returns:
            Number of tasks recovered
        """
        with self._file_lock:
            if not self.TASKS_FILE.exists():
                logger.info("No tasks file found, starting fresh")
                return 0

            try:
                with open(self.TASKS_FILE, "r", encoding="utf-8") as f:
                    snapshot = json.load(f)

                # Check version compatibility
                version = snapshot.get("version", 1)
                if version != self.SCHEMA_VERSION:
                    logger.warning(
                        f"Tasks file version mismatch: {version} vs {self.SCHEMA_VERSION}"
                    )

                tasks_data = snapshot.get("tasks", {})
                recovered_count = 0
                tasks_to_queue = []

                for task_id, task_data in tasks_data.items():
                    task = self._deserialize_task(task_id, task_data)
                    if not task:
                        continue

                    original_status = task.status

                    # Apply recovery rules
                    if task.status == TaskStatus.IN_PROGRESS:
                        # Reset to pending for re-execution
                        task.status = TaskStatus.PENDING
                        task.translated_chunks = []
                        task.current_chunk = 0
                        tasks_to_queue.append(task)
                        recovered_count += 1
                        logger.info(
                            f"Task {task_id} recovered: "
                            f"{original_status.value} -> pending"
                        )

                    elif task.status == TaskStatus.PENDING:
                        tasks_to_queue.append(task)
                        recovered_count += 1
                        logger.info(f"Task {task_id} recovered: pending")

                    # Restore to cache
                    self._restore_task_to_cache(task)

                # Queue recovered tasks for execution
                if tasks_to_queue:
                    self._queue_recovered_tasks(tasks_to_queue)

                logger.info(
                    f"Recovery complete: {len(tasks_data)} tasks loaded, "
                    f"{recovered_count} tasks queued"
                )

                return recovered_count

            except Exception as e:
                logger.error(f"Failed to load/recover tasks: {e}", exc_info=True)
                return 0

    def _deserialize_task(
        self,
        task_id: str,
        task_data: Dict[str, Any],
    ) -> Optional[TranslationTask]:
        """
        Deserialize task data to TranslationTask object.

        Args:
            task_id: Task identifier
            task_data: Serialized task data

        Returns:
            TranslationTask object or None if invalid
        """
        try:
            # Reconstruct chunks list (we only store count)
            original_content = task_data.get("original_content", "")
            total_chunks = task_data.get("total_chunks", 1)

            # Need to re-chunk the content
            from backend.services.chunking_service import ChunkingService
            from config.settings import get_config

            config = get_config()
            chunking = ChunkingService(
                max_tokens=config.translation.chunking.max_chunk_tokens,
                overlap_sentences=config.translation.chunking.overlap_sentences,
            )

            if chunking.needs_chunking(original_content):
                chunks = chunking.split_by_semantic(original_content)
            else:
                chunks = [original_content]

            # Load translated chunks from result file if completed
            translated_chunks = []
            status_value = task_data.get("status", "pending")
            if status_value == "completed":
                result_file = self.RESULTS_DIR / f"{task_id}.txt"
                if result_file.exists():
                    # For completed tasks, we have the full result
                    # but don't need to load it into memory here
                    pass

            task = TranslationTask(
                task_id=task_id,
                original_content=original_content,
                chunks=chunks,
                translated_chunks=translated_chunks,
                current_chunk=task_data.get("completed_chunks", 0),
                status=TaskStatus(status_value),
                created_at=datetime.fromisoformat(task_data["created_at"]),
                updated_at=datetime.fromisoformat(task_data["updated_at"]),
                title=task_data.get("title"),
                source_url=task_data.get("source_url"),
                domain=task_data.get("domain", "tech"),
                error=task_data.get("error_message"),
                total_input_tokens=task_data.get("total_input_tokens", 0),
                total_output_tokens=task_data.get("total_output_tokens", 0),
            )

            return task

        except Exception as e:
            logger.error(f"Failed to deserialize task {task_id}: {e}")
            return None

    def _restore_task_to_cache(self, task: TranslationTask) -> None:
        """Restore a task to the cache service."""
        with self._cache._lock:
            self._cache._cache[task.task_id] = task

    def _queue_recovered_tasks(self, tasks: list[TranslationTask]) -> None:
        """
        Queue recovered tasks for execution.

        Args:
            tasks: List of tasks to queue
        """
        from backend.services.task_manager import get_task_manager

        try:
            manager = get_task_manager()
            for task in tasks:
                from backend.services.task_manager import BackgroundTask

                bg_task = BackgroundTask(
                    task_id=task.task_id,
                    content=task.original_content,
                    title=task.title,
                    source_url=task.source_url,
                    domain=task.domain,
                )
                manager._task_queue.put(bg_task)

                # Add to pending set
                with manager._pending_lock:
                    manager._pending_tasks.add(task.task_id)

        except Exception as e:
            logger.error(f"Failed to queue recovered tasks: {e}")

    def save_result_to_file(self, task_id: str, result: str) -> bool:
        """
        Save translation result to a separate file.

        Used to offload results from memory after task completion.

        Args:
            task_id: Task identifier
            result: Translation result text

        Returns:
            True if saved successfully
        """
        try:
            result_file = self.RESULTS_DIR / f"{task_id}.txt"
            with open(result_file, "w", encoding="utf-8") as f:
                f.write(result)

            logger.debug(f"Result saved to file: {result_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save result for {task_id}: {e}")
            return False

    def load_result_from_file(self, task_id: str) -> Optional[str]:
        """
        Load translation result from file.

        Args:
            task_id: Task identifier

        Returns:
            Result text or None if not found
        """
        try:
            result_file = self.RESULTS_DIR / f"{task_id}.txt"
            if not result_file.exists():
                return None

            with open(result_file, "r", encoding="utf-8") as f:
                return f.read()

        except Exception as e:
            logger.error(f"Failed to load result for {task_id}: {e}")
            return None

    def delete_result_file(self, task_id: str) -> bool:
        """
        Delete a task's result file.

        Args:
            task_id: Task identifier

        Returns:
            True if deleted successfully or not exists
        """
        try:
            result_file = self.RESULTS_DIR / f"{task_id}.txt"
            if result_file.exists():
                result_file.unlink()
            return True
        except Exception as e:
            logger.error(f"Failed to delete result file for {task_id}: {e}")
            return False

    def cleanup_expired_tasks(self) -> int:
        """
        Remove tasks older than retention period.

        Only removes completed/failed tasks.

        Returns:
            Number of tasks removed
        """
        cutoff = datetime.now() - timedelta(days=self.TASK_RETENTION_DAYS)
        removed_count = 0

        with self._file_lock:
            tasks_to_remove = []

            # Find expired tasks in cache
            with self._cache._lock:
                for task_id, task in list(self._cache._cache.items()):
                    if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                        if task.created_at < cutoff:
                            tasks_to_remove.append(task_id)

            # Remove tasks
            for task_id in tasks_to_remove:
                # Delete from cache
                self._cache.delete_task(task_id)

                # Delete result file
                self.delete_result_file(task_id)

                removed_count += 1
                logger.info(f"Expired task removed: {task_id}")

        if removed_count > 0:
            self.save_snapshot()
            logger.info(f"Cleanup complete: {removed_count} expired tasks removed")

        return removed_count

    def on_task_status_change(
        self,
        task_id: str,
        old_status: TaskStatus,
        new_status: TaskStatus,
    ) -> None:
        """
        Called when a task's status changes.

        Triggers immediate persistence for important state changes.

        Args:
            task_id: Task identifier
            old_status: Previous status
            new_status: New status
        """
        # Save result to file when completed
        if new_status == TaskStatus.COMPLETED:
            task = self._cache.get_task(task_id)
            if task:
                self.save_result_to_file(task_id, task.partial_result)

        # Save snapshot immediately
        self.save_snapshot()

        logger.info(
            f"Task {task_id} status changed: "
            f"{old_status.value} -> {new_status.value}, snapshot saved"
        )


# Singleton instance
_persistence_service: Optional[TaskPersistenceService] = None
_persistence_lock = threading.Lock()


def get_persistence_service() -> TaskPersistenceService:
    """
    Get the task persistence service singleton.

    Creates and starts the service if not already running.

    Returns:
        TaskPersistenceService singleton instance
    """
    global _persistence_service

    if _persistence_service is None:
        with _persistence_lock:
            if _persistence_service is None:
                _persistence_service = TaskPersistenceService()
                _persistence_service.start()

    return _persistence_service


def shutdown_persistence_service() -> None:
    """Shutdown the persistence service singleton."""
    global _persistence_service

    if _persistence_service is not None:
        _persistence_service.stop()
        _persistence_service = None
