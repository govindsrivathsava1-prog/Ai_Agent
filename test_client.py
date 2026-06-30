import requests

BASE = "http://localhost:8000"

topic = input("What do you want to study? ")
resp = requests.post(f"{BASE}/start", json={"topic": topic})
data = resp.json()

thread_id = data["thread_id"]
question = data["interrupt"]["question"]

while True:
    print(f"\nQuiz: {question}")
    answer = input("Your answer: ")

    resp = requests.post(f"{BASE}/resume", json={
        "thread_id": thread_id,
        "answer": answer
    })
    data = resp.json()

    if data["done"]:
        print(f"\n=== Session complete ===")
        print(f"Score: {data['score']}/{data['total_lessons']}")
        break

    question = data["interrupt"]["question"]

requests.post(f"{BASE}/save", json={
    "topic": topic,
    "score": data["score"],
    "total": data["total_lessons"]
})
print("Progress saved!")