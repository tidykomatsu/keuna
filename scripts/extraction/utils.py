"""Shared utilities for all extractors - WITH IMAGE SUPPORT AND ASSERTIONS"""

from pathlib import Path
import json
from datetime import datetime
from config import get_processed_data_root


# ============================================================================
# Schema Definition
# ============================================================================

QUESTION_SCHEMA = {
    "question_id": str,
    "question_number": str,
    "topic": str,
    "question_text": str,
    "answer_options": list,
    "correct_answer": str,
    "explanation": str,
    "images": list,
    "source_file": str,
    "source_type": str,
}

ANSWER_OPTION_SCHEMA = {
    "letter": str,
    "text": str,
    "explanation": str,
    "is_correct": bool,
}


# ============================================================================
# Validation with Assertions
# ============================================================================

def validate_question_strict(q: dict, raise_on_error: bool = True) -> list[str]:
    """
    Validate single question structure with strict assertions.
    
    Args:
        q: Question dict to validate
        raise_on_error: If True, raises AssertionError on first issue
        
    Returns:
        List of issues found (empty if valid)
    """
    issues = []
    q_id = q.get("question_id", "UNKNOWN")
    
    # Required fields
    for field, expected_type in QUESTION_SCHEMA.items():
        if field not in q:
            issues.append(f"[{q_id}] Missing required field: {field}")
            continue
        
        # Type check (allow None for optional string fields)
        value = q[field]
        if field in ("topic", "explanation", "source_file") and value is None:
            continue  # These can be None
        
        if not isinstance(value, expected_type):
            issues.append(f"[{q_id}] Field '{field}' has wrong type: expected {expected_type.__name__}, got {type(value).__name__}")
    
    # question_id must not be empty
    if not q.get("question_id", "").strip():
        issues.append(f"[{q_id}] Empty question_id")
    
    # question_text must not be empty
    if not q.get("question_text", "").strip():
        issues.append(f"[{q_id}] Empty question_text")
    
    # answer_options validation
    opts = q.get("answer_options", [])
    if not isinstance(opts, list):
        issues.append(f"[{q_id}] answer_options is not a list")
    elif len(opts) == 0:
        issues.append(f"[{q_id}] No answer options")
    else:
        # Validate each option
        for i, opt in enumerate(opts):
            if not isinstance(opt, dict):
                issues.append(f"[{q_id}] answer_options[{i}] is not a dict")
                continue
            
            for field in ["letter", "text", "is_correct"]:
                if field not in opt:
                    issues.append(f"[{q_id}] answer_options[{i}] missing '{field}'")
        
        # Must have exactly one correct answer
        correct_count = sum(1 for opt in opts if opt.get("is_correct", False))
        if correct_count == 0:
            issues.append(f"[{q_id}] No correct answer marked")
        elif correct_count > 1:
            issues.append(f"[{q_id}] Multiple correct answers marked ({correct_count})")
    
    # images must be a list (can be empty)
    images = q.get("images", [])
    if not isinstance(images, list):
        issues.append(f"[{q_id}] 'images' field is not a list")
    else:
        for i, img in enumerate(images):
            if not isinstance(img, str):
                issues.append(f"[{q_id}] images[{i}] is not a string")
    
    if raise_on_error and issues:
        raise AssertionError(f"Validation failed:\n" + "\n".join(issues))
    
    return issues


def validate_question(q: dict) -> list[str]:
    """Validate single question structure. Returns list of issues (non-strict mode)."""
    return validate_question_strict(q, raise_on_error=False)


