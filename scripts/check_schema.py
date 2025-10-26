"""
Check if Supabase schema is set up correctly
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

from src.database import get_connection


def check_schema():
    """Verify database schema exists"""

    print("\n" + "=" * 60)
    print("🔍 CHECKING DATABASE SCHEMA")
    print("=" * 60)

    conn = get_connection()
    cursor = conn.cursor()

    # Check if questions table exists
    print("\n1️⃣ Checking if 'questions' table exists...")
    cursor.execute(
        """
                   SELECT EXISTS (SELECT
                                  FROM information_schema.tables
                                  WHERE table_name = 'questions');
                   """
    )

    exists = cursor.fetchone()[0]

    if exists:
        print("   ✅ 'questions' table exists")
    else:
        print("   ❌ 'questions' table does NOT exist")
        print("\n   📝 You need to run the SQL schema first!")
        print("   👉 Go to Supabase SQL Editor")
        print("   👉 Run the SQL from: docs/SUPABASE_SCHEMA.sql")
        cursor.close()
        conn.close()
        return

    # Check table structure
    print("\n2️⃣ Checking table columns...")
    cursor.execute(
        """
                   SELECT column_name, data_type
                   FROM information_schema.columns
                   WHERE table_name = 'questions'
                   ORDER BY ordinal_position;
                   """
    )

    columns = cursor.fetchall()

    print("   Columns found:")
    for col_name, col_type in columns:
        print(f"      {col_name:20s} {col_type}")

    # Check indexes
    print("\n3️⃣ Checking indexes...")
    cursor.execute(
        """
                   SELECT indexname
                   FROM pg_indexes
                   WHERE tablename = 'questions';
                   """
    )

    indexes = cursor.fetchall()
    print(f"   Found {len(indexes)} indexes:")
    for (idx_name,) in indexes:
        print(f"      {idx_name}")

    # Check other tables
    print("\n4️⃣ Checking related tables...")
    related_tables = ["user_answers", "user_question_performance", "flashcard_reviews", "custom_flashcards"]

    for table in related_tables:
        cursor.execute(
            """
                       SELECT EXISTS (SELECT
                                      FROM information_schema.tables
                                      WHERE table_name = %s);
                       """,
            (table,),
        )

        exists = cursor.fetchone()[0]
        status = "✅" if exists else "❌"
        print(f"   {status} {table}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("✅ SCHEMA CHECK COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    try:
        check_schema()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("  1. Created a Supabase project")
        print("  2. Added DATABASE_URL to .streamlit/secrets.toml or .env")
        print("  3. Run the SQL schema from docs/SUPABASE_SCHEMA.sql")
