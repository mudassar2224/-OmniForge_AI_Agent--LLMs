"""
OmniForge AI — Main Streamlit Application

Research · Code · Remember · Create

A multimodal personal AI agent powered by:
LangChain · LangGraph · MCP · Gemini · LangSmith
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import streamlit as st

# ── Ensure src is on the path ──
sys.path.insert(0, str(Path(__file__).parent / "src"))

# ── Configure logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("omniforge")

# ── Page config ──
st.set_page_config(
    page_title="OmniForge AI",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ──────────────────────────────────────────────────────────────
# Session state initialization
# ──────────────────────────────────────────────────────────────

def init_session_state():
    """Initialize all session state variables."""
    import uuid
    defaults = {
        "chat_messages": [],
        "activity_events": [],
        "current_sources": [],
        "all_memories": [],
        "uploaded_files": [],
        "thread_id": str(uuid.uuid4()),
        "graph_compiled": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ──────────────────────────────────────────────────────────────
# LangSmith setup
# ──────────────────────────────────────────────────────────────

def setup_langsmith():
    """Configure LangSmith tracing if available."""
    api_key = os.getenv("LANGSMITH_API_KEY")
    if api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = api_key
        project = os.getenv("LANGSMITH_PROJECT", "OmniForge-AI")
        os.environ["LANGCHAIN_PROJECT"] = project
        logger.info(f"LangSmith tracing enabled for project: {project}")
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"


# ──────────────────────────────────────────────────────────────
# Graph compilation
# ──────────────────────────────────────────────────────────────

async def run_agent(user_message: str, uploaded_files_list: list = None) -> dict:
    """Run the OmniForge agent graph with the user's message."""
    import os
    from langchain_core.messages import HumanMessage
    import streamlit as st
    from omniforge.graph.graph import build_graph
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    from pathlib import Path

    db_path = "data/checkpoints/conversations.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    try:
        async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
            await checkpointer.setup()
            graph = build_graph(checkpointer=checkpointer)

            # Build input state
            uploaded_files_data = []
            if uploaded_files_list:
                upload_dir = Path("workspace/uploads")
                upload_dir.mkdir(parents=True, exist_ok=True)
                for uf in uploaded_files_list:
                    file_path = upload_dir / uf.name
                    with open(file_path, "wb") as f:
                        f.write(uf.getvalue())
                    uploaded_files_data.append({
                        "name": uf.name,
                        "path": str(file_path),
                        "type": uf.type
                    })

            input_state = {
                "messages": [HumanMessage(content=user_message)],
                "uploaded_files": uploaded_files_data,
                "activity_events": "CLEAR",
                "sources": "CLEAR",
                "media_artifacts": "CLEAR",
                "code_artifacts": "CLEAR",
                "error": "",
                "final_answer": "",
                "_loop_count": 0
            }

            config = {
                "configurable": {
                    "thread_id": st.session_state.get("thread_id", "default"),
                },
                "recursion_limit": 15,
            }

            # Run the graph
            result = await graph.ainvoke(input_state, config=config)
            return result
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        return {
            "final_answer": f"Agent error: {e}",
            "sources": [],
            "activity_events": [
                {
                    "event_type": "error",
                    "status": "failed",
                    "message": str(e),
                    "agent": "system",
                    "tool": "",
                }
            ],
            "code_artifacts": [],
            "media_artifacts": [],
        }


# ──────────────────────────────────────────────────────────────
# Main application
# ──────────────────────────────────────────────────────────────

