"""
Random Practice Mode
"""

import streamlit as st
import polars as pl

from auth import require_auth
from database import (
    save_answer,
    get_answered_questions,
    reset_user_progress,
    get_user_stats,
)
from utils import load_questions

# ============================================================================
# Page Config
# ============================================================================

st.set_page_config(
    page_title="Práctica Aleatoria",
    page_icon="📚",
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
    st.subheader(f"Pregunta #{question.get('question_number', question['question_id'])}")
    st.write(question["question_text"])

    options = {opt["letter"]: opt["text"] for opt in question["answer_options"]}

    selected = st.radio(
        "Selecciona tu respuesta:",
        options=options.keys(),
        format_func=lambda x: f"{x} {options[x]}",
        disabled=st.session_state.answered,
        key=f"answer_{question['question_id']}",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Verificar", disabled=st.session_state.answered, type="primary"):
            st.session_state.answered = True
            st.session_state.selected_answer = selected

            correct_opt = next(opt for opt in question["answer_options"] if opt["is_correct"])
            is_correct = selected == correct_opt["letter"]

            save_answer(st.session_state.username, question["question_id"], selected, is_correct)
            st.rerun()

    with col2:
        if st.button("➡️ Siguiente"):
            if selected and not st.session_state.answered:
                correct_opt = next(opt for opt in question["answer_options"] if opt["is_correct"])
                is_correct = selected == correct_opt["letter"]
                save_answer(st.session_state.username, question["question_id"], selected, is_correct)

            st.session_state.refresh_question = True
            st.rerun()

    # Show feedback if answered
    if st.session_state.answered:
        correct_opt = next(opt for opt in question["answer_options"] if opt["is_correct"])

        if st.session_state.selected_answer == correct_opt["letter"]:
            st.success("✅ ¡Correcto!")
        else:
            st.error(f"❌ Incorrecto. La respuesta correcta es: **{correct_opt['letter']} {correct_opt['text']}**")

        st.info(f"**📖 Explicación:** {question['explanation']}")

        if "source_exam" in question:
            st.caption(f"*Fuente: {question['source_exam']}*")

# ============================================================================
# Main Page Logic
# ============================================================================

def main():
    """Main practice mode logic"""
    st.title("📚 Práctica Aleatoria")

    init_state()
    questions_df, questions_dict = load_questions()

    # Sidebar stats
    stats = get_user_stats(st.session_state.username)
    st.sidebar.metric("Preguntas respondidas", stats["total_answered"])
    st.sidebar.metric("Precisión", f"{stats['accuracy']:.1f}%")
    st.sidebar.divider()

    # Sidebar options
    show_unanswered = st.sidebar.checkbox("Solo preguntas no respondidas", value=False)

    if show_unanswered:
        answered_ids = get_answered_questions(st.session_state.username)
        available_df = questions_df.filter(~pl.col("question_id").is_in(list(answered_ids)))

        if len(available_df) == 0:
            st.success("🎉 ¡Has respondido todas las preguntas!")
            if st.button("Reiniciar progreso"):
                reset_user_progress(st.session_state.username)
                st.rerun()
            return
    else:
        available_df = questions_df

    # Get current question
    if st.session_state.current_question is None or st.session_state.refresh_question:
        sampled_id = available_df.sample(1)["question_id"][0]
        st.session_state.current_question = questions_dict[sampled_id]
        st.session_state.refresh_question = False
        reset_question_state()

    display_question(st.session_state.current_question)


if __name__ == "__main__":
    main()
