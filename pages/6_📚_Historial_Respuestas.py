"""
Global Answer History Page - Review all answers across the entire app
Shows all user's answers with filters by topic and status
"""

import streamlit as st
import polars as pl
from datetime import datetime

from src.auth import require_auth, show_logout_button
from src.database import get_all_questions
from src.modern_ui import inject_modern_css

# ============================================================================
# Page Config
# ============================================================================

st.set_page_config(
    page_title="Historial de Respuestas",
    page_icon="📚",
    layout="wide"
)

inject_modern_css()
require_auth()

# ============================================================================
# Data Loading
# ============================================================================

@st.cache_data(ttl=30)
def get_user_answer_history(username: str) -> pl.DataFrame:
    """Get all answers for a user with question details"""
    from src.database import get_connection
    from psycopg2.extras import RealDictCursor
    
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute(
        """
        SELECT 
            ua.id,
            ua.question_id,
            ua.user_answer,
            ua.is_correct,
            ua.answered_at,
            q.question_text,
            q.topic,
            q.answer_options,
            q.correct_answer,
            q.explanation,
            q.images,
            q.source_type,
            q.reconstruction_name
        FROM user_answers ua
        JOIN questions q ON ua.question_id = q.question_id
        WHERE ua.username = %s
        ORDER BY ua.answered_at DESC
        """,
        (username,)
    )
    
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not rows:
        return pl.DataFrame()
    
    return pl.DataFrame(rows)


def get_unique_topics_from_answers(answers_df: pl.DataFrame) -> list[str]:
    """Get unique topics from user's answers"""
    if len(answers_df) == 0:
        return []
    return sorted(answers_df["topic"].unique().to_list())


# ============================================================================
# Answer Card Display
# ============================================================================

def display_answer_card(answer: dict, show_question: bool = True):
    """Display a single answer with question details"""
    
    is_correct = answer["is_correct"]
    topic = answer.get("topic", "Sin tema")
    answered_at = answer["answered_at"]
    
    # Format timestamp
    if isinstance(answered_at, datetime):
        date_str = answered_at.strftime("%d/%m/%Y %H:%M")
    else:
        date_str = str(answered_at)[:16]
    
    # Status badge
    if is_correct:
        status = "✅ Correcta"
        border_color = "#10B981"
    else:
        status = "❌ Incorrecta"
        border_color = "#EF4444"
    
    # Source info
    source = answer.get("reconstruction_name") or answer.get("source_type", "")
    
    with st.container(border=True):
        # Header row
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f"**{topic}**")
            st.caption(f"📅 {date_str}")
        
        with col2:
            st.markdown(f"<span style='color:{border_color};font-weight:bold;'>{status}</span>", 
                       unsafe_allow_html=True)
        
        with col3:
            if source:
                st.caption(f"📋 {source}")
        
        if show_question:
            # Question text (truncated for list view)
            question_text = answer["question_text"]
            if len(question_text) > 200:
                question_text = question_text[:200] + "..."
            
            st.markdown(f"*{question_text}*")
            
            # Show user's answer and correct answer
            user_ans = answer["user_answer"]
            correct_ans = answer["correct_answer"]
            
            if is_correct:
                st.success(f"**Tu respuesta:** {user_ans} - {correct_ans.split(' ', 1)[-1] if ' ' in correct_ans else ''}")
            else:
                # Find user's answer text
                options = answer.get("answer_options", [])
                user_ans_text = ""
                for opt in options:
                    if opt["letter"] == user_ans:
                        user_ans_text = opt["text"]
                        break
                
                st.error(f"**Tu respuesta:** {user_ans} {user_ans_text}")
                st.success(f"**Correcta:** {correct_ans}")


def display_answer_detail(answer: dict):
    """Display full answer details in an expander"""
    
    is_correct = answer["is_correct"]
    topic = answer.get("topic", "Sin tema")
    
    # Status
    if is_correct:
        status = "✅ Correcta"
    else:
        status = "❌ Incorrecta"
    
    header_text = f"**{topic}** | {status} | {answer['question_text'][:60]}..."
    
    with st.expander(header_text, expanded=False):
        # Full question
        st.markdown(f"### {answer['question_text']}")
        
        # Images
        images = answer.get("images", [])
        if images:
            for img_url in images:
                if img_url:
                    try:
                        st.image(img_url, use_container_width=True)
                    except:
                        pass
        
        st.markdown("")
        
        # Options
        st.markdown("**Opciones:**")
        options = answer.get("answer_options", [])
        user_ans = answer["user_answer"]
        
        for opt in options:
            letter = opt["letter"]
            text = opt["text"]
            is_opt_correct = opt["is_correct"]
            
            if is_opt_correct:
                prefix = "✅"
                style = "background-color: #D1FAE5; padding: 8px; border-radius: 4px; margin: 4px 0;"
            elif letter == user_ans and not is_correct:
                prefix = "❌"
                style = "background-color: #FEE2E2; padding: 8px; border-radius: 4px; margin: 4px 0;"
            else:
                prefix = "⬜"
                style = "padding: 8px; margin: 4px 0;"
            
            st.markdown(f"<div style='{style}'>{prefix} **{letter}** {text}</div>", unsafe_allow_html=True)
            
            # Show explanation
            if opt.get("explanation"):
                if is_opt_correct:
                    st.info(f"💡 {opt['explanation']}")
                elif letter == user_ans:
                    st.warning(f"❌ {opt['explanation']}")
        
        # General explanation
        if answer.get("explanation"):
            st.markdown("")
            st.markdown("**📖 Explicación:**")
            st.markdown(answer["explanation"])


