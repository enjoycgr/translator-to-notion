"""
Notion sync API endpoint.
"""

from flask import Blueprint, request, jsonify

from backend.middleware.auth import require_access_key
from backend.schemas.translate_schema import (
    NotionSyncRequest,
    NotionSyncResponse,
    NotionSyncResponseData,
    validation_error,
    error_response,
)
from backend.services.translation_service import get_translation_service


notion_bp = Blueprint('notion', __name__)


@notion_bp.route('/api/notion/sync', methods=['POST'])
@require_access_key
def sync_to_notion():
    """
    Sync a completed translation to Notion.

    Request body:
    {
        "task_id": "uuid",
        "title": "optional page title override"
    }

    Response:
    {
        "success": true,
        "data": {
            "notion_page_url": "https://notion.so/..."
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

        # Parse and validate request
        req = NotionSyncRequest.from_dict(data)
        errors = req.validate()

        if errors:
            return jsonify(validation_error(errors)), 400

        # Get translation service
        service = get_translation_service()

        # Publish to Notion
        result = service.publish_to_notion(
            task_id=req.task_id,
            title=req.title,
        )

        if not result.get('success'):
            error_msg = result.get('error', 'Notion sync failed')

            # Determine error code
            if 'not found' in error_msg.lower():
                return jsonify(error_response(
                    code='NOT_FOUND',
                    message=error_msg,
                )), 404
            elif 'not completed' in error_msg.lower():
                return jsonify(error_response(
                    code='TASK_NOT_COMPLETED',
                    message=error_msg,
                )), 400
            elif 'not configured' in error_msg.lower():
                return jsonify(error_response(
                    code='NOTION_NOT_CONFIGURED',
                    message=error_msg,
                )), 500
            else:
                return jsonify(error_response(
                    code='NOTION_SYNC_FAILED',
                    message=error_msg,
                )), 500

        response = NotionSyncResponse(
            success=True,
            data=NotionSyncResponseData(
                notion_page_url=result.get('notion_page_url', ''),
                page_id=result.get('page_id'),
            ),
        )

        return jsonify(response.to_dict()), 200

    except Exception as e:
        return jsonify(error_response(
            code='INTERNAL_ERROR',
            message=str(e),
        )), 500


@notion_bp.route('/api/notion/test', methods=['GET'])
@require_access_key
def test_notion_connection():
    """
    Test Notion API connection.

    Response:
    {
        "success": true,
        "message": "Notion connection successful"
    }
    """
    try:
        from config.settings import get_config

        config = get_config()

        if not config.notion.api_key:
            return jsonify(error_response(
                code='NOT_CONFIGURED',
                message='Notion API key not configured',
            )), 500

        if not config.notion.parent_page_id:
            return jsonify(error_response(
                code='NOT_CONFIGURED',
                message='Notion parent page ID not configured',
            )), 500

        # Test connection
        from agent.tools.notion_publisher import NotionPublisher
        publisher = NotionPublisher(
            api_key=config.notion.api_key,
            parent_page_id=config.notion.parent_page_id,
        )

        if publisher.test_connection():
            return jsonify({
                "success": True,
                "message": "Notion connection successful",
            }), 200
        else:
            return jsonify(error_response(
                code='CONNECTION_FAILED',
                message='Failed to connect to Notion',
            )), 500

    except Exception as e:
        return jsonify(error_response(
            code='INTERNAL_ERROR',
            message=str(e),
        )), 500
