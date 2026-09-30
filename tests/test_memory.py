"""Unit tests for the OmniForge memory system."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock
import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from omniforge.memory import (
    MemoryStore,
    close_checkpointer,
    extract_memories,
    format_memories_for_context,
    get_checkpointer,
    retrieve_relevant_memories,
    should_summarize,
    summarize_conversation,
)


@pytest.mark.asyncio
async def test_checkpointer(tmp_path):
    """Test AsyncSqliteSaver initialization and lifecycle."""
    db_file = str(tmp_path / "test_checkpoints.db")
    saver = await get_checkpointer(db_file)
    assert saver is not None

    # Singleton behavior
    saver_again = await get_checkpointer(db_file)
    assert saver_again is saver

    await close_checkpointer()


@pytest.mark.asyncio
async def test_long_term_memory_store(tmp_path):
    """Test full CRUD and category operations on MemoryStore."""
    db_file = str(tmp_path / "test_memories.db")
    store = MemoryStore(db_file)
    await store.initialize()

    # Store semantic memory
    id1 = await store.store(
        category="semantic",
        key="project_name",
        value="OmniForge AI",
        metadata={"created_by": "architect"},
    )
    assert isinstance(id1, str)
    assert len(id1) > 0

    # Store procedural memory
    id2 = await store.store(
        category="procedural",
        key="code_formatting",
        value="Use ruff and black for Python 3.12",
        metadata={"priority": "high"},
    )
    assert isinstance(id2, str)
    assert id2 != id1

    # Upsert test: updating existing key in same category
    id1_again = await store.store(
        category="semantic",
        key="project_name",
        value="OmniForge AI Suite v2",
        metadata={"created_by": "architect", "updated": True},
    )
    assert id1_again == id1

    # Verify updated value
    semantic_mems = await store.retrieve(category="semantic")
    assert len(semantic_mems) == 1
    assert semantic_mems[0]["value"] == "OmniForge AI Suite v2"
    assert semantic_mems[0]["metadata"]["updated"] is True

    # Retrieve by query
    query_results = await store.retrieve(query="ruff")
    assert len(query_results) == 1
    assert query_results[0]["key"] == "code_formatting"

    # List all
    all_mems = await store.list_all()
    assert len(all_mems) == 2

    # Delete specific memory
    deleted = await store.delete(id2)
    assert deleted is True
    all_after_delete = await store.list_all()
    assert len(all_after_delete) == 1

    # Clear category
    cleared = await store.clear_category("semantic")
    assert cleared == 1
    assert len(await store.list_all()) == 0

    # Clear all on empty
    assert await store.clear_all() == 0


def test_should_summarize():
    """Test summarization message threshold check."""
    msgs_10 = [HumanMessage(content=f"msg {i}") for i in range(10)]
    assert should_summarize(msgs_10, max_messages=20) is False

    msgs_25 = [HumanMessage(content=f"msg {i}") for i in range(25)]
    assert should_summarize(msgs_25, max_messages=20) is True


@pytest.mark.asyncio
async def test_summarize_conversation_threshold():
    """Messages <= 10 should return empty string without invoking LLM."""
    mock_llm = MagicMock()
    msgs_5 = [HumanMessage(content=f"msg {i}") for i in range(5)]
    summary = await summarize_conversation(msgs_5, mock_llm)
    assert summary == ""
    mock_llm.ainvoke.assert_not_called()


@pytest.mark.asyncio
async def test_summarize_conversation_success():
    """Messages > 10 should call LLM and return the summary content."""
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(
        return_value=AIMessage(content="User requested a full memory architecture.")
    )

    msgs_12 = [HumanMessage(content=f"Detail {i}") for i in range(12)]
    summary = await summarize_conversation(msgs_12, mock_llm)
    assert summary == "User requested a full memory architecture."
    mock_llm.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_retrieve_relevant_memories_and_formatting(tmp_path):
    """Test searching memories and converting them to prompt context."""
    db_file = str(tmp_path / "retrieval_test.db")
    store = MemoryStore(db_file)
    await store.initialize()

    await store.store("semantic", "tech_stack", "Python 3.12, LangGraph, and SQLite")
    await store.store("procedural", "testing", "Run pytest on all memory modules")

    # Empty query
    assert await retrieve_relevant_memories("", store) == []

    # Query matching keywords
    memories = await retrieve_relevant_memories("What tech stack are we using?", store)
    assert len(memories) >= 1
    assert any("Python 3.12" in m for m in memories)

    # Context formatting
    context_str = format_memories_for_context(memories)
    assert context_str.startswith("## Relevant Memories")
    assert "- [semantic]" in context_str

    # Empty formatting
    assert format_memories_for_context([]) == ""


@pytest.mark.asyncio
async def test_extract_memories_json_parsing():
    """Test extracting memories from LLM response in JSON format."""
    mock_llm = MagicMock()
    valid_json = json.dumps([
        {"category": "semantic", "key": "user_role", "value": "Project Lead"},
        {"category": "procedural", "key": "deploy_target", "value": "Local workstation"},
    ])
    mock_llm.ainvoke = AsyncMock(
        return_value=AIMessage(content=f"```json\n{valid_json}\n```")
    )

    msgs = [
        HumanMessage(content="I am the Project Lead, please deploy to local workstation."),
    ]
    extracted = await extract_memories(msgs, mock_llm)
    assert len(extracted) == 2
    assert extracted[0]["category"] == "semantic"
    assert extracted[0]["key"] == "user_role"
    assert extracted[1]["category"] == "procedural"


@pytest.mark.asyncio
async def test_extract_memories_invalid_json():
    """Malformed LLM output should fail gracefully and return empty list."""
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(
        return_value=AIMessage(content="Sorry, I cannot extract any memories today.")
    )

    msgs = [HumanMessage(content="Hello there!")]
    extracted = await extract_memories(msgs, mock_llm)
    assert extracted == []
