"""
Flask application factory and main entry point.
"""

import os
from pathlib import Path
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from config.settings import load_config, AppConfig

# Frontend build directory
FRONTEND_DIST = Path(__file__).parent.parent / 'frontend' / 'dist'


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
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "X-Access-Key"],
        }
    })

    # Register blueprints
    from backend.routes.health import health_bp
    from backend.routes.translate import translate_bp
    from backend.routes.notion import notion_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(translate_bp)
    app.register_blueprint(notion_bp)

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
