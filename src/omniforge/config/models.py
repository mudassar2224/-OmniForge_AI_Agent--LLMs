"""Model registry and routing configuration for OmniForge AI.

Implements a highly available, multi-provider API rotation and fallback architecture
using Groq and OpenRouter via LangChain's with_fallbacks() utility.
"""

import logging
from enum import StrEnum
from functools import lru_cache
from typing import Any

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import Runnable

from omniforge.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class TaskComplexity(StrEnum):
    """Task complexity levels for dynamic model routing."""
    LIGHT = "light"
    NORMAL = "normal"
    COMPLEX = "complex"
    HARD = "hard"


class ModelRegistry:
    """Central registry for managing AI models and routing with fallbacks."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings: Settings = settings or get_settings()
        
        # API keys are already lists
        self.groq_keys = self.settings.GROQ_API_KEYS
        self.or_keys = self.settings.OPENROUTER_API_KEYS
        
        # Warn if empty
        if not self.groq_keys:
            logger.warning("No Groq API keys found.")
        if not self.or_keys:
            logger.warning("No OpenRouter API keys found.")

    def _wrap_with_length_check(self, llm: Runnable) -> Runnable:
        return llm

    def _create_groq_llms(self, model_name: str, **kwargs) -> list[Runnable]:
        """Create a list of ChatGroq instances for each available key."""
        if not self.groq_keys:
            return []
            
        groq_kwargs = dict(kwargs)
        if "max_tokens" not in groq_kwargs or groq_kwargs["max_tokens"] is None:
            groq_kwargs["max_tokens"] = 800
        
        instances = []
        for key in self.groq_keys:
            llm = ChatGroq(
                api_key=key,
                model_name=model_name,
                max_retries=0,  # Fail fast to trigger fallback
                **groq_kwargs
            )
            instances.append(self._wrap_with_length_check(llm))
        return instances

    def _create_openrouter_llms(self, model_name: str, **kwargs) -> list[Runnable]:
        """Create a list of ChatOpenAI instances pointing to OpenRouter for each key."""
        if not self.or_keys:
            return []
        
        instances = []
        for key in self.or_keys:
            llm = ChatOpenAI(
                api_key=key,
                model_name=model_name,
                base_url="https://openrouter.ai/api/v1",
                max_retries=0,  # Fail fast to trigger fallback
                **kwargs
            )
            instances.append(self._wrap_with_length_check(llm))
        return instances

    def _create_gemini_llm(self, model_name: str, **kwargs) -> list[Runnable]:
        """Create a Gemini instance as the ultimate fallback."""
        gemini_key = __import__("os").environ.get("GEMINI_API_KEY")
        if not gemini_key:
            return []
        llm = ChatGoogleGenerativeAI(
            api_key=gemini_key,
            model=model_name,
            max_retries=0,
            **kwargs
        )
        return [self._wrap_with_length_check(llm)]

    def _build_fallback_chain(self, llm_list: list[Runnable]) -> Runnable:
        """Chain a list of LLMs using with_fallbacks."""
        if not llm_list:
            raise ValueError("No LLMs available to build fallback chain. Check API keys.")
        
        primary = llm_list[0]
        if len(llm_list) > 1:
            return primary.with_fallbacks(llm_list[1:])
        return primary

    def get_llm(self, temperature: float | None = None, max_tokens: int | None = None, **kwargs) -> Runnable:
        """Main agent / tool-use LLM."""
        llm_kwargs = {}
        if temperature is not None: llm_kwargs["temperature"] = temperature
        if max_tokens is not None: llm_kwargs["max_tokens"] = max_tokens
        llm_kwargs.update(kwargs)

        groq_llms = self._create_groq_llms("qwen/qwen3.8-27b", **llm_kwargs)
        or_llms = self._create_openrouter_llms("qwen/qwen3.8-27b:free", **llm_kwargs)
        or_llms2 = self._create_openrouter_llms("google/gemma-4-31b-it:free", **llm_kwargs)
        gemini_llm = self._create_gemini_llm("gemini-2.5-flash", **llm_kwargs)
        
        return self._build_fallback_chain(groq_llms + or_llms + or_llms2 + gemini_llm)

    def get_reasoning_llm(self, temperature: float | None = None, max_tokens: int | None = None, **kwargs) -> Runnable:
        """Hard reasoning / coding LLM."""
        llm_kwargs = {}
        if temperature is not None: llm_kwargs["temperature"] = temperature
        if max_tokens is not None: llm_kwargs["max_tokens"] = max_tokens
        llm_kwargs.update(kwargs)

        groq_llms = self._create_groq_llms("openai/gpt-oss-120b", **llm_kwargs)
        or_llms = self._create_openrouter_llms("nvidia/nemotron-3-super-120b-a12b:free", **llm_kwargs)
        gemini_llm = self._create_gemini_llm("gemini-2.5-pro", **llm_kwargs)
        emergency_llms = self._create_openrouter_llms("google/gemma-4-31b-it:free", **llm_kwargs)
        
        return self._build_fallback_chain(groq_llms + or_llms + gemini_llm + emergency_llms)

    def get_light_llm(self, temperature: float | None = None, max_tokens: int | None = None, **kwargs) -> Runnable:
        """Light tasks / memory summarization LLM."""
        llm_kwargs = {}
        if temperature is not None: llm_kwargs["temperature"] = temperature
        if max_tokens is not None: llm_kwargs["max_tokens"] = max_tokens
        llm_kwargs.update(kwargs)

        groq_llms = self._create_groq_llms("openai/gpt-oss-20b", **llm_kwargs)
        or_llms = self._create_openrouter_llms("google/gemma-4-31b-it:free", **llm_kwargs)
        gemini_llm = self._create_gemini_llm("gemini-2.5-flash", **llm_kwargs)
        
        return self._build_fallback_chain(groq_llms + or_llms + gemini_llm)

    def route_model(self, task_complexity: str | TaskComplexity) -> Runnable:
        """Route task to appropriate model chain based on complexity."""
        normalized = str(task_complexity).strip().lower()
        if normalized in (TaskComplexity.COMPLEX, TaskComplexity.HARD, "complex", "hard", "high"):
            return self.get_reasoning_llm()
        elif normalized in (TaskComplexity.LIGHT, "light"):
            return self.get_light_llm()
        return self.get_llm()


@lru_cache(maxsize=1)
def get_model_registry(settings: Settings | None = None) -> ModelRegistry:
    return ModelRegistry(settings=settings)
