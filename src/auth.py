"""
Authentication module for EUNACOM Quiz App
Cookie-based session persistence for reliable authentication
"""

import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta

# ============================================================================
# Configuration
# ============================================================================

# Users in display order: Andrea, German, Bruno, Maria
PROFILES = {
    'andrea': 'Andrea',
    'german': 'German',
    'bruno': 'Bruno',
    'maria': 'Maria',
}

# Cookie settings
COOKIE_NAME = "eunacom_auth"
COOKIE_EXPIRY_DAYS = 30


# ============================================================================
# Cookie Manager - Singleton per page run using session state
# ============================================================================

def get_cookie_manager():
    """
    Get cookie manager instance - singleton per page run.
    Stored in session state to avoid duplicate key errors.
    """
    if "_cookie_manager" not in st.session_state:
        st.session_state._cookie_manager = stx.CookieManager(key="eunacom_cookies")
    return st.session_state._cookie_manager


# ============================================================================
# Session Initialization
# ============================================================================

def init_session_for_user(username: str):
    """Initialize session state for authenticated user"""
    from src.utils import load_questions

    questions_df, questions_dict = load_questions()

    st.session_state.questions_df = questions_df
    st.session_state.questions_dict = questions_dict
    st.session_state.adaptive_weights = {}
    st.session_state.questions_since_update = 0
    st.session_state.authenticated = True
    st.session_state.username = username
    st.session_state.name = PROFILES.get(username, username.capitalize())


# ============================================================================
# Cookie Operations - All use the singleton manager
# ============================================================================

def save_session_to_cookie(username: str):
    """Save authenticated session to cookie"""
    cookie_manager = get_cookie_manager()
    expiry = datetime.now() + timedelta(days=COOKIE_EXPIRY_DAYS)
    cookie_manager.set(
        COOKIE_NAME,
        username,
        expires_at=expiry,
    )


def load_session_from_cookie() -> str | None:
    """Load session from cookie, returns username or None"""
    cookie_manager = get_cookie_manager()
    return cookie_manager.get(COOKIE_NAME)


def clear_session_cookie():
    """Clear authentication cookie"""
    cookie_manager = get_cookie_manager()
    cookie_manager.delete(COOKIE_NAME)


def restore_session_from_cookie() -> bool:
    """
    Try to restore session from cookie.
    Returns True if session was restored.
    """
    # Already authenticated in this session
    if st.session_state.get("authenticated"):
        return True

    # Try to load from cookie
    saved_username = load_session_from_cookie()

    if saved_username and saved_username in PROFILES:
        init_session_for_user(saved_username)
        return True

    return False


# ============================================================================
# Login UI
# ============================================================================

def show_login_page():
    """Display clean login page with profile selection"""

    # Initialize cookie manager early (must happen before any cookie operations)
    get_cookie_manager()

    # Custom CSS for login page
    st.markdown("""
        <style>
            .login-title {
                text-align: center;
                color: #1F2937;
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 0.5rem;
            }
            
            .login-subtitle {
                text-align: center;
                color: #6B7280;
                font-size: 1.1rem;
                margin-bottom: 2rem;
            }
            
            .profile-header {
                color: #374151;
                font-size: 1.3rem;
                font-weight: 600;
                margin-bottom: 1.5rem;
                text-align: center;
            }
            
            .stButton > button {
                border: 2px solid #E5E7EB;
                border-radius: 12px;
                padding: 0.75rem 1.5rem;
                font-size: 1rem;
                font-weight: 500;
                transition: all 0.2s ease;
                background: white;
                color: #374151;
            }
            
            .stButton > button:hover {
                border-color: #3B82F6;
                background: #EFF6FF;
                color: #1D4ED8;
                transform: translateY(-1px);
            }
            
            .login-divider {
                border: none;
                border-top: 1px solid #E5E7EB;
                margin: 1.5rem 0;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("")
    st.markdown("")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<h1 class="login-title">🏥 EUNACOM Quiz</h1>', unsafe_allow_html=True)
        st.markdown('<p class="login-subtitle">Sistema de Práctica para el Examen Único</p>', unsafe_allow_html=True)
        st.markdown('<hr class="login-divider">', unsafe_allow_html=True)
        st.markdown('<p class="profile-header">👤 Selecciona tu Perfil</p>', unsafe_allow_html=True)

    # Profile buttons - 2x2 grid
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        row1_col1, row1_col2 = st.columns(2)
        with row1_col1:
            if st.button("👤 Andrea", use_container_width=True, key="btn_andrea"):
                st.session_state._pending_login = "andrea"
                st.rerun()
        with row1_col2:
            if st.button("👤 German", use_container_width=True, key="btn_german"):
                st.session_state._pending_login = "german"
                st.rerun()

        st.markdown("")

        row2_col1, row2_col2 = st.columns(2)
        with row2_col1:
            if st.button("👤 Bruno", use_container_width=True, key="btn_bruno"):
                st.session_state._pending_login = "bruno"
                st.rerun()
        with row2_col2:
            if st.button("👤 Maria", use_container_width=True, key="btn_maria"):
                st.session_state._pending_login = "maria"
                st.rerun()


def process_pending_login():
    """Process any pending login (must be called after cookie manager is initialized)"""
    if st.session_state.get("_pending_login"):
        username = st.session_state._pending_login
        del st.session_state._pending_login

        init_session_for_user(username)
        save_session_to_cookie(username)
        st.rerun()


# ============================================================================
# Auth Guards
# ============================================================================

def require_auth():
    """Require authentication on pages - checks both session and cookie"""
    # Initialize cookie manager first
    get_cookie_manager()

    if not st.session_state.get("authenticated"):
        restore_session_from_cookie()

    if not st.session_state.get("authenticated"):
        st.warning("⚠️ Debes iniciar sesión primero")
        st.stop()


def logout():
    """Clear session and cookie, redirect to login"""
    # Clear cookie first
    clear_session_cookie()

    # Clear session state (except cookie manager)
    keys_to_keep = {"_cookie_manager"}
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]

    st.switch_page("pages/0_🏠_Inicio.py")


def show_logout_button():
    """Display logout button in sidebar"""
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary"):
        logout()