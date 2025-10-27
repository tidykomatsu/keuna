"""
Load, merge, and categorize medical questions using Gemini API
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
import polars as pl
from google import genai

# ============================================================================
# Configuration
# ============================================================================
from dotenv import load_dotenv

load_dotenv()

TEST_MODE = False  # ← Set to False for full run
TEST_ROWS = 15

CATEGORIES = [
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
    "Other",
]

API_KEY = os.getenv("GEMINI_API_KEY")
assert API_KEY, "Set GEMINI_API_KEY environment variable"

client = genai.Client(api_key=API_KEY)
MODEL = "gemini-2.5-flash-lite"

PROJECT_ROOT = Path(__file__).parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

GUEVARA_FILE = PROCESSED_DIR / "guevara_20251026_180614.json"
MI_EUNACOM_FILE = PROCESSED_DIR / "mi_eunacom_20251026_171423.json"
CHECKPOINT_FILE = PROCESSED_DIR / "categorization_checkpoint.json"
OUTPUT_FILE = PROCESSED_DIR / "questions_categorized.json"

CHECKPOINT_INTERVAL = 5  # Save every 5 questions


# ============================================================================
# Load and Merge
# ============================================================================


def load_and_merge() -> pl.DataFrame:
    """Load both JSON files and merge into single DataFrame"""

    with open(GUEVARA_FILE, "r", encoding="utf-8") as f:
        guevara_questions = json.load(f)

    with open(MI_EUNACOM_FILE, "r", encoding="utf-8") as f:
        mi_eunacom_questions = json.load(f)

    df_guevara = pl.DataFrame(guevara_questions)
    df_mi_eunacom = pl.DataFrame(mi_eunacom_questions)

    df_merged = pl.concat([df_guevara, df_mi_eunacom])
    df_merged = df_merged.unique(subset=["question_id"], keep="first")

    print(f"✅ Loaded {len(df_guevara)} from Guevara")
    print(f"✅ Loaded {len(df_mi_eunacom)} from MI_EUNACOM")
    print(f"✅ Merged total: {len(df_merged)} questions\n")

    return df_merged


# ============================================================================
# Categorization
# ============================================================================


def build_prompt(question_text: str, correct_answer: str, explanation: str) -> str:
    """Build categorization prompt"""

    categories_str = ", ".join(CATEGORIES[:-1])

    return f"""Categoriza esta pregunta médica en UNA de estas especialidades:
{categories_str}

Si no encaja claramente, responde "Other".

PREGUNTA: {question_text}

RESPUESTA CORRECTA: {correct_answer}

EXPLICACIÓN: {explanation}

