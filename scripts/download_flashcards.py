"""
Download flashcards from MiEunacom.cl via API

USAGE:
1. Get authentication data from browser (see instructions below)
2. Paste COOKIE and CSRF_TOKEN values in the configuration section
3. Set SUBAREA_ID and TOTAL_CARDS for the deck you want to download
4. Run: python scripts/download_flashcards.py
"""

import requests
import pandas as pd
import time
import json
from pathlib import Path

# ============================================================================
# CONFIGURATION - PASTE YOUR VALUES HERE
# ============================================================================

# Paste the full Cookie string from browser developer tools
COOKIE = "_ga=GA1.1.1573942331.1760660968; _fbp=fb.1.1760660968141.795941199217905393; _tt_enable_cookie=1; _ttp=01K7QS4MTAQDNBVXAEZZCC5SBA_.tt.1; _gcl_gs=2.1.k1$i1761354792$u178579640; _gcl_aw=GCL.1761354795.CjwKCAjwx-zHBhBhEiwA7Kjq60mEmlPOy9kfq9vtDk8PI9i9EFaL70TGeEJLyJ5w1omwhkpZ_jhs0hoCgxYQAvD_BwE; _gcl_au=1.1.426781313.1760660968.613846838.1762648542.1762648542; ttcsid=1762648537753::yjiYJ0bjS8kPwu_boegC.10.1762649581676.0; ttcsid_CTEP2LRC77U2EHKCBR90=1762648537753::wttcNEcbp6eSgpU2Y7sP.10.1762649581676.0; XSRF-TOKEN=eyJpdiI6Ijd0eXpSZFlHRG4yWEhOQU9yR0pyM1E9PSIsInZhbHVlIjoiR01xcWNJeVQ0elE5YXFTMHVlRm1Zc2xpUHNrRHRSU0ZwSzNZSlBxMW5vb0M5d1V3WVpiMThzRlI2TDRVeG5qWHNZaHFxQjRGamwvWlhMT3psbGF6bi9TNTlhb2svdTVnNmY0ZUJldkNqY0t4d1hRK051ZW9rZlJRdG1hdVY0ZW8iLCJtYWMiOiI3NDdjY2I3MTQ1MmQwNjQ5OWI3YzI2NmY1NmUwM2QzZmY3ZjlkNDA0Y2I5MDcxMTc0NDQ0NjlhZWViZTE0YTFhIiwidGFnIjoiIn0%3D; mi_eunacom_session=eyJpdiI6ImE0YmpKeThxbjczcVZLZ0RZaXUwTFE9PSIsInZhbHVlIjoiOGVYMWFtdk1SV2tFMUNrWmpKa0hPQTV6TzZyVkR1MjhnVnAxSldNMGVPaytoeHBDSS80M3Z6Zm14enN2RjNOcVp5SGxOOWJDTEduUC9YcEU5ZXUwWDN4ai9iYWE3NjBqYXNUbXJLV3B4My9EaWxKdWo1N1h3L0pDZ0tGeGF6U3ciLCJtYWMiOiI0Mzc1MTdmMDgzMjFlZmI1NDk2MWJlYWZmZTdhNWM2NTQ5MzkyM2ZmMTUxOTY5N2I5MzExMDJlYjk2MTJjMDNhIiwidGFnIjoiIn0%3D; _ga_3V96H0042L=GS2.1.s1762648536$o13$g1$t1762649582$j56$l0$h748116182"

# Paste the X-CSRF-TOKEN value from browser developer tools
CSRF_TOKEN = "bJ0oLo85WYeh9vN7p4WCtZ2iqpQMsEnF5YaC1Oj3"

# The sub-area ID for the deck you want to download
# Example: "1" for "CÓDIGO IAM..."
SUBAREA_ID = "1"

# Total number of cards in the deck (check the website to see the count)
# UPDATE THIS: Look at the flashcards page to see how many cards are in the deck
TOTAL_CARDS = 63  # <-- CHANGE THIS to match the actual number of cards

