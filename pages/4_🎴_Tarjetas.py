"""
Flashcards Study Mode
"""

import streamlit as st
import polars as pl

from auth import require_auth
from database import save_flashcard_review, get_flashcard_stats, get_user_stats
from utils import load_questions

# ============================================================================
# Page Config
# ============================================================================

st.set_page_config(
    page_title="Tarjetas de Estudio",
    page_icon="🎴",
    layout="centered"
)

require_auth()

# ============================================================================
# Session State Management
# ============================================================================

def init_flashcard_state():
    """Initialize flashcard-specific session state"""
    defaults = {
        "fc_current_idx": 0,
        "fc_show_answer": False,
        "fc_deck": [],
        "fc_reviews": [],
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ============================================================================
# Flashcard Display
# ============================================================================

def show_flashcard(card: dict):
    """Display a single flashcard"""

    # Card container with styling
    st.markdown(
        """
        <style>
        .flashcard {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            padding: 40px;
            min-height: 300px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.2em;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            margin: 20px 0;
        }
        .flashcard-back {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    if not st.session_state.fc_show_answer:
        # Front of card - Question
        st.markdown(
            f'<div class="flashcard"><div style="text-align: center;">{card["question_text"]}</div></div>',
            unsafe_allow_html=True
        )

        if st.button("🔄 Mostrar Respuesta", type="primary", use_container_width=True):
            st.session_state.fc_show_answer = True
            st.rerun()

    else:
        # Back of card - Answer
        st.markdown(
            f'<div class="flashcard flashcard-back"><div style="text-align: center;">{card["correct_answer"]}</div></div>',
            unsafe_allow_html=True
        )

        st.info(f"**📖 Explicación:** {card['explanation']}")

        st.markdown("### ¿Qué tan bien lo sabías?")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("❌ No lo sabía", type="secondary", use_container_width=True):
                save_flashcard_review(st.session_state.username, card["question_id"], "wrong")
                next_card()

        with col2:
            if st.button("🤔 Más o menos", type="secondary", use_container_width=True):
                save_flashcard_review(st.session_state.username, card["question_id"], "partial")
                next_card()

        with col3:
            if st.button("✅ Lo sabía bien", type="primary", use_container_width=True):
                save_flashcard_review(st.session_state.username, card["question_id"], "correct")
                next_card()


def next_card():
    """Move to next flashcard"""
    st.session_state.fc_current_idx += 1
    st.session_state.fc_show_answer = False

    if st.session_state.fc_current_idx >= len(st.session_state.fc_deck):
        st.session_state.fc_current_idx = 0
        st.balloons()

    st.rerun()

# ============================================================================
# Deck Setup
# ============================================================================

def setup_deck(questions_df: pl.DataFrame, questions_dict: dict):
    """Setup flashcard deck based on user selection"""
    st.header("🎴 Tarjetas de Estudio")

    topics = sorted(questions_df["topic"].unique().to_list())

    selected_topics = st.multiselect(
        "Selecciona temas (vacío = todos):",
        options=topics,
        default=None,
        key="fc_topics_selector"
    )

    if selected_topics:
        filtered_df = questions_df.filter(pl.col("topic").is_in(selected_topics))
    else:
        filtered_df = questions_df

    num_cards = st.number_input(
        "Número de tarjetas:",
        min_value=5,
        max_value=min(100, len(filtered_df)),
        value=min(20, len(filtered_df)),
        step=5
    )

    st.caption(f"📊 {len(filtered_df)} tarjetas disponibles")

    if st.button("🚀 Comenzar Estudio", type="primary"):
        sampled_ids = filtered_df.sample(num_cards)["question_id"].to_list()
        st.session_state.fc_deck = [questions_dict[qid] for qid in sampled_ids]
        st.session_state.fc_current_idx = 0
        st.session_state.fc_show_answer = False
        st.session_state.fc_reviews = []
        st.rerun()

# ============================================================================
# Main Page Function
# ============================================================================

def main():
    """Main entry point for flashcards page"""
    st.title("🎴 Tarjetas de Estudio")

    init_flashcard_state()
    questions_df, questions_dict = load_questions()

    # Sidebar stats
    stats = get_user_stats(st.session_state.username)
    st.sidebar.metric("Preguntas respondidas", stats["total_answered"])
    st.sidebar.metric("Precisión", f"{stats['accuracy']:.1f}%")
    st.sidebar.divider()

    # Flashcard-specific stats
    fc_stats = get_flashcard_stats(st.session_state.username)
    st.sidebar.subheader("📊 Estadísticas de Tarjetas")
    st.sidebar.metric("Tarjetas revisadas", fc_stats.get("total_reviewed", 0))
    st.sidebar.metric("Bien aprendidas", fc_stats.get("correct_count", 0))

    if not st.session_state.fc_deck:
        setup_deck(questions_df, questions_dict)
    else:
        deck = st.session_state.fc_deck
        current_idx = st.session_state.fc_current_idx

        # Progress
        progress = (current_idx + 1) / len(deck)
        st.progress(progress, text=f"Tarjeta {current_idx + 1} de {len(deck)}")

        # Show current card
        show_flashcard(deck[current_idx])

        # Reset deck button
        st.divider()
        if st.button("🔄 Nueva Ronda", type="secondary"):
            st.session_state.fc_deck = []
            st.rerun()


if __name__ == "__main__":
    main()
