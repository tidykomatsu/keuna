"""
EUNACOM Quiz Application - Home Page with Conditional Navigation
"""

import streamlit as st

from src.auth import show_login_page
from src.database import init_database, get_user_stats

# ============================================================================
# Page Config
# ============================================================================

st.set_page_config(
    page_title="EUNACOM Quiz",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="collapsed"  # Hide sidebar by default
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
        # Inject CSS to hide sidebar on login page
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

    # Show sidebar after authentication
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

    # Authenticated home page
    st.title("🏥 EUNACOM Quiz")
    st.markdown("### Sistema de Práctica para el Examen Único")

    # Data persistence warning
    st.warning("""
    ⚠️ **Importante sobre tus datos:**
    - Si usas Streamlit Cloud, los datos se reinician periódicamente
    - **Recomendación:** Exporta tus tarjetas personalizadas regularmente
    - Para uso permanente, ejecuta localmente en tu computadora
    """)

    # Welcome message
    st.success(f"¡Bienvenida {st.session_state.name}! 👋")

    # Quick stats overview
    stats = get_user_stats(st.session_state.username)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📝 Respondidas", stats["total_answered"])
    with col2:
        st.metric("✅ Correctas", stats["total_correct"])
    with col3:
        st.metric("🎯 Precisión", f"{stats['accuracy']:.1f}%")

    st.divider()

    # Navigation guide with visual cards
    st.markdown("### 📚 Modos de Estudio")

    st.markdown("""
    Usa el **menú de la izquierda** ☰ para navegar entre los diferentes modos:
    """)

    # Mode descriptions in cards
    col1, col2 = st.columns(2)

    with col1:
        st.info("""
        **📚 Práctica Aleatoria**

        Preguntas al azar con retroalimentación inmediata
        """)

        st.info("""
        **🎯 Examen Simulado**

        Simula las condiciones del examen real
        """)

        st.info("""
        **✏️ Mis Tarjetas**

        Crea y gestiona tus propias tarjetas
        """)

    with col2:
        st.info("""
        **📖 Por Tema**

        Enfócate en temas específicos
        """)

        st.info("""
        **🎴 Tarjetas**

        Modo flashcards para memorización
        """)

        st.info("""
        **📊 Estadísticas**

        Revisa tu progreso detallado
        """)

    st.divider()
    st.markdown("### 💪 ¡Buena suerte en tu preparación!")


if __name__ == "__main__":
    main()
