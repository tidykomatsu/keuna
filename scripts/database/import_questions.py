"""
Script to import questions from JSON file into Supabase
Run this once to populate your database
WITH IMAGE SUPPORT, STRICT VALIDATION, AND RECONSTRUCCIONES

Usage:
    python import_questions.py                      # Default: insert-only mode
    python import_questions.py --mode insert-only   # Skip existing questions
    python import_questions.py --mode upsert        # Update existing questions
    python import_questions.py path/to/file.json   # Custom file path
"""

import json
import sys
import os
import argparse

from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# TEST MODE - Set to True to import only questions with images
# ============================================================================
TEST_MODE = False
TEST_LIMIT = 200
TEST_IMAGES_ONLY = False  # When TEST_MODE=True, only import questions with images

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database import insert_questions_from_json, get_question_count, get_existing_question_ids


# ============================================================================
# Schema Definition (same as extraction/utils.py)
# ============================================================================

REQUIRED_FIELDS = [
    "question_id",
    "question_number",
    "topic",
    "question_text",
    "answer_options",
    "correct_answer",
    "explanation",
]

OPTIONAL_FIELDS = [
    "images",
    "source_file",
    "source_type",
    "reconstruction_name",
    "reconstruction_order",
]

ANSWER_OPTION_REQUIRED = ["letter", "text", "is_correct"]


# ============================================================================
# Validation with Assertions
# ============================================================================

def validate_question_structure(question: dict) -> tuple[bool, list[str]]:
    """
    Validate question has all required fields with correct types.
    Returns (is_valid, list_of_issues)
    """
    issues = []
    q_id = question.get("question_id", "UNKNOWN")

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in question:
            issues.append(f"[{q_id}] Missing field: {field}")

    # question_id validation
    q_id_value = question.get("question_id", "")
    if not q_id_value or not str(q_id_value).strip():
        issues.append(f"[{q_id}] Empty question_id")

    # question_text validation
    q_text = question.get("question_text", "")
    if not q_text or not str(q_text).strip():
        issues.append(f"[{q_id}] Empty question_text")

    # topic validation
    topic = question.get("topic")
    if topic is None or (isinstance(topic, str) and not topic.strip()):
        issues.append(f"[{q_id}] Empty or missing topic")

    # answer_options validation
    opts = question.get("answer_options")
    if not isinstance(opts, list):
        issues.append(f"[{q_id}] answer_options must be a list")
    elif len(opts) == 0:
        issues.append(f"[{q_id}] No answer options")
    else:
        # Validate each option structure
        for i, opt in enumerate(opts):
            if not isinstance(opt, dict):
                issues.append(f"[{q_id}] answer_options[{i}] must be a dict")
                continue
            
            for field in ANSWER_OPTION_REQUIRED:
                if field not in opt:
                    issues.append(f"[{q_id}] answer_options[{i}] missing '{field}'")
        
        # Must have exactly one correct answer
        correct_count = sum(1 for opt in opts if opt.get("is_correct", False))
        if correct_count == 0:
            issues.append(f"[{q_id}] No correct answer marked")
        elif correct_count > 1:
            issues.append(f"[{q_id}] Multiple correct answers ({correct_count})")

    # images validation (optional but must be list if present)
    images = question.get("images", [])
    if not isinstance(images, list):
        issues.append(f"[{q_id}] 'images' must be a list")

    # Reconstruction fields validation
    recon_name = question.get("reconstruction_name")
    recon_order = question.get("reconstruction_order")
    
    if recon_name is not None and not isinstance(recon_name, str):
        issues.append(f"[{q_id}] reconstruction_name must be string or None")
    
    if recon_order is not None and not isinstance(recon_order, int):
        issues.append(f"[{q_id}] reconstruction_order must be int or None")

    return len(issues) == 0, issues


def has_correct_answer(question: dict) -> bool:
    """Check if question has at least one correct answer marked"""
    return any(opt.get("is_correct", False) for opt in question.get("answer_options", []))


