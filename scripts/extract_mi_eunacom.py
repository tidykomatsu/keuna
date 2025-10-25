"""Extract questions from MI_EUNACOM HTML files"""
from bs4 import BeautifulSoup
import html as html_module
from pathlib import Path
from shared_utils import save_questions, print_extraction_summary


def extract_from_view_source(filepath: Path) -> str:
    """Extract HTML from view-source saved file"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if "line-content" in content:
        soup = BeautifulSoup(content, "html.parser")
        lines = soup.find_all("td", class_="line-content")
        html_parts = [line.get_text() for line in lines]
        raw_html = "\n".join(html_parts)
        return html_module.unescape(raw_html)

    return content


def parse_answer_options(soup: BeautifulSoup) -> list[dict]:
    """Extract answer options"""
    answers = []
    answer_list = soup.find("ul", class_="global-list")

    if not answer_list:
        return answers

    for li in answer_list.find_all("li", recursive=False):
        is_correct = False
        span = li.find("span", style=True)
        if span and "#CFFCE4" in span.get("style", ""):
            is_correct = True

        label = li.find("span", class_="mdl-radio__label")
        if not label:
            continue

        full_text = label.get_text()
        strong = label.find("strong")

        if strong:
            option_letter = full_text.split(strong.get_text())[0].strip().split("\n")[0].strip()
            explanation_text = strong.get_text(strip=True)
        else:
            option_letter = full_text.strip().split()[0] if full_text.strip() else ""
            explanation_text = full_text.strip()

        answers.append({
            "letter": option_letter,
            "text": explanation_text,
            "is_correct": is_correct
        })

    return answers


def extract_question(item_html: str, source_filename: str) -> dict | None:
    """Extract single question from HTML"""
    soup = BeautifulSoup(item_html, "html.parser")

    # Extract question ID
    import re
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

    # Extract explanation
    explanation = ""
    modal_body = soup.find("div", class_="modal-body")
    if modal_body:
        p_tag = modal_body.find("p")
        if p_tag:
            explanation = p_tag.get_text(strip=True).replace("&quot;", "").strip('"')

    # Extract answer options
    answer_options = parse_answer_options(soup)

    # Find correct answer
    correct_answer = ""
    for opt in answer_options:
        if opt["is_correct"]:
            correct_answer = f"{opt['letter']} {opt['text']}"
            break

    return {
        "question_id": question_id,
        "question_number": question_id,  # Use ID as number
        "topic": "",  # Empty - will be filled by Gemini
        "question_text": question_text,
        "answer_options": answer_options,
        "correct_answer": correct_answer,
        "explanation": explanation,
        "source_file": source_filename,
        "source_type": "mi_eunacom"
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