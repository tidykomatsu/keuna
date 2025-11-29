"""
Topic-Based Practice Mode - With Smart Question Selection and IMAGE SUPPORT
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
# Image Display Helper
# ============================================================================

def display_question_images(question: dict):
    """Display images associated with a question"""
    images = question.get("images", [])
    
    if not images:
        return
    
    for idx, img_url in enumerate(images):
        if img_url:
            try:
                st.image(img_url, use_container_width=True)
            except Exception as e:
                st.warning(f"⚠️ No se pudo cargar la imagen {idx + 1}")


# ============================================================================
# Question Display
# ============================================================================

def display_question(question: dict):
    """Display question with answer options and images"""

    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            if question.get('topic'):
                st.caption(f"📚 {question['topic']}")
        with col2:
            st.caption(f"Pregunta #{question.get('question_number', question['question_id'])}")

        st.markdown("")
        st.markdown(f"**{question['question_text']}**")
        
        # Display images if present
        display_question_images(question)

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

    if st.session_state.answered:
        st.markdown("")

        correct_opt = next(opt for opt in question["answer_options"] if opt["is_correct"])
        selected_opt = next(
            (opt for opt in question["answer_options"] if opt["letter"] == st.session_state.selected_answer),
            None
        )

        if st.session_state.selected_answer == correct_opt["letter"]:
            st.success("### ✅ ¡Correcto!")
            st.toast("¡Respuesta correcta! 🎉", icon="✅")

            if correct_opt.get("explanation"):
                st.info(f"**💡 Por qué es correcta:**\n\n{correct_opt['explanation']}")

        else:
            st.error("### ❌ Incorrecto")
            st.toast("Respuesta incorrecta. Revisa la explicación.", icon="❌")

            if selected_opt and selected_opt.get("explanation"):
                st.warning(
                    f"**❌ Tu respuesta ({selected_opt['letter']} {selected_opt['text']}):**\n\n"
                    f"{selected_opt['explanation']}"
                )

            st.markdown("")

            st.success(f"**✅ Respuesta correcta: {correct_opt['letter']} {correct_opt['text']}**")

            if correct_opt.get("explanation"):
                st.info(f"**💡 Por qué es correcta:**\n\n{correct_opt['explanation']}")

        st.markdown("")

        if question.get('explanation'):
            with st.expander("📖 Explicación Completa del Tema", expanded=False):
                st.markdown(question['explanation'])

        if question.get("source_exam"):
            st.caption(f"*📚 Fuente: {question['source_exam']}*")
        elif question.get("source_file"):
            st.caption(f"*📚 Fuente: {question['source_file']}*")


# ============================================================================
# Main Page Logic
# ============================================================================

def main():
    """Topic-based practice"""
    st.title("📖 Práctica por Tema")

    init_state()

    questions_df = st.session_state.get('questions_df')
    if questions_df is None:
        from src.utils import load_questions
        questions_df, questions_dict = load_questions()
        st.session_state.questions_df = questions_df
        st.session_state.questions_dict = questions_dict

    with st.sidebar:
        st.markdown("### 📊 Tu Progreso")
        stats = get_user_stats(st.session_state.username)

        st.metric("Respondidas", stats["total_answered"])
        st.metric("Precisión", f"{stats['accuracy']:.1f}%")

        st.markdown("")

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

    if st.session_state.selected_topic != selected_topic:
        st.session_state.selected_topic = selected_topic
        st.session_state.refresh_question = True
        st.session_state.current_question = None

    topic_df = questions_df.filter(pl.col("topic") == selected_topic)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.info(f"**📚 Tema:** {selected_topic}")
    with col2:
        st.info(f"**📊 Preguntas:** {len(topic_df)}")

    answered_ids = get_answered_questions(st.session_state.username)
    topic_answered = topic_df.filter(pl.col("question_id").is_in(list(answered_ids)))

    if len(topic_answered) > 0:
        progress_pct = (len(topic_answered) / len(topic_df)) * 100
        st.progress(progress_pct / 100, text=f"Progreso en este tema: {progress_pct:.0f}% ({len(topic_answered)}/{len(topic_df)})")

    st.markdown("")

    if st.session_state.current_question is None or st.session_state.refresh_question:
        from src.question_selector import select_adaptive_cached

        selected_question = select_adaptive_cached(
            st.session_state.username,
            topic=selected_topic
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
