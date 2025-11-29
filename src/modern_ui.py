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
    /* Tighter container */
    .main .block-container {
        max-width: 850px;
        padding: 1.5rem 2rem;
    }

    /* Remove default divider styling */
    hr {
        margin: 1rem 0;
        border: none;
        border-top: 1px solid #e5e7eb;
    }

    /* Cleaner buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
    }

    /* Subtle hover on radio */
    .stRadio label:hover {
        background: #f8fafc;
    }

    /* Metric cards - reduce label font size */
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem;
        color: #6b7280;
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
    """Show user progress statistics in sidebar"""
    st.subheader("📊 Tu Progreso")

    stats = get_user_stats(username)

    st.metric("Respondidas", stats["total_answered"])
    st.metric("Precisión", f"{stats['accuracy']:.1f}%")
    st.metric("Correctas", stats["total_correct"])

    incorrect = stats["total_answered"] - stats["total_correct"]
    st.metric("Incorrectas", incorrect)


def show_flashcard_stats_sidebar(username: str):
    """Show flashcard review statistics in sidebar"""
    st.subheader("🎴 Tarjetas de Estudio")

    fc_stats = get_flashcard_stats(username)

    st.metric("Revisadas", fc_stats.get("total_reviewed", 0))
    st.metric("Dominadas", fc_stats.get("correct_count", 0))


def show_combined_stats_sidebar(username: str):
    """Show both exam and flashcard stats in sidebar"""
    show_exam_stats_sidebar(username)
    st.divider()
    show_flashcard_stats_sidebar(username)
