"""
tools/shadow.py — Shadow Stats: deep self-analytics from conversation history.

Analyzes everything Praful has said to Buddy and generates life insights.

"Shadow report"
"Weekly life stats"
"What do I talk about most"
"My activity streak"
"Shadow analysis"
"""

import sqlite3
import datetime
import re
import requests
import config

DB_PATH = config.DB_PATH
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

STOP = {'the', 'and', 'was', 'that', 'this', 'with', 'from', 'then', 'were', 'have',
        'been', 'they', 'there', 'some', 'just', 'like', 'what', 'when', 'will',
        'you', 'buddy', 'okay', 'yeah', 'yep', 'nope', 'also', 'really', 'very',
        'said', 'tell', 'know', 'want', 'need', 'going', 'make', 'time', 'today'}


def shadow_report(days: int = 7) -> str:
    data = _gather(days)
    if data["count"] < 5:
        return "Not enough data for a shadow report yet. Keep talking — I'm always listening."

    prompt = (
        f"You are Praful's personal AI life analyst. Based on a week of his conversations, "
        f"give him a 5-sentence candid shadow report. Cover: emotional state, dominant obsessions, "
        f"productivity signals, growth areas, and one honest observation he needs to hear. "
        f"Be specific and personal — not generic life-coach fluff.\n\n"
        f"Stats: {data['count']} messages over {days} days.\n"
        f"Most frequent topics: {', '.join(data['top'][:10])}\n"
        f"Sample messages: {data['sample'][:1800]}"
    )
    return _ask(prompt, temp=0.75)


def topic_map() -> str:
    data = _gather(30)
    if not data["top"]:
        return "No conversation data yet."
    top = data["top"][:12]
    return (f"Your top topics this month: {', '.join(top[:6])}. "
            f"Also came up a lot: {', '.join(top[6:])}. "
            f"You sent {data['count']} messages total — I've been paying attention.")


def activity_streak() -> str:
    c = sqlite3.connect(DB_PATH)
    rows = c.execute(
        "SELECT DATE(timestamp) as d, COUNT(*) as n FROM conversations "
        "WHERE role='user' GROUP BY d ORDER BY d DESC LIMIT 30"
    ).fetchall()
    c.close()

    if not rows:
        return "No activity recorded yet."

    active_days  = len(rows)
    avg_msgs     = sum(r[1] for r in rows) / active_days if active_days else 0
    peak_day, peak_n = max(rows, key=lambda r: r[1])
    quiet_day, quiet_n = min(rows, key=lambda r: r[1])

    return (f"You've been active {active_days} out of the last 30 days. "
            f"Average {avg_msgs:.0f} messages/day. "
            f"Most talkative: {peak_day} ({peak_n} messages). "
            f"Quietest: {quiet_day} ({quiet_n} messages). "
            f"Consistent — I respect that.")


def word_cloud() -> str:
    data = _gather(30)
    if not data["top"]:
        return "No data yet."
    prompt = (
        f"Praful's most used words when talking to his AI: {', '.join(data['top'][:15])}. "
        f"In 2 sentences, give a witty psychoanalysis of what these words reveal about his personality. "
        f"Be funny and insightful."
    )
    return _ask(prompt, temp=0.85)


def _gather(days: int) -> dict:
    since = str(datetime.date.today() - datetime.timedelta(days=days))
    c = sqlite3.connect(DB_PATH)
    rows = c.execute(
        "SELECT content FROM conversations WHERE role='user' AND timestamp >= ? "
        "ORDER BY id DESC LIMIT 300",
        (since,),
    ).fetchall()
    c.close()

    msgs = [r[0] for r in rows]
    all_text = " ".join(msgs)
    words = re.findall(r"\b[a-z]{4,}\b", all_text.lower())
    freq: dict = {}
    for w in words:
        if w not in STOP:
            freq[w] = freq.get(w, 0) + 1
    top = [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:20]]
    return {"count": len(msgs), "top": top, "sample": " | ".join(msgs[:25])}


def _ask(prompt: str, temp: float = 0.75) -> str:
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": config.GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
        "temperature": temp,
    }
    try:
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Shadow analysis failed: {e}"
