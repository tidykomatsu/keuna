"""
Extract questions from Reconstrucciones folders.
Reuses Guevara and MI_EUNACOM extraction logic.
Adds reconstruction_name and reconstruction_order fields for ordered practice.
"""

from pathlib import Path
import re
from bs4 import BeautifulSoup

from config import get_raw_data_root
from utils import save_questions, print_extraction_summary
from extract_guevara import extract_images_from_element
from extract_mi_eunacom import extract_question as extract_mi_eunacom_question


# ============================================================================
# Reconstruction Extraction - Guevara Format
# ============================================================================

def extract_question_reconstruction(question_div, source_filename: str) -> dict | None:
    """
    Extract single question from Reconstrucción HTML.
    
    KEY DIFFERENCE from regular Guevara:
    - Correct answer is NOT marked in option classes
    - Correct answer is in: <div class="rightanswer">La respuesta correcta es: {text}</div>
    """
    try:
        # Question ID
        question_id = question_div.get("id", "")
        if not question_id:
            return None

        # Question number (remove "Pregunta" prefix)
        qno_span = question_div.find("span", class_="qno")
        q_number = qno_span.get_text(strip=True).replace("Pregunta ", "") if qno_span else ""

        # Question text div
        qtext_div = question_div.find("div", class_="qtext")
        
        # Extract images
        images = extract_images_from_element(qtext_div)
        
        # Extract text
        if qtext_div:
            qtext_copy = qtext_div.__copy__()
            for table in qtext_copy.find_all("table"):
                table.decompose()
            q_text = qtext_copy.get_text(strip=True, separator=" ")
        else:
            q_text = ""

        # Answer options - extract ALL first (none marked correct yet)
        answer_divs = question_div.find_all("div", class_=re.compile(r"^r[0-1]$"))

        all_options = []
        for ans_div in answer_divs:
            label = ans_div.find("div", class_="d-flex")
            if label:
                letter_span = label.find("span", class_="answernumber")
                text_div = label.find("div", class_="flex-fill")

                if letter_span and text_div:
                    letter = letter_span.get_text(strip=True)
                    text = text_div.get_text(strip=True)

                    all_options.append({
                        "letter": letter,
                        "text": text,
                        "explanation": "",
                        "is_correct": False,  # Will be set below
                    })

        # CRITICAL: Find correct answer from rightanswer div
        correct_answer_text = ""
        rightanswer_div = question_div.find("div", class_="rightanswer")
        
        if rightanswer_div:
            rightanswer_full = rightanswer_div.get_text(strip=True)
            # Pattern: "La respuesta correcta es: {answer text}"
            if "La respuesta correcta es:" in rightanswer_full:
                correct_answer_text = rightanswer_full.split("La respuesta correcta es:")[-1].strip()
            elif "respuesta correcta" in rightanswer_full.lower():
                # Fallback: try to extract after any "correcta" mention
                parts = rightanswer_full.lower().split("correcta")
                if len(parts) > 1:
                    correct_answer_text = rightanswer_full[rightanswer_full.lower().rfind("correcta") + len("correcta"):].strip()
                    # Remove leading ":"  or "es:" if present
                    correct_answer_text = re.sub(r"^[:\s]+", "", correct_answer_text).strip()

        # Match correct answer to options
        correct_answer = ""
        if correct_answer_text and all_options:
            # Normalize for comparison
            correct_normalized = correct_answer_text.lower().strip()
            
            for opt in all_options:
                opt_text_normalized = opt["text"].lower().strip()
                
                # Check if option text matches (exact or contained)
                if opt_text_normalized == correct_normalized:
                    opt["is_correct"] = True
                    correct_answer = f"{opt['letter']} {opt['text']}"
                    break
                elif correct_normalized in opt_text_normalized or opt_text_normalized in correct_normalized:
                    opt["is_correct"] = True
                    correct_answer = f"{opt['letter']} {opt['text']}"
                    break
            
            # If no match found, try fuzzy match (first few words)
            if not correct_answer:
                correct_words = correct_normalized.split()[:3]  # First 3 words
                for opt in all_options:
                    opt_words = opt["text"].lower().split()[:3]
                    if correct_words == opt_words:
                        opt["is_correct"] = True
                        correct_answer = f"{opt['letter']} {opt['text']}"
                        break

        # If still no match, log warning
        if not correct_answer and correct_answer_text:
            print(f"      ⚠️ Could not match correct answer: '{correct_answer_text[:50]}...'")

        # General explanation (topic-level)
        feedback_div = question_div.find("div", class_="generalfeedback")
        explanation = feedback_div.get_text(strip=True, separator=" ") if feedback_div else ""

        return {
            "question_id": question_id,
            "question_number": q_number,
            "topic": "",
            "question_text": q_text,
            "answer_options": all_options,
            "correct_answer": correct_answer,
            "explanation": explanation,
            "images": images,
            "source_file": source_filename,
            "source_type": "guevara_reconstruccion",
        }

    except Exception as e:
        print(f"    ✗ Error extracting question: {e}")
        return None


