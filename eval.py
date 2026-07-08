import os
import json
from datetime import date
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()
EVAL_FILE = "eval_log.json"

judge = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    api_key=os.environ.get("OPENAI_API_KEY")
)

def evaluate_lesson(topic: str, lesson_title: str, teaching: str, question: str) -> dict:
    """Use GPT to score the quality of the lesson and quiz question."""

    prompt = f"""You are an expert education evaluator. Score this AI generated lesson strictly and honestly.
             Topic: {topic}, Lesson Title: {lesson_title}, Lesson Content: {teaching}, Quiz Question: {question}.
             Score each dimension from 1 to 5:
             - clarity: Is the explanation easy for a beginner to understand?
             - accuracy: Is the content factually correct?
             - difficulty: Is the quiz question appropriately challenging? (not too easy, not too hard).
             Reply ONLY with valid JSON, no extra text:
             {{"clarity":N, "accuracy":N, "difficulty":N, "reason": "one sentence explanation"}}"""
 
    try:
        response = judge.invoke(prompt).content
        clean = response.strip().replace("```json", "").replace("```", "").strip()
        scores = json.loads(clean)
        scores['topic'] = topic
        scores['lesson_title'] = lesson_title
        scores['overall'] = round((scores['clarity'] + scores['accuracy'] + scores['difficulty']) / 3, 1)
        scores['date'] = str(date.today())
        return scores
    except Exception as e:
        print(f" [eval skipped: {e}]")
        return {}


def save_eval(scores: dict):
    """Save evaluation scores to a JSON file."""
    if not scores:
        return

    
    log = []
    if os.path.exists(EVAL_FILE):
        with open(EVAL_FILE, "r") as f:
            content = f.read().strip()          # read as string first
            log = json.loads(content) if content else []  # only parse if not empty

    log.append(scores)

   
    with open(EVAL_FILE, "w") as f:
        json.dump(log, f, indent=2)


def show_eval_summary():
    """Print average scores across all sessions."""
    if not os.path.exists(EVAL_FILE):
        print("No eval data yet.")
        return

   
    with open(EVAL_FILE, "r") as f:
        content = f.read().strip()
        log = json.loads(content) if content else []

    if not log:
        print("No eval data yet.")
        return

    clarity  = sum(e.get("clarity",  0) for e in log) / len(log)
    accuracy = sum(e.get("accuracy", 0) for e in log) / len(log)
    overall  = sum(e.get("overall",  0) for e in log) / len(log)

    print(f"\n=== Eval Summary ({len(log)} lessons graded) ===")
    print(f"Avg clarity:  {clarity:.1f}/5")
    print(f"Avg accuracy: {accuracy:.1f}/5")
    print(f"Avg overall:  {overall:.1f}/5")

