"""Event emission and activity tracking for OmniForge AI graphs.

Provides the EventEmitter class used across graph nodes and agents to record
progress, status updates, tool actions, and errors in a standardized event stream.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from omniforge.graph.state import ActivityEvent

logger = logging.getLogger(__name__)

_GLOBAL_LISTENERS: list[Callable[[dict[str, Any]], Any]] = []

def register_global_listener(listener: Callable[[dict[str, Any]], Any]) -> None:
    if listener not in _GLOBAL_LISTENERS:
        _GLOBAL_LISTENERS.append(listener)

def clear_global_listeners() -> None:
    _GLOBAL_LISTENERS.clear()


class EventEmitter:
    """Emits and tracks activity events across graph nodes and execution steps.

    Events are validated through Pydantic's ActivityEvent model and stored
    as serializable dictionaries using ActivityEvent.model_dump().
    """

    def __init__(
        self,
        events: list[dict[str, Any]] | None = None,
        listeners: list[Callable[[dict[str, Any]], Any]] | None = None,
    ) -> None:
        """Initialize the EventEmitter.

        Args:
            events: Optional existing list to append events into (e.g., from AgentState).
                    If None, an internal list is created.
            listeners: Optional list of callback functions invoked when an event is emitted.
        """
        self._events: list[dict[str, Any]] = events if events is not None else []
        self._new_events: list[dict[str, Any]] = []
        self._listeners: list[Callable[[dict[str, Any]], Any]] = (
            list(listeners) if listeners is not None else []
        )

    def add_listener(self, listener: Callable[[dict[str, Any]], Any]) -> None:
        """Register a callback listener that receives each emitted event dict."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[dict[str, Any]], Any]) -> None:
        """Unregister an existing callback listener."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def emit(
        self,
        event_type: str,
        message: str,
        agent: str = "",
        tool: str = "",
        status: str = "running",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Emit a generic activity event and store it in the event list.

        Args:
            event_type: Category of the event (e.g., planning, searching, coding).
            message: Human-readable description of current activity or result.
            agent: Name of the agent emitting the event.
            tool: Name of the tool involved, if any.
            status: Execution status ('running', 'complete', 'failed', 'skipped').
            metadata: Additional structured context or payload data.

        Returns:
            The serialized event dictionary from ActivityEvent.model_dump().
        """
        event = ActivityEvent(
            event_type=event_type,
            agent=agent,
            tool=tool,
            status=status,
            message=message,
            metadata=metadata if metadata is not None else {},
        )
        event_dict = event.model_dump()
        self._events.append(event_dict)
        self._new_events.append(event_dict)

        # Structured logging
        log_msg = (
            f"[{event_type.upper()}] agent='{agent or 'system'}' "
            f"tool='{tool or 'none'}' status='{status}': {message}"
        )
        if status == "failed" or event_type == "error":
            logger.error(log_msg)
        else:
            logger.info(log_msg)

        # Notify registered listeners safely
# Notify registered listeners safely
        for listener in self._listeners + _GLOBAL_LISTENERS:
            try:
                listener(event_dict)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error in event listener callback: %s", exc)

        return event_dict

    def emit_event(self, event: ActivityEvent) -> dict[str, Any]:
        """Store and broadcast an already constructed ActivityEvent instance."""
        event_dict = event.model_dump()
        self._events.append(event_dict)
        self._new_events.append(event_dict)

        log_msg = (
            f"[{event.event_type.upper()}] agent='{event.agent or 'system'}' "
            f"tool='{event.tool or 'none'}' status='{event.status}': {event.message}"
        )
        if event.status == "failed" or event.event_type == "error":
            logger.error(log_msg)
        else:
            logger.info(log_msg)

