"""
Sidebar UI component for OmniForge AI.
"""

import streamlit as st


def render_sidebar():
    """Render the left sidebar with minimal tools."""
    with st.sidebar:
        st.markdown("## 🔥 OmniForge AI")
        st.caption("Multimodal AI Agent")
        st.markdown("---")
        
        # Conversation controls
        st.markdown("#### Conversation")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear", use_container_width=True, help="Clear conversation"):
                st.session_state.chat_messages = []
                st.session_state.activity_events = []
                st.session_state.current_sources = []
                import uuid
                st.session_state.thread_id = str(uuid.uuid4())
                st.rerun()
        with col2:
            if st.button("📋 Export", use_container_width=True, help="Export conversation"):
                _export_conversation()
        
        # About
        st.markdown("---")
        st.caption(
            "Built with LangChain · LangGraph · MCP · "
            "Gemini · LangSmith · Streamlit"
        )
    
    return "💬 Chat"


def _export_conversation():
    """Export the current conversation as markdown."""
    messages = st.session_state.get("chat_messages", [])
    if not messages:
        st.toast("No messages to export.")
        return
    
    lines = ["# OmniForge AI Conversation\n"]
    for msg in messages:
        role = msg.get("role", "unknown").title()
        content = msg.get("content", "")
        lines.append(f"## {role}\n\n{content}\n")
    
    export_text = "\n".join(lines)
    st.download_button(
        "📥 Download",
        data=export_text,
        file_name="omniforge_conversation.md",
        mime="text/markdown",
    )


def render_settings_page():
    """Render the settings page."""
    st.markdown("## ⚙️ Settings")
    
    try:
        from omniforge.config.settings import get_settings
        settings = get_settings()
        
        st.markdown("### Models")
        st.text_input("Primary Model", value=settings.DEFAULT_MODEL, disabled=True)
        st.text_input("Reasoning Model", value=settings.REASONING_MODEL, disabled=True)
        st.text_input("Image Model", value=settings.IMAGE_MODEL, disabled=True)
        st.text_input("Video Model", value=settings.VIDEO_MODEL, disabled=True)
        
        st.markdown("### Limits")
        st.number_input("Max Search Results", value=settings.MAX_SEARCH_RESULTS, disabled=True)
        st.number_input("Max Fetch Pages", value=settings.MAX_FETCH_PAGES, disabled=True)
        st.number_input("Max Code Repair Attempts", value=settings.MAX_CODE_REPAIR_ATTEMPTS, disabled=True)
        
        st.markdown("### Features")
        st.checkbox("Memory Enabled", value=settings.MEMORY_ENABLED, disabled=True)
        st.checkbox("Media Enabled", value=settings.MEDIA_ENABLED, disabled=True)
        
        st.info("Settings are configured via `.env` file. Restart the app after changes.")
        
    except Exception as e:
        st.error(f"Failed to load settings: {e}")


def render_workspace_page():
    """Render the workspace file browser."""
    st.markdown("## 📁 Workspace")
    
    try:
        from omniforge.coding.workspace import Workspace
        workspace = Workspace()
        files = workspace.list_files()
        
        if not files:
            st.info("Workspace is empty. The coding agent will create files here.")
            return
        
        for f in files:
            icon = "📁" if f["is_dir"] else "📄"
            size = f"{f['size']} bytes" if not f["is_dir"] else ""
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"{icon} `{f['name']}`")
            with col2:
                if not f["is_dir"]:
                    st.caption(size)
                    if st.button("👁️", key=f"view_{f['path']}", help="View file"):
                        try:
                            content = workspace.read_file(f["path"])
                            st.code(content, language="python")
                        except Exception as e:
                            st.error(str(e))
    except Exception as e:
        st.error(f"Failed to load workspace: {e}")
