# Personal AI Study Agent
> A stateful, multi-node AI tutor built with LangGraph and Google Gemini.
> Teaches any topic, quizzes you, and remembers your progress across sessions.
> Exposed both as a terminal app and as a FastAPI backend that drives the same compiled LangGraph graph.

## Demo — terminal

```
$ python agent.py
What do you want to study? machine learning

Plan ready: ['What is ML', 'Supervised Learning', 'Neural Networks']

--- Lesson 1: What is ML ---
Machine learning is a branch of AI where systems learn patterns
from data rather than following explicit rules...
Key point: ML systems improve automatically through experience.

Quiz: What distinguishes supervised from unsupervised learning?
Your Answer: supervised uses labelled data

Feedback: Correct — precise distinction between the two paradigms.
  [quality score: 4.3/5 — Clear but could include a concrete example.]

===Session complete ===
Score: 3/3
Congratulations! You have mastered this topic.
```

## Demo — API

```
POST /start    {"topic": "machine learning"}
  -> {"thread_id": "a1b2...", "interrupt": {"question": "What is..."}}

POST /resume   {"thread_id": "a1b2...", "answer": "It uses labeled data"}
  -> {"done": false, "interrupt": {"question": "Next question..."}}
  -> ... repeat until ...
  -> {"done": true, "topic": "machine learning", "score": 2, "total_lessons": 3}

POST /save     {"topic": "machine learning", "score": 2, "total": 3}
GET  /progress
```

## Architecture

```
User input (topic)
       |
       v
+--------------+
|   planner    |  -> Breaks topic into 3 lessons via LLM
+------+-------+
       |
       v
+--------------+
| teacher_node |  -> Retrieves from ChromaDB (RAG), explains lesson
+------+-------+
       |
       v
+--------------+
|  quiz_node   |  -> Generates question, interrupt() pauses for answer,
+------+-------+     grades response, runs LLM-as-judge eval
       |
  score loop:
  more lessons? --> back to teacher_node
  all done?     --> END
```

The graph is compiled once in `agent.py` with a `MemorySaver` checkpointer. The terminal entrypoint (`python agent.py`) drives it with blocking `input()` calls inside `quiz_node`. The API entrypoint (`uvicorn api:app`) drives the *same compiled graph* through `agent.invoke()` and `Command(resume=...)` — `quiz_node` calls `interrupt()` instead of `input()`, which pauses the entire graph mid-execution and hands control back to the caller. Each HTTP request resumes exactly where the graph left off, using a `thread_id` to identify the run.

## Features

| Feature | Implementation |
|---|---|
| Multi-node agent | LangGraph `StateGraph` with typed state (`StudyState`) |
| RAG pipeline | ChromaDB + Gemini embeddings |
| LLM-as-judge eval | Scores clarity, accuracy, difficulty per lesson |
| Session memory | JSON persistence with 70% pass threshold |
| Progress tracking | Scores, dates, mastered topics across sessions |
| Real-time API | FastAPI driving the actual LangGraph graph via `interrupt()` / `Command(resume=...)` — not a re-implementation |
| Graceful fallback | RAG miss -> Gemini knowledge; eval fail -> agent continues |

## Tech Stack

- **Framework**: LangGraph (1.x), LangChain
- **API**: FastAPI, Uvicorn
- **LLM**: Google Gemini (gemini-2.0-flash)
- **Embeddings**: Gemini text-embedding-004
- **Vector store**: ChromaDB (local)
- **Language**: Python 3.11

## Key Design Decisions

**Why TypedDict state?**
LangGraph requires a typed state schema to validate inputs/outputs at each node boundary. This catches bugs early and makes the data flow explicit.

**Why conditional edges?**
After each quiz, a routing function checks the lesson index against the lesson count. More lessons remaining routes back to `teacher_node`; otherwise the graph reaches `END`. This makes the agent adaptive rather than linear.

**Why `interrupt()` instead of re-implementing the loop in the API layer?**
The early version of the API called individual node functions directly from FastAPI endpoints, which meant the orchestration logic (the loop, the conditional routing) lived in two places — once in the graph's edges, once in the API's request handling. Using `interrupt()` and `Command(resume=...)` means there is exactly one place the control flow is defined: the compiled graph. The API layer is pure plumbing — it never decides what runs next, it only feeds answers back in and reports what the graph paused on.

**Why LLM-as-judge?**
Manual evaluation doesn't scale. Using Gemini to score its own outputs on clarity, accuracy and difficulty gives automated quality signals across every session, surfacing regressions without human review.

**Why JSON over a database?**
For a single-user local agent, JSON is zero-infrastructure and inspectable. The memory module is designed so swapping to Postgres requires changing only `load_progress()` and `save_progress()`.

**Why `MemorySaver` and not a persistent checkpointer?**
`MemorySaver` keeps paused graph state in RAM for the lifetime of the server process — sufficient for a single-user demo. A production deployment would swap in `SqliteSaver` or `PostgresSaver` so in-progress sessions survive a server restart.

## Results

- Tested across 10+ topics and 30+ study sessions
- Average lesson quality score: 4.2/5 (LLM-judged)
- Pass rate (>=70% quiz score): ~78% of sessions

## Setup

```bash
git clone https://github.com/govindsrivathsava1-prog/Ai_Agent
cd Ai_Agent
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
```

Create a `.env` file:
```
GEMINI_API_KEY=your-key-from-aistudio.google.com
```

Optionally add a PDF to use RAG:
```bash
# Place a PDF in the folder as AI_Study_Notes.pdf
python agent.py
```

## Running it

**Terminal mode:**
```bash
python agent.py
```

**API mode:**
```bash
uvicorn api:app --reload
```
Then either:
- Open `http://localhost:8000/docs` for interactive testing, or
- Run the included `test_client.py` for a scripted end-to-end session:
```bash
pip install requests
python test_client.py
```

## API Reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Health check |
| POST | `/start` | Start a new session for a topic. Returns `thread_id` and the first quiz question. |
| POST | `/resume` | Submit an answer for the current `thread_id`. Returns the next question, or final results if the session is complete. |
| POST | `/save` | Save a completed session's score to `progress.json`. |
| GET | `/progress` | View all saved progress. |

## File Structure

```
study-agent/
|-- agent.py         # LangGraph agent: state, nodes, interrupt-based quiz_node, compiled graph
|-- api.py            # FastAPI wrapper around agent.invoke() / Command(resume=...) - no business logic
|-- test_client.py    # Minimal scripted client exercising the full API loop
|-- memory.py         # Session persistence and progress tracking
|-- rag.py             # PDF loading, ChromaDB, semantic search
|-- eval.py            # LLM-as-judge evaluation pipeline
|-- requirements.txt
`-- .env              # API keys (not committed)
```
