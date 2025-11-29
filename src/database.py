"""
Database operations for EUNACOM Quiz App - PostgreSQL/Supabase Version
All data persistence with automatic performance tracking
WITH IMAGE SUPPORT
"""

import psycopg2
from psycopg2.extras import RealDictCursor, Json
import polars as pl
import streamlit as st
import os
from datetime import datetime

# ============================================================================
# Connection Management
# ============================================================================


def get_connection():
    """Get PostgreSQL connection from Supabase"""
    try:
        connection_string = st.secrets["DATABASE_URL"]
    except:
        connection_string = os.getenv("DATABASE_URL")

    assert connection_string, "DATABASE_URL not found in secrets or environment"

    return psycopg2.connect(connection_string)


# ============================================================================
# Database Initialization
# ============================================================================


def init_database():
    """
    Initialize database - tables are created via Supabase SQL editor
    This function just ensures connection works
    """
    try:
        conn = get_connection()
        conn.close()
        return True
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        return False


# ============================================================================
# QUESTION MANAGEMENT
# ============================================================================


def insert_questions_from_json(questions: list[dict]) -> tuple[int, int]:
    """
    Insert questions from JSON structure into database
    Returns (success_count, error_count)
    """
    conn = get_connection()
    cursor = conn.cursor()

    success_count = 0
    error_count = 0

    for question in questions:
        try:
            # Handle images field (new)
            images = question.get("images", [])
            
            cursor.execute(
                """
                INSERT INTO questions (
                    question_id, question_number, topic, question_text,
                    answer_options, correct_answer, explanation,
                    source_file, source_type, images
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (question_id) DO UPDATE SET
                    question_number = EXCLUDED.question_number,
                    topic = EXCLUDED.topic,
                    question_text = EXCLUDED.question_text,
                    answer_options = EXCLUDED.answer_options,
                    correct_answer = EXCLUDED.correct_answer,
                    explanation = EXCLUDED.explanation,
                    source_file = EXCLUDED.source_file,
                    source_type = EXCLUDED.source_type,
                    images = EXCLUDED.images,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    question["question_id"],
                    question["question_number"],
                    question["topic"],
                    question["question_text"],
                    Json(question["answer_options"]),
                    question["correct_answer"],
                    question["explanation"],
                    question.get("source_file"),
                    question.get("source_type"),
                    Json(images),
                ),
            )
            success_count += 1
        except Exception as e:
            error_count += 1
            print(f"❌ Error inserting question {question['question_id']}: {e}")
            conn.rollback()
            cursor = conn.cursor()
            continue

    conn.commit()
    cursor.close()
    conn.close()

    return success_count, error_count


def get_all_questions() -> pl.DataFrame:
    """
    Load all questions from database as Polars DataFrame
    """
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT
            question_id,
            question_number,
            topic,
            question_text,
            answer_options,
            correct_answer,
            explanation,
            source_file,
            source_type,
            images
        FROM questions
        ORDER BY question_number
    """
    )

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        return pl.DataFrame(
            schema={
                "question_id": pl.Utf8,
                "question_number": pl.Utf8,
                "topic": pl.Utf8,
                "question_text": pl.Utf8,
                "answer_options": pl.List(
                    pl.Struct(
                        [pl.Field("letter", pl.Utf8), pl.Field("text", pl.Utf8), pl.Field("is_correct", pl.Boolean)]
                    )
                ),
                "correct_answer": pl.Utf8,
                "explanation": pl.Utf8,
                "source_file": pl.Utf8,
                "source_type": pl.Utf8,
                "images": pl.List(pl.Utf8),
            }
        )

    return pl.DataFrame(rows)


def get_questions_by_topic(topic: str) -> pl.DataFrame:
    """Get questions filtered by topic"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT * FROM questions
        WHERE topic = %s
        ORDER BY question_number
        """,
        (topic,),
    )

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return pl.DataFrame(rows) if rows else pl.DataFrame()


def get_question_by_id(question_id: str) -> dict:
    """Get single question by ID"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("SELECT * FROM questions WHERE question_id = %s", (question_id,))

    row = cursor.fetchone()
    cursor.close()
    conn.close()

    return dict(row) if row else None


def get_question_count() -> int:
    """Get total number of questions in database"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM questions")
    count = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return count


