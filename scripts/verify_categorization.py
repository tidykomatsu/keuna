"""
Quick verification script to check categorization status
"""

import json
from pathlib import Path
import polars as pl

# ============================================================================
# Configuration
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

GUEVARA_FILE = PROCESSED_DIR / "guevara.json"
MI_EUNACOM_FILE = PROCESSED_DIR / "mi_eunacom.json"
CHECKPOINT_FILE = PROCESSED_DIR / "categorization_checkpoint.json"
OUTPUT_FILE = PROCESSED_DIR / "questions_categorized.json"
TEST_OUTPUT_FILE = PROCESSED_DIR / "questions_categorized_TEST.json"

# ============================================================================
# Main Verification
# ============================================================================


def main():
    """Check categorization status"""

    print("\n" + "=" * 80)
    print("🔍 CATEGORIZATION STATUS CHECK")
    print("=" * 80 + "\n")

    # Check source files
    print("📂 SOURCE FILES:")
    if GUEVARA_FILE.exists():
        with open(GUEVARA_FILE, "r", encoding="utf-8") as f:
            guevara_count = len(json.load(f))
        print(f"   ✅ guevara.json: {guevara_count} questions")
    else:
        print(f"   ❌ guevara.json: NOT FOUND")
        guevara_count = 0

    if MI_EUNACOM_FILE.exists():
        with open(MI_EUNACOM_FILE, "r", encoding="utf-8") as f:
            mi_eunacom_count = len(json.load(f))
        print(f"   ✅ mi_eunacom.json: {mi_eunacom_count} questions")
    else:
        print(f"   ❌ mi_eunacom.json: NOT FOUND")
        mi_eunacom_count = 0

    # Calculate expected total (accounting for duplicates)
    if guevara_count > 0 and mi_eunacom_count > 0:
        with open(GUEVARA_FILE, "r", encoding="utf-8") as f:
            guevara_data = json.load(f)
        with open(MI_EUNACOM_FILE, "r", encoding="utf-8") as f:
            mi_eunacom_data = json.load(f)

        df_guevara = pl.DataFrame(guevara_data)
        df_mi_eunacom = pl.DataFrame(mi_eunacom_data)
        df_merged = pl.concat([df_guevara, df_mi_eunacom])
        df_merged = df_merged.unique(subset=["question_id"], keep="first")
        expected_total = len(df_merged)
        print(f"   📊 Expected unique total: {expected_total} questions")
    else:
        expected_total = 0

    print()

    # Check checkpoint
    print("💾 CHECKPOINT STATUS:")
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, "r") as f:
            checkpoint = json.load(f)

        last_idx = checkpoint.get("last_index", 0)
        categorized_count = len(checkpoint.get("categorized", {}))
        start_time = checkpoint.get("start_time")

        print(f"   ⚠️  CHECKPOINT EXISTS (processing incomplete)")
        print(f"   📍 Last processed index: {last_idx}")
        print(f"   ✅ Questions categorized: {categorized_count}")
        if start_time:
            print(f"   🕐 Started: {start_time}")

        if expected_total > 0:
            remaining = expected_total - last_idx
            pct = (last_idx / expected_total) * 100
            print(f"   📊 Progress: {pct:.1f}% ({remaining} remaining)")
    else:
        print(f"   ✅ No checkpoint (either complete or not started)")

    print()

    # Check output files
    print("📄 OUTPUT FILES:")

    # Test output
    if TEST_OUTPUT_FILE.exists():
        with open(TEST_OUTPUT_FILE, "r", encoding="utf-8") as f:
            test_data = json.load(f)
        print(f"   📝 questions_categorized_TEST.json: {len(test_data)} questions")
    else:
        print(f"   ⚪ questions_categorized_TEST.json: NOT FOUND")

    # Main output
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            output_data = json.load(f)

        output_count = len(output_data)
        file_size_kb = OUTPUT_FILE.stat().st_size / 1024

        print(f"   ✅ questions_categorized.json: {output_count} questions ({file_size_kb:.1f} KB)")

        # Analyze categorization quality
        df = pl.DataFrame(output_data)

        if "topic" in df.columns and "topic_confidence" in df.columns:
            # Confidence distribution
            low_conf = df.filter(pl.col("topic_confidence") < 0.5)
            med_conf = df.filter((pl.col("topic_confidence") >= 0.5) & (pl.col("topic_confidence") < 0.8))
            high_conf = df.filter(pl.col("topic_confidence") >= 0.8)

            print(f"\n   🎯 CONFIDENCE BREAKDOWN:")
            print(f"      🔴 Low (<0.5):    {len(low_conf):4d} ({len(low_conf)/len(df)*100:5.1f}%)")
            print(f"      🟡 Medium (≥0.5): {len(med_conf):4d} ({len(med_conf)/len(df)*100:5.1f}%)")
            print(f"      🟢 High (≥0.8):   {len(high_conf):4d} ({len(high_conf)/len(df)*100:5.1f}%)")

            # Check for default/fallback categorizations
            default_cat = df.filter(
                (pl.col("topic") == "Medicina Legal") &
                (pl.col("topic_confidence") < 0.5)
            )

            if len(default_cat) > 0:
                print(f"\n      ⚠️  Potential failed categorizations: {len(default_cat)}")
                print(f"         (Medicina Legal with confidence < 0.5)")

        # Compare with expected
        if expected_total > 0:
            print(f"\n   📊 COMPLETENESS CHECK:")
            if output_count == expected_total:
                print(f"      ✅ ALL questions categorized ({output_count}/{expected_total})")
            elif output_count < expected_total:
                missing = expected_total - output_count
                print(f"      ⚠️  INCOMPLETE: {missing} questions missing")
            else:
                print(f"      ⚠️  More questions than expected ({output_count} vs {expected_total})")
    else:
        print(f"   ❌ questions_categorized.json: NOT FOUND")

    print("\n" + "=" * 80)

    # Summary recommendation
    print("\n📋 RECOMMENDATION:")

    if not OUTPUT_FILE.exists():
        print("   ➡️  Run classify.py to start categorization")
    elif CHECKPOINT_FILE.exists():
        print("   ➡️  Categorization incomplete - run classify.py to resume")
    elif OUTPUT_FILE.exists() and expected_total > 0:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            output_data = json.load(f)
        if len(output_data) == expected_total:
            print("   ✅ Categorization complete! Ready for next step.")
        else:
            print("   ⚠️  Output count doesn't match - consider re-running classify.py")
    else:
        print("   ℹ️  Check source files first")

    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
