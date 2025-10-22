"""
Exam Questions Page - Quiz modes
"""

import streamlit as st
import polars as pl
from plotnine import *

from database import (
    save_answer,
    get_user_stats,
    get_answered_questions,
    get_stats_by_topic,
    reset_user_progress,
)


# ============================================================================
# Session State Management
# ============================================================================


def init_quiz_state():
    """Initialize quiz-specific session state"""
    defaults = {
        "current_question_idx": 0,
        "answered": False,
        "selected_answer": None,
        "exam_mode": False,
        "exam_questions": [],
        "exam_answers": [],
        "exam_started": False,
        "show_stats": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_question_state():
    """Reset state for new question"""
    st.session_state.answered = False
    st.session_state.selected_answer = None


# ============================================================================
# Quiz Modes
# ============================================================================


def practice_mode(questions_df: pl.DataFrame, questions_dict: dict):
    """Random practice mode with immediate feedback"""
    st.header("📚 Práctica Aleatoria")

    show_unanswered = st.sidebar.checkbox("Solo preguntas no respondidas", value=False)

    if show_unanswered:
        answered_ids = get_answered_questions(st.session_state.username)
        available_df = questions_df.filter(~pl.col("question_id").is_in(list(answered_ids)))

        if len(available_df) == 0:
            st.success("🎉 ¡Has respondido todas las preguntas!")
            if st.button("Reiniciar progreso"):
                reset_user_progress(st.session_state.username)
                st.rerun()
            return
    else:
        available_df = questions_df

    if "current_question" not in st.session_state or st.session_state.get("refresh_question"):
        sampled_id = available_df.sample(1)["question_id"][0]
        st.session_state.current_question = questions_dict[sampled_id]
        st.session_state.refresh_question = False
        reset_question_state()

    display_question(st.session_state.current_question, mode="practice")


def topic_mode(questions_df: pl.DataFrame, questions_dict: dict):
    """Practice by specific topic"""
    st.header("📖 Práctica por Tema")

    topics = sorted(questions_df["topic"].unique().to_list())
    selected_topic = st.sidebar.selectbox("Selecciona un tema:", options=topics, key="topic_selector")

    if "selected_topic" not in st.session_state or st.session_state.selected_topic != selected_topic:
        st.session_state.selected_topic = selected_topic
        st.session_state.refresh_question = True
        if "current_question" in st.session_state:
            del st.session_state.current_question

    topic_df = questions_df.filter(pl.col("topic") == selected_topic)
    st.info(f"📊 **{len(topic_df)} preguntas** disponibles en este tema")

    answered_ids = get_answered_questions(st.session_state.username)
    topic_answered = topic_df.filter(pl.col("question_id").is_in(list(answered_ids)))

    if len(topic_answered) > 0:
        st.caption(f"Has respondido {len(topic_answered)} preguntas de este tema")

    if "current_question" not in st.session_state or st.session_state.get("refresh_question"):
        sampled_id = topic_df.sample(1)["question_id"][0]
        st.session_state.current_question = questions_dict[sampled_id]
        st.session_state.refresh_question = False
        reset_question_state()

    display_question(st.session_state.current_question, mode="practice")


def exam_mode(questions_df: pl.DataFrame, questions_dict: dict):
    """Simulated exam mode"""
    st.header("🎯 Examen Simulado")

    if not st.session_state.exam_started:
        st.info(
            """
        **Modo Examen:**
        - Selecciona los temas a evaluar
        - Sin retroalimentación inmediata
        - Ver resultados al finalizar
        """
        )

        topics = sorted(questions_df["topic"].unique().to_list())
        selected_topics = st.multiselect(
            "Selecciona los temas para el examen (vacío = todos):",
            options=topics,
            default=None,
            key="exam_topics_selector"
        )

        if selected_topics:
            filtered_df = questions_df.filter(pl.col("topic").is_in(selected_topics))
            st.caption(f"📊 {len(filtered_df)} preguntas disponibles en los temas seleccionados")
        else:
            filtered_df = questions_df
            st.caption(f"📊 {len(filtered_df)} preguntas disponibles (todos los temas)")

        num_questions = st.number_input(
            "Número de preguntas:",
            min_value=10,
            max_value=min(100, len(filtered_df)),
            value=min(40, len(filtered_df)),
            step=10
        )

        if st.button("🚀 Iniciar Examen", type="primary"):
            sampled_ids = filtered_df.sample(num_questions)["question_id"].to_list()
            exam_qs = [questions_dict[qid] for qid in sampled_ids]
            st.session_state.exam_questions = exam_qs
            st.session_state.exam_answers = [None] * len(exam_qs)
            st.session_state.exam_is_correct = [None] * len(exam_qs)
            st.session_state.exam_started = True
            st.session_state.current_question_idx = 0
            st.rerun()
    else:
        run_exam()


def run_exam():
    """Run the exam session"""
    questions = st.session_state.exam_questions
    current_idx = st.session_state.current_question_idx

    progress = (current_idx + 1) / len(questions)
    st.progress(progress, text=f"Pregunta {current_idx + 1} de {len(questions)}")

    question = questions[current_idx]

    st.subheader(f"Pregunta {current_idx + 1}")
    st.write(question["question_text"])

    options = {opt["letter"]: opt["text"] for opt in question["answer_options"]}

    selected = st.radio(
        "Selecciona tu respuesta:",
        options=options.keys(),
        format_func=lambda x: f"{x} {options[x]}",
        key=f"exam_q_{current_idx}",
        index=(
            None
            if st.session_state.exam_answers[current_idx] is None
            else list(options.keys()).index(st.session_state.exam_answers[current_idx])
        ),
    )

    if selected:
        st.session_state.exam_answers[current_idx] = selected

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if current_idx > 0:
            if st.button("⬅️ Anterior"):
                st.session_state.current_question_idx -= 1
                st.rerun()

    with col2:
        if current_idx < len(questions) - 1:
            if st.button("➡️ Siguiente"):
                st.session_state.current_question_idx += 1
                st.rerun()

    with col3:
        if current_idx == len(questions) - 1:
            if st.button("✅ Finalizar", type="primary"):
                show_exam_results()
                st.session_state.exam_started = False


def show_exam_results():
    """Display exam results"""
    questions = st.session_state.exam_questions
    answers = st.session_state.exam_answers

    correct_count = 0
    results = []

    for i, (question, user_answer) in enumerate(zip(questions, answers)):
        correct_opt = next(opt for opt in question["answer_options"] if opt["is_correct"])
        is_correct = user_answer == correct_opt["letter"]

        if is_correct:
            correct_count += 1

        save_answer(st.session_state.username, question["question_id"], user_answer or "N/A", is_correct)

        results.append(
            {
                "question_num": i + 1,
                "user_answer": user_answer,
                "correct_answer": correct_opt["letter"],
                "is_correct": is_correct,
                "question": question,
            }
        )

    st.balloons()
    st.success(f"## 🎉 Examen Finalizado")

    score_pct = (correct_count / len(questions)) * 100
    st.metric("Puntaje", f"{correct_count}/{len(questions)}", f"{score_pct:.1f}%")

    if score_pct >= 70:
        st.success("✅ ¡Excelente! Estás bien preparada")
    elif score_pct >= 50:
        st.info("📚 Buen trabajo, sigue practicando")
    else:
        st.warning("💪 Necesitas más práctica en algunos temas")

    with st.expander("📋 Ver Respuestas Detalladas"):
        for result in results:
            q = result["question"]
            icon = "✅" if result["is_correct"] else "❌"

            st.markdown(f"### {icon} Pregunta {result['question_num']}")
            st.write(q["question_text"])
            st.write(f"**Tu respuesta:** {result['user_answer']}")
            st.write(f"**Respuesta correcta:** {result['correct_answer']}")

            if not result["is_correct"]:
                st.info(f"**Explicación:** {q['explanation']}")

            st.divider()


# ============================================================================
# Question Display
# ============================================================================


def display_question(question: dict, mode: str = "practice"):
    """Display question with answer options"""
    st.subheader(f"Pregunta #{question.get('question_number', question['question_id'])}")
    st.write(question["question_text"])

    options = {opt["letter"]: opt["text"] for opt in question["answer_options"]}

    selected = st.radio(
        "Selecciona tu respuesta:",
        options=options.keys(),
        format_func=lambda x: f"{x} {options[x]}",
        disabled=st.session_state.answered,
        key=f"answer_{question['question_id']}",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Verificar", disabled=st.session_state.answered, type="primary"):
            st.session_state.answered = True
            st.session_state.selected_answer = selected

            correct_opt = next(opt for opt in question["answer_options"] if opt["is_correct"])
            is_correct = selected == correct_opt["letter"]

            save_answer(st.session_state.username, question["question_id"], selected, is_correct)

            st.rerun()

    with col2:
        if st.button("➡️ Siguiente"):
            if selected and not st.session_state.answered:
                correct_opt = next(opt for opt in question["answer_options"] if opt["is_correct"])
                is_correct = selected == correct_opt["letter"]
                save_answer(st.session_state.username, question["question_id"], selected, is_correct)

            st.session_state.refresh_question = True
            st.rerun()

    if st.session_state.answered:
        correct_opt = next(opt for opt in question["answer_options"] if opt["is_correct"])

        if st.session_state.selected_answer == correct_opt["letter"]:
            st.success("✅ ¡Correcto!")
        else:
            st.error(f"❌ Incorrecto. La respuesta correcta es: **{correct_opt['letter']} {correct_opt['text']}**")

        st.info(f"**📖 Explicación:** {question['explanation']}")

        if "source_exam" in question:
            st.caption(f"*Fuente: {question['source_exam']}*")


# ============================================================================
# Statistics Dashboard
# ============================================================================


def show_statistics(questions_df: pl.DataFrame):
    """Display user statistics dashboard"""
    st.header("📊 Estadísticas")

    stats = get_user_stats(st.session_state.username)

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
            viz_data = topic_stats.with_columns([
                pl.col("correct").alias("Correctas"),
                (pl.col("total") - pl.col("correct")).alias("Incorrectas")
            ]).select(["topic", "Correctas", "Incorrectas"])

            plot_data = pl.concat([
                viz_data.select(["topic", "Correctas"]).rename({"Correctas": "count"}).with_columns(pl.lit("Correctas").alias("type")),
                viz_data.select(["topic", "Incorrectas"]).rename({"Incorrectas": "count"}).with_columns(pl.lit("Incorrectas").alias("type"))
            ])

            plot_df = plot_data.to_pandas()

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

            display_df = topic_stats.select(
                [
                    pl.col("topic").alias("Tema"),
                    pl.col("total").alias("Total"),
                    pl.col("correct").alias("Correctas"),
                    pl.col("accuracy").round(1).alias("Precisión %"),
                ]
            )

            st.dataframe(display_df, use_container_width=True, hide_index=True)

            weakest = topic_stats.head(3)

            st.subheader("🎯 Temas a Reforzar")
            for row in weakest.iter_rows(named=True):
                st.write(f"- **{row['topic']}**: {row['accuracy']:.1f}% ({row['correct']}/{row['total']})")
    else:
        st.info("Aún no has respondido ninguna pregunta. ¡Comienza a practicar!")

    st.divider()
    if st.button("🔄 Reiniciar Todo el Progreso", type="secondary"):
        if st.checkbox("⚠️ Confirmar reinicio (esta acción no se puede deshacer)"):
            reset_user_progress(st.session_state.username)
            st.success("Progreso reiniciado exitosamente")
            st.rerun()


# ============================================================================
# Main Page Function
# ============================================================================


def show_exam_questions_page(questions_df: pl.DataFrame, questions_dict: dict):
    """Main entry point for exam questions page"""
    init_quiz_state()

    st.sidebar.divider()

    mode = st.sidebar.radio(
        "Modo de Estudio",
        ["📚 Práctica Aleatoria", "📖 Por Tema", "🎯 Examen Simulado", "📊 Estadísticas"],
        label_visibility="collapsed",
    )

    if mode == "📚 Práctica Aleatoria":
        practice_mode(questions_df, questions_dict)
    elif mode == "📖 Por Tema":
        topic_mode(questions_df, questions_dict)
    elif mode == "🎯 Examen Simulado":
        exam_mode(questions_df, questions_dict)
    elif mode == "📊 Estadísticas":
        show_statistics(questions_df)
