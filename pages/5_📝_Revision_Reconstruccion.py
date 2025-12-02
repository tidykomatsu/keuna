"""
Reconstruction Review Page - Review all questions from a reconstruction
Shows complete explanations and user's performance
"""

import streamlit as st
import polars as pl

from src.auth import require_auth, show_logout_button
from src.database import (
    get_reconstruction_names,
    get_reconstruction_questions,
    get_reconstruction_stats,
    get_answered_questions,
)
from src.modern_ui import inject_modern_css

# ============================================================================
# Page Config
# ============================================================================

st.set_page_config(
    page_title="Revisión Reconstrucción",
    page_icon="📝",
    layout="wide"
)

inject_modern_css()
require_auth()

# ============================================================================
# Helper Functions
# ============================================================================

def get_user_answer_for_question(username: str, question_id: str) -> dict | None:
    """Get user's answer for a specific question"""
    from src.database import get_connection
    from psycopg2.extras import RealDictCursor
    
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute(
        """
        SELECT user_answer, is_correct, answered_at
        FROM user_answers
        WHERE username = %s AND question_id = %s
        ORDER BY answered_at DESC
        LIMIT 1
        """,
        (username, question_id)
    )
    
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return dict(row) if row else None


@st.cache_data(ttl=60)
def get_all_user_answers_for_reconstruction(username: str, reconstruction_name: str) -> dict:
    """Get all user answers for questions in a reconstruction"""
    from src.database import get_connection
    from psycopg2.extras import RealDictCursor
    
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute(
        """
        SELECT 
            ua.question_id,
            ua.user_answer,
            ua.is_correct,
            ua.answered_at
        FROM user_answers ua
        JOIN questions q ON ua.question_id = q.question_id
        WHERE ua.username = %s 
          AND q.reconstruction_name = %s
        ORDER BY ua.answered_at DESC
        """,
        (username, reconstruction_name)
    )
    
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Create dict: question_id -> latest answer
    answers_dict = {}
    for row in rows:
        q_id = row["question_id"]
        if q_id not in answers_dict:  # Keep only the latest answer
            answers_dict[q_id] = dict(row)
    
    return answers_dict


# ============================================================================
# Question Card Display
# ============================================================================

def display_question_review(question: dict, index: int, user_answer: dict | None):
    """Display a question card with full review information"""
    
    question_id = question["question_id"]
    topic = question.get("topic", "Sin tema")
    correct_opt = next((opt for opt in question["answer_options"] if opt["is_correct"]), None)
    
    # Determine status
    if user_answer is None:
        status = "⬜ Sin responder"
        status_color = "#9CA3AF"
    elif user_answer["is_correct"]:
        status = "✅ Correcta"
        status_color = "#10B981"
    else:
        status = "❌ Incorrecta"
        status_color = "#EF4444"
    
    with st.expander(f"**{index + 1}.** {question['question_text'][:80]}... | {status}", expanded=False):
        # Header
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.caption(f"**Tema:** {topic}")
        with col2:
            st.markdown(f"<span style='color:{status_color};font-weight:bold;'>{status}</span>", unsafe_allow_html=True)
        with col3:
            st.caption(f"ID: {question_id[:20]}...")
        
        st.divider()
        
        # Full question text
        st.markdown(f"### {question['question_text']}")
        
        # Images if present
        images = question.get("images", [])
        for img_url in images:
            if img_url:
                try:
                    st.image(img_url, use_container_width=True)
                except:
                    st.warning("No se pudo cargar la imagen")
        
        st.markdown("")
        
        # Answer options with highlighting
        st.markdown("**Opciones:**")
        for opt in question["answer_options"]:
            letter = opt["letter"]
            text = opt["text"]
            is_correct = opt["is_correct"]
            
            # Determine styling
            if is_correct:
                prefix = "✅"
                style = "background-color: #D1FAE5; padding: 8px; border-radius: 4px; margin: 4px 0;"
            elif user_answer and user_answer["user_answer"] == letter and not user_answer["is_correct"]:
                prefix = "❌"
                style = "background-color: #FEE2E2; padding: 8px; border-radius: 4px; margin: 4px 0;"
            else:
                prefix = "⬜"
                style = "padding: 8px; margin: 4px 0;"
            
            st.markdown(f"<div style='{style}'>{prefix} **{letter}** {text}</div>", unsafe_allow_html=True)
            
            # Show explanation for this option if available
            if opt.get("explanation"):
                with st.container():
                    if is_correct:
                        st.info(f"💡 **Por qué es correcta:** {opt['explanation']}")
                    elif user_answer and user_answer["user_answer"] == letter:
                        st.warning(f"❌ **Por qué es incorrecta:** {opt['explanation']}")
        
        # General explanation
        if question.get("explanation"):
            st.markdown("")
            st.markdown("**📖 Explicación General:**")
            st.markdown(question["explanation"])
        
        # User's answer info
        if user_answer:
            st.markdown("")
            st.caption(f"*Respondida el: {user_answer['answered_at']}*")


