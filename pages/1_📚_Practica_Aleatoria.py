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
)
from src.utils import load_questions
from src.question_selector import select_next_question

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
    """Main practice mode logic"""
    st.title("📚 Práctica Aleatoria")
    st.markdown("---")

    init_state()
    questions_df, questions_dict = load_questions()

    # Sidebar stats
    with st.sidebar:
        st.markdown("### 📊 Tu Progreso")
        stats = get_user_stats(st.session_state.username)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Respondidas", stats["total_answered"])
        with col2:
            st.metric("Precisión", f"{stats['accuracy']:.1f}%")

        st.divider()

        st.markdown("### ⚙️ Opciones")
        mode = st.selectbox(
            "Modo de selección:",
            options=["adaptive", "unanswered", "weakest", "random"],
            format_func=lambda x: {
                "adaptive": "🧠 Adaptativo (Recomendado)",
                "unanswered": "📝 Solo no respondidas",
                "weakest": "⚠️ Solo incorrectas",
                "random": "🎲 Completamente aleatorio"
            }[x],
            index=0,
            help="Adaptativo: Mezcla inteligente basada en tu rendimiento"
        )

        st.divider()
        show_logout_button()

    # Get current question using smart selector
    if st.session_state.current_question is None or st.session_state.refresh_question:
        # Use smart selection algorithm
        selected_question = select_next_question(
            st.session_state.username,
            mode=mode
        )

        if selected_question is None:
            st.warning("No hay preguntas disponibles")

            # Check if user completed all in unanswered mode
            if mode == "unanswered":
                st.success("### 🎉 ¡Felicitaciones!")
                st.info("Has respondido todas las preguntas disponibles.")

                if st.button("🔄 Reiniciar progreso", type="secondary"):
                    with st.spinner("Reiniciando..."):
                        reset_user_progress(st.session_state.username)
                        st.success("Progreso reiniciado exitosamente")
                        st.rerun()
            return

        st.session_state.current_question = selected_question
        st.session_state.refresh_question = False
        reset_question_state()

    display_question(st.session_state.current_question)


if __name__ == "__main__":
    main()
