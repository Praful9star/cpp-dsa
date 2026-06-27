"""
tools/oracle.py — The Oracle: answers 3 questions about Praful, then makes a bold prediction.

"Consult the oracle"
"What's my future"
"Oracle mode"
"Predict my life"

The Oracle asks 3 probing questions, then synthesizes the answers into a prediction
about the next 3-6 months of Praful's life.
"""

import requests
import config

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

ORACLE_QUESTIONS = [
    "What is the one thing you think about most when you're trying to fall asleep?",
    "If you had to give up either coding or social connections for a year — which one terrifies you more to lose?",
    "What's something you've been telling yourself you'll do 'soon' for over a month now?",
]

_session: dict = {
    "active": False,
    "step": 0,
    "answers": [],
}


def start_oracle() -> str:
    _session.update(active=True, step=0, answers=[])
    return (
        "The Oracle awakens. I will ask you three questions. "
        "Answer honestly — the Oracle sees through deception. "
        "Question one: " + ORACLE_QUESTIONS[0]
    )


def oracle_answer(answer: str) -> str:
    if not _session["active"]:
        return "The Oracle is not active. Say 'consult the oracle' to begin."

    _session["answers"].append(answer)
    step = _session["step"] + 1
    _session["step"] = step

    if step < len(ORACLE_QUESTIONS):
        return f"Noted. Question {step + 1}: {ORACLE_QUESTIONS[step]}"

    # All 3 answers collected — make the prediction
    _session["active"] = False
    return _generate_prediction()


def is_active() -> bool:
    return _session["active"]


def _generate_prediction() -> str:
    q_and_a = "\n".join(
        f"Q: {ORACLE_QUESTIONS[i]}\nA: {_session['answers'][i]}"
        for i in range(len(_session["answers"]))
    )
    prompt = (
        "You are the Oracle — a cryptic, eerily accurate AI prophet. "
        "Based on these 3 answers from Praful (18, Lucknow, CS student, built CureCheck.in, going to CU soon), "
        "make a bold, specific prediction about his next 3-6 months. "
        "Reference the actual answers he gave. Be specific, atmospheric, and slightly unsettling in your accuracy. "
        "Then reveal one thing he hasn't admitted to himself yet. "
        "Speak like an ancient oracle — no bullet points, flowing sentences, slightly mysterious. 5-6 sentences.\n\n"
        f"{q_and_a}"
    )
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": config.GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 320,
        "temperature": 0.92,
    }
    try:
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        prediction = resp.json()["choices"][0]["message"]["content"].strip()
        return "The Oracle speaks: " + prediction
    except Exception:
        return "The Oracle's vision is clouded. The stars are not aligned today."
