"""
Simulated Exam Mode
"""

import streamlit as st
import polars as pl

from auth import require_auth
from database import save_answer, get_user_stats
from utils import load_questions

# ============================================================================
# Page Config
# ============================================================================

st.set_page_config(
    page_title="Examen Simulado",
    page_icon="🎯",
    layout="centered"
)

require_auth()

# ============================================================================
# Session State
# ============================================================================

def init_exam_state():
    """Initialize exam state"""
    defaults = {
        "exam_started": False,
        "exam_questions": [],
        "exam_answers": [],
        "current_question_idx": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ============================================================================
# Exam Setup
# ============================================================================

def show_exam_setup(questions_df, questions_dict):
    """Display exam configuration"""
    st.info("""
    **Modo Examen:**
    - Selecciona los temas a evaluar
    - Sin retroalimentación inmediata
    - Ver resultados al finalizar
    """)

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
        st.session_state.exam_started = True
        st.session_state.current_question_idx = 0
        st.rerun()

# ============================================================================
# Run Exam
# ============================================================================

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

# ============================================================================
# Exam Results
# ============================================================================

def show_exam_results():
    """Display exam results"""
    questions = st.session_state.exam_questions
    answers = st.session_state.exam_answers

    correct_count = 0
    results = []

    for i, (question, user_answer) in enumerate(zip(questions, answers)):
        correct_opt = next(opt for opt in question["answer_options"] if opt["is_correct"])
        is_correct = user_answer == correct_opt["letter"] if user_answer else False

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
            st.write(f"**Tu respuesta:** {result['user_answer'] or 'No contestada'}")
            st.write(f"**Respuesta correcta:** {result['correct_answer']}")

            if not result["is_correct"]:
                st.info(f"**Explicación:** {q['explanation']}")

            st.divider()

    # Reset exam button
    if st.button("🔄 Nuevo Examen"):
        st.session_state.exam_started = False
        st.session_state.exam_questions = []
        st.session_state.exam_answers = []
        st.session_state.current_question_idx = 0
        st.rerun()

# ============================================================================
# Main Page Logic
# ============================================================================

def main():
    """Simulated exam mode"""
    st.title("🎯 Examen Simulado")

    init_exam_state()
    questions_df, questions_dict = load_questions()

    # Sidebar stats
    stats = get_user_stats(st.session_state.username)
    st.sidebar.metric("Preguntas respondidas", stats["total_answered"])
    st.sidebar.metric("Precisión", f"{stats['accuracy']:.1f}%")

    if not st.session_state.exam_started:
        show_exam_setup(questions_df, questions_dict)
    else:
        run_exam()


if __name__ == "__main__":
    main()
