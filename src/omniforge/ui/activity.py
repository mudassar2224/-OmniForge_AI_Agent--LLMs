"""
Agent activity panel UI component for OmniForge AI.
"""

import streamlit as st


# Status icons mapping
STATUS_ICONS = {
    "planning": "🧠",
    "searching": "🔍",
    "fetching": "📄",
    "analyzing": "🧠",
    "coding": "💻",
    "generating": "🎨",
    "memory": "🧠",
    "complete": "✅",
    "error": "❌",
    "fallback": "⚠️",
}

STATUS_PROGRESS = {
    "running": "🔄",
    "complete": "✅",
    "failed": "❌",
    "skipped": "⏭️",
}


def render_activity_panel():
    """Render the agent activity panel showing execution progress."""
    events = st.session_state.get("activity_events", [])
    
    if not events:
        st.caption("No agent activity yet.")
        return

    st.markdown("#### ⚡ Agent Activity")
    
    for event in events:
        event_type = event.get("event_type", "")
        status = event.get("status", "running")
        message = event.get("message", "")
        agent = event.get("agent", "")
        tool = event.get("tool", "")
        
        # Build the display line
        icon = STATUS_PROGRESS.get(status, "🔄")
        type_icon = STATUS_ICONS.get(event_type, "📌")
        
        detail = f"{type_icon} {message}"
        if tool:
            detail += f" *({tool})*"
        
        if status == "complete":
            st.markdown(f"{icon} {detail}")
        elif status == "failed":
            st.markdown(f"{icon} {detail}")
        elif status == "running":
            st.markdown(f"{icon} {detail}")
        else:
            st.markdown(f"{icon} {detail}")


def update_activity(events: list[dict]):
    """Update the session state with new activity events for the current turn."""
    st.session_state.activity_events = events


def clear_activity():
    """Clear activity events."""
    st.session_state.activity_events = []