def assert_no_duplicate_ids(questions: list[dict]):
    """
    Assert no duplicate question IDs exist.
    Fails fast with detailed error.
    """
    seen = {}
    duplicates = []
    
    for q in questions:
        q_id = q.get("question_id", "")
        if q_id in seen:
            duplicates.append({
                "id": q_id,
                "first_idx": seen[q_id],
                "second_idx": questions.index(q)
            })
        else:
            seen[q_id] = questions.index(q)
    
    if duplicates:
        error_lines = ["DUPLICATE QUESTION IDS FOUND:"]
        for dup in duplicates[:10]:
            error_lines.append(f"  ID '{dup['id']}' at indices {dup['first_idx']} and {dup['second_idx']}")
        if len(duplicates) > 10:
            error_lines.append(f"  ... and {len(duplicates) - 10} more")
        raise AssertionError("\n".join(error_lines))


# ============================================================================
# Import Questions
# ============================================================================


def import_questions_from_file(filepath: str, mode: str = "insert-only"):
    """
    Import questions from JSON file with strict validation.
    
    Args:
        filepath: Path to JSON file
        mode: "insert-only" (skip existing) or "upsert" (update existing)
    """

    print(f"\n{'='*60}")
    print(f"📂 Loading questions from: {filepath}")
    print(f"📋 Mode: {mode.upper()}")
    print(f"{'='*60}")

    # File existence check
    assert os.path.exists(filepath), f"File not found: {filepath}"

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            questions = json.load(f)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON in {filepath}: {e}")

    # Type check
    assert isinstance(questions, list), f"Expected list, got {type(questions)}"
    assert len(questions) > 0, "Empty questions list"

    print(f"📊 Found {len(questions)} questions in file")

    if TEST_MODE:
        if TEST_IMAGES_ONLY:
            questions = [q for q in questions if q.get("images")]
            print(f"🧪 TEST MODE: Filtered to {len(questions)} questions with images")
        questions = questions[:TEST_LIMIT]
        print(f"🧪 TEST MODE: Limiting to {len(questions)} questions\n")

    # ============================================================================
    # CRITICAL: Check for duplicate IDs FIRST
    # ============================================================================
    print("🔍 Checking for duplicate IDs in file...")
    assert_no_duplicate_ids(questions)
    print("✅ No duplicate IDs found in file")

    # ============================================================================
    # INSERT-ONLY MODE: Filter out existing questions
    # ============================================================================
    skipped_count = 0
    
    if mode == "insert-only":
        print("\n🔍 Checking which questions already exist in database...")
        existing_ids = get_existing_question_ids()
        print(f"   Found {len(existing_ids)} existing questions in database")
        
        original_count = len(questions)
        questions = [q for q in questions if q.get("question_id") not in existing_ids]
        skipped_count = original_count - len(questions)
        
        print(f"   ⏭️  Skipping {skipped_count} existing questions")
        print(f"   ✨ {len(questions)} NEW questions to import")
        
        if len(questions) == 0:
            print(f"\n{'='*60}")
            print("✅ NO NEW QUESTIONS TO IMPORT")
            print(f"   All {original_count} questions already exist in database")
            print(f"{'='*60}\n")
            return

    # ============================================================================
    # Validate and filter
    # ============================================================================
    print("\n🔍 Validating question structure...")
    
    valid_questions = []
    all_issues = []
    with_images_count = 0
    recon_count = 0

    for i, q in enumerate(questions, 1):
        is_valid, issues = validate_question_structure(q)

        if not is_valid:
            all_issues.extend(issues)
            # Print first 10 issues inline
            if len([iss for iss in all_issues if iss.startswith(f"[{q.get('question_id', 'UNKNOWN')}]")]) <= 1:
                for iss in issues[:3]:
                    print(f"  ⚠️  {iss}")
            continue

        # Ensure optional fields exist
        if "images" not in q:
            q["images"] = []
        if "reconstruction_name" not in q:
            q["reconstruction_name"] = None
        if "reconstruction_order" not in q:
            q["reconstruction_order"] = None

        if q["images"]:
            with_images_count += 1
        
        if q["reconstruction_name"]:
            recon_count += 1

        valid_questions.append(q)

    print(f"\n{'='*60}")
    print(f"📊 VALIDATION RESULTS")
    print(f"{'='*60}")
    print(f"✅ Valid questions: {len(valid_questions)}")
    print(f"❌ Invalid questions: {len(questions) - len(valid_questions)}")
    print(f"📸 Questions with images: {with_images_count}")
    print(f"📋 Reconstruction questions: {recon_count}")
    
    if skipped_count > 0:
        print(f"⏭️  Skipped (already exist): {skipped_count}")
    
    if all_issues:
        # Group issues by type
        issue_types = {}
        for iss in all_issues:
            # Extract type: "[ID] Type: ..."
            parts = iss.split("]")
            if len(parts) > 1:
                issue_type = parts[1].strip().split(":")[0] if ":" in parts[1] else parts[1].strip()
            else:
                issue_type = iss
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
        
        print(f"\n⚠️  Issue breakdown:")
        for issue_type, count in sorted(issue_types.items(), key=lambda x: -x[1]):
            print(f"   {issue_type}: {count}")

    if len(valid_questions) == 0:
        print(f"\n{'='*60}")
        print("✅ NO VALID NEW QUESTIONS TO IMPORT")
        print(f"{'='*60}\n")
        return

    # ============================================================================
    # Insert into database
    # ============================================================================
    print(f"\n{'='*60}")
    print("💾 Inserting into database...")
    print(f"{'='*60}")
    
    # Use upsert=False for insert-only mode
    use_upsert = (mode == "upsert")
    success_count, error_count = insert_questions_from_json(valid_questions, upsert=use_upsert)

    print(f"\n✅ Successfully inserted: {success_count}")
    print(f"❌ Database errors: {error_count}")

    # Verify
    total_in_db = get_question_count()
    print(f"\n📊 Total questions in database: {total_in_db}")

    # Post-import assertion
    if success_count == 0 and len(valid_questions) > 0:
        print("⚠️ Warning: No questions were imported!")

    # Show topic distribution
    print("\n📚 Topics loaded:")
    topics = {}
    for q in valid_questions:
        topic = q["topic"]
        topics[topic] = topics.get(topic, 0) + 1

    for topic, count in sorted(topics.items(), key=lambda x: -x[1]):
        print(f"   {topic}: {count}")

    # Show reconstruction distribution
    recon_names = {}
    for q in valid_questions:
        if q.get("reconstruction_name"):
            name = q["reconstruction_name"]
            recon_names[name] = recon_names.get(name, 0) + 1

    if recon_names:
        print("\n📋 Reconstrucciones loaded:")
        for name, count in sorted(recon_names.items()):
            print(f"   {name}: {count} questions")

    print(f"\n{'='*60}")
    print("✅ IMPORT COMPLETE")
    print(f"{'='*60}\n")


