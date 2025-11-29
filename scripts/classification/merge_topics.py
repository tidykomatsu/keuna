"""
Merge topics from historical classifications into fresh extraction.
Replaces the Gemini API classification step.

Input:
    - merged_all.json (fresh extraction, topics may be empty)
    - questions_categorized.json (historical, only use question_id + topic)
    - manual_topics.csv (optional overrides)

Output:
    - questions_final.json (ready for import)
    - unclassified_report.csv (questions still without topic)

Manual topics CSV format:
    question_id,topic
    some_id,Cardiología
    another_id,Neurología
"""

import sys
import io
import json
import csv
from pathlib import Path
from collections import Counter
import polars as pl
from sys import path as sys_path

# Fix encoding on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ============================================================================
# Configuration
# ============================================================================

# Add parent directory to path to import from extraction
SCRIPT_DIR = Path(__file__).parent
EXTRACTION_DIR = SCRIPT_DIR.parent / "extraction"
sys_path.insert(0, str(EXTRACTION_DIR))

from config import get_processed_data_root
from utils import save_questions, print_extraction_summary, validate_question_strict

PROCESSED_DIR = get_processed_data_root()

# Input: data/processed/extracted.json (output of extract_all.py)
FRESH_FILE = PROCESSED_DIR / "extracted.json"

# Historical topics (Gemini API classification) - used as lookup for missing topics
HISTORICAL_FILE = PROCESSED_DIR / "questions_categorized.json"

# Optional manual overrides
MANUAL_FILE = PROCESSED_DIR / "manual_topics.csv"

# Output: data/processed/questions_ready.json (ready for import)
OUTPUT_FINAL = PROCESSED_DIR / "questions_ready.json"
UNCLASSIFIED_REPORT = PROCESSED_DIR / "unclassified_report.csv"

# 24 valid topics
VALID_TOPICS = [
    "Gastroenterología",
    "Nefrología",
    "Cardiología",
    "Infectología",
    "Diabetes",
    "Endocrinología",
    "Respiratorio",
    "Neurología",
    "Reumatología",
    "Hematología",
    "Geriatría",
    "Psiquiatría",
    "Salud Pública",
    "Dermatología",
    "Otorrinolaringología",
    "Oftalmología",
    "Traumatología",
    "Urología",
    "Cirugía",
    "Anestesiología",
    "Obstetricia",
    "Ginecología",
    "Pediatría",
    "Medicina Legal",
]


# ============================================================================
# Loading Functions
# ============================================================================


