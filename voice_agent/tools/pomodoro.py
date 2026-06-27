"""
tools/pomodoro.py — Pomodoro timer with voice alerts and session tracking.

"Start pomodoro" / "Start 45 minute pomodoro"
"Stop pomodoro"
"Pomodoro status" / "How many pomodoros today"
"""

import threading
import time
import datetime
import sqlite3
import re
import config

_stop_event = threading.Event()
_session: dict = {"active": False, "start": 0.0, "work_mins": 25, "break_mins": 5, "round": 0}


def _conn():
    c = sqlite3.connect(config.DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS pomodoro_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work_mins INTEGER,
        date TEXT
    )""")
    c.commit()
    return c


def start_pomodoro(query: str = "") -> str:
    if _session["active"]:
        return "Pomodoro's already running. Say 'stop pomodoro' first."

    work, brk = _parse_times(query)
    _stop_event.clear()
    _session.update(active=True, start=time.time(), work_mins=work, break_mins=brk, round=1)

    threading.Thread(target=_run, args=(work, brk), daemon=True).start()
    return f"Pomodoro started! {work} minutes of pure focus. Let's go Praful!"


def stop_pomodoro() -> str:
    if not _session["active"]:
        return "No pomodoro running right now."
    _stop_event.set()
    _session["active"] = False
    return "Pomodoro cancelled. Rest up."


def pomodoro_status() -> str:
    c = _conn()
    today_count = c.execute(
        "SELECT COUNT(*) FROM pomodoro_log WHERE date=?", (str(datetime.date.today()),)
    ).fetchone()[0]
    c.close()

    if not _session["active"]:
        return f"No active pomodoro. You've done {today_count} session{'s' if today_count != 1 else ''} today."

    elapsed = int((time.time() - _session["start"]) / 60)
    remaining = max(0, _session["work_mins"] - elapsed)
    return (f"Round {_session['round']} active — {remaining} minute{'s' if remaining != 1 else ''} left. "
            f"{today_count} session{'s' if today_count != 1 else ''} completed today.")


def _parse_times(query: str):
    t = query.lower()
    work = 25
    brk = 5
    m = re.search(r'(\d+)\s*(?:minute|min)', t)
    if m:
        work = int(m.group(1))
        brk = max(5, work // 5)
    return work, brk


def _run(work_mins: int, break_mins: int):
    import tts
    round_num = 1

    while not _stop_event.is_set():
        _session["round"] = round_num
        tts.speak(f"Round {round_num}. {work_mins} minutes of focus. No distractions.")

        if _stop_event.wait(work_mins * 60):
            break

        if _stop_event.is_set():
            break

        # Log completed session
        c = _conn()
        c.execute("INSERT INTO pomodoro_log (work_mins, date) VALUES (?, ?)",
                  (work_mins, str(datetime.date.today())))
        c.commit()
        c.close()

        if round_num % 4 == 0:
            tts.speak("Incredible — four rounds done! Take a 15 minute long break. You've earned it.")
            if _stop_event.wait(15 * 60):
                break
        else:
            tts.speak(f"Nice! Round {round_num} done. {break_mins} minute break. Stretch a little.")
            if _stop_event.wait(break_mins * 60):
                break

        if _stop_event.is_set():
            break

        round_num += 1
        tts.speak("Break's over. Back to it!")

    _session["active"] = False
    if not _stop_event.is_set():
        tts.speak("All pomodoro sessions done. Great work today, Praful!")
