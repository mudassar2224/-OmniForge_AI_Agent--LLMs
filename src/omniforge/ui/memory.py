"""
Memory panel UI component for OmniForge AI.
"""

import asyncio
import streamlit as st


def render_memory_panel():
    """Render the memory management panel."""
    st.markdown("#### 🧠 Memory")
    
    # Memory controls
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Load Memories", use_container_width=True):
            _load_memories()
    with col2:
        if st.button("🗑️ Clear All", use_container_width=True):
            _clear_all_memories()
    
    # Display memories by category
    memories = st.session_state.get("all_memories", [])
    
    if not memories:
        st.caption("No memories stored yet. The agent learns from conversations.")
        return
    
    # Group by category
    categories = {}
    for mem in memories:
        cat = mem.get("category", "other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(mem)
    
    category_labels = {
        "semantic": "📋 User Preferences & Facts",
        "episodic": "📝 Past Interactions",
        "procedural": "⚙️ Workflow Preferences",
    }
    
    for cat, items in categories.items():
        label = category_labels.get(cat, f"📌 {cat.title()}")
        with st.expander(f"{label} ({len(items)})"):
            for item in items:
                cols = st.columns([3, 1])
                with cols[0]:
                    st.markdown(f"**{item.get('key', '')}**: {item.get('value', '')}")
                with cols[1]:
                    if st.button("🗑️", key=f"del_{item.get('id', '')}", help="Delete"):
                        _delete_memory(item.get("id", ""))
                        st.rerun()
    
    # Manual memory input
    st.markdown("---")
    st.markdown("**Add a memory manually:**")
    with st.form("add_memory_form"):
        category = st.selectbox("Category", ["semantic", "episodic", "procedural"])
        key = st.text_input("Label (e.g., 'Preferred language')")
        value = st.text_input("Value (e.g., 'Python')")
        submitted = st.form_submit_button("💾 Remember")
        if submitted and key and value:
            _add_memory(category, key, value)
            st.rerun()


def _load_memories():
    """Load all memories from the store."""
    try:
        from omniforge.memory.long_term import MemoryStore
        store = MemoryStore()
        loop = asyncio.new_event_loop()
        loop.run_until_complete(store.initialize())
        memories = loop.run_until_complete(store.list_all())
        loop.close()
        st.session_state.all_memories = memories
    except Exception as e:
        st.error(f"Failed to load memories: {e}")
        st.session_state.all_memories = []


def _add_memory(category: str, key: str, value: str):
    """Add a memory to the store."""
    try:
        from omniforge.memory.long_term import MemoryStore
        store = MemoryStore()
        loop = asyncio.new_event_loop()
        loop.run_until_complete(store.initialize())
        loop.run_until_complete(store.store(category, key, value))
        loop.close()
        _load_memories()
        st.success(f"Remembered: {key}")
    except Exception as e:
        st.error(f"Failed to save memory: {e}")


def _delete_memory(memory_id: str):
    """Delete a memory from the store."""
    try:
        from omniforge.memory.long_term import MemoryStore
        store = MemoryStore()
        loop = asyncio.new_event_loop()
        loop.run_until_complete(store.initialize())
        loop.run_until_complete(store.delete(memory_id))
        loop.close()
        _load_memories()
    except Exception as e:
        st.error(f"Failed to delete memory: {e}")


def _clear_all_memories():
    """Clear all memories."""
    try:
        from omniforge.memory.long_term import MemoryStore
        store = MemoryStore()
        loop = asyncio.new_event_loop()
        loop.run_until_complete(store.initialize())
        loop.run_until_complete(store.clear_all())
        loop.close()
        st.session_state.all_memories = []
        st.success("All memories cleared.")
    except Exception as e:
        st.error(f"Failed to clear memories: {e}")
