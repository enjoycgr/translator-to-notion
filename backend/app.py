"""
Flask application factory and main entry point.
"""

import atexit
import logging
import os
import threading
from pathlib import Path
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from config.settings import load_config, AppConfig

# Frontend build directory
FRONTEND_DIST = Path(__file__).parent.parent / 'frontend' / 'dist'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Flag to track if background services are initialized
_services_initialized = False
_services_lock = threading.Lock()


def init_background_services(app: Flask) -> None:
    """
    Initialize background task services.

    Should only be called once, typically when the app starts.
    """
    global _services_initialized

    with _services_lock:
        if _services_initialized:
            return

        logger.info("Initializing background services...")

        try:
            # Initialize task persistence service (loads/recovers tasks)
            from backend.services.task_persistence import get_persistence_service
            persistence = get_persistence_service()

            # Load and recover tasks from disk
            recovered = persistence.load_and_recover()
            logger.info(f"Recovered {recovered} tasks from disk")

            # Initialize background task manager (starts worker thread)
            from backend.services.task_manager import get_task_manager
            manager = get_task_manager()

            # Initial cleanup of expired tasks
            cleaned = persistence.cleanup_expired_tasks()
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} expired tasks")

            _services_initialized = True
            logger.info("Background services initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize background services: {e}", exc_info=True)
            raise


def shutdown_background_services() -> None:
    """Shutdown background services gracefully."""
    global _services_initialized

    with _services_lock:
        if not _services_initialized:
            return

        logger.info("Shutting down background services...")

        try:
            # Shutdown task manager
            from backend.services.task_manager import shutdown_task_manager
            shutdown_task_manager()

            # Shutdown persistence service (final snapshot)
            from backend.services.task_persistence import shutdown_persistence_service
            shutdown_persistence_service()

            _services_initialized = False
            logger.info("Background services shutdown complete")

        except Exception as e:
            logger.error(f"Error during background services shutdown: {e}")


def create_app(config: AppConfig = None) -> Flask:
    """
    Create and configure the Flask application.

    Args:
        config: Optional AppConfig. If not provided, loads from config file.

    Returns:
        Configured Flask application.
    """
    # Load config if not provided
    if config is None:
        config = load_config()

    # Create Flask app
    app = Flask(__name__)

    # Store config in app
    app.config['APP_CONFIG'] = config

    # Configure CORS - 从环境变量读取允许的来源，默认仅允许本地开发
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
    origins_list = [origin.strip() for origin in allowed_origins.split(",") if origin.strip()]

    CORS(app, resources={
        r"/api/*": {
            "origins": origins_list,
            "methods": ["GET", "POST", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "X-Access-Key"],
        }
    })

    # Register blueprints
    from backend.routes.health import health_bp
    from backend.routes.translate import translate_bp
    from backend.routes.notion import notion_bp
    from backend.routes.tasks import tasks_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(translate_bp)
    app.register_blueprint(notion_bp)
    app.register_blueprint(tasks_bp)

    # Initialize background services (only in non-reloader process)
    # Check for WERKZEUG_RUN_MAIN to avoid double initialization in debug mode
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        init_background_services(app)

        # Register shutdown handler
        atexit.register(shutdown_background_services)

    # Register error handlers
    register_error_handlers(app)

    # Serve frontend static files (production)
    if FRONTEND_DIST.exists():
        @app.route('/')
        def serve_frontend():
            return send_from_directory(FRONTEND_DIST, 'index.html')

        @app.route('/<path:path>')
        def serve_static(path):
            # Try to serve static file, fallback to index.html for SPA routing
            file_path = FRONTEND_DIST / path
            if file_path.exists() and file_path.is_file():
                return send_from_directory(FRONTEND_DIST, path)
            return send_from_directory(FRONTEND_DIST, 'index.html')

    return app


def register_error_handlers(app: Flask) -> None:
    """Register global error handlers."""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': {
                'code': 'BAD_REQUEST',
                'message': str(error.description) if hasattr(error, 'description') else 'Bad request',
            }
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'success': False,
            'error': {
                'code': 'UNAUTHORIZED',
                'message': str(error.description) if hasattr(error, 'description') else 'Unauthorized',
            }
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'success': False,
            'error': {
                'code': 'FORBIDDEN',
                'message': str(error.description) if hasattr(error, 'description') else 'Forbidden',
            }
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': {
                'code': 'NOT_FOUND',
                'message': str(error.description) if hasattr(error, 'description') else 'Not found',
            }
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An internal error occurred',
            }
        }), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        # Log the error
        app.logger.error(f"Unhandled exception: {error}", exc_info=True)

        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': str(error) if app.debug else 'An internal error occurred',
            }
        }), 500


def run_app(
    host: str = None,
    port: int = None,
    debug: bool = None,
) -> None:
    """
    Run the Flask application.

    Args:
        host: Host to bind to. Defaults to config value.
        port: Port to bind to. Defaults to config value.
        debug: Debug mode. Defaults to config value.
    """
    config = load_config()

    # Use provided values or defaults from config
    host = host or config.server.host
    port = port or config.server.port
    debug = debug if debug is not None else config.server.debug

    app = create_app(config)
    app.run(host=host, port=port, debug=debug)


# For direct execution
if __name__ == '__main__':
    run_app()
