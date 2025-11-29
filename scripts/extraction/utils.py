"""Shared utilities for all extractors - WITH IMAGE SUPPORT"""

from pathlib import Path
import json
from datetime import datetime
from config import get_processed_data_root


def save_questions(questions: list[dict], output_name: str) -> Path:
    """Save questions to JSON with timestamp"""
    processed_dir = get_processed_data_root()
    output_file = processed_dir / f"{output_name}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    return output_file


def validate_question(q: dict) -> list[str]:
    """Validate single question structure. Returns list of issues."""
    issues = []

    if not q.get("question_text", "").strip():
        issues.append("Missing question_text")

    if not isinstance(q.get("answer_options"), list):
        issues.append("Invalid answer_options")
    elif len(q["answer_options"]) == 0:
        issues.append("No answer options")
    else:
        has_correct = any(opt.get("is_correct") for opt in q["answer_options"])
        if not has_correct:
            issues.append("No correct answer marked")

    if not q.get("explanation", "").strip():
        issues.append("Missing explanation")

    required_fields = ["question_id", "question_number", "source_file", "source_type"]
    for field in required_fields:
        if field not in q:
            issues.append(f"Missing {field}")

    # Images field is optional but should be a list if present
    if "images" in q and not isinstance(q["images"], list):
        issues.append("Invalid images field (should be list)")

    return issues


def print_extraction_summary(questions: list[dict], source_name: str):
    """Print summary of extracted questions"""
    print(f"\n{'='*60}")
    print(f"📊 EXTRACTION SUMMARY - {source_name}")
    print(f"{'='*60}")
    print(f"Total questions: {len(questions)}")

    # Validate all
    total_issues = 0
    for q in questions:
        issues = validate_question(q)
        total_issues += len(issues)

    if total_issues == 0:
        print("✅ All questions validated successfully!")
    else:
        print(f"⚠️  Found {total_issues} validation issues")

    # Image summary
    with_images = sum(1 for q in questions if q.get("images"))
    total_images = sum(len(q.get("images", [])) for q in questions)
    print(f"\n📸 Questions with images: {with_images}/{len(questions)}")
    print(f"📸 Total image URLs: {total_images}")

    # Source files breakdown
    source_files = {}
    for q in questions:
        src = q.get("source_file", "unknown")
        source_files[src] = source_files.get(src, 0) + 1

    print(f"\n📁 Questions by source file:")
    for src, count in sorted(source_files.items()):
        print(f"   {src}: {count}")
