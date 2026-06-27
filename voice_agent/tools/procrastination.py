"""
tools/procrastination.py — Real-time procrastination detector and destroyer.

Detects lazy language, logs it, calls Praful out, sets 2-min check-back timer.
Also tracks weekly procrastination patterns.

Triggered passively in brain.py when detected phrases appear.
"""

import sqlite3
import datetime
import random
import threading
import config

DB_PATH = config.DB_PATH

LAZY_PHRASES = [
    "i'll do it later", "do it later", "maybe later", "later",
    "i'll study tomorrow", "tomorrow", "eventually", "someday", "some day",
    "i should but", "not right now", "after this", "in a while",
    "when i feel like it", "don't feel like", "too tired", "too lazy",
    "i'll start soon", "next time", "another day", "i'm not ready",
    "maybe tomorrow", "maybe next", "i'll try later",
]

CALLOUTS = [
    ("That's procrastination attempt #{n} today, Praful. "
     "You know the 2-minute rule — just open it and start. I'm checking back in 2 minutes."),
    ("'{phrase}' — classic delay tactic, attempt #{n}. "
     "Start the task for literally 2 minutes. I'll follow up."),
    ("Caught you! #{n} times today. Two minutes, right now. That's all. Go."),
    ("Yeah no. That's #{n} times you've done this today. "
     "The task isn't going anywhere, but your day is. 2 minutes — start now."),
    ("Future Praful isn't gonna thank Present Praful for this. "
     "Procrastination #{n} today. 2-minute rule. Start it. I'm timing."),
]


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS procrastination_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        context TEXT,
        date TEXT
    )""")
    c.commit()
    return c


def detect(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in LAZY_PHRASES)


def call_out(text: str) -> str:
    today = str(datetime.date.today())
    c = _conn()
    c.execute("INSERT INTO procrastination_log (context, date) VALUES (?, ?)", (text[:200], today))
    c.commit()
    n = c.execute("SELECT COUNT(*) FROM procrastination_log WHERE date=?", (today,)).fetchone()[0]
    c.close()

    # Check back in 2 minutes
    threading.Timer(120, _check_back).start()

    template = random.choice(CALLOUTS)
    phrase = text[:40]
    return template.format(n=n, phrase=phrase)


def _check_back():
    try:
        import tts
        tts.speak("Two minutes are up, Praful. Did you start? No excuses — go.")
    except Exception:
        pass


def stats() -> str:
    c = _conn()
    today_n = c.execute(
        "SELECT COUNT(*) FROM procrastination_log WHERE date=?", (str(datetime.date.today()),)
    ).fetchone()[0]
    week_n = c.execute(
        "SELECT COUNT(*) FROM procrastination_log WHERE date >= date('now', '-7 days')"
    ).fetchone()[0]
    c.close()
    if today_n == 0:
        return "Zero procrastination caught today. You're actually locked in — respect."
    return (f"Procrastination caught {today_n} time{'s' if today_n != 1 else ''} today, "
            f"{week_n} this week. Something to work on, Praful.")
