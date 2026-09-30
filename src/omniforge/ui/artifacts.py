"""
Artifacts UI component for OmniForge AI.
"""

import os
import streamlit as st
from pathlib import Path


def render_artifacts_section():
    """Render artifacts display (generated code, images, videos, reports)."""
    artifacts_path = Path("artifacts")
    
    # Images
    images_path = artifacts_path / "images"
    if images_path.exists():
        image_files = sorted(images_path.glob("*.*"), reverse=True)
        if image_files:
            st.markdown("#### 🖼️ Generated Images")
            cols = st.columns(min(3, len(image_files)))
            for i, img in enumerate(image_files[:6]):
                with cols[i % 3]:
                    try:
                        st.image(str(img), caption=img.name, use_container_width=True)
                    except Exception:
                        st.caption(f"📎 {img.name}")
    
    # Videos
    videos_path = artifacts_path / "videos"
    if videos_path.exists():
        video_files = sorted(videos_path.glob("*.mp4"), reverse=True)
        if video_files:
            st.markdown("#### 🎬 Generated Videos")
            for vid in video_files[:3]:
                try:
                    st.video(str(vid))
                    st.caption(vid.name)
                except Exception:
                    st.caption(f"📎 {vid.name}")
    
    # Code artifacts
    code_path = artifacts_path / "code"
    if code_path.exists():
        code_files = sorted(code_path.glob("*.*"), reverse=True)
        if code_files:
            st.markdown("#### 💻 Code Artifacts")
            for cf in code_files[:5]:
                with st.expander(f"📄 {cf.name}"):
                    try:
                        content = cf.read_text(encoding="utf-8")
                        lang = "python" if cf.suffix == ".py" else "text"
                        st.code(content, language=lang)
                    except Exception as e:
                        st.error(str(e))