def get_questions_with_images_count() -> int:
    """Get count of questions that have images"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM questions WHERE images != '[]'::jsonb")
    count = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return count


# ============================================================================
# USER ANSWERS
# ============================================================================


def save_answer(username: str, question_id: str, user_answer: str, is_correct: bool):
    """
    Save user answer - trigger automatically updates performance stats
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO user_answers (username, question_id, user_answer, is_correct)
        VALUES (%s, %s, %s, %s)
        """,
        (username, question_id, user_answer, is_correct),
    )

    conn.commit()
    cursor.close()
    conn.close()


def get_answered_questions(username: str) -> set:
    """Get set of question IDs user has answered"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT question_id FROM user_answers WHERE username = %s", (username,))

    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return {row[0] for row in results}


def get_user_stats(username: str) -> dict:
    """Get overall user statistics"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            COUNT(*) as total_answered,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as total_correct
        FROM user_answers
        WHERE username = %s
        """,
        (username,),
    )

    row = cursor.fetchone()
    cursor.close()
    conn.close()

    total_answered = row[0] or 0
    total_correct = row[1] or 0
    accuracy = (total_correct / total_answered * 100) if total_answered > 0 else 0

    return {"total_answered": total_answered, "total_correct": total_correct, "accuracy": accuracy}


def get_stats_by_topic(username: str, questions_df: pl.DataFrame = None) -> pl.DataFrame:
    """Get statistics grouped by topic"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT
            q.topic,
            COUNT(*) as total,
            SUM(CASE WHEN ua.is_correct THEN 1 ELSE 0 END) as correct
        FROM user_answers ua
        JOIN questions q ON ua.question_id = q.question_id
        WHERE ua.username = %s
        GROUP BY q.topic
        ORDER BY correct::float / COUNT(*) ASC
        """,
        (username,),
    )

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        return pl.DataFrame()

    df = pl.DataFrame(rows)
    df = df.with_columns([(pl.col("correct") / pl.col("total") * 100).alias("accuracy")])

    return df


def reset_user_progress(username: str):
    """Delete all user progress (answers and performance, not custom flashcards)"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM user_answers WHERE username = %s", (username,))
    cursor.execute("DELETE FROM user_question_performance WHERE username = %s", (username,))
    cursor.execute("DELETE FROM flashcard_reviews WHERE username = %s", (username,))

    conn.commit()
    cursor.close()
    conn.close()


# ============================================================================
# USER PERFORMANCE TRACKING
# ============================================================================


def get_user_performance(username: str, limit: int = None) -> pl.DataFrame:
    """
    Get user performance stats for all questions
    Used by smart question selector
    """
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT
            question_id,
            topic,
            total_attempts,
            correct_attempts,
            incorrect_attempts,
            last_answered_at,
            streak,
            priority_score
        FROM user_question_performance
        WHERE username = %s
        ORDER BY priority_score DESC
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query, (username,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        return pl.DataFrame(
            schema={
                "question_id": pl.Utf8,
                "topic": pl.Utf8,
                "total_attempts": pl.Int64,
                "correct_attempts": pl.Int64,
                "incorrect_attempts": pl.Int64,
                "last_answered_at": pl.Datetime,
                "streak": pl.Int64,
                "priority_score": pl.Float64,
            }
        )

    return pl.DataFrame(rows)


def get_topic_performance(username: str) -> pl.DataFrame:
    """Get aggregated performance by topic"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT
            topic,
            COUNT(*) as questions_answered,
            SUM(correct_attempts) as total_correct,
            SUM(total_attempts) as total_attempts,
            AVG(priority_score) as avg_priority
        FROM user_question_performance
        WHERE username = %s
        GROUP BY topic
        ORDER BY avg_priority DESC
        """,
        (username,),
    )

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        return pl.DataFrame()

    df = pl.DataFrame(rows)
    df = df.with_columns([(pl.col("total_correct") / pl.col("total_attempts") * 100).alias("accuracy")])

    return df


# ============================================================================
# FLASHCARD OPERATIONS (Kept for backwards compatibility)
# ============================================================================


def save_flashcard_review(username: str, card_id: str, rating: str):
    """Save flashcard review"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO flashcard_reviews (username, card_id, rating)
        VALUES (%s, %s, %s)
        """,
        (username, card_id, rating),
    )

    conn.commit()
    cursor.close()
    conn.close()


def get_flashcard_stats(username: str) -> dict:
    """Get flashcard review statistics"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            COUNT(*) as total_reviewed,
            SUM(CASE WHEN rating = 'correct' THEN 1 ELSE 0 END) as correct_count
        FROM flashcard_reviews
        WHERE username = %s
        """,
        (username,),
    )

    row = cursor.fetchone()
    cursor.close()
    conn.close()

    return {"total_reviewed": row[0] or 0, "correct_count": row[1] or 0}


# ============================================================================
# CUSTOM FLASHCARDS (Kept for backwards compatibility)
# ============================================================================


def create_custom_flashcard(username: str, front_text: str, back_text: str, topic: str = None) -> bool:
    """Create new custom flashcard"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO custom_flashcards (username, front_text, back_text, topic)
            VALUES (%s, %s, %s, %s)
            """,
            (username, front_text, back_text, topic),
        )
        conn.commit()
        success = True
    except psycopg2.IntegrityError:
        conn.rollback()
        success = False
    finally:
        cursor.close()
        conn.close()

    return success


def get_custom_flashcards(username: str) -> pl.DataFrame:
    """Get all custom flashcards for user"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT id, front_text, back_text, topic, created_at
        FROM custom_flashcards
        WHERE username = %s AND archived = FALSE
        ORDER BY created_at DESC
        """,
        (username,),
    )

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        return pl.DataFrame(
            schema={
                "id": pl.Int64,
                "front_text": pl.Utf8,
                "back_text": pl.Utf8,
                "topic": pl.Utf8,
                "created_at": pl.Datetime,
            }
        )

    return pl.DataFrame(rows)


def update_custom_flashcard(card_id: int, front_text: str, back_text: str, topic: str = None) -> bool:
    """Update existing flashcard"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            UPDATE custom_flashcards
            SET front_text = %s, back_text = %s, topic = %s
            WHERE id = %s
            """,
            (front_text, back_text, topic, card_id),
        )
        conn.commit()
        success = True
    except:
        conn.rollback()
        success = False
    finally:
        cursor.close()
        conn.close()

    return success


def archive_custom_flashcard(card_id: int):
    """Archive (soft delete) flashcard"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE custom_flashcards SET archived = TRUE WHERE id = %s", (card_id,))

    conn.commit()
    cursor.close()
    conn.close()