def main():
    """Main application entry point."""
    # Load .env first so all setups have access to it
    from dotenv import load_dotenv
    load_dotenv()

    # Initialize
    init_session_state()
    setup_langsmith()

    # ── Sidebar ──
    from omniforge.ui.sidebar import render_sidebar
    render_sidebar()

    # ── Main chat page ──
    
    # Header
    if not st.session_state.get("chat_messages"):
        st.markdown(
            """
            <div style="text-align: center; padding: 2rem 0;">
                <h1>🔥 OmniForge AI</h1>
                <p style="color: gray;">Research · Code · Remember · Create</p>
                <p style="font-size: 0.9rem; color: gray;">
                    Ask me to research topics, write code, analyze documents, 
                    generate images, or create videos.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Theme and Layout ──
    from omniforge.ui.theme import apply_claude_theme
    apply_claude_theme()
    
    # ── Check for Latest Artifacts (Split Screen Logic) ──
    latest_media = None
    latest_code_execution = None
    if st.session_state.get("chat_messages"):
        for msg in reversed(st.session_state["chat_messages"]):
            if msg.get("media_artifacts") and not latest_media:
                latest_media = msg["media_artifacts"][-1]
            if msg.get("code_artifacts") and not latest_code_execution:
                for ca in reversed(msg["code_artifacts"]):
                    if ca.get("output") or ca.get("error"):
                        latest_code_execution = ca
                        break
            if latest_media and latest_code_execution:
                break
                
    has_artifact = latest_media or latest_code_execution
    
    if has_artifact:
        chat_col, artifact_col = st.columns([1.2, 1], gap="large")
    else:
        chat_col = st.container()
        artifact_col = None
        
    with chat_col:
        # Render chat history
        from omniforge.ui.chat import render_chat_area, get_chat_input, add_user_message, add_assistant_message
        render_chat_area()

    # Chat input must be at the root level to pin to the bottom of the screen
    user_input = get_chat_input()
    
    if user_input:
        with chat_col:
            if hasattr(user_input, "text"):
                text_prompt = user_input.text
                files = user_input.files if hasattr(user_input, "files") else []
            else:
                text_prompt = str(user_input)
                files = []
                
            if not text_prompt and not files:
                st.stop()
                
            if files:
                st.session_state.uploaded_files = files
                
            # Add user message
            add_user_message(text_prompt)
            
            # Show user message immediately
            with st.chat_message("user"):
                st.markdown(text_prompt)
                if files:
                    for f in files:
                        st.caption(f"📎 Attached: {f.name}")
            
            # Run the agent
            with st.chat_message("assistant"):
                with st.status("💭 Thinking Process", expanded=True) as status:
                    # Run async agent with live event streaming
                    import threading
                    import queue
                    import time
                    from omniforge.graph.events import register_global_listener, clear_global_listeners
                    
                    event_queue = queue.Queue()
                    def on_event(event):
                        event_queue.put(event)
                    
                    clear_global_listeners()
                    register_global_listener(on_event)
                    
                    def run_async(coro):
                        res = None
                        exc = None
                        def thread_target():
                            nonlocal res, exc
                            try:
                                res = asyncio.run(coro)
                            except Exception as e:
                                exc = e
                        t = threading.Thread(target=thread_target)
                        t.start()
                        
                        while t.is_alive():
                            while not event_queue.empty():
                                evt = event_queue.get()
                                msg = evt.get("message", "")
                                evt_status = evt.get("status", "")
                                icon = "✅" if evt_status == "complete" else "❌" if evt_status == "failed" else "🔄"
                                st.write(f"{icon} {msg}")
                            time.sleep(0.1)
                            
                        # Drain remaining
                        while not event_queue.empty():
                            evt = event_queue.get()
                            msg = evt.get("message", "")
                            evt_status = evt.get("status", "")
                            icon = "✅" if evt_status == "complete" else "❌" if evt_status == "failed" else "🔄"
                            st.write(f"{icon} {msg}")
                            
                        if exc:
                            raise exc
                        return res

                    result = run_async(run_agent(text_prompt, files))
                    clear_global_listeners()
                    
                    # Clear session state files so they don't persist to the next turn if empty
                    st.session_state.uploaded_files = []
                    # Extract results
                    final_answer = result.get("final_answer", "I couldn't process that request.")
                    sources = result.get("sources", [])
                    events = result.get("activity_events", [])
                    code_artifacts = result.get("code_artifacts", [])
                    media_artifacts = result.get("media_artifacts", [])
                    # Keep status expanded so user can see what happened
                    status.update(label="💭 Thinking Process (Complete)", state="complete", expanded=True)
                
                # Show final answer
                st.markdown(final_answer)
                
                # Show code artifacts execution output inline
                if code_artifacts:
                    for artifact in code_artifacts:
                        if artifact.get("output") or artifact.get("error"):
                            with st.expander(f"💻 Execution Output: {artifact.get('filename', 'code')}"):
                                if artifact.get("output"):
                                    st.success(f"Output:\n```text\n{artifact['output']}\n```")
                                if artifact.get("error"):
                                    st.error(f"Error:\n```text\n{artifact['error']}\n```")
                
                # Show sources
                if sources:
                    st.markdown("### 📚 Sources")
                    # Group sources in a visually distinct way
                    for src in sources:
                        cid = src.get("citation_id", "")
                        title = src.get("title", "Untitled")
                        url = src.get("url", "")
                        domain = src.get("domain", "")
                        
                        # Create a nice box for each source
                        st.info(f"**[{cid}] {title}**\n\n🔗 [{url}]({url})")
            
            # Store to session state
            add_assistant_message(
                final_answer,
                sources=sources,
                code_artifacts=code_artifacts,
                media_artifacts=media_artifacts,
            )
            
            # Since we just generated an artifact, update the latest pointers and rerun to show it
            if code_artifacts or media_artifacts:
                st.rerun()
            
            # Update global state
            from omniforge.ui.activity import update_activity
            from omniforge.ui.resources import update_sources
            update_activity(events)
            update_sources(sources)

    # ── Render Artifacts Panel ──
    if artifact_col:
        with artifact_col:
            st.markdown('<div class="artifact-panel">', unsafe_allow_html=True)
            if latest_media:
                st.markdown(f"<div class='artifact-header'>🎨 Artifact: {latest_media.get('type', 'Media').title()}</div>", unsafe_allow_html=True)
                if latest_media.get("type") == "image" and latest_media.get("path"):
                    st.image(latest_media["path"])
                elif latest_media.get("type") == "video" and latest_media.get("path"):
                    st.video(latest_media["path"])
            
            if latest_code_execution:
                st.markdown(f"<div class='artifact-header'>💻 Artifact: Execution Output</div>", unsafe_allow_html=True)
                if latest_code_execution.get("output"):
                    st.success(f"Output:\n```text\n{latest_code_execution['output']}\n```")
                if latest_code_execution.get("error"):
                    st.error(f"Error:\n```text\n{latest_code_execution['error']}\n```")
            st.markdown('</div>', unsafe_allow_html=True)

    # (End of chat flow)


if __name__ == "__main__":
    main()
