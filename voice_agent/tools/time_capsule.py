"""
tools/time_capsule.py — Voice messages to your future self, opened on a specific date.

"Time capsule for 6 months: hey future me, I hope CU is going well"
"Open time capsule" (auto-unlocks when date arrives)
"What time capsules do I have"
"Time capsule for 1 year: ..."

A background thread checks daily and reads unlocked capsules aloud.
"""

import sqlite3
import datetime
import re
import threading
import time
import config

DB_PATH = config.DB_PATH
_checked_today = False


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS time_capsules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT NOT NULL,
        unlock_date TEXT NOT NULL,
        opened INTEGER DEFAULT 0,
        created TEXT NOT NULL
    )""")
    c.commit()
    return c


def seal_capsule(query: str) -> str:
    """Record a voice message for future Praful."""
    raw = re.sub(
        r"^(time capsule for|capsule for|message to future self for|future me in)\s*",
        "", query, flags=re.IGNORECASE,
    ).strip()

    unlock_date, message = _parse_capsule(raw)
    if not unlock_date:
        return ("Tell me when to open it: 'time capsule for 6 months: hey future me...'. "
                "Options: days, weeks, months, years, or a date like July 2026.")
    if not message:
        return "What's the message? Say: 'time capsule for 6 months: [your message]'."

    c = _conn()
    c.execute(
        "INSERT INTO time_capsules (message, unlock_date, created) VALUES (?, ?, ?)",
        (message, str(unlock_date), str(datetime.date.today())),
    )
    c.commit()
    c.close()

    days_left = (unlock_date - datetime.date.today()).days
    return (f"Time capsule sealed. I'll open it for you on {unlock_date} "
            f"— {days_left} day{'s' if days_left != 1 else ''} from now. "
            f"Future Praful is going to love this.")


def list_capsules() -> str:
    c = _conn()
    rows = c.execute(
        "SELECT message, unlock_date, opened, created FROM time_capsules ORDER BY unlock_date ASC"
    ).fetchall()
    c.close()
    if not rows:
        return "No time capsules sealed. Send a message to future Praful!"
    sealed   = [(r[0][:40], r[1]) for r in rows if not r[2]]
    opened   = [(r[0][:40], r[1]) for r in rows if r[2]]
    result = ""
    if sealed:
        result += f"{len(sealed)} sealed: " + ", ".join(f"'{m}...' (opens {d})" for m, d in sealed[:3])
    if opened:
        result += f" | {len(opened)} already opened."
    return result or "No capsules."


def check_and_open_due() -> list[str]:
    """Called by background monitor — returns any capsules due today."""
    today = str(datetime.date.today())
    c = _conn()
    rows = c.execute(
        "SELECT id, message, created FROM time_capsules WHERE unlock_date <= ? AND opened=0",
        (today,),
    ).fetchall()
    for row in rows:
        c.execute("UPDATE time_capsules SET opened=1 WHERE id=?", (row[0],))
    c.commit()
    c.close()
    return [(r[1], r[2]) for r in rows]


def _parse_capsule(raw: str):
    """Returns (unlock_date, message) or (None, None)."""
    today = datetime.date.today()
    sep_match = re.search(r'[:\-](.+)', raw)
    message = sep_match.group(1).strip() if sep_match else ""
    prefix  = raw[:sep_match.start()].strip() if sep_match else raw

    # Duration patterns
    m = re.search(r'(\d+)\s*(day|week|month|year)', prefix, re.IGNORECASE)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        delta = ({"day": 1, "week": 7, "month": 30, "year": 365}[unit]) * n
        return today + datetime.timedelta(days=delta), message

    # Specific month+year: "july 2026"
    MONTHS = {"january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
              "july":7,"august":8,"september":9,"october":10,"november":11,"december":12}
    for mname, mnum in MONTHS.items():
        if mname in prefix.lower():
            yr_m = re.search(r'20\d\d', prefix)
            year = int(yr_m.group(0)) if yr_m else today.year + 1
            day_m = re.search(r'\b(\d{1,2})\b', prefix)
            day  = int(day_m.group(1)) if day_m else 1
            try:
                return datetime.date(year, mnum, day), message
            except ValueError:
                pass

    return None, None


def start_capsule_monitor():
    """Start background thread that checks for due capsules every hour."""
    def _loop():
        while True:
            time.sleep(3600)
            try:
                due = check_and_open_due()
                for message, created in due:
                    import tts
                    tts.speak(
                        f"Praful! A time capsule from {created} just unlocked. Here's what past you said: {message}"
                    )
                    time.sleep(2)
            except Exception:
                pass
    threading.Thread(target=_loop, daemon=True).start()
