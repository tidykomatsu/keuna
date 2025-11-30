"""
Standalone topic enrichment and image migration script.

NOTE: Topic enrichment is now integrated into extract_all.py, which outputs
questions_ready.json directly. This script is kept for:
1. Standalone topic re-enrichment if needed
2. Image migration from Moodle to Supabase Storage (not in extract_all.py)
3. Manual topic overrides via manual_topics.csv

For normal extraction workflow, just run extract_all.py which handles:
- Extraction from all sources
- Merge and deduplication
- Topic enrichment from historical data
- Output to questions_ready.json

Use this script when you need to:
- Migrate images to Supabase (requires MOODLE_SESSION)
- Apply manual topic overrides
- Re-run topic enrichment independently

Input:
    - extracted.json (fresh extraction, topics may be empty)
    - questions_categorized.json (historical, only use question_id + topic)
    - manual_topics.csv (optional overrides)

Output:
    - questions_ready.json (ready for import, with Supabase image URLs)
    - unclassified_report.csv (questions still without topic)

Manual topics CSV format:
    question_id,topic
    some_id,Cardiología
    another_id,Neurología

Environment variables required for image migration:
    - SUPABASE_URL
    - SUPABASE_SERVICE_ROLE_KEY
    - MOODLE_SESSION (get from browser when logged into Moodle)
"""

import sys
import io
import json
import csv
import os
import re
import time
from pathlib import Path
from collections import Counter
from urllib.parse import urlparse

import polars as pl
import requests
from dotenv import load_dotenv
from sys import path as sys_path

load_dotenv()

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
# Supabase Storage Configuration
# ============================================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
MOODLE_SESSION = os.getenv("MOODLE_SESSION", "")
BUCKET_NAME = "question-images"


# ============================================================================
# Image Migration Functions
# ============================================================================


def can_migrate_images() -> bool:
    """Check if image migration is possible"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    if not MOODLE_SESSION:
        return False
    return True


def get_supabase_client():
    """Initialize Supabase client"""
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def download_image(url: str, session: requests.Session) -> bytes | None:
    """Download image from Moodle URL"""
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "image" not in content_type and "octet-stream" not in content_type:
            print(f"  ⚠️  Not an image: {content_type}")
            return None

        return response.content
    except requests.RequestException as e:
        print(f"  ❌ Download failed: {e}")
        return None


def generate_storage_path(question_id: str, image_index: int, original_url: str) -> str:
    """Generate storage path for image"""
    parsed = urlparse(original_url)
    filename = parsed.path.split("/")[-1]
    ext = Path(filename).suffix or ".jpg"
    safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', question_id)
    return f"{safe_id}_{image_index}{ext}"


def upload_to_supabase(client, file_path: str, image_data: bytes) -> str | None:
    """Upload image to Supabase Storage and return public URL"""
    try:
        client.storage.from_(BUCKET_NAME).upload(
            file_path,
            image_data,
            {"content-type": "image/jpeg", "upsert": "true"}
        )
        return client.storage.from_(BUCKET_NAME).get_public_url(file_path)
    except Exception as e:
        print(f"  ❌ Upload failed: {e}")
        return None


def is_already_migrated(url: str) -> bool:
    """Check if URL is already a Supabase URL"""
    return "supabase" in url if url else True


def migrate_images(questions: list[dict]) -> list[dict]:
    """Migrate all images from Moodle to Supabase Storage"""

    if not can_migrate_images():
        print("\n⚠️  Image migration skipped (missing credentials or MOODLE_SESSION)")
        print("   Set MOODLE_SESSION in .env to enable image migration")
        return questions

    print(f"\n{'='*60}")
    print("🖼️  MIGRATING IMAGES TO SUPABASE")
    print(f"{'='*60}")

    # Setup HTTP session with Moodle cookies
    session = requests.Session()
    session.cookies.set("MoodleSession", MOODLE_SESSION, domain="cursosonline.doctorguevara.cl")
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

    # Setup Supabase client
    supabase = get_supabase_client()

    stats = {"total": 0, "migrated": 0, "skipped": 0, "failed": 0}

    questions_with_images = [q for q in questions if q.get("images")]
    print(f"📸 Found {len(questions_with_images)} questions with images")

    for question in questions_with_images:
        question_id = question["question_id"]
        new_images = []

        for idx, image_url in enumerate(question.get("images", []), 1):
            stats["total"] += 1

            if not image_url or is_already_migrated(image_url):
                new_images.append(image_url)
                stats["skipped"] += 1
                continue

            print(f"  📥 {question_id} img {idx}...", end=" ")

            # Download
            image_data = download_image(image_url, session)
            if not image_data:
                stats["failed"] += 1
                new_images.append(image_url)
                continue

            # Upload
            storage_path = generate_storage_path(question_id, idx, image_url)
            public_url = upload_to_supabase(supabase, storage_path, image_data)

            if public_url:
                stats["migrated"] += 1
                new_images.append(public_url)
                print("✅")
            else:
                stats["failed"] += 1
                new_images.append(image_url)

            time.sleep(0.1)  # Rate limiting

        question["images"] = new_images

    print(f"\n{'='*60}")
    print("📊 IMAGE MIGRATION SUMMARY")
    print(f"{'='*60}")
    print(f"  Total images:  {stats['total']}")
    print(f"  ✅ Migrated:   {stats['migrated']}")
    print(f"  ⏭️  Skipped:    {stats['skipped']} (already migrated)")
    print(f"  ❌ Failed:     {stats['failed']}")

    return questions


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
    print("🔄 TOPIC MERGE + IMAGE MIGRATION PIPELINE")
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

    # Migrate images to Supabase Storage
    merged_questions = migrate_images(merged_questions)

    # Validate before saving
    print(f"\n🔍 Validating {len(merged_questions)} questions...")
    total_issues = 0
    for q in merged_questions:
        issues = validate_question_strict(q, raise_on_error=False)
        total_issues += len(issues)

    if total_issues > 0:
        print(f"⚠️  WARNING: {total_issues} validation issues found (saving anyway)")

    # Save outputs
    print(f"\n💾 Saving outputs...")
    OUTPUT_FINAL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FINAL, "w", encoding="utf-8") as f:
        json.dump(merged_questions, f, ensure_ascii=False, indent=2)

    assert OUTPUT_FINAL.exists(), f"Failed to create output file: {OUTPUT_FINAL}"
    print(f"✅ Saved: {OUTPUT_FINAL.name}")

    # Save unclassified report
    save_unclassified_report(unclassified)

    # Final summary
    with_images = sum(1 for q in merged_questions if q.get("images"))
    supabase_images = sum(
        1 for q in merged_questions
        for img in q.get("images", [])
        if img and "supabase" in img
    )

    print(f"\n{'='*60}")
    print("✅ PIPELINE COMPLETE!")
    print(f"{'='*60}")
    print(f"   Total questions: {len(merged_questions)}")
    print(f"   With images: {with_images}")
    print(f"   Supabase URLs: {supabase_images}")
    print(f"\nNext step:")
    print(f"   python scripts/database/import_questions.py")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
