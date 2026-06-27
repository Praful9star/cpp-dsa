"""
tools/life_os.py — Treats Praful's life like a computer operating system.

Generates a full OS health report with CPU, RAM, Storage, Processes, Bugs, etc.
Completely unique way to think about productivity and life.

"Life OS report"
"Run diagnostics"
"System status"
"What processes are running"
"Check my RAM"
"""

import sqlite3
import datetime
import requests
import config

DB_PATH = config.DB_PATH
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _gather_metrics() -> dict:
    today = str(datetime.date.today())
    c = sqlite3.connect(DB_PATH)

    msgs_today = c.execute(
        "SELECT COUNT(*) FROM conversations WHERE role='user' AND DATE(timestamp)=?", (today,)
    ).fetchone()[0]

    msgs_week = c.execute(
        "SELECT COUNT(*) FROM conversations WHERE role='user' AND timestamp >= date('now', '-7 days')"
    ).fetchone()[0]

    facts_count = 0
    try:
        facts_count = c.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    except Exception:
        pass

    notes_count = 0
    try:
        notes_count = c.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    except Exception:
        pass

    reminders = 0
    try:
        reminders = c.execute("SELECT COUNT(*) FROM reminders WHERE fired=0").fetchone()[0]
    except Exception:
        pass

    poms_today = 0
    try:
        poms_today = c.execute(
            "SELECT COUNT(*) FROM pomodoro_log WHERE date=?", (today,)
        ).fetchone()[0]
    except Exception:
        pass

    sr_due = 0
    try:
        sr_due = c.execute(
            "SELECT COUNT(*) FROM sr_cards WHERE next_review <= ?", (today,)
        ).fetchone()[0]
    except Exception:
        pass

    streak = 0
    try:
        row = c.execute("SELECT count FROM streak WHERE id=1").fetchone()
        streak = row[0] if row else 0
    except Exception:
        pass

    expenses_today = 0
    try:
        expenses_today = c.execute(
            "SELECT COUNT(*) FROM expenses WHERE date=?", (today,)
        ).fetchone()[0]
    except Exception:
        pass

    c.close()

    return {
        "msgs_today": msgs_today, "msgs_week": msgs_week,
        "facts": facts_count, "notes": notes_count,
        "reminders": reminders, "pomodoros": poms_today,
        "sr_due": sr_due, "streak": streak, "expenses": expenses_today,
    }


def life_os_report() -> str:
    m = _gather_metrics()

    cpu = min(100, m["pomodoros"] * 20 + m["msgs_today"] * 3)
    ram = min(100, m["facts"] * 4 + m["notes"] * 2)
    storage = m["facts"] + m["notes"] + m["msgs_week"] // 5
    active_processes = []
    if m["reminders"] > 0: active_processes.append(f"{m['reminders']} reminder{'s' if m['reminders']>1 else ''}")
    if m["sr_due"] > 0:    active_processes.append(f"{m['sr_due']} reviews due")
    bugs = []
    if m["sr_due"] > 3:    bugs.append("review queue overflow")
    if m["msgs_today"] < 3: bugs.append("low engagement today")
    if m["pomodoros"] == 0: bugs.append("no focus sessions detected")

    prompt = (
        f"Generate a Praful's Life OS diagnostic report. Frame his life as an operating system. "
        f"Be creative and specific. Use:\n"
        f"- CPU (focus/productivity): {cpu}% — {m['pomodoros']} pomodoros today, {m['msgs_today']} interactions\n"
        f"- RAM (active memory/facts): {ram}% — {m['facts']} facts learned, {m['notes']} notes stored\n"
        f"- Storage: {storage} units — {m['msgs_week']} messages this week\n"
        f"- Running processes: {', '.join(active_processes) or 'idle'}\n"
        f"- Streak uptime: {m['streak']} days\n"
        f"- Known bugs: {', '.join(bugs) or 'none detected'}\n\n"
        f"Write the report in 5-6 sentences as if it's a real OS diagnostic. "
        f"Include a performance rating (like 67/100), a bottleneck, and one recommended patch. "
        f"Make it feel like a real system report but about his life. Spoken naturally."
    )
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": config.GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
        "temperature": 0.8,
    }
    try:
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return (f"LIFE OS v1.0 — CPU {cpu}%, RAM {ram}%, Streak {m['streak']} days. "
                f"Processes: {', '.join(active_processes) or 'idle'}. "
                f"Bugs: {', '.join(bugs) or 'none'}.")


def quick_status() -> str:
    m = _gather_metrics()
    cpu = min(100, m["pomodoros"] * 20 + m["msgs_today"] * 3)
    return (f"LIFE OS: CPU {cpu}% | RAM: {m['facts']} facts | "
            f"Uptime: {m['streak']}d streak | Processes: {m['reminders']} reminders | "
            f"Bugs: {'review queue' if m['sr_due'] > 0 else 'none'}.")
