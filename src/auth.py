"""
Authentication module for EUNACOM Quiz App
"""

import streamlit as st
from extra_streamlit_components import CookieManager
import hashlib
import time
from datetime import datetime, timedelta

# ============================================================================
# Cookie Manager Setup
# ============================================================================

cookie_manager = CookieManager()

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

def generate_auth_token(username: str) -> str:
    """Generate a simple auth token"""
    secret = "eunacom_quiz_secret_2024"
    timestamp = str(int(time.time()))
    token_string = f"{username}:{timestamp}:{secret}"
    return hashlib.sha256(token_string.encode()).hexdigest()


def authenticate(username: str, password: str) -> bool:
    """Validate username and password"""
    if username in valid_passwords:
        return valid_passwords[username] == password
    return False


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


def check_cookie_auth():
    """Check if user has valid auth cookie"""
    try:
        cookies = cookie_manager.get_all()
        if cookies and 'eunacom_user' in cookies:
            username = cookies['eunacom_user']
            if username in valid_passwords:
                if "authenticated" not in st.session_state or not st.session_state.authenticated:
                    with st.spinner("⏳ Cargando perfil..."):
                        init_session_for_user(username)
                return True
    except:
        pass
    return False


def show_login_page():
    """Display login form with profile selection"""

    st.title("🏥 EUNACOM Quiz")
    st.markdown("### Sistema de Práctica para el Examen Único")
    st.markdown("---")

    # Check for cookie auth first
    if check_cookie_auth():
        st.rerun()
        return

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
                # Auto-login for profile
                with st.spinner("⏳ Iniciando aplicación..."):
                    init_session_for_user(username)

                    # Set persistent cookie (expires in 30 days)
                    expires = datetime.now() + timedelta(days=30)
                    cookie_manager.set(
                        'eunacom_user',
                        username,
                        expires_at=expires
                    )

                st.success(f"✅ ¡Bienvenida {st.session_state.name}!")
                st.rerun()


def require_auth():
    """Decorator/function to require authentication on pages"""
    # Check cookie auth first
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        if not check_cookie_auth():
            st.warning("⚠️ Debes iniciar sesión primero")
            st.stop()


def logout():
    """Clear session and logout"""
    # Clear cookie
    try:
        cookie_manager.delete('eunacom_user')
    except:
        pass

    # Clear session
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.name = None
    st.rerun()


def show_logout_button():
    """Display logout button in sidebar"""
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary"):
        logout()
