"""Conversation summarization module for OmniForge AI.

Compresses extended conversation history into concise summaries when
token/message thresholds are exceeded, maintaining ongoing context.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence

from langchain_core.messages import BaseMessage
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

SUMMARY_PROMPT_TEMPLATE = (
    "Summarize the key points, decisions, and context from this conversation. "
    "Focus on objectives, key facts, user preferences, technical decisions, "
    "progress made, and open tasks:\n\n"
    "{conversation}\n\n"
    "Summary:"
)


def _format_message_content(content: Any) -> str:
    """Extract plain text string from various message content representations."""
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


def _format_conversation(messages: Sequence[Any]) -> str:
    """Format a sequence of messages into a readable conversation transcript."""
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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def _invoke_summary_llm(llm: Any, prompt: str) -> Any:
    """Invoke the LLM with retry mechanism."""
    return await llm.ainvoke(prompt)


def should_summarize(messages: list[Any], max_messages: int = 20) -> bool:
    """Determine whether the message list exceeds the summarization threshold.

    Args:
        messages: List of conversation messages.
        max_messages: Maximum message threshold before summarization is recommended.
            Defaults to 20.

    Returns:
        True if len(messages) > max_messages, False otherwise.
    """
    return len(messages) > max_messages


async def summarize_conversation(messages: list[Any], llm: Any) -> str:
    """Generate a high-level summary of the conversation if length exceeds 10 messages.

    Args:
        messages: List of BaseMessage objects or message dictionaries.
        llm: A LangChain-compatible LLM instance providing an async `ainvoke` method.

    Returns:
        Summary string, or an empty string if len(messages) <= 10 or if summarization fails.
    """
    if len(messages) <= 10:
        return ""

    conversation_text = _format_conversation(messages)
    prompt = SUMMARY_PROMPT_TEMPLATE.format(conversation=conversation_text)

    try:
        response = await _invoke_summary_llm(llm, prompt)
        if hasattr(response, "content"):
            summary = _format_message_content(response.content)
        else:
            summary = str(response)

        cleaned_summary = summary.strip()
        logger.info(
            "Successfully generated summary for %d messages (%d characters)",
            len(messages),
            len(cleaned_summary),
        )
        return cleaned_summary
    except Exception as exc:
        logger.error("Failed to summarize conversation with LLM: %s", exc, exc_info=True)
        return ""
