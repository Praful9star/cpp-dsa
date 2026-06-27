"""
tools/dream.py — Dream journal with AI psychological interpretation.

"I had a dream about falling"
"Interpret my dream: I was running from something"
"What does dreaming about water mean"
"Read my dream journal"
"Dream patterns"
"""

import sqlite3
import datetime
import re
import requests
import config

DB_PATH = config.DB_PATH
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

STOP_WORDS = {'the', 'and', 'was', 'that', 'this', 'with', 'from', 'then', 'were',
              'have', 'been', 'they', 'there', 'some', 'about', 'just', 'like'}


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS dreams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dream TEXT NOT NULL,
        interpretation TEXT,
        date TEXT NOT NULL
    )""")
    c.commit()
    return c


def log_and_interpret(text: str) -> str:
    dream = re.sub(
        r"^(i had a dream|interpret my dream|log dream|dream about|dream:)[:\s]*",
        "", text.lower(), flags=re.IGNORECASE,
    ).strip() or text

    prompt = (
        f"Praful (18, Lucknow, ambitious CS student, about to move cities for college) "
        f"described this dream: '{dream}'. "
        f"Give a thoughtful 3-4 sentence psychological interpretation. "
        f"Use Jungian symbolism or common dream psychology. "
        f"Relate it subtly to his life stage — transition, ambition, identity. "
        f"Be specific and a bit mysterious. No generic 'dreams about falling mean anxiety' clichés."
    )
    interpretation = _ask(prompt)

    c = _conn()
    c.execute("INSERT INTO dreams (dream, interpretation, date) VALUES (?, ?, ?)",
              (dream, interpretation, str(datetime.date.today())))
    c.commit()
    c.close()
    return interpretation


def read_dreams(count: int = 3) -> str:
    c = _conn()
    rows = c.execute(
        "SELECT dream, date FROM dreams ORDER BY id DESC LIMIT ?", (count,)
    ).fetchall()
    c.close()
    if not rows:
        return "No dreams logged yet. Tell me about one when you wake up — even fragments count."
    entries = [f"[{r[1]}] {r[0][:100]}" for r in reversed(rows)]
    return "Recent dreams: " + " | ".join(entries)


def dream_patterns() -> str:
    c = _conn()
    rows = c.execute("SELECT dream FROM dreams ORDER BY id DESC LIMIT 20").fetchall()
    c.close()
    if len(rows) < 3:
        return "Log at least 3 dreams before I can find patterns."

    all_text = " ".join(r[0] for r in rows)
    words = re.findall(r"\b[a-z]{4,}\b", all_text.lower())
    freq: dict = {}
    for w in words:
        if w not in STOP_WORDS:
            freq[w] = freq.get(w, 0) + 1
    top = [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:8]]

    prompt = (
        f"Praful's recurring dream themes (most frequent words): {', '.join(top)}. "
        f"Based on these themes, give a 2-3 sentence insight into what his subconscious "
        f"seems preoccupied with. Be specific and insightful — relate to a young person's psyche."
    )
    return _ask(prompt)


def _ask(prompt: str) -> str:
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": config.GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 250,
        "temperature": 0.8,
    }
    try:
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return "Dream saved, but couldn't interpret right now. Try again when connected."
