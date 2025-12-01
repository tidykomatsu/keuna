"""
Migrate question images from Moodle to Supabase Storage.

INCREMENTAL MIGRATION:
- Maintains image_mappings.json: {original_url -> supabase_url}
- Only downloads/uploads images NOT already in mappings
- Never modifies questions_ready.json (import_questions.py handles merging)
- Saves progress after each successful upload (resume-safe)

Usage:
    python migrate_images_to_supabase.py --test       # Test with 5 questions
    python migrate_images_to_supabase.py --full       # Process all pending images
    python migrate_images_to_supabase.py --status     # Show migration status
"""

import json
import logging
import os
import re
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

MOODLE_SESSION_COOKIE = os.getenv("MOODLE_SESSION", "")

PROCESSED_DIR = Path(os.getenv("EUNACOM_PROCESSED_DATA"))
QUESTIONS_FILE = PROCESSED_DIR / "questions_ready.json"
MAPPINGS_FILE = PROCESSED_DIR / "image_mappings.json"


# ============================================================================
# Mappings Management
# ============================================================================

def load_mappings() -> dict[str, str]:
    """Load existing image mappings from file"""
    if not MAPPINGS_FILE.exists():
        return {}

    with open(MAPPINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_mappings(mappings: dict[str, str]):
    """Save mappings to file (atomic write)"""
    temp_file = MAPPINGS_FILE.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(mappings, f, ensure_ascii=False, indent=2)
    temp_file.replace(MAPPINGS_FILE)


def is_already_migrated(url: str, mappings: dict[str, str]) -> bool:
    """Check if URL is already in mappings or is already a Supabase URL"""
    if not url:
        return True
    if "supabase" in url:
        return True
    return url in mappings


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
        client.storage.from_(BUCKET_NAME).upload(
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
# Status Report
# ============================================================================

def show_status():
    """Show migration status without modifying anything"""
    log.info(f"Loading questions from {QUESTIONS_FILE}")

    assert QUESTIONS_FILE.exists(), f"Questions file not found: {QUESTIONS_FILE}"

    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    mappings = load_mappings()

    # Collect all image URLs
    all_urls = []
    for q in questions:
        for url in q.get("images", []):
            if url:
                all_urls.append(url)

    # Categorize
    already_supabase = [u for u in all_urls if "supabase" in u]
    in_mappings = [u for u in all_urls if u in mappings and "supabase" not in u]
    pending = [u for u in all_urls if not is_already_migrated(u, mappings)]

    print(f"\n{'='*60}")
    print("IMAGE MIGRATION STATUS")
    print(f"{'='*60}")
    print(f"Questions file: {QUESTIONS_FILE}")
    print(f"Mappings file:  {MAPPINGS_FILE}")
    print(f"\nTotal images in questions: {len(all_urls)}")
    print(f"  Already Supabase URLs:   {len(already_supabase)}")
    print(f"  In mappings file:        {len(in_mappings)}")
    print(f"  Pending migration:       {len(pending)}")
    print(f"\nMappings file entries:     {len(mappings)}")
    print(f"{'='*60}\n")

    if pending:
        print(f"Sample pending URLs (first 5):")
        for url in pending[:5]:
            print(f"  {url[:80]}...")

    return {"total": len(all_urls), "pending": len(pending), "migrated": len(in_mappings) + len(already_supabase)}


# ============================================================================
# Main Migration
# ============================================================================

def migrate_images(test_mode: bool = False, limit: int = 5):
    """Migrate pending images from Moodle to Supabase (incremental)"""

    assert MOODLE_SESSION_COOKIE, "MOODLE_SESSION cookie not set. Get it from browser DevTools."

    # Load questions (read-only, we never modify this file)
    log.info(f"Loading questions from {QUESTIONS_FILE}")
    assert QUESTIONS_FILE.exists(), f"Questions file not found: {QUESTIONS_FILE}"

    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    # Load existing mappings
    mappings = load_mappings()
    log.info(f"Loaded {len(mappings)} existing image mappings")

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

    # Collect pending images
    pending_images = []
    for q in questions:
        question_id = q["question_id"]
        for idx, image_url in enumerate(q.get("images", []), 1):
            if not is_already_migrated(image_url, mappings):
                pending_images.append({
                    "question_id": question_id,
                    "index": idx,
                    "url": image_url
                })

    log.info(f"Found {len(pending_images)} pending images to migrate")

    if test_mode:
        pending_images = pending_images[:limit]
        log.info(f"TEST MODE: Processing only {limit} images")

    if not pending_images:
        log.info("No pending images to migrate!")
        return stats

    # Process each pending image
    for i, img in enumerate(pending_images, 1):
        stats["total"] += 1
        question_id = img["question_id"]
        idx = img["index"]
        image_url = img["url"]

        log.info(f"[{i}/{len(pending_images)}] {question_id} image {idx}")

        # Download
        image_data = download_image(image_url, session)
        if not image_data:
            stats["failed"] += 1
            continue
        stats["downloaded"] += 1

        # Upload
        storage_path = generate_storage_path(question_id, idx, image_url)
        public_url = upload_to_supabase(supabase, storage_path, image_data)

        if public_url:
            stats["uploaded"] += 1
            # Add to mappings and save immediately (resume-safe)
            mappings[image_url] = public_url
            save_mappings(mappings)
            log.info(f"  -> {public_url}")
        else:
            stats["failed"] += 1

        # Rate limiting
        time.sleep(0.2)

    # Print summary
    log.info("=" * 60)
    log.info("Migration Summary:")
    log.info(f"  Processed:    {stats['total']}")
    log.info(f"  Downloaded:   {stats['downloaded']}")
    log.info(f"  Uploaded:     {stats['uploaded']}")
    log.info(f"  Failed:       {stats['failed']}")
    log.info(f"  Total mapped: {len(mappings)}")
    log.info("=" * 60)

    return stats


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate images to Supabase Storage (incremental)")
    parser.add_argument("--test", action="store_true", help="Test mode: process only 5 images")
    parser.add_argument("--limit", type=int, default=5, help="Number of images to process in test mode")
    parser.add_argument("--full", action="store_true", help="Process all pending images")
    parser.add_argument("--status", action="store_true", help="Show migration status only")

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.full or args.test:
        migrate_images(test_mode=args.test, limit=args.limit)
    else:
        print("Usage:")
        print("  Status:     python migrate_images_to_supabase.py --status")
        print("  Test mode:  python migrate_images_to_supabase.py --test")
        print("  Full run:   python migrate_images_to_supabase.py --full")
