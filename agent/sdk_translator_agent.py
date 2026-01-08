"""
SDK-based Translator Agent using Claude Agent SDK.

Core translation agent that orchestrates:
- Content fetching (via MCP tools)
- Translation with domain-specific prompts
- Streaming responses via SDK
- Notion publishing (via MCP tools)
"""

import os
from dataclasses import dataclass
from typing import AsyncGenerator, Optional

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
)

from config.settings import AppConfig, get_config
from agent.tools.tools_server import (
    get_translation_tools_server,
    get_all_tool_names,
)
from agent.tools.web_fetcher import WebFetcher
from agent.prompts.translation_prompts import (
    get_system_prompt,
    get_translation_prompt,
    get_chunk_translation_prompt,
)
from agent.prompts.domain_prompts import get_domain_prompt


@dataclass
class SDKStreamChunk:
    """A chunk of streamed translation output from SDK."""

    text: str
    is_complete: bool = False
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class SDKTranslatorAgent:
    """
    Translation agent using Claude Agent SDK.

    Features:
    - MCP server integration for tools
    - Streaming output via SDK
    - Domain-specific translation
    - Flexible tool usage (with/without tools)
    """

    def __init__(self, config: Optional[AppConfig] = None):
        """
        Initialize the SDK translator agent.

        Args:
            config: Application configuration. Uses default if not provided.
        """
        self.config = config or get_config()

        # Validate API key
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        self.model = self.config.agent.model

        # Initialize tools server
        self._tools_server = get_translation_tools_server()

        # Keep WebFetcher for direct use (faster than MCP for simple fetches)
        self.web_fetcher = WebFetcher()

    def _create_agent_options(
        self,
        system_prompt: str,
        include_tools: bool = True,
    ) -> ClaudeAgentOptions:
        """
        Create ClaudeAgentOptions for a translation request.

        Args:
            system_prompt: System prompt for the agent.
            include_tools: Whether to include MCP tools.

        Returns:
            ClaudeAgentOptions configured for translation.
        """
        options_dict = {
            "model": self.model,
            "system_prompt": system_prompt,
            "permission_mode": "acceptEdits",
        }

        if include_tools:
            options_dict["mcp_servers"] = {
                "translation-tools": self._tools_server
            }
            options_dict["allowed_tools"] = get_all_tool_names()

        return ClaudeAgentOptions(**options_dict)

    async def translate_stream(
        self,
        content: Optional[str] = None,
        url: Optional[str] = None,
        title: Optional[str] = None,
        domain: str = "tech",
        task_id: str = "",
    ) -> AsyncGenerator[SDKStreamChunk, None]:
        """
        Translate content with streaming output using Claude Agent SDK.

        Args:
            content: Text content to translate.
            url: URL to fetch and translate.
            title: Optional title.
            domain: Translation domain.
            task_id: Optional task ID for tracking.

        Yields:
            SDKStreamChunk objects with translation progress.
        """
        # Validate input
        if not content and not url:
            yield SDKStreamChunk(
                text="Error: Either content or url must be provided",
                is_complete=True,
            )
            return

        if content and url:
            yield SDKStreamChunk(
                text="Error: Only one of content or url can be provided",
                is_complete=True,
            )
            return

        # Fetch content from URL if needed
        source_url = url
        if url:
            fetch_result = self.web_fetcher.fetch(url)
            if not fetch_result.success:
                yield SDKStreamChunk(
                    text=f"Error fetching URL: {fetch_result.error}",
                    is_complete=True,
                )
                return
            content = fetch_result.content
            if not title:
                title = fetch_result.title

        # Build prompts
        domain_modifier = get_domain_prompt(domain)
        system_prompt = get_system_prompt(domain_modifier)
        user_prompt = get_translation_prompt(
            content=content,
            title=title,
            source_url=source_url,
            domain=domain,
        )

        # Create agent options (no tools needed for direct translation)
        options = self._create_agent_options(
            system_prompt=system_prompt,
            include_tools=False,
        )

        try:
            # Use query() for streaming translation
            accumulated_text = ""
            total_cost = 0.0
            input_tokens = 0
            output_tokens = 0

            async for message in query(prompt=user_prompt, options=options):
                if isinstance(message, AssistantMessage):
                    # Process content blocks
                    for block in message.content:
                        if hasattr(block, "text"):
                            text = block.text
                            # Yield incremental text
                            if text and text != accumulated_text:
                                new_text = text[len(accumulated_text):]
                                accumulated_text = text
                                if new_text:
                                    yield SDKStreamChunk(
                                        text=new_text,
                                        is_complete=False,
                                    )

                elif isinstance(message, ResultMessage):
                    # Final result with usage stats
                    if message.total_cost_usd:
                        total_cost = message.total_cost_usd
                    if message.usage:
                        input_tokens = message.usage.get("input_tokens", 0)
                        output_tokens = message.usage.get("output_tokens", 0)

            # Yield completion
            yield SDKStreamChunk(
                text="",
                is_complete=True,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=total_cost,
            )

        except Exception as e:
            yield SDKStreamChunk(
                text=f"\n\nError: {str(e)}",
                is_complete=True,
            )

    async def translate_chunk_stream(
        self,
        content: str,
        chunk_number: int,
        total_chunks: int,
        context: str = "",
        domain: str = "tech",
    ) -> AsyncGenerator[SDKStreamChunk, None]:
        """
        Translate a single chunk with streaming output.

        Args:
            content: Chunk content to translate.
            chunk_number: Current chunk number (1-based).
            total_chunks: Total number of chunks.
            context: Previous translation context.
            domain: Translation domain.

        Yields:
            SDKStreamChunk objects with translation progress.
        """
        domain_modifier = get_domain_prompt(domain)
        system_prompt = get_system_prompt(domain_modifier)
        user_prompt = get_chunk_translation_prompt(
            content=content,
            chunk_number=chunk_number,
            total_chunks=total_chunks,
            context=context,
        )

        options = self._create_agent_options(
            system_prompt=system_prompt,
            include_tools=False,
        )

        try:
            accumulated_text = ""
            total_cost = 0.0
            input_tokens = 0
            output_tokens = 0

            async for message in query(prompt=user_prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if hasattr(block, "text"):
                            text = block.text
                            if text and text != accumulated_text:
                                new_text = text[len(accumulated_text):]
                                accumulated_text = text
                                if new_text:
                                    yield SDKStreamChunk(
                                        text=new_text,
                                        is_complete=False,
                                    )

                elif isinstance(message, ResultMessage):
                    if message.total_cost_usd:
                        total_cost = message.total_cost_usd
                    if message.usage:
                        input_tokens = message.usage.get("input_tokens", 0)
                        output_tokens = message.usage.get("output_tokens", 0)

            yield SDKStreamChunk(
                text="",
                is_complete=True,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=total_cost,
            )

        except Exception as e:
            yield SDKStreamChunk(
                text=f"\n\nError: {str(e)}",
                is_complete=True,
            )

    async def translate_with_tools(
        self,
        prompt: str,
        domain: str = "tech",
    ) -> AsyncGenerator[SDKStreamChunk, None]:
        """
        Translate using agent with MCP tools (for URL fetching and Notion publishing).

        This method allows Claude to autonomously:
        - Fetch content from URLs using web_fetch tool
        - Translate the content
        - Publish to Notion using notion_publish tool

        Args:
            prompt: User prompt describing the translation task.
            domain: Translation domain.

        Yields:
            SDKStreamChunk objects with progress and results.
        """
        domain_modifier = get_domain_prompt(domain)
        system_prompt = get_system_prompt(domain_modifier)

        # Include tools for autonomous operation
        options = self._create_agent_options(
            system_prompt=system_prompt,
            include_tools=True,
        )

        try:
            accumulated_text = ""
            total_cost = 0.0
            input_tokens = 0
            output_tokens = 0

            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if hasattr(block, "text"):
                            text = block.text
                            if text and text != accumulated_text:
                                new_text = text[len(accumulated_text):]
                                accumulated_text = text
                                if new_text:
                                    yield SDKStreamChunk(
                                        text=new_text,
                                        is_complete=False,
                                    )
                        elif hasattr(block, "name"):
                            # Tool use block - yield tool name for UI feedback
                            yield SDKStreamChunk(
                                text=f"\n[Using tool: {block.name}]\n",
                                is_complete=False,
                            )

                elif isinstance(message, ResultMessage):
                    if message.total_cost_usd:
                        total_cost = message.total_cost_usd
                    if message.usage:
                        input_tokens = message.usage.get("input_tokens", 0)
                        output_tokens = message.usage.get("output_tokens", 0)

            yield SDKStreamChunk(
                text="",
                is_complete=True,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=total_cost,
            )

        except Exception as e:
            yield SDKStreamChunk(
                text=f"\n\nError: {str(e)}",
                is_complete=True,
            )


# Convenience function for direct usage
def create_sdk_translator(config: Optional[AppConfig] = None) -> SDKTranslatorAgent:
    """
    Create an SDK translator agent instance.

    Args:
        config: Optional configuration. Uses default if not provided.

    Returns:
        SDKTranslatorAgent instance.
    """
    return SDKTranslatorAgent(config)
