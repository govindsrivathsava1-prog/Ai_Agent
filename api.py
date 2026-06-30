from agent import agent
from memory import load_progress, save_progress
from pydantic import BaseModel
from fastapi import FastAPI
from langgraph.types import Command
import uuid


app = FastAPI(title="AI Study Agent API", version="1.0")


class StartRequest(BaseModel):
    topic: str = ""

class ResumeRequest(BaseModel):
    thread_id: str
    answer: str
 
class SaveRequest(BaseModel):
    topic: str
    score: int
    total: int

# ── Endpoint 1: health check ────────────────────────────────────
@app.get("/") 
def root(): 
    return {"status": "ok", "message": "AI Study Agent API is running"}

@app.post("/start")
def start_session(req: StartRequest):
    """Starts a brand new graph run. Generates a thread_id so this run
    can be resumed later. Runs planner -> teacher -> quiz_node until
    quiz_node hits interrupt() and the graph pauses."""

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "topic": req.topic,
        "lessons": [],
        "current": 0,
        "teaching": "",
        "question": "",
        "user_answer": "",
        "score": 0,
        "feedback": ""
    }

    result = agent.invoke(initial_state, config=config)

    return {
        "thread_id": thread_id,
        "interrupt": result["__interrupt__"][0].value
    }

@app.post("/resume")
def resume_session(req:ResumeRequest):
    """Resumes a paused graph run with the user's answer.
    Continues through grading, eval, should_continue, and either
    loops back to teacher_node (next interrupt) or finishes."""

    config = {"configurable": {"thread_id":req.thread_id}}

    result = agent.invoke(Command(resume=req.answer), config=config)

    if "__interrupt__" in result:
        return {
            "done": False,
            "thread_id": req.thread_id,
            "interrupt": result["__interrupt__"][0].value
        }
    
    return {
        "done": True,
        "thread_id": req.thread_id,
        "topic": result["topic"],
        "score": result["score"],
        "total_lessons": len(result["lessons"])
    }

@app.post("/save")
def save_endpoint(req: SaveRequest):
    return save_progress(req.topi, req.score, req.total)

@app.get("/progress")
def get_progress():
    return load_progress()
