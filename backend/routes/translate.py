"""
Translation API endpoints.

Provides:
- POST /api/translate/stream - Streaming translation (SSE)
- POST /api/translate/agent - Agent mode with tools (SSE)
- GET /api/translate/progress/{task_id} - Check translation progress
"""

import asyncio
import threading
from flask import Blueprint, request, jsonify, Response, stream_with_context

from backend.middleware.auth import require_access_key
from backend.schemas.translate_schema import (
    TranslateRequest,
    ResumeResponse,
    ResumeResponseData,
    validation_error,
    error_response,
)
from backend.services.translation_service import get_translation_service


translate_bp = Blueprint('translate', __name__)


# 单例事件循环管理器
class AsyncLoopManager:
    """线程安全的单例事件循环管理器。"""

    _instance = None
    _lock = threading.Lock()
    _loop = None
    _thread = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def get_loop(self) -> asyncio.AbstractEventLoop:
        """获取或创建单例事件循环。"""
        if self._loop is None or self._loop.is_closed():
            with self._lock:
                if self._loop is None or self._loop.is_closed():
                    self._loop = asyncio.new_event_loop()
                    # 在后台线程中运行事件循环
                    self._thread = threading.Thread(
                        target=self._run_loop,
                        daemon=True
                    )
                    self._thread.start()
        return self._loop

    def _run_loop(self):
        """在后台线程中运行事件循环。"""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()


_loop_manager = AsyncLoopManager()


def _run_async_generator_sync(async_gen):
    """
    Run async generator in sync context for Flask.

    使用单例事件循环，避免每次请求创建新循环。

    Args:
        async_gen: Async generator to run.

    Yields:
        Values from the async generator.
    """
    loop = _loop_manager.get_loop()

    async def get_next():
        return await async_gen.__anext__()

    try:
        while True:
            try:
                future = asyncio.run_coroutine_threadsafe(get_next(), loop)
                value = future.result(timeout=300)  # 5分钟超时
                yield value
            except StopAsyncIteration:
                break
            except Exception as e:
                # 清理异步生成器
                try:
                    asyncio.run_coroutine_threadsafe(async_gen.aclose(), loop).result(timeout=5)
                except Exception:
                    pass
                raise e
    except GeneratorExit:
        # 客户端断开连接时清理
        try:
            asyncio.run_coroutine_threadsafe(async_gen.aclose(), loop).result(timeout=5)
        except Exception:
            pass


@translate_bp.route('/api/translate/stream', methods=['POST'])
@require_access_key
def translate_stream():
    """
    Streaming translation endpoint using Server-Sent Events (SSE).

    Request body:
    {
        "content": "text to translate" or "url": "https://...",
        "title": "optional title",
        "domain": "tech" | "business" | "academic"
    }

    Response: text/event-stream with events:
    - event: start - {"task_id": "...", "status": "started"}
    - event: fetch_complete - {"title": "...", "content_length": N}
    - event: chunking - {"total_chunks": N, "task_id": "..."}
    - event: chunk_start - {"chunk_number": N, "total_chunks": M, "progress": P}
    - event: text - {"text": "...", "is_complete": false}
    - event: chunk_complete - {"chunk_number": N, "total_chunks": M, "progress": P}
    - event: complete - {"text": "", "is_complete": true, ...}
    - event: error - {"text": "error message", "is_complete": true}
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(error_response(
                code='INVALID_REQUEST',
                message='Request body must be JSON',
            )), 400

        # Parse and validate request
        req = TranslateRequest.from_dict(data)
        errors = req.validate()

        if errors:
            return jsonify(validation_error(errors)), 400

        # Get translation service
        service = get_translation_service()

        def generate():
            """Generator for SSE stream."""
            async_gen = service.translate_stream_sse(
                content=req.content,
                url=req.url,
                title=req.title,
                domain=req.domain,
                sync_to_notion=req.sync_to_notion,
            )
            for sse_string in _run_async_generator_sync(async_gen):
                yield sse_string

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
            },
        )

    except Exception as e:
        return jsonify(error_response(
            code='INTERNAL_ERROR',
            message=str(e),
        )), 500


@translate_bp.route('/api/translate/agent', methods=['POST'])
@require_access_key
def translate_agent():
    """
    Agent mode endpoint - autonomous translation with MCP tools.

    This endpoint allows Claude to autonomously:
    - Fetch content from URLs using web_fetch tool
    - Translate the content
    - Optionally publish to Notion using notion_publish tool

    Request body:
    {
        "prompt": "Translate the article at https://... and publish to Notion",
        "domain": "tech" | "business" | "academic"
    }

    Response: text/event-stream with same events as /api/translate/stream
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(error_response(
                code='INVALID_REQUEST',
                message='Request body must be JSON',
            )), 400

        prompt = data.get('prompt', '')
        domain = data.get('domain', 'tech')

        if not prompt:
            return jsonify(error_response(
                code='INVALID_REQUEST',
                message='prompt is required',
            )), 400

        # Get translation service
        service = get_translation_service()

        def generate():
            """Generator for SSE stream using agent mode."""
            async_gen = service.translate_with_agent_sse(
                prompt=prompt,
                domain=domain,
            )
            for sse_string in _run_async_generator_sync(async_gen):
                yield sse_string

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
            },
        )

    except Exception as e:
        return jsonify(error_response(
            code='INTERNAL_ERROR',
            message=str(e),
        )), 500


@translate_bp.route('/api/translate/progress/<task_id>', methods=['GET'])
@require_access_key
def get_translation_progress(task_id: str):
    """
    Get translation task progress.

    Path params:
    - task_id: The translation task ID

    Response:
    {
        "success": true,
        "data": {
            "status": "in_progress" | "completed" | "failed",
            "progress": 75,
            "partial_result": "translated content so far..."
        }
    }
    """
    try:
        service = get_translation_service()
        progress = service.get_task_progress(task_id)

        if progress.get('status') == 'not_found':
            return jsonify(error_response(
                code='NOT_FOUND',
                message='Task not found or expired',
            )), 404

        response = ResumeResponse(
            success=True,
            data=ResumeResponseData(
                task_id=task_id,
                status=progress.get('status', 'unknown'),
                progress=progress.get('progress', 0),
                partial_result=progress.get('partial_result'),
                original_content=progress.get('original_content'),
                error=progress.get('error'),
            ),
        )

        return jsonify(response.to_dict()), 200

    except Exception as e:
        return jsonify(error_response(
            code='INTERNAL_ERROR',
            message=str(e),
        )), 500
