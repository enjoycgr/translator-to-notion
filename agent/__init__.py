"""Claude Agent module for translation."""

from .sdk_translator_agent import (
    SDKTranslatorAgent,
    SDKStreamChunk,
    create_sdk_translator,
)

# Aliases for backward compatibility
TranslatorAgent = SDKTranslatorAgent
StreamChunk = SDKStreamChunk
create_translator = create_sdk_translator

__all__ = [
    "SDKTranslatorAgent",
    "SDKStreamChunk",
    "create_sdk_translator",
    # Aliases
    "TranslatorAgent",
    "StreamChunk",
    "create_translator",
]
