"""
tools/spaced_repetition.py — Track DSA weak spots and schedule re-reviews.

"I'm struggling with recursion"
"I don't understand trees"
"What should I review today"
"I got it — mark recursion understood"
"""

import sqlite3
import datetime
import config

DB_PATH = config.DB_PATH
INTERVALS = [1, 3, 7, 14, 30]  # days between reviews


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS sr_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        concept TEXT NOT NULL UNIQUE,
        difficulty INTEGER DEFAULT 3,
        last_reviewed TEXT,
        next_review TEXT,
        review_count INTEGER DEFAULT 0
    )""")
    c.commit()
    return c


def mark_struggle(concept: str) -> str:
    concept = concept.strip()
    today = str(datetime.date.today())
    next_r = str(datetime.date.today() + datetime.timedelta(days=1))
    c = _conn()
    c.execute(
        """INSERT INTO sr_cards (concept, difficulty, last_reviewed, next_review)
           VALUES (?, 4, ?, ?)
           ON CONFLICT(concept) DO UPDATE SET
             difficulty = MIN(difficulty + 1, 5),
             next_review = excluded.next_review""",
        (concept, today, next_r),
    )
    c.commit()
    c.close()
    return f"Noted — '{concept}' flagged as tricky. I'll remind you to review it tomorrow."


def mark_understood(concept: str) -> str:
    concept = concept.strip()
    c = _conn()
    row = c.execute(
        "SELECT difficulty, review_count FROM sr_cards WHERE concept=?", (concept,)
    ).fetchone()
    if not row:
        c.close()
        return f"'{concept}' isn't in your review list. Say 'I'm struggling with {concept}' first."

    diff, count = row
    diff = max(1, diff - 1)
    interval = INTERVALS[min(count, len(INTERVALS) - 1)]
    next_r = str(datetime.date.today() + datetime.timedelta(days=interval))
    today = str(datetime.date.today())
    c.execute(
        """UPDATE sr_cards SET difficulty=?, last_reviewed=?, next_review=?, review_count=review_count+1
           WHERE concept=?""",
        (diff, today, next_r, concept),
    )
    c.commit()
    c.close()
    return f"Awesome — '{concept}' understood. Next review in {interval} day{'s' if interval != 1 else ''}."


def get_due_reviews() -> str:
    today = str(datetime.date.today())
    c = _conn()
    rows = c.execute(
        "SELECT concept, difficulty FROM sr_cards WHERE next_review <= ? ORDER BY difficulty DESC",
        (today,),
    ).fetchall()
    c.close()
    if not rows:
        return "Nothing due for review today — you're all caught up! Keep grinding."
    names = [f"{r[0]} (level {r[1]}/5)" for r in rows]
    return (f"{len(rows)} concept{'s' if len(rows) > 1 else ''} to review: {', '.join(names)}. "
            f"Say 'explain X' or 'I got it — mark X understood' after each one.")


def list_all_cards() -> str:
    c = _conn()
    rows = c.execute(
        "SELECT concept, difficulty, next_review FROM sr_cards ORDER BY next_review ASC LIMIT 15"
    ).fetchall()
    c.close()
    if not rows:
        return "No review cards yet. Tell me what you're struggling with to add one."
    items = [f"{r[0]} (d={r[1]}, next: {r[2]})" for r in rows]
    return "Your review cards: " + ", ".join(items)
