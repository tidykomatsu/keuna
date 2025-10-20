"""
Simple authentication for 3 users
"""

import streamlit as st
import streamlit_authenticator as stauth

# ============================================================================
# User Configuration
# ============================================================================

USERS = {
    "maria": {
        "name": "María",
        "password": "$2b$12$KIXqFhlhbJVwXkqXqZ5vYOYxGxg5nEJ5rKMZ1kZqGxqGxqGxqGxqG",  # 'eunacom2024'
    },
    "amigo1": {
        "name": "Amigo 1",
        "password": "$2b$12$KIXqFhlhbJVwXkqXqZ5vYOYxGxg5nEJ5rKMZ1kZqGxqGxqGxqGxqG",  # 'pass123'
    },
    "amigo2": {
        "name": "Amigo 2",
        "password": "$2b$12$KIXqFhlhbJVwXkqXqZ5vYOYxGxg5nEJ5rKMZ1kZqGxqGxqGxqGxqG",  # 'pass456'
    },
}


# ============================================================================
# Auth Functions
# ============================================================================


def init_auth():
    """Initialize authentication in session state"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.name = None


def show_login_page():
    """Display login form"""
    st.title("🏥 EUNACOM Quiz")
    st.markdown("### Sistema de Práctica para el Examen Único")

    with st.form("login_form"):
        username = st.text_input("Usuario", placeholder="maria, amigo1, amigo2")
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("🔐 Ingresar")

        if submit:
            if authenticate(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.name = USERS[username]["name"]
                st.success(f"✅ Bienvenida {st.session_state.name}!")
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")

    st.markdown("---")
    st.caption("💡 **Contraseñas de prueba:** maria: eunacom2024 | amigo1: pass123 | amigo2: pass456")


def authenticate(username: str, password: str) -> bool:
    """Simple password check (in production, use hashed passwords)"""
    # For simplicity, using plain text comparison
    # In production: use stauth.Hasher(['password']).generate()

    valid_passwords = {"maria": "eunacom2024", "amigo1": "pass123", "amigo2": "pass456"}

    return username in valid_passwords and password == valid_passwords[username]


def logout():
    """Clear session state and logout"""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.name = None
    st.rerun()


def show_logout_button():
    """Display logout button in sidebar"""
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        logout()
