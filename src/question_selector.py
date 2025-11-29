"""
Smart Question Selection Algorithm - ENHANCED VERSION
Prioritizes weakest topic first, then weighted selection within that topic
"""

import polars as pl
import random
from src.database import (
    get_all_questions,
    get_user_performance,
    get_topic_performance,
    get_answered_questions
)

# ============================================================================
# OPTIMIZED ADAPTIVE SELECTION WITH CACHING
# ============================================================================

def get_adaptive_weights(username: str, questions_df: pl.DataFrame) -> dict:
    """
    Calculate adaptive selection weights for all questions
    """
    performance_df = get_user_performance(username)

    if len(performance_df) == 0:
        return {q_id: 1.0 for q_id in questions_df["question_id"].to_list()}

    weights = {}
    for q_id in questions_df["question_id"].to_list():
        perf = performance_df.filter(pl.col("question_id") == q_id)

        if len(perf) == 0:
            weights[q_id] = 5.0
        else:
            priority = perf["priority_score"][0]
            weights[q_id] = max(priority, 0.1) if priority > 0 else 0.5

    return weights


def select_adaptive_cached(username: str, topic: str = None) -> dict:
    """
    Adaptive selection using cached weights
    """
    import streamlit as st

    questions_df = st.session_state.get('questions_df')
    if questions_df is None:
        questions_df = get_all_questions()
        st.session_state.questions_df = questions_df

    if topic:
        questions_df = questions_df.filter(pl.col("topic") == topic)

    if len(questions_df) == 0:
        return None

    if 'adaptive_weights' not in st.session_state:
        st.session_state.adaptive_weights = get_adaptive_weights(username, questions_df)
        st.session_state.questions_since_update = 0

    st.session_state.questions_since_update = st.session_state.get('questions_since_update', 0)

    if st.session_state.questions_since_update >= 20:
        st.session_state.adaptive_weights = get_adaptive_weights(username, questions_df)
        st.session_state.questions_since_update = 0

    st.session_state.questions_since_update += 1

    weights_dict = st.session_state.adaptive_weights
    available_ids = questions_df["question_id"].to_list()
    available_weights = [weights_dict.get(q_id, 1.0) for q_id in available_ids]

    total_weight = sum(available_weights)
    if total_weight == 0:
        return questions_df.sample(1).to_dicts()[0]

    normalized = [w / total_weight for w in available_weights]

    selected_id = random.choices(available_ids, weights=normalized, k=1)[0]

    questions_dict = st.session_state.get('questions_dict')
    if questions_dict is None:
        questions_dict = {row["question_id"]: dict(row) for row in questions_df.iter_rows(named=True)}
        st.session_state.questions_dict = questions_dict

    return questions_dict[selected_id]


# ============================================================================
# Topic Mastery Calculation
# ============================================================================

def calculate_topic_mastery(username: str, topic: str) -> dict:
    """Calculate mastery level for a topic (0-5 stars)"""
    topic_perf = get_topic_performance(username)

    if len(topic_perf) == 0:
        return {'level': 0, 'stars': '☆☆☆☆☆', 'progress': 0, 'status': 'Sin iniciar'}

    topic_data = topic_perf.filter(pl.col("topic") == topic)

    if len(topic_data) == 0:
        return {'level': 0, 'stars': '☆☆☆☆☆', 'progress': 0, 'status': 'Sin iniciar'}

    row = topic_data.row(0, named=True)
    accuracy = row['accuracy']
    questions_answered = row['questions_answered']

    if accuracy >= 90 and questions_answered >= 20:
        level = 5
        status = 'Maestro'
    elif accuracy >= 80 and questions_answered >= 15:
        level = 4
        status = 'Experto'
    elif accuracy >= 70 and questions_answered >= 10:
        level = 3
        status = 'Avanzado'
    elif accuracy >= 60 and questions_answered >= 5:
        level = 2
        status = 'Intermedio'
    elif questions_answered >= 3:
        level = 1
        status = 'Principiante'
    else:
        level = 0
        status = 'Iniciando'

    stars = '⭐' * level + '☆' * (5 - level)
    progress = min(accuracy, 100.0)

    return {
        'level': level,
        'stars': stars,
        'progress': progress,
        'status': status,
        'accuracy': accuracy,
        'questions_answered': questions_answered
    }


