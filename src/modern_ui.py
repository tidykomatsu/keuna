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
    /* Minimal custom CSS - Let Streamlit's theme do the heavy lifting */

    /* Larger text for better readability */
    .main p, .main div, .main label {
        font-size: 1.1rem !important;
        line-height: 1.6 !important;
    }

    /* Larger buttons */
    .stButton button {
        font-size: 1.2rem !important;
        padding: 0.75rem 1.5rem !important;
        min-height: 3rem !important;
        border-radius: 8px !important;
    }

    /* Button hover effect */
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
    }

    /* Radio button improvements */
    .stRadio > div {
        gap: 0.75rem !important;
    }

    .stRadio label {
        padding: 1rem !important;
        font-size: 1.1rem !important;
        border-radius: 8px;
        transition: all 0.2s ease;
    }

    /* Container max width */
    .main .block-container {
        max-width: 950px;
        padding: 2rem 1.5rem;
    }
</style>
"""


def inject_modern_css():
    """Inject minimal CSS styling - Let Streamlit theme handle the rest"""
    st.markdown(MINIMAL_CSS, unsafe_allow_html=True)


# ============================================================================
# Sidebar Components
# ============================================================================

def show_exam_stats_sidebar(username: str):
    """Show exam practice statistics in sidebar - Using native Streamlit"""
    st.subheader("📚 Práctica de Examen")

    stats = get_user_stats(username)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Respondidas", stats["total_answered"])
    with col2:
        st.metric("Precisión", f"{stats['accuracy']:.1f}%")

    # Additional breakdown
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("✅ Correctas", stats["total_correct"])
    with col2:
        incorrect = stats["total_answered"] - stats["total_correct"]
        st.metric("❌ Incorrectas", incorrect)


def show_flashcard_stats_sidebar(username: str):
    """Show flashcard review statistics in sidebar - Using native Streamlit"""
    st.subheader("🎴 Tarjetas de Estudio")

    fc_stats = get_flashcard_stats(username)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Revisadas", fc_stats.get("total_reviewed", 0))
    with col2:
        st.metric("Dominadas", fc_stats.get("correct_count", 0))

    # Additional metrics
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("🤔 Parcial", fc_stats.get("partial_count", 0))
    with col2:
        st.metric("❌ Revisar", fc_stats.get("wrong_count", 0))


def show_combined_stats_sidebar(username: str):
    """Show both exam and flashcard stats in sidebar"""
    show_exam_stats_sidebar(username)
    st.divider()
    show_flashcard_stats_sidebar(username)