Responde SOLO con el nombre de la especialidad."""


def categorize_question(question_text: str, correct_answer: str, explanation: str) -> str:
    """Categorize single question with retry logic"""

    prompt = build_prompt(question_text, correct_answer, explanation)

    for attempt in range(3):
        try:
            response = client.models.generate_content(model=MODEL, contents=prompt)

            category = response.text.strip()

            if category in CATEGORIES:
                return category

            for valid_cat in CATEGORIES:
                if valid_cat.lower() in category.lower():
                    return valid_cat

            return "Other"

        except Exception as e:
            if "429" in str(e):
                wait = (attempt + 1) * 2
                print(f"\n  ⏳ Rate limit hit, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"\n  ❌ Error: {e}")
                return "Other"

    return "Other"


# ============================================================================
# Progress Tracking
# ============================================================================


def format_time(seconds: float) -> str:
    """Format seconds into readable time string"""

    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        mins = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds / 3600)
        mins = int((seconds % 3600) / 60)
        return f"{hours}h {mins}m"


def print_progress(current: int, total: int, category: str, elapsed: float, avg_time: float):
    """Print detailed progress information"""

    pct = (current / total) * 100
    remaining = total - current
    eta_seconds = remaining * avg_time

    elapsed_str = format_time(elapsed)
    eta_str = format_time(eta_seconds)

    # Progress bar
    bar_length = 30
    filled = int(bar_length * current / total)
    bar = "█" * filled + "░" * (bar_length - filled)

    print(f"[{current}/{total}] {bar} {pct:5.1f}% | " f"⏱️ {elapsed_str} | ETA {eta_str} | ✅ {category}")


# ============================================================================
# Batch Processing with Checkpointing
# ============================================================================


def load_checkpoint() -> dict:
    """Load checkpoint if exists"""

    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, "r") as f:
            return json.load(f)

    return {"categorized": {}, "last_index": 0, "start_time": None}


def save_checkpoint(checkpoint: dict):
    """Save checkpoint"""

    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint, f, indent=2)


def categorize_dataframe(df: pl.DataFrame, delay: float = 1.0) -> pl.DataFrame:
    """
    Categorize all questions in DataFrame with detailed tracking

    Args:
        df: Input DataFrame
        delay: Seconds between API calls

    Returns:
        DataFrame with 'topic' column updated
    """

    checkpoint = load_checkpoint()
    start_idx = checkpoint["last_index"]
    categorized_dict = checkpoint["categorized"]

    total = len(df)

    # Track timing
    if checkpoint.get("start_time"):
        start_time = datetime.fromisoformat(checkpoint["start_time"])
        print(f"📌 Resuming from question {start_idx + 1}/{total}")
        print(f"   Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    else:
        start_time = datetime.now()
        checkpoint["start_time"] = start_time.isoformat()

    # Calculate estimated time
    questions_to_process = total - start_idx
    estimated_seconds = questions_to_process * (delay + 0.5)  # +0.5 for API time
    estimated_time = format_time(estimated_seconds)

    print(f"🔍 Categorizing {questions_to_process} questions")
    print(f"⏱️  Estimated time: {estimated_time}")
    print(f"💾 Auto-save every {CHECKPOINT_INTERVAL} questions\n")
    print("=" * 80)

    # Track average processing time
    processing_times = []
    avg_time = 1.5  # Default fallback
    questions_processed = 0

    for idx, row in enumerate(df.iter_rows(named=True)):
        if idx < start_idx:
            continue

        question_id = row["question_id"]

        if question_id in categorized_dict:
            continue

        # Start timing this question
        q_start = time.time()

        category = categorize_question(row["question_text"], row["correct_answer"], row["explanation"])

        categorized_dict[question_id] = category
        questions_processed += 1

        # Calculate timing
        q_elapsed = time.time() - q_start
        processing_times.append(q_elapsed)
        avg_time = sum(processing_times) / len(processing_times)

        total_elapsed = (datetime.now() - start_time).total_seconds()

        # Print progress
        print_progress(idx + 1, total, category, total_elapsed, avg_time)

        # Save checkpoint every N questions
        if questions_processed % CHECKPOINT_INTERVAL == 0:
            checkpoint["categorized"] = categorized_dict
            checkpoint["last_index"] = idx + 1
            save_checkpoint(checkpoint)
            print(f"   💾 Checkpoint saved ({idx + 1}/{total})")

        if idx < total - 1:
            time.sleep(delay)

    # Final checkpoint
    checkpoint["categorized"] = categorized_dict
    checkpoint["last_index"] = total
    save_checkpoint(checkpoint)

    print("=" * 80)

    total_time = (datetime.now() - start_time).total_seconds()
    print(f"\n⏱️  Total processing time: {format_time(total_time)}")

    if questions_processed > 0:
        print(f"📊 Average time per question: {avg_time:.2f}s")

    print()

    # Create category column
    categories = [categorized_dict.get(row["question_id"], "Other") for row in df.iter_rows(named=True)]

    result_df = df.with_columns(pl.Series("gemini_category", categories))

    return result_df


# ============================================================================
# Statistics
# ============================================================================


def print_stats(df: pl.DataFrame):
    """Print categorization statistics"""

    stats = df.group_by("gemini_category").agg(pl.len().alias("count")).sort("count", descending=True)

    print("=" * 60)
    print("📊 CATEGORIZATION RESULTS")
    print("=" * 60)

    for row in stats.iter_rows(named=True):
        category = row["gemini_category"]
        count = row["count"]
        pct = (count / len(df)) * 100
        print(f"{category:25s}: {count:4d} ({pct:5.1f}%)")

    print("=" * 60)


# ============================================================================
# Main
# ============================================================================


def main():
    """Main pipeline"""

    print("\n" + "=" * 60)
    if TEST_MODE:
        print(f"🧪 TEST MODE - Processing {TEST_ROWS} questions only")
    else:
        print("🚀 FULL RUN - Categorizing all questions")
    print(f"🤖 Model: {MODEL}")
    print("=" * 60 + "\n")

    # Load and merge
    df = load_and_merge()

    # Test mode: take only first N rows
    if TEST_MODE:
        df = df.head(TEST_ROWS)
        print(f"🧪 Testing with {len(df)} questions\n")

    # Categorize
    df_categorized = categorize_dataframe(df, delay=1.0)

    # Update topic column
    df_categorized = df_categorized.with_columns(pl.col("gemini_category").alias("topic")).drop("gemini_category")

    # Stats
    print_stats(df_categorized.select(pl.col("topic").alias("gemini_category")))

    # Save
    if TEST_MODE:
        output_file = PROCESSED_DIR / "questions_categorized_TEST.json"
    else:
        output_file = OUTPUT_FILE

    questions_list = df_categorized.to_dicts()

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(questions_list, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Saved to: {output_file.relative_to(PROJECT_ROOT)}")

    # Clean up checkpoint (only in full mode)
    if not TEST_MODE and CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        print("🗑️  Checkpoint file removed")

    print("\n" + "=" * 60)
    if TEST_MODE:
        print("✅ TEST COMPLETE!")
        print("\nSet TEST_MODE = False to run full categorization")
    else:
        print("✅ CATEGORIZATION COMPLETE!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
