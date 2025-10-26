"""
Authentication module for EUNACOM Quiz App
"""

import streamlit as st

# ============================================================================
# Valid Users Configuration
# ============================================================================

# For production, use hashed passwords with libraries like bcrypt
# Example: pip install bcrypt
# import bcrypt
# hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
# bcrypt.checkpw(password.encode('utf-8'), hashed)

valid_passwords = {
    'maria': 'eunacom2024',
    'amigo1': 'pass123',
    'amigo2': 'pass456',
    'andrea': 'beba0230',
    'bruno': 'bruno2024',
    'german': 'medico2024'
}

# ============================================================================
# Authentication Functions
# ============================================================================

def authenticate(username: str, password: str) -> bool:
    """Validate username and password"""
    if username in valid_passwords:
        return valid_passwords[username] == password
    return False


def show_login_page():
    """Display login form"""

    st.title("🏥 EUNACOM Quiz")
    st.markdown("### Sistema de Práctica para el Examen Único")
    st.markdown("---")

    with st.form("login_form"):
        st.markdown("### 🔐 Iniciar Sesión")

        username = st.text_input(
            "Usuario",
            placeholder="Ingresa tu usuario",
            key="login_username"
        )

        password = st.text_input(
            "Contraseña",
            type="password",
            placeholder="Ingresa tu contraseña",
            key="login_password"
        )

        submit = st.form_submit_button("🚀 Ingresar", use_container_width=True, type="primary")

        if submit:
            if authenticate(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.name = username.capitalize()
                st.success(f"¡Bienvenida {st.session_state.name}!")
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")


def require_auth():
    """Decorator/function to require authentication on pages"""
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.warning("⚠️ Debes iniciar sesión primero")
        st.stop()


def logout():
    """Clear session and logout"""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.name = None
    st.rerun()


def show_logout_button():
    """Display logout button in sidebar"""
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary"):
        logout()
