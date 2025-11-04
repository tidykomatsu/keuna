"""
Flashcards Study Mode - With Custom Cards Support
"""

import streamlit as st
import polars as pl

from src.auth import require_auth, show_logout_button
from src.database import (
    save_flashcard_review,
    get_flashcard_stats,
    get_user_stats,
    get_custom_flashcards
)
from src.utils import load_questions
from src.modern_ui import inject_modern_css, show_flashcard_stats_sidebar

# ============================================================================
# Page Config
# ============================================================================

st.set_page_config(
    page_title="Tarjetas de Estudio",
    page_icon="🎴",
    layout="centered"
)

inject_modern_css()
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
        "fc_source": "questions",  # "questions", "custom", or "both"
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ============================================================================
# Flashcard Display
# ============================================================================

def show_flashcard(card: dict, is_custom: bool = False):
    """Display a single flashcard"""

    # Card container with styling
    st.markdown(
        """
        <style>
        .flashcard {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            padding: 60px;
            min-height: 400px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.5em;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            margin: 20px 0;
        }
        .flashcard-back {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        .flashcard-custom {
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        }
        .flashcard-custom-back {
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    card_class = "flashcard-custom" if is_custom else "flashcard"
    back_class = "flashcard-custom-back" if is_custom else "flashcard-back"

    if not st.session_state.fc_show_answer:
        # Front of card - Question
        front_text = card.get("front_text", card.get("question_text", ""))
        st.markdown(
            f'<div class="{card_class}"><div style="text-align: center;">{front_text}</div></div>',
            unsafe_allow_html=True
        )

        if st.button("🔄 Mostrar Respuesta", type="primary", use_container_width=True):
            st.session_state.fc_show_answer = True
            st.rerun()

    else:
        # Back of card - Answer
        back_text = card.get("back_text", card.get("correct_answer", ""))
        st.markdown(
            f'<div class="{back_class}"><div style="text-align: center;">{back_text}</div></div>',
            unsafe_allow_html=True
        )

        # Show explanation only for question cards
        if not is_custom and "explanation" in card:
            st.info(f"**📖 Explicación:** {card['explanation']}")

        st.markdown("### ¿Qué tan bien lo sabías?")

        col1, col2, col3 = st.columns(3)

        card_id = card.get("id", card.get("question_id", ""))

        with col1:
            if st.button("❌ No lo sabía", type="secondary", use_container_width=True):
                save_flashcard_review(st.session_state.username, str(card_id), "wrong")
                next_card()

        with col2:
            if st.button("🤔 Más o menos", type="secondary", use_container_width=True):
                save_flashcard_review(st.session_state.username, str(card_id), "partial")
                next_card()

        with col3:
            if st.button("✅ Lo sabía bien", type="primary", use_container_width=True):
                save_flashcard_review(st.session_state.username, str(card_id), "correct")
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
    st.markdown("### ⚙️ Configuración del Mazo")
    st.markdown("---")

    # Source selection
    col1, col2 = st.columns(2)

    with col1:
        source = st.radio(
            "📚 Fuente de las tarjetas:",
            options=["questions", "custom", "both"],
            format_func=lambda x: {
                "questions": "🎯 Preguntas del Examen",
                "custom": "✏️ Mis Tarjetas",
                "both": "🔀 Ambas"
            }[x],
            key="fc_source_selector"
        )

    # Get custom flashcards count
    custom_cards_df = get_custom_flashcards(st.session_state.username)
    custom_count = len(custom_cards_df)

    if source in ["custom", "both"] and custom_count == 0:
        st.warning("⚠️ No tienes tarjetas personalizadas. Ve a **Mis Tarjetas** para crearlas.")
        return

    with col2:
        # Topic filter for questions
        if source in ["questions", "both"]:
            topics = sorted(questions_df["topic"].unique().to_list())
            selected_topics = st.multiselect(
                "Filtrar por temas:",
                options=topics,
                default=None,
                key="fc_topics_selector"
            )
        else:
            selected_topics = None

    # Filter cards based on selection
    question_cards = []
    custom_cards = []

    if source in ["questions", "both"]:
        if selected_topics:
            filtered_df = questions_df.filter(pl.col("topic").is_in(selected_topics))
        else:
            filtered_df = questions_df
        question_cards = list(questions_dict.values())[:len(filtered_df)]

    if source in ["custom", "both"]:
        custom_cards = custom_cards_df.to_dicts()

    total_available = len(question_cards) + len(custom_cards)

    num_cards = st.number_input(
        "📊 Número de tarjetas:",
        min_value=5,
        max_value=min(100, total_available),
        value=min(20, total_available),
        step=5
    )

    st.caption(f"📊 {total_available} tarjetas disponibles ({len(question_cards)} del examen + {len(custom_cards)} personalizadas)")

    st.markdown("")

    if st.button("🚀 Comenzar Estudio", type="primary", use_container_width=True):
        # Combine and sample cards
        all_cards = []

        if source in ["questions", "both"]:
            sampled_q = questions_df.sample(min(num_cards, len(filtered_df)))["question_id"].to_list()
            all_cards.extend([{**questions_dict[qid], "is_custom": False} for qid in sampled_q])

        if source in ["custom", "both"]:
            remaining = num_cards - len(all_cards)
            if remaining > 0 and len(custom_cards) > 0:
                sampled_c = custom_cards_df.sample(min(remaining, len(custom_cards_df))).to_dicts()
                all_cards.extend([{**card, "is_custom": True} for card in sampled_c])

        # Shuffle combined deck
        import random
        random.shuffle(all_cards)

        st.session_state.fc_deck = all_cards[:num_cards]
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
    st.markdown("---")

    init_flashcard_state()
    questions_df, questions_dict = load_questions()

    # Sidebar: Flashcard stats only
    with st.sidebar:
        show_flashcard_stats_sidebar(st.session_state.username)
        st.divider()
        show_logout_button()

    if not st.session_state.fc_deck:
        setup_deck(questions_df, questions_dict)
    else:
        deck = st.session_state.fc_deck
        current_idx = st.session_state.fc_current_idx

        # Progress
        progress = (current_idx + 1) / len(deck)
        st.progress(progress, text=f"📝 Tarjeta {current_idx + 1} de {len(deck)}")

        st.markdown("---")

        # Show current card
        current_card = deck[current_idx]
        is_custom = current_card.get("is_custom", False)

        if is_custom:
            st.caption("✏️ Tarjeta Personalizada")
        else:
            st.caption("🎯 Pregunta del Examen")

        show_flashcard(current_card, is_custom=is_custom)

        # Reset deck button
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Nueva Ronda", type="secondary", use_container_width=True):
                st.session_state.fc_deck = []
                st.rerun()
        with col2:
            if st.button("✏️ Gestionar Mis Tarjetas", use_container_width=True):
                st.switch_page("pages/6_✏️_Mis_Tarjetas.py")


if __name__ == "__main__":
    main()
