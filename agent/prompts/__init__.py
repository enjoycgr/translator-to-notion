"""Prompt templates module."""

from .translation_prompts import get_system_prompt, get_translation_prompt
from .domain_prompts import get_domain_prompt, DOMAIN_PROMPTS

__all__ = [
    "get_system_prompt",
    "get_translation_prompt",
    "get_domain_prompt",
    "DOMAIN_PROMPTS",
]
