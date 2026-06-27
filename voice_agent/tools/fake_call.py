"""
tools/fake_call.py — Fake incoming call to escape awkward situations.

"Fake call in 2 minutes"
"Call me in 5 minutes from mom"
"Schedule escape call"
"Cancel fake call"
"""

import subprocess
import threading
import re
import random

_timer: threading.Timer | None = None

CALLERS = ["Mom", "Dad", "Bhai", "Rohit", "Riya", "Professor Singh", "Priya", "Unknown Number"]


def schedule_fake_call(query: str) -> str:
    global _timer

    minutes = _parse_minutes(query)
    caller  = _pick_caller(query)

    if _timer and _timer.is_alive():
        _timer.cancel()

    delay_secs = max(10, int(minutes * 60))
    _timer = threading.Timer(delay_secs, _trigger, args=(caller,))
    _timer.daemon = True
    _timer.start()

    human = f"{int(minutes)} minute{'s' if minutes != 1 else ''}" if minutes >= 1 else "30 seconds"
    return f"Fake call from {caller} set for {human} from now. I've got you — escape ready!"


def cancel_fake_call() -> str:
    global _timer
    if _timer and _timer.is_alive():
        _timer.cancel()
        _timer = None
        return "Fake call cancelled."
    return "No fake call scheduled."


def _trigger(caller: str):
    try:
        subprocess.run([
            "termux-notification",
            "--title", f"\U0001f4de Incoming Call — {caller}",
            "--content", "Tap to answer",
            "--id", "911",
            "--priority", "high",
            "--sound",
            "--vibrate", "500,200,500,200,500",
        ], timeout=5)
    except Exception:
        pass

    try:
        import tts
        tts.speak(f"Incoming call. Incoming call from {caller}.")
    except Exception:
        pass


def _parse_minutes(query: str) -> float:
    t = query.lower()
    m = re.search(r'(\d+)\s*(minute|min|second|sec)', t)
    if m:
        val = int(m.group(1))
        return val / 60 if 'sec' in m.group(2) else float(val)
    return 2.0


def _pick_caller(query: str) -> str:
    t = query.lower()
    named = ["mom", "dad", "bhai", "rohit", "riya", "priya", "professor"]
    for name in named:
        if name in t:
            return name.capitalize()
    return random.choice(CALLERS)
