"""Memory retrieval module for OmniForge AI.

Extracts relevant long-term memories using keyword matching and formats them
as structured context for injection into LLM prompts.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

STOP_WORDS: frozenset[str] = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
    "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then",
    "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what",
    "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's",
    "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd",
    "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves",
})


def _extract_keywords(query: str) -> list[str]:
    """Extract significant keywords from a user query string.

    Args:
        query: Raw query text.

    Returns:
        List of lowercase keyword strings with stop words removed.
    """
    tokens = re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", query.lower())
    return [token for token in tokens if token not in STOP_WORDS]


def _format_single_memory(mem: dict[str, Any]) -> str:
    """Format a memory record dictionary into a concise string."""
    category = mem.get("category", "memory")
    key = mem.get("key", "").strip()
    value = mem.get("value", "").strip()

    if key and value:
        return f"[{category}] {key}: {value}"
    elif value:
        return f"[{category}] {value}"
    return f"[{category}] {key}"


async def retrieve_relevant_memories(
    query: str,
    memory_store: Any,
    limit: int = 5,
) -> list[str]:
    """Retrieve relevant memories matching the query using keyword search.

    Searches using the entire query string and significant decomposed keywords,
    deduplicating and ranking results by keyword match frequency.

    Args:
        query: Query or context string to find related memories for.
        memory_store: An initialized MemoryStore instance or compatible retriever.
        limit: Maximum number of formatted memory strings to return. Defaults to 5.

    Returns:
        List of formatted memory description strings.
    """
    if not query or not query.strip():
        return []

    cleaned_query = query.strip()
    keywords = _extract_keywords(cleaned_query)

    seen_ids: set[str] = set()
    scored_memories: list[tuple[int, dict[str, Any]]] = []

    try:
        # 1. Search with direct query first
        direct_results = await memory_store.retrieve(query=cleaned_query, limit=limit)
        for mem in direct_results:
            mem_id = mem.get("id") or f"{mem.get('category')}_{mem.get('key')}"
            if mem_id not in seen_ids:
                seen_ids.add(mem_id)
                scored_memories.append((10, mem))

        # 2. Decompose and search individual keywords if needed
        for word in keywords:
            if len(scored_memories) >= limit * 2:
                break
            kw_results = await memory_store.retrieve(query=word, limit=limit)
            for mem in kw_results:
                mem_id = mem.get("id") or f"{mem.get('category')}_{mem.get('key')}"
                key_text = str(mem.get("key", "")).lower()
                val_text = str(mem.get("value", "")).lower()
                # Compute simple keyword overlap score
                score = sum(1 for kw in keywords if kw in key_text or kw in val_text)
                if mem_id not in seen_ids:
                    seen_ids.add(mem_id)
                    scored_memories.append((score, mem))

        # Sort by relevance score descending, then updated_at descending
        scored_memories.sort(
            key=lambda x: (x[0], x[1].get("updated_at", "")),
            reverse=True,
        )

        top_memories = [mem for _, mem in scored_memories[:limit]]
        formatted = [_format_single_memory(m) for m in top_memories]
        logger.debug(
            "Retrieved %d relevant memories for query '%s'",
            len(formatted),
            cleaned_query,
        )
        return formatted

    except Exception as exc:
        logger.error("Error retrieving relevant memories: %s", exc, exc_info=True)
        return []


def format_memories_for_context(memories: list[str]) -> str:
    """Format a list of memory strings into a structured Markdown section for prompt context.

    Args:
        memories: List of memory description strings.

    Returns:
        Markdown-formatted string with ## Relevant Memories header,
        or an empty string if no valid memories are provided.
    """
    valid_items = [m.strip() for m in memories if m and m.strip()]
    if not valid_items:
        return ""

    bullet_points = "\n".join(f"- {item}" for item in valid_items)
    return f"## Relevant Memories\n{bullet_points}"
