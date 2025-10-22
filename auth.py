"""
Authentication system
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
    st.title("🏥 EUNACOM Quiz")
    st.markdown("### Sistema de Práctica para el Examen Único")

    with st.form("login_form"):
        username = st.text_input("Usuario", placeholder="maria, amigo1, amigo2")
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("🔐 Ingresar")

        if submit:
            if username in USERS and password == USERS[username]["password"]:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.name = USERS[username]["name"]
                st.success(f"✅ Bienvenida {st.session_state.name}!")
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")

    st.caption("💡 **Usuarios:** maria / eunacom2024 | amigo1 / pass123 | amigo2 / pass456")


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
    st.sidebar.divider()
    st.sidebar.markdown(f"**👤 {st.session_state.name}**")

    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.name = None
        st.switch_page("app.py")
