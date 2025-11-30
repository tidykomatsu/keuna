"""
Reconstrucciones Practice Mode - Practice official exam reconstructions in order
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
    reset_question_state()


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

def display_question(question: dict, current_index: int, total: int):
    """Display question with answer options and images"""

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

    selected = st.radio(
        "Selecciona tu respuesta:",
        options=options.keys(),
        format_func=lambda x: f"**{x}** {options[x]}",
        disabled=st.session_state.recon_answered,
        key=f"recon_answer_{question['question_id']}",
    )

    st.markdown("")

    # Navigation buttons
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

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

    with col4:
        # Jump to question
        jump_to = st.number_input(
            "Ir a:",
            min_value=1,
            max_value=total,
            value=current_index + 1,
            step=1,
            key="jump_input",
            label_visibility="collapsed"
        )
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
# Main Page Logic
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
        
        # Reconstruction selector in sidebar
        reconstruction_names = get_reconstruction_names()
        
        if reconstruction_names:
            st.markdown("### 📋 Reconstrucciones")
            
            # Add "Seleccionar" option at the beginning
            options = ["-- Seleccionar --"] + reconstruction_names
            
            selected_idx = 0
            if st.session_state.recon_selected_name in reconstruction_names:
                selected_idx = reconstruction_names.index(st.session_state.recon_selected_name) + 1
            
            selected = st.selectbox(
                "Examen:",
                options=options,
                index=selected_idx,
                key="sidebar_recon_selector",
                label_visibility="collapsed"
            )
            
            if selected != "-- Seleccionar --" and selected != st.session_state.recon_selected_name:
                st.session_state.recon_selected_name = selected
                reset_reconstruction()
                st.rerun()
            
            # Show current reconstruction stats
            if st.session_state.recon_selected_name:
                recon_stats = get_reconstruction_stats(
                    st.session_state.username,
                    st.session_state.recon_selected_name
                )
                st.metric("Preguntas", f"{recon_stats['answered']}/{recon_stats['total']}")
                if recon_stats['answered'] > 0:
                    st.metric("Precisión", f"{recon_stats['accuracy']:.1f}%")
                
                if st.button("🔄 Reiniciar", use_container_width=True):
                    st.session_state.recon_current_index = 0
                    reset_question_state()
                    st.rerun()
        
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
    
    # Load questions if needed
    if st.session_state.recon_questions is None:
        questions_df = get_reconstruction_questions(st.session_state.recon_selected_name)
        if len(questions_df) == 0:
            st.error("No se encontraron preguntas para esta reconstrucción")
            st.session_state.recon_selected_name = None
            return
        st.session_state.recon_questions = questions_df.to_dicts()
    
    questions = st.session_state.recon_questions
    total = len(questions)
    current_index = st.session_state.recon_current_index
    
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
