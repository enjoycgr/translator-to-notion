"""
Configuration loader for the Translation Agent System.

Supports:
- YAML configuration files
- Environment variable overrides
- Type-safe configuration classes using dataclasses
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from dotenv import load_dotenv


@dataclass
class DomainConfig:
    """Configuration for a translation domain."""

    name: str
    prompt_modifier: str


@dataclass
class ChunkingConfig:
    """Configuration for text chunking/splitting."""

    strategy: str = "semantic"
    max_chunk_tokens: int = 8000
    overlap_sentences: int = 2


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    retry_on: List[str] = field(default_factory=lambda: ["network_error", "rate_limit"])
    backoff_multiplier: float = 2.0
    initial_delay_ms: int = 1000


@dataclass
class TranslationConfig:
    """Configuration for translation settings."""

    source_language: str = "en"
    target_language: str = "zh-CN"
    domains: Dict[str, DomainConfig] = field(default_factory=dict)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)


@dataclass
class CacheConfig:
    """Configuration for caching (checkpoint/resume)."""

    type: str = "memory"
    ttl_minutes: int = 30
    max_entries: int = 100


@dataclass
class NotionMetadataConfig:
    """Configuration for Notion page metadata."""

    include_source_url: bool = True
    include_domain: bool = True
    include_translate_time: bool = False
    include_cost: bool = False


@dataclass
class NotionConfig:
    """Configuration for Notion integration."""

    api_key: str = ""
    parent_page_id: str = ""
    metadata: NotionMetadataConfig = field(default_factory=NotionMetadataConfig)


@dataclass
class AuthConfig:
    """Configuration for authentication."""

    access_keys: List[str] = field(default_factory=list)


@dataclass
class AgentConfig:
    """Configuration for the Claude Agent."""

    model: str = "claude-sonnet-4-20250514"
    max_turns: int = 10
    timeout: int = 300
    base_url: str = "https://api.anthropic.com"  # Anthropic API base URL
    use_sdk: bool = True  # SDK mode switch (True = use claude-agent-sdk)
    sdk_options: dict = field(default_factory=lambda: {
        "max_tokens": 8192,
        "temperature": 0.7,
        "permission_mode": "acceptEdits",
    })


@dataclass
class ServerConfig:
    """Configuration for the Flask server."""

    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False


@dataclass
class AppConfig:
    """Main application configuration."""

    translation: TranslationConfig = field(default_factory=TranslationConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    notion: NotionConfig = field(default_factory=NotionConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    server: ServerConfig = field(default_factory=ServerConfig)


def _get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable value."""
    return os.environ.get(key, default)


