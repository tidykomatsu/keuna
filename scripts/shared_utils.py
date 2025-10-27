"""Shared utilities for all extractors"""

from pathlib import Path
import json
from datetime import datetime


def save_questions(questions: list[dict], output_name: str) -> Path:
    """Save questions to JSON with timestamp"""
    project_root = Path(__file__).parent.parent
    processed_dir = project_root / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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

    # Source files breakdown
    source_files = {}
    for q in questions:
        src = q.get("source_file", "unknown")
        source_files[src] = source_files.get(src, 0) + 1

    print(f"\n📁 Questions by source file:")
    for src, count in sorted(source_files.items()):
        print(f"   {src}: {count}")
