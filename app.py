import json, os
import streamlit as st
from dotenv import load_dotenv
from memory import load_progress, save_progress
from eval import evaluate_lesson, save_eval
from agent import teacher_node, StudyState, llm
from rag import load_pdf_to_chroma

load_dotenv()

# ── Page config ───────────────────────────────
st.set_page_config(page_title="AI Study Agent", page_icon="🤖")

# ── Load PDF once ─────────────────────────────
PDF_PATH = "AI_Study_Notes.pdf"
if not os.path.exists("chroma_db") and os.path.exists(PDF_PATH):
    load_pdf_to_chroma(PDF_PATH)

# ── Sidebar navigation ────────────────────────
page = st.sidebar.radio("Navigation", ["📚 Study", "📊 Progress"])


# ══════════════════════════════════════════════
# PAGE 1 — STUDY
# ══════════════════════════════════════════════
if page == "📚 Study":
    st.title("🤖 AI Study Agent")
    st.caption("Powered by LangGraph + GPT-4o")

    # Initialise all session state keys once
    defaults = {
        "stage": "input",       # input | lesson | done
        "lesson_idx": 0,
        "lessons": [],
        "topic": "",
        "score": 0,
        "teachings": {},        # {idx: {teaching, question}}
        "submitted": {},        # {idx: {correct, feedback, scores}}
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ── SCREEN 1: Topic input ─────────────────
    if st.session_state.stage == "input":
        st.session_state.score = 0
        st.session_state.teachings = {}
        st.session_state.submitted = {}

        topic = st.text_input(
            "What do you want to learn?",
            placeholder="e.g. neural networks, Python loops, transformers"
        )

        if topic:
            progress = load_progress()
            already_done = topic.lower() in [
                t.lower() for t in progress.get("completed_topics", [])
            ]
            if already_done:
                st.warning(f"You already mastered **{topic}**! You can still study it again.")

        if st.button("🚀 Start session", disabled=not topic):
            with st.spinner("Planning lessons..."):
                
                # Instead call planner directly to get lesson titles only
                from agent import planner
                init = {
                    "topic": topic, "lessons": [], "current": 0,
                    "teaching": "", "question": "", "user_answer": "",
                    "score": 0, "feedback": ""
                }
                planned = planner(init)

            st.session_state.topic = topic
            st.session_state.lessons = planned["lessons"]
            st.session_state.lesson_idx = 0
            st.session_state.stage = "lesson"
            st.rerun()

    # ── SCREEN 2: Lesson + Quiz ───────────────
    elif st.session_state.stage == "lesson":
        idx     = st.session_state.lesson_idx
        lessons = st.session_state.lessons
        total   = len(lessons)
        topic   = st.session_state.topic

        # Progress bar
        st.progress((idx) / total, text=f"Lesson {idx + 1} of {total}")
        st.subheader(f"📖 Lesson {idx + 1}: {lessons[idx]}")  # BUG FIX 1: removed st.chat_message(lessons)

        # Generate lesson content once per lesson index — cache in session_state
        if idx not in st.session_state.teachings:
            with st.spinner("Preparing lesson..."):
                tmp = {
                    "topic": topic, "lessons": lessons, "current": idx,
                    "teaching": "", "question": "", "user_answer": "",
                    "score": 0, "feedback": ""
                }
                taught = teacher_node(tmp)
                q_prompt = (
                    f"Write one short quiz question (one sentence only) "
                    f"about: {taught['teaching']}"
                )
                question = llm.invoke(q_prompt).content

            st.session_state.teachings[idx] = {
                "teaching": taught["teaching"],
                "question": question,
            }

        data = st.session_state.teachings[idx]

        # Show lesson
        st.info(data["teaching"])
        st.divider()

        # ── Quiz ──────────────────────────────
        st.subheader("🧠 Quiz time")
        st.write(data["question"])

        answer = st.text_area("Your answer:", key=f"ans_{idx}")

       
        
        if st.button("Submit answer ✓", disabled=not answer, key=f"submit_{idx}"):
            with st.spinner("Grading..."):
                fb = llm.invoke(
                    f"Question: {data['question']}\n"
                    f"Student answer: {answer}\n"
                    f"Reply with EXACTLY 'Correct' or 'Incorrect' as the first word, "
                    f"then one sentence of feedback."
                ).content

                scores = evaluate_lesson(
                    topic=topic,
                    lesson_title=lessons[idx],
                    teaching=data["teaching"],
                    question=data["question"],
                )
                save_eval(scores)

            
            first_word = fb.strip().split()[0].upper()
            print(first_word)
            is_correct = False
            if first_word == "CORRECT.":
                is_correct = True
                print(is_correct)
            # Store result so it survives re-render
            st.session_state.submitted[idx] = {
                "correct": is_correct,
                "feedback": fb,
                "scores": scores,
            }

            # Add to score only once
            if is_correct:
                st.session_state.score += 1

            st.rerun()  # re-render to show result + Next button cleanly

        # Show result if already submitted (persists across re-renders)
        if idx in st.session_state.submitted:
            result = st.session_state.submitted[idx]
            fb     = result["feedback"]
            scores = result["scores"]

            print(result)
            print(result['correct'])
            if result["correct"]:
                st.success(f"✅ {fb}")
            else:
                st.error(f"❌ {fb}")

            if scores:
                st.caption(
                    f"Lesson quality: {scores.get('overall', '?')}/5 "
                    f"— {scores.get('reason', '')}"
                )

            st.divider()

            # BUG FIX 4: Next button is OUTSIDE submit block — always visible after submit
            if idx + 1 < total:
                if st.button("Next lesson →", key=f"next_{idx}"):
                    st.session_state.lesson_idx += 1
                    st.rerun()
            else:
                if st.button("🎉 See results"):
                    st.session_state.stage = "done"
                    st.rerun()

    # ── SCREEN 3: Session complete ────────────
    elif st.session_state.stage == "done":
        topic  = st.session_state.topic
        score  = st.session_state.score          # BUG FIX 3: already an int
        total  = len(st.session_state.lessons)
        pct    = int(score / total * 100) if total > 0 else 0
        passed = pct >= 70

        progress = save_progress(topic, score, total)

        if passed:
            st.balloons()

        st.title("🎉 Session complete!")

        col1, col2, col3 = st.columns(3)
        col1.metric("Score",      f"{score}/{total}")
        col2.metric("Percentage", f"{pct}%")
        col3.metric("Result",     "PASSED ✓" if passed else "Try again")

        if passed:
            st.success("Topic marked as mastered! Pick something new to learn.")
        else:
            st.warning(
                f"You need 70% to master this topic. "
                f"You got {pct}%. Give it another go!"
            )

        st.metric("Total sessions so far", progress["total_sessions"])

        if st.button("📚 Study another topic"):
            for k in ["stage", "lessons", "topic", "score", "teachings",
                       "submitted", "lesson_idx"]:
                st.session_state.pop(k, None)
            st.rerun()


# ══════════════════════════════════════════════
# PAGE 2 — PROGRESS DASHBOARD
# ══════════════════════════════════════════════
elif page == "📊 Progress":
    st.title("📊 Your Progress")

    progress    = load_progress()
    scores_data = progress.get("scores", {})

    col1, col2, col3 = st.columns(3)
    col1.metric("Topics studied", len(scores_data))
    col2.metric("Mastered",       len(progress.get("completed_topics", [])))
    col3.metric("Total sessions", progress.get("total_sessions", 0))

    if scores_data:
        st.subheader("Topics")
        for topic, data in scores_data.items():
            pct      = int(data["score"] / data["total"] * 100)
            mastered = topic in progress.get("completed_topics", [])
            icon     = "✅" if mastered else "🔄"
            st.progress(
                pct / 100,
                text=f"{icon} {topic}: {data['score']}/{data['total']} ({pct}%) — {data['date']}"
            )
    else:
        st.info("No sessions yet. Go to 📚 Study to get started!")

    if os.path.exists("eval_log.json"):
        with open("eval_log.json") as f:
            content = f.read().strip()
            log = json.loads(content) if content else []
        if log:
            st.subheader("Lesson Quality (LLM-judged)")
            avg_c = sum(e.get("clarity",  0) for e in log) / len(log)
            avg_a = sum(e.get("accuracy", 0) for e in log) / len(log)
            avg_o = sum(e.get("overall",  0) for e in log) / len(log)
            c1, c2, c3 = st.columns(3)
            c1.metric("Avg Clarity",  f"{avg_c:.1f}/5")
            c2.metric("Avg Accuracy", f"{avg_a:.1f}/5")
            c3.metric("Avg Overall",  f"{avg_o:.1f}/5")
    else:
        st.info("Complete a study session to see lesson quality scores.")