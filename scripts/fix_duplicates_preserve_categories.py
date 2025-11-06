"""
Fix duplicate answer text while PRESERVING existing categorizations
This updates the answer_options but keeps all categories you already paid for!
"""

import json
from pathlib import Path

# ============================================================================
# Configuration
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

CATEGORIZED_FILE = PROCESSED_DIR / "questions_categorized.json"
OUTPUT_FILE = PROCESSED_DIR / "questions_categorized_FIXED.json"
BACKUP_FILE = PROCESSED_DIR / "questions_categorized_BACKUP.json"

# ============================================================================
# Fix Duplicates
# ============================================================================

def remove_duplicate_text(text: str) -> str:
    """Remove duplicate text like 'TextoTexto' -> 'Texto'"""

    if not text or len(text) < 2:
        return text

    # Check if text is exactly duplicated (first half == second half)
    if len(text) % 2 == 0:
        midpoint = len(text) // 2
        first_half = text[:midpoint]
        second_half = text[midpoint:]

        if first_half == second_half and len(first_half) > 0:
            return first_half

    return text


def fix_question(question: dict) -> dict:
    """Fix duplicate text in answer options and correct_answer"""

    fixed_q = question.copy()

    # Fix answer_options
    fixed_options = []
    for opt in question.get("answer_options", []):
        fixed_opt = opt.copy()
        fixed_opt["text"] = remove_duplicate_text(opt.get("text", ""))
        fixed_opt["explanation"] = remove_duplicate_text(opt.get("explanation", ""))
        fixed_options.append(fixed_opt)

    fixed_q["answer_options"] = fixed_options

    # Fix correct_answer field
    if question.get("correct_answer"):
        fixed_q["correct_answer"] = remove_duplicate_text(question["correct_answer"])

    # Fix explanation
    if question.get("explanation"):
        fixed_q["explanation"] = remove_duplicate_text(question["explanation"])

    return fixed_q


def main():
    """Fix duplicates while preserving categories"""

    print("\n" + "=" * 80)
    print("🔧 FIXING DUPLICATES (PRESERVING CATEGORIES)")
    print("=" * 80 + "\n")

    # Load categorized data
    print(f"📂 Loading: {CATEGORIZED_FILE.name}")
    with open(CATEGORIZED_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print(f"📊 Total questions: {len(questions)}")

    # Backup
    print(f"💾 Creating backup: {BACKUP_FILE.name}")
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    # Find and fix duplicates
    print(f"\n🔍 Checking for duplicates...")

    fixed_count = 0

    for i, q in enumerate(questions):
        original = json.dumps(q, ensure_ascii=False)
        fixed_q = fix_question(q)
        fixed = json.dumps(fixed_q, ensure_ascii=False)

        if original != fixed:
            questions[i] = fixed_q
            fixed_count += 1

    print(f"✅ Fixed {fixed_count} questions with duplicate text")
    print(f"✅ Preserved {len(questions)} categorizations")

    # Check that categories are preserved
    categorized_count = sum(1 for q in questions if q.get("topic") and q["topic"] != "")
    print(f"✅ Questions with categories: {categorized_count}")

    # Save fixed version
    print(f"\n💾 Saving: {OUTPUT_FILE.name}")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    # Verify
    print(f"\n🔍 Verifying...")
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        verify_data = json.load(f)

    assert len(verify_data) == len(questions), "Question count mismatch!"

    # Sample check
    sample = verify_data[0]
    print(f"\n📋 Sample question:")
    print(f"   ID: {sample['question_id']}")
    print(f"   Topic: {sample.get('topic', 'NO TOPIC')}")
    print(f"   Answer options: {len(sample.get('answer_options', []))}")
    if sample.get('answer_options'):
        print(f"   Sample answer: {sample['answer_options'][0]['text'][:50]}...")

    print("\n" + "=" * 80)
    print("✅ FIX COMPLETE - CATEGORIES PRESERVED!")
    print(f"\n📋 Next steps:")
    print(f"   1. Review: {OUTPUT_FILE.name}")
    print(f"   2. If good, replace original:")
    print(f"      mv {OUTPUT_FILE.name} {CATEGORIZED_FILE.name}")
    print(f"   3. Clear database: python scripts/clear_database.py")
    print(f"   4. Import fresh: python scripts/import_questions.py")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
