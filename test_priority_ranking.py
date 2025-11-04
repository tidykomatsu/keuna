"""
Standalone Priority Ranking Test Script
Tests the categorization logic without requiring dagster, streamlit, or database
"""

import random
from typing import Dict, List


# ============================================================================
# MOCK DATA - Simulating Database Results
# ============================================================================

def get_mock_questions():
    """Mock questions data"""
    return [
        {
            "question_id": "Q001",
            "question_number": 1,
            "topic": "Cardiología",
            "question_text": "¿Cuál es el tratamiento de primera línea para la hipertensión?",
            "correct_answer": "A",
        },
        {
            "question_id": "Q002",
            "question_number": 2,
            "topic": "Cardiología",
            "question_text": "¿Qué arritmia es más común en el infarto agudo?",
            "correct_answer": "B",
        },
        {
            "question_id": "Q003",
            "question_number": 3,
            "topic": "Neurología",
            "question_text": "¿Cuál es el signo más específico de meningitis?",
            "correct_answer": "C",
        },
        {
            "question_id": "Q004",
            "question_number": 4,
            "topic": "Neurología",
            "question_text": "¿Qué tipo de ACV es más frecuente?",
            "correct_answer": "A",
        },
        {
            "question_id": "Q005",
            "question_number": 5,
            "topic": "Pediatría",
            "question_text": "¿A qué edad se espera que un niño camine solo?",
            "correct_answer": "B",
        },
    ]


def get_mock_performance():
    """
    Mock user performance data

    Key fields:
    - priority_score: Higher = needs more practice (wrong answers)
                     Lower/Negative = mastered (correct streak)
    - streak: Consecutive correct answers
    - correct_attempts: Total correct
    - incorrect_attempts: Total incorrect
    """
    return {
        "Q001": {
            "question_id": "Q001",
            "priority_score": 15.0,  # HIGH PRIORITY - many wrong answers
            "streak": 0,
            "correct_attempts": 1,
            "incorrect_attempts": 4,
        },
        "Q002": {
            "question_id": "Q002",
            "priority_score": 3.0,  # MEDIUM PRIORITY - some struggles
            "streak": 1,
            "correct_attempts": 2,
            "incorrect_attempts": 1,
        },
        "Q003": {
            "question_id": "Q003",
            "priority_score": -8.0,  # LOW PRIORITY - mastered
            "streak": 3,
            "correct_attempts": 4,
            "incorrect_attempts": 0,
        },
        # Q004 and Q005 have no performance data (never answered)
    }


def get_mock_topic_mastery():
    """
    Mock topic mastery levels

    Returns topics sorted by weakness (lowest mastery first)
    """
    return [
        {
            "topic": "Pediatría",
            "level": 0,  # WEAKEST - not started
            "accuracy": 0.0,
            "questions_answered": 0,
            "status": "Sin iniciar",
        },
        {
            "topic": "Cardiología",
            "level": 1,  # WEAK - started but struggling
            "accuracy": 40.0,
            "questions_answered": 5,
            "status": "Principiante",
        },
        {
            "topic": "Neurología",
            "level": 3,  # STRONG - doing well
            "accuracy": 75.0,
            "questions_answered": 12,
            "status": "Avanzado",
        },
    ]


# ============================================================================
# PRIORITY RANKING LOGIC (Extracted from question_selector.py)
# ============================================================================

def calculate_selection_weight(performance: Dict = None) -> float:
    """
    Calculate selection weight for a question

    Weight determines probability of being selected:
    - Higher weight = more likely to be selected
    - Based on priority_score from performance data

    Returns:
        float: Selection weight (0.5 to 15+)
    """
    if performance is None:
        # Never answered: HIGH PRIORITY
        return 5.0

    priority = performance["priority_score"]

    if priority > 0:
        # Positive priority = wrong answers = HIGH WEIGHT
        return priority
    else:
        # Negative priority = correct streak = LOW WEIGHT (but never zero)
        return max(abs(priority) * 0.1, 0.5) + 0.5


def is_question_mastered(performance: Dict = None) -> bool:
    """
    Check if a question is considered mastered

    Mastered = streak >= 2 AND priority_score < -5
    """
    if performance is None:
        return False

    return performance["streak"] >= 2 and performance["priority_score"] < -5