def load_fresh_extraction() -> list[dict]:
    """Load fresh extraction JSON file"""
    assert FRESH_FILE.exists(), f"Fresh extraction file not found: {FRESH_FILE}"

    with open(FRESH_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    assert isinstance(questions, list), "Fresh extraction must be a list"
    assert len(questions) > 0, "Fresh extraction is empty"

    print(f"✅ Loaded {len(questions)} questions from {FRESH_FILE.name}")

    return questions


def load_historical_topics() -> pl.DataFrame:
    """Load historical topics as DataFrame (only question_id, topic)"""
    if not HISTORICAL_FILE.exists():
        print(f"ℹ️  Historical file not found: {HISTORICAL_FILE.name} (optional)")
        return pl.DataFrame({"question_id": [], "topic": []})

    with open(HISTORICAL_FILE, "r", encoding="utf-8") as f:
        historical = json.load(f)

    assert isinstance(historical, list), "Historical file must be a list"

    # Create DataFrame with only question_id and topic columns
    df = pl.DataFrame(historical).select(["question_id", "topic"])

    print(f"✅ Loaded {len(df)} historical topics from {HISTORICAL_FILE.name}")

    return df


def load_manual_overrides() -> pl.DataFrame | None:
    """Load manual topic overrides if file exists"""
    if not MANUAL_FILE.exists():
        print("ℹ️  No manual_topics.csv found (optional)")
        return None

    df = pl.read_csv(MANUAL_FILE)

    # Validate schema
    assert "question_id" in df.columns, "manual_topics.csv must have 'question_id' column"
    assert "topic" in df.columns, "manual_topics.csv must have 'topic' column"

    # Validate all topics are in valid list
    invalid_topics = df.filter(~pl.col("topic").is_in(VALID_TOPICS))
    assert len(invalid_topics) == 0, \
        f"manual_topics.csv contains invalid topics: {invalid_topics['topic'].unique().to_list()}"

    print(f"✅ Loaded {len(df)} manual topic overrides")

    return df


# ============================================================================
# Topic Merging
# ============================================================================


def merge_topics(
    fresh_questions: list[dict],
    historical_df: pl.DataFrame,
    manual_df: pl.DataFrame | None
) -> tuple[list[dict], list[dict]]:
    """
    Merge topics with priority:
    1. If fresh topic != "" → keep it (from mi_eunacom_topics)
    2. Else if manual_df has it → use manual
    3. Else if historical_df has it → use historical
    4. Else → "Sin clasificar"

    Returns:
        tuple: (questions_with_topics, unclassified_questions)
    """

    # Create lookup dicts for efficiency
    historical_dict = {row["question_id"]: row["topic"]
                       for row in historical_df.iter_rows(named=True)}

    manual_dict = {}
    if manual_df is not None:
        manual_dict = {row["question_id"]: row["topic"]
                       for row in manual_df.iter_rows(named=True)}

    unclassified_questions = []
    merged_questions = []

    stats = {
        "already_had_topic": 0,
        "matched_from_historical": 0,
        "matched_from_manual": 0,
        "still_unclassified": 0
    }

    for q in fresh_questions:
        q_id = q.get("question_id", "")
        current_topic = q.get("topic", "").strip()

        # Priority 1: Keep if fresh topic already exists
        if current_topic and current_topic != "":
            # Validate it's in valid topics
            assert current_topic in VALID_TOPICS, \
                f"Question {q_id} has invalid topic: '{current_topic}'"
            stats["already_had_topic"] += 1
            merged_questions.append(q)
            continue

        # Priority 2: Check manual overrides
        if q_id in manual_dict:
            q["topic"] = manual_dict[q_id]
            stats["matched_from_manual"] += 1
            merged_questions.append(q)
            continue

        # Priority 3: Check historical
        if q_id in historical_dict:
            q["topic"] = historical_dict[q_id]
            stats["matched_from_historical"] += 1
            merged_questions.append(q)
            continue

        # Priority 4: Mark as unclassified
        q["topic"] = "Sin clasificar"
        stats["still_unclassified"] += 1
        merged_questions.append(q)
        unclassified_questions.append(q)

    print(f"\n{'='*60}")
    print(f"📊 TOPIC MERGE SUMMARY")
    print(f"{'='*60}")
    print(f"Total questions: {len(merged_questions)}")
    print(f"  ✅ Already had topic: {stats['already_had_topic']}")
    print(f"  📝 Matched from manual: {stats['matched_from_manual']}")
    print(f"  📚 Matched from historical: {stats['matched_from_historical']}")
    print(f"  ❌ Still unclassified: {stats['still_unclassified']}")

    return merged_questions, unclassified_questions


# ============================================================================
# Topic Distribution
# ============================================================================


def print_topic_distribution(questions: list[dict]):
    """Print distribution of topics across all questions"""
    topics = [q.get("topic", "Sin clasificar") for q in questions]
    topic_counts = Counter(topics)

    print(f"\n{'='*60}")
    print(f"📊 TOPIC DISTRIBUTION")
    print(f"{'='*60}")

    # Sort by count descending
    for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
        pct = (count / len(questions)) * 100
        bar_length = int(pct / 2)  # Scale to 50 chars max
        bar = "█" * bar_length
        print(f"{topic:25s} │ {count:4d} ({pct:5.1f}%) {bar}")

    print(f"{'='*60}")


# ============================================================================
# Unclassified Report
# ============================================================================


def save_unclassified_report(unclassified: list[dict]):
    """Save CSV report of unclassified questions"""
    if len(unclassified) == 0:
        print(f"✅ No unclassified questions - skipping report")
        return

    with open(UNCLASSIFIED_REPORT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["question_id", "question_text", "source_type"])
        writer.writeheader()

        for q in unclassified:
            text = q.get("question_text", "")[:100]  # First 100 chars
            writer.writerow({
                "question_id": q.get("question_id", ""),
                "question_text": text,
                "source_type": q.get("source_type", "")
            })

    print(f"✅ Saved unclassified report: {UNCLASSIFIED_REPORT.name}")
    print(f"   {len(unclassified)} questions still need classification")


# ============================================================================
# Main
# ============================================================================


def main():
    """Main pipeline"""

    print("\n" + "="*60)
    print("🔄 TOPIC MERGE PIPELINE")
    print("="*60 + "\n")

    # Load inputs
    print("📂 Loading files...")
    fresh_questions = load_fresh_extraction()
    historical_df = load_historical_topics()
    manual_df = load_manual_overrides()

    # Merge topics
    print("\n🔗 Merging topics with priority logic...")
    merged_questions, unclassified = merge_topics(fresh_questions, historical_df, manual_df)

    # Print statistics
    print_topic_distribution(merged_questions)

    # Save outputs
    print(f"\n💾 Saving outputs...")

    # Validate before saving
    print(f"🔍 Validating {len(merged_questions)} questions...")
    # Note: not using full assert_questions_valid to allow partial data
    total_issues = 0
    for q in merged_questions:
        issues = validate_question_strict(q, raise_on_error=False)
        total_issues += len(issues)

    if total_issues > 0:
        print(f"⚠️  WARNING: {total_issues} validation issues found (saving anyway)")

    # Save to project root
    OUTPUT_FINAL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FINAL, "w", encoding="utf-8") as f:
        json.dump(merged_questions, f, ensure_ascii=False, indent=2)

    assert OUTPUT_FINAL.exists(), f"Failed to create output file: {OUTPUT_FINAL}"
    print(f"✅ Saved merged questions: {OUTPUT_FINAL.name}")

    # Save unclassified report
    save_unclassified_report(unclassified)

    print(f"\n{'='*60}")
    print("✅ MERGE COMPLETE!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
