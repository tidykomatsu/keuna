"""
Authentication module for EUNACOM Quiz App
Session-based authentication (no cookies)
"""

import streamlit as st

# ============================================================================
# Valid Users Configuration
# ============================================================================

# Profiles (display names)
profiles = {
    'maria': 'Maria',
    'amigo1': 'Amigo 1',
    'amigo2': 'Amigo 2',
    'andrea': 'Andrea',
    'bruno': 'Bruno',
    'german': 'German'
}

# ============================================================================
# Authentication Functions
# ============================================================================

def init_session_for_user(username: str):
    """Initialize session state for authenticated user"""
    # Preload questions into session state (ONE TIME)
    from src.utils import load_questions
    questions_df, questions_dict = load_questions()

    # Store for instant access throughout session
    st.session_state.questions_df = questions_df
    st.session_state.questions_dict = questions_dict

    # Initialize adaptive weights
    st.session_state.adaptive_weights = {}
    st.session_state.questions_since_update = 0

    # Set auth state
    st.session_state.authenticated = True
    st.session_state.username = username
    st.session_state.name = profiles.get(username, username.capitalize())


def show_login_page():
    """Display login form with profile selection"""

    st.title("🏥 EUNACOM Quiz")
    st.markdown("### Sistema de Práctica para el Examen Único")
    st.markdown("---")

    st.markdown("### 👤 Selecciona tu Perfil")

    # Profile selection
    col1, col2, col3 = st.columns(3)

    profile_list = list(profiles.keys())

    for idx, username in enumerate(profile_list):
        col = [col1, col2, col3][idx % 3]
        with col:
            if st.button(
                f"👤 {profiles[username]}",
                use_container_width=True,
                key=f"profile_{username}"
            ):
                # Login for this profile
                with st.spinner("⏳ Iniciando aplicación..."):
                    init_session_for_user(username)

                st.success(f"✅ ¡Bienvenida {st.session_state.name}!")
                st.rerun()


def require_auth():
    """Require authentication on pages - redirect if not authenticated"""
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.warning("⚠️ Debes iniciar sesión primero")
        st.stop()


def logout():
    """Clear session and logout"""
    # Clear all session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    # Redirect to home page (login screen)
    st.switch_page("app.py")


def show_logout_button():
    """Display logout button in sidebar"""
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary"):
        logout()