def categorize_questions(questions: List[Dict], performance: Dict[str, Dict]) -> Dict:
    """
    Categorize questions by priority for selection

    Returns:
        {
            'high_priority': [(question, weight), ...],
            'medium_priority': [...],
            'low_priority': [...],
            'mastered': [...],
            'never_answered': [...]
        }
    """
    categorized = {
        "high_priority": [],      # priority_score > 5
        "medium_priority": [],    # priority_score 0-5
        "low_priority": [],       # priority_score < 0 (but not mastered)
        "mastered": [],           # streak >= 2 and priority < -5
        "never_answered": [],     # no performance data
    }

    for q in questions:
        q_id = q["question_id"]
        perf = performance.get(q_id)
        weight = calculate_selection_weight(perf)

        if perf is None:
            categorized["never_answered"].append((q, weight))
        elif is_question_mastered(perf):
            categorized["mastered"].append((q, weight))
        elif perf["priority_score"] > 5:
            categorized["high_priority"].append((q, weight))
        elif perf["priority_score"] > 0:
            categorized["medium_priority"].append((q, weight))
        else:
            categorized["low_priority"].append((q, weight))

    return categorized


def select_by_topic_first(questions: List[Dict], performance: Dict[str, Dict], topic_mastery: List[Dict]) -> Dict:
    """
    TOPIC-FIRST ALGORITHM: Select from weakest topic

    Steps:
    1. Iterate topics from weakest to strongest
    2. Find non-mastered questions in that topic
    3. Use weighted selection

    Returns:
        Selected question
    """
    for topic_data in topic_mastery:
        topic = topic_data["topic"]
        mastery_level = topic_data["level"]

        # Skip topics at max mastery
        if mastery_level >= 5:
            continue

        # Filter questions for this topic
        topic_questions = [q for q in questions if q["topic"] == topic]

        if not topic_questions:
            continue

        # Find non-mastered questions
        available = []
        for q in topic_questions:
            perf = performance.get(q["question_id"])
            if not is_question_mastered(perf):
                available.append(q)

        # If we found available questions, select from this topic
        if available:
            # Calculate weights for weighted random selection
            weights = [calculate_selection_weight(performance.get(q["question_id"])) for q in available]
            selected = random.choices(available, weights=weights, k=1)[0]

            return {
                "selected_question": selected,
                "selected_from_topic": topic,
                "topic_mastery_level": mastery_level,
                "available_in_topic": len(available),
            }

    # All topics mastered - fallback to random
    return {
        "selected_question": random.choice(questions),
        "selected_from_topic": "random_fallback",
        "topic_mastery_level": 5,
        "available_in_topic": len(questions),
    }


# ============================================================================
# TEST EXECUTION
# ============================================================================

