"""
Smart Question Selection Algorithm
Prioritizes questions user is struggling with
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
# Smart Question Selection
# ============================================================================

def select_next_question(
    username: str,
    topic: str = None,
    mode: str = "adaptive"
) -> dict:
    """
    Select next question using adaptive algorithm

    Args:
        username: User identifier
        topic: Optional topic filter
        mode: Selection mode
            - "adaptive": Smart selection based on performance
            - "random": Pure random
            - "weakest": Only show questions user struggles with
            - "unanswered": Only show never-answered questions

    Returns:
        dict: Selected question
    """

    # Load all questions
    questions_df = get_all_questions()

    if len(questions_df) == 0:
        return None

    # Filter by topic if specified
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

    else:  # adaptive (default)
        return _select_adaptive(username, questions_df, topic)


# ============================================================================
# Selection Strategies
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
        # All answered, fall back to random
        return _select_random(questions_df)

    return unanswered_df.sample(1).to_dicts()[0]


def _select_weakest(username: str, questions_df: pl.DataFrame) -> dict:
    """Select from questions user consistently gets wrong"""
    performance_df = get_user_performance(username)

    if len(performance_df) == 0:
        # No history, random selection
        return _select_random(questions_df)

    # Filter to questions with negative accuracy (more wrong than right)
    weak_questions = performance_df.filter(
        pl.col("incorrect_attempts") > pl.col("correct_attempts")
    )

    if len(weak_questions) == 0:
        # No weak questions, use random
        return _select_random(questions_df)

    # Join with questions to get full data
    weak_ids = weak_questions.select("question_id")
    weak_questions_full = questions_df.join(
        weak_ids,
        on="question_id",
        how="inner"
    )

    if len(weak_questions_full) == 0:
        return _select_random(questions_df)

    return weak_questions_full.sample(1).to_dicts()[0]


def _select_adaptive(
    username: str,
    questions_df: pl.DataFrame,
    topic: str = None
) -> dict:
    """
    Adaptive selection based on priority scores

    Algorithm:
    1. Get user performance stats
    2. Calculate selection weights:
       - High priority (wrong answers) = higher chance
       - Low priority (correct streak) = lower chance
       - Never answered = medium chance
    3. Weighted random selection
    """

    performance_df = get_user_performance(username)

    if len(performance_df) == 0:
        # No history - random from unanswered
        return _select_unanswered(username, questions_df)

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
        .then(pl.lit(3.0))  # Medium priority for new questions
        # High priority (wrong answers) = high weight
        .when(pl.col("priority_score") > 0)
        .then(pl.col("priority_score"))
        # Low priority (correct streak) = low weight, but never zero
        .otherwise(pl.max_horizontal([pl.col("priority_score"), pl.lit(-10.0)]).abs() * 0.1 + 0.5)
        .alias("selection_weight")
    ])

    # Convert to pandas for weighted sampling (Polars doesn't have native weighted sample)
    questions_pd = questions_with_perf.to_pandas()
    weights = questions_pd["selection_weight"].values

    # Normalize weights
    weights = weights / weights.sum()

    # Weighted random selection
    selected_idx = random.choices(range(len(questions_pd)), weights=weights, k=1)[0]
    selected_row = questions_pd.iloc[selected_idx]

    # Convert back to dict
    question_dict = {
        "question_id": selected_row["question_id"],
        "question_number": selected_row["question_number"],
        "topic": selected_row["topic"],
        "question_text": selected_row["question_text"],
        "answer_options": selected_row["answer_options"],
        "correct_answer": selected_row["correct_answer"],
        "explanation": selected_row["explanation"],
        "source_file": selected_row.get("source_file"),
        "source_type": selected_row.get("source_type")
    }

    return question_dict


# ============================================================================
# Topic-Based Selection
# ============================================================================

def select_next_topic(username: str) -> str:
    """
    Select next topic based on user's weak areas

    Returns topic with lowest accuracy
    """
    topic_perf = get_topic_performance(username)

    if len(topic_perf) == 0:
        # No history, get random topic from all questions
        questions_df = get_all_questions()
        topics = questions_df.select("topic").unique().to_series().to_list()
        return random.choice(topics)

    # Return topic with highest priority (lowest accuracy)
    weakest_topic = topic_perf.sort("avg_priority", descending=True)[0, "topic"]
    return weakest_topic


# ============================================================================
# Batch Selection for Exams
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

    # Filter by topics
    if topics:
        questions_df = questions_df.filter(pl.col("topic").is_in(topics))

    if len(questions_df) < num_questions:
        num_questions = len(questions_df)

    if difficulty_balance == "mixed":
        # Pure random selection
        selected = questions_df.sample(num_questions)
        return selected.to_dicts()

    elif difficulty_balance == "challenging":
        # Prioritize weak areas
        selected_questions = []
        for _ in range(num_questions):
            q = select_next_question(username, mode="adaptive")
            if q:
                selected_questions.append(q)
                # Remove from pool to avoid duplicates
                questions_df = questions_df.filter(
                    pl.col("question_id") != q["question_id"]
                )
        return selected_questions

    else:  # adaptive
        # Mix of strategies
        num_weak = num_questions // 3
        num_random = num_questions - num_weak

        selected_questions = []

        # Add weak questions
        for _ in range(num_weak):
            q = select_next_question(username, mode="weakest")
            if q and q["question_id"] not in [sq["question_id"] for sq in selected_questions]:
                selected_questions.append(q)

        # Fill rest with random
        remaining = questions_df.filter(
            ~pl.col("question_id").is_in([q["question_id"] for q in selected_questions])
        )

        if len(remaining) > 0:
            random_selected = remaining.sample(
                min(num_random, len(remaining))
            ).to_dicts()
            selected_questions.extend(random_selected)

        return selected_questions
