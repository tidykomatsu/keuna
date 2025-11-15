"""
EUNACOM Quiz Application - Home Page
"""

import streamlit as st

from src.auth import show_login_page, show_logout_button
from src.database import init_database, get_user_stats
from src.modern_ui import inject_modern_css

# ============================================================================
# Page Config
# ============================================================================

st.set_page_config(
    page_title="EUNACOM Quiz - Inicio",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="collapsed"
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

    # Hide sidebar completely before authentication
    if not st.session_state.authenticated:
        st.markdown(
            """
            <style>
                [data-testid="collapsedControl"] {
                    display: none
                }
                section[data-testid="stSidebar"] {
                    display: none;
                }
            </style>
            """,
            unsafe_allow_html=True
        )
        show_login_page()
        return

    # Show sidebar after authentication + inject modern CSS
    st.markdown(
        """
        <style>
            [data-testid="collapsedControl"] {
                display: block
            }
            section[data-testid="stSidebar"] {
                display: block;
            }
        </style>
        """,
        unsafe_allow_html=True
    )
    inject_modern_css()

    # Authenticated home page
    st.title("🏥 EUNACOM Quiz")

    st.markdown(f"### Bienvenida {st.session_state.name} 👋")

    # Quick stats
    stats = get_user_stats(st.session_state.username)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📝 Respondidas", stats["total_answered"])
    with col2:
        st.metric("✅ Correctas", stats["total_correct"])
    with col3:
        st.metric("🎯 Precisión", f"{stats['accuracy']:.1f}%")

    st.divider()

    # Navigation - Grouped by mode type
    # Exam Practice Modes
    st.markdown("### 📝 Práctica de Examen")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📚 Práctica Aleatoria", use_container_width=True, type="primary"):
            st.switch_page("pages/1_📚_Practica_Aleatoria.py")
    with col2:
        if st.button("📖 Por Tema", use_container_width=True, type="primary"):
            st.switch_page("pages/2_📖_Por_Tema.py")

    st.divider()

    # Flashcard Modes
    st.markdown("### 🎴 Tarjetas de Estudio")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎴 Estudiar Tarjetas", use_container_width=True):
            st.switch_page("pages/4_🎴_Tarjetas.py")
    with col2:
        if st.button("✏️ Mis Tarjetas", use_container_width=True):
            st.switch_page("pages/6_✏️_Mis_Tarjetas.py")

    st.divider()

    # Other
    st.markdown("### 📊 Análisis")
    if st.button("📊 Estadísticas", use_container_width=True):
        st.switch_page("pages/5_📊_Estadisticas.py")

    # Sidebar with stats and logout
    with st.sidebar:
        st.markdown("### 📊 Tu Progreso")

        # Use single column to prevent truncation
        st.metric("📝 Total", stats["total_answered"])
        st.metric("🎯 Precisión", f"{stats['accuracy']:.1f}%")

        st.divider()
        show_logout_button()


if __name__ == "__main__":
    main()