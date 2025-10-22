"""
SQLite database for user progress tracking
"""

import sqlite3
from datetime import datetime
from pathlib import Path
import polars as pl
import json

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
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            question_id TEXT NOT NULL,
            selected_answer TEXT NOT NULL,
            is_correct INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            UNIQUE(username, question_id, timestamp)
        )
        """
    )

    # User statistics cache
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_stats (
            username TEXT PRIMARY KEY,
            total_answered INTEGER DEFAULT 0,
            total_correct INTEGER DEFAULT 0,
            last_updated TEXT
        )
        """
    )

    # Flashcard reviews table
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

    # Custom flashcards table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS custom_flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            front_text TEXT NOT NULL,
            back_text TEXT NOT NULL,
            topic TEXT,
            created_at TEXT NOT NULL,
            is_archived INTEGER DEFAULT 0,
            UNIQUE(username, front_text)
        )
        """
    )

    conn.commit()
    conn.close()


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
        VALUES (?, 1, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
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

    cursor.execute(
        "SELECT question_id, is_correct FROM user_progress WHERE username = ?",
        (username,)
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return pl.DataFrame({"topic": [], "total": [], "correct": [], "accuracy": []})

    history_df = pl.DataFrame({
        "question_id": [r[0] for r in rows],
        "is_correct": [r[1] for r in rows]
    })

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


# ============================================================================
# Custom Flashcards CRUD
# ============================================================================


def create_custom_flashcard(username: str, front_text: str, back_text: str, topic: str = None) -> bool:
    """Create a new custom flashcard"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    timestamp = datetime.now().isoformat()

    try:
        cursor.execute(
            """
            INSERT INTO custom_flashcards (username, front_text, back_text, topic, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, front_text, back_text, topic, timestamp),
        )
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    finally:
        conn.close()

    return success


def get_custom_flashcards(username: str, include_archived: bool = False) -> pl.DataFrame:
    """Get all custom flashcards for a user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if include_archived:
        query = """
        SELECT id, front_text, back_text, topic, created_at, is_archived
        FROM custom_flashcards
        WHERE username = ?
        ORDER BY created_at DESC
        """
    else:
        query = """
        SELECT id, front_text, back_text, topic, created_at, is_archived
        FROM custom_flashcards
        WHERE username = ? AND is_archived = 0
        ORDER BY created_at DESC
        """

    cursor.execute(query, (username,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return pl.DataFrame({
            "id": [],
            "front_text": [],
            "back_text": [],
            "topic": [],
            "created_at": [],
            "is_archived": []
        })

    df = pl.DataFrame({
        "id": [r[0] for r in rows],
        "front_text": [r[1] for r in rows],
        "back_text": [r[2] for r in rows],
        "topic": [r[3] for r in rows],
        "created_at": [r[4] for r in rows],
        "is_archived": [r[5] for r in rows]
    })

    return df


def update_custom_flashcard(card_id: int, front_text: str, back_text: str, topic: str = None) -> bool:
    """Update an existing custom flashcard"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE custom_flashcards
        SET front_text = ?, back_text = ?, topic = ?
        WHERE id = ?
        """,
        (front_text, back_text, topic, card_id),
    )

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return success


def archive_custom_flashcard(card_id: int) -> bool:
    """Soft delete (archive) a custom flashcard"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE custom_flashcards
        SET is_archived = 1
        WHERE id = ?
        """,
        (card_id,),
    )

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return success


def delete_custom_flashcard(card_id: int) -> bool:
    """Permanently delete a custom flashcard"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM custom_flashcards WHERE id = ?", (card_id,))

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return success


def export_custom_flashcards_json(username: str) -> str:
    """Export custom flashcards to JSON string"""
    df = get_custom_flashcards(username, include_archived=False)

    if len(df) == 0:
        return "[]"

    cards_list = df.to_dicts()
    return json.dumps(cards_list, ensure_ascii=False, indent=2)


def import_custom_flashcards_json(username: str, json_data: str) -> tuple[int, int]:
    """Import custom flashcards from JSON string. Returns (success_count, error_count)"""
    try:
        cards = json.loads(json_data)
    except json.JSONDecodeError:
        return 0, 0

    success_count = 0
    error_count = 0

    for card in cards:
        front = card.get("front_text", "")
        back = card.get("back_text", "")
        topic = card.get("topic")

        if front and back:
            if create_custom_flashcard(username, front, back, topic):
                success_count += 1
            else:
                error_count += 1
        else:
            error_count += 1

    return success_count, error_count
