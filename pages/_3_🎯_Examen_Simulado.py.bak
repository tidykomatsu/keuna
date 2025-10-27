"""
Simulated Exam Mode - Polished
"""

import streamlit as st
import polars as pl

from src.auth import require_auth, show_logout_button
from src.database import save_answer, get_user_stats
from src.utils import load_questions

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
        "exam_finished": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ============================================================================
# Exam Setup
# ============================================================================

def show_exam_setup(questions_df, questions_dict):
    """Display exam configuration"""

    st.markdown("### ⚙️ Configuración del Examen")
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        topics = sorted(questions_df["topic"].unique().to_list())
        selected_topics = st.multiselect(
            "🎯 Selecciona temas (vacío = todos):",
            options=topics,
            default=None,
            key="exam_topics_selector"
        )

    with col2:
        if selected_topics:
            filtered_df = questions_df.filter(pl.col("topic").is_in(selected_topics))
        else:
            filtered_df = questions_df

        num_questions = st.number_input(
            "📊 Número de preguntas:",
            min_value=10,
            max_value=min(100, len(filtered_df)),
            value=min(40, len(filtered_df)),
            step=10
        )

    st.caption(f"📊 {len(filtered_df)} preguntas disponibles en tu selección")

    st.markdown("")

    if st.button("🚀 Iniciar Examen", type="primary", use_container_width=True):
        sampled_ids = filtered_df.sample(num_questions)["question_id"].to_list()
        exam_qs = [questions_dict[qid] for qid in sampled_ids]
        st.session_state.exam_questions = exam_qs
        st.session_state.exam_answers = [None] * len(exam_qs)
        st.session_state.exam_started = True
        st.session_state.exam_finished = False
        st.session_state.current_question_idx = 0
        st.rerun()

# ============================================================================
# Run Exam
# ============================================================================

def run_exam():
    """Run the exam session"""
    questions = st.session_state.exam_questions
    current_idx = st.session_state.current_question_idx

    # Progress bar
    progress = (current_idx + 1) / len(questions)
    st.progress(progress, text=f"📝 Pregunta {current_idx + 1} de {len(questions)}")

    st.markdown("---")

    question = questions[current_idx]

    # Question display
    st.markdown(f"### Pregunta {current_idx + 1}")
    st.markdown(f"**{question['question_text']}**")
    st.markdown("")

    options = {opt["letter"]: opt["text"] for opt in question["answer_options"]}

    selected = st.radio(
        "Selecciona tu respuesta:",
        options=options.keys(),
        format_func=lambda x: f"**{x}** {options[x]}",
        key=f"exam_q_{current_idx}",
        index=(
            None
            if st.session_state.exam_answers[current_idx] is None
            else list(options.keys()).index(st.session_state.exam_answers[current_idx])
        ),
    )

    if selected:
        st.session_state.exam_answers[current_idx] = selected

    st.markdown("")

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if current_idx > 0:
            if st.button("⬅️ Anterior", use_container_width=True):
                st.session_state.current_question_idx -= 1
                st.rerun()

    with col2:
        if current_idx < len(questions) - 1:
            if st.button("➡️ Siguiente", use_container_width=True):
                st.session_state.current_question_idx += 1
                st.rerun()

    with col3:
        if current_idx == len(questions) - 1:
            answered_count = sum(1 for a in st.session_state.exam_answers if a is not None)
            if answered_count < len(questions):
                st.warning(f"⚠️ Faltan {len(questions) - answered_count} preguntas")

            if st.button("✅ Finalizar", type="primary", use_container_width=True):
                st.session_state.exam_finished = True
                st.rerun()

    # Sidebar: Answer overview
    with st.sidebar:
        st.markdown("### 📋 Vista General")
        st.caption(f"Respondidas: {sum(1 for a in st.session_state.exam_answers if a is not None)}/{len(questions)}")

        st.divider()

        # Quick navigation grid
        st.markdown("**Ir a pregunta:**")
        cols_per_row = 5
        for i in range(0, len(questions), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                idx = i + j
                if idx < len(questions):
                    answered = st.session_state.exam_answers[idx] is not None
                    btn_type = "primary" if answered else "secondary"
                    if col.button(f"{idx + 1}", key=f"nav_{idx}", type=btn_type, use_container_width=True):
                        st.session_state.current_question_idx = idx
                        st.rerun()

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
                "correct_text": correct_opt["text"],
                "is_correct": is_correct,
                "question": question,
            }
        )

    # Celebration
    st.balloons()

    st.markdown("# 🎉 Examen Finalizado")
    st.markdown("---")

    # Score display
    score_pct = (correct_count / len(questions)) * 100

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Preguntas", len(questions))
    with col2:
        st.metric("Respuestas Correctas", correct_count)
    with col3:
        st.metric("Puntaje", f"{score_pct:.1f}%")

    st.markdown("")

    # Performance feedback
    if score_pct >= 70:
        st.success("### ✅ ¡Excelente! Estás bien preparada")
    elif score_pct >= 50:
        st.info("### 📚 Buen trabajo, sigue practicando")
    else:
        st.warning("### 💪 Necesitas más práctica en algunos temas")

    st.markdown("---")

    # Detailed results
    with st.expander("📋 Ver Respuestas Detalladas", expanded=False):
        for result in results:
            q = result["question"]
            icon = "✅" if result["is_correct"] else "❌"

            st.markdown(f"### {icon} Pregunta {result['question_num']}")
            st.markdown(f"**{q['question_text']}**")
            st.markdown("")

            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**Tu respuesta:** {result['user_answer'] or 'No contestada'}")
            with col2:
                st.success(f"**Correcta:** {result['correct_answer']} {result['correct_text']}")

            if not result["is_correct"]:
                st.markdown(f"**📖 Explicación:** {q['explanation']}")

            st.divider()

    st.markdown("---")

    # Reset button
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔄 Nuevo Examen", use_container_width=True, type="primary"):
            st.session_state.exam_started = False
            st.session_state.exam_finished = False
            st.session_state.exam_questions = []
            st.session_state.exam_answers = []
            st.session_state.current_question_idx = 0
            st.rerun()

    with col2:
        if st.button("🏠 Volver al Inicio", use_container_width=True):
            st.session_state.exam_started = False
            st.session_state.exam_finished = False
            st.switch_page("app.py")

# ============================================================================
# Main Page Logic
# ============================================================================

def main():
    """Simulated exam mode"""
    st.title("🎯 Examen Simulado")

    if "exam_finished" not in st.session_state:
        st.session_state.exam_finished = False

    init_exam_state()
    questions_df, questions_dict = load_questions()

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
        show_logout_button()

    if st.session_state.exam_finished:
        show_exam_results()
    elif not st.session_state.exam_started:
        show_exam_setup(questions_df, questions_dict)
    else:
        run_exam()


if __name__ == "__main__":
    main()