# ============================================================================
# Main Page
# ============================================================================

def main():
    """Main review page"""
    st.title("📝 Revisión de Reconstrucción")
    st.markdown("*Revisa todas las preguntas con explicaciones completas*")
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 📋 Selecciona Reconstrucción")
        
        reconstruction_names = get_reconstruction_names()
        
        if not reconstruction_names:
            st.warning("No hay reconstrucciones disponibles")
            show_logout_button()
            return
        
        selected_recon = st.selectbox(
            "Reconstrucción:",
            options=reconstruction_names,
            key="review_recon_selector"
        )
        
        if selected_recon:
            stats = get_reconstruction_stats(st.session_state.username, selected_recon)
            st.metric("Respondidas", f"{stats['answered']}/{stats['total']}")
            if stats['answered'] > 0:
                st.metric("Precisión", f"{stats['accuracy']:.1f}%")
        
        st.divider()
        
        # Filters
        st.markdown("### 🔍 Filtros")
        filter_option = st.radio(
            "Mostrar:",
            options=["Todas", "Solo correctas", "Solo incorrectas", "Sin responder"],
            key="filter_option"
        )
        
        st.divider()
        show_logout_button()
    
    # Main content
    if not selected_recon:
        st.info("Selecciona una reconstrucción en el menú lateral para revisar")
        return
    
    # Load questions
    questions_df = get_reconstruction_questions(selected_recon)
    
    if len(questions_df) == 0:
        st.error("No se encontraron preguntas para esta reconstrucción")
        return
    
    questions = questions_df.to_dicts()
    total = len(questions)
    
    # Get user answers
    user_answers = get_all_user_answers_for_reconstruction(
        st.session_state.username, 
        selected_recon
    )
    
    # Header stats
    col1, col2, col3, col4 = st.columns(4)
    
    correct_count = sum(1 for a in user_answers.values() if a["is_correct"])
    incorrect_count = sum(1 for a in user_answers.values() if not a["is_correct"])
    unanswered_count = total - len(user_answers)
    
    with col1:
        st.metric("📊 Total", total)
    with col2:
        st.metric("✅ Correctas", correct_count)
    with col3:
        st.metric("❌ Incorrectas", incorrect_count)
    with col4:
        st.metric("⬜ Sin responder", unanswered_count)
    
    st.divider()
    
    # Apply filter
    filtered_questions = []
    for q in questions:
        q_id = q["question_id"]
        user_answer = user_answers.get(q_id)
        
        if filter_option == "Todas":
            filtered_questions.append((q, user_answer))
        elif filter_option == "Solo correctas" and user_answer and user_answer["is_correct"]:
            filtered_questions.append((q, user_answer))
        elif filter_option == "Solo incorrectas" and user_answer and not user_answer["is_correct"]:
            filtered_questions.append((q, user_answer))
        elif filter_option == "Sin responder" and user_answer is None:
            filtered_questions.append((q, user_answer))
    
    # Show count
    st.markdown(f"**Mostrando {len(filtered_questions)} de {total} preguntas**")
    
    if not filtered_questions:
        st.info("No hay preguntas que coincidan con el filtro seleccionado")
        return
    
    # Display questions
    for idx, (question, user_answer) in enumerate(filtered_questions):
        display_question_review(question, idx, user_answer)


if __name__ == "__main__":
    main()
