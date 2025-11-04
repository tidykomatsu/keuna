"""
Custom Flashcards Management - CRUD Interface
"""

import streamlit as st
import polars as pl
from datetime import datetime

from src.auth import require_auth, show_logout_button
from src.database import (
    create_custom_flashcard,
    get_custom_flashcards,
    update_custom_flashcard,
    archive_custom_flashcard,
    export_custom_flashcards_json,
    import_custom_flashcards_json,
    get_user_stats
)
from src.utils import load_questions

# ============================================================================
# Page Config
# ============================================================================

st.set_page_config(
    page_title="Mis Tarjetas",
    page_icon="✏️",
    layout="centered"
)

# Modern UI styling
st.markdown(
    """
    <style>
        /* Make UI bigger and more modern */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 900px;
        }
        h1 {
            font-size: 3rem !important;
            margin-bottom: 1.5rem !important;
        }
        h2, h3 {
            font-size: 2rem !important;
            margin-top: 1.5rem !important;
            margin-bottom: 1rem !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 2rem !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 1.2rem !important;
        }
        .stButton button {
            font-size: 1.3rem !important;
            padding: 1rem 1.5rem !important;
            height: auto !important;
            min-height: 3.5rem !important;
            border-radius: 10px !important;
        }
        p, div, span, label {
            font-size: 1.1rem !important;
        }
        .stTextInput input, .stTextArea textarea {
            font-size: 1.1rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

require_auth()

# ============================================================================
# Session State
# ============================================================================

def init_state():
    """Initialize page state"""
    defaults = {
        "editing_card_id": None,
        "show_create_form": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ============================================================================
# Create Form
# ============================================================================

def show_create_form():
    """Display form to create new flashcard"""
    st.markdown("### ➕ Crear Nueva Tarjeta")

    with st.form("create_flashcard_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            front_text = st.text_area(
                "📝 Pregunta / Frente:",
                placeholder="¿Cuál es la capital de Chile?",
                height=100,
                help="El contenido que aparecerá en el frente de la tarjeta"
            )

        with col2:
            back_text = st.text_area(
                "✅ Respuesta / Reverso:",
                placeholder="Santiago",
                height=100,
                help="El contenido que aparecerá en el reverso de la tarjeta"
            )

        # Get available topics from questions
        questions_df, _ = load_questions()
        topics = [""] + sorted(questions_df["topic"].unique().to_list())

        topic = st.selectbox(
            "📚 Tema (opcional):",
            options=topics,
            help="Agrupa tus tarjetas por tema para organizarlas mejor"
        )

        col1, col2 = st.columns(2)

        with col1:
            submit = st.form_submit_button("➕ Crear Tarjeta", type="primary", use_container_width=True)

        with col2:
            cancel = st.form_submit_button("❌ Cancelar", use_container_width=True)

        if submit:
            if not front_text or not back_text:
                st.error("⚠️ Debes completar ambos campos (pregunta y respuesta)")
            else:
                topic_val = topic if topic else None
                success = create_custom_flashcard(
                    st.session_state.username,
                    front_text.strip(),
                    back_text.strip(),
                    topic_val
                )

                if success:
                    st.success("✅ Tarjeta creada exitosamente!")
                    st.session_state.show_create_form = False
                    st.rerun()
                else:
                    st.error("❌ Error: Ya existe una tarjeta con esa pregunta")

        if cancel:
            st.session_state.show_create_form = False
            st.rerun()

# ============================================================================
# Edit Form
# ============================================================================

def show_edit_form(card: dict):
    """Display form to edit existing flashcard"""
    st.markdown("### ✏️ Editar Tarjeta")

    with st.form("edit_flashcard_form"):
        col1, col2 = st.columns(2)

        with col1:
            front_text = st.text_area(
                "📝 Pregunta / Frente:",
                value=card["front_text"],
                height=100
            )

        with col2:
            back_text = st.text_area(
                "✅ Respuesta / Reverso:",
                value=card["back_text"],
                height=100
            )

        # Get available topics
        questions_df, _ = load_questions()
        topics = [""] + sorted(questions_df["topic"].unique().to_list())

        current_topic = card.get("topic") or ""
        topic_index = topics.index(current_topic) if current_topic in topics else 0

        topic = st.selectbox(
            "📚 Tema (opcional):",
            options=topics,
            index=topic_index
        )

        col1, col2 = st.columns(2)

        with col1:
            submit = st.form_submit_button("💾 Guardar Cambios", type="primary", use_container_width=True)

        with col2:
            cancel = st.form_submit_button("❌ Cancelar", use_container_width=True)

        if submit:
            if not front_text or not back_text:
                st.error("⚠️ Debes completar ambos campos")
            else:
                topic_val = topic if topic else None
                success = update_custom_flashcard(
                    card["id"],
                    front_text.strip(),
                    back_text.strip(),
                    topic_val
                )

                if success:
                    st.success("✅ Tarjeta actualizada exitosamente!")
                    st.session_state.editing_card_id = None
                    st.rerun()
                else:
                    st.error("❌ Error al actualizar la tarjeta")

        if cancel:
            st.session_state.editing_card_id = None
            st.rerun()

# ============================================================================
# Card List
# ============================================================================

def show_cards_list(cards_df: pl.DataFrame):
    """Display list of flashcards with edit/delete options"""

    if len(cards_df) == 0:
        st.info("""
        📝 **No tienes tarjetas personalizadas aún**

        Crea tu primera tarjeta usando el botón de arriba.
        Las tarjetas personalizadas son perfectas para:
        - Repasar conceptos específicos
        - Agregar notas propias
        - Crear resúmenes personalizados
        """)
        return

    st.markdown(f"### 📚 Mis Tarjetas ({len(cards_df)})")

    # Group by topic
    topics = cards_df.get_column("topic").unique().to_list()
    topics_with_cards = [t for t in topics if t is not None]

    if None in topics:
        topics_with_cards.append("Sin tema")

    if len(topics_with_cards) > 1:
        topic_filter = st.selectbox(
            "Filtrar por tema:",
            options=["Todos"] + sorted([t for t in topics_with_cards if t != "Sin tema"]) + (["Sin tema"] if "Sin tema" in topics_with_cards else [])
        )

        if topic_filter != "Todos":
            if topic_filter == "Sin tema":
                cards_df = cards_df.filter(pl.col("topic").is_null())
            else:
                cards_df = cards_df.filter(pl.col("topic") == topic_filter)

    st.markdown("---")

    # Display cards
    cards = cards_df.to_dicts()

    for card in cards:
        with st.container():
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**📝 {card['front_text'][:80]}{'...' if len(card['front_text']) > 80 else ''}**")
                st.caption(f"✅ {card['back_text'][:80]}{'...' if len(card['back_text']) > 80 else ''}")

                if card.get("topic"):
                    st.caption(f"📚 Tema: {card['topic']}")

            with col2:
                if st.button("✏️ Editar", key=f"edit_{card['id']}", use_container_width=True):
                    st.session_state.editing_card_id = card["id"]
                    st.rerun()

                if st.button("🗑️ Eliminar", key=f"delete_{card['id']}", use_container_width=True, type="secondary"):
                    st.session_state[f"confirm_delete_{card['id']}"] = True
                    st.rerun()

                # Confirmation dialog
                if st.session_state.get(f"confirm_delete_{card['id']}", False):
                    st.warning("⚠️ ¿Confirmar eliminación?")
                    col_yes, col_no = st.columns(2)

                    with col_yes:
                        if st.button("Sí", key=f"confirm_yes_{card['id']}", type="primary", use_container_width=True):
                            archive_custom_flashcard(card["id"])
                            st.success("✅ Tarjeta eliminada")
                            del st.session_state[f"confirm_delete_{card['id']}"]
                            st.rerun()

                    with col_no:
                        if st.button("No", key=f"confirm_no_{card['id']}", use_container_width=True):
                            del st.session_state[f"confirm_delete_{card['id']}"]
                            st.rerun()

            st.divider()

# ============================================================================
# Export/Import
# ============================================================================

def show_export_import():
    """Display export/import functionality"""
    st.markdown("### 💾 Exportar / Importar")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📥 Exportar")
        if st.button("💾 Descargar mis tarjetas (JSON)", use_container_width=True, type="primary"):
            json_data = export_custom_flashcards_json(st.session_state.username)

            if json_data == "[]":
                st.warning("No tienes tarjetas para exportar")
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"tarjetas_{st.session_state.username}_{timestamp}.json"

                st.download_button(
                    label="⬇️ Descargar archivo",
                    data=json_data,
                    file_name=filename,
                    mime="application/json",
                    use_container_width=True
                )

    with col2:
        st.markdown("#### 📤 Importar")
        uploaded_file = st.file_uploader(
            "Selecciona archivo JSON:",
            type=["json"],
            help="Sube un archivo JSON previamente exportado"
        )

        if uploaded_file is not None:
            try:
                json_data = uploaded_file.read().decode("utf-8")
                success_count, error_count = import_custom_flashcards_json(
                    st.session_state.username,
                    json_data
                )

                st.success(f"✅ Importadas: {success_count} tarjetas")
                if error_count > 0:
                    st.warning(f"⚠️ Errores/Duplicadas: {error_count}")

                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al importar: {str(e)}")

# ============================================================================
# Main Page Logic
# ============================================================================

def main():
    """Custom flashcards management page"""
    st.title("✏️ Mis Tarjetas Personalizadas")
    st.markdown("---")

    init_state()

    # Sidebar stats
    with st.sidebar:
        st.markdown("### 📊 Tu Progreso General")
        stats = get_user_stats(st.session_state.username)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Respondidas", stats["total_answered"])
        with col2:
            st.metric("Precisión", f"{stats['accuracy']:.1f}%")

        st.divider()

        # Custom cards count
        cards_df = get_custom_flashcards(st.session_state.username)
        st.markdown("### ✏️ Mis Tarjetas")
        st.metric("Total", len(cards_df))

        st.divider()
        show_logout_button()

    # Main actions
    col1, col2 = st.columns(2)

    with col1:
        if st.button("➕ Nueva Tarjeta", type="primary", use_container_width=True):
            st.session_state.show_create_form = True
            st.session_state.editing_card_id = None
            st.rerun()

    with col2:
        if st.button("🎴 Estudiar con Tarjetas", use_container_width=True):
            st.switch_page("pages/4_🎴_Tarjetas.py")

    st.markdown("---")

    # Show appropriate view
    if st.session_state.show_create_form:
        show_create_form()
    elif st.session_state.editing_card_id is not None:
        cards_df = get_custom_flashcards(st.session_state.username)
        card = cards_df.filter(pl.col("id") == st.session_state.editing_card_id).to_dicts()[0]
        show_edit_form(card)
    else:
        cards_df = get_custom_flashcards(st.session_state.username)
        show_cards_list(cards_df)

        if len(cards_df) > 0:
            st.markdown("---")
            show_export_import()


if __name__ == "__main__":
    main()
