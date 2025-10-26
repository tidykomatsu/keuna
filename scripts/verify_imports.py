"""
Verify questions were imported correctly into Supabase
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

from src.database import get_connection, get_all_questions, get_question_count
import polars as pl


def verify_import():
    """Verify database import"""

    print("\n" + "=" * 60)
    print("🔍 VERIFYING SUPABASE IMPORT")
    print("=" * 60)

    # Test connection
    print("\n1️⃣ Testing database connection...")
    try:
        conn = get_connection()
        conn.close()
        print("   ✅ Connection successful!")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return

    # Get question count
    print("\n2️⃣ Counting questions...")
    try:
        total = get_question_count()
        print(f"   ✅ Total questions in database: {total}")

        if total == 0:
            print("   ⚠️  Database is empty - run import_questions.py first")
            return
    except Exception as e:
        print(f"   ❌ Error counting: {e}")
        return

    # Load all questions
    print("\n3️⃣ Loading questions...")
    try:
        questions_df = get_all_questions()
        print(f"   ✅ Loaded {len(questions_df)} questions as DataFrame")
    except Exception as e:
        print(f"   ❌ Error loading: {e}")
        return

    # Validate schema
    print("\n4️⃣ Validating schema...")
    required_columns = [
        "question_id",
        "question_number",
        "topic",
        "question_text",
        "answer_options",
        "correct_answer",
        "explanation",
    ]

    missing_cols = [col for col in required_columns if col not in questions_df.columns]

    if missing_cols:
        print(f"   ❌ Missing columns: {missing_cols}")
        return
    else:
        print(f"   ✅ All required columns present")

    # Check for nulls in critical fields
    print("\n5️⃣ Checking data quality...")
    issues = []

    for col in ["question_text", "topic", "correct_answer", "explanation"]:
        null_count = questions_df.filter(pl.col(col).is_null()).height
        if null_count > 0:
            issues.append(f"   ⚠️  {null_count} questions have NULL {col}")

    if issues:
        for issue in issues:
            print(issue)
    else:
        print("   ✅ No NULL values in critical fields")

    # Topic distribution
    print("\n6️⃣ Topic distribution:")
    topic_counts = questions_df.group_by("topic").agg(pl.len().alias("count")).sort("count", descending=True)

    for row in topic_counts.iter_rows(named=True):
        print(f"   {row['topic']:30s}: {row['count']:3d} questions")

    # Source distribution
    print("\n7️⃣ Source distribution:")
    source_counts = questions_df.group_by("source_type").agg(pl.len().alias("count")).sort("count", descending=True)

    for row in source_counts.iter_rows(named=True):
        source = row["source_type"] or "Unknown"
        print(f"   {source:30s}: {row['count']:3d} questions")

    # Check answer_options structure
    print("\n8️⃣ Validating answer_options structure...")

    sample_question = questions_df.head(1).to_dicts()[0]
    answer_opts = sample_question.get("answer_options", [])

    if isinstance(answer_opts, list) and len(answer_opts) > 0:
        print(f"   ✅ answer_options is a list with {len(answer_opts)} options")

        first_opt = answer_opts[0]
        required_keys = ["letter", "text", "is_correct"]

        if all(key in first_opt for key in required_keys):
            print(f"   ✅ Sample option has correct structure: {list(first_opt.keys())}")
        else:
            print(f"   ⚠️  Sample option missing keys. Has: {list(first_opt.keys())}")
    else:
        print(f"   ❌ answer_options has wrong structure: {type(answer_opts)}")

    # Check for duplicates
    print("\n9️⃣ Checking for duplicates...")

    duplicate_ids = questions_df.group_by("question_id").agg(pl.len().alias("count")).filter(pl.col("count") > 1)

    if len(duplicate_ids) > 0:
        print(f"   ⚠️  Found {len(duplicate_ids)} duplicate question_ids:")
        for row in duplicate_ids.iter_rows(named=True):
            print(f"      {row['question_id']}: {row['count']} times")
    else:
        print("   ✅ No duplicate question_ids")

    # Sample question display
    print("\n🔟 Sample question:")
    print("-" * 60)
    sample = questions_df.sample(1).to_dicts()[0]

    print(f"ID: {sample['question_id']}")
    print(f"Topic: {sample['topic']}")
    print(f"Question: {sample['question_text'][:100]}...")
    print(f"Correct: {sample['correct_answer'][:80]}...")
    print(f"Options: {len(sample['answer_options'])} choices")

    print("\n" + "=" * 60)
    print("✅ VERIFICATION COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    verify_import()
