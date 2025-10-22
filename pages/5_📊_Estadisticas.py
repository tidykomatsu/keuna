"""
Statistics Dashboard
"""

import streamlit as st
import polars as pl
from plotnine import *

from auth import require_auth
from database import get_user_stats, get_stats_by_topic, reset_user_progress
from utils import load_questions

# ============================================================================
# Page Config
# ============================================================================

st.set_page_config(
    page_title="Estadísticas",
    page_icon="📊",
    layout="wide"
)

require_auth()

# ============================================================================
# Main Page Logic
# ============================================================================

def main():
    """Statistics dashboard"""
    st.title("📊 Estadísticas de Progreso")

    questions_df, _ = load_questions()
    stats = get_user_stats(st.session_state.username)

    # Overall metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Preguntas Respondidas", stats["total_answered"])

    with col2:
        st.metric("Respuestas Correctas", stats["total_correct"])

    with col3:
        st.metric("Precisión", f"{stats['accuracy']:.1f}%")

    st.divider()

    if stats["total_answered"] > 0:
        st.subheader("📚 Rendimiento por Tema")

        topic_stats = get_stats_by_topic(st.session_state.username, questions_df)

        if len(topic_stats) > 0:
            # Prepare data for visualization
            viz_data = topic_stats.with_columns([
                pl.col("correct").alias("Correctas"),
                (pl.col("total") - pl.col("correct")).alias("Incorrectas")
            ]).select(["topic", "Correctas", "Incorrectas"])

            # Transform to long format for plotnine
            plot_data = pl.concat([
                viz_data.select(["topic", "Correctas"]).rename({"Correctas": "count"}).with_columns(
                    pl.lit("Correctas").alias("type")),
                viz_data.select(["topic", "Incorrectas"]).rename({"Incorrectas": "count"}).with_columns(
                    pl.lit("Incorrectas").alias("type"))
            ])

            plot_df = plot_data.to_pandas()

            # Create chart
            p = (
                    ggplot(plot_df, aes(x='topic', y='count', fill='type'))
                    + geom_bar(stat='identity', position='dodge', width=0.7)
                    + scale_fill_manual(values={'Correctas': '#2ecc71', 'Incorrectas': '#e74c3c'})
                    + labs(
                title='Respuestas Correctas vs Incorrectas por Tema',
                x='Tema',
                y='Cantidad de Respuestas',
                fill='Tipo'
            )
                    + theme_classic()
                    + theme(
                figure_size=(12, 6),
                axis_text_x=element_text(angle=45, hjust=1),
                plot_title=element_text(size=14, weight='bold'),
                legend_position='top'
            )
            )

            st.pyplot(ggplot.draw(p))

            st.divider()

            # Table view
            display_df = topic_stats.select(
                [
                    pl.col("topic").alias("Tema"),
                    pl.col("total").alias("Total"),
                    pl.col("correct").alias("Correctas"),
                    pl.col("accuracy").round(1).alias("Precisión %"),
                ]
            )

            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # Weakest topics
            weakest = topic_stats.head(3)

            st.subheader("🎯 Temas a Reforzar")
            for row in weakest.iter_rows(named=True):
                st.write(f"- **{row['topic']}**: {row['accuracy']:.1f}% ({row['correct']}/{row['total']})")
    else:
        st.info("Aún no has respondido ninguna pregunta. ¡Comienza a practicar!")

    # Reset progress
    st.divider()
    if st.button("🔄 Reiniciar Todo el Progreso", type="secondary"):
        if st.checkbox("⚠️ Confirmar reinicio (esta acción no se puede deshacer)"):
            reset_user_progress(st.session_state.username)
            st.success("Progreso reiniciado exitosamente")
            st.rerun()


if __name__ == "__main__":
    main()
