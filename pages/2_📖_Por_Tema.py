"""
Topic-Based Practice Mode - With Smart Question Selection
"""

import streamlit as st
import polars as pl

from src.auth import require_auth, show_logout_button
from src.database import (
    save_answer,
    get_answered_questions,
    get_user_stats,
    get_topic_mastery_levels,
)
from src.utils import load_questions
from src.question_selector import select_next_question, get_all_topic_masteries
from src.modern_ui import inject_modern_css, show_exam_stats_sidebar

# ============================================================================
# Page Config
# ============================================================================

st.set_page_config(
    page_title="Por Tema",
    page_icon="📖",
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
        "selected_topic": None,
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
    """Display question with answer options - ENHANCED VERSION"""

    # Question card
    with st.container():
        # SHOW TOPIC - Modern badge style
        if question.get('topic'):
            st.markdown(
                f'<div class="topic-badge">📚 {question["topic"]}</div>',
                unsafe_allow_html=True
            )

        st.markdown(f"### 📝 Pregunta #{question.get('question_number', question['question_id'])}")
        st.markdown("---")
        st.markdown(f"**{question['question_text']}**")
        st.markdown("")

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

            save_answer(st.session_state.username, question["question_id"], selected, is_correct)
            st.rerun()

    with col2:
        if st.button("➡️ Siguiente", use_container_width=True):
            if selected and not st.session_state.answered:
                correct_opt = next(opt for opt in question["answer_options"] if opt["is_correct"])
                is_correct = selected == correct_opt["letter"]
                save_answer(st.session_state.username, question["question_id"], selected, is_correct)

            st.session_state.refresh_question = True
            st.rerun()

    # ============================================================================
    # ENHANCED FEEDBACK SECTION - THIS IS THE NEW PART
    # ============================================================================
    if st.session_state.answered:
        st.markdown("---")

        # Get relevant option objects
        correct_opt = next(opt for opt in question["answer_options"] if opt["is_correct"])
        selected_opt = next(
            (opt for opt in question["answer_options"] if opt["letter"] == st.session_state.selected_answer),
            None
        )

        if st.session_state.selected_answer == correct_opt["letter"]:
            # ✅ CORRECT ANSWER
            st.success("### ✅ ¡Correcto!")

            # Show why this answer is correct (if explanation exists)
            if correct_opt.get("explanation"):
                st.info(f"**💡 Por qué es correcta:**\n\n{correct_opt['explanation']}")

        else:
            # ❌ INCORRECT ANSWER
            st.error("### ❌ Incorrecto")

            # Show why user's answer is wrong (if explanation exists)
            if selected_opt and selected_opt.get("explanation"):
                st.warning(
                    f"**❌ Tu respuesta ({selected_opt['letter']} {selected_opt['text']}):**\n\n"
                    f"{selected_opt['explanation']}"
                )

            st.markdown("")

            # Show the correct answer
            st.success(f"**✅ Respuesta correcta: {correct_opt['letter']} {correct_opt['text']}**")

            # Show why correct answer is correct
            if correct_opt.get("explanation"):
                st.info(f"**💡 Por qué es correcta:**\n\n{correct_opt['explanation']}")

        # General medical topic explanation (in expandable section)
        st.markdown("")

        if question.get('explanation'):
            with st.expander("📖 Explicación Completa del Tema", expanded=False):
                st.markdown(question['explanation'])

        # Source citation
        if question.get("source_exam"):
            st.caption(f"*📚 Fuente: {question['source_exam']}*")
        elif question.get("source_file"):
            st.caption(f"*📚 Fuente: {question['source_file']}*")

# ============================================================================
# Main Page Logic
# ============================================================================

def main():
    """Topic-based practice - OPTIMIZED"""
    st.title("📖 Práctica por Tema")
    st.markdown("---")

    init_state()

    # Get cached questions from session state
    questions_df = st.session_state.get('questions_df')
    if questions_df is None:
        # Fallback: load if not cached
        from src.utils import load_questions
        questions_df, questions_dict = load_questions()
        st.session_state.questions_df = questions_df
        st.session_state.questions_dict = questions_dict

    # Sidebar: MINIMAL stats and topic selector
    with st.sidebar:
        st.markdown("### 📊 Tu Progreso")
        stats = get_user_stats(st.session_state.username)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Respondidas", stats["total_answered"])
        with col2:
            st.metric("Precisión", f"{stats['accuracy']:.1f}%")

        st.divider()

        st.markdown("### 📚 Selecciona Tema")
        topics = sorted(questions_df["topic"].unique().to_list())
        selected_topic = st.selectbox(
            "Tema:",
            options=topics,
            key="topic_selector",
            label_visibility="collapsed"
        )

        st.divider()
        show_logout_button()

    # Reset question if topic changed
    if st.session_state.selected_topic != selected_topic:
        st.session_state.selected_topic = selected_topic
        st.session_state.refresh_question = True
        st.session_state.current_question = None

    # Filter by topic
    topic_df = questions_df.filter(pl.col("topic") == selected_topic)

    # Topic info card
    col1, col2 = st.columns([2, 1])
    with col1:
        st.info(f"**📚 Tema:** {selected_topic}")
    with col2:
        st.info(f"**📊 Preguntas:** {len(topic_df)}")

    # Show progress in this topic
    answered_ids = get_answered_questions(st.session_state.username)
    topic_answered = topic_df.filter(pl.col("question_id").is_in(list(answered_ids)))

    if len(topic_answered) > 0:
        progress_pct = (len(topic_answered) / len(topic_df)) * 100
        st.progress(progress_pct / 100, text=f"Progreso en este tema: {progress_pct:.0f}% ({len(topic_answered)}/{len(topic_df)})")

    st.markdown("---")

    # Get question using cached adaptive selection with topic filter
    if st.session_state.current_question is None or st.session_state.refresh_question:
        from src.question_selector import select_adaptive_cached

        selected_question = select_adaptive_cached(
            st.session_state.username,
            topic=selected_topic  # Pass the selected topic
        )

        if selected_question is None:
            st.warning("No hay preguntas disponibles para este tema")
            return

        st.session_state.current_question = selected_question
        st.session_state.refresh_question = False
        reset_question_state()

    display_question(st.session_state.current_question)


if __name__ == "__main__":
    main()
