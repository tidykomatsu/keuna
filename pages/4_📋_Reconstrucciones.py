"""
Reconstrucciones Practice Mode - Practice official exam reconstructions in order
FIXED: State management issues with radio buttons and navigation
"""

import streamlit as st
import polars as pl

from src.auth import require_auth, show_logout_button
from src.database import (
    save_answer,
    get_answered_questions,
    get_user_stats,
    get_reconstruction_names,
    get_reconstruction_questions,
    get_reconstruction_stats,
    get_all_reconstructions_stats,
)
from src.modern_ui import inject_modern_css

# ============================================================================
# Page Config
# ============================================================================

st.set_page_config(
    page_title="Reconstrucciones",
    page_icon="📋",
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
        "recon_answered": False,
        "recon_selected_answer": None,
        "recon_current_index": 0,
        "recon_questions": None,
        "recon_selected_name": None,
        "recon_questions_dict": None,  # NEW: Cache for quick lookup
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_question_state():
    """Reset for new question"""
    st.session_state.recon_answered = False
    st.session_state.recon_selected_answer = None


def reset_reconstruction():
    """Reset when changing reconstruction"""
    st.session_state.recon_current_index = 0
    st.session_state.recon_questions = None
    st.session_state.recon_questions_dict = None
    reset_question_state()


# ============================================================================
# Question Loading with Caching
# ============================================================================

def load_reconstruction_questions(reconstruction_name: str) -> list[dict]:
    """
    Load and cache reconstruction questions.
    Uses session_state to avoid repeated DB calls.
    """
    # Check if already loaded for this reconstruction
    if (st.session_state.recon_questions is not None and
        st.session_state.recon_selected_name == reconstruction_name):
        return st.session_state.recon_questions

    # Load from database (cached at database level too)
    questions_df = get_reconstruction_questions(reconstruction_name)

    if len(questions_df) == 0:
        return []

    questions_list = questions_df.to_dicts()

    # Cache in session state
    st.session_state.recon_questions = questions_list
    st.session_state.recon_questions_dict = {
        q["question_id"]: q for q in questions_list
    }

    return questions_list


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
# Question Display - FIXED VERSION
# ============================================================================

def display_question(question: dict, current_index: int, total: int):
    """Display question with answer options and images - FIXED state management"""

    # Question card with border
    with st.container(border=True):
        # Header with position and topic
        col1, col2 = st.columns([3, 1])
        with col1:
            if question.get('topic'):
                st.caption(f"Tema: {question['topic']}")
        with col2:
            st.caption(f"Pregunta {current_index + 1} de {total}")

        st.markdown("")
        st.markdown(f"### {question['question_text']}")

        # Display images if present
        display_question_images(question)

    # Build clean options dict (letter -> short text only)
    options = {opt["letter"]: opt["text"] for opt in question["answer_options"]}

    # FIXED: Use unique key per question AND include index to prevent conflicts
    radio_key = f"recon_radio_{question['question_id']}_{current_index}"

    # Determine default value - if answered, show selected; else None
    default_index = None
    if st.session_state.recon_answered and st.session_state.recon_selected_answer:
        option_letters = list(options.keys())
        if st.session_state.recon_selected_answer in option_letters:
            default_index = option_letters.index(st.session_state.recon_selected_answer)

    selected = st.radio(
        "Selecciona tu respuesta:",
        options=list(options.keys()),
        format_func=lambda x: f"**{x}** {options[x]}",
        disabled=st.session_state.recon_answered,
        key=radio_key,
        index=default_index,
    )

    st.markdown("")

    # Navigation buttons - FIXED: Removed problematic number_input auto-jump
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        # Previous button
        prev_disabled = current_index == 0
        if st.button("⬅️ Anterior", disabled=prev_disabled, use_container_width=True):
            st.session_state.recon_current_index = max(0, current_index - 1)
            reset_question_state()
            st.rerun()

    with col2:
        verify_disabled = st.session_state.recon_answered or selected is None
        if st.button("✅ Verificar", disabled=verify_disabled, type="primary", use_container_width=True):
            st.session_state.recon_answered = True
            st.session_state.recon_selected_answer = selected

            correct_opt = next(opt for opt in question["answer_options"] if opt["is_correct"])
            is_correct = selected == correct_opt["letter"]

            save_answer(st.session_state.username, question["question_id"], selected, is_correct)
            st.rerun()

    with col3:
        if st.button("➡️ Siguiente", use_container_width=True):
            # Save answer if not yet verified
            if selected and not st.session_state.recon_answered:
                correct_opt = next(opt for opt in question["answer_options"] if opt["is_correct"])
                is_correct = selected == correct_opt["letter"]
                save_answer(st.session_state.username, question["question_id"], selected, is_correct)

            # Move to next question
            st.session_state.recon_current_index = min(total - 1, current_index + 1)
            reset_question_state()
            st.rerun()

    # FIXED: Jump to question using a separate expander to avoid auto-trigger
    with st.expander("🔢 Ir a pregunta específica", expanded=False):
        col_jump1, col_jump2 = st.columns([3, 1])
        with col_jump1:
            jump_to = st.number_input(
                "Número de pregunta:",
                min_value=1,
                max_value=total,
                value=current_index + 1,
                step=1,
                key=f"jump_input_{current_index}",  # Dynamic key!
            )
        with col_jump2:
            st.markdown("")  # Spacing
            if st.button("Ir", key="jump_btn"):
                if jump_to != current_index + 1:
                    st.session_state.recon_current_index = jump_to - 1
                    reset_question_state()
                    st.rerun()

    # ============================================================================
    # FEEDBACK SECTION
    # ============================================================================
    if st.session_state.recon_answered:
        st.markdown("")

        correct_opt = next(opt for opt in question["answer_options"] if opt["is_correct"])
        selected_opt = next(
            (opt for opt in question["answer_options"] if opt["letter"] == st.session_state.recon_selected_answer),
            None
        )

        if st.session_state.recon_selected_answer == correct_opt["letter"]:
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

            st.success(f"**✅ Respuesta correcta: {correct_opt['letter']} {correct_opt['text']}**")

            if correct_opt.get("explanation"):
                st.info(f"**💡 Por qué es correcta:**\n\n{correct_opt['explanation']}")

        st.markdown("")

        if question.get('explanation'):
            with st.expander("📖 Explicación Completa del Tema", expanded=False):
                st.markdown(question['explanation'])

        if question.get("source_file"):
            st.caption(f"*📚 Fuente: {question['source_file']}*")


# ============================================================================
# Reconstruction Selection View
# ============================================================================

def show_reconstruction_selection():
    """Show reconstruction selection interface"""
    st.markdown("### 📋 Selecciona una Reconstrucción")
    st.markdown("*Practica exámenes oficiales reconstruidos en el orden original*")

    # Get all reconstructions with stats
    all_stats = get_all_reconstructions_stats(st.session_state.username)

    if not all_stats:
        st.warning("No hay reconstrucciones disponibles en este momento.")
        st.info("Las reconstrucciones son exámenes oficiales que han sido digitalizados.")
        return None

    st.markdown("")

    # Display as cards
    for stat in all_stats:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.markdown(f"**📋 {stat['name']}**")
                st.caption(f"{stat['total']} preguntas")

            with col2:
                if stat['answered'] > 0:
                    st.metric(
                        "Progreso",
                        f"{stat['progress']:.0f}%",
                        label_visibility="collapsed"
                    )
                else:
                    st.caption("Sin iniciar")

            with col3:
                if st.button("Practicar", key=f"btn_{stat['name']}", use_container_width=True):
                    return stat['name']

    return None


# ============================================================================
# Main Page Logic - FIXED VERSION
# ============================================================================

def main():
    """Main reconstruction practice logic"""
    st.title("📋 Reconstrucciones")

    init_state()

    # Sidebar
    with st.sidebar:
        st.markdown("### 📊 Tu Progreso")
        stats = get_user_stats(st.session_state.username)
        st.metric("Total Respondidas", stats["total_answered"])
        st.metric("Precisión Global", f"{stats['accuracy']:.1f}%")

        st.divider()

        # Reconstruction selector in sidebar - FIXED
        reconstruction_names = get_reconstruction_names()

        if reconstruction_names:
            st.markdown("### 📋 Reconstrucciones")

            # FIXED: Calculate index properly
            current_name = st.session_state.recon_selected_name

            if current_name and current_name in reconstruction_names:
                # Show current reconstruction with option to change
                st.info(f"**Actual:** {current_name}")

                if st.button("🔄 Cambiar Reconstrucción", use_container_width=True):
                    reset_reconstruction()
                    st.session_state.recon_selected_name = None
                    st.rerun()

                # Show current reconstruction stats
                recon_stats = get_reconstruction_stats(
                    st.session_state.username,
                    current_name
                )
                st.metric("Preguntas", f"{recon_stats['answered']}/{recon_stats['total']}")
                if recon_stats['answered'] > 0:
                    st.metric("Precisión", f"{recon_stats['accuracy']:.1f}%")

                if st.button("🔄 Reiniciar Posición", use_container_width=True):
                    st.session_state.recon_current_index = 0
                    reset_question_state()
                    st.rerun()
            else:
                st.caption("Selecciona una reconstrucción para comenzar")

        st.divider()
        show_logout_button()

    # Main content area
    if not st.session_state.recon_selected_name:
        # Show selection view
        selected_name = show_reconstruction_selection()
        if selected_name:
            st.session_state.recon_selected_name = selected_name
            reset_reconstruction()
            st.rerun()
        return

    # Load questions using cached function
    questions = load_reconstruction_questions(st.session_state.recon_selected_name)

    if not questions:
        st.error("No se encontraron preguntas para esta reconstrucción")
        st.session_state.recon_selected_name = None
        return

    total = len(questions)
    current_index = st.session_state.recon_current_index

    # Ensure index is valid
    if current_index >= total:
        current_index = total - 1
        st.session_state.recon_current_index = current_index

    # Header with reconstruction name
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"**📋 {st.session_state.recon_selected_name}**")
    with col2:
        recon_stats = get_reconstruction_stats(
            st.session_state.username,
            st.session_state.recon_selected_name
        )
        st.info(f"**{recon_stats['answered']}/{total}** completadas")

    # Progress bar
    answered_ids = get_answered_questions(st.session_state.username)
    recon_answered = sum(1 for q in questions if q["question_id"] in answered_ids)
    progress_pct = (recon_answered / total) * 100
    st.progress(progress_pct / 100, text=f"Progreso: {progress_pct:.0f}% ({recon_answered}/{total})")

    st.markdown("")

    # Display current question
    if 0 <= current_index < total:
        display_question(questions[current_index], current_index, total)
    else:
        st.error("Índice de pregunta inválido")


if __name__ == "__main__":
    main()