"""
Files panel UI component for OmniForge AI.
"""

import streamlit as st
from pathlib import Path


def render_files_panel():
    """Render the file upload and analysis panel."""
    uploaded_files = st.session_state.get("uploaded_files", [])
    
    if not uploaded_files:
        st.caption("Upload files using the sidebar to analyze them.")
        return
    
    st.markdown(f"#### 📁 Uploaded Files ({len(uploaded_files)})")
    
    for i, f in enumerate(uploaded_files):
        with st.expander(f"📄 {f.name} ({f.size} bytes)"):
            if f.name.endswith((".png", ".jpg", ".jpeg")):
                st.image(f, caption=f.name)
            elif f.name.endswith(".csv"):
                try:
                    import pandas as pd
                    df = pd.read_csv(f)
                    st.dataframe(df.head(20))
                    st.caption(f"Shape: {df.shape}")
                except Exception as e:
                    st.error(str(e))
            elif f.name.endswith((".txt", ".json")):
                try:
                    content = f.read().decode("utf-8")
                    st.code(content[:3000], language="json" if f.name.endswith(".json") else "text")
                    f.seek(0)
                except Exception as e:
                    st.error(str(e))
            else:
                st.info(f"File type: {Path(f.name).suffix}")
            
            if st.button(f"🧠 Analyze this file", key=f"analyze_{i}"):
                st.session_state.pending_file_analysis = f.name
                st.info("Send a message about this file in the chat to analyze it.")
