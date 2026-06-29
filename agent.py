import os
from dotenv import load_dotenv
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_openai import OpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from memory import load_progress, save_progress, show_progress, alread_mastered
from rag import load_pdf_to_chroma, get_vectorstore, search_notes
from eval import evaluate_lesson, save_eval, show_eval_summary

load_dotenv()


llm = ChatGoogleGenerativeAI(
    google_api_key=os.environ.get("GEMINI_API_KEY"),
    model = "gemini-2.0-flash",
    temperature=0.7
    )

class StudyState(TypedDict):
    topic: str
    lessons: List[str]
    current: int
    teaching: str
    question: str
    user_answer: str
    score: int
    feedback: str

def planner(state: StudyState) -> StudyState:
    topic = state["topic"]
    print(f"Planner node started")
    prompt = f"""you are a study planner. The student wants to learn: {topic}. Give exaclty 3 lesson titles as a numbered list.
             Format: 1. Title, 2. Title, 3. Title. 
             Keep each title short(under 8 words)."""
    response = llm.invoke(prompt)
    raw = response.content
    lessons = []
    for line in raw.strip().split("\n"):
        if line.strip() and line[0].isdigit():
            line = line.strip()
            lessons.append(line[3:].strip())
    state["lessons"] = lessons
    state["current"] = 0
    #print(f"Planner generated lessons: {lessons}")
    return state

#state = planner({"topic": "Python programming", "lessons": [], "current": 0, "teaching": "", "question": "", "user_answer": "", "score": 0, "feedback": ""})

def teacher_node(state: StudyState) -> StudyState:
    print("Teacher node started")
    #print(state)
    lessons = state["lessons"]
    current = state["current"]
    lesson_title = lessons[current]
    #Call vectorstore to get relevant notes for the lesson
    vectorstore = get_vectorstore()
    context = search_notes(vectorstore, lesson_title)
    if context.strip():
        print(f"Found relevant notes for lesson: {lesson_title}")
        prompt = f"""you are a friendly teacher. Explain this topic in 3-4 simple sentences a begunner can understand: {lesson_title}.
             Use ONLY the following notes as context: {context} to explain: {lesson_title}.
             End with one key takeaway Starting with key point."""
    else:
        prompt = f"""you are a friendly teacher. Explain this topic in 3-4 simple sentences a begunner can understand: {lesson_title}.
             End with one key takeaway Starting with key point."""
    response = llm.invoke(prompt)
    teaching = response.content
    state["teaching"] = teaching
    #print(f"\n--- Lesson {current + 1}: {lesson_title} ---")
    #print(f"Teaching: {teaching}")
    #print(f"state: {state}")
    return state

def quiz_node(state: StudyState) -> StudyState:
    print("Quiz node started")
    teaching = state["teaching"]
    lessons = state['lessons']
    current = state['current']
    lesson_title = lessons[current]
    q_prompt = f"""Based on this lesson:{teaching} Write one short quiz question (one sentenc only)."""
    question = llm.invoke(q_prompt).content
    state["question"] = question
    #print(f"\nQuiz Question: {question}")
    user_answer = input("Your Answer: ")
    state["user_answer"] = user_answer
    grade_prompt = f"""Question:{question} Student's answer: {user_answer}. Is this correct?. Reply with 'Correct' or 'Incorrect', then one sentence of feedback."""
    feedback = llm.invoke(grade_prompt).content
    state["feedback"] = feedback
    if "CORRECT" in feedback.upper():
        state["score"] += 1
        #print(f"\nFeedback: {feedback}")
    else:
        #print(f"\nFeedback: {feedback}")
        state["score"] += 0
    

    print(" [evaluation lesson quality...]")
    scores = evaluate_lesson(topic = state['topic'], lesson_title = lesson_title, teaching = teaching, question = question)
    save_eval(scores)
    if scores:
        print(f"[quality score: {scores.get('overall', '?')}/5 - {scores.get('reason', '')}]")
    
    state["current"] += 1
    return state

def should_continue(state: StudyState) -> str:
    if state["current"] < len(state["lessons"]):
        return "teacher"
    return "end"

#Build Graph
graph = StateGraph(StudyState)
graph.add_node("planner", planner)
graph.add_node("teacher", teacher_node)
graph.add_node("quiz", quiz_node)
graph.set_entry_point("planner")

graph.add_edge("planner", "teacher")
graph.add_edge("teacher", "quiz")
graph.add_conditional_edges("quiz", should_continue, {"teacher": "teacher", "end": END})
agent = graph.compile()

if __name__ == "__main__":
    """Load pdf to ChromaDB"""
    PDF_PATH = "AI_Study_Notes.pdf"
    if not os.path.exists("chroma_db"):
        if os.path.exists(PDF_PATH):
            load_pdf_to_chroma(PDF_PATH)
        else:
            print(f"PDF file {PDF_PATH} not found. Using Gemini's knowledge base for teaching.")
            


    show_progress()

    topic = input("Enter a topic you want to learn: ")
    if alread_mastered(topic):
        again = input("You have already mastered this topic. Do you want to study it again? (y/n): ")
        if again.lower() != 'y':
            print("pick a new topic and comeback")
            exit(0)

    initial_state = {
        "topic": topic,
        "lessons": [],
        "current": 0,
        "teaching": "",
        "question": "",
        "user_answer": "",
        "score": 0,
        "feedback": ""

    } 
    print(initial_state)


    result = agent.invoke(initial_state)


    total_lessons = len(result["lessons"])

    score = result["score"]
    progress = save_progress(topic, score, total_lessons)

    pct = int(score/total_lessons*100) if total_lessons > 0 else 0


    print(f"\n===Session complete ===")
    print(f"Topic: {result['topic']}")
    print(f"Score: {score}/{total_lessons}")

    if pct >= 70:
        print("Congratulations! You have mastered this topic.")
    else:
        print("Keep practicing to master this topic.")

    print(f"Total sessions so far: {progress['total_sessions']}")

    show_eval_summary()


