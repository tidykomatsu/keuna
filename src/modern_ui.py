"""
Modern UI Components for EUNACOM Quiz App
Leverages Streamlit native components with minimal custom CSS
"""

import streamlit as st
from src.database import get_user_stats, get_flashcard_stats, get_custom_flashcards


# ============================================================================
# MINIMAL CSS INJECTION
# ============================================================================

def inject_modern_css():
    """
    Inject minimal custom CSS - only where Streamlit native components fall short
    Keep this under 30 lines!
    """
    st.markdown(
        """
        <style>
        /* Font improvements */
        html, body, [class*="css"] {
            font-family: system-ui, -apple-system, sans-serif;
        }

        /* Remove excessive padding for compact layout */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 900px;
        }

        /* Button hover states */
        .stButton button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
            transition: all 0.2s ease;
        }

        /* Subtle borders for containers */
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================================
# REUSABLE COMPONENTS
# ============================================================================

def score_dashboard(correct: int, incorrect: int, total: int = None):
    """
    Display score metrics in a modern dashboard layout
    Uses native st.metric() with columns
    """
    if total is None:
        total = correct + incorrect

    accuracy = (correct / total * 100) if total > 0 else 0

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="✅ Correctas",
            value=correct,
            help="Total de respuestas correctas"
        )

    with col2:
        st.metric(
            label="❌ Incorrectas",
            value=incorrect,
            help="Total de respuestas incorrectas"
        )

    with col3:
        st.metric(
            label="📊 Precisión",
            value=f"{accuracy:.1f}%",
            delta=f"{total} total",
            help="Porcentaje de respuestas correctas"
        )


def topic_badge(topic: str, question_number: str = None):
    """
    Display topic badge using native components
    No custom CSS needed!
    """
    col1, col2 = st.columns([3, 1])

    with col1:
        st.caption(f"🏥 {topic}")

    if question_number:
        with col2:
            st.caption(f"Pregunta #{question_number}", help="Número de pregunta en la base de datos")


def question_card(question_text: str, question_number: str = None, topic: str = None):
    """
    Display question in a clean card using st.container(border=True)
    Completely native - no custom CSS!
    """
    with st.container(border=True):
        # Topic and question number header
        if topic or question_number:
            topic_badge(topic, question_number)
            st.divider()

        # Question text
        st.markdown(f"**{question_text}**")


def answer_feedback(is_correct: bool, user_answer: dict = None, correct_answer: dict = None,
                    explanation: str = None, topic_explanation: str = None, source: str = None):
    """
    Display answer feedback using native st.success/st.error/st.info
    No custom CSS cards needed!
    """
    if is_correct:
        st.success("🎉 ¡Correcto! Muy bien.", icon="✅")

        # Show explanation for correct answer
        if user_answer and user_answer.get("explanation"):
            with st.container(border=True):
                st.markdown("**💡 Explicación:**")
                st.markdown(user_answer["explanation"])
    else:
        st.error("❌ Incorrecto. Revisa la explicación.", icon="❌")

        # Show user's wrong answer explanation
        if user_answer and user_answer.get("explanation"):
            with st.container(border=True):
                st.markdown(f"**Tu respuesta:** {user_answer['letter']}. {user_answer['text']}")
                st.markdown(f"_{user_answer['explanation']}_")

        # Show correct answer
        if correct_answer:
            st.success("✅ Respuesta correcta:", icon="✅")
            with st.container(border=True):
                st.markdown(f"**{correct_answer['letter']}. {correct_answer['text']}**")
                if correct_answer.get("explanation"):
                    st.markdown(correct_answer["explanation"])

    # Full topic explanation (expandable)
    if topic_explanation:
        with st.expander("📖 Ver explicación completa del tema"):
            st.markdown(explanation or topic_explanation)

    # Source citation
    if source:
        st.caption(f"📚 Fuente: {source}")


def modern_answer_options(options: list[dict], key_prefix: str = "answer"):
    """
    Modern answer selection using buttons in columns
    Returns selected option or None
    """
    st.markdown("**Selecciona tu respuesta:**")

    # Display options in 2 columns for better layout
    col1, col2 = st.columns(2)

    selected = None

    for i, option in enumerate(options):
        col = col1 if i % 2 == 0 else col2

        with col:
            # Use container for each option
            with st.container(border=True):
                st.markdown(f"**{option['letter']}**")
                st.markdown(option['text'])

                if st.button(
                    f"Seleccionar {option['letter']}",
                    key=f"{key_prefix}_{option['letter']}",
                    use_container_width=True
                ):
                    selected = option

    return selected


# ============================================================================
# SIDEBAR COMPONENTS
# ============================================================================

def show_exam_stats_sidebar(username: str):
    """
    Display exam statistics in sidebar with clean hierarchy
    Uses native st.metric() for stats
    """
    with st.sidebar:
        st.markdown("### 📊 Tu Progreso")

        # Get stats
        stats = get_user_stats(username)

        # Display metrics
        st.metric(
            label="Total Respondidas",
            value=stats["total_answered"],
            help="Total de preguntas que has respondido"
        )

        st.metric(
            label="Precisión",
            value=f"{stats['accuracy']:.1f}%",
            delta=f"{stats['total_correct']} correctas",
            help="Porcentaje de respuestas correctas"
        )

        st.divider()

        # Settings expander
        with st.expander("⚙️ Configuración"):
            st.caption("Próximamente: opciones de configuración")

        st.divider()

        # Logout button
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


def show_flashcard_stats_sidebar(username: str):
    """
    Display flashcard statistics in sidebar
    """
    with st.sidebar:
        st.markdown("### 📊 Tu Progreso")

        # Get flashcard stats
        fc_stats = get_flashcard_stats(username)

        # Get custom flashcard count
        custom_cards_df = get_custom_flashcards(username)
        custom_count = len(custom_cards_df)

        # Display metrics
        st.metric(
            label="Tarjetas Revisadas",
            value=fc_stats["total_reviewed"],
            help="Total de tarjetas que has revisado"
        )

        if fc_stats["total_reviewed"] > 0:
            accuracy = (fc_stats["correct_count"] / fc_stats["total_reviewed"] * 100)
            st.metric(
                label="Recordadas",
                value=f"{accuracy:.1f}%",
                delta=f"{fc_stats['correct_count']} correctas",
                help="Porcentaje de tarjetas recordadas correctamente"
            )

        st.metric(
            label="✏️ Mis Tarjetas",
            value=custom_count,
            help="Tarjetas personalizadas que has creado"
        )

        st.divider()

        # Settings expander
        with st.expander("⚙️ Configuración"):
            st.caption("Próximamente: opciones de estudio")

        st.divider()

        # Logout button
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


def show_progress_bar(current: int, total: int, label: str = "Progreso"):
    """
    Display progress bar with percentage
    """
    if total > 0:
        progress = current / total
        st.progress(progress, text=f"{label}: {current}/{total} ({progress*100:.1f}%)")
    else:
        st.progress(0, text=f"{label}: 0/0")
