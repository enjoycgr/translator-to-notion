"""
Task management API endpoints for background translation.

Provides:
- POST /api/translate/background - Submit background translation task
- GET /api/tasks - List tasks with pagination
- GET /api/tasks/{task_id} - Get task details with result
- DELETE /api/tasks/{task_id} - Delete a task
- POST /api/tasks/{task_id}/retry - Retry a failed task
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

from backend.middleware.auth import require_access_key
from backend.services.cache_service import get_cache_service, TaskStatus
from backend.services.task_manager import get_task_manager
from backend.services.task_persistence import get_persistence_service

logger = logging.getLogger(__name__)

tasks_bp = Blueprint('tasks', __name__)


def error_response(code: str, message: str) -> dict:
    """Create standard error response."""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        }
    }


def success_response(data: dict) -> dict:
    """Create standard success response."""
    return {
        "success": True,
        "data": data,
    }


@tasks_bp.route('/api/translate/background', methods=['POST'])
@require_access_key
def submit_background_task():
    """
    Submit a background translation task.

    This API returns immediately after creating the task.
    URL fetching and content chunking are done in the background.

    Request body:
    {
        "content": "text to translate",  // optional if url is provided
        "url": "https://...",            // optional if content is provided
        "title": "optional title",
        "source_url": "optional source URL",
        "domain": "tech" | "business" | "academic",
        "source_lang": "en",
        "target_lang": "zh",
        "sync_to_notion": true           // optional, sync to Notion after completion
    }

    Response:
    {
        "success": true,
        "data": {
            "task_id": "uuid",
            "status": "pending",
            "created_at": "ISO timestamp",
            "sync_to_notion": true
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(error_response(
                code='INVALID_REQUEST',
                message='Request body must be JSON',
            )), 400

        # Get content from either direct input or URL
        content = data.get('content', '')
        url = data.get('url', '')
        title = data.get('title')
        source_url = data.get('source_url') or url  # Use url as source_url if not specified

        # Validate: need either content or url
        if not content and not url:
            return jsonify(error_response(
                code='INVALID_REQUEST',
                message='Either content or url is required',
            )), 400

        # Extract optional fields
        domain = data.get('domain', 'tech')
        source_lang = data.get('source_lang', 'en')
        target_lang = data.get('target_lang', 'zh')
        sync_to_notion = data.get('sync_to_notion', False)

        # Validate domain
        valid_domains = ['tech', 'business', 'academic']
        if domain not in valid_domains:
            return jsonify(error_response(
                code='INVALID_REQUEST',
                message=f'Invalid domain. Must be one of: {", ".join(valid_domains)}',
            )), 400

        # Get task manager
        manager = get_task_manager()

        # Submit task fast (no URL fetching or chunking here)
        task_id = manager.submit_task_fast(
            content=content,
            url=url,
            title=title,
            source_url=source_url,
            domain=domain,
            source_lang=source_lang,
            target_lang=target_lang,
            sync_to_notion=sync_to_notion,
        )

        logger.info(f"Background task submitted: {task_id}, sync_to_notion={sync_to_notion}")

        # Return immediately
        return jsonify(success_response({
            "task_id": task_id,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "sync_to_notion": sync_to_notion,
        })), 201

    except Exception as e:
        logger.error(f"Failed to submit background task: {e}", exc_info=True)
        return jsonify(error_response(
            code='INTERNAL_ERROR',
            message=str(e),
        )), 500


@tasks_bp.route('/api/tasks', methods=['GET'])
@require_access_key
def get_task_list():
    """
    Get paginated list of tasks.

    Query params:
    - offset: Number of tasks to skip (default: 0)
    - limit: Maximum tasks to return (default: 20, max: 100)

    Response:
    {
        "success": true,
        "data": {
            "tasks": [...],
            "total": 50,
            "has_more": true
        }
    }
    """
    try:
        # Parse pagination params
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 20, type=int)

        # Validate
        offset = max(0, offset)
        limit = min(max(1, limit), 100)  # Clamp between 1 and 100

        # Get tasks from cache
        cache = get_cache_service()
        tasks, total, has_more = cache.get_tasks_list(
            offset=offset,
            limit=limit,
        )

        return jsonify(success_response({
            "tasks": tasks,
            "total": total,
            "has_more": has_more,
        })), 200

    except Exception as e:
        logger.error(f"Failed to get task list: {e}", exc_info=True)
        return jsonify(error_response(
            code='INTERNAL_ERROR',
            message=str(e),
        )), 500


@tasks_bp.route('/api/tasks/<task_id>', methods=['GET'])
@require_access_key
def get_task_detail(task_id: str):
    """
    Get detailed task information including translation result.

    Path params:
    - task_id: The task ID

    Response:
    {
        "success": true,
        "data": {
            "task_id": "...",
            "status": "completed",
            "progress": 100,
            "title": "...",
            "original_content": "...",
            "result": "translated content...",  // only for completed
            "error_message": "...",             // only for failed
            "domain": "tech",
            "created_at": "...",
            "completed_at": "..."
        }
    }
    """
    try:
        cache = get_cache_service()
        persistence = get_persistence_service()

        # Get task
        task = cache.get_task(task_id)
        if not task:
            return jsonify(error_response(
                code='NOT_FOUND',
                message=f'Task {task_id} not found',
            )), 404

        # Build response
        response_data = {
            "task_id": task.task_id,
            "status": task.status.value,
            "progress": task.progress,
            "title": task.title,
            "original_content": task.original_content,
            "domain": task.domain,
            "source_url": task.source_url,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "total_chunks": len(task.chunks),
            "completed_chunks": len(task.translated_chunks),
            "total_input_tokens": task.total_input_tokens,
            "total_output_tokens": task.total_output_tokens,
        }

        # Add result for completed tasks
        if task.status == TaskStatus.COMPLETED:
            # Try to load from file first (for memory efficiency)
            result = persistence.load_result_from_file(task_id)
            if not result:
                # Fall back to in-memory result
                result = task.partial_result
            response_data["result"] = result
            response_data["completed_at"] = task.updated_at.isoformat()

        # Add partial result for in-progress tasks
        elif task.status == TaskStatus.IN_PROGRESS and task.translated_chunks:
            response_data["partial_result"] = task.partial_result

        # Add info for preparing tasks
        elif task.status == TaskStatus.PREPARING:
            response_data["status_message"] = "正在获取内容并准备翻译..."
            if task.url:
                response_data["source_url"] = task.url

        # Add error for failed tasks
        if task.status == TaskStatus.FAILED:
            response_data["error_message"] = task.error

        return jsonify(success_response(response_data)), 200

    except Exception as e:
        logger.error(f"Failed to get task detail: {e}", exc_info=True)
        return jsonify(error_response(
            code='INTERNAL_ERROR',
            message=str(e),
        )), 500


@tasks_bp.route('/api/tasks/<task_id>', methods=['DELETE'])
@require_access_key
def delete_task(task_id: str):
    """
    Delete a task and its result file.

    Path params:
    - task_id: The task ID

    Response:
    {
        "success": true,
        "data": {
            "deleted": true
        }
    }
    """
    try:
        cache = get_cache_service()
        persistence = get_persistence_service()

        # Check if task exists
        task = cache.get_task(task_id)
        if not task:
            return jsonify(error_response(
                code='NOT_FOUND',
                message=f'Task {task_id} not found',
            )), 404

        # Delete from cache
        cache.delete_task(task_id)

        # Delete result file
        persistence.delete_result_file(task_id)

        # Save snapshot
        persistence.save_snapshot()

        logger.info(f"Task deleted: {task_id}")

        return jsonify(success_response({
            "deleted": True,
        })), 200

    except Exception as e:
        logger.error(f"Failed to delete task: {e}", exc_info=True)
        return jsonify(error_response(
            code='INTERNAL_ERROR',
            message=str(e),
        )), 500


@tasks_bp.route('/api/tasks/<task_id>/retry', methods=['POST'])
@require_access_key
def retry_task(task_id: str):
    """
    Retry a failed task.

    Path params:
    - task_id: The task ID (must be in failed status)

    Response:
    {
        "success": true,
        "data": {
            "task_id": "...",
            "status": "pending"
        }
    }
    """
    try:
        cache = get_cache_service()
        manager = get_task_manager()

        # Check if task exists
        task = cache.get_task(task_id)
        if not task:
            return jsonify(error_response(
                code='NOT_FOUND',
                message=f'Task {task_id} not found',
            )), 404

        # Check if task is in failed status
        if task.status != TaskStatus.FAILED:
            return jsonify(error_response(
                code='INVALID_REQUEST',
                message=f'Only failed tasks can be retried. Current status: {task.status.value}',
            )), 400

        # Retry the task
        success = manager.retry_task(task_id)
        if not success:
            return jsonify(error_response(
                code='RETRY_FAILED',
                message='Failed to retry task',
            )), 500

        logger.info(f"Task retry queued: {task_id}")

        return jsonify(success_response({
            "task_id": task_id,
            "status": "pending",
        })), 200

    except Exception as e:
        logger.error(f"Failed to retry task: {e}", exc_info=True)
        return jsonify(error_response(
            code='INTERNAL_ERROR',
            message=str(e),
        )), 500


@tasks_bp.route('/api/tasks/stats', methods=['GET'])
@require_access_key
def get_task_stats():
    """
    Get task statistics.

    Response:
    {
        "success": true,
        "data": {
            "total_tasks": 50,
            "by_status": {
                "pending": 5,
                "in_progress": 2,
                "completed": 40,
                "failed": 3
            },
            "queue_size": 5
        }
    }
    """
    try:
        cache = get_cache_service()
        manager = get_task_manager()

        stats = cache.get_stats()
        stats["queue_size"] = manager.get_queue_size()

        return jsonify(success_response(stats)), 200

    except Exception as e:
        logger.error(f"Failed to get task stats: {e}", exc_info=True)
        return jsonify(error_response(
            code='INTERNAL_ERROR',
            message=str(e),
        )), 500
