"""
Authentication system with improved UX
"""

import streamlit as st

# ============================================================================
# User Configuration
# ============================================================================

USERS = {
    "maria": {"name": "María", "password": "eunacom2024"},
    "amigo1": {"name": "Amigo 1", "password": "pass123"},
    "amigo2": {"name": "Amigo 2", "password": "pass456"},
}

# ============================================================================
# Auth Functions
# ============================================================================

def show_login_page():
    """Display login form"""

    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("<h1 style='text-align: center;'>🏥 EUNACOM Quiz</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>Sistema de Práctica</h3>", unsafe_allow_html=True)

        st.divider()

        with st.form("login_form"):
            username = st.text_input("👤 Usuario", placeholder="maria, amigo1, amigo2")
            password = st.text_input("🔒 Contraseña", type="password", placeholder="Ingresa tu contraseña")

            submit = st.form_submit_button("🔐 Ingresar", use_container_width=True, type="primary")

            if submit:
                if username in USERS and password == USERS[username]["password"]:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.name = USERS[username]["name"]
                    st.success(f"✅ ¡Bienvenida {st.session_state.name}!")
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")

        st.caption("💡 **Usuarios disponibles:**")
        st.caption("• maria / eunacom2024")
        st.caption("• amigo1 / pass123")
        st.caption("• amigo2 / pass456")


def require_auth():
    """
    Require authentication - call at start of each page
    Redirects to home if not authenticated
    """
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.warning("⚠️ Debes iniciar sesión primero")
        st.info("👉 Ve a la página de inicio para ingresar")
        st.stop()

    # Show user info and logout in sidebar
    with st.sidebar:
        st.divider()
        st.markdown(f"### 👤 {st.session_state.name}")

        if st.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary"):
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