# Notify registered listeners safely
        for listener in self._listeners + _GLOBAL_LISTENERS:
            try:
                listener(event_dict)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error in event listener callback: %s", exc)

        return event_dict

    def emit_planning(
        self,
        message: str,
        agent: str = "",
        tool: str = "",
        status: str = "running",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Emit a planning event."""
        return self.emit(
            event_type="planning",
            message=message,
            agent=agent,
            tool=tool,
            status=status,
            metadata=metadata,
        )

    def emit_searching(
        self,
        message: str,
        agent: str = "",
        tool: str = "",
        status: str = "running",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Emit a searching event."""
        return self.emit(
            event_type="searching",
            message=message,
            agent=agent,
            tool=tool,
            status=status,
            metadata=metadata,
        )

    def emit_fetching(
        self,
        message: str,
        agent: str = "",
        tool: str = "",
        status: str = "running",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Emit a content fetching or scraping event."""
        return self.emit(
            event_type="fetching",
            message=message,
            agent=agent,
            tool=tool,
            status=status,
            metadata=metadata,
        )

    def emit_analyzing(
        self,
        message: str,
        agent: str = "",
        tool: str = "",
        status: str = "running",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Emit a data or text analysis event."""
        return self.emit(
            event_type="analyzing",
            message=message,
            agent=agent,
            tool=tool,
            status=status,
            metadata=metadata,
        )

    def emit_coding(
        self,
        message: str,
        agent: str = "",
        tool: str = "",
        status: str = "running",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Emit a code generation, repair, or execution event."""
        return self.emit(
            event_type="coding",
            message=message,
            agent=agent,
            tool=tool,
            status=status,
            metadata=metadata,
        )

    def emit_generating(
        self,
        message: str,
        agent: str = "",
        tool: str = "",
        status: str = "running",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Emit a media or artifact generation event."""
        return self.emit(
            event_type="generating",
            message=message,
            agent=agent,
            tool=tool,
            status=status,
            metadata=metadata,
        )

    def emit_memory(
        self,
        message: str,
        agent: str = "",
        tool: str = "",
        status: str = "running",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Emit a memory recall or storage event."""
        return self.emit(
            event_type="memory",
            message=message,
            agent=agent,
            tool=tool,
            status=status,
            metadata=metadata,
        )

    def emit_complete(
        self,
        message: str,
        agent: str = "",
        tool: str = "",
        status: str = "complete",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Emit a task completion event."""
        return self.emit(
            event_type="complete",
            message=message,
            agent=agent,
            tool=tool,
            status=status,
            metadata=metadata,
        )

    def emit_error(
        self,
        message: str,
        agent: str = "",
        tool: str = "",
        status: str = "failed",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Emit an error or failure event."""
        return self.emit(
            event_type="error",
            message=message,
            agent=agent,
            tool=tool,
            status=status,
            metadata=metadata,
        )

    def emit_fallback(
        self,
        message: str,
        agent: str = "",
        tool: str = "",
        status: str = "running",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Emit a fallback invocation event when an initial attempt or tool fails."""
        return self.emit(
            event_type="fallback",
            message=message,
            agent=agent,
            tool=tool,
            status=status,
            metadata=metadata,
        )

    def get_events(self) -> list[dict[str, Any]]:
        """Return a copy of all emitted events recorded by this emitter."""
        return list(self._events)

    def get_all_events(self) -> list[dict[str, Any]]:
        """Alias for get_events() to retrieve all recorded events."""
        return self.get_events()

    def get_new_events(self, clear: bool = True) -> list[dict[str, Any]]:
        """Return events recorded since the last call to get_new_events.

        Args:
            clear: Whether to clear the buffer of new events after retrieval.
        """
        new = list(self._new_events)
        if clear:
            self._new_events.clear()
        return new

    def clear(self) -> None:
        """Clear all stored events from this emitter."""
        self._events.clear()
        self._new_events.clear()

    @property
    def events(self) -> list[dict[str, Any]]:
        """Direct access to the internal list of events."""
        return self._events

    def __len__(self) -> int:
        return len(self._events)
