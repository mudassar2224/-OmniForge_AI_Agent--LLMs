"""Unit tests for omniforge.graph module: state, events, and policies."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph

from omniforge.graph import (
    MAX_CODE_REPAIR_ATTEMPTS,
    MAX_FETCH_PAGES,
    MAX_IDENTICAL_SEARCH,
    MAX_PLANNING_DEPTH,
    MAX_SEARCH_ESCALATION,
    MAX_SOURCES_PER_SEARCH,
    MAX_SOURCES_TOTAL,
    MAX_TOOL_RETRIES,
    MIN_SOURCES_FOR_RESEARCH,
    PREFERRED_SOURCES,
    ActivityEvent,
    AgentState,
    Artifact,
    CodeArtifact,
    EventEmitter,
    GraphPolicies,
    MediaArtifact,
    Source,
    add_to_list,
    create_initial_state,
)


def test_source_model() -> None:
    """Test Source Pydantic model initialization and defaults."""
    source = Source(
        title="Python 3.12 Release Notes",
        url="https://docs.python.org/3/whatsnew/3.12.html",
        domain="docs.python.org",
        source_provider="ddgs",
        source_type="documentation",
    )
    assert len(source.id) == 8
    assert source.title == "Python 3.12 Release Notes"
    assert source.domain == "docs.python.org"
    assert source.status == "found"
    assert source.retrieved_at is not None
    data = source.model_dump()
    assert isinstance(data, dict)
    assert data["source_provider"] == "ddgs"


def test_activity_event_model() -> None:
    """Test ActivityEvent model initialization and dump."""
    event = ActivityEvent(
        event_type="planning",
        agent="lead_orchestrator",
        tool="planner",
        status="running",
        message="Generating execution plan",
        metadata={"step": 1},
    )
    assert len(event.event_id) == 8
    assert event.event_type == "planning"
    assert event.status == "running"
    assert event.metadata["step"] == 1
    dump = event.model_dump()
    assert isinstance(dump, dict)
    assert dump["message"] == "Generating execution plan"


def test_artifacts_models() -> None:
    """Test CodeArtifact, MediaArtifact, and Artifact models."""
    code = CodeArtifact(
        filename="solution.py",
        code="def solve(): return 42",
        language="python",
        output="42",
        tests_passed=True,
    )
    assert code.filename == "solution.py"
    assert code.tests_passed is True

    media = MediaArtifact(
        type="image",
        path="/tmp/diagram.png",
        prompt="system architecture diagram",
        model="imagen-3.0",
    )
    assert media.type == "image"
    assert media.model == "imagen-3.0"

    artifact = Artifact(
        type="report",
        filename="summary.md",
        path="/tmp/summary.md",
        metadata={"author": "omniforge"},
    )
    assert len(artifact.id) == 8
    assert artifact.type == "report"


def test_add_to_list_reducer() -> None:
    """Test add_to_list reducer handles None, lists, and single elements."""
    assert add_to_list(None, None) == []
    assert add_to_list([1, 2], None) == [1, 2]
    assert add_to_list(None, [3, 4]) == [3, 4]
    assert add_to_list([1, 2], [3, 4]) == [1, 2, 3, 4]
    assert add_to_list([1, 2], 5) == [1, 2, 5]


def test_create_initial_state() -> None:
    """Test create_initial_state helper function."""
    state = create_initial_state(
        messages=[HumanMessage(content="Hello OmniForge")],
        route="RESEARCH",
    )
    assert len(state["messages"]) == 1
    assert state["route"] == "RESEARCH"
    assert state["sources"] == []
    assert state["activity_events"] == []
    assert state["code_artifacts"] == []
    assert state["media_artifacts"] == []
    assert state["artifacts"] == []
    assert state["needs_approval"] is False


def test_agent_state_langgraph_integration() -> None:
    """Test that AgentState functions correctly within a LangGraph StateGraph."""
    workflow = StateGraph(AgentState)

    def node_planner(state: AgentState) -> dict[str, Any]:
        emitter = EventEmitter()
        evt = emitter.emit_planning("Planning completed", agent="planner", status="complete")
        return {
            "plan": "Step 1: Research, Step 2: Code",
            "activity_events": [evt],
            "messages": [AIMessage(content="Plan generated")],
        }

    def node_research(state: AgentState) -> dict[str, Any]:
        src = Source(title="Docs", url="https://python.org").model_dump()
        return {
            "sources": [src],
            "final_answer": "Research complete",
        }

    workflow.add_node("planner", node_planner)
    workflow.add_node("research", node_research)
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "research")
    workflow.add_edge("research", END)

    app = workflow.compile()
    initial_state = create_initial_state(messages=[HumanMessage(content="Build app")])
    result = app.invoke(initial_state)

    assert result["plan"] == "Step 1: Research, Step 2: Code"
    assert len(result["activity_events"]) == 1
    assert result["activity_events"][0]["event_type"] == "planning"
    assert len(result["sources"]) == 1
    assert result["sources"][0]["url"] == "https://python.org"
    assert result["final_answer"] == "Research complete"
    assert len(result["messages"]) == 2


def test_event_emitter_all_methods() -> None:
    """Test all 10 emit methods and event query methods on EventEmitter."""
    shared_list: list[dict[str, Any]] = []
    emitter = EventEmitter(events=shared_list)

    listener_events: list[dict[str, Any]] = []
    emitter.add_listener(lambda e: listener_events.append(e))

    e_plan = emitter.emit_planning("Devising strategy", agent="planner")
    e_search = emitter.emit_searching("Searching web", tool="ddgs")
    e_fetch = emitter.emit_fetching("Fetching page content", tool="trafilatura")
    e_analyze = emitter.emit_analyzing("Synthesizing citations", agent="analyst")
    e_code = emitter.emit_coding("Generating script", agent="coder")
    e_gen = emitter.emit_generating("Creating diagram", tool="imagen")
    e_mem = emitter.emit_memory("Loading context", tool="sqlite")
    e_comp = emitter.emit_complete("Task accomplished")
    e_err = emitter.emit_error("Connection timeout", tool="fetcher")
    e_fall = emitter.emit_fallback("Switching to backup provider", tool="arxiv")

    assert e_plan["event_type"] == "planning"
    assert e_search["event_type"] == "searching"
    assert e_fetch["event_type"] == "fetching"
    assert e_analyze["event_type"] == "analyzing"
    assert e_code["event_type"] == "coding"
    assert e_gen["event_type"] == "generating"
    assert e_mem["event_type"] == "memory"
    assert e_comp["event_type"] == "complete"
    assert e_comp["status"] == "complete"
    assert e_err["event_type"] == "error"
    assert e_err["status"] == "failed"
    assert e_fall["event_type"] == "fallback"

    all_events = emitter.get_events()
    assert len(all_events) == 10
    assert len(emitter.get_all_events()) == 10
    assert len(shared_list) == 10
    assert len(listener_events) == 10

    # Test get_new_events
    new_evts = emitter.get_new_events(clear=True)
    assert len(new_evts) == 10
    assert len(emitter.get_new_events()) == 0

    emitter.clear()
    assert len(emitter.get_events()) == 0


def test_policies_constants() -> None:
    """Verify execution policy constants and GraphPolicies Pydantic model."""
    assert MAX_PLANNING_DEPTH == 3
    assert MAX_SEARCH_ESCALATION == 3
    assert MAX_CODE_REPAIR_ATTEMPTS == 2
    assert MAX_IDENTICAL_SEARCH == 1
    assert MAX_TOOL_RETRIES == 2
    assert MAX_SOURCES_PER_SEARCH == 10
    assert MAX_FETCH_PAGES == 5
    assert MIN_SOURCES_FOR_RESEARCH == 2
    assert PREFERRED_SOURCES == 5
    assert MAX_SOURCES_TOTAL == 15

    policies = GraphPolicies()
    assert policies.max_planning_depth == 3
    assert policies.max_search_escalation == 3
    assert policies.max_sources_total == 15
