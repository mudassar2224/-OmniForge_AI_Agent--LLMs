"""AgentState and artifact definitions for OmniForge AI graphs.

Defines the core LangGraph state schema (AgentState) and Pydantic models for sources,
events, code artifacts, media artifacts, and general artifacts.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, Field


class Source(BaseModel):
    """Represents an external information source (web page, paper, doc, code)."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    url: str = ""
    domain: str = ""
    source_provider: str = ""  # gemini, ddgs, arxiv, etc.
    source_type: str = ""  # web, academic, code, documentation
    query: str = ""
    snippet: str = ""
    content: str = ""
    publication_date: str | None = None
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now().isoformat()  # noqa: DTZ005
    )
    relevance_score: float = 0.0
    citation_id: int = 0
    status: str = "found"  # found, fetched, verified, failed


class ActivityEvent(BaseModel):
    """Represents a discrete activity or lifecycle event during graph execution."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat()  # noqa: DTZ005
    )
    event_type: str = ""  # planning, searching, fetching, analyzing, coding, generating, etc.
    agent: str = ""
    tool: str = ""
    status: str = "running"  # running, complete, failed, skipped
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodeArtifact(BaseModel):
    """Represents a generated or modified code artifact and its execution status."""

    filename: str = ""
    code: str = ""
    language: str = "python"
    output: str = ""
    error: str = ""
    tests_passed: bool | None = None


class MediaArtifact(BaseModel):
    """Represents a generated or processed media file (image, video, audio)."""

    type: str = ""  # image, video
    path: str = ""
    prompt: str = ""
    model: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class Artifact(BaseModel):
    """Represents a persistent artifact produced during workflow execution."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str = ""  # code, report, image, video, data, text
    filename: str = ""
    path: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat()  # noqa: DTZ005
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


def add_to_list(current: list[Any] | None, new: list[Any] | Any | str) -> list[Any]:
    """Reducer helper to append new items to an existing list in AgentState.

    Handles initial None values and supports appending either a list of items
    or a single item, returning a new consolidated list.
    Passing the exact string 'CLEAR' will reset the list to empty.
    """
    if new == "CLEAR":
        return []
        
    base = list(current) if current is not None else []
    if new is None:
        return base
    if isinstance(new, list):
        return base + list(new)
    return base + [new]


class AgentState(TypedDict):
    """Main execution state schema for OmniForge LangGraph workflows."""

    messages: Annotated[list[BaseMessage], add_messages]
    plan: str
    route: str  # GENERAL, RESEARCH, CODING, etc.
    sources: Annotated[list[dict[str, Any]], add_to_list]
    activity_events: Annotated[list[dict[str, Any]], add_to_list]
    code_artifacts: Annotated[list[dict[str, Any]], add_to_list]
    media_artifacts: Annotated[list[dict], add_to_list]
    artifacts: Annotated[list[dict[str, Any]], add_to_list]
    uploaded_files: list[dict[str, Any]]
    active_skills: list[str]
    needs_approval: bool
    error: str
    _loop_count: int
    final_answer: str
    conversation_summary: str
    relevant_memories: list[str]


def create_initial_state(
    messages: list[BaseMessage] | None = None,
    plan: str = "",
    route: str = "GENERAL",
    sources: list[dict[str, Any]] | None = None,
    activity_events: list[dict[str, Any]] | None = None,
    code_artifacts: list[dict[str, Any]] | None = None,
    media_artifacts: list[dict[str, Any]] | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    uploaded_files: list[dict[str, Any]] | None = None,
    active_skills: list[str] | None = None,
    needs_approval: bool = False,
    error: str = "",
    _loop_count: int = 0,
    final_answer: str = "",
    conversation_summary: str = "",
    relevant_memories: list[str] | None = None,
) -> AgentState:
    """Create a fully-initialized AgentState dictionary with default values."""
    return {
        "messages": list(messages) if messages is not None else [],
        "plan": plan,
        "route": route,
        "sources": list(sources) if sources is not None else [],
        "activity_events": list(activity_events) if activity_events is not None else [],
        "code_artifacts": list(code_artifacts) if code_artifacts is not None else [],
        "media_artifacts": list(media_artifacts) if media_artifacts is not None else [],
        "artifacts": list(artifacts) if artifacts is not None else [],
        "uploaded_files": list(uploaded_files) if uploaded_files is not None else [],
        "active_skills": list(active_skills) if active_skills is not None else [],
        "needs_approval": needs_approval,
        "error": error,
        "_loop_count": _loop_count,
        "final_answer": final_answer,
        "conversation_summary": conversation_summary,
        "relevant_memories": list(relevant_memories) if relevant_memories is not None else [],
    }
