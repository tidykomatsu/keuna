"""
Topic-Based Practice Mode - Polished
"""

import streamlit as st
import polars as pl

from src.auth import require_auth
from src.database import (
    save_answer,
    get_answered_questions,
    get_user_stats,
)
from src.utils import load_questions

# ============================================================================
# Page Config
# ============================================================================

st.set_page_config(
    page_title="Por Tema",
    page_icon="📖",
    layout="centered"
)

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
    """Display question with answer options"""

    # Question card
    with st.container():
        st.markdown(f"### 📝 Pregunta #{question.get('question_number', question['question_id'])}")
        st.markdown("---")
        st.markdown(f"**{question['question_text']}**")
        st.markdown("")

    options = {opt["letter"]: opt["text"] for opt in question["answer_options"]}

    selected = st.radio(
        "Selecciona tu respuesta:",
        options=options.keys(),
        format_func=lambda x: f"**{x}** {options[x]}",
        disabled=st.session_state.answered,
        key=f"answer_{question['question_id']}",
    )

    st.markdown("")

    col1, col2 = st.columns([1, 1])

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

    # Show feedback if answered
    if st.session_state.answered:
        st.markdown("---")
        correct_opt = next(opt for opt in question["answer_options"] if opt["is_correct"])

        if st.session_state.selected_answer == correct_opt["letter"]:
            st.success("### ✅ ¡Correcto!")
        else:
            st.error(f"### ❌ Incorrecto")
            st.info(f"**Respuesta correcta:** {correct_opt['letter']} {correct_opt['text']}")

        st.markdown("")
        st.info(f"**📖 Explicación:**\n\n{question['explanation']}")

        if "source_exam" in question:
            st.caption(f"*📚 Fuente: {question['source_exam']}*")

# ============================================================================
# Main Page Logic
# ============================================================================

def main():
    """Topic-based practice"""
    st.title("📖 Práctica por Tema")
    st.markdown("Enfócate en temas específicos para fortalecer tus conocimientos")
    st.markdown("---")

    init_state()
    questions_df, questions_dict = load_questions()

    # Sidebar stats and topic selector
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

    # Get current question
    if st.session_state.current_question is None or st.session_state.refresh_question:
        sampled_id = topic_df.sample(1)["question_id"][0]
        st.session_state.current_question = questions_dict[sampled_id]
        st.session_state.refresh_question = False
        reset_question_state()

    display_question(st.session_state.current_question)


if __name__ == "__main__":
    main()
