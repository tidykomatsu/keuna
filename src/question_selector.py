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
# Topic Mastery Calculation
# ============================================================================

def calculate_topic_mastery(username: str, topic: str) -> dict:
    """
    Calculate mastery level for a topic (0-5 stars)

    Returns:
        {
            'level': int (0-5),
            'stars': str ('⭐⭐⭐'),
            'progress': float (0-100),
            'status': str ('Principiante', 'Intermedio', 'Avanzado', 'Experto', 'Maestro')
        }
    """
    topic_perf = get_topic_performance(username)

    if len(topic_perf) == 0:
        return {'level': 0, 'stars': '☆☆☆☆☆', 'progress': 0, 'status': 'Sin iniciar'}

    topic_data = topic_perf.filter(pl.col("topic") == topic)

    if len(topic_data) == 0:
        return {'level': 0, 'stars': '☆☆☆☆☆', 'progress': 0, 'status': 'Sin iniciar'}

    row = topic_data.row(0, named=True)
    accuracy = row['accuracy']
    questions_answered = row['questions_answered']

    # Level calculation based on accuracy + volume
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
    """Get mastery levels for all topics"""
    questions_df = get_all_questions()
    topics = questions_df["topic"].unique().to_list()

    masteries = []
    for topic in topics:
        mastery = calculate_topic_mastery(username, topic)
        masteries.append({
            'topic': topic,
            'level': mastery['level'],
            'stars': mastery['stars'],
            'accuracy': mastery.get('accuracy', 0),
            'questions_answered': mastery.get('questions_answered', 0),
            'status': mastery['status']
        })

    return pl.DataFrame(masteries).sort('level')


# ============================================================================
# Enhanced Adaptive Selection (Pseudocódigo Implementation)
# ============================================================================

def select_next_question(
    username: str,
    topic: str = None,
    mode: str = "adaptive"
) -> dict:
    """
    ENHANCED: Select next question using topic-first adaptive algorithm

    Algorithm (from pseudocódigo):
    1. Calculate mastery by topic
    2. Identify weakest topic (lowest mastery)
    3. Filter questions from that topic
    4. Weighted selection within topic based on individual performance
    5. Fallback to next weakest topic if current is mastered

    Args:
        username: User identifier
        topic: Optional topic filter (overrides adaptive topic selection)
        mode: Selection mode
            - "adaptive": Smart topic-first selection (NEW ALGORITHM)
            - "random": Pure random
            - "weakest": Only show questions user struggles with
            - "unanswered": Only show never-answered questions

    Returns:
        dict: Selected question
    """

    questions_df = get_all_questions()

    if len(questions_df) == 0:
        return None

    # Filter by topic if specified (overrides adaptive)
    if topic:
        questions_df = questions_df.filter(pl.col("topic") == topic)
        if len(questions_df) == 0:
            return None

    # Mode-specific selection
    if mode == "random":
        return _select_random(questions_df)

    elif mode == "unanswered":
        return _select_unanswered(username, questions_df)

    elif mode == "weakest":
        return _select_weakest(username, questions_df)

    else:  # adaptive (ENHANCED)
        if topic:
            # Topic specified: weighted selection within topic
            return _select_adaptive_within_topic(username, questions_df, topic)
        else:
            # No topic: use new topic-first algorithm
            return _select_adaptive_topic_first(username, questions_df)


# ============================================================================
# NEW: Topic-First Adaptive Selection
# ============================================================================

