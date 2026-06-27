"""
tools/emotion_timeline.py — Tracks and visualizes Praful's emotional journey over time.

Scores every saved message for sentiment using keyword matching.
Lets Praful "time travel" back to how he felt on any past day.

"How was I feeling last week"
"Emotional report"
"When was I happiest"
"When was I most stressed"
"My emotional journey"
"How was I feeling on [date]"
"""

import sqlite3
import datetime
import re
import requests
import config

DB_PATH = config.DB_PATH
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

POS_WORDS = {"great", "awesome", "happy", "excited", "love", "amazing", "perfect", "good",
             "nice", "yes", "yay", "cool", "solid", "won", "success", "done", "finished",
             "completed", "proud", "confident", "ready", "motivated", "energized", "pumped"}

NEG_WORDS = {"bad", "tired", "stressed", "anxious", "worried", "sad", "angry", "hate",
             "terrible", "awful", "fail", "failed", "stuck", "confused", "lost", "scared",
             "overwhelmed", "exhausted", "bored", "frustrated", "annoyed", "can't", "useless",
             "hopeless", "depressed", "nervous", "ugly", "broken", "crash", "ugh", "damn"}


def _score(text: str) -> int:
    words = set(text.lower().split())
    pos = len(words & POS_WORDS)
    neg = len(words & NEG_WORDS)
    return pos - neg


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS emotion_log (
        date TEXT PRIMARY KEY,
        score INTEGER DEFAULT 0,
        samples TEXT DEFAULT ''
    )""")
    c.commit()
    return c


def update_today(text: str):
    """Called passively on each user message to update today's score."""
    today = str(datetime.date.today())
    delta = _score(text)
    c = _conn()
    row = c.execute("SELECT score, samples FROM emotion_log WHERE date=?", (today,)).fetchone()
    if row:
        new_score = row[0] + delta
        samples   = (row[1] + " | " + text[:60]) if row[1] else text[:60]
        c.execute("UPDATE emotion_log SET score=?, samples=? WHERE date=?", (new_score, samples, today))
    else:
        c.execute("INSERT INTO emotion_log (date, score, samples) VALUES (?, ?, ?)",
                  (today, delta, text[:60]))
    c.commit()
    c.close()


def emotional_report(days: int = 7) -> str:
    since = str(datetime.date.today() - datetime.timedelta(days=days))
    c = _conn()
    rows = c.execute(
        "SELECT date, score FROM emotion_log WHERE date >= ? ORDER BY date ASC", (since,)
    ).fetchall()
    c.close()

    if not rows:
        return "No emotional data yet — keep talking to me and I'll track your journey."

    scores = [r[1] for r in rows]
    avg    = sum(scores) / len(scores)
    peak_day   = max(rows, key=lambda r: r[1])
    lowest_day = min(rows, key=lambda r: r[1])
    trend = "trending up" if scores[-1] > scores[0] else ("trending down" if scores[-1] < scores[0] else "stable")

    mood_label = ("really good" if avg > 3 else
                  "positive" if avg > 0 else
                  "neutral to low" if avg > -3 else "rough")

    return (
        f"Your emotional {days}-day snapshot: overall mood is {mood_label} (avg score: {avg:.1f}). "
        f"Best day was {peak_day[0]} ({peak_day[1]:+d}), hardest day was {lowest_day[0]} ({lowest_day[1]:+d}). "
        f"You're {trend} right now."
    )


def best_days(n: int = 3) -> str:
    c = _conn()
    rows = c.execute(
        "SELECT date, score FROM emotion_log ORDER BY score DESC LIMIT ?", (n,)
    ).fetchall()
    c.close()
    if not rows:
        return "No emotional history yet."
    days = [f"{r[0]} (score {r[1]:+d})" for r in rows]
    return f"Your {n} happiest days recorded: {', '.join(days)}."


def worst_days(n: int = 3) -> str:
    c = _conn()
    rows = c.execute(
        "SELECT date, score FROM emotion_log ORDER BY score ASC LIMIT ?", (n,)
    ).fetchall()
    c.close()
    if not rows:
        return "No emotional history yet."
    days = [f"{r[0]} (score {r[1]:+d})" for r in rows]
    return f"Your {n} toughest days: {', '.join(days)}. You got through all of them."


def time_travel(date_query: str) -> str:
    """How was Praful feeling on a specific past date?"""
    today = datetime.date.today()
    target = None

    # "last week", "yesterday", "monday"
    t = date_query.lower()
    if "yesterday" in t:
        target = today - datetime.timedelta(days=1)
    elif "last week" in t:
        target = today - datetime.timedelta(days=7)
    elif "last month" in t:
        target = today - datetime.timedelta(days=30)
    else:
        m = re.search(r'(\d{4}-\d{2}-\d{2})', t)
        if m:
            try:
                target = datetime.date.fromisoformat(m.group(1))
            except ValueError:
                pass

    if not target:
        return "Which date? Say 'how was I feeling yesterday' or 'on 2025-06-01'."

    c = _conn()
    row = c.execute("SELECT score, samples FROM emotion_log WHERE date=?",
                    (str(target),)).fetchone()
    c.close()

    if not row:
        return f"No emotional data for {target}. I wasn't tracking that far back."

    score, samples = row
    mood = ("great" if score > 3 else "good" if score > 0 else "okay" if score > -2 else "rough")
    prompt = (
        f"Based on these messages Praful sent on {target} (score: {score:+d}), "
        f"describe how he was feeling that day in 2-3 sentences. "
        f"Sound like you actually remember that day with him. Be specific.\n\nMessages: {samples[:500]}"
    )
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": config.GROQ_MODEL,
               "messages": [{"role": "user", "content": prompt}],
               "max_tokens": 180, "temperature": 0.7}
    try:
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return f"On {target} your mood was {mood} (score {score:+d})."