# Output filename (will be saved in data/processed/)
OUTPUT_FILENAME = "eunacom_flashcards.csv"

# ============================================================================
# SCRIPT LOGIC
# ============================================================================

def validate_config():
    """Validate configuration before starting"""
    if not COOKIE or not CSRF_TOKEN:
        print("\n❌ ERROR: Missing authentication data!")
        print("\nPlease follow these steps to get Cookie and CSRF-TOKEN:\n")
        print("1. Open https://mieunacom.cl in your browser")
        print("2. Log in to your account")
        print("3. Navigate to the flashcards page you want to download")
        print("4. Open Developer Tools (F12 or Right-click > Inspect)")
        print("5. Go to the 'Network' tab")
        print("6. Click on a flashcard to flip it (this triggers a network request)")
        print("7. Look for a request to 'get-flip-questions' in the Network tab")
        print("8. Click on it and go to the 'Headers' section")
        print("9. Scroll down to 'Request Headers':")
        print("   - Copy the entire 'Cookie:' value")
        print("   - Copy the 'X-CSRF-TOKEN:' value")
        print("10. Paste these values in the CONFIGURATION section of this script\n")
        return False
    return True


def download_flashcards():
    """Download all flashcards from the specified deck"""

    if not validate_config():
        return

    # Set UTF-8 encoding for Windows console
    import sys
    if sys.platform == "win32":
        import codecs
        sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

    # API endpoint
    url = "https://mieunacom.cl/get-flip-questions"

    # Request headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRF-TOKEN": CSRF_TOKEN,
        "Cookie": COOKIE,
        "Origin": "https://mieunacom.cl",
        "Referer": f"https://mieunacom.cl/study-flash-cards/{SUBAREA_ID}",
    }

    not_included_ids = []
    flashcards_data = []

    print(f"\n{'='*60}")
    print(f"Downloading {TOTAL_CARDS} flashcards from deck {SUBAREA_ID}")
    print(f"{'='*60}\n")

    for i in range(TOTAL_CARDS):
        payload = {
            "currentSubAreaID": SUBAREA_ID,
            "notIncludedQuestionsIDS": not_included_ids
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()

            data = response.json()

            # Extract question and answer
            question_text = data["question"]["question"]
            answer_text = data["validoptions"]

            flashcards_data.append({
                "Front": question_text,
                "Back": answer_text
            })

            # Add to exclusion list
            current_question_id = data["question"]["id"]
            not_included_ids.append(current_question_id)

            print(f"  [{i + 1}/{TOTAL_CARDS}] Fetched card ID: {current_question_id}")

            # Rate limiting
            time.sleep(0.5)

        except requests.exceptions.RequestException as e:
            print(f"\n❌ Network error: {e}")
            print("\nPossible causes:")
            print("  - Cookie/CSRF token expired (repeat authentication steps)")
            print("  - Network connection issue")
            print("  - Website is down or blocking requests")
            break

        except KeyError as e:
            print(f"\n❌ Unexpected API response: {e}")
            print("The website's API structure may have changed.")
            print(f"Response: {response.text[:200]}...")
            break

    if not flashcards_data:
        print("\n❌ No flashcards downloaded!")
        return

    # Save to CSV
    df = pd.DataFrame(flashcards_data)

    # Create output directory if needed
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / OUTPUT_FILENAME
    df.to_csv(output_path, index=False, sep="\t", encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"✅ Success! Downloaded {len(flashcards_data)} flashcards")
    print(f"💾 Saved to: {output_path}")
    print(f"{'='*60}\n")
    print("You can now import this file into Anki:")
    print("  1. Open Anki")
    print("  2. File > Import")
    print("  3. Select the CSV file")
    print("  4. Make sure 'Fields separated by: Tab' is selected")
    print("  5. Map Front -> Front and Back -> Back")
    print("  6. Import!\n")


if __name__ == "__main__":
    download_flashcards()