def get_all_topic_masteries(username: str) -> pl.DataFrame:
    """Get mastery levels for all topics - OPTIMIZED VERSION"""
    questions_df = get_all_questions()
    all_topics = questions_df["topic"].unique().to_list()

    topic_perf = get_topic_performance(username)

    if len(topic_perf) == 0:
        return pl.DataFrame({
            'topic': all_topics,
            'level': [0] * len(all_topics),
            'stars': ['☆☆☆☆☆'] * len(all_topics),
            'accuracy': [0.0] * len(all_topics),
            'questions_answered': [0] * len(all_topics),
            'status': ['Sin iniciar'] * len(all_topics)
        }).sort('level')

    masteries = []

    for row in topic_perf.iter_rows(named=True):
        accuracy = row['accuracy']
        questions_answered = row['questions_answered']

        if accuracy >= 90 and questions_answered >= 20:
            level = 5
            status = 'Maestro'
        elif accuracy >= 80 and questions_answered >= 15:
            level = 4
            status = 'Experto'
        elif accuracy >= 70 and questions_answered >= 10:
            level = 3
            status = 'Avanzado'
        elif accuracy >= 60 and questions_answered >= 5:
            level = 2
            status = 'Intermedio'
        elif questions_answered >= 3:
            level = 1
            status = 'Principiante'
        else:
            level = 0
            status = 'Iniciando'

        stars = '⭐' * level + '☆' * (5 - level)

        masteries.append({
            'topic': row['topic'],
            'level': level,
            'stars': stars,
            'accuracy': accuracy,
            'questions_answered': questions_answered,
            'status': status
        })

    topics_with_data = {m['topic'] for m in masteries}
    for topic in all_topics:
        if topic not in topics_with_data:
            masteries.append({
                'topic': topic,
                'level': 0,
                'stars': '☆☆☆☆☆',
                'accuracy': 0.0,
                'questions_answered': 0,
                'status': 'Sin iniciar'
            })

    return pl.DataFrame(masteries).sort('level')


# ============================================================================
# Enhanced Adaptive Selection
# ============================================================================

def select_next_question(
    username: str,
    topic: str = None,
    mode: str = "adaptive"
) -> dict:
    """Select next question using topic-first adaptive algorithm"""

    questions_df = get_all_questions()

    if len(questions_df) == 0:
        return None

    if topic:
        questions_df = questions_df.filter(pl.col("topic") == topic)
        if len(questions_df) == 0:
            return None

    if mode == "random":
        return _select_random(questions_df)
    elif mode == "unanswered":
        return _select_unanswered(username, questions_df)
    elif mode == "weakest":
        return _select_weakest(username, questions_df)
    else:
        if topic:
            return _select_adaptive_within_topic(username, questions_df, topic)
        else:
            return _select_adaptive_topic_first(username, questions_df)


def _select_adaptive_topic_first(username: str, questions_df: pl.DataFrame) -> dict:
    """NEW ALGORITHM: Select from weakest topic first"""

    topic_masteries = get_all_topic_masteries(username)

    if len(topic_masteries) == 0:
        return _select_random(questions_df)

    performance_df = get_user_performance(username)

    for topic_row in topic_masteries.iter_rows(named=True):
        topic = topic_row['topic']
        mastery_level = topic_row['level']

        if mastery_level >= 5:
            continue

        topic_questions = questions_df.filter(pl.col("topic") == topic)

        if len(topic_questions) == 0:
            continue

        topic_question_ids = topic_questions["question_id"].to_list()

        if len(performance_df) > 0:
            topic_perf = performance_df.filter(
                pl.col("question_id").is_in(topic_question_ids)
            )
        else:
            topic_perf = pl.DataFrame()

        if len(topic_perf) > 0:
            mastered_ids = topic_perf.filter(
                (pl.col("streak") >= 2) & (pl.col("priority_score") < -5)
            )["question_id"].to_list()

            available_questions = topic_questions.filter(
                ~pl.col("question_id").is_in(mastered_ids)
            )
        else:
            available_questions = topic_questions

        if len(available_questions) > 0:
            return _select_adaptive_within_topic(username, available_questions, topic)

    return _select_random(questions_df)


