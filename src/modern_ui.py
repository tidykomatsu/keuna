"""
Modern UI Components and Styling for EUNACOM Quiz
"""

import streamlit as st
from src.database import get_user_stats, get_flashcard_stats


# ============================================================================
# Modern CSS Styling
# ============================================================================

MINIMAL_CSS = """
<style>
    .main p, .main div, .main label, .main span {
        font-size: 1.3rem !important;
        line-height: 1.7 !important;
    }

    h1 {
        font-size: 3rem !important;
        margin-bottom: 1rem !important;
    }

    h2 {
        font-size: 2.2rem !important;
        margin-bottom: 0.8rem !important;
    }

    h3 {
        font-size: 1.8rem !important;
        margin-bottom: 0.6rem !important;
    }

    .stButton button {
        font-size: 1.5rem !important;
        padding: 1rem 2rem !important;
        min-height: 3.5rem !important;
        border-radius: 10px !important;
        font-weight: 500 !important;
    }

    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15) !important;
        transition: all 0.2s ease;
    }

    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 600 !important;
    }

    [data-testid="stMetricLabel"] {
        font-size: 1.2rem !important;
        font-weight: 500 !important;
    }

    .stRadio > div {
        gap: 1rem !important;
    }

    .stRadio label {
        padding: 1.2rem 1.5rem !important;
        font-size: 1.3rem !important;
        border-radius: 10px;
        transition: all 0.2s ease;
        cursor: pointer;
    }

    .stRadio label:hover {
        background-color: rgba(59, 130, 246, 0.1);
        transform: translateX(4px);
    }

    .stSelectbox label, .stNumberInput label, .stTextInput label, .stTextArea label {
        font-size: 1.3rem !important;
        font-weight: 500 !important;
        margin-bottom: 0.5rem !important;
    }

    .stSelectbox > div > div, .stNumberInput > div > div > input, .stTextInput > div > div > input {
        font-size: 1.3rem !important;
        padding: 0.75rem 1rem !important;
        min-height: 3rem !important;
    }

    .stProgress > div > div {
        height: 1.5rem !important;
        border-radius: 8px !important;
    }

    .stProgress [role="progressbar"] {
        font-size: 1.1rem !important;
    }

    .element-container .stCaption {
        font-size: 1.1rem !important;
        opacity: 0.8;
    }

    .stAlert {
        font-size: 1.3rem !important;
        padding: 1.2rem !important;
    }

    .streamlit-expanderHeader {
        font-size: 1.3rem !important;
        font-weight: 500 !important;
        padding: 1rem !important;
    }

    .main .block-container {
        max-width: 1000px;
        padding: 2.5rem 2rem;
    }

    section[data-testid="stSidebar"] {
        padding: 2rem 1rem !important;
    }

    hr {
        margin: 1.5rem 0 !important;
    }

    .stToast {
        font-size: 1.3rem !important;
    }
</style>
"""


def inject_modern_css():
    """Inject minimal CSS styling"""
    st.markdown(MINIMAL_CSS, unsafe_allow_html=True)


# ============================================================================
# Sidebar Components
# ============================================================================

def show_exam_stats_sidebar(username: str):
    """Show exam practice statistics in sidebar"""
    st.subheader("📚 Práctica de Examen")

    stats = get_user_stats(username)

    st.metric("📝 Respondidas", stats["total_answered"])
    st.metric("🎯 Precisión", f"{stats['accuracy']:.1f}%")
    st.metric("✅ Correctas", stats["total_correct"])

    incorrect = stats["total_answered"] - stats["total_correct"]
    st.metric("❌ Incorrectas", incorrect)


def show_flashcard_stats_sidebar(username: str):
    """Show flashcard review statistics in sidebar"""
    st.subheader("🎴 Tarjetas de Estudio")

    fc_stats = get_flashcard_stats(username)

    st.metric("📚 Revisadas", fc_stats.get("total_reviewed", 0))
    st.metric("✅ Dominadas", fc_stats.get("correct_count", 0))


def show_combined_stats_sidebar(username: str):
    """Show both exam and flashcard stats in sidebar"""
    show_exam_stats_sidebar(username)
    st.divider()
    show_flashcard_stats_sidebar(username)
