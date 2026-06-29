import os
import json
from datetime import date

MEMORY_FILE = "progress.json"

def load_progress():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    else:
        return {"completed_topics":[], "scores": {}, "total_sessions": 0}
    
def save_progress(topic, score, total):
    progress = load_progress()
    progress["scores"][topic] = {"score": score, "total": total, "date": str(date.today())}
    if score >= total*0.7:  # Assuming 70% is the passing score
        if topic not in progress["completed_topics"]:
            progress["completed_topics"].append(topic)
    progress["total_sessions"] += 1
    with open(MEMORY_FILE, "w") as f:
        json.dump(progress, f, indent=4)
    return progress

def show_progress():
    progress = load_progress()
    print("\n=== Your Progress ===")
    print(f"Total Study Sessions: {progress['total_sessions']}")
    print(f"Topics mastered: {len(progress['completed_topics'])}")
    if progress["scores"]:
        print("\nScores by Topic:")
        for topic, data in progress["scores"].items():
            pct = int(data['score']/data['total']*100)
            status = "Mastered" if topic in progress["completed_topics"] else "In Progress"
        print(f"{status} - {topic}: {data['score']}/{data['total']} ({pct}%) on {data['date']}")
    else:
        print("no sessions yet")

def alread_mastered(topic):
    progress = load_progress()
    return topic.lower() in [t.lower() for t in progress["completed_topics"]]