def run_test():
    """Run the priority ranking test"""

    print("=" * 80)
    print("PRIORITY RANKING TEST - CATEGORIZATION ANALYSIS")
    print("=" * 80)
    print()

    # Get mock data
    questions = get_mock_questions()
    performance = get_mock_performance()
    topic_mastery = get_mock_topic_mastery()

    # ========================================================================
    # TEST 1: Categorize all questions
    # ========================================================================
    print("TEST 1: QUESTION CATEGORIZATION")
    print("-" * 80)
    print()

    categorized = categorize_questions(questions, performance)

    for category, items in categorized.items():
        print(f"\n📊 {category.upper().replace('_', ' ')}: ({len(items)} questions)")
        print("-" * 40)

        if items:
            for q, weight in items:
                perf = performance.get(q["question_id"])

                print(f"  • {q['question_id']} [{q['topic']}]")
                print(f"    Weight: {weight:.2f}")

                if perf:
                    print(f"    Priority Score: {perf['priority_score']:.1f}")
                    print(f"    Streak: {perf['streak']}")
                    print(f"    Correct: {perf['correct_attempts']} | Incorrect: {perf['incorrect_attempts']}")
                else:
                    print(f"    Status: Never answered")
                print()

    # ========================================================================
    # TEST 2: Topic mastery ranking
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 2: TOPIC MASTERY RANKING (Weakest to Strongest)")
    print("-" * 80)
    print()

    for i, topic_data in enumerate(topic_mastery, 1):
        stars = "⭐" * topic_data["level"] + "☆" * (5 - topic_data["level"])
        print(f"{i}. {topic_data['topic']}")
        print(f"   Level: {topic_data['level']} {stars}")
        print(f"   Accuracy: {topic_data['accuracy']:.1f}%")
        print(f"   Questions Answered: {topic_data['questions_answered']}")
        print(f"   Status: {topic_data['status']}")
        print()

    # ========================================================================
    # TEST 3: Simulate topic-first selection (10 iterations)
    # ========================================================================
    print("=" * 80)
    print("TEST 3: TOPIC-FIRST SELECTION SIMULATION (10 iterations)")
    print("-" * 80)
    print()
    print("Algorithm: Select from weakest topic first, then weighted within topic")
    print()

    topic_counts = {}
    question_counts = {}

    for i in range(10):
        result = select_by_topic_first(questions, performance, topic_mastery)

        selected = result["selected_question"]
        topic = result["selected_from_topic"]

        # Count selections
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        q_id = selected["question_id"]
        question_counts[q_id] = question_counts.get(q_id, 0) + 1

        print(f"Iteration {i+1}:")
        print(f"  Selected: {selected['question_id']} from {topic}")
        print(f"  Topic Mastery: Level {result['topic_mastery_level']}")
        print(f"  Available in topic: {result['available_in_topic']}")

        perf = performance.get(selected["question_id"])
        if perf:
            weight = calculate_selection_weight(perf)
            print(f"  Weight: {weight:.2f} (Priority: {perf['priority_score']:.1f})")
        else:
            print(f"  Weight: 5.00 (Never answered)")
        print()

    # ========================================================================
    # TEST 4: Selection statistics
    # ========================================================================
    print("=" * 80)
    print("TEST 4: SELECTION STATISTICS")
    print("-" * 80)
    print()

    print("📈 Topic Selection Distribution:")
    print("-" * 40)
    for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
        pct = (count / 10) * 100
        bar = "█" * int(pct / 5)
        print(f"  {topic:20s}: {count:2d}/10 ({pct:5.1f}%) {bar}")
    print()

    print("📈 Question Selection Distribution:")
    print("-" * 40)
    for q_id, count in sorted(question_counts.items(), key=lambda x: -x[1]):
        perf = performance.get(q_id)
        weight = calculate_selection_weight(perf)
        pct = (count / 10) * 100
        bar = "█" * int(pct / 5)

        q = next(q for q in questions if q["question_id"] == q_id)
        print(f"  {q_id} [{q['topic']:15s}]")
        print(f"    Selected: {count:2d}/10 ({pct:5.1f}%) {bar}")
        print(f"    Weight: {weight:.2f}")
        print()

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("=" * 80)
    print("SUMMARY & INSIGHTS")
    print("-" * 80)
    print()

    weakest_topic = topic_mastery[0]["topic"]
    most_selected_topic = max(topic_counts.items(), key=lambda x: x[1])[0]

    print(f"✅ Weakest Topic: {weakest_topic} (Level {topic_mastery[0]['level']})")
    print(f"✅ Most Selected Topic: {most_selected_topic} ({topic_counts[most_selected_topic]}/10 selections)")
    print()

    if weakest_topic == most_selected_topic:
        print("✅ SUCCESS: Algorithm correctly prioritizes weakest topic!")
    else:
        print("⚠️  NOTE: Algorithm may have selected from other topics")
        print(f"   This can happen if weakest topic has no available questions")
    print()

    print("Priority Categorization Working:")
    print(f"  • High Priority: {len(categorized['high_priority'])} questions")
    print(f"  • Medium Priority: {len(categorized['medium_priority'])} questions")
    print(f"  • Low Priority: {len(categorized['low_priority'])} questions")
    print(f"  • Mastered: {len(categorized['mastered'])} questions")
    print(f"  • Never Answered: {len(categorized['never_answered'])} questions")
    print()

    print("=" * 80)


if __name__ == "__main__":
    run_test()
