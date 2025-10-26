"""
Script to import questions from JSON file into Supabase
Run this once to populate your database
"""

import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database import insert_questions_from_json, get_question_count

# ============================================================================
# Topic Extraction (from old utils.py)
# ============================================================================

TOPICS = [
    'Cardiología',
    'Diabetes',
    'Endocrinología',
    'Gastroenterología',
    'Hematología',
    'Infectología',
    'Nefrología',
    'Neurología',
    'Respiratorio',
    'Reumatología'
]


def extract_topic_from_source(source_file: str) -> str:
    """Extract topic from source_file using string detection"""
    source_lower = source_file.lower()

    for topic in TOPICS:
        if topic.lower() in source_lower:
            return topic

    return "General"  # Default topic if none found


def has_correct_answer(question: dict) -> bool:
    """Check if question has at least one correct answer marked"""
    return any(opt.get("is_correct", False) for opt in question.get("answer_options", []))


# ============================================================================
# Import Questions
# ============================================================================

def import_questions_from_file(filepath: str):
    """Import questions from JSON file"""

    print(f"📂 Loading questions from: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    print(f"📊 Found {len(questions)} questions")

    # Filter and enrich questions
    print("🔍 Validating and enriching question structure...")
    valid_questions = []

    for i, q in enumerate(questions):
        # Check if has correct answer
        if not has_correct_answer(q):
            print(f"⚠️  Skipping question {i+1}: No correct answer marked")
            continue

        # Extract topic from source_file
        topic = extract_topic_from_source(q.get("source_file", ""))

        # Validate required fields
        required_fields = [
            "question_id", "question_number",
            "question_text", "answer_options", "correct_answer", "explanation"
        ]

        try:
            for field in required_fields:
                assert field in q, f"Missing field: {field}"

            # Validate answer_options structure
            for opt in q["answer_options"]:
                assert "letter" in opt, f"Answer option missing 'letter'"
                assert "text" in opt, f"Answer option missing 'text'"
                assert "is_correct" in opt, f"Answer option missing 'is_correct'"

            # Add enriched topic
            q["topic"] = topic

            valid_questions.append(q)

        except AssertionError as e:
            print(f"⚠️  Skipping question {i+1}: {e}")
            continue

    print(f"✅ Validation passed: {len(valid_questions)} valid questions")

    if len(valid_questions) < len(questions):
        print(f"⚠️  Filtered out {len(questions) - len(valid_questions)} invalid questions")

    # Insert into database
    print("💾 Inserting into database...")
    success_count, error_count = insert_questions_from_json(valid_questions)

    print(f"✅ Successfully inserted: {success_count}")
    print(f"❌ Errors: {error_count}")

    # Verify
    total_in_db = get_question_count()
    print(f"📊 Total questions in database: {total_in_db}")


if __name__ == "__main__":
    # Default to the questions file in EUNACOM/OUTPUTS
    default_file = "EUNACOM/OUTPUTS/questions_complete_20251019_185913.json"
    filepath = default_file

    if len(sys.argv) > 1:
        filepath = sys.argv[1]

    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        print(f"Usage: python {sys.argv[0]} [path_to_questions.json]")
        print(f"Default file: {default_file}")
        sys.exit(1)

    import_questions_from_file(filepath)
