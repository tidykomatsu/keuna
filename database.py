"""
SQLite database for user progress tracking
"""

import sqlite3
from datetime import datetime
from pathlib import Path
import polars as pl

# ============================================================================
# Database Setup
# ============================================================================

DB_PATH = Path("users.db")


def init_database():
    """Create database tables if they don't exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # User progress table
    cursor.execute(
        """
                   CREATE TABLE IF NOT EXISTS user_progress
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       username
                       TEXT
                       NOT
                       NULL,
                       question_id
                       TEXT
                       NOT
                       NULL,
                       selected_answer
                       TEXT
                       NOT
                       NULL,
                       is_correct
                       INTEGER
                       NOT
                       NULL,
                       timestamp
                       TEXT
                       NOT
                       NULL,
                       UNIQUE
                   (
                       username,
                       question_id,
                       timestamp
                   )
                       )
                   """
    )

    # User statistics cache
    cursor.execute(
        """
                   CREATE TABLE IF NOT EXISTS user_stats
                   (
                       username
                       TEXT
                       PRIMARY
                       KEY,
                       total_answered
                       INTEGER
                       DEFAULT
                       0,
                       total_correct
                       INTEGER
                       DEFAULT
                       0,
                       last_updated
                       TEXT
                   )
                   """
    )

    conn.commit()
    conn.close()

    # Initialize flashcard table
    init_flashcard_table()


# ============================================================================
# Progress Tracking
# ============================================================================


def save_answer(username: str, question_id: str, selected_answer: str, is_correct: bool):
    """Save user answer to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    timestamp = datetime.now().isoformat()

    cursor.execute(
        """
                   INSERT INTO user_progress (username, question_id, selected_answer, is_correct, timestamp)
                   VALUES (?, ?, ?, ?, ?)
                   """,
        (username, question_id, selected_answer, int(is_correct), timestamp),
    )

    # Update stats
    cursor.execute(
        """
                   INSERT INTO user_stats (username, total_answered, total_correct, last_updated)
                   VALUES (?, 1, ?, ?) ON CONFLICT(username) DO
                   UPDATE SET
                       total_answered = total_answered + 1,
                       total_correct = total_correct + ?,
                       last_updated = ?
                   """,
        (username, int(is_correct), timestamp, int(is_correct), timestamp),
    )

    conn.commit()
    conn.close()


def get_user_stats(username: str) -> dict:
    """Get user statistics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
                   SELECT total_answered, total_correct, last_updated
                   FROM user_stats
                   WHERE username = ?
                   """,
        (username,),
    )

    result = cursor.fetchone()
    conn.close()

    if result:
        total_answered, total_correct, last_updated = result
        accuracy = (total_correct / total_answered * 100) if total_answered > 0 else 0
        return {
            "total_answered": total_answered,
            "total_correct": total_correct,
            "accuracy": accuracy,
            "last_updated": last_updated,
        }

    return {"total_answered": 0, "total_correct": 0, "accuracy": 0, "last_updated": None}


def get_answered_questions(username: str) -> set:
    """Get set of question IDs already answered by user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
                   SELECT DISTINCT question_id
                   FROM user_progress
                   WHERE username = ?
                   """,
        (username,),
    )

    result = {row[0] for row in cursor.fetchall()}
    conn.close()

    return result


def get_user_history(username: str, limit: int = 50) -> pl.DataFrame:
    """Get user answer history as Polars DataFrame"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
            SELECT question_id, selected_answer, is_correct, timestamp
            FROM user_progress
            WHERE username = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """

    cursor.execute(query, (username, limit))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return pl.DataFrame({
            "question_id": [],
            "selected_answer": [],
            "is_correct": [],
            "timestamp": []
        })

    df = pl.DataFrame({
        "question_id": [r[0] for r in rows],
        "selected_answer": [r[1] for r in rows],
        "is_correct": [r[2] for r in rows],
        "timestamp": [r[3] for r in rows]
    })

    return df


def get_stats_by_topic(username: str, questions_df: pl.DataFrame) -> pl.DataFrame:
    """Calculate statistics grouped by topic"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all user answers
    cursor.execute("SELECT question_id, is_correct FROM user_progress WHERE username = ?", (username,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return pl.DataFrame({"topic": [], "total": [], "correct": [], "accuracy": []})

    # Create DataFrame from query results
    history_df = pl.DataFrame({
        "question_id": [r[0] for r in rows],
        "is_correct": [r[1] for r in rows]
    })

    # Join with questions to get topics
    stats_df = (
        history_df.join(questions_df.select(["question_id", "topic"]), on="question_id", how="left")
        .group_by("topic")
        .agg([pl.count().alias("total"), pl.col("is_correct").sum().alias("correct")])
        .with_columns((pl.col("correct") / pl.col("total") * 100).alias("accuracy"))
        .sort("accuracy", descending=False)
    )

    return stats_df


def reset_user_progress(username: str):
    """Reset all progress for a user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM user_progress WHERE username = ?", (username,))
    cursor.execute("DELETE FROM user_stats WHERE username = ?", (username,))

    conn.commit()
    conn.close()


# ============================================================================
# Flashcard Progress Tracking
# ============================================================================


def init_flashcard_table():
    """Create flashcard review table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS flashcard_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            question_id TEXT NOT NULL,
            review_result TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def save_flashcard_review(username: str, question_id: str, result: str):
    """Save flashcard review (wrong, partial, correct)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    timestamp = datetime.now().isoformat()

    cursor.execute(
        """
        INSERT INTO flashcard_reviews (username, question_id, review_result, timestamp)
        VALUES (?, ?, ?, ?)
        """,
        (username, question_id, result, timestamp),
    )

    conn.commit()
    conn.close()


def get_flashcard_stats(username: str) -> dict:
    """Get flashcard review statistics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) as total,
               SUM(CASE WHEN review_result = 'correct' THEN 1 ELSE 0 END) as correct
        FROM flashcard_reviews
        WHERE username = ?
        """,
        (username,),
    )

    result = cursor.fetchone()
    conn.close()

    if result:
        total, correct = result
        return {"total_reviewed": total, "correct_count": correct}

    return {"total_reviewed": 0, "correct_count": 0}
