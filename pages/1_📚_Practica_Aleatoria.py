"""
Random Practice Mode - With Smart Question Selection
"""

import streamlit as st
import polars as pl

from src.auth import require_auth, show_logout_button
from src.database import (
    save_answer,
    get_answered_questions,
    reset_user_progress,
    get_user_stats,
    get_topic_mastery_levels,
)
from src.utils import load_questions
from src.question_selector import select_next_question, get_all_topic_masteries
from src.modern_ui import inject_modern_css, show_exam_stats_sidebar, question_card, answer_feedback

# ============================================================================
# Page Config
# ============================================================================

st.set_page_config(
    page_title="Práctica Aleatoria",
    page_icon="📚",
    layout="centered"
)

inject_modern_css()
require_auth()

# ============================================================================
# Session State
# ============================================================================

def init_state():
    """Initialize page-specific state"""
    defaults = {
        "answered": False,
        "selected_answer": None,
        "current_question": None,
        "refresh_question": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_question_state():
    """Reset for new question"""
    st.session_state.answered = False
    st.session_state.selected_answer = None

# ============================================================================
# Question Display
# ============================================================================

def display_question(question: dict):
    """Display question with answer options - MODERN VERSION"""

    # Modern question card using native components
    question_card(
        question_text=question['question_text'],
        question_number=question.get('question_number', question['question_id']),
        topic=question.get('topic')
    )

    # Build clean options dict (letter -> short text only)
    options = {opt["letter"]: opt["text"] for opt in question["answer_options"]}

    selected = st.radio(
        "Selecciona tu respuesta:",
        options=options.keys(),
        format_func=lambda x: f"**{x}** {options[x]}",
        disabled=st.session_state.answered,
        key=f"answer_{question['question_id']}",
    )

    st.markdown("")

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        verify_disabled = st.session_state.answered or selected is None
        if st.button("✅ Verificar", disabled=verify_disabled, type="primary", use_container_width=True):
            st.session_state.answered = True
            st.session_state.selected_answer = selected

            correct_opt = next(opt for opt in question["answer_options"] if opt["is_correct"])
            is_correct = selected == correct_opt["letter"]

            # Toast notification for immediate feedback
            if is_correct:
                st.toast("🎉 ¡Correcto! Muy bien.", icon="✅")
            else:
                st.toast("❌ Incorrecto. Revisa la explicación.", icon="❌")

            save_answer(st.session_state.username, question["question_id"], selected, is_correct)
            st.rerun()

    with col2:
        if st.button("➡️ Siguiente", use_container_width=True):
            if selected and not st.session_state.answered:
                correct_opt = next(opt for opt in question["answer_options"] if opt["is_correct"])
                is_correct = selected == correct_opt["letter"]
                save_answer(st.session_state.username, question["question_id"], selected, is_correct)
                st.toast("✅ Respuesta guardada", icon="💾")

            st.session_state.refresh_question = True
            st.rerun()

    # ============================================================================
    # MODERN FEEDBACK SECTION - Using native components
    # ============================================================================
    if st.session_state.answered:
        st.markdown("---")

        # Get relevant option objects
        correct_opt = next(opt for opt in question["answer_options"] if opt["is_correct"])
        selected_opt = next(
            (opt for opt in question["answer_options"] if opt["letter"] == st.session_state.selected_answer),
            None
        )

        is_correct = st.session_state.selected_answer == correct_opt["letter"]
        source = question.get("source_exam") or question.get("source_file")

        # Use modern answer_feedback component
        answer_feedback(
            is_correct=is_correct,
            user_answer=selected_opt,
            correct_answer=correct_opt if not is_correct else None,
            explanation=question.get('explanation'),
            topic_explanation=question.get('explanation'),
            source=source
        )

# ============================================================================
# Main Page Logic
# ============================================================================

def main():
    """Main practice mode logic - OPTIMIZED"""
    st.title("📚 Práctica Aleatoria")
    st.markdown("---")

    init_state()

    # Sidebar: Exam stats only
    with st.sidebar:
        show_exam_stats_sidebar(st.session_state.username)
        st.divider()
        show_logout_button()

    # Get question using cached adaptive selection (FAST!)
    if st.session_state.current_question is None or st.session_state.refresh_question:
        from src.question_selector import select_adaptive_cached

        selected_question = select_adaptive_cached(st.session_state.username)

        if selected_question is None:
            st.warning("No hay preguntas disponibles")
            return

        st.session_state.current_question = selected_question
        st.session_state.refresh_question = False
        reset_question_state()

    display_question(st.session_state.current_question)


if __name__ == "__main__":
    main()