def _select_adaptive_topic_first(username: str, questions_df: pl.DataFrame) -> dict:
    """
    NEW ALGORITHM: Select from weakest topic first

    Steps:
    1. Get all topics ranked by mastery (weakest first)
    2. Iterate from weakest to strongest
    3. For each topic, try to find non-mastered questions
    4. Use weighted selection within chosen topic
    5. Fallback to random if all topics mastered
    """

    # Get topics ranked by mastery (weakest first)
    topic_masteries = get_all_topic_masteries(username)

    if len(topic_masteries) == 0:
        # No performance data: random selection
        return _select_random(questions_df)

    performance_df = get_user_performance(username)

    # Iterate through topics from weakest to strongest
    for topic_row in topic_masteries.iter_rows(named=True):
        topic = topic_row['topic']
        mastery_level = topic_row['level']

        # Skip topics at max mastery (5 stars)
        if mastery_level >= 5:
            continue

        # Filter questions for this topic
        topic_questions = questions_df.filter(pl.col("topic") == topic)

        if len(topic_questions) == 0:
            continue

        # Find questions in this topic that aren't mastered
        # Mastered = answered correctly 2+ times consecutively
        topic_question_ids = topic_questions["question_id"].to_list()

        # Get performance for this topic's questions
        if len(performance_df) > 0:
            topic_perf = performance_df.filter(
                pl.col("question_id").is_in(topic_question_ids)
            )
        else:
            topic_perf = pl.DataFrame()

        # Identify non-mastered questions
        # Mastered = streak >= 2 AND priority_score < -5
        if len(topic_perf) > 0:
            mastered_ids = topic_perf.filter(
                (pl.col("streak") >= 2) & (pl.col("priority_score") < -5)
            )["question_id"].to_list()

            # Questions to practice: not mastered or never answered
            available_questions = topic_questions.filter(
                ~pl.col("question_id").is_in(mastered_ids)
            )
        else:
            # No performance data for this topic: all questions available
            available_questions = topic_questions

        # If we found available questions, select from this topic
        if len(available_questions) > 0:
            return _select_adaptive_within_topic(username, available_questions, topic)

    # All topics mastered: fallback to random
    return _select_random(questions_df)


def _select_adaptive_within_topic(
    username: str,
    questions_df: pl.DataFrame,
    topic: str
) -> dict:
    """
    Weighted selection within a specific topic
    Uses existing priority_score system
    """

    performance_df = get_user_performance(username)

    # Join questions with performance
    questions_with_perf = questions_df.join(
        performance_df,
        on="question_id",
        how="left"
    )

    # Calculate selection weight
    questions_with_perf = questions_with_perf.with_columns([
        # Questions never answered get base weight
        pl.when(pl.col("priority_score").is_null())
        .then(pl.lit(3.0))
        # High priority (wrong answers) = high weight
        .when(pl.col("priority_score") > 0)
        .then(pl.col("priority_score"))
        # Low priority (correct streak) = low weight, but never zero
        .otherwise(
            pl.max_horizontal([pl.col("priority_score"), pl.lit(-10.0)]).abs() * 0.1 + 0.5
        )
        .alias("selection_weight")
    ])

    # Convert to list for weighted selection
    questions_list = questions_with_perf.to_dicts()
    weights = [q['selection_weight'] for q in questions_list]

    # Normalize weights
    total_weight = sum(weights)
    if total_weight == 0:
        # All weights are zero: random selection
        return _select_random(questions_df)

    normalized_weights = [w / total_weight for w in weights]

    # Weighted random selection
    selected = random.choices(questions_list, weights=normalized_weights, k=1)[0]

    # Convert back to dict (remove performance columns)
    question_dict = {
        "question_id": selected["question_id"],
        "question_number": selected["question_number"],
        "topic": selected["topic"],
        "question_text": selected["question_text"],
        "answer_options": selected["answer_options"],
        "correct_answer": selected["correct_answer"],
        "explanation": selected["explanation"],
        "source_file": selected.get("source_file"),
        "source_type": selected.get("source_type")
    }

    return question_dict


# ============================================================================
# Existing Selection Strategies (Unchanged)
# ============================================================================

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


# ============================================================================
# Topic-Based Selection (Enhanced)
# ============================================================================

def select_next_topic(username: str) -> str:
    """
    Select next topic based on user's weak areas
    Returns topic with lowest mastery level
    """
    topic_masteries = get_all_topic_masteries(username)

    if len(topic_masteries) == 0:
        # No history, get random topic from all questions
        questions_df = get_all_questions()
        topics = questions_df.select("topic").unique().to_series().to_list()
        return random.choice(topics)

    # Return topic with lowest level (weakest)
    weakest_topic = topic_masteries.head(1)["topic"][0]
    return weakest_topic


# ============================================================================
# Batch Selection for Exams (Unchanged)
# ============================================================================

def select_exam_questions(
    username: str,
    num_questions: int,
    topics: list[str] = None,
    difficulty_balance: str = "mixed"
) -> list[dict]:
    """
    Select questions for simulated exam

    Args:
        username: User identifier
        num_questions: Number of questions to select
        topics: Optional list of topics to include
        difficulty_balance:
            - "mixed": Mix of easy and hard
            - "adaptive": Based on user level
            - "challenging": Prioritize weak areas

    Returns:
        list[dict]: List of selected questions
    """

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

    else:  # adaptive
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
