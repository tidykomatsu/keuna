"""
Migrate question images from Moodle to Supabase Storage.
Downloads images using authenticated session and uploads to Supabase.

This script reads questions_ready.json, migrates images, and overwrites
the same file (after creating a backup at questions_ready_pre_migration.json).
"""

import json
import logging
import os
import re
import shutil
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# ============================================================================
# Configuration
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
BUCKET_NAME = "question-images"

# Moodle session cookie - SET THIS BEFORE RUNNING
MOODLE_SESSION_COOKIE = os.getenv("MOODLE_SESSION", "")

PROCESSED_DIR = Path(os.getenv("EUNACOM_PROCESSED_DATA"))
QUESTIONS_FILE = PROCESSED_DIR / "questions_ready.json"
BACKUP_FILE = PROCESSED_DIR / "questions_ready_pre_migration.json"
OUTPUT_FILE = QUESTIONS_FILE  # Overwrite input after backup


# ============================================================================
# Supabase Client
# ============================================================================

def get_supabase_client():
    """Initialize Supabase client"""
    assert SUPABASE_URL, "SUPABASE_URL not set"
    assert SUPABASE_KEY, "SUPABASE_SERVICE_ROLE_KEY not set"
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ============================================================================
# Image Download
# ============================================================================

def download_image(url: str, session: requests.Session) -> bytes | None:
    """Download image from Moodle URL"""
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "image" not in content_type and "octet-stream" not in content_type:
            log.warning(f"Not an image response for {url}: {content_type}")
            return None

        return response.content
    except requests.RequestException as e:
        log.error(f"Failed to download {url}: {e}")
        return None


def extract_filename_from_url(url: str) -> str:
    """Extract clean filename from Moodle URL"""
    parsed = urlparse(url)
    path = parsed.path
    filename = path.split("/")[-1]
    return filename


def generate_storage_path(question_id: str, image_index: int, original_url: str) -> str:
    """Generate storage path for image"""
    ext = Path(extract_filename_from_url(original_url)).suffix or ".jpg"
    safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', question_id)
    return f"{safe_id}_{image_index}{ext}"


# ============================================================================
# Supabase Upload
# ============================================================================

def upload_to_supabase(client, file_path: str, image_data: bytes, content_type: str = "image/jpeg") -> str | None:
    """Upload image to Supabase Storage and return public URL"""
    try:
        result = client.storage.from_(BUCKET_NAME).upload(
            file_path,
            image_data,
            {"content-type": content_type, "upsert": "true"}
        )

        public_url = client.storage.from_(BUCKET_NAME).get_public_url(file_path)
        return public_url

    except Exception as e:
        log.error(f"Failed to upload {file_path}: {e}")
        return None


# ============================================================================
# Main Migration
# ============================================================================

def migrate_images(test_mode: bool = False, limit: int = 5):
    """Migrate all images from Moodle to Supabase"""

    assert MOODLE_SESSION_COOKIE, "MOODLE_SESSION cookie not set. Get it from browser DevTools."

    # Create backup before modifying
    if QUESTIONS_FILE.exists():
        shutil.copy(QUESTIONS_FILE, BACKUP_FILE)
        log.info(f"Backup created: {BACKUP_FILE}")

    # Load questions
    log.info(f"Loading questions from {QUESTIONS_FILE}")
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    # Setup HTTP session with Moodle cookies
    session = requests.Session()
    session.cookies.set("MoodleSession", MOODLE_SESSION_COOKIE, domain="cursosonline.doctorguevara.cl")
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })

    # Setup Supabase client
    supabase = get_supabase_client()

    # Track statistics
    stats = {"total": 0, "downloaded": 0, "uploaded": 0, "failed": 0, "skipped": 0}

    # Filter questions with images
    questions_with_images = [q for q in questions if q.get("images")]
    log.info(f"Found {len(questions_with_images)} questions with images")

    if test_mode:
        questions_with_images = questions_with_images[:limit]
        log.info(f"TEST MODE: Processing only {limit} questions")

    # Process each question
    for question in questions_with_images:
        question_id = question["question_id"]
        new_images = []

        for idx, image_url in enumerate(question.get("images", []), 1):
            stats["total"] += 1

            if not image_url or "supabase" in image_url:
                # Already migrated or empty
                new_images.append(image_url)
                stats["skipped"] += 1
                continue

            log.info(f"Processing {question_id} image {idx}: {image_url}")

            # Download
            image_data = download_image(image_url, session)
            if not image_data:
                stats["failed"] += 1
                new_images.append(image_url)  # Keep original on failure
                continue
            stats["downloaded"] += 1

            # Upload
            storage_path = generate_storage_path(question_id, idx, image_url)
            public_url = upload_to_supabase(supabase, storage_path, image_data)

            if public_url:
                stats["uploaded"] += 1
                new_images.append(public_url)
                log.info(f"  -> Uploaded to {public_url}")
            else:
                stats["failed"] += 1
                new_images.append(image_url)  # Keep original on failure

            # Rate limiting
            time.sleep(0.2)

        question["images"] = new_images

    # Save updated questions
    log.info(f"Saving migrated questions to {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    # Print summary
    log.info("=" * 60)
    log.info("Migration Summary:")
    log.info(f"  Total images: {stats['total']}")
    log.info(f"  Downloaded:   {stats['downloaded']}")
    log.info(f"  Uploaded:     {stats['uploaded']}")
    log.info(f"  Skipped:      {stats['skipped']}")
    log.info(f"  Failed:       {stats['failed']}")
    log.info("=" * 60)

    return stats


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate images to Supabase Storage")
    parser.add_argument("--test", action="store_true", help="Test mode: process only 5 images")
    parser.add_argument("--limit", type=int, default=5, help="Number of questions to process in test mode")
    parser.add_argument("--full", action="store_true", help="Process all images (production run)")

    args = parser.parse_args()

    if not args.full and not args.test:
        print("Usage:")
        print("  Test mode:  python migrate_images_to_supabase.py --test")
        print("  Full run:   python migrate_images_to_supabase.py --full")
        exit(1)

    migrate_images(test_mode=args.test, limit=args.limit)
