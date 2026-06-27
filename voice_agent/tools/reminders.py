"""
tools/reminders.py — Timers, reminders, and alarms.

"Remind me in 20 minutes to drink water"
"Set a timer for 5 minutes"
"Set alarm for 8 AM"
"Cancel reminder"
"""

import threading
import time
import re
import datetime

# Import tts lazily to avoid circular imports
_tts_speak = None
def _speak(text):
    global _tts_speak
    if _tts_speak is None:
        import tts
        _tts_speak = tts.speak
    _tts_speak(text)


_reminders: list[dict] = []
_lock = threading.Lock()


def set_reminder(text: str) -> str:
    """Parse a natural language reminder/timer request and schedule it."""
    t = text.lower()

    seconds = _parse_duration(t)
    alarm_time = _parse_alarm_time(t)

    # Extract the task (what to remind about)
    task = _extract_task(text)

    if seconds:
        label = task or "your reminder"
        _schedule(seconds, label)
        human_time = _human_duration(seconds)
        return f"Got it — I'll remind you about '{label}' in {human_time}."

    elif alarm_time:
        now = datetime.datetime.now()
        target = datetime.datetime.combine(now.date(), alarm_time)
        if target <= now:
            target += datetime.timedelta(days=1)
        seconds = int((target - now).total_seconds())
        label = task or "your alarm"
        _schedule(seconds, label)
        return f"Alarm set for {alarm_time.strftime('%I:%M %p')} — I'll wake you up for '{label}'."

    return "I couldn't figure out when to remind you. Try 'remind me in 10 minutes to...' or 'set alarm for 7 AM'."


def cancel_reminders() -> str:
    with _lock:
        count = len(_reminders)
        _reminders.clear()
    if count:
        return f"Cancelled {count} reminder{'s' if count > 1 else ''}."
    return "No active reminders to cancel."


def list_reminders() -> str:
    with _lock:
        if not _reminders:
            return "No active reminders."
        lines = []
        for r in _reminders:
            remaining = int(r["fire_at"] - time.time())
            if remaining > 0:
                lines.append(f"• '{r['label']}' in {_human_duration(remaining)}")
        return "Active reminders:\n" + "\n".join(lines) if lines else "No active reminders."


# ── Internal ──────────────────────────────────────────────────────────────────

def _schedule(seconds: int, label: str):
    entry = {"fire_at": time.time() + seconds, "label": label}
    with _lock:
        _reminders.append(entry)

    def _fire():
        time.sleep(seconds)
        with _lock:
            if entry in _reminders:
                _reminders.remove(entry)
        _speak(f"Hey Praful! Reminder: {label}")
        # Repeat once in case it was missed
        time.sleep(5)
        _speak(f"Just reminding you again: {label}")

    threading.Thread(target=_fire, daemon=True).start()


def _parse_duration(text: str) -> int | None:
    """Return total seconds from phrases like '5 minutes', '1 hour 30 minutes'."""
    total = 0
    patterns = [
        (r"(\d+)\s*hour",   3600),
        (r"(\d+)\s*min",    60),
        (r"(\d+)\s*sec",    1),
    ]
    found = False
    for pattern, multiplier in patterns:
        m = re.search(pattern, text)
        if m:
            total += int(m.group(1)) * multiplier
            found = True
    return total if found else None


def _parse_alarm_time(text: str) -> datetime.time | None:
    """Parse '7 AM', '10:30 PM', '08:00' etc."""
    # HH:MM AM/PM
    m = re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)?", text, re.IGNORECASE)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        ampm = (m.group(3) or "").lower()
        if ampm == "pm" and h != 12:
            h += 12
        if ampm == "am" and h == 12:
            h = 0
        try:
            return datetime.time(h, mn)
        except ValueError:
            pass

    # H AM/PM
    m = re.search(r"(\d{1,2})\s*(am|pm)", text, re.IGNORECASE)
    if m:
        h = int(m.group(1))
        ampm = m.group(2).lower()
        if ampm == "pm" and h != 12:
            h += 12
        if ampm == "am" and h == 12:
            h = 0
        try:
            return datetime.time(h, 0)
        except ValueError:
            pass
    return None


def _extract_task(text: str) -> str:
    """Pull out what the reminder is about."""
    for kw in ["to remind me to", "to remind me about", "remind me to",
                "remind me about", "to ", "about ", "for "]:
        idx = text.lower().find(kw)
        if idx != -1:
            candidate = text[idx + len(kw):].strip(" .,")
            if len(candidate) > 2:
                return candidate
    return ""


def _human_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} seconds"
    if seconds < 3600:
        m = seconds // 60
        s = seconds % 60
        return f"{m} minute{'s' if m>1 else ''}" + (f" {s}s" if s else "")
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h} hour{'s' if h>1 else ''}" + (f" {m} min" if m else "")