def extract_guevara_reconstruction(filepath: Path, reconstruction_name: str, order_offset: int) -> list[dict]:
    """
    Extract questions from a Guevara-format reconstruction HTML file.
    Returns questions with reconstruction metadata.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Handle view-source format
        soup_viewsource = BeautifulSoup(html_content, "html.parser")
        line_contents = soup_viewsource.find_all("td", class_="line-content")

        if line_contents:
            actual_html_lines = [line_td.get_text() for line_td in line_contents]
            actual_html = "\n".join(actual_html_lines)
            soup = BeautifulSoup(actual_html, "html.parser")
        else:
            soup = soup_viewsource

        # Find questions
        questions_divs = soup.find_all("div", id=re.compile(r"question-\d+-\d+"))
        if not questions_divs:
            questions_divs = soup.find_all("div", class_=re.compile(r"que.*multichoice"))

        questions = []
        for idx, question_div in enumerate(questions_divs):
            # Use reconstruction-specific extractor (handles rightanswer div)
            question = extract_question_reconstruction(question_div, filepath.name)
            
            if question:
                # Generate unique ID for reconstruction
                safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', reconstruction_name.lower())
                original_id = question["question_id"]
                question["question_id"] = f"recon_guevara_{safe_name}_{original_id}"
                
                # Add reconstruction metadata
                question["reconstruction_name"] = reconstruction_name
                question["reconstruction_order"] = order_offset + idx + 1
                
                questions.append(question)

        return questions

    except Exception as e:
        print(f"    ✗ Error extracting {filepath.name}: {e}")
        return []


# ============================================================================
# Reconstruction Extraction - MI_EUNACOM Format
# ============================================================================

def extract_mi_eunacom_reconstruction(filepath: Path, reconstruction_name: str, order_offset: int) -> list[dict]:
    """
    Extract questions from a MI_EUNACOM-format reconstruction HTML file.
    Returns questions with reconstruction metadata.
    """
    from extract_mi_eunacom import extract_from_view_source
    
    try:
        html = extract_from_view_source(filepath)
        soup = BeautifulSoup(html, "html.parser")

        accordion_items = soup.find_all("div", class_="gray-card accordion-item")
        if not accordion_items:
            accordion_items = soup.find_all("div", class_="accordion-item")

        questions = []
        for idx, item in enumerate(accordion_items):
            question = extract_mi_eunacom_question(str(item), filepath.name)
            if question:
                # Generate unique ID for reconstruction
                safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', reconstruction_name.lower())
                original_id = question["question_id"]
                question["question_id"] = f"recon_mieunacom_{safe_name}_{original_id}"
                
                # Add reconstruction metadata
                question["reconstruction_name"] = reconstruction_name
                question["reconstruction_order"] = order_offset + idx + 1
                question["source_type"] = "mi_eunacom_reconstruccion"
                
                questions.append(question)

        return questions

    except Exception as e:
        print(f"    ✗ Error extracting {filepath.name}: {e}")
        return []


# ============================================================================
# Process Single Reconstruction Folder
# ============================================================================

def extract_reconstruction_folder(folder: Path, source_type: str) -> list[dict]:
    """
    Extract all questions from a reconstruction folder (e.g., "Agosto 2021").
    Maintains order across multiple HTML files.
    """
    reconstruction_name = folder.name
    print(f"\n  📁 Reconstruction: {reconstruction_name}")

    # Get HTML files sorted by name (01.html, 02.html, etc.)
    html_files = sorted(
        list(folder.glob("*.html")) + list(folder.glob("*.htm")),
        key=lambda p: p.stem  # Sort by filename without extension
    )

    if not html_files:
        print(f"    ⚠️ No HTML files found")
        return []

    print(f"    Files: {len(html_files)}")

    all_questions = []
    order_offset = 0

    for html_file in html_files:
        print(f"    Processing: {html_file.name}", end=" ")

        if source_type == "guevara":
            questions = extract_guevara_reconstruction(html_file, reconstruction_name, order_offset)
        else:
            questions = extract_mi_eunacom_reconstruction(html_file, reconstruction_name, order_offset)

        print(f"→ {len(questions)} questions")
        
        all_questions.extend(questions)
        order_offset += len(questions)

    # Stats
    with_images = sum(1 for q in all_questions if q.get("images"))
    with_correct = sum(1 for q in all_questions if any(opt.get("is_correct") for opt in q.get("answer_options", [])))
    without_correct = len(all_questions) - with_correct
    
    print(f"    ✓ Total: {len(all_questions)} questions ({with_images} with images)")
    
    if without_correct > 0:
        print(f"    ⚠️ {without_correct} questions without matched correct answer")

    return all_questions


# ============================================================================
# Main Extraction Functions
# ============================================================================

def extract_guevara_reconstrucciones() -> list[dict]:
    """Extract all Guevara-format reconstructions"""
    raw_root = get_raw_data_root()
    recon_dir = raw_root / "guevara" / "Reconstrucciones"

    if not recon_dir.exists():
        print(f"  ℹ️ No Guevara Reconstrucciones folder found at {recon_dir}")
        return []

    # Find reconstruction folders
    recon_folders = sorted([d for d in recon_dir.iterdir() if d.is_dir()])

    if not recon_folders:
        print(f"  ℹ️ No reconstruction folders found in {recon_dir}")
        return []

    print(f"  Found {len(recon_folders)} Guevara reconstructions:")
    for folder in recon_folders:
        print(f"    - {folder.name}")

    all_questions = []
    for folder in recon_folders:
        questions = extract_reconstruction_folder(folder, "guevara")
        all_questions.extend(questions)

    return all_questions


def extract_mi_eunacom_reconstrucciones() -> list[dict]:
    """Extract all MI_EUNACOM-format reconstructions"""
    raw_root = get_raw_data_root()
    recon_dir = raw_root / "mi_eunacom" / "Reconstrucciones"

    if not recon_dir.exists():
        print(f"  ℹ️ No MI_EUNACOM Reconstrucciones folder found at {recon_dir}")
        return []

    # Find reconstruction folders
    recon_folders = sorted([d for d in recon_dir.iterdir() if d.is_dir()])

    if not recon_folders:
        print(f"  ℹ️ No reconstruction folders found in {recon_dir}")
        return []

    print(f"  Found {len(recon_folders)} MI_EUNACOM reconstructions:")
    for folder in recon_folders:
        print(f"    - {folder.name}")

    all_questions = []
    for folder in recon_folders:
        questions = extract_reconstruction_folder(folder, "mi_eunacom")
        all_questions.extend(questions)

    return all_questions


def extract_all_reconstrucciones() -> list[dict]:
    """Main extraction function - extracts from both source types"""
    print(f"\n{'='*60}")
    print("EXTRACTING: RECONSTRUCCIONES")
    print(f"{'='*60}")

    # Extract from both sources
    print("\n📚 Guevara Reconstrucciones:")
    guevara_questions = extract_guevara_reconstrucciones()

    print("\n📚 MI_EUNACOM Reconstrucciones:")
    mi_eunacom_questions = extract_mi_eunacom_reconstrucciones()

    # Merge
    all_questions = guevara_questions + mi_eunacom_questions

    if not all_questions:
        print("\n⚠️ No reconstruction questions found")
        return []

    # Remove duplicates (shouldn't happen but safety check)
    seen_ids = set()
    unique_questions = []
    for q in all_questions:
        qid = q["question_id"]
        if qid not in seen_ids:
            seen_ids.add(qid)
            unique_questions.append(q)

    duplicates = len(all_questions) - len(unique_questions)
    if duplicates > 0:
        print(f"\n⚠️ Removed {duplicates} duplicates")

    # Summary by reconstruction
    print(f"\n{'='*60}")
    print("📊 RECONSTRUCTION SUMMARY")
    print(f"{'='*60}")

    recon_counts = {}
    for q in unique_questions:
        name = q.get("reconstruction_name", "Unknown")
        recon_counts[name] = recon_counts.get(name, 0) + 1

    for name, count in sorted(recon_counts.items()):
        print(f"  {name}: {count} questions")

    print(f"\n  Total: {len(unique_questions)} questions")

    # Image summary
    total_with_images = sum(1 for q in unique_questions if q.get("images"))
    print(f"  📸 With images: {total_with_images}")

    return unique_questions


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    questions = extract_all_reconstrucciones()
    if questions:
        output_file = save_questions(questions, "reconstrucciones")
        print(f"\n💾 Saved: {output_file}")
    else:
        print("\n❌ No questions extracted")
