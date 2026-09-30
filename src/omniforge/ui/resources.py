"""
Resources panel UI component for OmniForge AI.
"""

import streamlit as st


def render_resources_panel():
    """Render the resources/sources panel."""
    sources = st.session_state.get("current_sources", [])
    
    if not sources:
        st.caption("No sources collected yet.")
        return
    
    st.markdown(f"#### 📚 Resources ({len(sources)})")
    
    for src in sources:
        cid = src.get("citation_id", "")
        title = src.get("title", "Untitled")
        url = src.get("url", "")
        domain = src.get("domain", "")
        provider = src.get("source_provider", "unknown")
        source_type = src.get("source_type", "web")
        status = src.get("status", "found")
        snippet = src.get("snippet", "")
        content = src.get("content", "")
        
        # Type badges
        type_icons = {
            "academic": "📚",
            "documentation": "📖",
            "code": "💻",
            "web": "🌐",
            "news": "📰",
        }
        type_icon = type_icons.get(source_type, "🔗")
        
        # Status badge
        status_badge = "✓" if status in ("fetched", "verified") else "○"
        
        with st.expander(f"[{cid}] {type_icon} {title[:60]}"):
            cols = st.columns([2, 1])
            with cols[0]:
                if url:
                    st.markdown(f"🔗 [{domain or url[:40]}]({url})")
                st.caption(f"Provider: {provider} | Type: {source_type} | Status: {status}")
            with cols[1]:
                st.caption(f"Relevance: {src.get('relevance_score', 0):.1f}")
            
            if snippet:
                st.markdown(f"*{snippet[:300]}*")
            if content and len(content) > len(snippet or ""):
                st.text_area(
                    "Extracted content",
                    value=content[:2000],
                    height=150,
                    disabled=True,
                    key=f"src_content_{cid}_{id(src)}",
                )


def update_sources(sources: list[dict]):
    """Update session state with new sources."""
    if "current_sources" not in st.session_state:
        st.session_state.current_sources = []
    
    # Deduplicate by URL
    existing_urls = {s.get("url") for s in st.session_state.current_sources}
    for src in sources:
        if src.get("url") not in existing_urls:
            st.session_state.current_sources.append(src)
            existing_urls.add(src.get("url"))
