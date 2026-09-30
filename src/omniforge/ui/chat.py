"""
Streamlit chat UI component for OmniForge AI.
"""

import streamlit as st
from datetime import datetime


def render_chat_area():
    """Render the main chat conversation area."""
    # Display message history
    for msg in st.session_state.get("chat_messages", []):
        role = msg.get("role", "assistant")
        content = msg.get("content", "")
        
        with st.chat_message(role):
            st.markdown(content)
            
            # Show sources inline if available
            if msg.get("sources"):
                st.markdown("### 📚 Sources")
                for src in msg["sources"]:
                    cid = src.get("citation_id", "")
                    title = src.get("title", "Untitled")
                    url = src.get("url", "")
                    st.info(f"**[{cid}] {title}**\n\n🔗 [{url}]({url})")
            
            # Only render inline artifacts for historical messages (not the latest one)
            is_latest = msg is st.session_state["chat_messages"][-1]
            if not is_latest:
                # Show code artifacts execution output
                if msg.get("code_artifacts"):
                    for artifact in msg["code_artifacts"]:
                        if artifact.get("output") or artifact.get("error"):
                            with st.expander(f"💻 Execution Output: {artifact.get('filename', 'code')}"):
                                if artifact.get("output"):
                                    st.success(f"Output:\n```text\n{artifact['output']}\n```")
                                if artifact.get("error"):
                                    st.error(f"Error:\n```text\n{artifact['error']}\n```")
                
                # Show media artifacts
                if msg.get("media_artifacts"):
                    for artifact in msg["media_artifacts"]:
                        if artifact.get("type") == "image" and artifact.get("path"):
                            try:
                                st.image(artifact["path"], caption=artifact.get("prompt", ""))
                            except Exception:
                                st.info(f"Image saved to: {artifact['path']}")
                        elif artifact.get("type") == "video" and artifact.get("path"):
                            try:
                                st.video(artifact["path"])
                            except Exception:
                                st.info(f"Video saved to: {artifact['path']}")


def get_chat_input():
    """Get user input from the chat input field, allowing file uploads."""
    return st.chat_input("Ask OmniForge anything...", accept_file="multiple")


def add_user_message(content: str):
    """Add a user message to the chat history."""
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    st.session_state.chat_messages.append({
        "role": "user",
        "content": content,
        "timestamp": datetime.now().isoformat(),
    })


def add_assistant_message(content: str, sources=None, code_artifacts=None, media_artifacts=None):
    """Add an assistant message to the chat history."""
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    st.session_state.chat_messages.append({
        "role": "assistant",
        "content": content,
        "sources": sources or [],
        "code_artifacts": code_artifacts or [],
        "media_artifacts": media_artifacts or [],
        "timestamp": datetime.now().isoformat(),
    })
