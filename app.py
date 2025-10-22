"""
EUNACOM Quiz Application - Modern Multipage App
"""

import streamlit as st
import polars as pl
import json
from pathlib import Path

from auth import init_auth, show_login_page, show_logout_button
from database import init_database, get_user_stats
from pages.exam_questions import show_exam_questions_page
from pages.flashcards import show_flashcards_page

# ============================================================================
# Configuration
# ============================================================================

st.set_page_config(
    page_title="EUNACOM Quiz",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="expanded"
)

QUESTIONS_FILE = Path(__file__).parent / "questions_complete_20251019_185913.json"

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


# ============================================================================
# Data Loading
# ============================================================================


def extract_topic_from_source(source_file: str) -> str:
    """Extract topic from source_file using string detection"""
    source_lower = source_file.lower()

    for topic in TOPICS:
        if topic.lower() in source_lower:
            return topic

    return None


def has_correct_answer(question: dict) -> bool:
    """Check if question has at least one correct answer marked"""
    return any(opt.get("is_correct", False) for opt in question.get("answer_options", []))


@st.cache_data
def load_questions():
    """Load questions from JSON file"""
    assert QUESTIONS_FILE.exists(), f"Questions file not found: {QUESTIONS_FILE}"

    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    valid_questions = [q for q in data if has_correct_answer(q)]

    if len(valid_questions) < len(data):
        print(f"Warning: Filtered out {len(data) - len(valid_questions)} questions without correct answers")

    df = pl.DataFrame({
        "question_id": [q["question_id"] for q in valid_questions],
        "question_number": [q.get("question_number", "") for q in valid_questions],
        "source_file": [q.get("source_file", "") for q in valid_questions],
        "question_text": [q["question_text"] for q in valid_questions],
        "correct_answer": [q["correct_answer"] for q in valid_questions],
        "explanation": [q["explanation"] for q in valid_questions],
    })

    df = df.with_columns(
        pl.col("source_file").map_elements(extract_topic_from_source, return_dtype=pl.Utf8).alias("topic")
    )

    df = df.filter(pl.col("topic").is_not_null())

    questions_dict = {q["question_id"]: q for q in valid_questions}

    for row in df.iter_rows(named=True):
        if row["question_id"] in questions_dict:
            questions_dict[row["question_id"]]["topic"] = row["topic"]

    required_cols = ["question_id", "question_text", "correct_answer", "explanation", "topic"]
    assert all(col in df.columns for col in required_cols), f"Missing required columns"

    return df, questions_dict


# ============================================================================
# Main Application
# ============================================================================


def main():
    """Main application with modern navigation"""

    init_auth()
    init_database()

    if not st.session_state.authenticated:
        show_login_page()
        return

    questions_df, questions_dict = load_questions()

    # Sidebar user info
    st.sidebar.title(f"👋 {st.session_state.name}")

    stats = get_user_stats(st.session_state.username)
    st.sidebar.metric("Preguntas respondidas", stats["total_answered"])
    st.sidebar.metric("Precisión", f"{stats['accuracy']:.1f}%")

    st.sidebar.divider()

    # Modern navigation
    page = st.sidebar.radio(
        "Navegación",
        ["📝 Preguntas de Examen", "🎴 Tarjetas de Estudio"],
        label_visibility="collapsed"
    )

    # Render selected page
    if page == "📝 Preguntas de Examen":
        show_exam_questions_page(questions_df, questions_dict)
    elif page == "🎴 Tarjetas de Estudio":
        show_flashcards_page(questions_df, questions_dict)

    # Logout button
    st.sidebar.divider()
    show_logout_button()


if __name__ == "__main__":
    main()
