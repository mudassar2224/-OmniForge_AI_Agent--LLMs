"""Memory extraction module for OmniForge AI.

Analyzes conversation messages to identify user preferences, project decisions,
factual context, and workflow conventions, extracting them into structured memories.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Sequence

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field, field_validator
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = (
    "From these messages, identify any user preferences, project decisions, "
    "important facts, or workflow preferences that should be remembered. "
    "Return as JSON array with keys: category (semantic/episodic/procedural), "
    "key (short label), value (the information).\n\n"
    "Messages:\n{messages_text}\n\n"
    "Respond ONLY with a valid JSON array of objects, with no surrounding commentary or markdown code fences.\n"
    "If there is nothing worth remembering, return []."
)


class ExtractedMemoryItem(BaseModel):
    """Pydantic model representing an extracted memory candidate."""

    category: str = Field(
        default="semantic",
        description="Category: 'semantic', 'episodic', or 'procedural'",
    )
    key: str = Field(..., description="Short identifying label for the memory")
    value: str = Field(..., description="The factual or instructional content")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Normalize category to valid categories; default to 'semantic'."""
        cleaned = str(v).strip().lower()
        if cleaned in {"semantic", "episodic", "procedural"}:
            return cleaned
        return "semantic"

    @field_validator("key", "value")
    @classmethod
    def non_empty_str(cls, v: str) -> str:
        """Ensure string fields are stripped and non-empty."""
        cleaned = str(v).strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned


def _format_message_content(content: Any) -> str:
    """Extract plain text string from message content."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(str(part["text"]))
            elif hasattr(part, "text"):
                parts.append(str(part.text))
        return " ".join(parts)
    return str(content)


def _format_messages_transcript(messages: Sequence[Any]) -> str:
    """Format messages into a conversation transcript for the prompt."""
    lines: list[str] = []
    for msg in messages:
        if isinstance(msg, BaseMessage):
            role = msg.type.capitalize()
            text = _format_message_content(msg.content)
            lines.append(f"{role}: {text}")
        elif isinstance(msg, dict):
            role = str(msg.get("role", "User")).capitalize()
            text = _format_message_content(msg.get("content", ""))
            lines.append(f"{role}: {text}")
        else:
            lines.append(str(msg))
    return "\n".join(lines)


def _clean_json_response(raw_text: str) -> str:
    """Strip markdown formatting and isolate the JSON array."""
    text = raw_text.strip()
    # Strip markdown code block wrappers if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    # If text is not already a valid array start, find the outer brackets
    if not (text.startswith("[") and text.endswith("]")):
        match = re.search(r"\[[\s\S]*\]", text)
        if match:
            text = match.group(0)

    return text


@retry(
    stop=stop_after_attempt(1),
    reraise=True,
)
async def _invoke_extraction_llm(llm: Any, prompt: str) -> Any:
    """Invoke the LLM with retry mechanism."""
    return await llm.ainvoke(prompt)


async def extract_memories(messages: list[Any], llm: Any) -> list[dict[str, str]]:
    """Extract valuable context, preferences, and decisions from conversation messages.

    Args:
        messages: List of conversation messages (BaseMessage or dictionaries).
        llm: A LangChain-compatible LLM instance providing an async `ainvoke` method.

    Returns:
        List of dictionaries with 'category', 'key', and 'value' keys.
        Returns an empty list if no messages exist or on JSON parsing failure.
    """
    if not messages:
        return []

    # Trim messages to the last 4 to prevent 413 Payload Too Large on strict limits
    recent_messages = messages[-4:] if len(messages) > 4 else messages
    messages_text = _format_messages_transcript(recent_messages)
    if not messages_text.strip():
        return []

    prompt = EXTRACTION_PROMPT.format(messages_text=messages_text)

    try:
        response = await _invoke_extraction_llm(llm, prompt)
        if hasattr(response, "content"):
            raw_output = _format_message_content(response.content)
        else:
            raw_output = str(response)

        cleaned_json = _clean_json_response(raw_output)
        if not cleaned_json:
            logger.debug("Extraction returned empty or unparseable output")
            return []

        parsed = json.loads(cleaned_json)
        if not isinstance(parsed, list):
            logger.warning("LLM extraction output was not a JSON list: %r", type(parsed))
            return []

        extracted_items: list[dict[str, str]] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            try:
                validated = ExtractedMemoryItem(**item)
                extracted_items.append(validated.model_dump())
            except Exception as item_err:
                logger.debug("Skipping invalid memory item %r: %s", item, item_err)

        logger.info(
            "Extracted %d memories from %d messages",
            len(extracted_items),
            len(messages),
        )
        return extracted_items

    except json.JSONDecodeError as json_err:
        logger.warning(
            "JSON parsing error when extracting memories: %s (raw output: %.100s...)",
            json_err,
            locals().get("raw_output", ""),
        )
        return []
    except Exception as exc:
        logger.error("Unexpected error during memory extraction: %s", exc, exc_info=True)
        return []
