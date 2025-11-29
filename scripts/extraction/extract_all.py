"""Master extraction script - runs all extractors and merges results WITH IMAGE SUPPORT"""
from pathlib import Path
import json
from datetime import datetime
from extract_mi_eunacom import extract_all_mi_eunacom
from extract_mi_eunacom_topics import extract_all_mi_eunacom_topics
from extract_guevara import extract_all_guevara
from utils import save_questions, print_extraction_summary
from config import get_raw_data_root, get_processed_data_root


def merge_and_deduplicate(questions_list: list[list[dict]]) -> list[dict]:
    """Merge multiple question lists and remove duplicates"""
    all_questions = []
    for questions in questions_list:
        all_questions.extend(questions)

    # Deduplicate by question_text (fuzzy match could be added later)
    seen_texts = set()
    unique_questions = []

    for q in all_questions:
        text_key = q["question_text"][:100].strip().lower()
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
    print("🚀 MASTER EXTRACTION - ALL SOURCES (WITH IMAGES)")
    print("="*60)
    print(f"📂 Raw data from: {get_raw_data_root()}")
    print(f"📂 Output to: {get_processed_data_root()}")
    print("="*60)

    # Extract from all sources
    mi_eunacom_questions = extract_all_mi_eunacom()
    mi_eunacom_topics_questions = extract_all_mi_eunacom_topics()
    guevara_questions = extract_all_guevara()

    # Merge
    print(f"\n{'='*60}")
    print("MERGING ALL SOURCES")
    print(f"{'='*60}")

    all_questions = merge_and_deduplicate([
        mi_eunacom_questions,
        mi_eunacom_topics_questions,
        guevara_questions
    ])

    print_extraction_summary(all_questions, "MERGED (ALL SOURCES)")

    # Save merged - ONE canonical output location
    output_file = save_questions(all_questions, "extracted")
    print(f"\n💾 Extracted questions: {output_file}")

    # Image summary
    with_images = sum(1 for q in all_questions if q.get("images"))
    total_images = sum(len(q.get("images", [])) for q in all_questions)
    
    print(f"\n{'='*60}")
    print("✅ EXTRACTION COMPLETE!")
    print(f"{'='*60}")
    print(f"\n📊 Summary:")
    print(f"   Total questions: {len(all_questions)}")
    print(f"   📸 With images: {with_images}")
    print(f"   📸 Total image URLs: {total_images}")
    print(f"\nNext steps:")
    print(f"  1. ✅ Questions extracted: {output_file}")
    print(f"  2. 🔄 Run merge_topics.py to fill in missing topics")
    print(f"  3. 🚀 Import to database: python scripts/database/import_questions.py")


if __name__ == "__main__":
    main()
