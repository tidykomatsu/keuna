"""
Statistics Dashboard - Simplified
"""

import streamlit as st
import polars as pl

from src.auth import require_auth, show_logout_button
from src.database import get_user_stats, get_stats_by_topic, reset_user_progress
from src.utils import load_questions
from src.modern_ui import inject_modern_css

# ============================================================================
# Page Config
# ============================================================================

st.set_page_config(
    page_title="Estadísticas",
    page_icon="📊",
    layout="wide"
)

inject_modern_css()
require_auth()

# ============================================================================
# Main Page Logic
# ============================================================================

def main():
    """Statistics dashboard"""
    st.title("📊 Estadísticas de Progreso")
    st.markdown("---")

    questions_df, _ = load_questions()
    stats = get_user_stats(st.session_state.username)

    # Overall metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📝 Total Respondidas", stats["total_answered"])

    with col2:
        st.metric("✅ Correctas", stats["total_correct"])

    with col3:
        incorrect = stats["total_answered"] - stats["total_correct"]
        st.metric("❌ Incorrectas", incorrect)

    with col4:
        st.metric("🎯 Precisión", f"{stats['accuracy']:.1f}%")

    st.divider()

    if stats["total_answered"] > 0:
        # Mastery levels
        st.subheader("🏆 Niveles de Dominio por Tema")
        st.markdown("*Basado en precisión y número de preguntas respondidas*")

        from src.question_selector import get_all_topic_masteries

        with st.spinner("Calculando niveles..."):
            mastery_df = get_all_topic_masteries(st.session_state.username)

        if len(mastery_df) > 0:
            for idx, row in enumerate(mastery_df.iter_rows(named=True)):
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

                with col1:
                    st.markdown(f"**{row['topic']}**")

                with col2:
                    st.markdown(f"{row['stars']}")

                with col3:
                    accuracy = row.get('accuracy', 0)
                    if accuracy >= 80:
                        st.success(f"{accuracy:.0f}%")
                    elif accuracy >= 60:
                        st.info(f"{accuracy:.0f}%")
                    else:
                        st.warning(f"{accuracy:.0f}%")

                with col4:
                    q_count = row.get('questions_answered', 0)
                    st.caption(f"{q_count} preguntas")

            st.markdown("")
            weakest = mastery_df.head(3)

            st.info(
                "**💡 Recomendación:** Enfócate en " +
                ", ".join([f"**{row['topic']}**" for row in weakest.iter_rows(named=True)]) +
                " para mejorar tu preparación."
            )
        else:
            st.info("Comienza a responder preguntas para ver tus niveles de dominio")

        st.divider()

        st.subheader("📚 Rendimiento por Tema")

        topic_stats = get_stats_by_topic(st.session_state.username, questions_df)

        if len(topic_stats) > 0:
            display_df = topic_stats.select(
                [
                    pl.col("topic").alias("Tema"),
                    pl.col("total").alias("Total"),
                    pl.col("correct").alias("Correctas"),
                    (pl.col("total") - pl.col("correct")).alias("Incorrectas"),
                    pl.col("accuracy").round(1).alias("Precisión %"),
                ]
            )

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Precisión %": st.column_config.ProgressColumn(
                        "Precisión %",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                    ),
                }
            )

    else:
        st.info("""
        ### 📚 Aún no has respondido ninguna pregunta

        ¡Comienza a practicar para ver tus estadísticas!

        **Sugerencias:**
        - Prueba el modo de **Práctica Aleatoria** para familiarizarte
        - Enfócate en un tema usando **Por Tema**
        """)

    # Reset progress section
    st.divider()
    st.markdown("### ⚠️ Zona de Peligro")

    with st.expander("🔄 Reiniciar Todo el Progreso"):
        st.warning("""
        **Atención:** Esta acción eliminará permanentemente:
        - Todas tus respuestas
        - Todas tus estadísticas
        - Todo tu historial de progreso
        """)

        confirm_text = st.text_input(
            "Escribe 'REINICIAR' para confirmar:",
            key="reset_confirm"
        )

        if st.button("🔄 Confirmar Reinicio", type="secondary"):
            if confirm_text == "REINICIAR":
                reset_user_progress(st.session_state.username)
                st.success("✅ Progreso reiniciado exitosamente")
                st.rerun()
            else:
                st.error("❌ Debes escribir 'REINICIAR' para confirmar")

    # Sidebar
    with st.sidebar:
        show_logout_button()


if __name__ == "__main__":
    main()
