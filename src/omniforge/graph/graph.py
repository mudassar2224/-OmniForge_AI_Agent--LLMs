"""
Main LangGraph for OmniForge AI.

Builds the stateful agent graph with supervisor routing,
agent nodes, and memory integration.
"""

import logging
from typing import Any

from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig

from omniforge.graph.state import AgentState
from omniforge.graph.supervisor import supervisor_node
from omniforge.graph.router import route_to_agent, should_synthesize
from omniforge.agents import (
    general_node,
    research_node,
    coding_node,
    file_node,
    media_node,
    synthesis_node,
)

logger = logging.getLogger(__name__)


def build_graph(checkpointer=None) -> Any:
    """
    Build the main OmniForge LangGraph.

    Graph structure:
        START
          │
          ▼
        memory_load_node  (retrieve relevant memories)
          │
          ▼
        supervisor_node   (analyze, plan, route)
          │
          ├── general_node
          ├── research_node
          ├── coding_node
          ├── file_node
          └── media_node
                │
                ▼
          [conditional: synthesis or end]
                │
                ▼
          memory_save_node  (persist important memories)
                │
                ▼
              END
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("memory_load_node", memory_load_node)
    graph.add_node("supervisor_node", supervisor_node)
    graph.add_node("general_node", general_node)
    graph.add_node("research_node", research_node)
    graph.add_node("coding_node", coding_node)
    graph.add_node("file_node", file_node)
    graph.add_node("media_node", media_node)
    graph.add_node("synthesis_node", synthesis_node)
    graph.add_node("memory_save_node", memory_save_node)

    # Edges
    graph.add_edge(START, "memory_load_node")
    graph.add_edge("memory_load_node", "supervisor_node")

    # Conditional routing from supervisor to agents or synthesis
    graph.add_conditional_edges(
        "supervisor_node",
        route_to_agent,
        {
            "general_node": "general_node",
            "research_node": "research_node",
            "coding_node": "coding_node",
            "file_node": "file_node",
            "media_node": "media_node",
            "synthesis_node": "synthesis_node",
        },
    )

    # After agent execution, loop back to supervisor to check if task is done!
    graph.add_edge("general_node", "supervisor_node")
    graph.add_edge("research_node", "supervisor_node")
    graph.add_edge("coding_node", "supervisor_node")
    graph.add_edge("file_node", "supervisor_node")
    graph.add_edge("media_node", "supervisor_node")

    # Synthesis -> memory save -> end
    graph.add_edge("synthesis_node", "memory_save_node")
    graph.add_edge("memory_save_node", END)

    # Compile
    compile_kwargs = {}
    if checkpointer:
        compile_kwargs["checkpointer"] = checkpointer

    compiled = graph.compile(**compile_kwargs)
    logger.info("OmniForge graph compiled successfully")
    return compiled


async def memory_load_node(state: dict, config: RunnableConfig | None = None) -> dict:
    """Load relevant memories before processing the request."""
    from omniforge.config.settings import get_settings
    from omniforge.graph.events import EventEmitter

    settings = get_settings()
    emitter = EventEmitter()
    events = []

    if not settings.MEMORY_ENABLED:
        return {"relevant_memories": [], "activity_events": events}

    messages = state.get("messages", [])
    if not messages:
        return {"relevant_memories": [], "activity_events": events}

    last_msg = messages[-1].content if hasattr(messages[-1], "content") else ""

    try:
        from omniforge.memory.long_term import MemoryStore
        from omniforge.memory.retrieval import retrieve_relevant_memories

        store = MemoryStore()
        await store.initialize()
        memories = await retrieve_relevant_memories(last_msg, store, limit=5)

        if memories:
            events.append(emitter.emit_memory(
                f"Retrieved {len(memories)} relevant memories"
            ))

        return {"relevant_memories": memories, "activity_events": events}
    except Exception as e:
        logger.warning(f"Memory load failed: {e}")
        return {"relevant_memories": [], "activity_events": events}


async def memory_save_node(state: dict, config: RunnableConfig | None = None) -> dict:
    """Save important information to long-term memory after processing."""
    from omniforge.config.settings import get_settings
    from omniforge.graph.events import EventEmitter

    settings = get_settings()
    emitter = EventEmitter()
    events = []

    if not settings.MEMORY_ENABLED:
        return {"activity_events": events}

    messages = state.get("messages", [])
    if len(messages) < 2:
        return {"activity_events": events}

    try:
        from omniforge.config.models import ModelRegistry
        from omniforge.memory.long_term import MemoryStore
        from omniforge.memory.extraction import extract_memories

        model_registry = ModelRegistry()
        llm = model_registry.get_llm()
        store = MemoryStore()
        await store.initialize()

        # Extract memories from recent messages
        recent = messages[-6:]  # Last 3 exchanges max
        extracted = await extract_memories(recent, llm)

        for mem in extracted:
            await store.store(
                category=mem.get("category", "semantic"),
                key=mem.get("key", ""),
                value=mem.get("value", ""),
            )

        if extracted:
            events.append(emitter.emit_memory(
                f"Saved {len(extracted)} new memories", status="complete"
            ))

        return {"activity_events": events}
    except Exception as e:
        logger.warning(f"Memory save failed: {e}")
        return {"activity_events": events}
