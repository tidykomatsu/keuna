"""Extract questions from MI_EUNACOM HTML files"""

from bs4 import BeautifulSoup
import html as html_module
from pathlib import Path
import re
from shared_utils import save_questions, print_extraction_summary


def extract_from_view_source(filepath: Path) -> str:
    """Extract HTML from view-source saved file"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if "line-content" in content:
        soup = BeautifulSoup(content, "html.parser")
        lines = soup.find_all("td", class_="line-content")
        html_parts = [line.get_text() for line in lines]
        actual_html = "\n".join(html_parts)
        return html_module.unescape(actual_html)

    return content


def parse_answer_options(soup: BeautifulSoup) -> list[dict]:
    """
    Extract answer options - FIXED VERSION
    Handles the broken HTML structure properly
    """
    answers = []
    answer_list = soup.find("ul", class_="global-list")

    if not answer_list:
        return answers

    for li in answer_list.find_all("li", recursive=False):
        # Check if correct (green background)
        is_correct = False
        span = li.find("span", style=True)
        if span and "#CFFCE4" in span.get("style", ""):
            is_correct = True

        # Get the label containing all text
        label = li.find("span", class_="mdl-radio__label")
        if not label:
            continue

        full_text = label.get_text(strip=True)

        # Parse structure: "a) Short answer text (correcta/incorrecta): Detailed explanation"
        # OR sometimes: "Short text (correcta): Explanation"

        # Try to extract letter (a), b), c), etc.)
        letter_match = re.match(r"^([a-e])\)\s*", full_text)
        if letter_match:
            option_letter = letter_match.group(1) + "."
            text_after_letter = full_text[len(letter_match.group(0)) :].strip()
        else:
            # No letter found, use default
            option_letter = f"{chr(97 + len(answers))}."  # a., b., c., etc.
            text_after_letter = full_text

        # Split on (correcta)/(incorrecta) marker followed by ":"
        # This separates short answer from detailed explanation
        pattern = r"^(.*?)\s*\((correcta|incorrecta)\):\s*(.*)$"
        match = re.match(pattern, text_after_letter, re.DOTALL | re.IGNORECASE)

        if match:
            short_text = match.group(1).strip()
            detailed_explanation = match.group(3).strip()
        else:
            # Fallback: try splitting on first ":"
            if ":" in text_after_letter:
                parts = text_after_letter.split(":", 1)
                short_text = re.sub(r"\s*\((correcta|incorrecta)\)", "", parts[0], flags=re.IGNORECASE).strip()
                detailed_explanation = parts[1].strip()
            else:
                # No explanation found
                short_text = re.sub(r"\s*\((correcta|incorrecta)\)", "", text_after_letter, flags=re.IGNORECASE).strip()
                detailed_explanation = ""

        # Remove any remaining (correcta)/(incorrecta) markers
        short_text = re.sub(r"\s*\((correcta|incorrecta)\)", "", short_text, flags=re.IGNORECASE).strip()

        # Remove duplicate text patterns like "Disenteríad) Disentería"
        # This happens when text is duplicated with different separators
        duplicate_pattern = r"^(.+?)([a-e]\)|\s+)\s*\1$"
        duplicate_match = re.match(duplicate_pattern, short_text, re.IGNORECASE)
        if duplicate_match:
            short_text = duplicate_match.group(1).strip()

        # FIXED: Also handle direct duplicates like "TextoTexto" (no separator)
        # Check if text is exactly duplicated (first half == second half)
        if len(short_text) % 2 == 0:
            midpoint = len(short_text) // 2
            first_half = short_text[:midpoint]
            second_half = short_text[midpoint:]
            if first_half == second_half and len(first_half) > 0:
                short_text = first_half

        answers.append(
            {
                "letter": option_letter,
                "text": short_text,
                "explanation": detailed_explanation,
                "is_correct": is_correct,
            }
        )

    return answers


def extract_question(item_html: str, source_filename: str) -> dict | None:
    """Extract single question from HTML"""
    soup = BeautifulSoup(item_html, "html.parser")

    # Extract question ID
    question_id = None
    button = soup.find("button", {"data-bs-target": re.compile("question_")})
    if button:
        target = button.get("data-bs-target", "")
        match = re.search(r"question_(\d+)", target)
        if match:
            question_id = match.group(1)

    if not question_id:
        return None

    # Extract question text
    question_text = ""
    if button:
        bold = button.find("b")
        if bold:
            question_text = bold.get_text(strip=True)

    # Extract general explanation (topic-level, not option-level)
    explanation = ""
    modal_body = soup.find("div", class_="modal-body")
    if modal_body:
        p_tag = modal_body.find("p")
        if p_tag:
            explanation = p_tag.get_text(strip=True).replace("&quot;", "").strip('"')

    # Extract answer options
    answer_options = parse_answer_options(soup)

    if not answer_options:
        return None

    # Find correct answer
    correct_answer = ""
    for opt in answer_options:
        if opt["is_correct"]:
            correct_answer = f"{opt['letter']} {opt['text']}"
            break

    return {
        "question_id": question_id,
        "question_number": question_id,
        "topic": "",
        "question_text": question_text,
        "answer_options": answer_options,
        "correct_answer": correct_answer,
        "explanation": explanation,
        "source_file": source_filename,
        "source_type": "mi_eunacom",
    }


def extract_from_file(filepath: Path) -> list[dict]:
    """Extract all questions from one file"""
    print(f"  Processing: {filepath.name}")

    try:
        html = extract_from_view_source(filepath)
        soup = BeautifulSoup(html, "html.parser")

        accordion_items = soup.find_all("div", class_="gray-card accordion-item")
        if not accordion_items:
            accordion_items = soup.find_all("div", class_="accordion-item")

        questions = []
        for item in accordion_items:
            question = extract_question(str(item), filepath.name)
            if question:
                questions.append(question)

        print(f"    ✓ Extracted {len(questions)} questions")
        return questions

    except Exception as e:
        print(f"    ✗ Error: {str(e)}")
        return []


def extract_all_mi_eunacom() -> list[dict]:
    """Main extraction function"""
    project_root = Path(__file__).parent.parent
    raw_dir = project_root / "data" / "raw" / "mi_eunacom"

    html_files = sorted(list(raw_dir.glob("*.html")) + list(raw_dir.glob("*.htm")))

    print(f"\n{'='*60}")
    print("EXTRACTING: MI_EUNACOM")
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

    print_extraction_summary(unique_questions, "MI_EUNACOM")

    return unique_questions


if __name__ == "__main__":
    questions = extract_all_mi_eunacom()
    if questions:
        output_file = save_questions(questions, "mi_eunacom")
        print(f"\n💾 Saved: {output_file}")