def export_custom_flashcards_json(username: str) -> str:
    """Export custom flashcards as JSON"""
    import json

    cards_df = get_custom_flashcards(username)

    if len(cards_df) == 0:
        return "[]"

    cards_list = cards_df.select(["front_text", "back_text", "topic"]).to_dicts()
    return json.dumps(cards_list, ensure_ascii=False, indent=2)


def import_custom_flashcards_json(username: str, json_data: str) -> tuple:
    """Import custom flashcards from JSON"""
    import json

    cards = json.loads(json_data)
    success_count = 0
    error_count = 0

    for card in cards:
        success = create_custom_flashcard(username, card["front_text"], card["back_text"], card.get("topic"))

        if success:
            success_count += 1
        else:
            error_count += 1

    return success_count, error_count


# ============================================================================
# TOPIC MASTERY FUNCTIONS
# ============================================================================


def get_topic_mastery_levels(username: str) -> pl.DataFrame:
    """
    Get mastery levels for all topics
    Calculated from user_question_performance
    """
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT
            topic,
            COUNT(*) as questions_answered,
            AVG(CASE WHEN total_attempts > 0
                THEN (correct_attempts::float / total_attempts * 100)
                ELSE 0 END) as accuracy,
            AVG(priority_score) as avg_priority,
            CASE
                WHEN AVG(CASE WHEN total_attempts > 0
                    THEN (correct_attempts::float / total_attempts * 100)
                    ELSE 0 END) >= 90 AND COUNT(*) >= 20 THEN 5
                WHEN AVG(CASE WHEN total_attempts > 0
                    THEN (correct_attempts::float / total_attempts * 100)
                    ELSE 0 END) >= 80 AND COUNT(*) >= 15 THEN 4
                WHEN AVG(CASE WHEN total_attempts > 0
                    THEN (correct_attempts::float / total_attempts * 100)
                    ELSE 0 END) >= 70 AND COUNT(*) >= 10 THEN 3
                WHEN AVG(CASE WHEN total_attempts > 0
                    THEN (correct_attempts::float / total_attempts * 100)
                    ELSE 0 END) >= 60 AND COUNT(*) >= 5 THEN 2
                WHEN COUNT(*) >= 3 THEN 1
                ELSE 0
            END as level
        FROM user_question_performance
        WHERE username = %s
        GROUP BY topic
        ORDER BY level ASC, accuracy ASC
        """,
        (username,),
    )

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        return pl.DataFrame()

    return pl.DataFrame(rows)


def get_weakest_topic(username: str) -> str:
    """
    Get user's weakest topic (lowest mastery level)
    Returns topic name or None
    """
    mastery_df = get_topic_mastery_levels(username)

    if len(mastery_df) == 0:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT topic FROM questions LIMIT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result else None

    weakest = mastery_df.head(1)
    return weakest["topic"][0]
