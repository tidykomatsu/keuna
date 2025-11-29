"""
Admin Debug Page - Test Questions with Images
Verify images load correctly and display question metadata
"""

import streamlit as st

from src.auth import require_auth, show_logout_button
from src.database import (
    get_question_by_id,
    get_random_question_with_images,
    get_questions_with_images_count,
)
from src.modern_ui import inject_modern_css

# ============================================================================
# Page Config
# ============================================================================

st.set_page_config(
    page_title="Debug - Verificar Preguntas",
    page_icon="🔧",
    layout="centered"
)

inject_modern_css()
require_auth()

# ============================================================================
# Admin Access Control
# ============================================================================

ADMIN_USERS = {"maria", "cecil"}


def check_admin_access():
    """Check if user has admin access"""
    if st.session_state.username not in ADMIN_USERS:
        st.error("❌ Acceso denegado. Esta página es solo para administradores.")
        st.stop()


check_admin_access()

# ============================================================================
# Session State
# ============================================================================

def init_state():
    """Initialize page-specific state"""
    defaults = {
        "current_question": None,
        "search_performed": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ============================================================================
# Question Display Component
# ============================================================================

def display_question_with_images(question: dict):
    """Display question fully with images and metadata"""

    with st.container(border=True):
        # Metadata row
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(f"**ID:** {question['question_id']}")
        with col2:
            st.caption(f"#{question.get('question_number', 'N/A')}")

        # Topic and Source
        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"**Tema:** {question.get('topic', 'N/A')}")
        with col2:
            source = question.get('source_file', question.get('source_type', 'N/A'))
            st.caption(f"**Fuente:** {source}")

        st.divider()

        # Question text
        st.markdown(f"### {question['question_text']}")

        # Images
        images = question.get("images", [])
        if images:
            st.markdown("#### Imágenes:")
            for idx, img_url in enumerate(images, 1):
                if img_url:
                    try:
                        st.image(img_url, use_container_width=True)
                        st.caption(f"Imagen {idx}")
                    except Exception as e:
                        st.error(f"❌ Error cargando imagen {idx}: {str(e)}")
        else:
            st.info("ℹ️ Esta pregunta no tiene imágenes")

        st.divider()

        # Answer options
        st.markdown("#### Opciones de Respuesta:")
        for opt in question.get("answer_options", []):
            marker = "✅" if opt.get("is_correct") else "  "
            st.markdown(f"{marker} **{opt['letter']}** {opt['text']}")
            if opt.get("explanation"):
                st.caption(f"   💡 {opt['explanation']}")


# ============================================================================
# Main Page Logic
# ============================================================================

def main():
    """Main debug page logic"""
    st.title("🔧 Debug - Verificar Preguntas")

    init_state()

    with st.sidebar:
        st.markdown("### 🔧 Administración")
        st.caption(f"**Usuario:** {st.session_state.username}")

        # Show count of questions with images
        with st.spinner("Contando preguntas..."):
            images_count = get_questions_with_images_count()
        st.metric("Preguntas con Imágenes", images_count)

        st.divider()
        show_logout_button()

    # Create tabs
    tab1, tab2 = st.tabs(["🔍 Buscar por ID", "🖼️ Con Imágenes"])

    # ========================================================================
    # TAB 1: Search by ID
    # ========================================================================

    with tab1:
        st.markdown("### Buscar Pregunta por ID")

        question_id = st.text_input(
            "Ingresa el ID de la pregunta:",
            placeholder="ejemplo-123-456"
        )

        col1, col2 = st.columns([1, 3])

        with col1:
            search_button = st.button("🔍 Buscar", type="primary", use_container_width=True)

        if search_button and question_id:
            with st.spinner("Buscando pregunta..."):
                question = get_question_by_id(question_id)

            if question:
                st.session_state.current_question = question
                st.session_state.search_performed = True
            else:
                st.error(f"❌ No se encontró pregunta con ID: {question_id}")
                st.session_state.search_performed = False

        # Display search result if available
        if st.session_state.search_performed and st.session_state.current_question:
            st.markdown("")
            display_question_with_images(st.session_state.current_question)

    # ========================================================================
    # TAB 2: Random with Images
    # ========================================================================

    with tab2:
        st.markdown("### Pregunta Aleatoria con Imágenes")
        st.caption(f"Total de preguntas con imágenes: **{images_count}**")

        if st.button("🎲 Cargar Aleatoria", type="primary", use_container_width=True):
            with st.spinner("Cargando pregunta aleatoria..."):
                question = get_random_question_with_images()

            if question:
                st.session_state.current_question = question
            else:
                st.error("❌ No hay preguntas con imágenes disponibles")

        # Display random question if available
        if st.session_state.current_question:
            st.markdown("")
            display_question_with_images(st.session_state.current_question)


if __name__ == "__main__":
    main()
