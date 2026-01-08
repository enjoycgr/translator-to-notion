"""
Health check API endpoint.
"""

from flask import Blueprint, jsonify

from config.settings import get_config


health_bp = Blueprint('health', __name__)


@health_bp.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.

    Returns server status and version information.
    No authentication required.
    """
    config = get_config()

    response = {
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "translation": "available",
            "notion": "configured" if config.notion.api_key else "not_configured",
        },
        "config": {
            "model": config.agent.model,
            "max_chunk_tokens": config.translation.chunking.max_chunk_tokens,
            "cache_ttl_minutes": config.cache.ttl_minutes,
        }
    }

    return jsonify(response), 200


@health_bp.route('/api/health/ready', methods=['GET'])
def readiness_check():
    """
    Readiness check endpoint.

    Checks if the service is ready to handle requests.
    """
    import os

    errors = []

    # Check for required environment variables
    if not os.environ.get('ANTHROPIC_API_KEY'):
        errors.append("ANTHROPIC_API_KEY not set")

    config = get_config()
    if not config.auth.access_keys:
        errors.append("No access keys configured")

    if errors:
        return jsonify({
            "status": "not_ready",
            "errors": errors,
        }), 503

    return jsonify({
        "status": "ready",
    }), 200
