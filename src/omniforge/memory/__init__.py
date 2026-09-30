"""Memory system for OmniForge AI.

Provides thread-level checkpointing, SQLite-backed long-term memory,
conversation summarization, context-aware memory retrieval, and LLM-driven memory extraction.
"""

from omniforge.memory.checkpoint import close_checkpointer, get_checkpointer
from omniforge.memory.extraction import ExtractedMemoryItem, extract_memories
from omniforge.memory.long_term import MemoryRecord, MemoryStore
from omniforge.memory.retrieval import (
    format_memories_for_context,
    retrieve_relevant_memories,
)
from omniforge.memory.summarizer import should_summarize, summarize_conversation

__all__ = [
    "get_checkpointer",
    "close_checkpointer",
    "MemoryStore",
    "MemoryRecord",
    "summarize_conversation",
    "should_summarize",
    "retrieve_relevant_memories",
    "format_memories_for_context",
    "extract_memories",
    "ExtractedMemoryItem",
]
