"""
memory.py — SQLite-backed memory for the voice agent.

Two tables:
  conversations  → every message, timestamped (rolling log)
  facts          → long-term facts about the user (permanent)

On each turn:
  1. Load recent conversation history from DB
  2. Load all long-term facts and inject into context
  3. After Claude replies, save both turns
  4. Ask Claude if anything is worth remembering long-term → save if yes
"""

import sqlite3
import json
import datetime
import requests
import config

DB_PATH = config.DB_PATH


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist. Safe to call every startup."""
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            role      TEXT NOT NULL,
            content   TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS facts (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            fact      TEXT NOT NULL UNIQUE,
            added_on  TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


# ── Facts ──────────────────────────────────────────────────────────────────────

def seed_facts(facts: list[str]):
    """Insert initial facts about the user (skips duplicates)."""
    conn = _connect()
    now = _now()
    for fact in facts:
        conn.execute(
            "INSERT OR IGNORE INTO facts (fact, added_on) VALUES (?, ?)",
            (fact, now),
        )
    conn.commit()
    conn.close()


def add_fact(fact: str):
    conn = _connect()
    conn.execute(
        "INSERT OR IGNORE INTO facts (fact, added_on) VALUES (?, ?)",
        (fact.strip(), _now()),
    )
    conn.commit()
    conn.close()


def get_all_facts() -> list[str]:
    conn = _connect()
    rows = conn.execute("SELECT fact FROM facts ORDER BY id").fetchall()
    conn.close()
    return [r["fact"] for r in rows]


# ── Conversation log ───────────────────────────────────────────────────────────

def save_turn(role: str, content: str):
    conn = _connect()
    conn.execute(
        "INSERT INTO conversations (role, content, timestamp) VALUES (?, ?, ?)",
        (role, content, _now()),
    )
    conn.commit()
    conn.close()


def load_recent_history(n_turns: int = None) -> list[dict]:
    """Return the last n_turns of conversation as a list of {role, content} dicts."""
    if n_turns is None:
        n_turns = config.CONTEXT_WINDOW_TURNS

    conn = _connect()
    rows = conn.execute(
        """
        SELECT role, content FROM conversations
        ORDER BY id DESC
        LIMIT ?
        """,
        (n_turns * 2,),
    ).fetchall()
    conn.close()

    # fetchall gives newest-first; reverse to chronological order
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


# ── Auto fact extraction ───────────────────────────────────────────────────────

EXTRACT_PROMPT = """You are a memory assistant. Given the user's message below,
decide if it contains a personal fact worth remembering long-term
(name, location, job, hobby, preference, goal, relationship, etc.).

If yes, reply with ONLY a single short sentence starting with "FACT:".
If no, reply with ONLY the word "NONE".

User message: {message}"""


def maybe_extract_fact(user_message: str):
    """Ask the LLM if the user said something worth remembering. Save if yes."""
    prompt = EXTRACT_PROMPT.format(message=user_message)
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.1-8b-instant",  # fast small model for this meta-task
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 60,
        "temperature": 0,
    }
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        if text.startswith("FACT:"):
            fact = text[5:].strip()
            add_fact(fact)
            print(f"[Memory] Saved fact: {fact}")
    except Exception as e:
        print(f"[Memory] Fact extraction skipped: {e}")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def facts_as_context() -> str:
    """Format all facts as a short paragraph for injection into the system prompt."""
    facts = get_all_facts()
    if not facts:
        return ""
    lines = "\n".join(f"- {f}" for f in facts)
    return f"\n\nWhat you know about the user:\n{lines}"
