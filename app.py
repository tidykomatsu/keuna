"""
EUNACOM Quiz - Entry Point Redirect
Streamlit requires app.py at root. This redirects to the actual home page.
"""

import streamlit as st

st.set_page_config(
    page_title="EUNACOM Quiz",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Redirect to home page
st.switch_page("pages/0_🏠_Inicio.py")
