"""Middleware module."""

from .auth import require_access_key

__all__ = ["require_access_key"]
