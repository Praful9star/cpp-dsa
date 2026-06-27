"""
tools/battle.py — Battle Mode: compete against your past self.

Tracks daily productivity score (messages, pomodoros, notes, expenses logged).
Compares today vs yesterday vs personal best.

"Battle mode"
"How am I doing vs yesterday"
"My personal best"
"Beat my record"
"""

import sqlite3
import datetime
import config

DB_PATH = config.DB_PATH


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS battle_scores (
        date TEXT PRIMARY KEY,
        messages INTEGER DEFAULT 0,
        pomodoros INTEGER DEFAULT 0,
        notes INTEGER DEFAULT 0,
        expenses INTEGER DEFAULT 0,
        score INTEGER DEFAULT 0
    )""")
    c.commit()
    return c


def _compute_score(date_str: str) -> dict:
    c = sqlite3.connect(DB_PATH)

    msgs = c.execute(
        "SELECT COUNT(*) FROM conversations WHERE role='user' AND DATE(timestamp)=?", (date_str,)
    ).fetchone()[0]

    poms = 0
    try:
        poms = c.execute(
            "SELECT COUNT(*) FROM pomodoro_log WHERE date=?", (date_str,)
        ).fetchone()[0]
    except Exception:
        pass

    notes = 0
    try:
        notes = c.execute(
            "SELECT COUNT(*) FROM notes WHERE DATE(timestamp)=?", (date_str,)
        ).fetchone()[0]
    except Exception:
        pass

    exps = 0
    try:
        exps = c.execute(
            "SELECT COUNT(*) FROM expenses WHERE date=?", (date_str,)
        ).fetchone()[0]
    except Exception:
        pass

    c.close()

    score = msgs * 2 + poms * 25 + notes * 5 + exps * 3
    return {"date": date_str, "messages": msgs, "pomodoros": poms,
            "notes": notes, "expenses": exps, "score": score}


def _upsert_score(data: dict):
    c = _conn()
    c.execute(
        """INSERT INTO battle_scores (date, messages, pomodoros, notes, expenses, score)
           VALUES (:date, :messages, :pomodoros, :notes, :expenses, :score)
           ON CONFLICT(date) DO UPDATE SET
             messages=excluded.messages, pomodoros=excluded.pomodoros,
             notes=excluded.notes, expenses=excluded.expenses, score=excluded.score""",
        data,
    )
    c.commit()
    c.close()


def battle_report() -> str:
    today_str     = str(datetime.date.today())
    yesterday_str = str(datetime.date.today() - datetime.timedelta(days=1))

    today     = _compute_score(today_str)
    yesterday = _compute_score(yesterday_str)
    _upsert_score(today)

    c = _conn()
    best_row = c.execute("SELECT date, score FROM battle_scores ORDER BY score DESC LIMIT 1").fetchone()
    c.close()
    best_score = best_row[1] if best_row else 0
    best_date  = best_row[0] if best_row else "N/A"

    t, y = today["score"], yesterday["score"]
    if t > y:
        verdict = f"You're WINNING vs yesterday by {t - y} points! 🔥"
    elif t == y:
        verdict = "Dead even with yesterday. Push harder."
    else:
        verdict = f"Down {y - t} points vs yesterday. Time to grind."

    pb_note = ""
    if t >= best_score and t > 0:
        pb_note = " New personal best — you're breaking records!"
    elif best_score > 0:
        pb_note = f" Personal best is {best_score} pts ({best_date}) — you need {best_score - t} more."

    return (
        f"Today: {t} pts ({today['messages']} msgs, {today['pomodoros']} pomodoros, "
        f"{today['notes']} notes). "
        f"Yesterday: {y} pts. "
        f"{verdict}{pb_note}"
    )


def personal_best() -> str:
    c = _conn()
    rows = c.execute(
        "SELECT date, score, messages, pomodoros FROM battle_scores ORDER BY score DESC LIMIT 3"
    ).fetchall()
    c.close()
    if not rows:
        return "No battle data yet. Start talking, grinding, and logging!"
    lines = [f"#{i+1}: {r[0]} — {r[1]} pts ({r[2]} msgs, {r[3]} pomos)" for i, r in enumerate(rows)]
    return "Your all-time leaderboard: " + " | ".join(lines)


def streak_battle() -> str:
    """How many days in a row have you beaten the previous day?"""
    c = _conn()
    rows = c.execute(
        "SELECT date, score FROM battle_scores ORDER BY date DESC LIMIT 14"
    ).fetchall()
    c.close()
    if len(rows) < 2:
        return "Need at least 2 days of data for a streak battle."

    streak = 0
    for i in range(len(rows) - 1):
        if rows[i][1] > rows[i + 1][1]:
            streak += 1
        else:
            break

    if streak == 0:
        return "No winning streak right now. Beat today's score to start one."
    return f"You've beaten your previous day's score {streak} day{'s' if streak != 1 else ''} in a row. Keep the chain alive!"
