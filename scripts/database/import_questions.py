"""
Script to import questions from JSON file into Supabase
Run this once to populate your database
WITH IMAGE SUPPORT
"""

import json
import sys
import os

from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# TEST MODE - Set to True to import only first 10 questions
# ============================================================================
TEST_MODE = False
TEST_LIMIT = 10

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database import insert_questions_from_json, get_question_count

# ============================================================================
# Validation
# ============================================================================


def has_correct_answer(question: dict) -> bool:
    """Check if question has at least one correct answer marked"""
    return any(opt.get("is_correct", False) for opt in question.get("answer_options", []))


def validate_question_structure(question: dict) -> tuple[bool, str]:
    """
    Validate question has all required fields
    Returns (is_valid, error_message)
    """
    required_fields = [
        "question_id",
        "question_number",
        "topic",
        "question_text",
        "answer_options",
        "correct_answer",
        "explanation",
    ]

    for field in required_fields:
        if field not in question:
            return False, f"Missing field: {field}"

    if not isinstance(question["answer_options"], list):
        return False, "answer_options must be a list"

    if len(question["answer_options"]) == 0:
        return False, "No answer options"

    for opt in question["answer_options"]:
        if "letter" not in opt:
            return False, "Answer option missing 'letter'"
        if "text" not in opt:
            return False, "Answer option missing 'text'"
        if "is_correct" not in opt:
            return False, "Answer option missing 'is_correct'"

    if not has_correct_answer(question):
        return False, "No correct answer marked"

    return True, ""


# ============================================================================
# Import Questions
# ============================================================================


def import_questions_from_file(filepath: str):
    """Import questions from JSON file"""

    print(f"📂 Loading questions from: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            questions = json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return

    print(f"📊 Found {len(questions)} questions")

    if TEST_MODE:
        questions = questions[:TEST_LIMIT]
        print(f"🧪 TEST MODE: Limiting to {len(questions)} questions\n")

    # Filter and validate
    print("🔍 Validating question structure...")
    valid_questions = []
    skipped_count = 0
    with_images_count = 0

    for i, q in enumerate(questions, 1):
        is_valid, error_msg = validate_question_structure(q)

        if not is_valid:
            print(f"⚠️  Skipping question {i} ({q.get('question_id', 'unknown')}): {error_msg}")
            skipped_count += 1
            continue

        if not q.get("topic") or q["topic"].strip() == "":
            print(f"⚠️  Skipping question {i}: Empty topic")
            skipped_count += 1
            continue

        # Ensure images field exists (default to empty list)
        if "images" not in q:
            q["images"] = []
        
        if q["images"]:
            with_images_count += 1

        valid_questions.append(q)

    print(f"✅ Validation passed: {len(valid_questions)} valid questions")
    print(f"📸 Questions with images: {with_images_count}")

    if skipped_count > 0:
        print(f"⚠️  Skipped {skipped_count} invalid questions")

    if len(valid_questions) == 0:
        print("❌ No valid questions to import")
        return

    # Insert into database
    print("\n💾 Inserting into database...")
    success_count, error_count = insert_questions_from_json(valid_questions)

    print(f"\n{'='*60}")
    print(f"✅ Successfully inserted: {success_count}")
    print(f"❌ Errors: {error_count}")
    print(f"{'='*60}")

    # Verify
    total_in_db = get_question_count()
    print(f"\n📊 Total questions in database: {total_in_db}")

    # Show topic distribution
    print("\n📚 Topics loaded:")
    topics = {}
    for q in valid_questions:
        topic = q["topic"]
        topics[topic] = topics.get(topic, 0) + 1

    for topic, count in sorted(topics.items(), key=lambda x: x[1], reverse=True):
        print(f"   {topic}: {count}")

    # Show image distribution
    print(f"\n📸 Questions with images: {with_images_count}/{len(valid_questions)}")


if __name__ == "__main__":
    # Default to categorized file
    default_file = r"data/processed/questions_categorized.json"
    filepath = default_file

    if len(sys.argv) > 1:
        filepath = sys.argv[1]

    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        print(f"\nUsage: python {sys.argv[0]} [path_to_questions.json]")
        print(f"Default file: {default_file}")
        sys.exit(1)

    import_questions_from_file(filepath)
