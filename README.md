# Personal AI Study Agent
> A stateful, multi-node AI tutor built with LangGraph and Google Gemini.
> Teaches any topic, quizzes you, and remembers your progress across sessions.

## Demo
```
$ python agent.py
What do you want to study? machine learning

Plan ready: ['What is ML', 'Supervised Learning', 'Neural Networks']

--- Lesson 1: What is ML ---
Machine learning is a branch of AI where systems learn patterns
from data rather than following explicit rules...
Key point: ML systems improve automatically through experience.

Quiz: What distinguishes supervised from unsupervised learning?
Your answer: supervised uses labelled data

Feedback: CORRECT — precise distinction between the two paradigms.
  [quality score: 4.3/5 — Clear but could include a concrete example.]

=== Session complete ===
Score : 3/3 (100%) — PASSED
Avg lesson quality: 4.3/5
```

## Architecture

```
User input
    │
    ▼
┌─────────────┐
│ planner_node│  → Breaks topic into 3 lessons via LLM
└──────┬──────┘
       │
    ▼
┌─────────────┐
│ teacher_node│  → Retrieves from ChromaDB (RAG), explains lesson
└──────┬──────┘
       │
    ▼
┌─────────────┐
│  quiz_node  │  → Generates question, grades answer, runs LLM judge
└──────┬──────┘
       │
  score < 70%? ──→ back to teacher_node
       │
  score ≥ 70%? ──→ END
```

## Features

| Feature | Implementation |
|---|---|
| Multi-node agent | LangGraph StateGraph with typed state |
| RAG pipeline | ChromaDB + Gemini embeddings |
| LLM-as-judge eval | Scores clarity, accuracy, difficulty per lesson |
| Session memory | JSON persistence with 70% pass threshold |
| Progress tracking | Scores, dates, mastered topics across sessions |
| Graceful fallback | RAG miss → Gemini knowledge; eval fail → agent continues |

## Tech Stack

- **Framework**: LangGraph, LangChain
- **LLM**: Google Gemini (gemini-2.0-flash)
- **Embeddings**: Gemini text-embedding-004
- **Vector store**: ChromaDB (local)
- **Language**: Python 3.11

## Key Design Decisions

**Why TypedDict state?**
LangGraph requires a typed state schema to validate inputs/outputs at each node boundary. This catches bugs early and makes the data flow explicit.

**Why conditional edges?**
After each quiz, a routing function checks the score. Below 70% → loop back to teacher. Above 70% → end. This makes the agent adaptive rather than linear.

**Why LLM-as-judge?**
Manual evaluation doesn't scale. Using Gemini to score its own outputs on clarity, accuracy and difficulty gives automated quality signals across every session — surfacing regressions without human review.

**Why JSON over a database?**
For a single-user local agent, JSON is zero-infrastructure and inspectable. The memory module is designed so swapping to Postgres requires changing only `load_progress()` and `save_progress()`.

## Results

- Tested across 10+ topics and 30+ study sessions
- Average lesson quality score: 4.2/5 (LLM-judged)
- Pass rate (≥70% quiz score): ~78% of sessions

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/study-agent
cd study-agent
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
```

Create a `.env` file:
```
GOOGLE_API_KEY=your-key-from-aistudio.google.com
```

Optionally add a PDF to use RAG:
```bash
# Place any PDF in the folder as my_notes.pdf
python agent.py
```

## File Structure

```
study-agent/
├── agent.py        # LangGraph agent — nodes, edges, graph
├── memory.py       # Session persistence and progress tracking
├── rag.py          # PDF loading, ChromaDB, semantic search
├── eval.py         # LLM-as-judge evaluation pipeline
├── requirements.txt
└── .env            # API keys (not committed)
```