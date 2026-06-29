import os
import json
from datetime import date
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

EVAL_FILE = "eval_log.json"
judge = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.environ.get("GEMINI_API_KEY"), temperature=0.7)

def evaluate_lesson(topic: str, lesson_title: str, teaching: str, question: str) -> dict:
    """Use Gemini to score the quality of the lesson and quiz question. Returns a dictionary with the score and feedback."""

    prompt = f"""You are an expert education evaluator. Score this AI generated lesson strictly and honestly.
             Topic: {topic}, Lesson Title: {lesson_title}, Lesson Content: {teaching}, Quiz Question: {question}.
             Score each dimensionfrom 1 tp 5: - clarity: Is the explanation easy for a beginner to understand?
             - accuracy: Is the content factually correct? - difficulty: Is the quiz question appropriately challenging?(not too easy, not too hard).
             Reply ONLY with valid json, no extra text: {{'clarity':N, 'accuracy':N, 'difficulty':N, 'reason': "one sentence explanation"}}"""
    
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
            log = json.load(f)
            log.append(scores)
        with open(EVAL_FILE, "w") as f:
            json.dump(log, f, indent=2)

def show_eval_summary():
    """Print average scores across all sessions."""
    if not os.path.exists(EVAL_FILE):
        print("No eval data yest.")

        return 
    with open(EVAL_FILE, "r") as f:
        log = json.load(f)

    if not log:
        return 
    clarity = sum(e.get("clarity", 0) for e in log) / len(log)
    accuracy = sum(e.get("accuracy", 0) for e in log) / len(log)
    overall = sum(e.get("overall", 0) for e in log) / len(log)

    print(f"\n===  Eval Summary ({len(log)} lessons gradded) ====")
    print(f"Avg clarity: {clarity: .1f}/5")
    print(f"Avh accuracy: {accuracy: .1f}/5")
    print(f"Avg overall: {overall: .1f}/5")


