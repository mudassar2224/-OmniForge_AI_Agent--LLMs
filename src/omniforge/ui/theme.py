import streamlit as st

def apply_claude_theme():
    """Apply custom CSS to make Streamlit look more like Claude/Premium SaaS."""
    st.markdown("""
    <style>
        /* Hide Streamlit Chrome */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {display:none;}
        
        /* Typography and Spacing */
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 16px;
            color: #2D2D2D;
        }
        
        /* Make chat messages cleaner */
        .stChatMessage {
            background-color: transparent !important;
            border: none !important;
            padding-bottom: 2rem !important;
        }
        
        /* Subtler code block styling */
        pre {
            border-radius: 8px !important;
            border: 1px solid #E5E7EB !important;
        }
        
        /* Inline citations */
        sup {
            color: #0066cc;
            font-weight: 600;
            cursor: pointer;
        }
        
        /* Artifact panel styling (when rendered in columns) */
        .artifact-header {
            font-size: 1.2rem;
            font-weight: 600;
            color: #111827;
            padding-bottom: 1rem;
            border-bottom: 1px solid #E5E7EB;
            margin-bottom: 1rem;
        }
        
        /* Clean up st.info boxes for sources */
        .stAlert {
            border-radius: 8px !important;
            border: 1px solid #E5E7EB !important;
            background-color: #F9FAFB !important;
            color: #374151 !important;
        }
        
        /* Slightly reduce main padding top */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 5rem !important;
        }
    </style>
    """, unsafe_allow_html=True)
