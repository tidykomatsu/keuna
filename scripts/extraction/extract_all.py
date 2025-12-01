"""Master extraction script - runs all extractors, merges, and enriches topics.

This script:
1. Extracts questions from all sources (mi_eunacom, guevara, reconstrucciones)
2. Merges and deduplicates across sources
3. Enriches topics from historical data (questions_categorized.json)
4. Outputs questions_ready.json ready for database import
"""
from pathlib import Path
import json
from collections import Counter
from extract_mi_eunacom import extract_all_mi_eunacom
from extract_mi_eunacom_topics import extract_all_mi_eunacom_topics
from extract_guevara import extract_all_guevara
from extract_reconstrucciones import extract_all_reconstrucciones
from utils import save_questions, print_extraction_summary
from config import get_raw_data_root, get_processed_data_root


# ============================================================================
# Valid Topics (24 categories)
# ============================================================================

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


# ============================================================================
# Topic Enrichment (from merge_topics.py)
# ============================================================================


def load_historical_topics(processed_dir: Path) -> dict[str, str]:
    """Load historical topics as dict (question_id -> topic)"""
    historical_file = processed_dir / "questions_categorized.json"

    if not historical_file.exists():
        print(f"ℹ️  Historical file not found: {historical_file.name} (optional)")
        return {}

    with open(historical_file, "r", encoding="utf-8") as f:
        historical = json.load(f)

    assert isinstance(historical, list), "Historical file must be a list"

    # Create dict with question_id -> topic
    historical_dict = {
        q["question_id"]: q.get("topic", "")
        for q in historical
        if q.get("question_id")
    }

    print(f"✅ Loaded {len(historical_dict)} historical topics from {historical_file.name}")
    return historical_dict


def enrich_topics(questions: list[dict], historical_topics: dict[str, str]) -> tuple[list[dict], dict]:
    """
    Enrich questions with topics from historical data.

    Priority:
    1. Keep existing topic if present (from mi_eunacom_topics)
    2. Use historical topic if available
    3. Mark as "Sin clasificar"

    Returns: (enriched_questions, stats_dict)
    """
    stats = {
        "already_had_topic": 0,
        "matched_from_historical": 0,
        "still_unclassified": 0,
    }

    for q in questions:
        q_id = q.get("question_id", "")
        current_topic = q.get("topic", "").strip()

        # Priority 1: Keep existing topic
        if current_topic:
            assert current_topic in VALID_TOPICS, \
                f"Question {q_id} has invalid topic: '{current_topic}'"
            stats["already_had_topic"] += 1
            continue

        # Priority 2: Use historical topic
        if q_id in historical_topics and historical_topics[q_id]:
            q["topic"] = historical_topics[q_id]
            stats["matched_from_historical"] += 1
            continue

        # Priority 3: Mark as unclassified
        q["topic"] = "Sin clasificar"
        stats["still_unclassified"] += 1

    return questions, stats


def print_topic_distribution(questions: list[dict]):
    """Print distribution of topics across all questions"""
    topics = [q.get("topic", "Sin clasificar") for q in questions]
    topic_counts = Counter(topics)

    print(f"\n{'='*60}")
    print("TOPIC DISTRIBUTION")
    print(f"{'='*60}")

    # Sort by count descending
    for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
        pct = (count / len(questions)) * 100
        bar_length = int(pct / 2)  # Scale to 50 chars max
        bar = "#" * bar_length
        print(f"{topic:25s} | {count:4d} ({pct:5.1f}%) {bar}")

    print(f"{'='*60}")


def main():
    """Run all extractors, merge, enrich topics, and save ready for import"""
    processed_dir = get_processed_data_root()

    print("\n" + "="*60)
    print("MASTER EXTRACTION - ALL SOURCES (WITH IMAGES)")
    print("="*60)
    print(f"Raw data from: {get_raw_data_root()}")
    print(f"Output to: {processed_dir}")
    print("="*60)

    # Extract from all sources
    mi_eunacom_questions = extract_all_mi_eunacom()
    mi_eunacom_topics_questions = extract_all_mi_eunacom_topics()
    guevara_questions = extract_all_guevara()
    reconstrucciones_questions = extract_all_reconstrucciones()

    # Merge
    print(f"\n{'='*60}")
    print("MERGING ALL SOURCES")
    print(f"{'='*60}")

    all_questions = merge_and_deduplicate([
        reconstrucciones_questions,
        mi_eunacom_questions,
        mi_eunacom_topics_questions,
        guevara_questions,



    ])

    print_extraction_summary(all_questions, "MERGED (ALL SOURCES)")

    # Enrich topics from historical data
    print(f"\n{'='*60}")
    print("ENRICHING TOPICS FROM HISTORICAL DATA")
    print(f"{'='*60}")

    historical_topics = load_historical_topics(processed_dir)
    all_questions, topic_stats = enrich_topics(all_questions, historical_topics)

    print(f"\nTopic enrichment summary:")
    print(f"  Already had topic: {topic_stats['already_had_topic']}")
    print(f"  Matched from historical: {topic_stats['matched_from_historical']}")
    print(f"  Still unclassified: {topic_stats['still_unclassified']}")

    # Print topic distribution
    print_topic_distribution(all_questions)

    # Save final output as questions_ready.json
    output_file = processed_dir / "questions_ready.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_questions, f, ensure_ascii=False, indent=2)

    print(f"\nSaved: {output_file}")

    # Image summary
    with_images = sum(1 for q in all_questions if q.get("images"))
    total_images = sum(len(q.get("images", [])) for q in all_questions)

    # Reconstruction summary
    recon_questions = [q for q in all_questions if q.get("reconstruction_name")]
    recon_names = set(q.get("reconstruction_name") for q in recon_questions)

    print(f"\n{'='*60}")
    print("EXTRACTION COMPLETE!")
    print(f"{'='*60}")
    print(f"\nSummary:")
    print(f"   Total questions: {len(all_questions)}")
    print(f"   With images: {with_images}")
    print(f"   Total image URLs: {total_images}")
    print(f"   Reconstrucciones: {len(recon_questions)} questions in {len(recon_names)} exams")
    print(f"\nPipeline:")
    print(f"   1. (done) extract_all.py             -> questions_ready.json")
    print(f"   2. migrate_images_to_supabase.py     -> image_mappings.json (optional)")
    print(f"   3. import_questions.py               -> merges + inserts to DB")


if __name__ == "__main__":
    main()
