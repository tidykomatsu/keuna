"""
EUNACOM Quiz Application - Home Page
"""

import streamlit as st

from auth import show_login_page
from database import init_database, get_user_stats

# ============================================================================
# Page Config
# ============================================================================

st.set_page_config(
    page_title="EUNACOM Quiz - Inicio",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ============================================================================
# Main Application
# ============================================================================

def main():
    """Home page - welcome and navigation"""

    init_database()

    # Auth check
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        show_login_page()
        return

    # Authenticated home page
    st.title("🏥 EUNACOM Quiz")
    st.markdown("### Sistema de Práctica para el Examen Único")

    # Welcome message
    st.success(f"¡Bienvenida {st.session_state.name}! 👋")

    # Quick stats overview
    stats = get_user_stats(st.session_state.username)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Preguntas respondidas", stats["total_answered"])
    with col2:
        st.metric("Precisión", f"{stats['accuracy']:.1f}%")

    st.divider()

    # Navigation guide
    st.markdown("""
    ### 📚 Modos de Estudio

    Usa el menú de la izquierda para navegar entre:

    - **📚 Práctica Aleatoria**: Preguntas aleatorias con retroalimentación inmediata
    - **📖 Por Tema**: Enfócate en temas específicos
    - **🎯 Examen Simulado**: Simula condiciones de examen real
    - **🎴 Tarjetas**: Modo flashcards para memorización
    - **📊 Estadísticas**: Revisa tu progreso detallado

    ¡Buena suerte en tu preparación! 💪
    """)


if __name__ == "__main__":
    main()
