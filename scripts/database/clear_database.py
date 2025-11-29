"""
Clear all questions from the database
WARNING: This deletes all data!
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database import get_connection

def clear_all_questions():
    """Delete all questions from the database"""

    print("\n" + "=" * 60)
    print("⚠️  WARNING: DELETE ALL QUESTIONS")
    print("=" * 60)

    conn = get_connection()
    cursor = conn.cursor()

    # Count current questions
    cursor.execute("SELECT COUNT(*) FROM questions")
    count = cursor.fetchone()[0]

    print(f"\n📊 Current questions in database: {count}")

    if count == 0:
        print("✅ Database already empty!")
        cursor.close()
        conn.close()
        return

    # Confirm
    print(f"\n⚠️  This will DELETE all {count} questions!")
    response = input("Type 'DELETE' to confirm: ")

    if response != "DELETE":
        print("❌ Cancelled")
        cursor.close()
        conn.close()
        return

    # Delete (must delete in order due to foreign keys)
    print("\n🗑️  Deleting...")

    # First, delete related data
    cursor.execute("DELETE FROM user_answers")
    print("   ✓ Cleared user_answers")

    cursor.execute("DELETE FROM user_question_performance")
    print("   ✓ Cleared user_question_performance")

    cursor.execute("DELETE FROM flashcard_reviews")
    print("   ✓ Cleared flashcard_reviews")

    # Finally, delete questions
    cursor.execute("DELETE FROM questions")
    print("   ✓ Cleared questions")

    conn.commit()

    # Verify
    cursor.execute("SELECT COUNT(*) FROM questions")
    remaining = cursor.fetchone()[0]

    print(f"✅ Deleted {count - remaining} questions")
    print(f"📊 Remaining: {remaining}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("✅ DATABASE CLEARED")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    clear_all_questions()
