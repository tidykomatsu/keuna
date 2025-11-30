"""Extract questions from GUEVARA HTML files - WITH IMAGE SUPPORT"""

from bs4 import BeautifulSoup
from pathlib import Path
import re
from utils import save_questions, print_extraction_summary
from config import get_raw_data_root


# ============================================================================
# Image Extraction
# ============================================================================

def extract_images_from_element(element) -> list[str]:
    """
    Extract all image URLs from an HTML element
    Returns list of image URLs (can be empty)
    """
    if element is None:
        return []
    
    images = []
    for img in element.find_all("img"):
        src = img.get("src", "")
        if src:
            images.append(src)
    
    return images


# ============================================================================
# Question Extraction
# ============================================================================

def extract_question(question_div, source_filename: str) -> dict | None:
    """Extract single question from GUEVARA HTML - WITH IMAGE SUPPORT"""
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
        
        # FIXED: Extract images BEFORE stripping HTML
        images = extract_images_from_element(qtext_div)
        
        # Now extract text
        if qtext_div:
            qtext_copy = qtext_div.__copy__()
            for table in qtext_copy.find_all("table"):
                table.decompose()
            q_text = qtext_copy.get_text(strip=True, separator=" ")
        else:
            q_text = ""

        # Answer options
        answer_divs = question_div.find_all("div", class_=re.compile(r"^r[0-1]$"))

        all_options = []
        correct_answer = None

        for ans_div in answer_divs:
            label = ans_div.find("div", class_="d-flex")
            if label:
                letter_span = label.find("span", class_="answernumber")
                text_div = label.find("div", class_="flex-fill")

                if letter_span and text_div:
                    letter = letter_span.get_text(strip=True)
                    text = text_div.get_text(strip=True)
                    is_correct = "correct" in ans_div.get("class", [])

                    all_options.append({
                        "letter": letter,
                        "text": text,
                        "explanation": "",
                        "is_correct": is_correct,
                    })

                    if is_correct:
                        correct_answer = f"{letter} {text}"

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
            "images": images,  # NEW: List of image URLs
            "source_file": source_filename,
            "source_type": "guevara",
        }

    except Exception as e:
        print(f"    ✗ Error extracting question: {e}")
        return None


def extract_from_file(filepath: Path) -> list[dict]:
    """Extract all questions from one GUEVARA file"""
    print(f"  Processing: {filepath.name}")

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
        for question_div in questions_divs:
            question = extract_question(question_div, filepath.name)
            if question:
                questions.append(question)

        # Count questions with images
        with_images = sum(1 for q in questions if q.get("images"))
        print(f"    ✓ Extracted {len(questions)} questions ({with_images} with images)")
        
        return questions

    except Exception as e:
        print(f"    ✗ Error: {str(e)}")
        return []


def extract_all_guevara() -> list[dict]:
    """Main extraction function"""
    raw_root = get_raw_data_root()
    raw_dir = raw_root / "guevara"

    # Exclude files inside Reconstrucciones folder (handled separately by extract_reconstrucciones.py)
    html_files = sorted([
        f for f in (list(raw_dir.rglob("*.html")) + list(raw_dir.rglob("*.htm")))
        if "Reconstrucciones" not in str(f)
    ])

    print(f"\n{'='*60}")
    print("EXTRACTING: GUEVARA (WITH IMAGES)")
    print(f"{'='*60}")
    print(f"Files found: {len(html_files)}\n")

    all_questions = []

    for html_file in html_files:
        questions = extract_from_file(html_file)
        all_questions.extend(questions)

    # Remove duplicates
    seen_ids = set()
    unique_questions = []
    for q in all_questions:
        qid = q["question_id"]
        if qid not in seen_ids:
            seen_ids.add(qid)
            unique_questions.append(q)

    duplicates = len(all_questions) - len(unique_questions)
    if duplicates > 0:
        print(f"\n⚠️  Removed {duplicates} duplicates")

    # Image summary
    total_with_images = sum(1 for q in unique_questions if q.get("images"))
    print(f"\n📸 Questions with images: {total_with_images}/{len(unique_questions)}")

    print_extraction_summary(unique_questions, "GUEVARA")

    return unique_questions


if __name__ == "__main__":
    questions = extract_all_guevara()
    if questions:
        output_file = save_questions(questions, "guevara")
        print(f"\n💾 Saved: {output_file}")