def assert_no_duplicate_ids(questions: list[dict], source_name: str = ""):
    """
    Assert that all question IDs are unique.
    Fails fast with detailed error message if duplicates found.
    """
    seen_ids = {}
    duplicates = []
    
    for q in questions:
        q_id = q.get("question_id", "")
        if q_id in seen_ids:
            duplicates.append({
                "id": q_id,
                "first_source": seen_ids[q_id],
                "duplicate_source": q.get("source_file", "unknown")
            })
        else:
            seen_ids[q_id] = q.get("source_file", "unknown")
    
    if duplicates:
        error_msg = f"DUPLICATE IDS FOUND in {source_name or 'questions'}:\n"
        for dup in duplicates[:10]:  # Show first 10
            error_msg += f"  - ID '{dup['id']}': first in {dup['first_source']}, duplicate in {dup['duplicate_source']}\n"
        if len(duplicates) > 10:
            error_msg += f"  ... and {len(duplicates) - 10} more duplicates\n"
        
        raise AssertionError(error_msg)


def assert_questions_valid(questions: list[dict], source_name: str = ""):
    """
    Assert all questions pass validation.
    Collects all issues before failing.
    """
    all_issues = []
    
    for q in questions:
        issues = validate_question_strict(q, raise_on_error=False)
        all_issues.extend(issues)
    
    if all_issues:
        error_msg = f"VALIDATION FAILED for {source_name or 'questions'} ({len(all_issues)} issues):\n"
        for issue in all_issues[:20]:  # Show first 20
            error_msg += f"  - {issue}\n"
        if len(all_issues) > 20:
            error_msg += f"  ... and {len(all_issues) - 20} more issues\n"
        
        raise AssertionError(error_msg)


# ============================================================================
# Save with Validation
# ============================================================================

def save_questions(questions: list[dict], output_name: str, validate: bool = True) -> Path:
    """
    Save questions to JSON with optional validation.
    
    Args:
        questions: List of question dicts
        output_name: Output filename (without extension)
        validate: If True, validates before saving (default: True)
    """
    # Pre-save assertions
    assert isinstance(questions, list), "questions must be a list"
    assert len(questions) > 0, "questions list is empty"
    
    if validate:
        print(f"🔍 Validating {len(questions)} questions...")
        assert_no_duplicate_ids(questions, output_name)
        # Note: not using assert_questions_valid here to allow partial data
        # but we log issues
        total_issues = 0
        for q in questions:
            issues = validate_question_strict(q, raise_on_error=False)
            total_issues += len(issues)
        
        if total_issues > 0:
            print(f"⚠️  WARNING: {total_issues} validation issues found (saving anyway)")
    
    processed_dir = get_processed_data_root()
    output_file = processed_dir / f"{output_name}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    
    # Post-save verification
    assert output_file.exists(), f"Failed to create output file: {output_file}"
    
    with open(output_file, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
    
    assert len(saved_data) == len(questions), \
        f"Data mismatch: saved {len(saved_data)}, expected {len(questions)}"

    return output_file


# ============================================================================
# Summary Printing
# ============================================================================

def print_extraction_summary(questions: list[dict], source_name: str):
    """Print summary of extracted questions with validation report"""
    print(f"\n{'='*60}")
    print(f"📊 EXTRACTION SUMMARY - {source_name}")
    print(f"{'='*60}")
    print(f"Total questions: {len(questions)}")

    # Check for duplicates
    ids = [q.get("question_id", "") for q in questions]
    unique_ids = set(ids)
    if len(ids) != len(unique_ids):
        print(f"❌ DUPLICATE IDS: {len(ids) - len(unique_ids)} duplicates found!")
    else:
        print(f"✅ All {len(unique_ids)} IDs are unique")

    # Validate all
    issues_by_type = {}
    for q in questions:
        issues = validate_question_strict(q, raise_on_error=False)
        for issue in issues:
            # Extract issue type (first part after ID)
            issue_type = issue.split("]")[1].strip() if "]" in issue else issue
            issues_by_type[issue_type] = issues_by_type.get(issue_type, 0) + 1

    if not issues_by_type:
        print("✅ All questions validated successfully!")
    else:
        print(f"⚠️  Validation issues found:")
        for issue_type, count in sorted(issues_by_type.items(), key=lambda x: -x[1]):
            print(f"   - {issue_type}: {count}")

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