# ============================================================================
# Main Page
# ============================================================================

def main():
    """Main history page"""
    st.title("📚 Historial de Respuestas")
    st.markdown("*Revisa todas tus respuestas en la aplicación*")
    
    # Load all user answers
    answers_df = get_user_answer_history(st.session_state.username)
    
    if len(answers_df) == 0:
        st.info("Aún no has respondido ninguna pregunta. ¡Comienza a practicar!")
        with st.sidebar:
            show_logout_button()
        return
    
    # Calculate stats
    total_answers = len(answers_df)
    correct_answers = len(answers_df.filter(pl.col("is_correct") == True))
    incorrect_answers = total_answers - correct_answers
    accuracy = (correct_answers / total_answers * 100) if total_answers > 0 else 0
    
    # Get unique topics
    topics = get_unique_topics_from_answers(answers_df)
    
    # Sidebar filters
    with st.sidebar:
        st.markdown("### 🔍 Filtros")
        
        # Status filter
        status_filter = st.radio(
            "Estado:",
            options=["Todas", "Correctas", "Incorrectas"],
            key="status_filter"
        )
        
        st.markdown("")
        
        # Topic filter
        topic_filter = st.selectbox(
            "Tema:",
            options=["Todos los temas"] + topics,
            key="topic_filter"
        )
        
        st.markdown("")
        
        # Source filter
        sources = ["Todas las fuentes"]
        recon_names = answers_df.filter(
            pl.col("reconstruction_name").is_not_null()
        ).select("reconstruction_name").unique().to_series().to_list()
        
        if recon_names:
            sources.extend([f"📋 {name}" for name in recon_names])
        
        source_types = answers_df.filter(
            pl.col("reconstruction_name").is_null()
        ).select("source_type").unique().to_series().to_list()
        
        for st_type in source_types:
            if st_type:
                sources.append(f"📂 {st_type}")
        
        source_filter = st.selectbox(
            "Fuente:",
            options=sources,
            key="source_filter"
        )
        
        st.divider()
        show_logout_button()
    
    # Apply filters
    filtered_df = answers_df
    
    if status_filter == "Correctas":
        filtered_df = filtered_df.filter(pl.col("is_correct") == True)
    elif status_filter == "Incorrectas":
        filtered_df = filtered_df.filter(pl.col("is_correct") == False)
    
    if topic_filter != "Todos los temas":
        filtered_df = filtered_df.filter(pl.col("topic") == topic_filter)
    
    if source_filter != "Todas las fuentes":
        if source_filter.startswith("📋 "):
            recon_name = source_filter[3:]
            filtered_df = filtered_df.filter(pl.col("reconstruction_name") == recon_name)
        elif source_filter.startswith("📂 "):
            source_type = source_filter[3:]
            filtered_df = filtered_df.filter(
                (pl.col("source_type") == source_type) & 
                (pl.col("reconstruction_name").is_null())
            )
    
    # Header stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Total Respondidas", total_answers)
    with col2:
        st.metric("✅ Correctas", correct_answers)
    with col3:
        st.metric("❌ Incorrectas", incorrect_answers)
    with col4:
        st.metric("🎯 Precisión", f"{accuracy:.1f}%")
    
    st.divider()
    
    # Show filtered count
    filtered_count = len(filtered_df)
    st.markdown(f"**Mostrando {filtered_count} de {total_answers} respuestas**")
    
    if filtered_count == 0:
        st.info("No hay respuestas que coincidan con los filtros seleccionados")
        return
    
    # View mode selection
    view_mode = st.radio(
        "Vista:",
        options=["Lista compacta", "Vista detallada"],
        horizontal=True,
        key="view_mode"
    )
    
    st.markdown("")
    
    # Pagination
    items_per_page = 20 if view_mode == "Lista compacta" else 10
    total_pages = (filtered_count + items_per_page - 1) // items_per_page
    
    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            current_page = st.number_input(
                f"Página (1-{total_pages}):",
                min_value=1,
                max_value=total_pages,
                value=1,
                key="page_selector"
            )
    else:
        current_page = 1
    
    # Get page data
    start_idx = (current_page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    
    page_data = filtered_df.slice(start_idx, items_per_page).to_dicts()
    
    # Display answers
    if view_mode == "Lista compacta":
        for answer in page_data:
            display_answer_card(answer, show_question=True)
    else:
        for answer in page_data:
            display_answer_detail(answer)
    
    # Pagination info at bottom
    if total_pages > 1:
        st.markdown("")
        st.caption(f"Página {current_page} de {total_pages} | Mostrando {len(page_data)} respuestas")


if __name__ == "__main__":
    main()
