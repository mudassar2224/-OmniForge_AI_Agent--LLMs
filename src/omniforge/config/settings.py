"""Application configuration settings for OmniForge AI.

Loads settings from environment variables and .env file using pydantic-settings.
Provides validated, typed configurations across models, external tools,
storage paths, and operational limits.
"""

from functools import lru_cache
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file immediately
load_dotenv()

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """OmniForge AI configuration settings.

    Centralized configuration management loaded from environment variables
    and .env files with fallback defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # -------------------------------------------------------------------------
    # Core LLM API Keys (Groq, OpenRouter, HF)
    # -------------------------------------------------------------------------
    groq_api_key_1: str = Field(
        default_factory=lambda: os.getenv("GROQ_API_KEY_1", ""),
        description="Groq API Key 1",
    )
    groq_api_key_2: str = Field(
        default_factory=lambda: os.getenv("GROQ_API_KEY_2", ""),
        description="Groq API Key 2",
    )
    groq_api_key_3: str = Field(
        default_factory=lambda: os.getenv("GROQ_API_KEY_3", ""),
        description="Groq API Key 3",
    )
    openrouter_api_key_1: str = Field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY_1", ""),
        description="OpenRouter API Key 1",
    )
    openrouter_api_key_2: str = Field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY_2", ""),
        description="OpenRouter API Key 2",
    )
    openrouter_api_key_3: str = Field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY_3", ""),
        description="OpenRouter API Key 3",
    )
    hf_token: str = Field(
        default_factory=lambda: os.getenv("HF_TOKEN", ""),
        description="Hugging Face Token for Media",
    )

    # -------------------------------------------------------------------------
    # Tracing & Observability (LangSmith)
    # -------------------------------------------------------------------------
    langsmith_api_key: str | None = Field(
        default=None,
        description="LangSmith API key for tracing and observability",
    )
    langsmith_tracing: bool = Field(
        default=True,
        description="Whether to enable LangSmith tracing",
    )
    langsmith_project: str = Field(
        default="OmniForge-AI",
        description="LangSmith project name for trace categorization",
    )

    # -------------------------------------------------------------------------
    # External Tools & Search Providers (Optional)
    # -------------------------------------------------------------------------
    brave_search_api_key: str | None = Field(
        default=None,
        description="Brave Search API key for web search capabilities",
    )
    jina_api_key: str | None = Field(
        default=None,
        description="Jina AI API key for markdown extraction and deep search",
    )
    github_token: str | None = Field(
        default=None,
        description="GitHub personal access token for repo operations",
    )
    searxng_url: str | None = Field(
        default=None,
        description="SearXNG self-hosted metasearch instance URL",
    )
    semantic_scholar_api_key: str | None = Field(
        default=None,
        description="Semantic Scholar API key for academic literature search",
    )

    # -------------------------------------------------------------------------
    # Storage Paths
    # -------------------------------------------------------------------------
    workspace_path: str = Field(
        default="workspace",
        description="Path to local code workspace directory",
    )
    artifacts_path: str = Field(
        default="artifacts",
        description="Path to generated artifacts directory",
    )
    data_path: str = Field(
        default="data",
        description="Path to persistent agent data directory",
    )

    # -------------------------------------------------------------------------
    # Operational Limits & Execution Controls
    # -------------------------------------------------------------------------
    max_search_results: int = Field(
        default=10,
        description="Maximum search results returned per query",
    )
    max_fetch_pages: int = Field(
        default=5,
        description="Maximum web pages to fetch and parse in single operation",
    )
    max_code_repair_attempts: int = Field(
        default=2,
        description="Maximum retry attempts for automated code repair",
    )
    memory_enabled: bool = Field(
        default=True,
        description="Whether persistent agent memory is enabled",
    )
    media_enabled: bool = Field(
        default=True,
        description="Whether media generation (image/video) is enabled",
    )

    # -------------------------------------------------------------------------
    # Model Names (with defaults from environment variables or safe fallbacks)
    # -------------------------------------------------------------------------
    default_model: str = Field(
        default_factory=lambda: os.getenv("DEFAULT_MODEL", "qwen/qwen3.8-27b"),
        description="Default primary LLM model identifier",
    )
    reasoning_model: str = Field(
        default_factory=lambda: os.getenv("REASONING_MODEL", "openai/gpt-oss-120b"),
        description="Reasoning model identifier for complex problem solving",
    )
    light_model: str = Field(
        default_factory=lambda: os.getenv("LIGHT_MODEL", "openai/gpt-oss-20b"),
        description="Light model for memory and simple routing",
    )
    image_model: str = Field(
        default_factory=lambda: os.getenv("IMAGE_MODEL", "black-forest-labs/FLUX.1-dev"),
        description="Default image generation model identifier",
    )
    image_pro_model: str = Field(
        default_factory=lambda: os.getenv("IMAGE_PRO_MODEL", "black-forest-labs/FLUX.1-dev"),
        description="High-fidelity image generation model identifier",
    )
    video_model: str = Field(
        default_factory=lambda: os.getenv("VIDEO_MODEL", "Wan-AI/Wan2.2-T2V-A14B"),
        description="Video generation model identifier",
    )

    # -------------------------------------------------------------------------
    # Uppercase Property Aliases (for backward and case-insensitive compatibility)
    # -------------------------------------------------------------------------
    @property
    def GROQ_API_KEYS(self) -> list[str]:
        keys = [self.groq_api_key_1, self.groq_api_key_2, self.groq_api_key_3]
        return [k.strip() for k in keys if k and k.strip()]

    @property
    def OPENROUTER_API_KEYS(self) -> list[str]:
        keys = [self.openrouter_api_key_1, self.openrouter_api_key_2, self.openrouter_api_key_3]
        return [k.strip() for k in keys if k and k.strip()]

    @property
    def HF_TOKEN(self) -> str:
        return self.hf_token

    @property
    def LANGSMITH_API_KEY(self) -> str | None:
        """Alias for langsmith_api_key."""
        return self.langsmith_api_key

    @property
    def LANGSMITH_TRACING(self) -> bool:
        """Alias for langsmith_tracing."""
        return self.langsmith_tracing

    @property
    def LANGSMITH_PROJECT(self) -> str:
        """Alias for langsmith_project."""
        return self.langsmith_project

    @property
    def BRAVE_SEARCH_API_KEY(self) -> str | None:
        """Alias for brave_search_api_key."""
        return self.brave_search_api_key

    @property
    def JINA_API_KEY(self) -> str | None:
        """Alias for jina_api_key."""
        return self.jina_api_key

    @property
    def GITHUB_TOKEN(self) -> str | None:
        """Alias for github_token."""
        return self.github_token

    @property
    def SEARXNG_URL(self) -> str | None:
        """Alias for searxng_url."""
        return self.searxng_url

    @property
    def SEMANTIC_SCHOLAR_API_KEY(self) -> str | None:
        """Alias for semantic_scholar_api_key."""
        return self.semantic_scholar_api_key

    @property
    def WORKSPACE_PATH(self) -> str:
        """Alias for workspace_path."""
        return self.workspace_path

    @property
    def ARTIFACTS_PATH(self) -> str:
        """Alias for artifacts_path."""
        return self.artifacts_path

    @property
    def DATA_PATH(self) -> str:
        """Alias for data_path."""
        return self.data_path

    @property
    def MAX_SEARCH_RESULTS(self) -> int:
        """Alias for max_search_results."""
        return self.max_search_results

    @property
    def MAX_FETCH_PAGES(self) -> int:
        """Alias for max_fetch_pages."""
        return self.max_fetch_pages

    @property
    def MAX_CODE_REPAIR_ATTEMPTS(self) -> int:
        """Alias for max_code_repair_attempts."""
        return self.max_code_repair_attempts

    @property
    def MEMORY_ENABLED(self) -> bool:
        """Alias for memory_enabled."""
        return self.memory_enabled

    @property
    def MEDIA_ENABLED(self) -> bool:
        """Alias for media_enabled."""
        return self.media_enabled

    @property
    def DEFAULT_MODEL(self) -> str:
        """Alias for default_model."""
        return self.default_model

    @property
    def REASONING_MODEL(self) -> str:
        """Alias for reasoning_model."""
        return self.reasoning_model

    @property
    def IMAGE_MODEL(self) -> str:
        """Alias for image_model."""
        return self.image_model

    @property
    def IMAGE_PRO_MODEL(self) -> str:
        """Alias for image_pro_model."""
        return self.image_pro_model

    @property
    def VIDEO_MODEL(self) -> str:
        """Alias for video_model."""
        return self.video_model

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    @property
    def is_llm_configured(self) -> bool:
        """Check whether any LLM API keys are configured."""
        return bool(self.GROQ_API_KEYS or self.OPENROUTER_API_KEYS)

    def get_workspace_dir(self) -> Path:
        """Return Path object for workspace directory, ensuring it exists."""
        p = Path(self.workspace_path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_artifacts_dir(self) -> Path:
        """Return Path object for artifacts directory, ensuring it exists."""
        p = Path(self.artifacts_path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_data_dir(self) -> Path:
        """Return Path object for data directory, ensuring it exists."""
        p = Path(self.data_path)
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached singleton Settings instance.

    Loads and parses environment configuration on first call and caches the
    result for fast subsequent lookups.

    Returns:
        Settings: Validated configuration settings instance.
    """
    settings = Settings()
    if not settings.is_llm_configured:
        logger.warning(
            "Neither GROQ_API_KEYS nor OPENROUTER_API_KEYS are set. "
            "LLM calls will fail."
        )
    return settings


def clear_settings_cache() -> None:
    """Clear the cached settings instance.

    Useful in tests when environment variables are dynamically changed.
    """
    get_settings.cache_clear()
