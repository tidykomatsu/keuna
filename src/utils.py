"""
Utility functions for EUNACOM Quiz App
"""

import polars as pl
import streamlit as st
from src.database import get_all_questions

# ============================================================================
# Question Loading
# ============================================================================

@st.cache_data(ttl=600)
def load_questions() -> tuple[pl.DataFrame, dict]:
    """
    Load questions from database
    Returns (DataFrame, dict) where dict maps question_id -> question_dict
    """
    questions_df = get_all_questions()

    if len(questions_df) == 0:
        st.error("⚠️ No hay preguntas en la base de datos")
        st.info("Por favor, importa preguntas usando el script de carga")
        st.stop()

    questions_dict = {
        row["question_id"]: dict(row)
        for row in questions_df.iter_rows(named=True)
    }

    return questions_df, questions_dict


# ============================================================================
# Legacy Compatibility
# ============================================================================

TOPICS = [
    'Cardiología',
    'Diabetes',
    'Endocrinología',
    'Gastroenterología',
    'Hematología',
    'Infectología',
    'Nefrología',
    'Neurología',
    'Respiratorio',
    'Reumatología'
]
