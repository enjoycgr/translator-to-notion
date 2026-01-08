"""API routes module."""

from .health import health_bp
from .translate import translate_bp
from .notion import notion_bp

__all__ = ["health_bp", "translate_bp", "notion_bp"]
