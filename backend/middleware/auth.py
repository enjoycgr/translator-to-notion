"""
Access Key authentication middleware for Flask.

Provides a decorator for protecting API endpoints with Access Key validation.
"""

from functools import wraps
from typing import Callable, List, Optional

from flask import request, current_app, abort, g


def require_access_key(f: Callable) -> Callable:
    """
    Decorator to require Access Key authentication for an endpoint.

    Checks for X-Access-Key header and validates against configured keys.

    Usage:
        @app.route('/api/protected')
        @require_access_key
        def protected_endpoint():
            return {'message': 'Authenticated!'}
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get Access Key from header
        access_key = request.headers.get('X-Access-Key')

        if not access_key:
            abort(401, description="Missing Access Key. Include X-Access-Key header.")

        # Get valid keys from app config
        config = current_app.config.get('APP_CONFIG')
        if config is None:
            # Fallback to environment variable or config
            valid_keys = current_app.config.get('ACCESS_KEYS', [])
        else:
            valid_keys = config.auth.access_keys

        if not valid_keys:
            # No keys configured - reject all requests
            abort(500, description="No Access Keys configured on server")

        if access_key not in valid_keys:
            abort(401, description="Invalid Access Key")

        # Store the validated key in g for potential audit logging
        g.access_key = access_key

        return f(*args, **kwargs)

    return decorated


def get_access_keys_from_config() -> List[str]:
    """
    Get configured Access Keys from Flask app config.

    Returns:
        List of valid Access Keys.
    """
    config = current_app.config.get('APP_CONFIG')
    if config is not None:
        return config.auth.access_keys
    return current_app.config.get('ACCESS_KEYS', [])


def validate_access_key(key: str) -> bool:
    """
    Validate an Access Key against configured keys.

    Args:
        key: The Access Key to validate.

    Returns:
        True if the key is valid, False otherwise.
    """
    valid_keys = get_access_keys_from_config()
    return key in valid_keys


class AccessKeyAuth:
    """
    Class-based Access Key authentication.

    Can be used for more complex authentication scenarios or
    when you need to access the Flask app context differently.
    """

    def __init__(self, app=None, header_name: str = 'X-Access-Key'):
        """
        Initialize Access Key authentication.

        Args:
            app: Optional Flask app to initialize with.
            header_name: Header name to look for the Access Key.
        """
        self.header_name = header_name
        self._app = app

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """
        Initialize with Flask app.

        Args:
            app: Flask application instance.
        """
        self._app = app

        # Register error handlers
        @app.errorhandler(401)
        def handle_unauthorized(error):
            return {
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': str(error.description),
                }
            }, 401

    def get_access_key(self) -> Optional[str]:
        """
        Get the Access Key from the current request.

        Returns:
            The Access Key or None if not present.
        """
        return request.headers.get(self.header_name)

    def authenticate(self) -> bool:
        """
        Authenticate the current request.

        Returns:
            True if authentication succeeds.

        Raises:
            Abort 401 if authentication fails.
        """
        key = self.get_access_key()

        if not key:
            abort(401, description=f"Missing {self.header_name} header")

        if not validate_access_key(key):
            abort(401, description="Invalid Access Key")

        g.access_key = key
        return True

    def required(self, f: Callable) -> Callable:
        """
        Decorator to require authentication.

        Same as the standalone require_access_key function.
        """
        @wraps(f)
        def decorated(*args, **kwargs):
            self.authenticate()
            return f(*args, **kwargs)
        return decorated
