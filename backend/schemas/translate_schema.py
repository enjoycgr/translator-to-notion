"""
Data schemas for translation API.

Defines request/response models with validation.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Literal, List
from enum import Enum


class Domain(str, Enum):
    """Translation domain enum."""
    TECH = "tech"
    BUSINESS = "business"
    ACADEMIC = "academic"


class TaskStatus(str, Enum):
    """Translation task status enum."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TranslateRequest:
    """
    Translation request schema.

    Either content or url must be provided, but not both.
    """
    content: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    domain: str = "tech"
    sync_to_notion: bool = False

    def validate(self) -> List[str]:
        """
        Validate the request.

        Returns:
            List of validation error messages. Empty if valid.
        """
        errors = []

        # Check that either content or url is provided
        if not self.content and not self.url:
            errors.append("Either 'content' or 'url' must be provided")

        # Check that not both are provided
        if self.content and self.url:
            errors.append("Only one of 'content' or 'url' can be provided")

        # Validate domain
        valid_domains = ["tech", "business", "academic"]
        if self.domain not in valid_domains:
            errors.append(f"Invalid domain. Must be one of: {', '.join(valid_domains)}")

        # Validate URL format if provided
        if self.url:
            if not self.url.startswith(('http://', 'https://')):
                errors.append("URL must start with http:// or https://")

        return errors

    @classmethod
    def from_dict(cls, data: dict) -> 'TranslateRequest':
        """Create from dictionary."""
        return cls(
            content=data.get('content'),
            url=data.get('url'),
            title=data.get('title'),
            domain=data.get('domain', 'tech'),
            sync_to_notion=data.get('sync_to_notion', False),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class TranslateResponseData:
    """Data portion of translation response."""
    task_id: str
    original_content: str
    translated_content: str
    title: Optional[str] = None
    source_url: Optional[str] = None
    domain: Optional[str] = None
    notion_page_url: Optional[str] = None
    cost_usd: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TranslateResponse:
    """Full translation response schema."""
    success: bool
    data: Optional[TranslateResponseData] = None
    error: Optional[dict] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {'success': self.success}
        if self.data:
            result['data'] = self.data.to_dict()
        if self.error:
            result['error'] = self.error
        return result


@dataclass
class NotionSyncRequest:
    """Notion sync request schema."""
    task_id: str
    title: Optional[str] = None

    def validate(self) -> List[str]:
        """Validate the request."""
        errors = []
        if not self.task_id:
            errors.append("'task_id' is required")
        return errors

    @classmethod
    def from_dict(cls, data: dict) -> 'NotionSyncRequest':
        """Create from dictionary."""
        return cls(
            task_id=data.get('task_id', ''),
            title=data.get('title'),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class NotionSyncResponseData:
    """Data portion of Notion sync response."""
    notion_page_url: str
    page_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class NotionSyncResponse:
    """Full Notion sync response schema."""
    success: bool
    data: Optional[NotionSyncResponseData] = None
    error: Optional[dict] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {'success': self.success}
        if self.data:
            result['data'] = self.data.to_dict()
        if self.error:
            result['error'] = self.error
        return result


@dataclass
class ResumeResponseData:
    """Data portion of resume response."""
    task_id: str
    status: str
    progress: int  # 0-100
    partial_result: Optional[str] = None
    original_content: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ResumeResponse:
    """Full resume response schema."""
    success: bool
    data: Optional[ResumeResponseData] = None
    error: Optional[dict] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {'success': self.success}
        if self.data:
            result['data'] = self.data.to_dict()
        if self.error:
            result['error'] = self.error
        return result


@dataclass
class ErrorResponse:
    """Error response schema."""
    success: bool = False
    error: dict = field(default_factory=dict)

    @classmethod
    def create(cls, code: str, message: str, details: Optional[dict] = None) -> 'ErrorResponse':
        """
        Create an error response.

        Args:
            code: Error code (e.g., 'VALIDATION_ERROR', 'NOT_FOUND').
            message: Human-readable error message.
            details: Optional additional details.
        """
        error = {'code': code, 'message': message}
        if details:
            error['details'] = details
        return cls(success=False, error=error)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {'success': self.success, 'error': self.error}


@dataclass
class HealthResponse:
    """Health check response schema."""
    status: str = "healthy"
    version: str = "1.0.0"
    services: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


# Helper functions for creating responses
def success_response(data: dict) -> dict:
    """Create a success response."""
    return {'success': True, 'data': data}


def error_response(code: str, message: str, details: Optional[dict] = None) -> dict:
    """Create an error response."""
    return ErrorResponse.create(code, message, details).to_dict()


def validation_error(errors: List[str]) -> dict:
    """Create a validation error response."""
    return error_response(
        code='VALIDATION_ERROR',
        message='Request validation failed',
        details={'errors': errors},
    )