def _get_env_int(key: str, default: int) -> int:
    """Get environment variable as integer."""
    value = os.environ.get(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_env_bool(key: str, default: bool) -> bool:
    """Get environment variable as boolean."""
    value = os.environ.get(key)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


def _get_env_list(key: str, default: Optional[List[str]] = None) -> List[str]:
    """Get environment variable as list (comma-separated)."""
    value = os.environ.get(key)
    if value is None:
        return default or []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_domain_config(data: dict) -> DomainConfig:
    """Parse domain configuration from dict."""
    return DomainConfig(
        name=data.get("name", ""),
        prompt_modifier=data.get("prompt_modifier", ""),
    )


def _parse_domains(data: dict) -> Dict[str, DomainConfig]:
    """Parse all domain configurations."""
    domains = {}
    for key, value in data.items():
        if isinstance(value, dict):
            domains[key] = _parse_domain_config(value)
    return domains


def _parse_chunking_config(data: dict) -> ChunkingConfig:
    """Parse chunking configuration."""
    return ChunkingConfig(
        strategy=data.get("strategy", "semantic"),
        max_chunk_tokens=data.get("max_chunk_tokens", 8000),
        overlap_sentences=data.get("overlap_sentences", 2),
    )


def _parse_retry_config(data: dict) -> RetryConfig:
    """Parse retry configuration."""
    return RetryConfig(
        max_attempts=data.get("max_attempts", 3),
        retry_on=data.get("retry_on", ["network_error", "rate_limit"]),
        backoff_multiplier=data.get("backoff_multiplier", 2.0),
        initial_delay_ms=data.get("initial_delay_ms", 1000),
    )


def _parse_translation_config(data: dict) -> TranslationConfig:
    """Parse translation configuration."""
    return TranslationConfig(
        source_language=data.get("source_language", "en"),
        target_language=data.get("target_language", "zh-CN"),
        domains=_parse_domains(data.get("domains", {})),
        chunking=_parse_chunking_config(data.get("chunking", {})),
        retry=_parse_retry_config(data.get("retry", {})),
    )


def _parse_cache_config(data: dict) -> CacheConfig:
    """Parse cache configuration."""
    return CacheConfig(
        type=data.get("type", "memory"),
        ttl_minutes=_get_env_int("CACHE_TTL_MINUTES", data.get("ttl_minutes", 30)),
        max_entries=data.get("max_entries", 100),
    )


def _parse_notion_metadata_config(data: dict) -> NotionMetadataConfig:
    """Parse Notion metadata configuration."""
    return NotionMetadataConfig(
        include_source_url=data.get("include_source_url", True),
        include_domain=data.get("include_domain", True),
        include_translate_time=data.get("include_translate_time", False),
        include_cost=data.get("include_cost", False),
    )


def _parse_notion_config(data: dict) -> NotionConfig:
    """Parse Notion configuration with environment variable overrides."""
    return NotionConfig(
        api_key=_get_env("NOTION_API_KEY", data.get("api_key", "")),
        parent_page_id=_get_env("NOTION_PARENT_PAGE_ID", data.get("parent_page_id", "")),
        metadata=_parse_notion_metadata_config(data.get("metadata", {})),
    )


def _parse_auth_config(data: dict) -> AuthConfig:
    """Parse auth configuration with environment variable overrides."""
    # Environment variable takes precedence
    env_keys = _get_env_list("ACCESS_KEYS")
    if env_keys:
        return AuthConfig(access_keys=env_keys)
    return AuthConfig(access_keys=data.get("access_keys", []))


def _parse_agent_config(data: dict) -> AgentConfig:
    """Parse agent configuration with environment variable overrides."""
    return AgentConfig(
        model=_get_env("AGENT_MODEL", data.get("model", "claude-sonnet-4-20250514")),
        max_turns=data.get("max_turns", 10),
        timeout=_get_env_int("AGENT_TIMEOUT", data.get("timeout", 300)),
        base_url=_get_env("ANTHROPIC_BASE_URL", data.get("base_url", "https://api.anthropic.com")),
        use_sdk=_get_env_bool("USE_SDK", data.get("use_sdk", True)),
        sdk_options=data.get("sdk_options", {
            "max_tokens": 8192,
            "temperature": 0.7,
            "permission_mode": "acceptEdits",
        }),
    )


def _parse_server_config(data: dict) -> ServerConfig:
    """Parse server configuration with environment variable overrides."""
    return ServerConfig(
        host=_get_env("SERVER_HOST", data.get("host", "0.0.0.0")),
        port=_get_env_int("SERVER_PORT", data.get("port", 5000)),
        debug=_get_env_bool("DEBUG", data.get("debug", False)),
    )


def load_config(
    config_path: Optional[str] = None,
    env_file: Optional[str] = None,
) -> AppConfig:
    """
    Load application configuration from YAML file and environment variables.

    Args:
        config_path: Path to the YAML configuration file.
                    Defaults to config/config.yaml relative to project root.
        env_file: Path to .env file. Defaults to .env in project root.

    Returns:
        AppConfig: The loaded and validated configuration.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        yaml.YAMLError: If the config file has invalid YAML syntax.
    """
    # Determine project root
    project_root = Path(__file__).parent.parent

    # Load environment variables
    if env_file is None:
        env_file = str(project_root / ".env")
    if Path(env_file).exists():
        load_dotenv(env_file)

    # Determine config file path
    if config_path is None:
        config_path = str(project_root / "config" / "config.yaml")

    # Load YAML configuration
    config_data = {}
    if Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}
    else:
        # Config file not found, use defaults with environment variables
        pass

    # Parse configuration sections
    return AppConfig(
        translation=_parse_translation_config(config_data.get("translation", {})),
        cache=_parse_cache_config(config_data.get("cache", {})),
        notion=_parse_notion_config(config_data.get("notion", {})),
        auth=_parse_auth_config(config_data.get("auth", {})),
        agent=_parse_agent_config(config_data.get("agent", {})),
        server=_parse_server_config(config_data.get("server", {})),
    )


def validate_config(config: AppConfig) -> List[str]:
    """
    Validate the configuration and return a list of errors.

    Args:
        config: The configuration to validate.

    Returns:
        List of error messages. Empty list if configuration is valid.
    """
    errors = []

    # Check Anthropic API key (from environment)
    if not _get_env("ANTHROPIC_API_KEY"):
        errors.append("ANTHROPIC_API_KEY environment variable is required")

    # Check Notion configuration if needed
    if config.notion.api_key and not config.notion.parent_page_id:
        errors.append("Notion parent_page_id is required when api_key is set")

    # Check access keys
    if not config.auth.access_keys:
        errors.append("At least one access key is required in auth.access_keys")

    # Check translation domains
    if not config.translation.domains:
        errors.append("At least one translation domain must be configured")

    return errors


# Singleton config instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """
    Get the application configuration singleton.

    Loads configuration on first call and returns cached instance thereafter.

    Returns:
        AppConfig: The application configuration.
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> AppConfig:
    """
    Force reload the configuration.

    Returns:
        AppConfig: The newly loaded configuration.
    """
    global _config
    _config = load_config()
    return _config
