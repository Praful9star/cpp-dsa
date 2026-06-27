"""
tools/journal.py — Voice journal and brain dump mode.

"Journal entry: today was productive"
"Brain dump" → 60s of free talk → organized action list
"Read my journal"
"""

import sqlite3
import datetime
import requests
import config

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _conn():
    c = sqlite3.connect(config.DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )""")
    c.commit()
    return c


def add_journal_entry(text: str) -> str:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    c = _conn()
    c.execute("INSERT INTO journal (entry, timestamp) VALUES (?, ?)", (text.strip(), ts))
    c.commit()
    c.close()
    return f"Saved to your journal at {ts}."


def read_journal(count: int = 5) -> str:
    c = _conn()
    rows = c.execute(
        "SELECT entry, timestamp FROM journal ORDER BY id DESC LIMIT ?", (count,)
    ).fetchall()
    c.close()
    if not rows:
        return "Your journal is empty. Say 'journal entry' followed by what you want to record."
    entries = [f"[{r[1]}] {r[0]}" for r in reversed(rows)]
    return "Here are your recent journal entries: " + " | ".join(entries)


def brain_dump(raw_text: str) -> str:
    """Send a brain dump to Groq and get organized action items."""
    add_journal_entry(f"[Brain dump] {raw_text[:300]}")
    prompt = (
        "Praful just said everything on his mind in a brain dump. "
        "Organize it into: tasks to act on, things to think about later, and any emotional notes. "
        "Be brief and spoken-friendly — no bullet points, no markdown, just natural sentences.\n\n"
        f"Brain dump: {raw_text}"
    )
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": config.GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 350,
        "temperature": 0.6,
    }
    try:
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Brain dump organizing failed: {e}"


def clear_journal() -> str:
    c = _conn()
    c.execute("DELETE FROM journal")
    c.commit()
    c.close()
    return "Journal cleared."


def journal_stats() -> str:
    c = _conn()
    total = c.execute("SELECT COUNT(*) FROM journal").fetchone()[0]
    first = c.execute("SELECT timestamp FROM journal ORDER BY id ASC LIMIT 1").fetchone()
    c.close()
    if not total:
        return "No journal entries yet."
    return f"You have {total} journal entries, going back to {first[0] if first else 'unknown'}."
