"""
Authentication module for EUNACOM Quiz App
Session-based authentication (simple and reliable)
"""

import streamlit as st

# ============================================================================
# Configuration - 9 Users
# ============================================================================

PROFILES = {
    'andrea': 'Andrea',
    'german': 'German',
    'bruno': 'Bruno',
    'seba': 'Seba',
    'naty': 'Naty',
    'dani': 'Dani',
    'miguel': 'Miguel',
    'jose': 'Jose',
    'maria': 'Libre',
}


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
# Login UI
# ============================================================================

def show_login_page():
    """Display clean login page with profile selection"""
    
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

    # Profile buttons - Vertical list (mobile-friendly)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("👤 Andrea", use_container_width=True, key="btn_andrea"):
            with st.spinner("⏳ Iniciando sesión..."):
                init_session_for_user("andrea")
            st.rerun()

        if st.button("👤 German", use_container_width=True, key="btn_german"):
            with st.spinner("⏳ Iniciando sesión..."):
                init_session_for_user("german")
            st.rerun()

        if st.button("👤 Bruno", use_container_width=True, key="btn_bruno"):
            with st.spinner("⏳ Iniciando sesión..."):
                init_session_for_user("bruno")
            st.rerun()

        if st.button("👤 Seba", use_container_width=True, key="btn_seba"):
            with st.spinner("⏳ Iniciando sesión..."):
                init_session_for_user("seba")
            st.rerun()

        if st.button("👤 Naty", use_container_width=True, key="btn_naty"):
            with st.spinner("⏳ Iniciando sesión..."):
                init_session_for_user("naty")
            st.rerun()

        if st.button("👤 Dani", use_container_width=True, key="btn_dani"):
            with st.spinner("⏳ Iniciando sesión..."):
                init_session_for_user("dani")
            st.rerun()

        if st.button("👤 Miguel", use_container_width=True, key="btn_miguel"):
            with st.spinner("⏳ Iniciando sesión..."):
                init_session_for_user("miguel")
            st.rerun()

        if st.button("👤 Jose", use_container_width=True, key="btn_jose"):
            with st.spinner("⏳ Iniciando sesión..."):
                init_session_for_user("jose")
            st.rerun()

        if st.button("👤 Libre", use_container_width=True, key="btn_maria"):
            with st.spinner("⏳ Iniciando sesión..."):
                init_session_for_user("maria")
            st.rerun()


# ============================================================================
# Auth Guards
# ============================================================================

def require_auth():
    """Require authentication on pages"""
    if not st.session_state.get("authenticated"):
        st.warning("⚠️ Debes iniciar sesión primero")
        st.stop()


def logout():
    """Clear session and logout"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.switch_page("pages/0_🏠_Inicio.py")


def show_logout_button():
    """Display logout button in sidebar"""
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary"):
        logout()