def get_default_input_path() -> str:
    """Get default input path from config (respects EUNACOM_PROCESSED_DATA env var)"""
    # Add extraction dir to path to import config
    script_dir = os.path.dirname(__file__)
    extraction_dir = os.path.join(script_dir, "..", "extraction")
    sys.path.insert(0, extraction_dir)

    from config import get_processed_data_root
    return str(get_processed_data_root() / "questions_ready.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import questions from JSON file into Supabase database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python import_questions.py                           # Insert only new questions
  python import_questions.py --mode upsert             # Update existing + insert new
  python import_questions.py --mode insert-only        # Skip existing (default)
  python import_questions.py path/to/questions.json    # Custom file path

Pipeline:
  1. Run extract_all.py                      → questions_ready.json
  2. Run migrate_images_to_supabase.py --full → updates questions_ready.json (optional)
  3. Run import_questions.py (this script)
        """
    )
    
    parser.add_argument(
        "filepath",
        nargs="?",
        default=None,
        help="Path to questions JSON file (default: data/processed/questions_ready.json)"
    )
    
    parser.add_argument(
        "--mode",
        choices=["insert-only", "upsert"],
        default="insert-only",
        help="Import mode: 'insert-only' skips existing questions (default), 'upsert' updates existing"
    )
    
    args = parser.parse_args()
    
    # Get filepath
    filepath = args.filepath if args.filepath else get_default_input_path()

    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        print(f"\nUsage: python {sys.argv[0]} [path_to_questions.json] [--mode insert-only|upsert]")
        print(f"Default file: {get_default_input_path()}")
        sys.exit(1)

    import_questions_from_file(filepath, mode=args.mode)