def _select_adaptive_within_topic(
    username: str,
    questions_df: pl.DataFrame,
    topic: str
) -> dict:
    """Weighted selection within a specific topic"""

    performance_df = get_user_performance(username)

    questions_with_perf = questions_df.join(
        performance_df,
        on="question_id",
        how="left"
    )

    questions_with_perf = questions_with_perf.with_columns([
        pl.when(pl.col("priority_score").is_null())
        .then(pl.lit(3.0))
        .when(pl.col("priority_score") > 0)
        .then(pl.col("priority_score"))
        .otherwise(
            pl.max_horizontal([pl.col("priority_score"), pl.lit(-10.0)]).abs() * 0.1 + 0.5
        )
        .alias("selection_weight")
    ])

    questions_list = questions_with_perf.to_dicts()
    weights = [q['selection_weight'] for q in questions_list]

    total_weight = sum(weights)
    if total_weight == 0:
        return _select_random(questions_df)

    normalized_weights = [w / total_weight for w in weights]

    selected = random.choices(questions_list, weights=normalized_weights, k=1)[0]

    question_dict = {
        "question_id": selected["question_id"],
        "question_number": selected["question_number"],
        "topic": selected["topic"],
        "question_text": selected["question_text"],
        "answer_options": selected["answer_options"],
        "correct_answer": selected["correct_answer"],
        "explanation": selected["explanation"],
        "images": selected.get("images", []),
        "source_file": selected.get("source_file"),
        "source_type": selected.get("source_type")
    }

    return question_dict


def _select_random(questions_df: pl.DataFrame) -> dict:
    """Pure random selection"""
    sampled = questions_df.sample(1)
    return sampled.to_dicts()[0]


def _select_unanswered(username: str, questions_df: pl.DataFrame) -> dict:
    """Select from unanswered questions only"""
    answered_ids = get_answered_questions(username)

    unanswered_df = questions_df.filter(
        ~pl.col("question_id").is_in(list(answered_ids))
    )

    if len(unanswered_df) == 0:
        return _select_random(questions_df)

    return unanswered_df.sample(1).to_dicts()[0]


def _select_weakest(username: str, questions_df: pl.DataFrame) -> dict:
    """Select from questions user consistently gets wrong"""
    performance_df = get_user_performance(username)

    if len(performance_df) == 0:
        return _select_random(questions_df)

    weak_questions = performance_df.filter(
        pl.col("incorrect_attempts") > pl.col("correct_attempts")
    )

    if len(weak_questions) == 0:
        return _select_random(questions_df)

    weak_ids = weak_questions.select("question_id")
    weak_questions_full = questions_df.join(weak_ids, on="question_id", how="inner")

    if len(weak_questions_full) == 0:
        return _select_random(questions_df)

    return weak_questions_full.sample(1).to_dicts()[0]


def select_next_topic(username: str) -> str:
    """Select next topic based on user's weak areas"""
    topic_masteries = get_all_topic_masteries(username)

    if len(topic_masteries) == 0:
        questions_df = get_all_questions()
        topics = questions_df.select("topic").unique().to_series().to_list()
        return random.choice(topics)

    weakest_topic = topic_masteries.head(1)["topic"][0]
    return weakest_topic


def select_exam_questions(
    username: str,
    num_questions: int,
    topics: list[str] = None,
    difficulty_balance: str = "mixed"
) -> list[dict]:
    """Select questions for simulated exam"""

    questions_df = get_all_questions()

    if topics:
        questions_df = questions_df.filter(pl.col("topic").is_in(topics))

    if len(questions_df) < num_questions:
        num_questions = len(questions_df)

    if difficulty_balance == "mixed":
        selected = questions_df.sample(num_questions)
        return selected.to_dicts()

    elif difficulty_balance == "challenging":
        selected_questions = []
        for _ in range(num_questions):
            q = select_next_question(username, mode="adaptive")
            if q:
                selected_questions.append(q)
                questions_df = questions_df.filter(
                    pl.col("question_id") != q["question_id"]
                )
        return selected_questions

    else:
        num_weak = num_questions // 3
        num_random = num_questions - num_weak

        selected_questions = []

        for _ in range(num_weak):
            q = select_next_question(username, mode="weakest")
            if q and q["question_id"] not in [sq["question_id"] for sq in selected_questions]:
                selected_questions.append(q)

        remaining = questions_df.filter(
            ~pl.col("question_id").is_in([q["question_id"] for q in selected_questions])
        )

        if len(remaining) > 0:
            random_selected = remaining.sample(
                min(num_random, len(remaining))
            ).to_dicts()
            selected_questions.extend(random_selected)

        return selected_questions
