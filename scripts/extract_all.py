"""Master extraction script - runs all extractors and merges results"""
from pathlib import Path
import json
from datetime import datetime
from extract_mi_eunacom import extract_all_mi_eunacom
from extract_guevara import extract_all_guevara
from shared_utils import save_questions, print_extraction_summary


def merge_and_deduplicate(questions_list: list[list[dict]]) -> list[dict]:
    """Merge multiple question lists and remove duplicates"""
    all_questions = []
    for questions in questions_list:
        all_questions.extend(questions)

    # Deduplicate by question_text (fuzzy match could be added later)
    seen_texts = set()
    unique_questions = []

    for q in all_questions:
        text_key = q["question_text"][:100].strip().lower()  # First 100 chars
        if text_key not in seen_texts:
            seen_texts.add(text_key)
            unique_questions.append(q)

    duplicates = len(all_questions) - len(unique_questions)
    if duplicates > 0:
        print(f"\n⚠️  Removed {duplicates} cross-source duplicates")

    return unique_questions


def main():
    """Run all extractors and create merged database"""
    print("\n" + "="*60)
    print("🚀 MASTER EXTRACTION - ALL SOURCES")
    print("="*60)

    # Extract from all sources
    mi_eunacom_questions = extract_all_mi_eunacom()
    guevara_questions = extract_all_guevara()

    # Merge
    print(f"\n{'='*60}")
    print("MERGING ALL SOURCES")
    print(f"{'='*60}")

    all_questions = merge_and_deduplicate([
        mi_eunacom_questions,
        guevara_questions
    ])

    print_extraction_summary(all_questions, "MERGED (ALL SOURCES)")

    # Save merged
    output_file = save_questions(all_questions, "merged_all")
    print(f"\n💾 Merged database: {output_file}")

    # Copy to root as questions.json
    project_root = Path(__file__).parent.parent
    questions_json = project_root / "questions.json"

    with open(output_file, "r", encoding="utf-8") as f:
        data = f.read()

    with open(questions_json, "w", encoding="utf-8") as f:
        f.write(data)

    print(f"💾 Copied to: questions.json (for app)")

    print(f"\n{'='*60}")
    print("✅ EXTRACTION COMPLETE!")
    print(f"{'='*60}")
    print(f"\nNext steps:")
    print(f"  1. ✅ Questions extracted: {len(all_questions)}")
    print(f"  2. 🔄 Run topic classification (Gemini API) - Stage 3")
    print(f"  3. 🚀 Use questions.json in your app")


if __name__ == "__main__":
    main()